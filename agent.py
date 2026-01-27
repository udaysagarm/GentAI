import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type, RetryError
from google.api_core.exceptions import ResourceExhausted

# Import tools
from tools.gmail import get_unread_emails, search_emails, send_email
from tools.docs import create_new_doc, read_doc_content
from tools.drive import list_drive_files, delete_file_by_name
from tools.calendar import list_upcoming_events, create_calendar_event
from tools.youtube import search_videos
from tools.search import google_search
from langchain_community.tools import RequestsGetTool, RequestsPostTool
from langchain_community.utilities import TextRequestsWrapper

# Load environment variables
load_dotenv()

def get_agent_executor():
    """Initializes and returns the agent executor."""
    
    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError("GEMINI_API_KEY not found in environment variables.")

    # 1. Initialize the model
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0,
        google_api_key=os.getenv("GEMINI_API_KEY")
    )

    # 2. Define tools
    tools = [
        get_unread_emails,
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
                       "4. CONFIRMATION PROTOCOL: You are FORBIDDEN from confirming an action (like sending email) until you receive a tool return value. "
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

def run_agent(input_text: str, chat_history: list = []):
    """Runs the agent with the given input and chat history."""
    from datetime import datetime
    executor = get_agent_executor()
    
    try:
        response = run_agent_with_retry(
            executor, 
            input_text, 
            chat_history, 
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        return response['output']
    except RetryError:
        return "I am currently hitting Google's rate limits. Please wait 2 minutes and try again."
