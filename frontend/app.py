import sys
from pathlib import Path

# Ensure project root is in sys.path regardless of execution directory
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st
import requests

from frontend.utils.constants import APP_TITLE, APP_CAPTION
from frontend.utils.youtube import extract_video_id
from frontend.utils.session import initialize_session, reset_video_state
from frontend.utils.timestamp import format_time
from frontend.services.chat_storage import initialize_chat_state
from frontend.services.api_client import initialize_video, check_api_health
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
    initial_sidebar_state="expanded",
)


def _load_styles():
    """Inject Tailwind CSS v3 CDN and custom Streamlit widget styles."""
    tailwind_cdn = """
    <!-- Tailwind CSS v3 CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/tailwindcss/2.2.19/tailwind.min.css">
    <script>
        try {
            if (window.parent && window.parent.document) {
                if (!window.parent.document.getElementById('tailwind-cdn')) {
                    var s = window.parent.document.createElement('script');
                    s.id = 'tailwind-cdn';
                    s.src = 'https://cdn.tailwindcss.com';
                    window.parent.document.head.appendChild(s);
                }
            }
        } catch(e) {}
    </script>
    """
    st.markdown(tailwind_cdn, unsafe_allow_html=True)

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
        status_html = '<span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-950/70 text-emerald-400 border border-emerald-500/30 shadow-sm shadow-emerald-500/10"><span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>Backend Online</span>'
    else:
        status_html = '<span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-950/70 text-rose-400 border border-rose-500/30 shadow-sm shadow-rose-500/10"><span class="w-2 h-2 rounded-full bg-rose-400"></span>Backend Offline</span>'

    title = metadata.get("title", "YouTube Video")
    author = metadata.get("author", "Unknown Channel")
    thumb_url = metadata.get("thumbnail") or f"https://img.youtube.com/vi/{vid_id}/hqdefault.jpg"

    card_html = f"""<div class="flex flex-col md:flex-row items-center gap-5 p-5 rounded-2xl bg-slate-900/80 border border-blue-500/20 backdrop-blur-xl shadow-xl shadow-blue-950/30 mb-6 transition-all duration-300 hover:border-blue-500/40">
<div class="w-full md:w-56 h-32 flex-shrink-0 overflow-hidden rounded-xl border border-blue-500/25 shadow-md bg-black">
<img src="{thumb_url}" class="w-full h-full object-cover" alt="Video Thumbnail" />
</div>
<div class="flex-1 min-w-0">
<h3 class="text-xl font-bold text-white tracking-tight truncate mb-2">{title}</h3>
<div class="flex flex-wrap items-center gap-2 mb-3">
<span class="inline-flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-medium bg-blue-950/60 text-blue-300 border border-blue-500/20 shadow-sm">📺 {author}</span>
<span class="inline-flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-medium bg-blue-950/60 text-blue-300 border border-blue-500/20 shadow-sm">📊 {len(segments):,} segments</span>
<span class="inline-flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-medium bg-blue-950/60 text-blue-300 border border-blue-500/20 shadow-sm">📝 ~{words:,} words</span>
{status_html}
</div>
<a href="https://www.youtube.com/watch?v={vid_id}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white shadow-md shadow-blue-600/30 transition-all duration-200 hover:-translate-y-0.5 no-underline">▶ Watch on YouTube</a>
</div>
</div>"""
    st.markdown(card_html, unsafe_allow_html=True)

    # Embedded Interactive Video Player
    current_seek = int(st.session_state.get("player_start_time", 0))
    with st.expander(f"🎬 Video Player • Seek Time: {format_time(current_seek)}", expanded=False):
        col_vid_player, col_vid_actions = st.columns([3, 1])
        with col_vid_player:
            st.video(f"https://www.youtube.com/watch?v={vid_id}", start_time=current_seek)
        with col_vid_actions:
            st.markdown(f"**Current Position:** `{format_time(current_seek)}`")
            st.caption("Seek timestamp updates automatically when clicking timestamps in transcript explorer or citations.")
            if current_seek > 0:
                if st.button("⏮️ Play from 00:00", key="global_reset_seek", use_container_width=True):
                    st.session_state.player_start_time = 0
                    st.rerun()

    # Feature Tabs
    tab_chat, tab_summary, tab_transcript = st.tabs(["💬 Hybrid RAG Chat", "📝 Deep Summary", "📄 Transcript Explorer"])
    with tab_chat:
        render_chat_ui()
    with tab_summary:
        render_summary_ui()
    with tab_transcript:
        render_transcript_ui()

else:
    render_landing_page()
