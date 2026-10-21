import re
from fastapi import APIRouter, HTTPException
from backend.utils.logger import get_available_log_dates, get_datewise_logs_markdown

router = APIRouter(tags=["Health & Observability"])


@router.get("/health")
@router.get("/api/health")
def health():
    """Health check endpoint for Docker, AWS CodeDeploy, and monitoring."""
    return {"status": "healthy", "service": "YouTube RAG Intelligence Backend"}


@router.get("/api/logs/dates")
def get_log_dates():
    """Retrieve all available datewise log dates."""
    return {"dates": get_available_log_dates()}


@router.get("/api/logs")
def get_logs(date: str = "", level: str = "", query: str = ""):
    """Retrieve datewise logs formatted in clean Markdown."""
    if date and not re.fullmatch(r"^\d{4}-\d{2}-\d{2}$", date):
        raise HTTPException(status_code=400, detail="Invalid date format. Expected YYYY-MM-DD.")
    md_content = get_datewise_logs_markdown(date_str=date or None, level_filter=level or None, search_query=query)
    return {"markdown": md_content, "date": date}
