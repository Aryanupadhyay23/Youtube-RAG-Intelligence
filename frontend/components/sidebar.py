import os
import streamlit as st
from frontend.utils.constants import APP_TITLE, APP_CAPTION
from frontend.services.chat_storage import create_new_chat, switch_chat, delete_current_chat
from frontend.services.api_client import check_api_health


def _render_backend_status():
    """Display backend service status badge in sidebar."""
    api_online = check_api_health()
    if api_online:
        st.success("🟢 Backend API Online", icon="✅")
    else:
        st.warning("🟠 Backend API Offline (Port 8000)", icon="⚠️")


def render_sidebar():
    """Render application sidebar with settings, video input, and chat sessions."""
    with st.sidebar:
        st.title(f"▶️ {APP_TITLE}")
        st.caption(APP_CAPTION)
        st.divider()

        # Backend API Status Badge
        _render_backend_status()
        st.divider()

        # Video URL Input
        video_url = st.text_input(
            "YouTube URL",
            placeholder="https://youtube.com/watch?v=…",
        )
        load_button = st.button("🚀 Load Video", type="primary", use_container_width=True)
        st.divider()

        # Chat Session Management
        if st.button("➕ New Chat", use_container_width=True):
            create_new_chat()
            st.rerun()

        if st.session_state.get("all_chats"):
            st.subheader("💬 Chats")
            for chat_id, chat_data in sorted(st.session_state.all_chats.items(), reverse=True):
                is_current = chat_id == st.session_state.get("current_chat_id")
                label = f"▸ {chat_data['title']}" if is_current else chat_data["title"]

                if st.button(
                    label,
                    key=f"btn_{chat_id}",
                    type="primary" if is_current else "secondary",
                    use_container_width=True,
                ):
                    switch_chat(chat_id)
                    st.rerun()

        if st.session_state.get("current_chat_id"):
            st.divider()
            if st.button("🗑️ Delete Current Chat", use_container_width=True):
                delete_current_chat()
                st.rerun()

    return video_url, load_button
