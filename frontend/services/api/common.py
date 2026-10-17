import os
import json
import requests
from typing import Generator, Dict

API_BASE_URL = os.environ.get("BACKEND_API_URL", "http://127.0.0.1:8000")


def _http_error(response: requests.Response) -> str:
    """Extract a descriptive error message from a non-200 streaming response."""
    try:
        err_json = response.json()
        return err_json.get("detail", err_json.get("error", f"HTTP {response.status_code}"))
    except Exception:
        return f"Backend returned HTTP {response.status_code}"


def _iter_sse(response: requests.Response) -> Generator[Dict[str, str], None, None]:
    """Parse a Server-Sent Events stream into {'type', 'value'} dicts (status/token/error)."""
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
            except json.JSONDecodeError:
                continue

            if event_type == "status":
                yield {"type": "status", "value": data.get("message", "")}
            elif event_type == "token":
                yield {"type": "token", "value": data.get("token", "")}
            elif event_type == "error":
                yield {"type": "error", "value": data.get("error", "Unknown error")}
