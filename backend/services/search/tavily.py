"""Web search used when a video does not contain the answer."""

from langchain_tavily import TavilySearch

from backend.config import TAVILY_API_KEY


async def fallback_web_search(query: str) -> str:
    """Run a web search through Tavily and return readable results."""
    if not TAVILY_API_KEY:
        return "Web search is currently unavailable (TAVILY_API_KEY not configured)."

    try:
        tool = TavilySearch(max_results=3, tavily_api_key=TAVILY_API_KEY)
        response = await tool.ainvoke({"query": query})
        items = response.get("results", []) if isinstance(response, dict) else response

        if not items:
            return f"No web search results found for '{query}'."

        formatted = [
            f"Source: {item.get('title', 'Web')} ({item.get('url', '')})\nContent: {item.get('content', '')}"
            for item in items
            if isinstance(item, dict)
        ]
        return "\n\n".join(formatted)

    except Exception as e:
        return f"Web search failed: {e}"
