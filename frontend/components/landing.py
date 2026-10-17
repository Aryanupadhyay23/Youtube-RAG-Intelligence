import streamlit as st
import requests
from frontend.utils.youtube import extract_video_id
from frontend.utils.session import reset_video_state
from frontend.services.api import initialize_video, API_BASE_URL


def render_landing_page():
    """Render a clean, modern landing page with a primary search bar and clear feature cards."""
    # ── Clean, Non-Technical Hero Section ─────────────────────────────────────
    hero_html = """<div class="landing-hero" style="text-align: center; margin: 0 auto; max-width: 820px; padding: 1.5rem 1rem 1rem 1rem;">
<div class="hero-badge" style="display: inline-flex; align-items: center; gap: 8px; padding: 6px 16px; border-radius: 9999px; font-size: 0.8rem; font-weight: 600; letter-spacing: 0.04em; background: rgba(30, 58, 138, 0.4); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); margin-bottom: 1.25rem;">
🎬 Intelligent YouTube Assistant
</div>
<h1 class="hero-title" style="font-size: 2.75rem; font-weight: 800; line-height: 1.2; letter-spacing: -0.025em; color: #ffffff; margin-bottom: 0.85rem;">
Chat & Learn from Any <span class="gradient-text" style="background: linear-gradient(135deg, #60a5fa 0%, #93c5fd 50%, #818cf8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">YouTube Video</span>
</h1>
<p class="hero-subtitle" style="font-size: 1.05rem; font-weight: 400; line-height: 1.6; color: #94a3b8; max-width: 620px; margin: 0 auto 1.5rem auto;">
Paste any link to ask questions with exact timestamps, get instant summaries, or search through every spoken word.
</p>
</div>"""
    st.markdown(hero_html, unsafe_allow_html=True)

    # ── Search Input Box ──────────────────────────────────────────────────────
    with st.form("youtube_input_form", clear_on_submit=False):
        col_input, col_submit = st.columns([5, 1])
        with col_input:
            url_value = st.text_input(
                "YouTube Video URL",
                placeholder="Paste any YouTube video link here... (e.g. https://www.youtube.com/watch?v=...)",
                label_visibility="collapsed",
                key="main_url_field",
                value=st.session_state.get("prefill_url", ""),
            )
        with col_submit:
            submitted = st.form_submit_button("🚀 Explore", type="primary", use_container_width=True)

        if submitted:
            if url_value and url_value.strip():
                st.session_state.submitted_video_url = url_value.strip()
                st.session_state.prefill_url = ""
                st.rerun()
            else:
                st.warning("⚠️ Please paste a valid YouTube video link first.")

    # Status / loading area
    status_area = st.container()

    active_url = st.session_state.get("submitted_video_url")
    if active_url:
        st.session_state.submitted_video_url = None
        video_id = extract_video_id(active_url)
        with status_area:
            if not video_id:
                st.error("⚠️ Invalid YouTube link. Please paste a valid YouTube watch, embed, or shorts link.")
            else:
                reset_video_state()
                with st.spinner("⏳ Loading video transcript and preparing your chat..."):
                    try:
                        init_data = initialize_video(video_id)
                        metadata = init_data.get("metadata", {})
                        transcript_text = init_data.get("transcript_text", "")
                        transcript_segments = init_data.get("transcript_segments", [])

                        if not transcript_text:
                            st.error("❌ No subtitles or transcript found for this video. Please try another video.")
                        else:
                            st.session_state.video_id = video_id
                            st.session_state.metadata = metadata
                            st.session_state.transcript_text = transcript_text
                            st.session_state.transcript_segments = transcript_segments
                            st.rerun()

                    except requests.exceptions.ConnectionError:
                        st.error(f"🔌 Cannot reach backend server at {API_BASE_URL}. Please ensure it is running.")
                    except Exception as error:
                        error_str = str(error)
                        st.error(f"❌ Failed to load video: {error_str}")
                        with st.expander("🔍 Error Details"):
                            st.code(error_str, language="text")

    # ── Instant Sample Video Chips ───────────────────────────────────────────
    st.markdown("<div style='margin-top: 10px; margin-bottom: 25px;'>", unsafe_allow_html=True)
    st.caption("Try an instant sample video:")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("💡 Tech & AI Explained (5 min)", use_container_width=True, key="s1"):
            st.session_state.submitted_video_url = "https://www.youtube.com/watch?v=sal78ACtGTc"
            st.rerun()
    with c2:
        if st.button("🔍 How Search Engines Work (4 min)", use_container_width=True, key="s2"):
            st.session_state.submitted_video_url = "https://www.youtube.com/watch?v=T-D1OfcDW1M"
            st.rerun()
    with c3:
        if st.button("🎙️ Habit Building & Focus (7 min)", use_container_width=True, key="s3"):
            st.session_state.submitted_video_url = "https://www.youtube.com/watch?v=bQ5BoolX9Ag"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Clean Feature Cards (What it does, zero jargon) ───────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            """<div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(59, 130, 246, 0.2); border-radius: 16px; padding: 1.5rem; height: 100%; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);">
<div style="width: 44px; height: 44px; border-radius: 12px; background: rgba(59, 130, 246, 0.12); border: 1px solid rgba(59, 130, 246, 0.25); display: flex; align-items: center; justify-content: center; font-size: 1.35rem; margin-bottom: 1rem;">💬</div>
<h3 style="font-size: 1.15rem; font-weight: 700; color: #ffffff; margin-bottom: 0.5rem; letter-spacing: -0.01em;">Ask Any Question</h3>
<p style="font-size: 0.9rem; color: #94a3b8; line-height: 1.55; margin: 0;">Ask naturally about anything in the video. Every answer includes clickable timestamps that take you straight to the exact scene.</p>
</div>""",
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """<div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(59, 130, 246, 0.2); border-radius: 16px; padding: 1.5rem; height: 100%; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);">
<div style="width: 44px; height: 44px; border-radius: 12px; background: rgba(99, 102, 241, 0.12); border: 1px solid rgba(99, 102, 241, 0.25); display: flex; align-items: center; justify-content: center; font-size: 1.35rem; margin-bottom: 1rem;">⚡</div>
<h3 style="font-size: 1.15rem; font-weight: 700; color: #ffffff; margin-bottom: 0.5rem; letter-spacing: -0.01em;">Instant Summary</h3>
<p style="font-size: 0.9rem; color: #94a3b8; line-height: 1.55; margin: 0;">Get clear overviews, key takeaways, and structured chapter summaries in seconds without watching hours of footage.</p>
</div>""",
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            """<div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(59, 130, 246, 0.2); border-radius: 16px; padding: 1.5rem; height: 100%; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);">
<div style="width: 44px; height: 44px; border-radius: 12px; background: rgba(14, 165, 233, 0.12); border: 1px solid rgba(14, 165, 233, 0.25); display: flex; align-items: center; justify-content: center; font-size: 1.35rem; margin-bottom: 1rem;">🔍</div>
<h3 style="font-size: 1.15rem; font-weight: 700; color: #ffffff; margin-bottom: 0.5rem; letter-spacing: -0.01em;">Search Every Word</h3>
<p style="font-size: 0.9rem; color: #94a3b8; line-height: 1.55; margin: 0;">Explore the complete transcript with synchronized timestamps. Find specific topics and jump immediately to that point in the player.</p>
</div>""",
            unsafe_allow_html=True,
        )

