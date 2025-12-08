# Google Drive Setup Instructions

## Test Results

✅ **Service Account Credentials**: Valid and working
✅ **Drive API Access**: Successfully connected
❌ **Folder Access**: Needs to be shared with service account

## Required Actions

### 1. Share the Google Drive Folder

The folder needs to be shared with the service account.

**Steps**:
1. Open your Google Drive folder
2. Click the **"Share"** button (top right)
3. Get your service account email from the JSON file (`client_email` field) or environment variable
4. In the "Add people and groups" field, paste the service account email:
   ```
   your-service-account@project-id.iam.gserviceaccount.com
   ```
5. Set permission to **"Editor"** (or "Viewer" if read-only is sufficient)
6. **Uncheck "Notify people"** (service accounts don't have email)
7. Click **"Share"**

**Note**: You may see "This email address doesn't exist" - that's normal for service accounts. The sharing will still work.

### 2. Add Credentials to .env File

Add these lines to your `.env` file:

```bash
# Google Drive Configuration
GOOGLE_SERVICE_ACCOUNT_JSON='<paste your service account JSON here as a single line>'
GOOGLE_DRIVE_FOLDER_ID='<your-folder-id-here>'
```

**How to get the service account JSON:**
1. Download the service account key file from Google Cloud Console
2. Convert it to a single-line JSON string:
   ```bash
   cat path/to/service-account.json | jq -c .
   ```
3. Or use the helper script:
   ```bash
   python3 add_google_drive_to_env.py path/to/service-account.json <folder-id>
   ```

### 3. Verify Connection

After sharing the folder and adding credentials, run:

```bash
source venv/bin/activate
python3 test_google_drive.py
```

Or test both connections:

```bash
python3 test_connections.py
```

## Service Account Details

After setting up your service account in Google Cloud Console, you'll need:
- **Service Account Email**: Found in your service account JSON file (client_email field)
- **Project ID**: Found in your service account JSON file (project_id field)
- **Folder ID**: The ID of the Google Drive folder you want to use

## Current Status

- ✅ Supabase: **Connected and ready**
- ⚠️ Google Drive: **Credentials valid, but folder needs to be shared**

Once the folder is shared, Google Drive will be fully functional for:
- Image uploads
- Graphics storage
- Document creation
- File management
