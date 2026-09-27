from config import TAVILY_API_KEY


async def fallback_web_search(query: str) -> str:
    """Perform an async fallback web search using Tavily."""
    if not TAVILY_API_KEY:
        return "Web search is currently unavailable (TAVILY_API_KEY not configured)."

    try:
        try:
            from langchain_tavily import TavilySearch
            tool = TavilySearch(max_results=3, tavily_api_key=TAVILY_API_KEY)
            response = await tool.ainvoke({"query": query})
            items = response.get("results", []) if isinstance(response, dict) else response
        except ImportError:
            from langchain_community.tools.tavily_search import TavilySearchResults
            tool = TavilySearchResults(max_results=3, tavily_api_key=TAVILY_API_KEY)
            items = await tool.ainvoke({"query": query})

        if not items:
            return f"No web search results found for '{query}'."

        formatted = [
            f"Source: {r.get('title', 'Web')} ({r.get('url', '')})\nContent: {r.get('content', '')}"
            for r in items if isinstance(r, dict)
        ]
        return "\n\n".join(formatted)

    except Exception as e:
        return f"Web search failed: {e}"
