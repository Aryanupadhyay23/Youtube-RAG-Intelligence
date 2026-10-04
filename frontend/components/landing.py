import streamlit as st
import requests
from frontend.utils.youtube import extract_video_id
from frontend.utils.session import reset_video_state
from frontend.services.api_client import initialize_video


def render_landing_page():
    """Render a clean, modern landing page with a primary search bar and feature showcase."""
    hero_html = """<div class="flex flex-col items-center justify-center text-center py-8 px-4 max-w-3xl mx-auto" style="text-align: center; margin-left: auto; margin-right: auto;">
<div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold tracking-wider uppercase bg-blue-950/70 text-blue-400 border border-blue-500/30 shadow-md shadow-blue-500/10 mb-4 backdrop-blur-md" style="margin-left: auto; margin-right: auto;">
⚡ HYBRID RAG • LANGGRAPH • SMART SUMMARISATION
</div>
<h1 class="text-4xl md:text-5xl lg:text-6xl font-black tracking-tight text-white mb-4 text-center" style="text-align: center;">
Chat with Any <span class="bg-gradient-to-r from-blue-400 via-sky-300 to-indigo-400 bg-clip-text text-transparent">YouTube Video</span>
</h1>
<p class="text-base md:text-lg text-slate-400 max-w-2xl mx-auto leading-relaxed font-normal text-center" style="text-align: center; margin-left: auto; margin-right: auto;">
Instant conversational intelligence, deep hierarchical summaries, and timestamp-grounded answers<br/>
from any video's verbatim transcript.
</p>
</div>"""
    st.markdown(hero_html, unsafe_allow_html=True)

    # Clean centered input form
    with st.form("youtube_input_form", clear_on_submit=False):
        col_input, col_submit = st.columns([5, 1])
        with col_input:
            url_value = st.text_input(
                "YouTube Video URL",
                placeholder="https://www.youtube.com/watch?v=... (Watch, Shorts, or Embed)",
                label_visibility="collapsed",
                key="main_url_field",
                value=st.session_state.get("prefill_url", ""),
            )
        with col_submit:
            submitted = st.form_submit_button("🚀 Analyze", type="primary", use_container_width=True)

        if submitted:
            if url_value and url_value.strip():
                st.session_state.submitted_video_url = url_value.strip()
                st.session_state.prefill_url = ""
                st.rerun()
            else:
                st.warning("⚠️ Please paste a valid YouTube URL first.")

    # Status / loading area directly beneath the input field (not at top of page)
    status_area = st.container()

    active_url = st.session_state.get("submitted_video_url")
    if active_url:
        st.session_state.submitted_video_url = None
        video_id = extract_video_id(active_url)
        with status_area:
            if not video_id:
                st.error("⚠️ Invalid YouTube URL. Please provide a valid watch, embed, or shorts link.")
            else:
                reset_video_state()
                with st.spinner("🚀 Analyzing video transcript & generating vector index..."):
                    try:
                        init_data = initialize_video(video_id)
                        metadata = init_data.get("metadata", {})
                        transcript_text = init_data.get("transcript_text", "")
                        transcript_segments = init_data.get("transcript_segments", [])

                        if not transcript_text:
                            st.error("❌ No transcript could be retrieved for this video.")
                        else:
                            st.session_state.video_id = video_id
                            st.session_state.metadata = metadata
                            st.session_state.transcript_text = transcript_text
                            st.session_state.transcript_segments = transcript_segments
                            st.rerun()

                    except requests.exceptions.ConnectionError:
                        st.error("🔌 Cannot reach backend at http://127.0.0.1:8000. Please ensure the backend is running.")
                    except Exception as error:
                        error_str = str(error)
                        st.error(f"❌ Failed to load video: {error_str}")
                        with st.expander("🔍 Error Details"):
                            st.code(error_str, language="text")

    # 1-Click Sample Videos
    st.markdown("<div style='margin-top: 10px; margin-bottom: 25px;'>", unsafe_allow_html=True)
    st.caption("Try an instant sample video:")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("💡 What is RAG? (4 min)", use_container_width=True, key="s1"):
            st.session_state.submitted_video_url = "https://www.youtube.com/watch?v=T-D1OfcDW1M"
            st.rerun()
    with c2:
        if st.button("🤖 AI Agents Explained (12 min)", use_container_width=True, key="s2"):
            st.session_state.submitted_video_url = "https://www.youtube.com/watch?v=sal78ACtGTc"
            st.rerun()
    with c3:
        if st.button("⚡ Attention Is All You Need (15 min)", use_container_width=True, key="s3"):
            st.session_state.submitted_video_url = "https://www.youtube.com/watch?v=bQ5BoolX9Ag"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    cards_html = """<div class="grid grid-cols-1 md:grid-cols-3 gap-5 my-8">
<div class="p-6 rounded-2xl bg-slate-900/60 border border-blue-500/15 backdrop-blur-xl shadow-xl shadow-blue-950/20 hover:border-blue-500/40 hover:-translate-y-1 transition-all duration-300 group">
<div class="w-12 h-12 rounded-xl bg-blue-500/10 border border-blue-500/25 flex items-center justify-center text-2xl mb-4 group-hover:scale-110 transition-transform duration-200">💬</div>
<h3 class="text-lg font-bold text-white mb-2">Hybrid RAG Chat</h3>
<p class="text-sm text-slate-400 leading-relaxed">Combines dense semantic vectors with BM25 keyword matching via Reciprocal Rank Fusion. Every response is strictly grounded with verifiable timestamp links.</p>
</div>
<div class="p-6 rounded-2xl bg-slate-900/60 border border-blue-500/15 backdrop-blur-xl shadow-xl shadow-blue-950/20 hover:border-blue-500/40 hover:-translate-y-1 transition-all duration-300 group">
<div class="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/25 flex items-center justify-center text-2xl mb-4 group-hover:scale-110 transition-transform duration-200">📝</div>
<h3 class="text-lg font-bold text-white mb-2">Deep Video Summaries</h3>
<p class="text-sm text-slate-400 leading-relaxed">Hierarchical map-reduce summarization that generates executive overviews, chronological key topics, and actionable takeaways in seconds.</p>
</div>
<div class="p-6 rounded-2xl bg-slate-900/60 border border-blue-500/15 backdrop-blur-xl shadow-xl shadow-blue-950/20 hover:border-blue-500/40 hover:-translate-y-1 transition-all duration-300 group">
<div class="w-12 h-12 rounded-xl bg-sky-500/10 border border-sky-500/25 flex items-center justify-center text-2xl mb-4 group-hover:scale-110 transition-transform duration-200">📄</div>
<h3 class="text-lg font-bold text-white mb-2">Interactive Transcript Explorer</h3>
<p class="text-sm text-slate-400 leading-relaxed">Browse every spoken word with precise timestamps. Search terms across the entire video and click any segment to jump directly to that exact moment on YouTube.</p>
</div>
</div>
<div class="flex flex-wrap items-center justify-center gap-2.5 my-6">
<span class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-900/80 text-blue-300 border border-blue-500/20 shadow-sm backdrop-blur-sm">⚡ Hybrid Retrieval</span>
<span class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-900/80 text-blue-300 border border-blue-500/20 shadow-sm backdrop-blur-sm">🧠 Smart Summarization</span>
<span class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-900/80 text-blue-300 border border-blue-500/20 shadow-sm backdrop-blur-sm">🎯 Gemini Embeddings</span>
<span class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-900/80 text-blue-300 border border-blue-500/20 shadow-sm backdrop-blur-sm">🔍 BM25 + Vector RRF</span>
<span class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-900/80 text-blue-300 border border-blue-500/20 shadow-sm backdrop-blur-sm">🛡️ Multi-Key Fallback</span>
</div>"""
    st.markdown(cards_html, unsafe_allow_html=True)
