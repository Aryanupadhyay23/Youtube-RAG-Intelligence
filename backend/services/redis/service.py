import json
import time
import logging
import threading
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
REDIS_RETRY_SECONDS = 5

# Race-safe: reads the existing session (from either hash), derives message_count /
# created_at / title, then pushes the turn and updates both hashes with fresh TTLs
# as a single atomic operation on the Redis side.
_APPEND_TURN_SCRIPT = """
local sess_key = KEYS[1]
local cat_key = KEYS[2]
local chat_key = KEYS[3]
local chat_id = ARGV[1]
local now = tonumber(ARGV[2])
local ttl = tonumber(ARGV[3])
local title = ARGV[4]
local video_id = ARGV[5]
local username = ARGV[6]
local turn_str = ARGV[7]

local msg_count = 1
local created_at = now
local existing = redis.call('HGET', sess_key, chat_id)
if not existing or existing == false then
    existing = redis.call('HGET', cat_key, chat_id)
end
if existing then
    local ok, data = pcall(cjson.decode, existing)
    if ok and type(data) == 'table' then
        msg_count = (tonumber(data.message_count) or 0) + 1
        if data.created_at then created_at = tonumber(data.created_at) end
        if data.title and data.title ~= '' and data.title ~= 'New Chat' then title = data.title end
    end
end
local session_data = cjson.encode({chat_id = chat_id, video_id = video_id, title = title,
    created_at = created_at, updated_at = now, message_count = msg_count, username = username})
redis.call('RPUSH', chat_key, turn_str)
redis.call('EXPIRE', chat_key, ttl)
redis.call('HSET', sess_key, chat_id, session_data)
redis.call('EXPIRE', sess_key, ttl)
redis.call('HSET', cat_key, chat_id, session_data)
redis.call('EXPIRE', cat_key, ttl)
return msg_count
"""


