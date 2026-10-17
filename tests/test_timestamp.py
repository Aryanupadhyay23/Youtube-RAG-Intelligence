import unittest
from backend.utils.timestamp import format_time, get_youtube_timestamp_url


class TestTimestamp(unittest.TestCase):
    def test_format_time(self):
        self.assertEqual(format_time(65), "01:05")
        self.assertEqual(format_time(3665), "01:01:05")
        self.assertEqual(format_time(0), "00:00")

    def test_get_youtube_timestamp_url(self):
        url = get_youtube_timestamp_url("dQw4w9WgXcQ", 65)
        self.assertEqual(url, "https://youtube.com/watch?v=dQw4w9WgXcQ&t=65s")
