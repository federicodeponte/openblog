# How to Share Google Drive Folder with Service Account

## Step-by-Step Instructions

### 1. Get Your Service Account Email

The service account email can be found in your service account JSON file. Look for the `client_email` field:

```bash
cat your-service-account.json | jq -r '.client_email'
```

Or if you have it set in your `.env` file:
```bash
python3 -c "import os; from dotenv import load_dotenv; load_dotenv(); import json; print(json.loads(os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON', '{}')).get('client_email', ''))"
```

### 2. Open Your Google Drive Folder

Open the folder you want to share in Google Drive.

### 3. Share with Service Account

1. **Click the "Share" button** (top right of the folder)
2. **In the "Add people and groups" field**, paste your service account email (from step 1):
   ```
   your-service-account@project-id.iam.gserviceaccount.com
   ```
3. **Set permission to "Editor"** (or "Viewer" if read-only is sufficient)
4. **Uncheck "Notify people"** (service accounts don't have email)
5. **Click "Share"**

### 3. Verify Access

After sharing, run this command to verify:

```bash
source venv/bin/activate
python3 test_google_drive.py
```

You should see:
- ✅ Folder access successful!
- ✅ Folder Name: OpenBlog
- ✅ Found X file(s) in folder

## Important Notes

- **Service accounts don't receive email notifications** - that's normal
- The service account email looks like a regular email but it's a service account
- You may need to wait a few seconds after sharing for access to propagate
- If you see "This email address doesn't exist" - ignore it, service accounts work differently

## Alternative: Share via Folder Settings

If the Share button doesn't work:

1. Right-click the folder → **Share** → **Share**
2. Click **"Change to anyone with the link"** (if you want public access)
   OR
3. Add the service account email directly in the share dialog

## Troubleshooting

If access still fails after sharing:

1. **Check folder permissions**: Make sure the folder isn't restricted by organization policies
2. **Verify service account**: Ensure the service account is active in Google Cloud Console
3. **Check Drive API**: Verify Drive API is enabled for the project
4. **Wait a moment**: Sometimes it takes 10-30 seconds for permissions to propagate

## Test Command

```bash
cd /path/to/openblog  # Change to your project directory
source venv/bin/activate
python3 test_google_drive.py
```