class UpstashRedisMemoryService:
    """Manages persistent conversation memory using Upstash Redis REST API with username support and in-memory fallback."""

    def __init__(self, rest_url: Optional[str] = None, rest_token: Optional[str] = None):
        self.rest_url = (rest_url if rest_url is not None else (UPSTASH_REDIS_REST_URL or "")).rstrip("/")
        self.rest_token = rest_token if rest_token is not None else (UPSTASH_REDIS_REST_TOKEN or "")
        # Fallback memory keyed by (username, video_id)
        self._fallback_sessions: Dict[str, Dict[str, Any]] = {}
        self._fallback_messages: Dict[str, List[Dict[str, Any]]] = {}
        self._fallback_lock = threading.Lock()
        # Keep configured Redis failures available in memory and replay mutations
        # after the endpoint becomes reachable again.
        self._redis_retry_after = 0.0
        self._redis_degraded = False
        self._fallback_data: Dict[str, Any] = {}
        self._fallback_writes: List[List[Any]] = []

    @property
    def is_configured(self) -> bool:
        return bool(self.rest_url and self.rest_token)

    def _execute(self, command: List[Any]) -> Optional[Any]:
        """Execute a single Redis command via Upstash REST API."""
        if not self.is_configured:
            return None

        if self._redis_degraded and command[0] != "PING":
            if time.monotonic() < self._redis_retry_after or not self._probe_and_replay():
                return self._execute_fallback(command)

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
                return self._handle_redis_failure(command)
        except Exception as e:
            logger.warning(f"Upstash Redis REST execution failed: {e}. Using in-memory fallback.")
            return self._handle_redis_failure(command)

    def _post_redis(self, command: List[Any]):
        """Make a Redis request without entering the fallback/retry machinery."""
        response = requests.post(
            self.rest_url,
            json=command,
            headers={
                "Authorization": f"Bearer {self.rest_token}",
                "Content-Type": "application/json",
            },
            timeout=5,
        )
        if response.status_code != 200:
            return False, None
        data = response.json()
        if data.get("error"):
            return False, None
        return True, data.get("result")

    def _handle_redis_failure(self, command: List[Any]) -> Optional[Any]:
        self._redis_degraded = True
        self._redis_retry_after = time.monotonic() + REDIS_RETRY_SECONDS
        return self._execute_fallback(command)

    def _probe_and_replay(self) -> bool:
        """Restore Redis and replay queued mutations before returning to it."""
        try:
            ok, result = self._post_redis(["PING"])
            if not ok or result != "PONG":
                self._redis_retry_after = time.monotonic() + REDIS_RETRY_SECONDS
                return False
            with self._fallback_lock:
                for command in self._fallback_writes:
                    replay_ok, _ = self._post_redis(command)
                    if not replay_ok:
                        self._redis_retry_after = time.monotonic() + REDIS_RETRY_SECONDS
                        return False
                self._fallback_writes.clear()
            self._redis_degraded = False
            return True
        except Exception as e:
            logger.warning(f"Upstash Redis recovery probe failed: {e}")
            self._redis_retry_after = time.monotonic() + REDIS_RETRY_SECONDS
            return False

    def _execute_fallback(self, command: List[Any]) -> Optional[Any]:
        """Execute the Redis command subset used here against process memory."""
        if not command:
            return None
        op = str(command[0]).upper()
        with self._fallback_lock:
            if op in {"PING", "EVAL"}:
                return None
            if op == "HGETALL":
                return dict(self._fallback_data.get(command[1], {}))
            if op == "HGET":
                return self._fallback_data.get(command[1], {}).get(command[2])
            if op == "LRANGE":
                items = list(self._fallback_data.get(command[1], []))
                start, end = int(command[2]), int(command[3])
                if end < 0:
                    end += len(items)
                return items[start : end + 1]
            if op == "HSET":
                key, field, value = command[1:4]
                self._fallback_data.setdefault(key, {})[field] = value
                self._fallback_writes.append(list(command))
                return 1
            if op == "HDEL":
                key, field = command[1:3]
                removed = self._fallback_data.get(key, {}).pop(field, None) is not None
                self._fallback_writes.append(list(command))
                return int(removed)
            if op == "RPUSH":
                key = command[1]
                self._fallback_data.setdefault(key, []).extend(command[2:])
                self._fallback_writes.append(list(command))
                return len(self._fallback_data[key])
            if op == "EXPIRE":
                self._fallback_writes.append(list(command))
                return 1
            if op == "DEL":
                removed = 0
                for key in command[1:]:
                    removed += int(key in self._fallback_data)
                    self._fallback_data.pop(key, None)
                self._fallback_writes.append(list(command))
                return removed
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
            with self._fallback_lock:
                sessions = dict(self._fallback_sessions.get(fb_key, {}))
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
            with self._fallback_lock:
                snapshot = {fb_key: dict(sessions) for fb_key, sessions in self._fallback_sessions.items()}
            for fb_key, sessions in snapshot.items():
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
            with self._fallback_lock:
                return self._fallback_sessions.get(fb_key, {}).get(chat_id)

        res = self._execute(["HGET", key, chat_id])
        if res:
            try:
                return json.loads(res)
            except Exception:
                pass
        return None

    def get_user_session(self, chat_id: str, username: str = "default") -> Optional[Dict[str, Any]]:
        """Retrieve metadata for a specific session scoped to a user."""
        u = clean_username(username)
        if not self.is_configured:
            prefix = f"{u}:"
            with self._fallback_lock:
                for fb_key, sessions in self._fallback_sessions.items():
                    if fb_key.startswith(prefix) and chat_id in sessions:
                        return sessions[chat_id]
            return None

        cat_key = self._user_catalog_key(u)
        res = self._execute(["HGET", cat_key, chat_id])
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
            with self._fallback_lock:
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
            with self._fallback_lock:
                msgs = list(self._fallback_messages.get(chat_id, []))
            if limit is not None:
                return msgs[-limit:] if limit > 0 else []
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

        if limit is not None:
            return messages[-limit:] if limit > 0 else []
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
            with self._fallback_lock:
                if chat_id not in self._fallback_messages:
                    self._fallback_messages[chat_id] = []
                self._fallback_messages[chat_id].append(turn)
                fb_key = f"{u}:{video_id}"
                if fb_key not in self._fallback_sessions:
                    self._fallback_sessions[fb_key] = {}
                self._fallback_sessions[fb_key][chat_id] = session_data
            return turn

        # Atomic path (single EVAL): push the turn and update both session hashes
        # in one operation so concurrent appends cannot lose message_count/title updates.
        chat_key = f"{CHAT_KEY_PREFIX}:{chat_id}"
        sess_key = self._user_session_key(video_id, u)
        cat_key = self._user_catalog_key(u)
        eval_result = self._execute(
            [
                "EVAL",
                _APPEND_TURN_SCRIPT,
                "3",
                sess_key,
                cat_key,
                chat_key,
                chat_id,
                str(now),
                str(DEFAULT_TTL_SECONDS),
                title,
                video_id,
                u,
                turn_str,
            ]
        )

        if eval_result is None:
            # EVAL unavailable/failed: keep the non-atomic legacy path as fallback.
            self._execute(["RPUSH", chat_key, turn_str])
            self._execute(["EXPIRE", chat_key, DEFAULT_TTL_SECONDS])
            self._execute(["HSET", sess_key, chat_id, val_str])
            self._execute(["EXPIRE", sess_key, DEFAULT_TTL_SECONDS])
            self._execute(["HSET", cat_key, chat_id, val_str])
            self._execute(["EXPIRE", cat_key, DEFAULT_TTL_SECONDS])

        return turn

    def delete_session(self, video_id: str, chat_id: str, username: str = "default") -> bool:
        """Delete a chat session and its stored message turns from Redis."""
        u = clean_username(username)
        if not self.is_configured:
            fb_key = f"{u}:{video_id}"
            with self._fallback_lock:
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
