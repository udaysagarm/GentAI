import os
import warnings
import logging
import datetime  # Added for time awareness
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from moth.tools import get_all_tools
from moth.memory_engine import init_db, save_memory, get_recent_memories

# Suppress warnings from langchain_google_genai about schema keys
warnings.filterwarnings("ignore", module="langchain_google_genai")
logging.getLogger("langchain_google_genai._function_utils").setLevel(logging.ERROR)

# Load environment variables (API Key)
load_dotenv()

def select_best_model(user_input: str) -> str:
    """
    Analyzes the user's query complexity to select the most efficient model.
    
    Tiers:
    1. Tier 1 (Fast): Simple greetings, factual q's -> gemini-2.0-flash-lite
    2. Tier 2 (Smart): Reasoning, coding, summarization -> gemini-2.0-flash
    """
    user_input_lower = user_input.lower().strip()
    word_count = len(user_input.split())
    
    # Tier 1 keywords (Very simple interactions)
    tier1_keywords = ["hi", "hello", "hey", "what time", "date", "weather", "thanks", "thank you"]
    
    # 0. SEARCH INTENT -> Gemini 2.5 Pro (Best for Search)
    search_keywords = ["search", "google", "find online", "latest news", "current events", "web"]
    if any(kw in user_input_lower for kw in search_keywords):
        return "gemini-2.5-pro"
    
    # Check for simple queries
    is_simple = any(kw in user_input_lower for kw in tier1_keywords)
    
    # CRITICAL FIX: If the user mentions "email", "send", or "schedule", FORCE Tier 2 (Smart)
    # This prevents the "Lite" model from misinterpreting "Send email" as "Draft email"
    if "email" in user_input_lower or "send" in user_input_lower or "schedule" in user_input_lower:
        return "gemini-2.0-flash"

    if is_simple and word_count < 15:
        return "gemini-2.0-flash-lite"
        
    # Default to Tier 2 (Smart) for everything else (including search, email, calendar)
    # Using -exp version as it is strictly 'gemini-2.0-flash-exp' in many regions currently, 
    # but user requested 'gemini-2.0-flash'. We will try the generic one, 
    # but if 404s continue, we might need -exp.
    return "gemini-2.0-flash"

