import time

import streamlit as st

from config import (
    APP_TITLE,
    APP_CAPTION,
    GROQ_API_KEY,
    SUPADATA_KEYS,
)

from utils.session import (
    initialize_session,
    reset_video_state,
)

from services.youtube_service import (
    extract_video_id,
    get_video_metadata,
)

from services.transcript_service import (
    fetch_transcript,
)

from services.chat_service import (
    initialize_chat_state,
)

from core.llm import load_llm

from core.vectorstore import build_vector_store

from core.rag import build_rag_chain

from ui.sidebar import render_sidebar

from ui.chat_ui import render_chat_ui

from ui.summary_ui import render_summary_ui

from ui.transcript_ui import render_transcript_ui

from ui.landing import render_landing_page


st.set_page_config(
    page_title=APP_TITLE,
    page_icon="▶️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── inject CSS ────────────────────────────────────────────
def _load_css():
    try:
        with open("assets/styles.css") as f:
            st.markdown(
                f"<style>{f.read()}</style>",
                unsafe_allow_html=True,
            )
    except FileNotFoundError:
        pass

_load_css()

# ── session & sidebar ─────────────────────────────────────
initialize_session()
initialize_chat_state()

video_url, load_button = render_sidebar()

# ── page header ───────────────────────────────────────────
st.title(APP_TITLE)
st.caption(APP_CAPTION)
st.divider()

# ── load video ────────────────────────────────────────────
if load_button:

    if not GROQ_API_KEY:
        st.warning("⚠️ GROQ_API_KEY is missing.")

    elif not SUPADATA_KEYS:
        st.warning("⚠️ No Supadata keys found.")

    elif not video_url.strip():
        st.warning("⚠️ Please enter a YouTube URL.")

    else:

        video_id = extract_video_id(video_url)

        if not video_id:
            st.warning("⚠️ Invalid YouTube URL.")

        else:

            reset_video_state()

            with st.status(
                "Loading video…",
                expanded=True,
            ) as status:

                try:

                    st.write("📄 Fetching transcript…")
                    transcript_text, transcript_segments = fetch_transcript(video_id)

                    st.write("🎬 Fetching metadata…")
                    metadata = get_video_metadata(video_id)

                    st.write("🤖 Loading language model…")
                    llm = load_llm()

                    st.write("🗄️ Building vector database…")
                    vector_store = build_vector_store(transcript_text)

                    st.write("🔗 Creating RAG chain…")
                    rag_chain = build_rag_chain(vector_store, llm)

                    st.session_state.video_id = video_id
                    st.session_state.metadata = metadata
                    st.session_state.transcript_text = transcript_text
                    st.session_state.transcript_segments = transcript_segments
                    st.session_state.vector_store = vector_store
                    st.session_state.rag_chain = rag_chain
                    st.session_state.llm = llm

                    status.update(
                        label="✅ Video loaded successfully.",
                        state="complete",
                        expanded=False,
                    )

                    time.sleep(0.3)
                    st.rerun()

                except Exception as error:

                    status.update(
                        label="❌ Failed to load video.",
                        state="error",
                        expanded=False,
                    )

                    st.error("Could not load video.")

                    with st.expander("Error Details"):
                        st.code(str(error), language="text")

# ── main content ──────────────────────────────────────────
if st.session_state.video_id:

    metadata = st.session_state.metadata
    transcript_text = st.session_state.transcript_text
    transcript_segments = st.session_state.transcript_segments
    video_id = st.session_state.video_id

    col1, col2 = st.columns([1, 2])

    with col1:

        if metadata["thumbnail"]:
            st.image(
                metadata["thumbnail"],
                use_container_width=True,
            )

        st.link_button(
            "▶️ Watch on YouTube",
            f"https://youtube.com/watch?v={video_id}",
            use_container_width=True,
        )

    with col2:

        st.subheader(metadata["title"])
        st.caption(f"Channel: {metadata['author']}")

        total_seconds = (
            transcript_segments[-1]["start"]
            + transcript_segments[-1]["duration"]
            if transcript_segments
            else 0
        )

        word_count = len(transcript_text.split())

        m1, m2, m3 = st.columns(3)
        m1.metric("Duration", f"{int(total_seconds // 60)} min")
        m2.metric("Words", f"{word_count:,}")
        m3.metric("Segments", f"{len(transcript_segments):,}")

    st.divider()

    tab1, tab2, tab3 = st.tabs([
        "💬 Chat",
        "📝 Summary",
        "📄 Transcript",
    ])

    with tab1:
        render_chat_ui()

    with tab2:
        render_summary_ui()

    with tab3:
        render_transcript_ui()

else:
    render_landing_page()