#!/usr/bin/env python3
"""
Debug Google Drive folder access issues.
"""

import os
import json
import sys
from dotenv import load_dotenv

load_dotenv()

FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

# Get service account email from JSON if available
SERVICE_ACCOUNT_EMAIL = None
if SERVICE_ACCOUNT_JSON:
    try:
        sa_data = json.loads(SERVICE_ACCOUNT_JSON)
        SERVICE_ACCOUNT_EMAIL = sa_data.get("client_email")
    except (json.JSONDecodeError, AttributeError):
        pass

if not FOLDER_ID:
    print("❌ Error: GOOGLE_DRIVE_FOLDER_ID environment variable is required")
    sys.exit(1)

if not SERVICE_ACCOUNT_EMAIL:
    print("❌ Error: Could not extract service account email from GOOGLE_SERVICE_ACCOUNT_JSON")
    sys.exit(1)

def debug_drive_access():
    """Debug Google Drive folder access."""
    print("=" * 60)
    print("🔍 Debugging Google Drive Folder Access")
    print("=" * 60)
    print()
    
    # Get credentials
    sa_json = (
        os.getenv("GOOGLE_SERVICE_ACCOUNT") or
        os.getenv("SERVICE_ACCOUNT_JSON") or
        os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON") or
        os.getenv("GOOGLE_CREDENTIALS")
    )
    
    if not sa_json:
        print("❌ Service account JSON not found in environment")
        return False
    
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
    except ImportError:
        print("❌ Google API packages not installed")
        return False
    
    # Parse JSON
    try:
        if isinstance(sa_json, str):
            sa_info = json.loads(sa_json)
        else:
            sa_info = sa_json
    except Exception as e:
        print(f"❌ Error parsing JSON: {e}")
        return False
    
    print(f"Service Account: {sa_info.get('client_email', 'unknown')}")
    print(f"Folder ID: {FOLDER_ID}")
    print()
    
    # Create credentials with full Drive scope
    try:
        # Use full Drive scope to ensure we can access shared folders
        credentials = service_account.Credentials.from_service_account_info(
            sa_info,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        drive_service = build('drive', 'v3', credentials=credentials)
        print("✅ Drive service created with full Drive scope")
    except Exception as e:
        print(f"❌ Failed to create Drive service: {e}")
        return False
    
    print()
    
    # Test 1: Try to get folder metadata
    print("Test 1: Getting folder metadata...")
    folder_found = False
    try:
        folder = drive_service.files().get(
            fileId=FOLDER_ID,
            fields="id, name, mimeType, permissions, shared, owners"
        ).execute()
        
        print("✅ Folder found!")
        folder_found = True
        print(f"   Name: {folder.get('name', 'Unknown')}")
        print(f"   ID: {folder.get('id', 'Unknown')}")
        print(f"   MIME Type: {folder.get('mimeType', 'Unknown')}")
        print(f"   Shared: {folder.get('shared', False)}")
        
        # Check permissions
        permissions = folder.get('permissions', [])
        print(f"   Permissions: {len(permissions)} found")
        
        # Check if service account has access
        sa_has_access = False
        for perm in permissions:
            email = perm.get('emailAddress', '')
            role = perm.get('role', '')
            if SERVICE_ACCOUNT_EMAIL.lower() in email.lower():
                sa_has_access = True
                print(f"   ✅ Service account found in permissions: {role}")
                break
        
        if not sa_has_access:
            print(f"   ⚠️  Service account NOT found in permissions list")
            print(f"   Current permissions:")
            for perm in permissions[:5]:  # Show first 5
                email = perm.get('emailAddress', perm.get('displayName', 'Unknown'))
                role = perm.get('role', 'unknown')
                print(f"     - {email}: {role}")
        
    except HttpError as e:
        folder_found = False
        
    except HttpError as e:
        error_details = json.loads(e.content.decode('utf-8'))
        error_reason = error_details.get('error', {}).get('errors', [{}])[0].get('reason', 'unknown')
        error_message = error_details.get('error', {}).get('message', str(e))
        
        print(f"❌ Error accessing folder: {error_message}")
        print(f"   Error reason: {error_reason}")
        
        if error_reason == 'notFound':
            print()
            print("Possible causes:")
            print("  1. Folder ID is incorrect")
            print("  2. Folder doesn't exist")
            print("  3. Folder was deleted")
        elif error_reason == 'insufficientPermissions' or 'permissionDenied' in error_reason.lower():
            print()
            print("Possible causes:")
            print("  1. Service account doesn't have access")
            print(f"  2. Folder not shared with: {SERVICE_ACCOUNT_EMAIL}")
            print("  3. Permissions haven't propagated yet (wait 1-2 minutes)")
            print("  4. Organization policies blocking access")
            print()
            print("To fix:")
            print(f"  1. Open: https://drive.google.com/drive/folders/{FOLDER_ID}")
            print(f"  2. Click Share")
            print(f"  3. Add: {SERVICE_ACCOUNT_EMAIL}")
            print(f"  4. Set permission to 'Editor'")
            print(f"  5. Wait 1-2 minutes for permissions to propagate")
        else:
            print(f"   Unexpected error reason: {error_reason}")
        
        print("   (Continuing with other tests...)")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        print("   (Continuing with other tests...)")
    
    print()
    
    # Test 1.5: List all accessible folders to see what the service account can see
    print("Test 1.5: Listing all accessible folders...")
    try:
        all_folders = drive_service.files().list(
            q="mimeType='application/vnd.google-apps.folder'",
            pageSize=10,
            fields="files(id, name, shared)"
        ).execute()
        
        folders = all_folders.get('files', [])
        if folders:
            print(f"✅ Service account can see {len(folders)} folder(s):")
            for folder in folders:
                folder_id = folder.get('id', '')
                folder_name = folder.get('name', 'Unknown')
                is_shared = folder.get('shared', False)
                match = "✅ MATCH!" if folder_id == FOLDER_ID else ""
                print(f"   - {folder_name} (ID: {folder_id}, Shared: {is_shared}) {match}")
        else:
            print("   ⚠️  Service account cannot see any folders")
            print("   This suggests the service account has no shared folders")
    except Exception as e:
        print(f"   ⚠️  Could not list folders: {e}")
    
    print()
    
    # Test 1.6: Try searching for the folder by name
    print("Test 1.5: Searching for folder by name 'OpenBlog'...")
    try:
        search_results = drive_service.files().list(
            q="name='OpenBlog' and mimeType='application/vnd.google-apps.folder'",
            fields="files(id, name, shared, permissions)"
        ).execute()
        
        folders = search_results.get('files', [])
        if folders:
            print(f"✅ Found {len(folders)} folder(s) named 'OpenBlog'")
            for folder in folders:
                print(f"   - ID: {folder.get('id')}, Name: {folder.get('name')}, Shared: {folder.get('shared', False)}")
                if folder.get('id') == FOLDER_ID:
                    print(f"   ✅ This matches the target folder ID!")
        else:
            print("   ⚠️  No folders named 'OpenBlog' found")
    except Exception as e:
        print(f"   ⚠️  Search failed: {e}")
    
    print()
    
    # Test 2: Try to list files in folder
    print("Test 2: Listing files in folder...")
    try:
        files = drive_service.files().list(
            q=f"'{FOLDER_ID}' in parents",
            pageSize=5,
            fields="files(id, name, mimeType)"
        ).execute()
        
        file_list = files.get('files', [])
        print(f"✅ Found {len(file_list)} file(s) in folder")
        if file_list:
            for file in file_list:
                print(f"   - {file.get('name', 'Unknown')}")
        else:
            print("   Folder is empty")
        
        return True
        
    except Exception as e:
        print(f"⚠️  Could not list folder contents: {e}")
        print("   (This might be a permissions issue)")
    
    print()
    print("=" * 60)
    print("📋 Summary & Recommendations")
    print("=" * 60)
    print()
    
    if not folder_found:
        print("❌ Folder access failed. Try these steps:")
        print()
        print("1. Verify the folder ID is correct:")
        print(f"   URL: https://drive.google.com/drive/folders/{FOLDER_ID}")
        print()
        print("2. Share the folder again with the service account:")
        print(f"   Email: {SERVICE_ACCOUNT_EMAIL}")
        print("   Steps:")
        print("   a. Open the folder in Google Drive")
        print("   b. Click 'Share' button")
        print("   c. Paste the service account email")
        print("   d. Set permission to 'Editor'")
        print("   e. UNCHECK 'Notify people'")
        print("   f. Click 'Share'")
        print()
        print("3. Wait 2-3 minutes for permissions to propagate")
        print()
        print("4. Verify sharing worked:")
        print("   - In the folder, click 'Share' again")
        print("   - Check if the service account appears in the list")
        print()
        print("5. If still not working, try:")
        print("   - Make the folder 'Anyone with the link can view' temporarily")
        print("   - Or check if your organization has sharing restrictions")
        
    return folder_found

if __name__ == "__main__":
    success = debug_drive_access()
    sys.exit(0 if success else 1)
