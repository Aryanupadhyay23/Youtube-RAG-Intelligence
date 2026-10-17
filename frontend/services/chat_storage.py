import time
import uuid
import streamlit as st
from frontend.services.api import (
    get_remote_chats,
    get_remote_chat_history,
    create_remote_chat,
    delete_remote_chat,
)


def get_current_username() -> str:
    """Retrieve the normalized active username (defaulting to 'default')."""
    raw = st.session_state.get("username") or "default"
    cleaned = raw.strip().lower()
    if not cleaned or cleaned in ("guest", "none", "null"):
        return "default"
    return cleaned


def create_new_chat():
    """Create a new chat session with a globally unique ID and persist to memory."""
    unique_suffix = uuid.uuid4().hex[:8]
    chat_id = f"chat_{int(time.time())}_{unique_suffix}"
    if "all_chats" not in st.session_state:
        st.session_state.all_chats = {}

    st.session_state.all_chats[chat_id] = {
        "title": "New Chat",
        "messages": [],
        "created_at": time.strftime("%H:%M"),
    }
    st.session_state.current_chat_id = chat_id
    st.session_state.chat_history = []

    # Notify backend / Redis
    video_id = st.session_state.get("video_id")
    if video_id:
        create_remote_chat(
            video_id=video_id,
            chat_id=chat_id,
            title="New Chat",
            username=get_current_username(),
        )


def switch_chat(chat_id: str):
    """Switch active chat to another session, loading history from Redis if needed."""
    st.session_state.current_chat_id = chat_id
    chat_info = st.session_state.all_chats.get(chat_id, {})
    messages = chat_info.get("messages", [])

    # If messages are not cached in session, fetch from Redis backend
    if not messages:
        video_id = st.session_state.get("video_id", "")
        remote_messages = get_remote_chat_history(
            chat_id,
            video_id=video_id,
            username=get_current_username(),
        )
        if remote_messages:
            messages = remote_messages
            if chat_id in st.session_state.all_chats:
                st.session_state.all_chats[chat_id]["messages"] = messages

    st.session_state.chat_history = messages


def save_current_chat(messages: list):
    """Save message history for current active chat in local session state."""
    current_chat_id = st.session_state.get("current_chat_id")
    if not current_chat_id:
        return

    if "all_chats" not in st.session_state:
        st.session_state.all_chats = {}

    if current_chat_id not in st.session_state.all_chats:
        st.session_state.all_chats[current_chat_id] = {
            "title": "New Chat",
            "messages": [],
            "created_at": time.strftime("%H:%M"),
        }

    st.session_state.all_chats[current_chat_id]["messages"] = messages
    if messages:
        first_q = messages[0].get("user", "")
        title = (first_q[:35] + "...") if len(first_q) > 35 else first_q
        st.session_state.all_chats[current_chat_id]["title"] = title


def delete_chat(chat_id: str):
    """Delete a specific chat session from local session and Redis."""
    all_chats = st.session_state.get("all_chats", {})
    all_chats.pop(chat_id, None)

    video_id = st.session_state.get("video_id", "")
    if video_id:
        delete_remote_chat(
            chat_id,
            video_id=video_id,
            username=get_current_username(),
        )

    if chat_id == st.session_state.get("current_chat_id"):
        st.session_state.chat_history = []
        if all_chats:
            switch_chat(next(iter(all_chats)))
        else:
            create_new_chat()


def delete_current_chat():
    """Delete current active chat session."""
    current_chat_id = st.session_state.get("current_chat_id")
    if current_chat_id:
        delete_chat(current_chat_id)
    else:
        create_new_chat()


def switch_user(new_username: str):
    """Switch active user account and load that user's persistent chats from Redis."""
    cleaned = (new_username or "default").strip().lower()
    if not cleaned or cleaned in ("guest", "none", "null"):
        cleaned = "default"

    st.session_state.username = cleaned
    st.session_state.all_chats = {}
    st.session_state.chat_history = []
    st.session_state.current_chat_id = None
    st.session_state._memory_synced_video = None
    st.session_state._memory_synced_user = None

    # Load sessions for the selected user
    video_id = st.session_state.get("video_id")
    if video_id:
        remote_sessions = get_remote_chats(video_id, username=cleaned)
        if remote_sessions:
            for s in remote_sessions:
                c_id = s.get("chat_id")
                if c_id:
                    st.session_state.all_chats[c_id] = {
                        "title": s.get("title", "Chat"),
                        "messages": [],
                        "created_at": s.get("created_at", time.strftime("%H:%M")),
                    }
            newest_id = remote_sessions[0].get("chat_id")
            st.session_state.current_chat_id = newest_id
            switch_chat(newest_id)
        else:
            create_new_chat()
    else:
        create_new_chat()


def get_saved_user_sessions(username: str = "") -> list:
    """Retrieve all saved conversation sessions across all videos for a user."""
    user = username or get_current_username()
    return get_remote_chats("", username=user)


def initialize_chat_state():
    """Ensure chat session state is loaded from Upstash Redis for the active user."""
    if "all_chats" not in st.session_state:
        st.session_state.all_chats = {}

    video_id = st.session_state.get("video_id")
    username = get_current_username()
    last_synced_video = st.session_state.get("_memory_synced_video")
    last_synced_user = st.session_state.get("_memory_synced_user")

    # If video or user changed or not synced yet, reload persistent sessions from Redis
    if video_id and (video_id != last_synced_video or username != last_synced_user):
        remote_sessions = get_remote_chats(video_id, username=username)
        st.session_state.all_chats = {}
        target_chat = st.session_state.pop("target_chat_id", None)
        if remote_sessions:
            for s in remote_sessions:
                c_id = s.get("chat_id")
                if c_id:
                    st.session_state.all_chats[c_id] = {
                        "title": s.get("title", "Chat"),
                        "messages": [],
                        "created_at": s.get("created_at", time.strftime("%H:%M")),
                    }
            if target_chat and target_chat in st.session_state.all_chats:
                chosen_id = target_chat
            else:
                chosen_id = remote_sessions[0].get("chat_id")
            if chosen_id:
                st.session_state.current_chat_id = chosen_id
                switch_chat(chosen_id)
        else:
            create_new_chat()

        st.session_state._memory_synced_video = video_id
        st.session_state._memory_synced_user = username

    if not st.session_state.get("current_chat_id"):
        create_new_chat()


def format_chat_export(chat_history: list) -> str:
    """Format chat history into clean text for export."""
    lines = []
    for idx, turn in enumerate(chat_history, 1):
        lines.append(f"Turn {idx}\n\nYou: {turn['user']}\n\nAI: {turn['ai']}\n")
    return "\n".join(lines)
