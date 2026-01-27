import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type, RetryError
from google.api_core.exceptions import ResourceExhausted

# Import tools
from tools.gmail import get_recent_emails, search_emails, send_email
from tools.docs import create_new_doc, read_doc_content
from tools.drive import list_drive_files, delete_file_by_name
from tools.calendar import list_upcoming_events, create_calendar_event
from tools.youtube import search_videos
from tools.search import google_search
from tools.scheduler import schedule_task, list_scheduled_tasks
from langchain_community.tools import RequestsGetTool, RequestsPostTool
from langchain_community.utilities import TextRequestsWrapper

# Load environment variables
load_dotenv()

def get_agent_executor(model_name: str = "gemini-1.5-flash-001"):
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
        get_recent_emails,
        search_emails,
        send_email,
        create_new_doc,
        read_doc_content,
        list_drive_files,
        delete_file_by_name,
        list_upcoming_events,
        create_calendar_event,
        search_videos,
        google_search,
        schedule_task,
        list_scheduled_tasks,
        RequestsGetTool(requests_wrapper=TextRequestsWrapper(), allow_dangerous_requests=True),
        RequestsPostTool(requests_wrapper=TextRequestsWrapper(), allow_dangerous_requests=True)
    ]

    # 3. Create the prompt
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are Gent AI, a helpful personal assistant. "
                       "You have access to the user's Google account (Gmail, Docs, Drive, Calendar, YouTube) "
                       "and can perform actions on their behalf. You can also delete files from Drive by moving them to the trash. "
                       "Current Date/Time: {date}\n\n"
                       "STRICT RULES:\n"
                       "1. FRESHNESS RULE: If the user asks for 'latest', 'current', 'recent', 'new' items, or asks about 'today', "
                       "you MUST ignore conversation history and execute the relevant Tool (e.g., Gmail, Calendar) to fetch real-time data. "
                       "Do not rely on past turn data for these queries.\n"
                       "2. NO ASSUMPTIONS: Never assume the state of the user's inbox, drive, or calendar. Always check with a tool.\n"
                       "3. EXPLICIT ACTION: When fetching data, briefly explicitly state what you are doing (e.g. 'Checking Gmail for latest messages...').\n"
                       "4. EMAIL SUMMARY: When asked for recent emails, summarize the top few results, explicitly noting which ones are Read vs. Unread.\n"
                       "5. TIME & SCHEDULING: If the user mentions specific future times (like 'at 6pm', 'in 2 hours', 'every day'), you MUST use the `schedule_task` tool. "
                       "If the user asks 'what is scheduled' or 'show future tasks', use the `list_scheduled_tasks` tool. Do not try to wait yourself.\n"
                       "6. CONFIRMATION PROTOCOL: You are FORBIDDEN from confirming an action (like sending email) until you receive a tool return value. "
                       "If tool execution fails, report the error. Do not assume success."),
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

    return agent_executor

from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type, RetryError

# ... imports ...

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

    # Use 2.0-flash as the router
    llm_flash = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
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
        "FLASH": "gemini-2.0-flash",
        "PRO": "gemini-2.5-pro"
    }
    selected_model = model_name_map.get(model_type, "gemini-2.0-flash")
    
    # 2. Get Executor with selected model
    executor = get_agent_executor(model_name=selected_model)
    
    try:
        response = run_agent_with_retry(
            executor, 
            input_text, 
            chat_history, 
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
