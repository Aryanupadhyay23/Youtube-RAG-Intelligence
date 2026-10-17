import requests
from typing import Generator, Dict, List
from frontend.services.api.common import API_BASE_URL, _http_error, _iter_sse


def stream_chat(
    video_id: str,
    chat_id: str,
    query: str,
    chat_history: List[Dict[str, str]],
    username: str = "default",
) -> Generator[Dict[str, str], None, None]:
    """Stream Server-Sent Events (status, token, error) from backend /chat/stream."""
    payload = {
        "video_id": video_id,
        "chat_id": chat_id,
        "query": query,
        "chat_history": chat_history,
        "username": username or "default",
    }

    try:
        with requests.post(
            f"{API_BASE_URL}/chat/stream",
            json=payload,
            stream=True,
            timeout=120,
        ) as response:
            if response.status_code != 200:
                yield {"type": "error", "value": _http_error(response)}
                return
            yield from _iter_sse(response)
    except requests.exceptions.ConnectionError:
        yield {"type": "error", "value": f"Could not connect to backend at {API_BASE_URL}. Is it running?"}
    except requests.exceptions.Timeout:
        yield {"type": "error", "value": "Request timed out. The backend may be overloaded. Try again."}
    except Exception as e:
        yield {"type": "error", "value": str(e)}
