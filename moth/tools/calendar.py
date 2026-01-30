from datetime import datetime, timedelta
from langchain.tools import tool
from moth.tools.utils import get_calendar_service

@tool
def list_upcoming_events(max_results: int = 10) -> str:
    """Lists upcoming events on the user's primary calendar."""
    service = get_calendar_service()
    now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    events_result = service.events().list(calendarId='primary', timeMin=now,
                                          maxResults=max_results, singleEvents=True,
                                          orderBy='startTime').execute()
    events = events_result.get('items', [])

    if not events:
        return "No upcoming events found."

    output = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        output.append(f"{start} - {event['summary']}")
    
    return "\n".join(output)

from tzlocal import get_localzone

@tool
def create_calendar_event(summary: str, start_datetime_iso: str, end_datetime_iso: str) -> str:
    """Creates a new event in the primary calendar.
    Format dates as ISO 8601 strings (e.g., '2023-10-23T09:00:00-07:00').
    """
    service = get_calendar_service()
    
    # Get local timezone
    local_tz = str(get_localzone())
    
    event = {
        'summary': summary,
        'start': {
            'dateTime': start_datetime_iso,
            'timeZone': local_tz,
        },
        'end': {
            'dateTime': end_datetime_iso,
            'timeZone': local_tz,
        },
    }
    
    print(f"DEBUG: Payload being sent: {event}")
    
    try:
        created_event = service.events().insert(calendarId='primary', body=event).execute()
        print(f"DEBUG: API Response: {created_event}")
        return f"Event created: {created_event.get('htmlLink')}"
    except Exception as e:
        error_msg = f"Error creating event: {e}"
        print(f"DEBUG: {error_msg}")
        return error_msg

def find_event(query: str, date_hint: str = None):
    """Helper: Finds an event ID by fuzzy matching the summary."""
    service = get_calendar_service()
    now = datetime.utcnow().isoformat() + 'Z'
    
    # List upcoming 20 events (better chance to find match)
    # Ideally we'd use date_hint to narrow down, but looking ahead 20 is safe default
    events_result = service.events().list(calendarId='primary', timeMin=now,
                                          maxResults=20, singleEvents=True,
                                          orderBy='startTime').execute()
    events = events_result.get('items', [])
    
    print(f"DEBUG: Searching {len(events)} events for query: '{query}'")
    
    query = query.lower()
    for event in events:
        summary = event.get('summary', '').lower()
        if query in summary:
            print(f"DEBUG: Found Event ID: {event['id']} for query {query} (Match: {event.get('summary')})")
            return event
            
    print(f"DEBUG: No event found for query: '{query}'")
    return None

@tool
def delete_event(query: str, date_hint: str = None) -> str:
    """Deletes an event by matching its summary/title.
    Args:
        query: The title or keywords of the meeting to delete (e.g. "CEO meeting")
        date_hint: Optional text like "tomorrow" to help (currently unused but good for agent context)
    """
    event = find_event(query, date_hint)
    if not event:
        return f"Error: Event containing '{query}' not found."
        
    try:
        service = get_calendar_service()
        service.events().delete(calendarId='primary', eventId=event['id']).execute()
        return f"Success: Deleted '{event.get('summary')}'"
    except Exception as e:
        return f"Error deleting event: {e}"

@tool
def update_event(query: str, date_hint: str = None, new_start_time: str = None, new_end_time: str = None) -> str:
    """Updates/Reschedules an event.
    Args:
        query: The title/keywords of the meeting to move.
        new_start_time: ISO 8601 string (e.g. '2023-10-23T14:00:00')
        new_end_time: ISO 8601 string
    """
    event = find_event(query, date_hint)
    if not event:
        return f"Error: Event containing '{query}' not found."
    
    local_tz = str(get_localzone())
    body = {}
    
    if new_start_time:
        body['start'] = {'dateTime': new_start_time, 'timeZone': local_tz}
    if new_end_time:
        body['end'] = {'dateTime': new_end_time, 'timeZone': local_tz}
        
    if not body:
        return "Error: No new time provided for update."
        
    print(f"DEBUG: Sending PATCH to Event ID {event['id']} with body: {body}")
    
    try:
        service = get_calendar_service()
        updated_event = service.events().patch(calendarId='primary', eventId=event['id'], body=body).execute()
        return f"Success: Moved '{updated_event.get('summary')}' to new time."
    except Exception as e:
        return f"Error updating event: {e}"
