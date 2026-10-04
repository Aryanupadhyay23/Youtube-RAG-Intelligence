import time
import streamlit as st


def create_new_chat():
    """Create a new chat session."""
    chat_id = f"chat_{int(time.time())}"
    if "all_chats" not in st.session_state:
        st.session_state.all_chats = {}

    st.session_state.all_chats[chat_id] = {
        "title": "New Chat",
        "messages": [],
        "created_at": time.strftime("%H:%M"),
    }
    st.session_state.current_chat_id = chat_id
    st.session_state.chat_history = []


def switch_chat(chat_id: str):
    """Switch active chat to another session."""
    st.session_state.current_chat_id = chat_id
    st.session_state.chat_history = st.session_state.all_chats.get(chat_id, {}).get("messages", [])


def save_current_chat(messages: list):
    """Save message history for current active chat."""
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


def delete_current_chat():
    """Delete current active chat session."""
    current_chat_id = st.session_state.get("current_chat_id")
    if current_chat_id and current_chat_id in st.session_state.all_chats:
        del st.session_state.all_chats[current_chat_id]

    st.session_state.chat_history = []
    if st.session_state.all_chats:
        switch_chat(list(st.session_state.all_chats.keys())[0])
    else:
        create_new_chat()


def initialize_chat_state():
    """Ensure at least one chat session exists."""
    if "all_chats" not in st.session_state:
        st.session_state.all_chats = {}
    if not st.session_state.get("current_chat_id"):
        create_new_chat()


def format_chat_export(chat_history: list) -> str:
    """Format chat history into clean text for export."""
    lines = []
    for idx, turn in enumerate(chat_history, 1):
        lines.append(f"Turn {idx}\n\nYou: {turn['user']}\n\nAI: {turn['ai']}\n")
    return "\n".join(lines)
