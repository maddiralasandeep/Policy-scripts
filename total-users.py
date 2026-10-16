import json
import os
from dotenv import load_dotenv
import requests

load_dotenv()

allenvs = {
    "plainid4-prod": "plainid4.x.com",
    "plainid5-prod": "plainid5platform.x.com",
}



apipath = "/api/runtime/userlist/v3"
headers = {
    "Content-Type": "application/json",
}

# Loop through each environment
for env_key, env_host in allenvs.items():
    # Select appropriate client ID and secret based on the environment version
    if "plainid4" in env_key:
        client_id = os.getenv("clientid_abc_plainid4_dev")
        client_secret = os.getenv("secret_abc_plainid4_dev")
    else:
        client_id = os.getenv("clientid_abc_plainid5_dev")
        client_secret = os.getenv("secret_abc_plainid5_dev")

    print(f"\n--- Checking Environment: {env_key} ({env_host}) ---")

    # Loop through each path for the current environment
    for path_name, path_value in paths.items():
        payload = {
            "clientId": client_id,
            "clientSecret": client_secret,
            "asset": {
                "resourceType": "Application",
                "path": path_value,
                "action": "Access",
            },
        }

        url = f"https://{env_host}{apipath}"

        try:
            response = requests.request(
                "POST", url, headers=headers, data=json.dumps(payload)
            )
            response.raise_for_status()
            totalresponse = response.json()

            # Safely extract user count length
            try:
                user_count = len(totalresponse["response"][0]["entities"])
            except (KeyError, IndexError, TypeError):
                user_count = 0

            print(
                f"Total no. of users for this {env_key} and path: {path_name} ({path_value}) is: {user_count}"
            )

        except Exception as e:
            print(
                f"URL {url} or path '{path_name}' failed for {env_key}. Error: {e}"
            )