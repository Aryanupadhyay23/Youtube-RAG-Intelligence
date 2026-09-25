import os
from config import TAVILY_API_KEY

try:
    from langchain_community.tools.tavily_search import TavilySearchResults
    if TAVILY_API_KEY:
        os.environ["TAVILY_API_KEY"] = TAVILY_API_KEY
        search_tool = TavilySearchResults(max_results=3)
    else:
        search_tool = None
except ImportError:
    search_tool = None

def fallback_web_search(query: str) -> str:
    """
    Perform a fallback web search using Tavily when internal RAG context is insufficient.
    Returns a string of results or a message if unavailable.
    """
    if search_tool is None or not TAVILY_API_KEY:
        return "Web search is currently unavailable (TAVILY_API_KEY not configured or library missing)."
        
    try:
        results = search_tool.invoke({"query": query})
        
        # Tavily returns a list of dicts. We format it into readable text.
        formatted_results = []
        if isinstance(results, list):
            for res in results:
                title = res.get("title", "No Title")
                content = res.get("content", "")
                url = res.get("url", "")
                formatted_results.append(f"Source: {title} ({url})\nContent: {content}")
            return "\n\n".join(formatted_results)
        return str(results)
    except Exception as e:
        return f"Web search failed: {str(e)}"
