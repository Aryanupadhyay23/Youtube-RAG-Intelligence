import streamlit as st
from frontend.services.api_client import request_summary


def render_summary_ui():
    """Render smart video summary interface with generate and download options."""
    st.subheader("📝 Smart Video Summary")

    transcript_text = st.session_state.get("transcript_text")
    if not transcript_text:
        st.warning("⚠️ No transcript available to summarize.")
        return

    word_count = len(transcript_text.split())
    if word_count > 6000:
        st.info(f"📦 Large transcript detected ({word_count:,} words). Map-reduce summarisation will be used.")
    else:
        st.info(f"📄 {word_count:,} words detected. Single-pass summarisation will be used.")

    if st.button("✨ Generate Summary", type="primary"):
        with st.spinner("🔄 Generating summary — this may take a moment…"):
            try:
                summary = request_summary(transcript_text)
                if summary and summary.strip():
                    st.session_state.summary = summary
                else:
                    st.warning("⚠️ Summary was empty. The model may have returned no content. Try again.")
            except Exception as error:
                error_str = str(error)

                # Provide user-friendly error messages
                if "Connection" in error_str or "connect" in error_str.lower():
                    st.error("🔌 Could not connect to the backend server. Please make sure it's running on port 8000.")
                elif "timeout" in error_str.lower():
                    st.error("⏱️ Summary generation timed out. The transcript may be too long, or the model is slow. Try again.")
                elif "500" in error_str:
                    st.error("⚠️ The summary model encountered an internal error. This usually means the Ollama service is down or the model is unavailable.")
                else:
                    st.error(f"❌ Summary generation failed: {error_str}")

                with st.expander("🔍 Technical Details"):
                    st.code(error_str, language="text")

    if st.session_state.get("summary"):
        st.divider()
        st.markdown(st.session_state.summary)
        st.divider()

        col1, col2 = st.columns(2)
        col1.download_button(
            label="⬇️ Download (.md)",
            data="# Video Summary\n\n" + st.session_state.summary,
            file_name="summary.md",
            mime="text/markdown",
            use_container_width=True,
        )
        col2.download_button(
            label="⬇️ Download (.txt)",
            data=st.session_state.summary,
            file_name="summary.txt",
            mime="text/plain",
            use_container_width=True,
        )
