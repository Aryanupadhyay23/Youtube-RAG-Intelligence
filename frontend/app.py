import streamlit as st
from frontend.utils.constants import APP_TITLE, APP_CAPTION
from frontend.utils.youtube import extract_video_id
from frontend.utils.session import initialize_session, reset_video_state
from frontend.services.chat_storage import initialize_chat_state
from frontend.services.api_client import initialize_video
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
    """Inject custom CSS stylesheet."""
    try:
        with open("frontend/assets/styles.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass


_load_styles()
initialize_session()
initialize_chat_state()

# Render Sidebar
video_url, load_button = render_sidebar()

# Handle Video Load
if load_button:
    if not video_url or not video_url.strip():
        st.warning("⚠️ Please enter a YouTube URL.")
    else:
        video_id = extract_video_id(video_url)
        if not video_id:
            st.warning("⚠️ Invalid YouTube URL. Please provide a valid watch, embed, or shorts link.")
        else:
            reset_video_state()
            with st.status("Loading video…", expanded=True) as status:
                try:
                    st.write("🔌 Fetching transcript and initializing vector index via backend…")
                    init_data = initialize_video(video_id)

                    metadata = init_data.get("metadata", {})
                    transcript_text = init_data.get("transcript_text", "")
                    transcript_segments = init_data.get("transcript_segments", [])

                    if not transcript_text:
                        raise ValueError("No transcript could be retrieved for this video.")

                    # Update Session State
                    st.session_state.video_id = video_id
                    st.session_state.metadata = metadata
                    st.session_state.transcript_text = transcript_text
                    st.session_state.transcript_segments = transcript_segments

                    status.update(label="✅ Video loaded successfully.", state="complete", expanded=False)
                    st.rerun()

                except Exception as error:
                    status.update(label="❌ Failed to load video.", state="error", expanded=True)
                    st.error(str(error))

# Main Content View
if st.session_state.get("video_id") and st.session_state.get("transcript_text"):
    metadata = st.session_state.get("metadata", {})
    col_thumb, col_info = st.columns([1, 4])

    with col_thumb:
        if metadata.get("thumbnail"):
            st.image(metadata["thumbnail"], use_container_width=True)

    with col_info:
        st.subheader(metadata.get("title", "YouTube Video"))
        st.caption(f"Channel: {metadata.get('author', 'Unknown')} • ID: `{st.session_state.video_id}`")

        segments = st.session_state.get("transcript_segments", [])
        words = len(st.session_state.transcript_text.split())
        st.caption(f"📊 {len(segments):,} segments • ~{words:,} spoken words")

    st.divider()

    # Feature Tabs
    tab_chat, tab_summary, tab_transcript = st.tabs(["💬 Chat", "📝 Summary", "📄 Transcript"])
    with tab_chat:
        render_chat_ui()
    with tab_summary:
        render_summary_ui()
    with tab_transcript:
        render_transcript_ui()

else:
    render_landing_page()
