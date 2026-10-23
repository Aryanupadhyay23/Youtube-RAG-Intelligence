import logging
import re
from fastapi import APIRouter, Request
from backend.routes.redis.schemas import CreateChatRequest, AddMessageRequest
from backend.utils.youtube import VIDEO_ID_REGEX
from backend.services.redis import redis_memory, clean_username

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Conversation Memory"])


@router.get("/api/memory/health")
def memory_health():
    """Check connectivity and authentication with Upstash Redis memory."""
    is_live = redis_memory.ping()
    return {
        "status": "online" if is_live else "offline",
        "configured": redis_memory.is_configured,
        "provider": "Upstash Redis REST",
    }


@router.get("/api/chats")
def list_chats(video_id: str = "", username: str = "default"):
    """List all chat sessions for a video and user stored in Redis, or all user sessions if video_id is not specified."""
    if not video_id:
        return {"chats": redis_memory.list_all_user_sessions(username=username)}
    return {"chats": redis_memory.list_sessions(video_id, username=username)}


@router.post("/api/chats")
def create_chat(req: CreateChatRequest):
    """Create or register a chat session in Redis."""
    session = redis_memory.create_session(req.video_id, req.chat_id, req.title, username=req.username)
    return {"status": "created", "session": session}


@router.get("/api/chats/{chat_id}")
def get_chat_history(chat_id: str, video_id: str = "", username: str = "default"):
    """Retrieve all message turns for a chat session from Redis scoped to user."""
    session = (
        redis_memory.get_session(video_id, chat_id, username=username)
        if video_id
        else redis_memory.get_user_session(chat_id, username=username)
    )
    if not session:
        return {"chat_id": chat_id, "messages": [], "session": None}
    messages = redis_memory.get_messages(chat_id)
    return {"chat_id": chat_id, "messages": messages, "session": session}


@router.post("/api/chats/{chat_id}/messages")
def save_message_turn(chat_id: str, req: AddMessageRequest):
    """Explicitly save a turn to Redis."""
    turn = redis_memory.append_turn(
        video_id=req.video_id,
        chat_id=chat_id,
        user_query=req.user,
        ai_response=req.ai,
        username=req.username,
    )
    return {"status": "saved", "turn": turn}


@router.delete("/api/chats/{chat_id}")
def delete_chat_session(chat_id: str, request: Request, video_id: str = "", username: str = "default"):
    """Delete a chat session, its messages, and its LangGraph checkpointer state from Redis."""
    redis_memory.delete_session(video_id, chat_id, username=username)
    # The LangGraph thread_id is only well-defined for a validated video id;
    # building it from anything else would orphan the checkpointer state.
    clean_user = clean_username(username)
    if video_id and re.fullmatch(VIDEO_ID_REGEX, video_id):
        thread_id = f"{clean_user}_{video_id}_{chat_id}"
        checkpointer = getattr(request.app.state, "checkpointer", None)
        if not checkpointer:
            try:
                from backend.core.checkpointer import get_redis_checkpointer

                checkpointer = get_redis_checkpointer()
                request.app.state.checkpointer = checkpointer
            except Exception as e:
                logger.warning(f"Could not load checkpointer: {e}")
        if checkpointer and hasattr(checkpointer, "delete_thread"):
            try:
                checkpointer.delete_thread(thread_id)
            except Exception as e:
                logger.warning(f"Failed to delete checkpointer thread {thread_id}: {e}")
    return {"status": "deleted", "chat_id": chat_id}


@router.delete("/api/chats")
def clear_all_chats(video_id: str = "", username: str = "default"):
    """Clear all chat sessions for a video and user, or for the whole user when video_id is empty."""
    if video_id:
        redis_memory.clear_video_sessions(video_id, username=username)
    else:
        for session in redis_memory.list_all_user_sessions(username=username):
            chat = session.get("chat_id")
            vid = session.get("video_id")
            if chat and vid:
                redis_memory.delete_session(vid, chat, username=username)
    return {"status": "cleared", "video_id": video_id}
