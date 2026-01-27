from langchain.tools import tool
from tools.utils import get_docs_service, get_drive_service

@tool
def create_new_doc(title: str, text_content: str = "") -> str:
    """Creates a new Google Doc with the given title and optional initial text content.
    Returns the URL of the new document.
    """
    docs_service = get_docs_service()
    drive_service = get_drive_service() # Needed if we want to move it or just trust it goes to root

    # 1. Create the blank doc
    doc = docs_service.documents().create(body={'title': title}).execute()
    document_id = doc.get('documentId')
    
    # 2. Insert content if provided
    if text_content:
        requests = [
            {
                'insertText': {
                    'location': {
                        'index': 1,
                    },
                    'text': text_content
                }
            }
        ]
        docs_service.documents().batchUpdate(documentId=document_id, body={'requests': requests}).execute()

    return f"Document created successfully: https://docs.google.com/document/d/{document_id}"

@tool
def read_doc_content(title_query: str) -> str:
    """Searches for a document by title, and reads its content. 
    If multiple found, reads the first one.
    """
    drive_service = get_drive_service()
    docs_service = get_docs_service()
    
    # Search for the file ID by name
    query = f"name contains '{title_query}' and mimeType = 'application/vnd.google-apps.document' and trashed = false"
    start_page_token = None
    
    results = drive_service.files().list(
        q=query, spaces='drive', fields='files(id, name)', pageToken=start_page_token
    ).execute()
    files = results.get('files', [])

    if not files:
        return f"No document found with title matching '{title_query}'."

    # Just take the first one
    file_id = files[0]['id']
    file_name = files[0]['name']

    doc_content = docs_service.documents().get(documentId=file_id).execute()
    
    # Simple extraction of text
    full_text = []
    content = doc_content.get('body').get('content')
    for elem in content:
        if 'paragraph' in elem:
            elements = elem.get('paragraph').get('elements')
            for e in elements:
                if 'textRun' in e:
                    full_text.append(e.get('textRun').get('content'))
    
    text = "".join(full_text)
    return f"Content of '{file_name}':\n{text}"
