import json
import os

def compare_policies(txt_file_path, json_file_path):
    # 1. Read v4 policy names from the text file
    if not os.path.exists(txt_file_path):
        print(f"Error: Text file not found at {txt_file_path}")
        return
    
    with open(txt_file_path, 'r', encoding='utf-8') as f:
        # Strip whitespace/newlines and ignore empty lines
        v4_names = [line.strip() for line in f if line.strip()]
    
    # 2. Load v5 policies from the JSON file
    if not os.path.exists(json_file_path):
        print(f"Error: JSON file not found at {json_file_path}")
        return
        
    with open(json_file_path, 'r', encoding='utf-8') as f:
        v5_data = json.load(f)
    
    # Extract all 'displayName' values into a set for fast O(1) lookups
    v5_names = set()
    if isinstance(v5_data, list):
        for policy in v5_data:
            if isinstance(policy, dict) and 'displayName' in policy:
                v5_names.add(policy['displayName'])
    else:
        print("Error: JSON root structure is not a list.")
        return

    # 3. Perform comparison
    found = []
    missing = []
    
    for name in v4_names:
        if name in v5_names:
            found.append(name)
        else:
            missing.append(name)
            
    # 4. Report Results
    print("=" * 50)
    print(f" COMPARISON RESULTS (v4 vs v5)")
    print("=" * 50)
    print(f"Total v4 policies checked: {len(v4_names)}")
    print(f"Found in v5:             {len(found)}")
    print(f"Missing from v5:         {len(missing)}")
    print("=" * 50)
    
    if missing:
        print("\n[!] MISSING POLICIES IN V5:")
        for name in missing:
            print(f"  - {name}")
    else:
        print("\n[+] All v4 policies were found in v5!")

    if found:
        print("\n[✓] FOUND POLICIES IN V5:")
        for name in found:
            print(f"  + {name}")

if __name__ == "__main__":
    # Update these filenames/paths to match your local file names
    TXT_PATH = "v4-policy-names.txt"
    JSON_PATH = "stg_policies_backup.json"
    
    compare_policies(TXT_PATH, JSON_PATH)