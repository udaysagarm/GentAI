import os
import sys
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type, RetryError
from google.api_core.exceptions import ResourceExhausted

# Import tools
from moth.tools.gmail_ops import create_gmail_draft, read_recent_emails, read_email_content, save_email_attachment
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

# Load environment variables
load_dotenv()

def debug_init():
    print("DEBUG: Starting initialization...")
    
    if not os.getenv("GEMINI_API_KEY"):
        print("ERROR: GEMINI_API_KEY not found!")
        return

    model_name = "gemini-2.0-flash-lite"
    print(f"DEBUG: Initializing LLM {model_name}...")
    llm = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0.7,
        google_api_key=os.getenv("GEMINI_API_KEY")
    )
    print(f"DEBUG: LLM type: {type(llm)}")

    print("DEBUG: Defining tools...")
    tools = [
        create_gmail_draft,
        read_recent_emails,
        read_email_content,
        save_email_attachment,
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
    
    for i, t in enumerate(tools):
        if t is None:
            print(f"CRITICAL: Tool {i} is None!")
        else:
            print(f"Tool {i}: {t.name} ({type(t)})")

    print("DEBUG: Creating prompt...")
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are Moth AI."),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ]
    )

    print("DEBUG: Calling create_tool_calling_agent...")
    try:
        agent = create_tool_calling_agent(llm, tools, prompt)
        print(f"DEBUG: Agent created. Type: {type(agent)}")
    except Exception as e:
        print(f"CRITICAL ERROR in create_tool_calling_agent: {e}")
        import traceback
        traceback.print_exc()
        return

    print("DEBUG: Creating AgentExecutor...")
    try:
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
        print(f"DEBUG: AgentExecutor created. Type: {type(agent_executor)}")
    except Exception as e:
        print(f"CRITICAL ERROR in AgentExecutor init: {e}")
        traceback.print_exc()
        return

    print("DEBUG: Invoking agent with test input 'hi'...")
    try:
        from datetime import datetime
        result = agent_executor.invoke({
            "input": "hi", 
            "chat_history": [],
            "date": datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        })
        print(f"DEBUG: Invocation success! Output: {result['output']}")
    except Exception as e:
        print(f"CRITICAL ERROR during invoke: {e}")
        import traceback
        traceback.print_exc()
        return

    print("DEBUG: Importing run_agent...")
    try:
        from moth.agent import run_agent
    except ImportError as e:
        print(f"CRITICAL ERROR importing run_agent: {e}")
        return

    print("DEBUG: Calling run_agent('hi')...")
    try:
        result = run_agent("hi", [])
        print(f"DEBUG: run_agent success! Result: {result}")
    except Exception as e:
        print(f"CRITICAL ERROR in run_agent: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_init()
