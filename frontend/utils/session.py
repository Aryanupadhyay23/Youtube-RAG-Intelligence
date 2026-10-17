import socket
import streamlit as st

# Prioritize IPv4 addresses during DNS resolution to avoid 20-45s IPv6 SYN timeouts on Windows/cloud
def _enable_ipv4_preference():
    orig_getaddrinfo = socket.getaddrinfo
    def ipv4_preferred_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        try:
            res = orig_getaddrinfo(host, port, family, type, proto, flags)
            return sorted(res, key=lambda x: 0 if x[0] == socket.AF_INET else 1)
        except Exception:
            return orig_getaddrinfo(host, port, family, type, proto, flags)
    socket.getaddrinfo = ipv4_preferred_getaddrinfo

_enable_ipv4_preference()

SESSION_DEFAULTS = {
    "video_id": None,
    "metadata": None,
    "transcript_text": None,
    "transcript_segments": None,
    "summary": None,
    "chat_history": [],
    "current_chat_id": "default_chat",
    "player_start_time": 0,
    "username": "default",
}


def initialize_session():
    """Ensure all required session state variables exist with safe defaults."""
    for key, value in SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_video_state():
    """Reset all video, transcript, chat, and summary state to return to landing page.
    Backend cache is managed via TTL and LRU, so we don't evict shared video stores here.
    """
    st.session_state.video_id = None
    st.session_state.metadata = None
    st.session_state.transcript_text = None
    st.session_state.transcript_segments = None
    st.session_state.summary = None
    st.session_state.chat_history = []
    st.session_state.submitted_video_url = None
    st.session_state.all_chats = {}
    st.session_state.current_chat_id = "default_chat"
    st.session_state.transcript_display_limit = 60
    st.session_state.player_start_time = 0
    st.session_state._memory_synced_video = None
    st.session_state.prefill_url = ""

