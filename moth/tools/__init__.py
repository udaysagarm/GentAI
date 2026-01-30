from moth.tools.gmail_ops import create_gmail_draft, read_recent_emails, read_email_content, save_email_attachment, send_gmail_message
from moth.tools.doc_ops import (
    create_document, read_document, append_to_document, overwrite_document, 
    delete_document, restore_document, create_folder, move_file,
    search_drive, list_recent_files, read_pdf_from_drive, upload_file_to_drive, 
    empty_trash, list_shared_files
)
from moth.tools.drive import list_drive_files, delete_file_by_name
from moth.tools.calendar import list_upcoming_events, create_calendar_event, delete_event, update_event
from moth.tools.youtube import search_videos
from moth.tools.search import google_search
from moth.tools.scheduler import schedule_task, list_scheduled_tasks
from moth.tools.weather import get_current_weather
from langchain_community.tools import RequestsGetTool, RequestsPostTool
from langchain_community.utilities import TextRequestsWrapper

def get_all_tools():
    return [
        create_gmail_draft,
        read_recent_emails,
        read_email_content,
        save_email_attachment,
        send_gmail_message,
        create_document,
        read_document,
        append_to_document,
        overwrite_document,
        restore_document,
        create_folder,
        move_file,
        search_drive,
        list_recent_files,
        read_pdf_from_drive,
        upload_file_to_drive,
        empty_trash,
        list_shared_files,
        list_drive_files,
        delete_file_by_name,
        list_upcoming_events,
        create_calendar_event,
        delete_event,
        update_event,
        search_videos,
        google_search,
        schedule_task,
        list_scheduled_tasks,
        get_current_weather,
        RequestsGetTool(requests_wrapper=TextRequestsWrapper(), allow_dangerous_requests=True),
        RequestsPostTool(requests_wrapper=TextRequestsWrapper(), allow_dangerous_requests=True)
    ]
