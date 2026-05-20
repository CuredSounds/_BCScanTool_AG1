import os
import io
import json
import zipfile
from datetime import datetime
from pathlib import Path
import sys

# Ensure src can be imported
from src import config

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    GDRIVE_AVAILABLE = True
except ImportError:
    GDRIVE_AVAILABLE = False

SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDENTIALS_FILE = config.PROJECT_ROOT / 'credentials.json'
TOKEN_FILE = config.PROJECT_ROOT / 'token.json'

def authenticate_gdrive():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError("credentials.json not found! Please follow the instructions to download it from Google Cloud Console and place it in the project root.")
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)

def backup_to_cloud():
    if not GDRIVE_AVAILABLE:
        return {"status": "error", "message": "Missing Google API libraries. Please run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"}
        
    try:
        service = authenticate_gdrive()
        
        # 1. Zip the DB and processed data
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_filename = f"BCScanTool_Backup_{timestamp}.zip"
        zip_filepath = config.PROJECT_ROOT / zip_filename
        
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
            db_file = config.DATA_DIR / 'diagnostics.db'
            if db_file.exists():
                zipf.write(db_file, arcname='diagnostics.db')
                
            processed_dir = config.DATA_DIR / 'processed'
            if processed_dir.exists():
                for root, _, files in os.walk(processed_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        zipf.write(file_path, arcname=f"processed/{file}")
        
        # 2. Upload to Drive
        file_metadata = {'name': zip_filename, 'mimeType': 'application/zip'}
        media = MediaFileUpload(str(zip_filepath), mimetype='application/zip', resumable=True)
        
        uploaded_file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        
        # Clean up local zip
        if zip_filepath.exists():
            os.remove(zip_filepath)
            
        return {"status": "success", "message": f"Backup uploaded successfully to Google Drive! File ID: {uploaded_file.get('id')}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == '__main__':
    result = backup_to_cloud()
    print(result)
