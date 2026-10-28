import json
import os

import requests
import urllib3
from dotenv import load_dotenv


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

BASE_URL = os.getenv("PLAINID_BASE_URL", "https://api.us1.plainid.io")
STG_ENV_ID = os.getenv("STG_ENV_ID", "YOUR_STG_ENV_ID")
STG_WS_ID = os.getenv("STG_WS_ID", "YOUR_STG_WORKSPACE_ID")
STG_CLIENT_ID = os.getenv("STG_CLIENT_ID")
STG_CLIENT_SECRET = os.getenv("STG_CLIENT_SECRET")


def get_token(client_id, client_secret, environment_name):
    """Return a PlainID bearer token using client credentials."""
    if not client_id or not client_secret:
        raise ValueError(
            f"{environment_name}_CLIENT_ID and {environment_name}_CLIENT_SECRET "
            "are required."
        )

    url = f"{BASE_URL}/api/1.0/api-key/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    payload = {
        "grant_type": "client_credentials",
        "clientId": client_id,
        "clientSecret": client_secret,
    }

    response = requests.post(
        url,
        headers=headers,
        data=payload,
        verify=False,
        timeout=30,
    )
    response.raise_for_status()

    token = response.json().get("access_token")
    if not token:
        raise ValueError("PlainID token response did not contain access_token.")
    return token


def get_all_policies(
    env_id=STG_ENV_ID,
    workspace_id=STG_WS_ID,
    token=None,
    environment_name="STG",
):
    """Fetch every active policy from a specified environment/workspace."""
    if not env_id or env_id.startswith("YOUR_"):
        raise ValueError(f"A valid {environment_name} environment ID is required.")
    if not workspace_id or workspace_id.startswith("YOUR_"):
        raise ValueError(f"A valid {environment_name} workspace ID is required.")

    token = token or get_token(STG_CLIENT_ID, STG_CLIENT_SECRET, "STG")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    all_policies = []
    offset = 0
    limit = 50

    while True:
        list_url = f"{BASE_URL}/api/1.0/policies-search/{env_id}"
        list_payload = {
            "authzWsIds": [workspace_id],
            "state": "active",
            "detailed": True,
        }

        response = requests.post(
            list_url,
            headers=headers,
            params={"limit": limit, "offset": offset},
            json=list_payload,
            verify=False,
            timeout=60,
        )
        response.raise_for_status()

        response_json = response.json()
        data = response_json.get("data", [])
        meta = response_json.get("meta", {})

        if not data:
            break

        all_policies.extend(data)
        total_policies = meta.get("total")
        total_text = total_policies if total_policies is not None else "unknown"
        print(
            f"[{environment_name}] Fetched {len(data)} policies "
            f"(total fetched: {len(all_policies)} / {total_text})"
        )

        offset += len(data)
        if total_policies is not None and offset >= total_policies:
            break
        if len(data) < limit:
            break

    return all_policies


if __name__ == "__main__":
    print("Fetching all active STG policies...\n")
    policies = get_all_policies()

    if policies:
        print(f"\n{'Policy ID':<40} | Display Name")
        print("-" * 80)

        for policy in policies:
            policy_id = policy.get("policyId", "Unknown ID")
            name = policy.get("displayName", "Unknown Name")
            print(f"{policy_id:<40} | {name}")

        print("-" * 80)

        backup_filename = "stg_policies_backup.json"
        with open(backup_filename, "w", encoding="utf-8") as backup_file:
            json.dump(policies, backup_file, indent=2)

        print(f"\n[+] Successfully retrieved {len(policies)} policies.")
        print(
            "[+] Full raw policy data saved to: "
            f"{os.path.abspath(backup_filename)}"
        )
    else:
        print("No policies were found.")