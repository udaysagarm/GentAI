from langchain.tools import tool
from moth.tools.utils import get_drive_service

@tool
def list_drive_files(limit: int = 10) -> str:
    """Lists the most recently modified files in Google Drive."""
    service = get_drive_service()
    results = service.files().list(
        pageSize=limit, fields="nextPageToken, files(id, name, mimeType, modifiedTime)"
    ).execute()
    files = results.get('files', [])

    if not files:
        return "No files found."

    output = []
    for item in files:
        output.append(f"{item['name']} ({item['mimeType']}) - ID: {item['id']}")
    
    return "\n".join(output)

@tool
def delete_file_by_name(filename: str) -> str:
    """Deletes a file from Google Drive by its name. 
    1. Searches for the file by name.
    2. If found, moves it to the trash.
    Handles duplicate names by asking for clarification (which isn't implemented here, so it just errors out safely).
    """
    service = get_drive_service()
    
    # query for the file
    query = f"name = '{filename}' and trashed = false"
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    files = results.get('files', [])

    if not files:
        return f"File not found: '{filename}'"
    
    if len(files) > 1:
        # Construct a helpful message listing the files
        file_list = "\n".join([f"- {f['name']} (ID: {f['id']})" for f in files])
        return f"Multiple files found with name '{filename}'. Please specify by ID or rename one:\n{file_list}"

    # Exactly one file found
    file_id = files[0]['id']
    try:
        service.files().update(fileId=file_id, body={'trashed': True}).execute()
        return f"Successfully moved '{filename}' (ID: {file_id}) to trash."
    except Exception as e:
        return f"Error deleting file: {e}"
