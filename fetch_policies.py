import requests
import json
import os

# ==========================================
# CONFIGURATION - SOURCE (STG) ENVIRONMENT
# ==========================================
BASE_URL = "https://api.us1.plainid.io"
TOKEN = "YOUR_BEARER_TOKEN"
STG_ENV_ID = "YOUR_STG_ENV_ID"
STG_WS_ID = "YOUR_STG_WORKSPACE_ID"

HEADERS_LIST = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

def get_all_policies():
    """Paginates the Source Workspace and returns a list of all active policy dictionaries."""
    all_policies = []
    offset = 0
    limit = 50

    while True:
        list_url = f"{BASE_URL}/api/1.0/policies-search/{STG_ENV_ID}?limit={limit}&offset={offset}"
        list_payload = {
            "authzWsIds": [STG_WS_ID],
            "state": "active",
            "detailed": True
        }
        
        res = requests.post(list_url, headers=HEADERS_LIST, json=list_payload)
        
        if res.status_code != 200:
            print(f"Error fetching policies: {res.status_code} - {res.text}")
            break
            
        data = res.json().get("data", [])
        
        if not data:
            break
            
        all_policies.extend(data)
        offset += limit
        
    return all_policies

if __name__ == "__main__":
    print("Fetching all active policies...\n")
    policies = get_all_policies()
    
    if policies:
        # Print structured console table
        print(f"{'Policy ID':<40} | {'Display Name'}")
        print("-" * 80)
        
        for policy in policies:
            pid = policy.get("policyId", "Unknown ID")
            name = policy.get("displayName", "Unknown Name")
            print(f"{pid:<40} | {name}")
            
        print("-" * 80)
        
        # Save raw backup artifact
        backup_filename = "stg_policies_backup.json"
        with open(backup_filename, "w") as f:
            json.dump(policies, f, indent=2)
            
        print(f"\n[+] Successfully retrieved {len(policies)} policies.")
        print(f"[+] Full raw policy data saved to: {os.path.abspath(backup_filename)}")
    else:
        print("No policies were found or an error occurred.")