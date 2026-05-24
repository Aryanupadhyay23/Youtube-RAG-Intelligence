import re
import json
import urllib.request


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


def get_video_metadata(video_id: str):

    try:

        url = (
            "https://www.youtube.com/oembed"
            f"?url=https://www.youtube.com/watch?v={video_id}"
            "&format=json"
        )

        with urllib.request.urlopen(
            url,
            timeout=5,
        ) as response:

            data = json.loads(
                response.read()
            )

        return {
            "title": data.get(
                "title",
                "Unknown Title",
            ),
            "author": data.get(
                "author_name",
                "Unknown Channel",
            ),
            "thumbnail": data.get(
                "thumbnail_url",
                "",
            ),
        }

    except Exception:

        return {
            "title": "Unknown Title",
            "author": "Unknown Channel",
            "thumbnail": "",
        }


def build_youtube_timestamp_url(
    video_id: str,
    seconds: int,
):

    return (
        "https://youtube.com/watch"
        f"?v={video_id}"
        f"&t={seconds}"
    )