#!/bin/bash
# Script to add Google Drive credentials to .env file
# 
# WARNING: This script requires you to provide the service account JSON file path
# Usage: ./add_google_drive_credentials.sh <path-to-service-account.json> <folder-id>
#
# Example:
#   ./add_google_drive_credentials.sh /path/to/service-account.json 1A9V17wiJObowwrGd9TmEhwCANNeoa1Zd

ENV_FILE=".env"

if [ $# -lt 2 ]; then
    echo "❌ Error: Missing required arguments"
    echo ""
    echo "Usage: $0 <path-to-service-account.json> <folder-id>"
    echo ""
    echo "Example:"
    echo "  $0 /path/to/service-account.json 1A9V17wiJObowwrGd9TmEhwCANNeoa1Zd"
    exit 1
fi

JSON_KEY_FILE="$1"
FOLDER_ID="$2"

if [ ! -f "$JSON_KEY_FILE" ]; then
    echo "❌ Error: JSON key file not found: $JSON_KEY_FILE"
    exit 1
fi

# Read and validate JSON file
SERVICE_ACCOUNT_JSON=$(cat "$JSON_KEY_FILE" | jq -c . 2>/dev/null)
if [ $? -ne 0 ]; then
    echo "❌ Error: Invalid JSON file or jq not installed"
    echo "   Install jq: brew install jq (macOS) or apt-get install jq (Linux)"
    exit 1
fi

echo "Adding Google Drive credentials to .env file..."

# Remove existing entries if they exist
sed -i.bak '/^GOOGLE_SERVICE_ACCOUNT_JSON=/d' "$ENV_FILE"
sed -i.bak '/^GOOGLE_DRIVE_FOLDER_ID=/d' "$ENV_FILE"

# Add new entries
echo "" >> "$ENV_FILE"
echo "# Google Drive Configuration" >> "$ENV_FILE"
echo "GOOGLE_SERVICE_ACCOUNT_JSON='$SERVICE_ACCOUNT_JSON'" >> "$ENV_FILE"
echo "GOOGLE_DRIVE_FOLDER_ID='$FOLDER_ID'" >> "$ENV_FILE"

# Extract client email for sharing instructions
CLIENT_EMAIL=$(echo "$SERVICE_ACCOUNT_JSON" | jq -r '.client_email')

echo "✅ Credentials added to .env file"
echo ""
echo "Next steps:"
echo "1. Share the Google Drive folder with: $CLIENT_EMAIL"
echo "2. Run: python3 test_google_drive.py to verify"
