import unittest
from unittest.mock import patch

from supadata import SupadataError

from backend.services.transcript import supadata as supadata_service

VIDEO_ID = "dQw4w9WgXcQ"


class FakeChunk:
    def __init__(self, text, offset, duration):
        self.text = text
        self.offset = offset
        self.duration = duration


class FakeResult:
    content = [
        FakeChunk("hello", 0, 1000),
        FakeChunk("world", 1000, 1000),
    ]


def make_fake_supadata(failing_keys, error_factory, attempted):
    class FakeYouTube:
        def __init__(self, api_key):
            self.api_key = api_key

        def transcript(self, video_id):
            if self.api_key in failing_keys:
                raise error_factory()
            return FakeResult()

    class FakeSupadata:
        def __init__(self, api_key):
            self.api_key = api_key
            attempted.append(api_key)

        def transcript(self, **kwargs):
            if self.api_key in failing_keys:
                raise error_factory()
            return FakeResult()

        @property
        def youtube(self):
            return FakeYouTube(self.api_key)

    return FakeSupadata


def supadata_error(code, message, details):
    return lambda: SupadataError(error=code, message=message, details=details)


class TestSupadataFailover(unittest.TestCase):
    def fetch(self, failing_keys, error_factory, keys, active_index=0):
        attempted = []
        self.attempted = attempted
        fake = make_fake_supadata(failing_keys, error_factory, attempted)
        with (
            patch("supadata.Supadata", fake),
            patch.object(supadata_service, "SUPADATA_KEYS", keys),
            patch.object(supadata_service, "_active_key_index", active_index),
        ):
            try:
                return supadata_service.fetch_from_supadata(VIDEO_ID), attempted
            finally:
                self.active_index_after = supadata_service._active_key_index

    def test_429_rotates_to_next_key(self):
        error = supadata_error(
            "limit-exceeded",
            "Limit Exceeded",
            "Request rate limit on current plan was exceeded.",
        )
        (text, segments), attempted = self.fetch(["dead-key"], error, ["dead-key", "good-key"])

        self.assertEqual(text, "hello world")
        self.assertEqual(len(segments), 2)
        self.assertEqual(attempted, ["dead-key", "good-key"])
        self.assertEqual(self.active_index_after, 1)

    def test_no_captions_raises_without_rotating(self):
        error = supadata_error(
            "transcript-unavailable",
            "Transcript Unavailable",
            "No transcript is available for this video",
        )
        with self.assertRaises(SupadataError):
            self.fetch(["dead-key"], error, ["dead-key", "good-key"])

        # The second key must never be tried for a non-retryable error.
        self.assertEqual(self.attempted, ["dead-key"])
        self.assertEqual(self.active_index_after, 0)

    def test_unrelated_401_in_message_does_not_rotate(self):
        error = supadata_error(
            "video-not-found",
            "Video 401abc could not be found",
            "The requested video does not exist",
        )
        with self.assertRaises(SupadataError):
            self.fetch(["dead-key"], error, ["dead-key", "good-key"])

        self.assertEqual(self.attempted, ["dead-key"])
        self.assertEqual(self.active_index_after, 0)

    def test_http_status_fallback_rotates_without_error_code(self):
        def error():
            return RuntimeError("429 Client Error: Too Many Requests for url: https://api.supadata.ai/v1/transcript")

        (text, segments), attempted = self.fetch(["dead-key"], error, ["dead-key", "good-key"])

        self.assertEqual(text, "hello world")
        self.assertEqual(len(segments), 2)
        self.assertEqual(attempted, ["dead-key", "good-key"])
        self.assertEqual(self.active_index_after, 1)
