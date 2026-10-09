import os
import json
import requests
import urllib3
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

BASE_URL = "https://api.us1.plainid.io"
STG_ENV_ID = "YOUR_STG_ENV_ID"
STG_WS_ID = "YOUR_STG_WORKSPACE_ID"

def get_token():
    url = f"{BASE_URL}/api/1.0/api-key/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    payload = {
        "grant_type": "client_credentials",
        "clientId": os.getenv("CLIENT_ID"), 
        "clientSecret": os.getenv("CLIENT_SECRET") 
    }
    res = requests.post(url, headers=headers, data=payload, verify=False)
    res.raise_for_status() 
    return res.json().get("access_token")

def get_all_policies():
    fresh_token = get_token()
    headers_list = {
        "Authorization": f"Bearer {fresh_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
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
        
        res = requests.post(list_url, headers=headers_list, json=list_payload, verify=False)
        
        if res.status_code != 200:
            print(f"Error fetching policies: {res.status_code} - {res.text}")
            break
            
        response_json = res.json()
        data = response_json.get("data", [])
        meta = response_json.get("meta", {})
        
        if not data:
            break
            
        all_policies.extend(data)
        
        # Extract the total available records from the meta object
        total_policies = meta.get("total", 0)
        
        print(f"Fetched {len(data)} policies... (Total saved: {len(all_policies)} / {total_policies})")
        
        offset += limit
        
        # Terminate the loop once the offset reaches or exceeds the total records available
        if offset >= total_policies:
            break
            
    return all_policies

if __name__ == "__main__":
    print("Fetching all active policies...\n")
    policies = get_all_policies()
    
    if policies:
        print(f"\n{'Policy ID':<40} | {'Display Name'}")
        print("-" * 80)
        
        for policy in policies:
            pid = policy.get("policyId", "Unknown ID")
            name = policy.get("displayName", "Unknown Name")
            print(f"{pid:<40} | {name}")
            
        print("-" * 80)
        
        backup_filename = "stg_policies_backup.json"
        with open(backup_filename, "w") as f:
            json.dump(policies, f, indent=2)
            
        print(f"\n[+] Successfully retrieved {len(policies)} policies.")
        print(f"[+] Full raw policy data saved to: {os.path.abspath(backup_filename)}")
    else:
        print("No policies were found or an error occurred.")