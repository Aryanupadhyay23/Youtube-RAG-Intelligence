import re


def extract_video_id(url: str):

    patterns = [
        r"(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})",
        r"^([A-Za-z0-9_-]{11})$",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            url.strip(),
        )

        if match:
            return match.group(1)

    return None


def safe_get(
    dictionary,
    key,
    default=None,
):

    if key in dictionary:
        return dictionary[key]

    return default


def truncate_text(
    text: str,
    limit: int = 50,
):

    if len(text) <= limit:
        return text

    return text[:limit] + "..."