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
