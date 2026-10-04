import streamlit as st

SESSION_DEFAULTS = {
    "video_id": None,
    "metadata": None,
    "transcript_text": None,
    "transcript_segments": None,
    "summary": None,
    "chat_history": [],
    "pending_question": None,
    "current_chat_id": "default_chat",
}


def initialize_session():
    """Ensure all required session state variables exist with safe defaults."""
    for key, value in SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_video_state():
    """Clear chat history and summary when loading a new video."""
    st.session_state.chat_history = []
    st.session_state.summary = None
