import io
import pypdf
from googleapiclient.http import MediaFileUpload
from langchain.tools import tool
from tools.utils import get_docs_service, get_drive_service

def get_doc_id(doc_name: str):
    """Helper: Finds a Google Doc ID by name."""
    drive_service = get_drive_service()
    query = f"name = '{doc_name}' and mimeType = 'application/vnd.google-apps.document' and trashed = false"
    
    results = drive_service.files().list(
        q=query, spaces='drive', fields='files(id, name)'
    ).execute()
    files = results.get('files', [])
    
    if not files:
        return None
    return files[0]['id']

def get_folder_id(folder_name: str):
    """Helper: Finds a Google Drive Folder ID by name."""
    drive_service = get_drive_service()
    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    
    results = drive_service.files().list(
        q=query, spaces='drive', fields='files(id, name)'
    ).execute()
    files = results.get('files', [])
    
    if not files:
        return None
    return files[0]['id']

@tool
def read_document(doc_name: str) -> str:
    """Reads a Google Doc by name and returns its plain text content."""
    doc_id = get_doc_id(doc_name)
    if not doc_id:
        return f"Error: Document '{doc_name}' not found."
    
    try:
        docs_service = get_docs_service()
        doc = docs_service.documents().get(documentId=doc_id).execute()
        
        # Parse content
        full_text = []
        content = doc.get('body').get('content')
        for elem in content:
            if 'paragraph' in elem:
                elements = elem.get('paragraph').get('elements')
                for e in elements:
                    if 'textRun' in e:
                        full_text.append(e.get('textRun').get('content'))
        
        return "".join(full_text)
    except Exception as e:
        return f"Error reading document: {e}"

@tool
def append_to_document(doc_name: str, new_text: str) -> str:
    """Appends text to the end of an existing Google Doc."""
    doc_id = get_doc_id(doc_name)
    if not doc_id:
        return f"Error: Document '{doc_name}' not found."
        
    try:
        docs_service = get_docs_service()
        
        # Get current document end index
        doc = docs_service.documents().get(documentId=doc_id).execute()
        content = doc.get('body').get('content')
        end_index = content[-1].get('endIndex') - 1
        
        requests = [{
            'insertText': {
                'location': {'index': end_index}, 
                'text': "\n" + new_text
            }
        }]
        
        docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
        return f"Successfully appended text to '{doc_name}'."
    except Exception as e:
        return f"Error appending to document: {e}"

@tool
def create_document(doc_name: str, initial_text: str = "", folder_name: str = None) -> str:
    """Creates a new Google Doc with the given title, optional initial text, and optional destination folder."""
    try:
        docs_service = get_docs_service()
        drive_service = get_drive_service()
        
        # Create doc (always in root first)
        doc = docs_service.documents().create(body={'title': doc_name}).execute()
        doc_id = doc.get('documentId')
        
        # Handle folder (Move logic)
        folder_msg = ""
        if folder_name:
            folder_id = get_folder_id(folder_name)
            if folder_id:
                # Move logic: Add new parent, remove existing parents (usually root)
                file = drive_service.files().get(fileId=doc_id, fields='parents').execute()
                previous_parents = ",".join(file.get('parents', []))
                
                drive_service.files().update(
                    fileId=doc_id,
                    addParents=folder_id,
                    removeParents=previous_parents,
                    fields='id, parents'
                ).execute()
                folder_msg = f" in folder '{folder_name}'"
            else:
                folder_msg = f" (Warning: Folder '{folder_name}' not found, created in root)"
        
        # Insert initial text if provided
        if initial_text:
            requests = [{
                'insertText': {
                    'location': {'index': 1}, 
                    'text': initial_text
                }
            }]
            docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
            
        return f"Created new document: {doc_name} (ID: {doc_id}){folder_msg}"
    except Exception as e:
        return f"Error creating document: {e}"

