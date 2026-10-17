import requests
from typing import Dict, Any, List
from frontend.services.api.common import API_BASE_URL


def check_memory_health() -> Dict[str, Any]:
    """Check backend Upstash Redis conversation memory health."""
    try:
        r = requests.get(f"{API_BASE_URL}/api/memory/health", timeout=3)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {"status": "offline", "configured": False}


def get_remote_chats(video_id: str = "", username: str = "default") -> List[Dict[str, Any]]:
    """Fetch stored chat sessions from Redis via backend API (for a video or across all user videos)."""
    try:
        params: Dict[str, str] = {"username": username or "default"}
        if video_id:
            params["video_id"] = video_id
        r = requests.get(
            f"{API_BASE_URL}/api/chats",
            params=params,
            timeout=4,
        )
        if r.status_code == 200:
            return r.json().get("chats", [])
    except Exception:
        pass
    return []


def get_remote_chat_history(chat_id: str, video_id: str = "", username: str = "default") -> List[Dict[str, str]]:
    """Fetch stored message turns for a chat session from Redis."""
    if not chat_id:
        return []
    try:
        r = requests.get(
            f"{API_BASE_URL}/api/chats/{chat_id}",
            params={"video_id": video_id, "username": username or "default"},
            timeout=4,
        )
        if r.status_code == 200:
            return r.json().get("messages", [])
    except Exception:
        pass
    return []


def create_remote_chat(
    video_id: str,
    chat_id: str,
    title: str = "New Chat",
    username: str = "default",
) -> Dict[str, Any]:
    """Register a new chat session in Redis via backend API."""
    try:
        payload = {
            "video_id": video_id,
            "chat_id": chat_id,
            "title": title,
            "username": username or "default",
        }
        r = requests.post(f"{API_BASE_URL}/api/chats", json=payload, timeout=4)
        if r.status_code == 200:
            return r.json().get("session", {})
    except Exception:
        pass
    return {}


def delete_remote_chat(chat_id: str, video_id: str = "", username: str = "default") -> bool:
    """Delete a chat session and its messages from Redis."""
    try:
        r = requests.delete(
            f"{API_BASE_URL}/api/chats/{chat_id}",
            params={"video_id": video_id, "username": username or "default"},
            timeout=4,
        )
        return r.status_code == 200
    except Exception:
        return False


def clear_remote_chats(video_id: str, username: str = "default") -> bool:
    """Clear all chat sessions for a video and user from Redis."""
    try:
        r = requests.delete(
            f"{API_BASE_URL}/api/chats",
            params={"video_id": video_id, "username": username or "default"},
            timeout=4,
        )
        return r.status_code == 200
    except Exception:
        return False
