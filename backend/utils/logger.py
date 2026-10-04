import os
import sys
import logging
import traceback
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Project root logs directory with fallback to system temp directory for container permissions
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"

try:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    # Test writability
    _test_file = LOGS_DIR / ".write_test"
    _test_file.touch()
    _test_file.unlink()
except (PermissionError, OSError):
    # Graceful fallback to /tmp/youtube_rag_logs (guaranteed writable on Hugging Face Spaces and Docker)
    LOGS_DIR = Path(tempfile.gettempdir()) / "youtube_rag_logs"
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


class MarkdownLogFormatter(logging.Formatter):
    """
    Format log records into clean, human-readable Markdown with badges,
    collapsible stack traces, and timestamps.
    """

    LEVEL_BADGES = {
        "DEBUG": "⚪ `DEBUG`",
        "INFO": "🟢 `INFO`",
        "WARNING": "🟡 `WARNING`",
        "ERROR": "🔴 `ERROR`",
        "CRITICAL": "🔥 `CRITICAL`",
    }

    def format(self, record: logging.LogRecord) -> str:
        time_str = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        level_badge = self.LEVEL_BADGES.get(record.levelname, f"`{record.levelname}`")
        module_name = record.name

        msg = record.getMessage()
        lines = [
            f"### `{time_str}` | {level_badge} | `{module_name}`",
            f"> **Message:** {msg}",
        ]

        if record.exc_info:
            exc_text = "".join(traceback.format_exception(*record.exc_info)).strip()
            lines.append("<details><summary>🔍 <b>View Error Traceback</b></summary>\n")
            lines.append("```python")
            lines.append(exc_text)
            lines.append("```\n</details>")
        elif record.stack_info:
            lines.append("<details><summary>🔍 <b>View Stack Info</b></summary>\n")
            lines.append("```text")
            lines.append(record.stack_info.strip())
            lines.append("```\n</details>")

        lines.append("\n---\n")
        return "\n".join(lines)


class DatewiseDailyFileHandler(logging.Handler):
    """
    Custom logging handler that dynamically routes log entries to a datewise file:
    logs/YYYY-MM-DD.md
    """

    def __init__(self, logs_dir: Path):
        super().__init__()
        self.logs_dir = logs_dir
        try:
            self.logs_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def emit(self, record: logging.LogRecord):
        try:
            date_str = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d")
            log_file = self.logs_dir / f"{date_str}.md"
            msg = self.format(record)
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except Exception:
            self.handleError(record)


_logging_initialized = False


def setup_logging(level=logging.INFO):
    """Initialize root logging once with dual outputs: console and datewise Markdown files."""
    global _logging_initialized
    if _logging_initialized:
        return

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 1. Console Handler (Standard terminal output)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_format = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)

    # 2. Datewise Markdown File Handler (logs/YYYY-MM-DD.md)
    md_handler = DatewiseDailyFileHandler(LOGS_DIR)
    md_handler.setLevel(level)
    md_handler.setFormatter(MarkdownLogFormatter())
    root_logger.addHandler(md_handler)

    _logging_initialized = True
    root_logger.info("System logging initialized with datewise Markdown recording.")


def get_available_log_dates() -> List[str]:
    """Return all available log dates sorted descending (newest first)."""
    if not LOGS_DIR.exists():
        return []
    dates = []
    for file in LOGS_DIR.glob("*.md"):
        dates.append(file.stem)
    dates.sort(reverse=True)
    return dates


def get_datewise_logs_markdown(
    date_str: Optional[str] = None,
    level_filter: Optional[str] = None,
    search_query: str = "",
) -> str:
    """
    Fetch and filter datewise logs directly formatted as clean Markdown.
    Includes header statistics: Total entries, Errors count, Warnings count.
    """
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    log_file = LOGS_DIR / f"{date_str}.md"
    if not log_file.exists():
        return f"### 📋 Logs for `{date_str}`\n\n> *No log entries recorded for this date yet.*"

    try:
        content = log_file.read_text(encoding="utf-8")
    except Exception as e:
        return f"⚠️ Error reading log file `{log_file.name}`: {e}"

    if not content.strip():
        return f"### 📋 Logs for `{date_str}`\n\n> *Log file for `{date_str}` is empty.*"

    # Split into individual markdown log blocks (separated by '---')
    blocks = [b.strip() for b in content.split("\n---\n") if b.strip()]

    # Filter blocks
    filtered_blocks = []
    error_count = 0
    warning_count = 0
    info_count = 0

    target_level = level_filter.upper().strip() if level_filter and level_filter != "ALL" else None
    search_lower = search_query.lower().strip() if search_query else None

    for block in blocks:
        if "🔴 `ERROR`" in block or "🔥 `CRITICAL`" in block:
            error_count += 1
        elif "🟡 `WARNING`" in block:
            warning_count += 1
        elif "🟢 `INFO`" in block:
            info_count += 1

        # Level match
        if target_level:
            if f"`{target_level}`" not in block:
                continue

        # Search match
        if search_lower:
            if search_lower not in block.lower():
                continue

        filtered_blocks.append(block)

    # Build Header Summary
    header = [
        f"## 📋 System Activity Log • `{date_str}`",
        f"**Stats:** 🔴 **{error_count}** Errors | 🟡 **{warning_count}** Warnings | 🟢 **{info_count}** Info | 📦 **{len(blocks)}** Total Events\n",
    ]

    if target_level or search_query:
        filters_applied = []
        if target_level:
            filters_applied.append(f"Level: `{target_level}`")
        if search_query:
            filters_applied.append(f"Search: `\"{search_query}\"`")
        header.append(f"*Filters Applied: {', '.join(filters_applied)} (Showing {len(filtered_blocks)} results)*\n")

    header.append("---\n")

    if not filtered_blocks:
        header.append("> *No log entries matched the selected filters.*")
        return "\n".join(header)

    return "\n".join(header) + "\n\n" + "\n\n---\n\n".join(filtered_blocks)
