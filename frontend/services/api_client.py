import os
import json
import requests
import streamlit as st
from typing import Generator, Dict, Any, List

API_BASE_URL = os.environ.get("BACKEND_API_URL", "http://127.0.0.1:8000")


@st.cache_data(ttl=10, show_spinner=False)
def check_api_health() -> bool:
    """Check if the backend FastAPI service is reachable (cached for 10s)."""
    try:
        r = requests.get(f"{API_BASE_URL}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def fetch_log_dates() -> List[str]:
    """Retrieve list of dates for which log files exist."""
    try:
        r = requests.get(f"{API_BASE_URL}/api/logs/dates", timeout=3)
        if r.status_code == 200:
            return r.json().get("dates", [])
    except Exception:
        pass
    # Local fallback
    try:
        from backend.utils.logger import get_available_log_dates
        return get_available_log_dates()
    except Exception:
        return []


def fetch_markdown_logs(date_str: str = "", level_filter: str = "", search_query: str = "") -> str:
    """Fetch logs formatted directly in Markdown with local fallback."""
    params = {}
    if date_str:
        params["date"] = date_str
    if level_filter:
        params["level"] = level_filter
    if search_query:
        params["query"] = search_query

    try:
        r = requests.get(f"{API_BASE_URL}/api/logs", params=params, timeout=5)
        if r.status_code == 200:
            return r.json().get("markdown", "")
    except Exception:
        pass

    # Local fallback
    try:
        from backend.utils.logger import get_datewise_logs_markdown
        return get_datewise_logs_markdown(
            date_str=date_str or None,
            level_filter=level_filter or None,
            search_query=search_query,
        )
    except Exception as e:
        return f"⚠️ Unable to retrieve logs: {e}"



def initialize_video(
    video_id: str,
    transcript_segments: list = None,
    transcript_text: str = "",
) -> Dict[str, Any]:
    """Call backend /init to fetch transcript & metadata and build hybrid vector stores."""
    payload = {
        "video_id": video_id,
        "transcript_text": transcript_text or "",
        "transcript_segments": transcript_segments or [],
    }
    r = requests.post(f"{API_BASE_URL}/init", json=payload, timeout=180)
    r.raise_for_status()
    return r.json()


def reset_backend_video(video_id: str = ""):
    """Notify backend to evict the in-memory vector store and immediately free RAM."""
    try:
        requests.post(f"{API_BASE_URL}/reset?video_id={video_id}", timeout=5)
    except Exception:
        pass


def stream_chat(
    video_id: str,
    chat_id: str,
    query: str,
    chat_history: List[Dict[str, str]],
) -> Generator[Dict[str, str], None, None]:
    """
    Stream Server-Sent Events (status, token, error) from backend /chat/stream.
    Yields dict with 'type' and 'value'.
    """
    payload = {
        "video_id": video_id,
        "chat_id": chat_id,
        "query": query,
        "chat_history": chat_history,
    }

    try:
        with requests.post(
            f"{API_BASE_URL}/chat/stream",
            json=payload,
            stream=True,
            timeout=120,
        ) as response:
            if response.status_code != 200:
                try:
                    err_json = response.json()
                    err_msg = err_json.get("detail", err_json.get("error", f"HTTP {response.status_code}"))
                except Exception:
                    err_msg = f"Backend returned HTTP {response.status_code}"
                yield {"type": "error", "value": err_msg}
                return

            event_type = None
            for line in response.iter_lines():
                if not line:
                    continue
                decoded = line.decode("utf-8")

                if decoded.startswith("event: "):
                    event_type = decoded[7:].strip()
                elif decoded.startswith("data: "):
                    data_str = decoded[6:].strip()
                    if not data_str or data_str == "{}":
                        continue
                    try:
                        data = json.loads(data_str)
                        if event_type == "status":
                            yield {"type": "status", "value": data.get("message", "")}
                        elif event_type == "token":
                            yield {"type": "token", "value": data.get("token", "")}
                        elif event_type == "error":
                            yield {"type": "error", "value": data.get("error", "Unknown error")}
                    except json.JSONDecodeError:
                        pass
    except requests.exceptions.ConnectionError:
        yield {"type": "error", "value": "Could not connect to backend server. Is port 8000 running?"}
    except requests.exceptions.Timeout:
        yield {"type": "error", "value": "Request timed out. The backend may be overloaded. Try again."}
    except Exception as e:
        yield {"type": "error", "value": str(e)}


def stream_summary(transcript_text: str) -> Generator[Dict[str, str], None, None]:
    """
    Stream Server-Sent Events (status, token, error) from backend /summary/stream.
    Yields dict with 'type' and 'value'.
    """
    payload = {"transcript_text": transcript_text}
    try:
        with requests.post(
            f"{API_BASE_URL}/summary/stream",
            json=payload,
            stream=True,
            timeout=180,
        ) as response:
            if response.status_code != 200:
                try:
                    err_json = response.json()
                    err_msg = err_json.get("detail", err_json.get("error", f"HTTP {response.status_code}"))
                except Exception:
                    err_msg = f"Backend returned HTTP {response.status_code}"
                yield {"type": "error", "value": err_msg}
                return

            event_type = None
            for line in response.iter_lines():
                if not line:
                    continue
                decoded = line.decode("utf-8")

                if decoded.startswith("event: "):
                    event_type = decoded[7:].strip()
                elif decoded.startswith("data: "):
                    data_str = decoded[6:].strip()
                    if not data_str or data_str == "{}":
                        continue
                    try:
                        data = json.loads(data_str)
                        if event_type == "status":
                            yield {"type": "status", "value": data.get("message", "")}
                        elif event_type == "token":
                            yield {"type": "token", "value": data.get("token", "")}
                        elif event_type == "error":
                            yield {"type": "error", "value": data.get("error", "Unknown error")}
                    except json.JSONDecodeError:
                        pass
    except requests.exceptions.ConnectionError:
        yield {"type": "error", "value": "Cannot connect to backend server. Is it running on port 8000?"}
    except requests.exceptions.Timeout:
        yield {"type": "error", "value": "Summary request timed out after 3 minutes. Try again."}
    except Exception as e:
        yield {"type": "error", "value": str(e)}


def request_summary(transcript_text: str) -> str:
    """Call backend /summary to generate video summary synchronously."""
    payload = {"transcript_text": transcript_text}
    try:
        r = requests.post(f"{API_BASE_URL}/summary", json=payload, timeout=180)
        r.raise_for_status()
        result = r.json()
        return result.get("summary", "")
    except requests.exceptions.ConnectionError:
        raise ConnectionError("Cannot connect to backend server. Is it running on port 8000?")
    except requests.exceptions.Timeout:
        raise TimeoutError("Summary request timed out after 3 minutes. Try again.")
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        raise RuntimeError(f"Backend error (HTTP {e.response.status_code}): {detail}")
