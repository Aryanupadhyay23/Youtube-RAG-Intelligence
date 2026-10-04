import streamlit as st
from datetime import datetime
from frontend.services.api_client import fetch_log_dates, fetch_markdown_logs


def render_logs_modal():
    """Render interactive datewise Markdown log viewer dialog/expander."""
    available_dates = fetch_log_dates()
    today_str = datetime.now().strftime("%Y-%m-%d")

    if today_str not in available_dates:
        available_dates.insert(0, today_str)

    col_date, col_level = st.columns([1, 1])
    with col_date:
        selected_date = st.selectbox(
            "📅 Select Log Date",
            options=available_dates,
            index=0,
            key="log_viewer_date",
        )

    with col_level:
        level_filter = st.selectbox(
            "🏷️ Filter by Level",
            options=["ALL", "ERROR", "WARNING", "INFO"],
            index=0,
            key="log_viewer_level",
        )

    col_search, col_refresh = st.columns([3, 1])
    with col_search:
        search_kw = st.text_input(
            "🔍 Search in Logs",
            placeholder="Search keywords or error messages…",
            key="log_viewer_search",
        )
    with col_refresh:
        st.write("")
        st.write("")
        if st.button("🔄 Refresh", key="log_viewer_refresh", use_container_width=True):
            st.rerun()

    st.divider()

    # Fetch and render formatted Markdown logs
    logs_md = fetch_markdown_logs(
        date_str=selected_date,
        level_filter=level_filter,
        search_query=search_kw,
    )

    with st.container(height=450):
        st.markdown(logs_md, unsafe_allow_html=True)

    st.download_button(
        label=f"⬇️ Download {selected_date} Logs (.md)",
        data=logs_md,
        file_name=f"logs_{selected_date}.md",
        mime="text/markdown",
        use_container_width=True,
    )
