import streamlit as st


def render_landing_page():

    st.info("👈 Enter a YouTube URL from the sidebar to begin.")

    st.markdown("### What you can do")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### 💬 RAG Chat")
        st.caption(
            "Ask questions grounded strictly in the video's transcript context. "
            "Powered by FAISS retrieval and Groq LLaMA 3.3."
        )

    with col2:
        st.markdown("#### 📝 Smart Summary")
        st.caption(
            "Generate concise, structured summaries for any video — "
            "short or feature-length — using map-reduce summarisation."
        )

    with col3:
        st.markdown("#### 📄 Transcript Explorer")
        st.caption(
            "Browse the full transcript, search keywords, and jump "
            "directly to timestamped moments on YouTube."
        )