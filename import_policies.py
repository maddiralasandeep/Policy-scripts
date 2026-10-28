import argparse
import json
import os
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

from fetch_policies import (
    BASE_URL,
    STG_CLIENT_ID,
    STG_CLIENT_SECRET,
    STG_ENV_ID,
    STG_WS_ID,
    get_all_policies,
    get_token,
)


load_dotenv()

PROD_ENV_ID = os.getenv("PROD_ENV_ID", "YOUR_PROD_ENV_ID")
PROD_WS_ID = os.getenv("PROD_WS_ID", "YOUR_PROD_WORKSPACE_ID")
PROD_CLIENT_ID = os.getenv("PROD_CLIENT_ID")
PROD_CLIENT_SECRET = os.getenv("PROD_CLIENT_SECRET")
DELTA_REPORT_FILE = os.getenv("DELTA_REPORT_FILE", "policy_delta_report.json")
STATE_FILE = os.getenv("STATE_FILE", "successful_imports.txt")


def normalize_policy_name(name):
    """Normalize a display name for reliable STG-to-PROD comparison."""
    return " ".join((name or "").split()).casefold()


def build_policy_delta(source_policies, target_policies):
    """Return source policies whose display names are absent from target."""
    target_names = {
        normalize_policy_name(policy.get("displayName"))
        for policy in target_policies
        if normalize_policy_name(policy.get("displayName"))
    }

    delta = []
    skipped_existing = []
    invalid_source = []
    duplicate_source = []
    seen_source_names = set()

    for policy in source_policies:
        policy_name = normalize_policy_name(policy.get("displayName"))

        if not policy_name or not policy.get("policyId"):
            invalid_source.append(policy)
            continue
        elif policy_name in seen_source_names:
            duplicate_source.append(policy)
        elif policy_name in target_names:
            skipped_existing.append(policy)
        else:
            delta.append(policy)

        seen_source_names.add(policy_name)

    return delta, skipped_existing, invalid_source, duplicate_source


def write_delta_report(
    source_policies,
    target_policies,
    delta,
    skipped_existing,
    invalid_source,
    duplicate_source,
    report_file=DELTA_REPORT_FILE,
):
    """Write the comparison result before any target changes are made."""
    report = {
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "comparisonKey": (
            "normalized displayName (trimmed, whitespace-collapsed, "
            "case-insensitive)"
        ),
        "sourcePolicyCount": len(source_policies),
        "targetPolicyCount": len(target_policies),
        "deltaPolicyCount": len(delta),
        "alreadyInTargetCount": len(skipped_existing),
        "invalidSourcePolicyCount": len(invalid_source),
        "duplicateSourceNameCount": len(duplicate_source),
        "deltaPolicies": [
            {
                "policyId": policy.get("policyId"),
                "displayName": policy.get("displayName"),
            }
            for policy in delta
        ],
        "alreadyInTarget": [
            {
                "policyId": policy.get("policyId"),
                "displayName": policy.get("displayName"),
            }
            for policy in skipped_existing
        ],
        "invalidSourcePolicies": [
            {
                "policyId": policy.get("policyId"),
                "displayName": policy.get("displayName"),
            }
            for policy in invalid_source
        ],
        "duplicateSourceNames": [
            {
                "policyId": policy.get("policyId"),
                "displayName": policy.get("displayName"),
            }
            for policy in duplicate_source
        ],
    }

    with open(report_file, "w", encoding="utf-8") as output_file:
        json.dump(report, output_file, indent=2)

    return os.path.abspath(report_file)


def mark_successful(policy_id, display_name):
    """Append an import result to the local audit ledger."""
    timestamp = datetime.now(timezone.utc).isoformat()
    with open(STATE_FILE, "a", encoding="utf-8") as state_file:
        state_file.write(f"{timestamp}\t{policy_id}\t{display_name}\n")