def get_agent_executor(model_name=None):
    """
    Builds the AI Agent with a Context-Aware System Prompt, using the safe manual creation method.
    Includes robust checks for tool loading and binding to prevent Nonetype crashes.
    """
    # Default model if none provided
    if not model_name:
        model_name = "gemini-2.0-flash"
        
    print(f"DEBUG: Initializing Agent with model: {model_name}")
    
    # 1. Initialize the Brain (LLM)
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("CRITICAL ERROR: GEMINI_API_KEY is missing. Please set it in your .env file.")
        raise ValueError("GEMINI_API_KEY not found.")

    llm = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0,
        google_api_key=api_key
    )

    # 2. Paranoid Tool Loading
    try:
        tools = get_all_tools()
        if tools is None:
            print("WARNING: get_all_tools() returned None. Using empty list.")
            tools = []
        
        # Explicitly filter out None tools
        tools = [t for t in tools if t is not None]
        print(f"DEBUG: Loaded {len(tools)} tools.")
        
        if not tools:
            print("WARNING: No valid tools loaded. Agent will operate in chat-only mode.")
            
    except Exception as e:
        print(f"ERROR: Failed to load tools. {e}")
        tools = []

    # ---------------------------------------------------------
    # 3. Dynamic Time Context (THE UPGRADE)
    # ---------------------------------------------------------
    current_time = datetime.datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")

    system_instructions = f"""
    You are Moth AI, a good AI Assistant.
    
    SYSTEM CONTEXT:
    - Current Date & Time: {current_time}
    - You must use this current time to calculate relative dates like "tomorrow", "next week", or "in 30 minutes".
    
    BEHAVIORAL GUIDELINES:
    1. **Context Retention:** If the user says "Add THAT to calendar", look at the immediately preceding message (e.g., an email summary) to extract the event title, date, and time. Do not ask for information you already have.
    2. **Proactivity:** If you perform a task (like summarizing an email) and detect an actionable item (like a meeting request), IMMEDIATELY ask the user if they want you to take action.
       - *Example:* "I found a meeting request for tomorrow at 9 AM. Would you like me to add this to your calendar?"
    3. **Tool Use:** Always use the provided tools to answer questions. Never guess.
    4. **EMAIL HANDLING:** 
       - If user says **"SEND email"**: Use `send_gmail_message`.
       - If user says **"DRAFT email"**: Use `create_gmail_draft`.
       - NEVER use the draft tool if the user explicitly asked to SEND.
    5. **MANDATORY SUMMARY:** AFTER executing a tool, you MUST provide a final natural language summary of the result. NEVER return an empty response.
    
    Begin!
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_instructions),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    # ---------------------------------------------------------
    # 4. Create the Agent (ROBUST & SAFE)
    # ---------------------------------------------------------
    try:
        from langchain.agents.format_scratchpad.tools import format_to_tool_messages
        from langchain.agents.output_parsers.tools import ToolsAgentOutputParser
        from langchain_core.runnables import RunnableLambda

        # Safety Check: Bind tools properly
        llm_with_tools = None
        
        if tools:
            # Only try to bind if we have tools
            if hasattr(llm, "bind_tools"):
                try:
                    llm_with_tools = llm.bind_tools(tools)
                except Exception as e:
                    print(f"WARNING: llm.bind_tools failed: {e}")
                    llm_with_tools = None
            
            # If binding failed or strictly returned None, fallback to raw LLM
            if llm_with_tools is None:
                 print("CRITICAL WARNING: bind_tools returned None. Fallback to raw LLM (no tools).")
                 llm_with_tools = llm
        else:
            # No tools to bind
            llm_with_tools = llm

        # Create a single RunnableLambda that prepares the input with scratchpad
        def prepare_input(x):
            """Adds agent_scratchpad to the input dict."""
            return {
                **x,
                "agent_scratchpad": format_to_tool_messages(x.get("intermediate_steps", []))
            }

        # Compose chain using only RunnableLambda
        def debug_llm_output(msg):
            print(f"DEBUG: RAW LLM OUTPUT CONTENT: {msg.content}")
            print(f"DEBUG: RAW LLM OUTPUT TYPE: {type(msg)}")
            return msg

        agent = (
            RunnableLambda(prepare_input)
            | prompt 
            | llm_with_tools 
            | RunnableLambda(debug_llm_output)
            | ToolsAgentOutputParser()
        )
        print("DEBUG: Agent chain composed successfully (using custom RunnableLambda).")
        
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to manually create agent. {e}")
        raise e

    # 5. Create the Executor - VERBOSE & PARSING ERRORS HANDLED
    executor = AgentExecutor(
        agent=agent, 
        tools=tools, 
        verbose=True, 
        handle_parsing_errors=True,
        return_intermediate_steps=True  # Enables access to tool outputs in fallback
    )
    
    return executor

def run_agent(user_input, chat_history):
    """
    Main function called by app.py to run the chat.
    """
    try:
        # Initialize Memory DB
        init_db()
        
        # Save User Input immediately
        save_memory('user', user_input)
        
        # Get "Short Term" Context from Long Term Memory
        # We fetch the last 10 messages to give the bot context of what just happened.
        memory_context = get_recent_memories(limit=10)
        
        # Dynamic Model Routing
        selected_model = select_best_model(user_input)
        print(f"DEBUG: 🧠 Routing query to [{selected_model}] based on complexity.")
        
        agent_executor = get_agent_executor(model_name=selected_model)
        
        # Pass memory_context to the agent
        print(f"DEBUG: Running agent with input: {user_input}")
        response = agent_executor.invoke({
            "input": user_input, 
            "chat_history": memory_context  # Use the DB memory instead of ephemeral list
        })
        output = response.get("output", "")
        
        # Save AI Response
        if output:
            save_memory('ai', output)
        if not output:
             # Check intermediate steps?
             steps = response.get("intermediate_steps", [])
             if steps:
                 print("DEBUG: Steps keys:", [s[0].tool for s in steps])
                 # Fallback: if we have steps but no output, maybe return the last tool output?
                 last_tool_output = steps[-1][1]
                 return f"I performed the action, but I'm having trouble summarizing it. Here is the raw result:\n{last_tool_output}"

             print("WARNING: Agent returned empty output!")
             return "I processed your request, but I have no specific respose to show. (Empty Output)"
        return output
        
    except Exception as e:
        print(f"ERROR in run_agent: {e}")
        return f"⚠️ An error occurred: {str(e)}"
