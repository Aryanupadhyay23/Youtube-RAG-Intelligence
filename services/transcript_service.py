import os

from dotenv import load_dotenv

from supadata import (
    Supadata,
    SupadataError,
)

load_dotenv()


SUPADATA_KEYS = [
    os.environ.get("SUPADATA_KEY_1"),
    os.environ.get("SUPADATA_KEY_2"),
    os.environ.get("SUPADATA_KEY_3"),
]

SUPADATA_KEYS = [
    key
    for key in SUPADATA_KEYS
    if key
]


def fetch_transcript(video_id: str):

    if not SUPADATA_KEYS:
        raise Exception(
            "No Supadata API keys configured."
        )

    last_error = None

    for api_key in SUPADATA_KEYS:

        try:

            client = Supadata(
                api_key=api_key
            )

            result = client.youtube.transcript(
                video_id=video_id,
                lang="en",
            )

            if not result or not result.content:
                raise Exception(
                    "Empty transcript returned."
                )

            segments = []

            for chunk in result.content:

                text = (
                    chunk.text
                    if hasattr(chunk, "text")
                    else str(chunk)
                )

                if text and text.strip():

                    segments.append({
                        "text": text.strip(),
                        "start": (
                            chunk.offset / 1000
                            if hasattr(chunk, "offset")
                            else 0
                        ),
                        "duration": (
                            chunk.duration / 1000
                            if hasattr(chunk, "duration")
                            else 0
                        ),
                    })

            if not segments:
                raise Exception(
                    "No transcript segments found."
                )

            full_text = " ".join(
                segment["text"]
                for segment in segments
            )

            return full_text, segments

        except SupadataError as error:

            last_error = (
                error.message
                if hasattr(error, "message")
                else str(error)
            )

        except Exception as error:

            last_error = str(error)

    raise Exception(last_error)