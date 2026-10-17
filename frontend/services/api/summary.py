import requests
from typing import Generator, Dict
from frontend.services.api.common import API_BASE_URL, _http_error, _iter_sse


def stream_summary(transcript_text: str) -> Generator[Dict[str, str], None, None]:
    """Stream Server-Sent Events (status, token, error) from backend /summary/stream."""
    payload = {"transcript_text": transcript_text}
    try:
        with requests.post(
            f"{API_BASE_URL}/summary/stream",
            json=payload,
            stream=True,
            timeout=180,
        ) as response:
            if response.status_code != 200:
                yield {"type": "error", "value": _http_error(response)}
                return
            yield from _iter_sse(response)
    except requests.exceptions.ConnectionError:
        yield {"type": "error", "value": f"Cannot connect to backend at {API_BASE_URL}. Is it running?"}
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
        raise ConnectionError(f"Cannot connect to backend at {API_BASE_URL}. Is it running?") from None
    except requests.exceptions.Timeout:
        raise TimeoutError("Summary request timed out after 3 minutes. Try again.") from None
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        raise RuntimeError(f"Backend error (HTTP {e.response.status_code}): {detail}") from e
