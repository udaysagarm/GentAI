from langchain_community.tools import DuckDuckGoSearchRun
from langchain.tools import tool

@tool
def google_search(query: str) -> str:
    """Performs a web search using DuckDuckGo to retrieve relevant information.
    Useful for getting current events, facts, or looking up info not in your email/docs.
    """
    search = DuckDuckGoSearchRun()
    return search.run(query)
