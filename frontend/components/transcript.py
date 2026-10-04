import streamlit as st
from frontend.utils.timestamp import format_time, build_youtube_timestamp_url


def render_transcript_ui():
    """Render interactive transcript viewer with keyword search and timestamp buttons."""
    st.subheader("📄 Transcript Explorer")

    transcript_text = st.session_state.get("transcript_text")
    transcript_segments = st.session_state.get("transcript_segments")
    video_id = st.session_state.get("video_id")

    if not transcript_segments or not transcript_text:
        st.warning("⚠️ No transcript data available for this video.")
        return

    current_seek = int(st.session_state.get("player_start_time", 0))
    with st.expander(f"🎬 Interactive Video Player (Seeking: {format_time(current_seek)})", expanded=True):
        st.video(f"https://www.youtube.com/watch?v={video_id}", start_time=current_seek)

    col_mode, col_search = st.columns([1, 2])
    view_mode = col_mode.radio(
        "View Mode",
        ["Plain Text", "Timestamped Segments"],
        horizontal=True,
    )
    search_query = col_search.text_input("🔍 Search Transcript", placeholder="Enter keyword…")
    st.divider()

    if view_mode == "Plain Text":
        display_text = transcript_text
        if search_query:
            matched = [seg["text"] for seg in transcript_segments if search_query.lower() in seg["text"].lower()]
            display_text = "\n\n".join(matched) if matched else "No matches found."

        st.text_area("Transcript", display_text, height=450, disabled=True)

    else:
        filtered = transcript_segments
        if search_query:
            filtered = [seg for seg in transcript_segments if search_query.lower() in seg["text"].lower()]

        if not filtered:
            st.info("No matching segments found.")
        else:
            total_segments = len(filtered)
            limit = st.session_state.get("transcript_display_limit", 60)
            displayed = filtered[:limit]

            st.caption(f"Showing {min(limit, total_segments):,} of {total_segments:,} segments • Click ▶ to seek player, 🔗 to open YouTube")

            for idx, seg in enumerate(displayed):
                timestamp = format_time(seg["start"])
                yt_url = build_youtube_timestamp_url(video_id=video_id, seconds=int(seg["start"]))

                c1, c2, c3 = st.columns([1.6, 0.6, 7.8])
                if c1.button(f"▶ {timestamp}", key=f"seek_{idx}_{int(seg['start'])}", use_container_width=True, help="Seek player to this timestamp"):
                    st.session_state.player_start_time = int(seg["start"])
                    st.rerun()
                c2.link_button("🔗", yt_url, help="Open on YouTube", use_container_width=True)
                c3.write(seg["text"])

            if total_segments > limit:
                if st.button("➕ Load Next 60 Segments", use_container_width=True):
                    st.session_state.transcript_display_limit = limit + 60
                    st.rerun()

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
