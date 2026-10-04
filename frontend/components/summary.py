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
        with st.spinner("Generating summary via backend…"):
            try:
                summary = request_summary(transcript_text)
                st.session_state.summary = summary
            except Exception as error:
                st.warning("⚠️ Summary generation failed.")
                with st.expander("Error Details"):
                    st.code(str(error), language="text")

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
