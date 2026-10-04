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
    """Reset all video, transcript, chat, and summary state to return to landing page."""
    st.session_state.video_id = None
    st.session_state.metadata = None
    st.session_state.transcript_text = None
    st.session_state.transcript_segments = None
    st.session_state.summary = None
    st.session_state.chat_history = []
    st.session_state.pending_question = None
    st.session_state.submitted_video_url = None
    st.session_state.all_chats = {}
    st.session_state.current_chat_id = "default_chat"
    st.session_state.transcript_display_limit = 60
