import base64
from typing import List, Optional
from langchain.tools import tool
from tools.utils import get_gmail_service

@tool
def get_recent_emails(max_results: int = 10) -> str:
    """Retrieves the latest emails from the user's Primary inbox (both Read and Unread).
    Returns a formatted string with status, sender, subject, and snippet.
    """
    service = get_gmail_service()
    # Query for Primary category, no 'is:unread' filter so we get everything
    results = service.users().messages().list(userId='me', q='category:primary', maxResults=max_results).execute()
    print(f"DEBUG: Gmail API Raw Response: {results}")
    messages = results.get('messages', [])

    if not messages:
        return "No recent messages found in Primary inbox."

    output = []
    for msg in messages:
        msg_detail = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        headers = msg_detail['payload']['headers']
        label_ids = msg_detail.get('labelIds', [])
        
        # Determine status
        status = "Unread" if 'UNREAD' in label_ids else "Read"
        
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
        snippet = msg_detail.get('snippet', '')
        output.append(f"Status: {status}\nFrom: {sender}\nSubject: {subject}\nSnippet: {snippet}\n---")

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
    from email.mime.multipart import MIMEMultipart
    import base64
    
    # Create a multipart message
    message = MIMEMultipart("alternative")
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject

    # Create plain text version (strip HTML tags broadly for simple fallback)
    # Ideally use a library like BeautifulSoup, but for simplicity here we just send content.
    # A better approach for plain text is to let the user see the raw text if they can't render HTML,
    # OR we just duplicate the content. 
    # Let's clean basic tags for the plain text part manually or just send as is?
    # Sending raw HTML as plain text is ugly. Let's just assume simple HTML text.
    # The 'message_text' input is likely HTML from the bot.
    
    # We'll attach both, assuming the client picks the best one.
    part1 = MIMEText(message_text, 'plain') 
    part2 = MIMEText(message_text, 'html')

    # Attach parts into message container.
    # According to RFC 2046, the last part of a multipart message, in this case
    # the HTML message, is best and preferred.
    message.attach(part1)
    message.attach(part2)

    raw = base64.urlsafe_b64encode(message.as_bytes())
    return {'raw': raw.decode()}
