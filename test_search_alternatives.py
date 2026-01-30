import os
import sys
import warnings
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

# Suppress Pydantic warnings
warnings.filterwarnings("ignore")
os.environ["create_tool_calling_agent"] = "false" # just in case

load_dotenv()

print("--- Test 2: Native Grounding ---")
try:
    # Attempt to enable Google Search tool via 'tools' argument
    # The native tool definition for google search is usually passed as a dict
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0
    )
    
    # In the raw API valid tool is: tools=[{'google_search': {}}]
    # LangChain might pass this through if we use .bind(tools=[...])
    
    tools = [{'google_search': {}}]
    llm_with_tools = llm.bind(tools=tools)
    
    print("Invoking LLM with google_search tool bound...")
    res = llm_with_tools.invoke("What is the latest score of the Super Bowl? Use google search.")
    print(f"LLM Response Content: {res.content}")
    print(f"LLM Response Tool Calls: {res.tool_calls}")
    
except Exception as e:
    print(f"Native Grounding Test Failed: {e}")
