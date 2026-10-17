import json
import time
import logging
from typing import List, Dict, Any, Optional
import requests

from backend.config import UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN
from backend.services.redis.utils import (
    SESSION_KEY_PREFIX,
    CHAT_KEY_PREFIX,
    USER_KEY_PREFIX,
    DEFAULT_TTL_SECONDS,
    clean_username,
)

logger = logging.getLogger(__name__)


class UpstashRedisMemoryService:
    """Manages persistent conversation memory using Upstash Redis REST API with username support and in-memory fallback."""

    def __init__(self, rest_url: Optional[str] = None, rest_token: Optional[str] = None):
        self.rest_url = (rest_url if rest_url is not None else (UPSTASH_REDIS_REST_URL or "")).rstrip("/")
        self.rest_token = rest_token if rest_token is not None else (UPSTASH_REDIS_REST_TOKEN or "")
        # Fallback memory keyed by (username, video_id)
        self._fallback_sessions: Dict[str, Dict[str, Any]] = {}
        self._fallback_messages: Dict[str, List[Dict[str, Any]]] = {}

    @property
    def is_configured(self) -> bool:
        return bool(self.rest_url and self.rest_token)

    def _execute(self, command: List[Any]) -> Optional[Any]:
        """Execute a single Redis command via Upstash REST API."""
        if not self.is_configured:
            return None

        headers = {
            "Authorization": f"Bearer {self.rest_token}",
            "Content-Type": "application/json",
        }
        try:
            resp = requests.post(
                self.rest_url,
                json=command,
                headers=headers,
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("result")
            else:
                logger.warning(f"Upstash Redis returned HTTP {resp.status_code}: {resp.text}")
                return None
        except Exception as e:
            logger.warning(f"Upstash Redis REST execution failed: {e}. Using in-memory fallback.")
            return None

    def ping(self) -> bool:
        """Check if Upstash Redis REST endpoint is reachable and authenticated."""
        if not self.is_configured:
            return False
        result = self._execute(["PING"])
        return result == "PONG"

    def _user_session_key(self, video_id: str, username: str = "default") -> str:
        u = clean_username(username)
        return f"{SESSION_KEY_PREFIX}:{u}:{video_id}"

    def _user_catalog_key(self, username: str = "default") -> str:
        u = clean_username(username)
        return f"{USER_KEY_PREFIX}:{u}:sessions"

    def list_sessions(self, video_id: str, username: str = "default") -> List[Dict[str, Any]]:
        """List all chat sessions for a specific video and user."""
        u = clean_username(username)
        key = self._user_session_key(video_id, u)
        if not self.is_configured:
            fb_key = f"{u}:{video_id}"
            sessions = self._fallback_sessions.get(fb_key, {})
            return sorted(sessions.values(), key=lambda s: s.get("updated_at", 0), reverse=True)

        res = self._execute(["HGETALL", key])
        if not res:
            return []

        sessions = []
        if isinstance(res, list):
            for i in range(0, len(res), 2):
                try:
                    val = json.loads(res[i + 1])
                    sessions.append(val)
                except Exception:
                    pass
        elif isinstance(res, dict):
            for val_str in res.values():
                try:
                    val = json.loads(val_str)
                    sessions.append(val)
                except Exception:
                    pass

        return sorted(sessions, key=lambda s: s.get("updated_at", 0), reverse=True)

    def list_all_user_sessions(self, username: str = "default") -> List[Dict[str, Any]]:
        """List all chat sessions across all videos for a given user from their catalog."""
        u = clean_username(username)
        cat_key = self._user_catalog_key(u)
        if not self.is_configured:
            all_sessions = []
            prefix = f"{u}:"
            for fb_key, sessions in self._fallback_sessions.items():
                if fb_key.startswith(prefix):
                    all_sessions.extend(sessions.values())
            return sorted(all_sessions, key=lambda s: s.get("updated_at", 0), reverse=True)

        res = self._execute(["HGETALL", cat_key])
        if not res:
            return []

        sessions = []
        if isinstance(res, list):
            for i in range(0, len(res), 2):
                try:
                    sessions.append(json.loads(res[i + 1]))
                except Exception:
                    pass
        elif isinstance(res, dict):
            for val_str in res.values():
                try:
                    sessions.append(json.loads(val_str))
                except Exception:
                    pass

        return sorted(sessions, key=lambda s: s.get("updated_at", 0), reverse=True)

    def get_session(self, video_id: str, chat_id: str, username: str = "default") -> Optional[Dict[str, Any]]:
        """Retrieve metadata for a specific session."""
        u = clean_username(username)
        key = self._user_session_key(video_id, u)
        if not self.is_configured:
            fb_key = f"{u}:{video_id}"
            return self._fallback_sessions.get(fb_key, {}).get(chat_id)

        res = self._execute(["HGET", key, chat_id])
        if res:
            try:
                return json.loads(res)
            except Exception:
                pass
        return None

    def create_session(
        self,
        video_id: str,
        chat_id: str,
        title: str = "New Chat",
        username: str = "default",
    ) -> Dict[str, Any]:
        """Create or register a chat session in Redis."""
        now = time.time()
        u = clean_username(username)
        session_data = {
            "chat_id": chat_id,
            "video_id": video_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
            "message_count": 0,
            "username": u,
        }
        val_str = json.dumps(session_data)

        if not self.is_configured:
            fb_key = f"{u}:{video_id}"
            if fb_key not in self._fallback_sessions:
                self._fallback_sessions[fb_key] = {}
            self._fallback_sessions[fb_key][chat_id] = session_data
            return session_data

        key = self._user_session_key(video_id, u)
        self._execute(["HSET", key, chat_id, val_str])
        self._execute(["EXPIRE", key, DEFAULT_TTL_SECONDS])

        cat_key = self._user_catalog_key(u)
        self._execute(["HSET", cat_key, chat_id, val_str])
        self._execute(["EXPIRE", cat_key, DEFAULT_TTL_SECONDS])

        return session_data

    def get_messages(self, chat_id: str, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """Retrieve stored message turns for a chat session from Redis."""
        key = f"{CHAT_KEY_PREFIX}:{chat_id}"
        if not self.is_configured:
            msgs = self._fallback_messages.get(chat_id, [])
            if limit:
                return msgs[-limit:]
            return msgs

        res = self._execute(["LRANGE", key, 0, -1])
        if not res or not isinstance(res, list):
            return []

        messages = []
        for item in res:
            try:
                turn = json.loads(item)
                messages.append(turn)
            except Exception:
                pass

        if limit:
            return messages[-limit:]
        return messages

    def append_turn(
        self,
        video_id: str,
        chat_id: str,
        user_query: str,
        ai_response: str,
        username: str = "default",
    ) -> Dict[str, str]:
        """Append a conversational turn to Redis."""
        now = time.time()
        u = clean_username(username)
        turn = {
            "user": user_query,
            "ai": ai_response,
            "timestamp": now,
        }
        turn_str = json.dumps(turn)

        # Update or register session metadata
        existing_session = self.get_session(video_id, chat_id, username=u)
        msg_count = (existing_session.get("message_count", 0) + 1) if existing_session else 1
        title = existing_session.get("title") if existing_session else None
        if not title or title == "New Chat":
            title = user_query[:45].strip() + ("..." if len(user_query) > 45 else "")

        session_data = {
            "chat_id": chat_id,
            "video_id": video_id,
            "title": title,
            "created_at": existing_session.get("created_at", now) if existing_session else now,
            "updated_at": now,
            "message_count": msg_count,
            "username": u,
        }
        val_str = json.dumps(session_data)

        if not self.is_configured:
            if chat_id not in self._fallback_messages:
                self._fallback_messages[chat_id] = []
            self._fallback_messages[chat_id].append(turn)
            fb_key = f"{u}:{video_id}"
            if fb_key not in self._fallback_sessions:
                self._fallback_sessions[fb_key] = {}
            self._fallback_sessions[fb_key][chat_id] = session_data
            return turn

        chat_key = f"{CHAT_KEY_PREFIX}:{chat_id}"
        self._execute(["RPUSH", chat_key, turn_str])
        self._execute(["EXPIRE", chat_key, DEFAULT_TTL_SECONDS])

        sess_key = self._user_session_key(video_id, u)
        self._execute(["HSET", sess_key, chat_id, val_str])
        self._execute(["EXPIRE", sess_key, DEFAULT_TTL_SECONDS])

        cat_key = self._user_catalog_key(u)
        self._execute(["HSET", cat_key, chat_id, val_str])
        self._execute(["EXPIRE", cat_key, DEFAULT_TTL_SECONDS])

        return turn

    def delete_session(self, video_id: str, chat_id: str, username: str = "default") -> bool:
        """Delete a chat session and its stored message turns from Redis."""
        u = clean_username(username)
        if not self.is_configured:
            fb_key = f"{u}:{video_id}"
            if fb_key in self._fallback_sessions:
                self._fallback_sessions[fb_key].pop(chat_id, None)
            self._fallback_messages.pop(chat_id, None)
            return True

        chat_key = f"{CHAT_KEY_PREFIX}:{chat_id}"
        self._execute(["DEL", chat_key])

        if video_id:
            sess_key = self._user_session_key(video_id, u)
            self._execute(["HDEL", sess_key, chat_id])

        cat_key = self._user_catalog_key(u)
        self._execute(["HDEL", cat_key, chat_id])

        return True

    def clear_video_sessions(self, video_id: str, username: str = "default") -> bool:
        """Delete all chat sessions for a video and user."""
        u = clean_username(username)
        sessions = self.list_sessions(video_id, username=u)
        for s in sessions:
            c_id = s.get("chat_id")
            if c_id:
                self.delete_session(video_id, c_id, username=u)
        return True


# Singleton instance shared across FastAPI application
redis_memory = UpstashRedisMemoryService()
