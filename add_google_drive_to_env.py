#!/usr/bin/env python3
"""
Add Google Drive service account credentials to .env file.

Reads the JSON key file and adds it to .env as GOOGLE_SERVICE_ACCOUNT_JSON.
"""

import os
import json
import sys
from pathlib import Path

import argparse

# Parse command line arguments
parser = argparse.ArgumentParser(description="Add Google Drive service account credentials to .env file")
parser.add_argument("json_key_file", help="Path to the JSON key file")
parser.add_argument("folder_id", help="Google Drive folder ID")
args = parser.parse_args()

JSON_KEY_FILE = args.json_key_file
ENV_FILE = ".env"
FOLDER_ID = args.folder_id

def main():
    """Add Google Drive credentials to .env file."""
    print("=" * 60)
    print("Adding Google Drive credentials to .env file")
    print("=" * 60)
    print()
    
    # Check if JSON file exists
    if not os.path.exists(JSON_KEY_FILE):
        print(f"❌ JSON key file not found: {JSON_KEY_FILE}")
        return False
    
    print(f"✅ Found JSON key file: {JSON_KEY_FILE}")
    
    # Read and validate JSON
    try:
        with open(JSON_KEY_FILE, 'r') as f:
            json_data = json.load(f)
        
        # Convert to single-line JSON string
        json_string = json.dumps(json_data)
        
        print(f"✅ JSON file is valid")
        print(f"   Service Account: {json_data.get('client_email', 'unknown')}")
        print(f"   Project ID: {json_data.get('project_id', 'unknown')}")
        print()
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON file: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading JSON file: {e}")
        return False
    
    # Read existing .env file
    env_path = Path(ENV_FILE)
    env_lines = []
    if env_path.exists():
        with open(env_path, 'r') as f:
            env_lines = f.readlines()
        print(f"✅ Found existing .env file")
    else:
        print(f"⚠️  .env file not found, will create new one")
    
    # Remove existing Google Drive entries
    new_lines = []
    skip_next = False
    for line in env_lines:
        stripped = line.strip()
        # Skip lines that start with Google Drive config
        if stripped.startswith('GOOGLE_SERVICE_ACCOUNT') or \
           stripped.startswith('GOOGLE_DRIVE_FOLDER_ID') or \
           stripped.startswith('# Google Drive'):
            continue
        # Skip empty lines after Google Drive section
        if stripped == '' and skip_next:
            skip_next = False
            continue
        new_lines.append(line)
    
    # Add Google Drive configuration
    new_lines.append('\n')
    new_lines.append('# Google Drive Configuration\n')
    new_lines.append(f"GOOGLE_SERVICE_ACCOUNT_JSON='{json_string}'\n")
    new_lines.append(f"GOOGLE_DRIVE_FOLDER_ID='{FOLDER_ID}'\n")
    
    # Write back to .env
    try:
        with open(env_path, 'w') as f:
            f.writelines(new_lines)
        print(f"✅ Added Google Drive credentials to .env file")
        print()
        print("Configuration added:")
        print(f"   GOOGLE_SERVICE_ACCOUNT_JSON='...' (JSON content)")
        print(f"   GOOGLE_DRIVE_FOLDER_ID='{FOLDER_ID}'")
        print()
        print("🎉 Google Drive credentials saved!")
        print()
        print("Next step: Share the folder with the service account:")
        print(f"   Email: {json_data.get('client_email', 'service account email')}")
        print("   See: SHARE_FOLDER_INSTRUCTIONS.md")
        return True
        
    except Exception as e:
        print(f"❌ Error writing to .env file: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