@tool
def overwrite_document(doc_name: str, new_content: str) -> str:
    """Completely rewrites a Google Doc, replacing old content with new content."""
    doc_id = get_doc_id(doc_name)
    if not doc_id:
        return f"Error: Document '{doc_name}' not found."
        
    try:
        docs_service = get_docs_service()
        
        # Get current document metadata to find bounds
        doc = docs_service.documents().get(documentId=doc_id).execute()
        content = doc.get('body').get('content')
        current_end_index = content[-1].get('endIndex')
        
        requests = []
        
        # Step 1: Delete existing content if not empty
        # The document must contain at least one character (the final newline)
        # So if endIndex is 2 (start index 1 + newline), it's effectively empty for our purpose
        if current_end_index > 2:
            requests.append({
                'deleteContentRange': {
                    'range': {
                        'startIndex': 1,
                        'endIndex': current_end_index - 1
                    }
                }
            })
            
        # Step 2: Insert new content at the start
        if new_content:
            requests.append({
                'insertText': {
                    'location': {'index': 1},
                    'text': new_content
                }
            })
        
        if requests:
            docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
            
        return f"Success: Overwrote content of '{doc_name}'."
    except Exception as e:
        return f"Error overwriting document: {e}"

@tool
def delete_document(doc_name: str) -> str:
    """Deletes a Google Doc by name."""
    doc_id = get_doc_id(doc_name)
    if not doc_id:
        return f"Document '{doc_name}' not found."
    
    try:
        drive_service = get_drive_service()
        # Soft delete (move to trash) so it can be restored
        drive_service.files().update(fileId=doc_id, body={'trashed': True}).execute()
        return "Success: Deleted document (moved to trash)."
    except Exception as e:
        return f"Error deleting document: {e}"

@tool
def restore_document(doc_name: str) -> str:
    """Restores a deleted (trashed) Google Doc by name."""
    drive_service = get_drive_service()
    
    # Search specifically for trashed files
    query = f"name = '{doc_name}' and mimeType = 'application/vnd.google-apps.document' and trashed = true"
    print(f"DEBUG: Searching for trash with query: {query}")
    
    # Order by 'modifiedTime desc' to get the most recently deleted one
    results = drive_service.files().list(
        q=query, spaces='drive', fields='files(id, name, trashed)', orderBy='modifiedTime desc'
    ).execute()
    files = results.get('files', [])
    
    if not files:
        return f"Error: No file named '{doc_name}' found in trash."
    
    if len(files) > 1:
        print(f"DEBUG: Found {len(files)} files in trash. Restoring the most recent one (ID: {files[0]['id']}).")
    
    # Pick the most recent one
    doc_id = files[0]['id']
    print(f"DEBUG: Attempting to restore file ID: {doc_id}")
    
    try:
        # Untrash
        drive_service.files().update(fileId=doc_id, body={'trashed': False}).execute()
        
        # Verify
        file_metadata = drive_service.files().get(fileId=doc_id, fields='trashed').execute()
        if file_metadata.get('trashed') is False:
             return f"Success: Restored '{doc_name}' (ID: {doc_id})."
        else:
             return f"Error: Failed to restore '{doc_name}'. It is still in trash."
             
    except Exception as e:
        return f"Error restoring document: {e}"

@tool
def create_folder(folder_name: str) -> str:
    """Creates a new folder in Google Drive."""
    folder_id = get_folder_id(folder_name)
    if folder_id:
        return f"Folder '{folder_name}' already exists (ID: {folder_id})."
        
    try:
        drive_service = get_drive_service()
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = drive_service.files().create(body=file_metadata, fields='id').execute()
        return f"Success: Created folder '{folder_name}' (ID: {folder.get('id')})."
    except Exception as e:
        return f"Error creating folder: {e}"

@tool
def move_file(file_name: str, folder_name: str) -> str:
    """Moves a file (e.g., Google Doc) into a specific folder."""
    # Note: We use get_doc_id assumes it's a doc we are moving, consistent with other ops
    # If we wanted to move ANY file, we'd need a generic get_file_id. 
    # For now, following user spec which references get_doc_id.
    doc_id = get_doc_id(file_name) 
    if not doc_id:
        return f"Error: File '{file_name}' not found."
        
    folder_id = get_folder_id(folder_name)
    if not folder_id:
        return f"Error: Folder '{folder_name}' not found."
        
    try:
        drive_service = get_drive_service()
        # 1. Get current parents
        file = drive_service.files().get(fileId=doc_id, fields='parents').execute()
        previous_parents = ",".join(file.get('parents'))
        
        # 2. Update (Add new folder, remove old ones)
        drive_service.files().update(
            fileId=doc_id,
            addParents=folder_id,
            removeParents=previous_parents,
            fields='id, parents'
        ).execute()
        return f"Success: Moved '{file_name}' into '{folder_name}'."
    except Exception as e:
        return f"Error moving file: {e}"

