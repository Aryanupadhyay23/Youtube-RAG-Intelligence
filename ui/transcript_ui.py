import streamlit as st

from utils.formatting import format_time

from services.youtube_service import build_youtube_timestamp_url


def render_transcript_ui():

    st.subheader("📄 Transcript Explorer")

    transcript_text = st.session_state.transcript_text
    transcript_segments = st.session_state.transcript_segments
    video_id = st.session_state.video_id

    col_mode, col_search = st.columns([1, 2])

    view_mode = col_mode.radio(
        "View Mode",
        ["Plain Text", "Timestamped Segments"],
        horizontal=True,
    )

    search_query = col_search.text_input(
        "🔍 Search Transcript",
        placeholder="Enter keyword…",
    )

    st.divider()

    if view_mode == "Plain Text":

        display_text = transcript_text

        if search_query:

            matched = [
                seg["text"]
                for seg in transcript_segments
                if search_query.lower() in seg["text"].lower()
            ]

            display_text = (
                "\n\n".join(matched)
                if matched
                else "No matches found."
            )

        st.text_area(
            "Transcript",
            display_text,
            height=450,
            disabled=True,
        )

    else:

        filtered = transcript_segments

        if search_query:
            filtered = [
                seg
                for seg in transcript_segments
                if search_query.lower() in seg["text"].lower()
            ]

        if not filtered:
            st.info("No matching segments found.")

        else:

            st.caption(f"{len(filtered):,} segments found")

            for seg in filtered:

                timestamp = format_time(seg["start"])

                yt_url = build_youtube_timestamp_url(
                    video_id=video_id,
                    seconds=int(seg["start"]),
                )

                c1, c2 = st.columns([1, 7])

                c1.link_button(
                    timestamp,
                    yt_url,
                    use_container_width=True,
                )

                c2.write(seg["text"])

    st.divider()

    col1, col2 = st.columns(2)

    col1.download_button(
        label="⬇️ Download (.txt)",
        data=transcript_text,
        file_name="transcript.txt",
        mime="text/plain",
        use_container_width=True,
    )

    col2.download_button(
        label="⬇️ Download (.md)",
        data="# Transcript\n\n" + transcript_text,
        file_name="transcript.md",
        mime="text/markdown",
        use_container_width=True,
    )