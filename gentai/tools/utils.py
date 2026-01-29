from googleapiclient.discovery import build
from auth import authenticate_google_services_local

_creds = None

def get_credentials():
    global _creds
    if not _creds:
        _creds = authenticate_google_services_local()
    return _creds

def get_gmail_service():
    return build('gmail', 'v1', credentials=get_credentials())

def get_docs_service():
    return build('docs', 'v1', credentials=get_credentials())

def get_drive_service():
    return build('drive', 'v3', credentials=get_credentials())

def get_calendar_service():
    return build('calendar', 'v3', credentials=get_credentials())

def get_youtube_service():
    return build('youtube', 'v3', credentials=get_credentials())