@tool
def search_drive(query_text: str, search_type: str = 'name', file_type: str = None) -> str:
    """Searches Google Drive for files.
    Args:
        query_text: Text to search for.
        search_type: 'name' (default) or 'content'.
        file_type: Optional 'pdf' or 'folder' to filter by type.
    """
    drive_service = get_drive_service()
    
    # Build query
    q_parts = ["trashed = false"]
    
    if search_type == 'content':
        q_parts.append(f"fullText contains '{query_text}'")
    else:
        q_parts.append(f"name contains '{query_text}'")
        
    if file_type == 'pdf':
        q_parts.append("mimeType = 'application/pdf'")
    elif file_type == 'folder':
        q_parts.append("mimeType = 'application/vnd.google-apps.folder'")
        
    query = " and ".join(q_parts)
    
    try:
        results = drive_service.files().list(
            q=query, spaces='drive', fields='files(id, name, mimeType)', pageSize=10
        ).execute()
        files = results.get('files', [])
        
        if not files:
            return "No files found matching query."
            
        output = [f"Found {len(files)} files:"]
        for f in files:
            output.append(f"- {f['name']} (ID: {f['id']}, Type: {f['mimeType']})")
        return "\n".join(output)
    except Exception as e:
        return f"Error searching drive: {e}"

@tool
def list_recent_files(limit: int = 5) -> str:
    """Lists the most recently modified files (excluding trash)."""
    drive_service = get_drive_service()
    try:
        results = drive_service.files().list(
            q="trashed = false",
            orderBy="modifiedTime desc",
            pageSize=limit,
            fields="files(id, name, mimeType, modifiedTime)"
        ).execute()
        files = results.get('files', [])
        
        if not files:
            return "No recent files found."
            
        output = [f"Recent {len(files)} files:"]
        for f in files:
            output.append(f"- {f['name']} (Type: {f['mimeType']})")
        return "\n".join(output)
    except Exception as e:
        return f"Error listing recent files: {e}"

@tool
def read_pdf_from_drive(pdf_name: str) -> str:
    """Reads text content from a PDF file in Google Drive."""
    drive_service = get_drive_service()
    
    # Find file ID
    query = f"name = '{pdf_name}' and mimeType = 'application/pdf' and trashed = false"
    try:
        results = drive_service.files().list(q=query, fields='files(id)').execute()
        files = results.get('files', [])
        if not files:
            return f"Error: PDF '{pdf_name}' not found."
            
        file_id = files[0]['id']
        
        # Download bytes
        request = drive_service.files().get_media(fileId=file_id)
        file_content = io.BytesIO(request.execute())
        
        # Extract text
        reader = pypdf.PdfReader(file_content)
        text = []
        for page in reader.pages:
            text.append(page.extract_text())
            
        return "\n".join(text)
    except Exception as e:
        return f"Error reading PDF: {e}"

@tool
def upload_file_to_drive(local_path: str, folder_name: str = None) -> str:
    """Uploads a local file to Google Drive."""
    drive_service = get_drive_service()
    
    filename = local_path.split('/')[-1]
    file_metadata = {'name': filename}
    
    if folder_name:
        folder_id = get_folder_id(folder_name)
        if folder_id:
            file_metadata['parents'] = [folder_id]
        else:
            return f"Error: Destination folder '{folder_name}' not found."
            
    try:
        media = MediaFileUpload(local_path, resumable=True)
        file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return f"Success: Uploaded '{filename}' to Drive (ID: {file.get('id')})."
    except Exception as e:
        return f"Error uploading file: {e}"

@tool
def empty_trash() -> str:
    """Permanently deletes all files in the trash. Use with CAUTION."""
    try:
        drive_service = get_drive_service()
        drive_service.files().emptyTrash().execute()
        return "Success: Trash has been permanently emptied."
    except Exception as e:
        return f"Error emptying trash: {e}"

@tool
def list_shared_files() -> str:
    """Lists files shared with you."""
    drive_service = get_drive_service()
    try:
        results = drive_service.files().list(
            q="sharedWithMe = true and trashed = false",
            pageSize=10,
            fields="files(id, name, owners)"
        ).execute()
        files = results.get('files', [])
        
        if not files:
            return "No shared files found."
            
        output = ["Files shared with you:"]
        for f in files:
            owner = f.get('owners', [{}])[0].get('displayName', 'Unknown')
            output.append(f"- {f['name']} (Owner: {owner})")
        return "\n".join(output)
    except Exception as e:
        return f"Error listing shared files: {e}"
