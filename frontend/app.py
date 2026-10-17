import sys
from pathlib import Path

# Ensure project root is in sys.path regardless of execution directory
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from frontend.utils.constants import APP_TITLE
from frontend.utils.session import initialize_session, reset_video_state
from frontend.utils.timestamp import format_time
from frontend.services.chat_storage import initialize_chat_state
from frontend.services.api import check_api_health
from frontend.components.sidebar import render_sidebar
from frontend.components.landing import render_landing_page
from frontend.components.chat import render_chat_ui
from frontend.components.summary import render_summary_ui
from frontend.components.transcript import render_transcript_ui

# Page Configuration
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="▶️",
    layout="wide",
    initial_sidebar_state="auto",
)


def _load_styles():
    """Inject custom styles for clean typography, dark theme, and glassmorphism."""
    css_path = Path(__file__).resolve().parent / "assets" / "styles.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


_load_styles()
initialize_session()
initialize_chat_state()

# Render Sidebar
render_sidebar()

# Main Content View
if st.session_state.get("video_id") and st.session_state.get("transcript_text"):
    metadata = st.session_state.get("metadata", {})
    vid_id = st.session_state.video_id
    segments = st.session_state.get("transcript_segments", [])
    words = len(st.session_state.transcript_text.split())

    # Backend status badge (compact, inline using Tailwind)
    api_online = check_api_health()
    if api_online:
        status_html = '<span style="display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; background: rgba(6, 78, 59, 0.4); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3);">🟢 Online</span>'
    else:
        status_html = '<span style="display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; background: rgba(136, 19, 55, 0.4); color: #fb7185; border: 1px solid rgba(244, 63, 94, 0.3);">🔴 Offline</span>'

    title = metadata.get("title", "YouTube Video")
    author = metadata.get("author", "Unknown Channel")
    thumb_url = metadata.get("thumbnail") or f"https://img.youtube.com/vi/{vid_id}/hqdefault.jpg"

    col_header_card, col_header_switch = st.columns([5.5, 1.2])
    with col_header_card:
        card_html = f"""
        <div style="display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 8px 14px; border-radius: 12px; background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(59, 130, 246, 0.2); box-shadow: 0 4px 16px rgba(0,0,0,0.25);">
            <div style="display: flex; align-items: center; gap: 12px; min-width: 0; flex: 1;">
                <img src="{thumb_url}" style="width: 72px; height: 42px; object-fit: cover; border-radius: 6px; border: 1px solid rgba(59, 130, 246, 0.25); flex-shrink: 0;" alt="Video Thumbnail" />
                <div style="min-width: 0; flex: 1;">
                    <div style="font-weight: 700; font-size: 0.95rem; color: #ffffff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; line-height: 1.3;" title="{title}">{title}</div>
                    <div style="font-size: 0.75rem; color: #94a3b8; display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 2px;">
                        <span style="color: #cbd5e1; font-weight: 500;">📺 {author}</span>
                        <span>•</span>
                        <span>{len(segments):,} segments</span>
                        <span>•</span>
                        <span>~{words:,} words</span>
                        <span>•</span>
                        {status_html}
                    </div>
                </div>
            </div>
            <a href="https://www.youtube.com/watch?v={vid_id}" target="_blank" rel="noopener noreferrer" style="display: inline-flex; align-items: center; gap: 5px; padding: 6px 14px; border-radius: 8px; font-size: 0.78rem; font-weight: 600; background: rgba(37, 99, 235, 0.2); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); text-decoration: none; flex-shrink: 0;" title="Open on YouTube">
                ▶ Watch on YouTube
            </a>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

    with col_header_switch:
        if st.button("🔄 Switch Video", key="top_switch_video", type="secondary", use_container_width=True, help="Clear active video and load a new YouTube video link"):
            reset_video_state()
            st.session_state.pop("main_url_field", None)
            st.rerun()

    # Embedded Interactive Video Player
    current_seek = int(st.session_state.get("player_start_time", 0))
    with st.expander(f"🎬 Video Player • Position: {format_time(current_seek)}", expanded=False):
        col_vid_player, col_vid_actions = st.columns([3, 1])
        with col_vid_player:
            st.video(f"https://www.youtube.com/watch?v={vid_id}", start_time=current_seek)
        with col_vid_actions:
            st.markdown(f"**Current Position:** `{format_time(current_seek)}`")
            st.caption("Seek timestamp updates automatically when clicking timestamps in transcript or answers.")
            if current_seek > 0:
                if st.button("⏮️ Play from 00:00", key="global_reset_seek", use_container_width=True):
                    st.session_state.player_start_time = 0
                    st.rerun()

    # Feature Tabs (Clean, descriptive, no jargon)
    tab_chat, tab_summary, tab_transcript = st.tabs(["💬 Ask Questions", "📝 Summary", "📄 Transcript"])
    with tab_chat:
        render_chat_ui()
    with tab_summary:
        render_summary_ui()
    with tab_transcript:
        render_transcript_ui()

else:
    render_landing_page()
