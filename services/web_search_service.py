import os
import asyncio
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

async def fallback_web_search(query: str) -> str:
    """
    Perform an async fallback web search using Tavily.
    """
    if search_tool is None or not TAVILY_API_KEY:
        return "Web search is currently unavailable (TAVILY_API_KEY not configured or library missing)."
        
    try:
        results = await asyncio.to_thread(search_tool.invoke, {"query": query})
        
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