def import_policy(policy, prod_token):
    """Import one policy into PROD and return the HTTP response."""
    policy_id = policy.get("policyId")
    structured_rego = policy.get("structuredRego")
    if not structured_rego:
        raise ValueError(f"Policy {policy_id} does not contain structuredRego.")

    import_url = f"{BASE_URL}/api/2.0/policies/{PROD_ENV_ID}"
    import_params = {
        "filter[authWsId]": PROD_WS_ID,
        "filter[id]": policy_id,
        "filter[extendedSchema]": "True",
        "evaluateByBBName": "false",
    }
    headers = {
        "Authorization": f"Bearer {prod_token}",
        "Content-Type": "text/plain;language=rego",
    }

    return requests.post(
        import_url,
        headers=headers,
        params=import_params,
        data=structured_rego.encode("utf-8"),
        timeout=60,
    )


def validate_configuration():
    configuration = {
        "STG_ENV_ID": STG_ENV_ID,
        "STG_WS_ID": STG_WS_ID,
        "STG_CLIENT_ID": STG_CLIENT_ID,
        "STG_CLIENT_SECRET": STG_CLIENT_SECRET,
        "PROD_ENV_ID": PROD_ENV_ID,
        "PROD_WS_ID": PROD_WS_ID,
        "PROD_CLIENT_ID": PROD_CLIENT_ID,
        "PROD_CLIENT_SECRET": PROD_CLIENT_SECRET,
    }
    missing = [
        key
        for key, value in configuration.items()
        if not value or value.startswith("YOUR_")
    ]
    if missing:
        raise ValueError(
            "Set valid environment variables for: " + ", ".join(missing)
        )


def run_migration(dry_run=False):
    validate_configuration()

    print("Generating token with STG credentials...")
    stg_token = get_token(STG_CLIENT_ID, STG_CLIENT_SECRET, "STG")

    print("Generating token with PROD credentials...")
    prod_token = get_token(PROD_CLIENT_ID, PROD_CLIENT_SECRET, "PROD")

    print("Fetching active policies from STG...")
    source_policies = get_all_policies(
        STG_ENV_ID,
        STG_WS_ID,
        token=stg_token,
        environment_name="STG",
    )

    print("\nFetching active policies from PROD...")
    target_policies = get_all_policies(
        PROD_ENV_ID,
        PROD_WS_ID,
        token=prod_token,
        environment_name="PROD",
    )

    delta, existing, invalid, duplicates = build_policy_delta(
        source_policies,
        target_policies,
    )
    report_path = write_delta_report(
        source_policies,
        target_policies,
        delta,
        existing,
        invalid,
        duplicates,
    )

    print("\nComparison complete:")
    print(f"  STG active policies:             {len(source_policies)}")
    print(f"  PROD active policies:            {len(target_policies)}")
    print(f"  Already present by policy name:  {len(existing)}")
    print(f"  Missing from PROD (delta):       {len(delta)}")
    print(f"  Invalid STG policies:            {len(invalid)}")
    print(f"  Duplicate STG policy names:      {len(duplicates)}")
    print(f"  Delta report:                    {report_path}")

    if not delta:
        print("\nNo missing policies to import.")
        return

    print("\nPolicies missing from PROD:")
    for policy in delta:
        print(f"  - {policy.get('policyId')} | {policy.get('displayName')}")

    if dry_run:
        print("\nDRY RUN: No policies were imported.")
        return

    print(f"\nImporting {len(delta)} missing policies into PROD...\n")
    success_count = 0
    failure_count = 0

    for policy in delta:
        policy_id = policy.get("policyId")
        display_name = policy.get("displayName")

        try:
            response = import_policy(policy, prod_token)
            if response.status_code in (200, 201):
                print(f"SUCCESS: {policy_id} | {display_name}")
                mark_successful(policy_id, display_name)
                success_count += 1
            else:
                print(
                    f"FAILED:  {policy_id} | {display_name} | "
                    f"Status: {response.status_code} | Error: {response.text}"
                )
                failure_count += 1
        except (requests.RequestException, ValueError) as error:
            print(f"FAILED:  {policy_id} | {display_name} | Error: {error}")
            failure_count += 1

        time.sleep(0.2)

    print(
        f"\nMigration complete. Successful: {success_count}; Failed: {failure_count}."
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Import STG policies whose names do not exist in PROD."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate and display the delta without importing policies.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    try:
        run_migration(dry_run=arguments.dry_run)
    except (requests.RequestException, ValueError) as error:
        raise SystemExit(f"Migration stopped: {error}") from error