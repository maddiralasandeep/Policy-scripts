import requests
import os
import time

# Import the extraction module from Script 1
from fetch_policies import get_all_policies

# ==========================================
# CONFIGURATION - TARGET (PROD) ENVIRONMENT
# ==========================================
BASE_URL = "https://api.us1.plainid.io"
TOKEN = "YOUR_BEARER_TOKEN"
PROD_ENV_ID = "YOUR_PROD_ENV_ID"
PROD_WS_ID = "YOUR_PROD_WORKSPACE_ID"

STATE_FILE = "successful_imports.txt"

HEADERS_IMPORT = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "text/plain;language=rego" 
}

def load_successful_imports():
    """Reads the local state ledger to skip already imported policies."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return set(line.strip() for line in f)
    return set()

def mark_successful(policy_id):
    """Appends a successful Policy ID to the local state ledger."""
    with open(STATE_FILE, "a") as f:
        f.write(f"{policy_id}\n")

def run_migration():
    successful_imports = load_successful_imports()
    
    print("Connecting to Source Environment to fetch policies...")
    
    # Execute the fetch silently
    policies_to_import = get_all_policies()
    
    if not policies_to_import:
        print("No policies found from Source. Exiting.")
        return
        
    print(f"\nStarting migration of {len(policies_to_import)} policies to Production...\n")

    for policy in policies_to_import:
        policy_id = policy.get("policyId")
        display_name = policy.get("displayName")
        structured_rego = policy.get("structuredRego")

        # Core validation
        if not policy_id or not structured_rego:
            continue

        # Check local state file to prevent duplicate imports
        if policy_id in successful_imports:
            print(f"SKIPPED: {policy_id} | {display_name} (Already in Production)")
            continue

        import_url = f"{BASE_URL}/api/2.0/policies/{PROD_ENV_ID}"
        import_params = {
            "filter[authWsId]": PROD_WS_ID,
            "filter[id]": policy_id,
            "filter[extendedSchema]": "True",
            "evaluateByBBName": "false"
        }

        # Send raw rego bytes
        import_res = requests.post(
            import_url, 
            headers=HEADERS_IMPORT, 
            params=import_params, 
            data=structured_rego.encode('utf-8')
        )

        # Handle API response and log to console/ledger
        if import_res.status_code in [200, 201]:
            print(f"SUCCESS: {policy_id} | {display_name} imported.")
            mark_successful(policy_id)
        else:
            print(f"FAILED:  {policy_id} | {display_name} | Status: {import_res.status_code} | Error: {import_res.text}")

        # Protect target API
        time.sleep(0.2)

    print("\nMigration Complete.")

if __name__ == "__main__":
    run_migration()