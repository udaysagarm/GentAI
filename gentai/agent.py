import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type, RetryError
from google.api_core.exceptions import ResourceExhausted

# Import tools
from tools.gmail_ops import create_gmail_draft, read_recent_emails, read_email_content, save_email_attachment
from tools.doc_ops import (
    create_document, read_document, append_to_document, overwrite_document, 
    delete_document, restore_document, create_folder, move_file,
    search_drive, list_recent_files, read_pdf_from_drive, upload_file_to_drive, 
    empty_trash, list_shared_files
)
from tools.drive import list_drive_files, delete_file_by_name
from tools.calendar import list_upcoming_events, create_calendar_event, delete_event, update_event
from tools.youtube import search_videos
from tools.search import google_search
from tools.scheduler import schedule_task, list_scheduled_tasks
from tools.weather import get_current_weather
from langchain_community.tools import RequestsGetTool, RequestsPostTool
from langchain_community.utilities import TextRequestsWrapper

# Load environment variables
load_dotenv()

def get_agent_executor(model_name: str = "gemini-2.0-flash-lite"):
    """Initializes and returns the agent executor."""
    
    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError("GEMINI_API_KEY not found in environment variables.")

    # 1. Initialize the model
    llm = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0.7,
        google_api_key=os.getenv("GEMINI_API_KEY")
    )


    # 2. Define tools
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

    # 3. Create the prompt
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are Gent AI, a smart assistant.\n\n"
                       "CRITICAL CONTEXT:\n"
                       "- Current Date & Time: {date}\n"
                       "- User's Timezone: America/Detroit (EST)\n\n"
                       "INSTRUCTIONS:\n"
                       "- If the user says 'tomorrow', 'next week', or 'in 2 days', CALCULATE the date yourself based on the Current Date above. "
                       "Do NOT ask the user for the date.\n"
                       "- FRESHNESS RULE: If the user asks for 'latest', 'current', 'recent', 'new' items, or asks about 'today', "
                       "you MUST ignore conversation history and execute the relevant Tool (e.g., Gmail, Calendar) to fetch real-time data. "
                       "Do not rely on past turn data for these queries.\n"
                       "- NO ASSUMPTIONS: Never assume the state of the user's inbox, drive, or calendar. Always check with a tool.\n"
                       "- EXPLICIT ACTION: When fetching data, briefly explicitly state what you are doing (e.g. 'Checking Gmail for latest messages...').\n"
                       "- EMAIL SUMMARY: When asked for recent emails, summarize the top few results, explicitly noting which ones are Read vs. Unread.\n"
                       "- TIME & SCHEDULING: If the user mentions specific future times (like 'at 6pm', 'in 2 hours', 'every day'), you MUST use the `schedule_task` tool. "
                       "If the user asks 'what is scheduled' or 'show future tasks', use the `list_scheduled_tasks` tool. Do not try to wait yourself.\n"
                       "- WEATHER QUERIES: When asked about weather, ALWAYS use the `get_current_weather` tool instead of Google Search.\n"
                       "- CONFIRMATION PROTOCOL: You are FORBIDDEN from confirming an action (like sending email) until you receive a tool return value. "
                       "If tool execution fails, report the error. Do not assume success.\n"
                       "8. CALENDAR UPDATES: When the user asks to RESCHEDULE, MOVE, or DELAY a meeting, you MUST use the `update_event` tool. "
                       "NEVER use `create_event` for existing meetings. When deleting, use `delete_event`.\n"
                       "9. GOOGLE DOCS: You cannot 'edit' a specific sentence. You can only READ the full doc, APPEND text to the end, or REWRITE the entire doc. "
                       "If the user says 'change', 'replace', or 'rewrite' the entire doc, use `overwrite_document`. If they just want to add notes, use `append_to_document`. "
                       "To write a new report, use `create_document`.\n"
                       "10. RESTORE/RECOVER: If the user asks to 'bring back', 'recover', or 'restore' a deleted file, use the `restore_document` tool.\n"
                       "11. ORGANIZATION: You can create folders and move files. When creating a new document, check if the user specified a destination folder.\n"
                       "12. DRIVE CAPABILITIES: You can read PDFs directly, search file contents, and list recent work. BE CAREFUL with `empty_trash` - ask for confirmation first.\n"
                       "13. GMAIL: Default to `create_gmail_draft` for writing emails unless the user explicitly commands 'SEND'. When reading, summarize the sender and subject.\n"
                       "14. EMAIL READING PROTOCOL: When the user asks 'what does it say' or for details, use `get_email_full_content`. DO NOT output the full raw text unless asked. INSTEAD, summarize key points, dates, and action items."),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ]
    )
    
    # 4. Create the agent
    agent = create_tool_calling_agent(llm, tools, prompt)
    

    # 5. Create the executor
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    return agent_executor

@retry(
    retry=retry_if_exception_type(ResourceExhausted),
    wait=wait_random_exponential(min=1, max=120),
    stop=stop_after_attempt(10)
)
def run_agent_with_retry(executor, input_text, chat_history, date_str):
    # Simplified debug print to avoid AttributeError on LCEL chain internals
    print("DEBUG: Executing agent with retry logic...")
    return executor.invoke({
        "input": input_text,
        "chat_history": chat_history,
        "date": date_str
    })

def decide_model(user_query: str) -> str:
    """Decides whether to use FLASH or PRO model based on query complexity."""
    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError("GEMINI_API_KEY not found in environment variables.")

    # Use 2.0-flash-lite as the router
    llm_flash = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-lite",
        temperature=0.7,
        google_api_key=os.getenv("GEMINI_API_KEY")
    )
    
    prompt = (
        "Analyze the following user query. If it requires complex reasoning, creative writing, coding, or deep analysis, return 'PRO'. "
        "If it is a simple informational query, a factual search, a tool look-up, or a greeting, return 'FLASH'. "
        "Return ONLY the word 'PRO' or 'FLASH'.\n\n"
        f"User Query: {user_query}"
    )
    
    try:
        response = llm_flash.invoke(prompt)
        decision = response.content.strip().upper()
        if decision not in ["PRO", "FLASH"]:
            return "FLASH" # Default fallback
        return decision
    except Exception as e:
        print(f"Error in decide_model: {e}")
        return "FLASH" # Fallback on error

def run_agent(input_text: str, chat_history: list = []):
    """Runs the agent with the given input and chat history."""
    from datetime import datetime
    
    # 1. Decide Model
    model_type = decide_model(input_text)
    print(f"DEBUG: Routing to: {model_type}")
    
    # Map to actual available models
    model_name_map = {
        "FLASH": "gemini-2.0-flash-lite",
        "PRO": "gemini-2.0-flash"
    }
    selected_model = model_name_map.get(model_type, "gemini-2.0-flash")
    
    # 2. Get Executor with selected model
    executor = get_agent_executor(model_name=selected_model)
    
    try:
        response = run_agent_with_retry(
            executor, 
            input_text, 
            chat_history, 
            datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        )
        # Return both output and model used
        return {
            "output": response['output'],
            "model_used": model_type
        }
    except RetryError:
        return {
            "output": "I am currently hitting Google's rate limits. Please wait 2 minutes and try again.",
            "model_used": "UNKNOWN"
        }
