from langchain.tools import tool
import base64
import email
from email.mime.text import MIMEText
from googleapiclient.http import MediaIoBaseUpload
from tools.utils import get_gmail_service, get_drive_service
import io
import re
import html
import binascii

# --- Robust Helper Functions ---

def safe_clean_decode(data_str: str) -> str:
    """
    Bulletproof decoder for Gmail data. 
    Fixes padding, replaces URL characters, and tries multiple encodings.
    """
    if not data_str: return ""
    
    # 1. Fix Padding (Crucial for preventing crashes)
    padding = len(data_str) % 4
    if padding:
        data_str += '=' * (4 - padding)
    
    # 2. Fix URL characters
    data_str = data_str.replace('-', '+').replace('_', '/')
        
    try:
        decoded_bytes = base64.b64decode(data_str)
        return decoded_bytes.decode('utf-8', errors='ignore')
    except Exception:
        return ""

def clean_html_content(text: str) -> str:
    """Removes HTML tags to reveal the actual text."""
    if not text: return ""
    text = html.unescape(text)
    text = re.sub(r'<style.*?>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<script.*?>.*?</script>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^<]+?>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_all_text(payload):
    """
    Recursively finds ALL text in an email (plain and html).
    """
    text_candidates = []
    
    parts = payload.get('parts', [])
    body_data = payload.get('body', {}).get('data')
    mime_type = payload.get('mimeType', '')

    if body_data and mime_type in ['text/plain', 'text/html']:
        decoded = safe_clean_decode(body_data)
        if decoded:
            if mime_type == 'text/html':
                decoded = clean_html_content(decoded)
            if len(decoded.strip()) > 5: 
                text_candidates.append(decoded)

    for part in parts:
        text_candidates.extend(extract_all_text(part))
        
    return text_candidates

# --- SMART TOOLS ---

@tool
def create_gmail_draft(to_recipients: str, subject: str, body: str) -> str:
    """Creates a draft email in the user's Gmail account."""
    try:
        service = get_gmail_service()
        message = MIMEText(body)
        message['to'] = to_recipients
        message['subject'] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        draft = service.users().drafts().create(userId='me', body={'message': {'raw': raw}}).execute()
        return f"Success: Draft created (ID: {draft['id']})."
    except Exception as e:
        return f"Error: {e}"

@tool
def read_recent_emails(limit: int = 5) -> str:
    """Returns a summary (Sender, Subject) of the recent emails."""
    try:
        service = get_gmail_service()
        results = service.users().messages().list(userId='me', maxResults=limit, labelIds=['INBOX']).execute()
        messages = results.get('messages', [])
        if not messages: return "No recent emails."

        summary = []
        for msg in messages:
            m = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
            headers = m['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(No Subject)')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), '(Unknown)')
            summary.append(f"ID: {msg['id']} | From: {sender} | Subj: {subject}")
        return "\n".join(summary)
    except Exception as e:
        return f"Error: {e}"

@tool
def read_email_content(query_or_id: str) -> str:
    """
    SMART READER: Reads an email's content.
    You can pass an Email ID OR a search query (e.g., "from Uday", "subject:Testing").
    If a query is passed, it finds the most recent match and reads it.
    """
    service = get_gmail_service()
    msg_id = query_or_id

    # 1. Determine if input is an ID or a Query
    # IDs are usually long hex strings; queries have spaces or colons.
    # If it looks like a query, search for the ID first.
    if " " in query_or_id or ":" in query_or_id or len(query_or_id) < 10:
        print(f"DEBUG: Input '{query_or_id}' looks like a query. Searching...")
        results = service.users().messages().list(userId='me', q=query_or_id, maxResults=1).execute()
        messages = results.get('messages', [])
        if not messages:
            return f"Error: No email found matching '{query_or_id}'"
        msg_id = messages[0]['id']
        print(f"DEBUG: Found ID {msg_id}")

    # 2. Read the email
    try:
        message = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
        payload = message.get('payload', {})
        candidates = extract_all_text(payload)
        
        # Fallback for flat emails
        if not candidates:
            data = payload.get('body', {}).get('data')
            if data:
                decoded = safe_clean_decode(data)
                if decoded: candidates.append(decoded)

        if not candidates:
            return "Email content is empty or only contains images."
            
        # Return the longest text block found
        candidates.sort(key=len, reverse=True)
        return candidates[0]

    except Exception as e:
        return f"Error reading email (ID: {msg_id}): {e}"

@tool
def save_email_attachment(email_query: str, attachment_name: str, drive_folder_name: str = None) -> str:
    """Saves an email attachment to Google Drive."""
    try:
        service = get_gmail_service()
        drive = get_drive_service()
        
        res = service.users().messages().list(userId='me', q=email_query, maxResults=1).execute()
        msgs = res.get('messages', [])
        if not msgs: return f"No email found for '{email_query}'"
        
        msg_id = msgs[0]['id']
        message = service.users().messages().get(userId='me', id=msg_id).execute()
        
        att_id = None
        def find_att(parts):
            for p in parts:
                if p.get('filename') == attachment_name: return p['body'].get('attachmentId')
                if 'parts' in p: 
                    found = find_att(p['parts'])
                    if found: return found
            return None

        att_id = find_att(message.get('payload', {}).get('parts', []))
        if not att_id: return f"Attachment '{attachment_name}' not found."
            
        att = service.users().messages().attachments().get(userId='me', messageId=msg_id, id=att_id).execute()
        data = base64.urlsafe_b64decode(att['data'])
        
        meta = {'name': attachment_name}
        if drive_folder_name:
            q = f"name = '{drive_folder_name}' and mimeType = 'application/vnd.google-apps.folder'"
            folders = drive.files().list(q=q).execute().get('files', [])
            if folders: meta['parents'] = [folders[0]['id']]
        
        media = MediaIoBaseUpload(io.BytesIO(data), mimetype='application/octet-stream')
        f = drive.files().create(body=meta, media_body=media).execute()
        return f"Saved to Drive (ID: {f.get('id')})"
    except Exception as e:
        return f"Error: {e}"
