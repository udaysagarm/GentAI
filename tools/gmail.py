import base64
from typing import List, Optional
from langchain.tools import tool
from tools.utils import get_gmail_service

@tool
def get_unread_emails(max_results: int = 10) -> str:
    """Retrieves the latest unread emails from the user's inbox.
    Returns a formatted string with sender, subject, and snippet.
    """
    service = get_gmail_service()
    results = service.users().messages().list(userId='me', q='is:unread', maxResults=max_results).execute()
    messages = results.get('messages', [])

    if not messages:
        return "No unread messages found."

    output = []
    for msg in messages:
        msg_detail = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        headers = msg_detail['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
        snippet = msg_detail.get('snippet', '')
        output.append(f"From: {sender}\nSubject: {subject}\nSnippet: {snippet}\n---")

    return "\n".join(output)

@tool
def search_emails(query: str, max_results: int = 5) -> str:
    """Searches for emails matching the given query string (e.g., 'from:alice', 'subject:invoice')."""
    service = get_gmail_service()
    results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
    messages = results.get('messages', [])

    if not messages:
        return f"No messages found satisfying query: {query}"

    output = []
    for msg in messages:
        msg_detail = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        headers = msg_detail['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
        snippet = msg_detail.get('snippet', '')
        output.append(f"From: {sender}\nSubject: {subject}\nSnippet: {snippet}\n---")

    return "\n".join(output)

@tool
def send_email(to: str, subject: str, message_text: str) -> str:
    """Sends an email to the specified recipient."""
    service = get_gmail_service()
    print(f"DEBUG: Attempting to send email to {to} with subject '{subject}'...")
    message = create_message('me', to, subject, message_text)
    sent_message = service.users().messages().send(userId='me', body=message).execute()
    print(f"DEBUG: Email sent successfully! ID: {sent_message['id']}")
    return f"Email sent successfully! Id: {sent_message['id']}"

def create_message(sender, to, subject, message_text):
    """Create a message for an email."""
    from email.mime.text import MIMEText
    import base64
    
    message = MIMEText(message_text)
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes())
    return {'raw': raw.decode()}
