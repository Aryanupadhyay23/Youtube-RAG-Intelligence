import requests
import streamlit as st
from frontend.services.api.common import API_BASE_URL


@st.cache_data(ttl=10, show_spinner=False)
def check_api_health() -> bool:
    """Check if the backend FastAPI service is reachable (cached for 10s)."""
    try:
        r = requests.get(f"{API_BASE_URL}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False
