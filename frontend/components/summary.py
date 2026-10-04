import streamlit as st
from frontend.services.api_client import stream_summary, request_summary


def render_summary_ui():
    """Render smart video summary interface with streaming generation and download options."""
    st.subheader("📝 Smart Video Summary")

    transcript_text = st.session_state.get("transcript_text")
    if not transcript_text:
        st.warning("⚠️ No transcript available to summarize.")
        return

    word_count = len(transcript_text.split())
    if word_count > 6000:
        st.info(f"📦 Large transcript detected ({word_count:,} words). Parallel map-reduce summarisation will be used.")
    else:
        st.info(f"📄 {word_count:,} words detected. Single-pass summarisation will be used.")

    if st.button("✨ Generate Summary", type="primary"):
        status_box = st.empty()
        summary_box = st.empty()
        full_summary = ""
        has_error = False

        status_box.caption("🔄 Connecting to summary engine…")

        try:
            for event in stream_summary(transcript_text):
                event_type = event.get("type")
                value = event.get("value", "")

                if event_type == "status":
                    status_box.caption(f"⚙️ {value}")
                elif event_type == "token":
                    status_box.empty()
                    full_summary += value
                    summary_box.markdown(full_summary + "▌")
                elif event_type == "error":
                    status_box.empty()
                    has_error = True
                    error_val = str(value)
                    if "connection" in error_val.lower() or "connect" in error_val.lower():
                        st.error("🔌 Could not connect to backend server on port 8000.")
                    elif "timeout" in error_val.lower():
                        st.error("⏱️ Summary request timed out. Please try again.")
                    else:
                        st.error(f"❌ {value}")
                    break

            if full_summary:
                summary_box.markdown(full_summary)
                status_box.empty()
                st.session_state.summary = full_summary
            elif not has_error:
                # Fallback to synchronous request if streaming returned nothing
                status_box.caption("🔄 Finalizing summary generation…")
                fallback_summary = request_summary(transcript_text)
                if fallback_summary and fallback_summary.strip():
                    summary_box.markdown(fallback_summary)
                    status_box.empty()
                    st.session_state.summary = fallback_summary
                else:
                    status_box.empty()
                    st.warning("⚠️ Summary was empty. Please try again.")

        except Exception as error:
            status_box.empty()
            error_str = str(error)
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
