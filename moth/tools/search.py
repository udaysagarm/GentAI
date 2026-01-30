import os
from google import genai
from google.genai import types
from langchain.tools import tool
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@tool
def google_search(query: str) -> str:
    """
    Performs a live web search using Gemini's native Google Search Grounding.
    Useful for finding current events, news, facts, or real-time information.
    """
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return "Error: GEMINI_API_KEY not found."

        # Configure the direct Gemini API (New SDK)
        client = genai.Client(api_key=api_key)
        
        # We ask the model to answer the query using the search tool
        print(f"DEBUG: Generating content with native search for: {query}")
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=query,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        
        # The response.text will contain the answer grounded in search results
        if response.text:
            return f"Search Result:\n{response.text}"
        else:
            return "No search results returned from Gemini."

    except Exception as e:
        return f"Gemini Search Error: {str(e)}"
