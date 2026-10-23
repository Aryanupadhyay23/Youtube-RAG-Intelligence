import unittest
from unittest.mock import Mock, patch

import requests

from backend.services.youtube import extract_video_id, get_video_metadata
from frontend.utils.youtube import extract_video_id as frontend_extract_video_id


class TestYouTube(unittest.TestCase):
    def test_extract_standard_watch_url(self):
        self.assertEqual(extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ"), "dQw4w9WgXcQ")

    def test_extract_short_url_embed_and_raw_id(self):
        self.assertEqual(extract_video_id("https://youtu.be/dQw4w9WgXcQ"), "dQw4w9WgXcQ")
        self.assertEqual(extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ"), "dQw4w9WgXcQ")
        self.assertEqual(extract_video_id("dQw4w9WgXcQ"), "dQw4w9WgXcQ")

    def test_extract_shorts_live_and_legacy_v_urls(self):
        self.assertEqual(extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ"), "dQw4w9WgXcQ")
        self.assertEqual(extract_video_id("https://www.youtube.com/live/dQw4w9WgXcQ"), "dQw4w9WgXcQ")
        self.assertEqual(extract_video_id("https://www.youtube.com/v/dQw4w9WgXcQ"), "dQw4w9WgXcQ")

    def test_extract_urls_with_extra_query_params(self):
        self.assertEqual(
            extract_video_id("https://m.youtube.com/watch?v=dQw4w9WgXcQ&t=42s&list=PL123"),
            "dQw4w9WgXcQ",
        )
        self.assertEqual(
            extract_video_id("https://www.youtube.com/watch?list=PL123&v=dQw4w9WgXcQ"),
            "dQw4w9WgXcQ",
        )
        self.assertEqual(extract_video_id("https://youtu.be/dQw4w9WgXcQ?t=42"), "dQw4w9WgXcQ")

    def test_frontend_parser_matches_backend(self):
        urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/embed/dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ",
            "https://www.youtube.com/live/dQw4w9WgXcQ",
            "https://www.youtube.com/v/dQw4w9WgXcQ",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s&list=PL123",
            "dQw4w9WgXcQ",
            "https://google.com",
        ]
        for url in urls:
            self.assertEqual(frontend_extract_video_id(url), extract_video_id(url), url)

    def test_invalid_url(self):
        self.assertIsNone(extract_video_id("https://google.com"))

    def test_video_id_schema_validation(self):
        from pydantic import ValidationError
        from backend.routes.video.schemas import InitRequest
        from backend.routes.chat.schemas import ChatRequest

        # Valid 11-char video ID
        req = InitRequest(video_id="dQw4w9WgXcQ")
        self.assertEqual(req.video_id, "dQw4w9WgXcQ")

        # Invalid video ID (too short, too long, special characters)
        with self.assertRaises(ValidationError):
            InitRequest(video_id="short")

        with self.assertRaises(ValidationError):
            InitRequest(video_id="this_is_way_too_long_for_youtube")

        with self.assertRaises(ValidationError):
            ChatRequest(video_id="invalid!@#$", chat_id="c1", query="hi")

    def test_metadata_falls_back_when_oembed_fails(self):
        with patch(
            "backend.services.youtube.metadata.requests.get",
            side_effect=requests.RequestException("network down"),
        ):
            metadata = get_video_metadata("dQw4w9WgXcQ")

        self.assertEqual(metadata["title"], "Video (dQw4w9WgXcQ)")
        self.assertEqual(metadata["author"], "Unknown")
        self.assertIn("dQw4w9WgXcQ", metadata["thumbnail"])

    def test_metadata_falls_back_on_non_200(self):
        response = Mock(status_code=500)
        with patch("backend.services.youtube.metadata.requests.get", return_value=response):
            metadata = get_video_metadata("dQw4w9WgXcQ")

        self.assertEqual(metadata["title"], "Video (dQw4w9WgXcQ)")
