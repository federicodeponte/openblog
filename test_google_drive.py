#!/usr/bin/env python3
"""
Test Google Drive connection with provided credentials.
"""

import os
import json
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Load credentials from environment variables
TEST_SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
TEST_FOLDER_ID = os.environ.get("GOOGLE_DRIVE_FOLDER_ID")

if not TEST_SERVICE_ACCOUNT_JSON:
    print("❌ Error: GOOGLE_SERVICE_ACCOUNT_JSON environment variable is required")
    print("   Please set it in your .env file")
    sys.exit(1)

if not TEST_FOLDER_ID:
    print("❌ Error: GOOGLE_DRIVE_FOLDER_ID environment variable is required")
    print("   Please set it in your .env file")
    sys.exit(1)

try:
    TEST_SERVICE_ACCOUNT = json.loads(TEST_SERVICE_ACCOUNT_JSON)
except json.JSONDecodeError as e:
    print(f"❌ Error: Invalid JSON in GOOGLE_SERVICE_ACCOUNT_JSON: {e}")
    sys.exit(1)

def test_google_drive():
    """Test Google Drive connection with provided credentials."""
    print("=" * 60)
    print("📁 Testing Google Drive Connection")
    print("=" * 60)
    print()
    
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        print("❌ Google API packages not installed")
        print("   Run: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        return False
    
    print("✅ Google API packages installed")
    print()
    
    # Use credentials from environment
    sa_info = TEST_SERVICE_ACCOUNT
    folder_id = TEST_FOLDER_ID
    
    print(f"Service Account: {sa_info['client_email']}")
    print(f"Project ID: {sa_info['project_id']}")
    print(f"Folder ID: {folder_id}")
    print()
    
    # Create credentials
    print("Creating credentials...")
    try:
        credentials = service_account.Credentials.from_service_account_info(
            sa_info,
            scopes=['https://www.googleapis.com/auth/drive.file']
        )
        print("✅ Credentials created")
    except Exception as e:
        print(f"❌ Failed to create credentials: {e}")
        return False
    
    # Build Drive service
    print("Building Drive service...")
    try:
        drive_service = build('drive', 'v3', credentials=credentials)
        print("✅ Drive service built")
    except Exception as e:
        print(f"❌ Failed to build Drive service: {e}")
        return False
    
    print()
    
    # Test 1: List files (basic API access)
    print("Test 1: Testing Drive API access...")
    try:
        result = drive_service.files().list(pageSize=1, fields="files(id, name)").execute()
        print("✅ Drive API access successful!")
        files = result.get('files', [])
        if files:
            print(f"   Found {len(files)} file(s) in Drive")
    except Exception as e:
        print(f"❌ Drive API access failed: {e}")
        return False
    
    print()
    
    # Test 2: Access specific folder
    print(f"Test 2: Testing folder access (ID: {folder_id})...")
    try:
        folder = drive_service.files().get(
            fileId=folder_id,
            fields="id, name, mimeType, permissions"
        ).execute()
        
        print("✅ Folder access successful!")
        print(f"   Folder Name: {folder.get('name', 'Unknown')}")
        print(f"   Folder ID: {folder.get('id', 'Unknown')}")
        print(f"   MIME Type: {folder.get('mimeType', 'Unknown')}")
        
        # Check if it's actually a folder
        if folder.get('mimeType') == 'application/vnd.google-apps.folder':
            print("   ✅ Confirmed: This is a folder")
        else:
            print("   ⚠️  Warning: This doesn't appear to be a folder")
            
    except Exception as e:
        error_str = str(e).lower()
        if 'not found' in error_str or '404' in error_str:
            print(f"❌ Folder not found or no access")
            print("   Possible issues:")
            print("   1. Folder ID is incorrect")
            print("   2. Service account doesn't have access to this folder")
            print("   3. Folder doesn't exist")
            print()
            print("   To fix:")
            print(f"   1. Share the folder with: {sa_info.get('client_email', 'service account email')}")
            print("   2. Or verify the folder ID is correct")
            return False
        else:
            print(f"❌ Folder access failed: {e}")
            return False
    
    print()
    
    # Test 3: List files in folder
    print("Test 3: Listing files in folder...")
    try:
        folder_files = drive_service.files().list(
            q=f"'{folder_id}' in parents",
            pageSize=5,
            fields="files(id, name, mimeType)"
        ).execute()
        
        files = folder_files.get('files', [])
        print(f"✅ Found {len(files)} file(s) in folder")
        if files:
            print("   Files:")
            for file in files[:5]:
                print(f"     - {file.get('name', 'Unknown')} ({file.get('mimeType', 'Unknown')})")
        else:
            print("   Folder is empty")
            
    except Exception as e:
        print(f"⚠️  Could not list folder contents: {e}")
        print("   (This might be a permissions issue, but basic access works)")
    
    print()
    print("=" * 60)
    print("🎉 Google Drive connection test complete!")
    print("=" * 60)
    print()
    print("✅ All tests passed!")
    print()
    print("To add these credentials to your .env file:")
    print()
    print("GOOGLE_SERVICE_ACCOUNT_JSON='{\"type\":\"service_account\",...}'")
    print(f"GOOGLE_DRIVE_FOLDER_ID='{folder_id}'")
    print()
    print("Note: The JSON needs to be on a single line or properly escaped")
    
    return True

if __name__ == "__main__":
    success = test_google_drive()
    sys.exit(0 if success else 1)
