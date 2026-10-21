import unittest
from backend.services.youtube import extract_video_id


class TestYouTube(unittest.TestCase):
    def test_extract_standard_watch_url(self):
        self.assertEqual(extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ"), "dQw4w9WgXcQ")

    def test_extract_short_url_embed_and_raw_id(self):
        self.assertEqual(extract_video_id("https://youtu.be/dQw4w9WgXcQ"), "dQw4w9WgXcQ")
        self.assertEqual(extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ"), "dQw4w9WgXcQ")
        self.assertEqual(extract_video_id("dQw4w9WgXcQ"), "dQw4w9WgXcQ")

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
