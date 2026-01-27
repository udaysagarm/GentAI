from datetime import datetime, timedelta
from langchain.tools import tool
from tools.utils import get_calendar_service

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

@tool
def create_calendar_event(summary: str, start_datetime_iso: str, end_datetime_iso: str) -> str:
    """Creates a new event in the primary calendar.
    Format dates as ISO 8601 strings (e.g., '2023-10-23T09:00:00-07:00').
    """
    service = get_calendar_service()
    event = {
        'summary': summary,
        'start': {
            'dateTime': start_datetime_iso,
        },
        'end': {
            'dateTime': end_datetime_iso,
        },
    }
    event = service.events().insert(calendarId='primary', body=event).execute()
    return f"Event created: {event.get('htmlLink')}"
