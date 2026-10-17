import unittest
from backend.core.ingestion import create_timestamp_aware_chunks


def _segments(count, chars=40):
    return [
        {"text": "x" * chars, "start": float(i), "duration": 1.0}
        for i in range(count)
    ]


class TestChunking(unittest.TestCase):
    def test_empty_segments(self):
        self.assertEqual(create_timestamp_aware_chunks("vid", []), [])

    def test_chunking_creates_documents(self):
        segs = _segments(30, chars=150)
        chunks = create_timestamp_aware_chunks("vid", segs)
        self.assertGreater(len(chunks), 0)
        self.assertEqual(chunks[0].metadata["video_id"], "vid")
        self.assertIn("start_time", chunks[0].metadata)
        self.assertIn("end_time", chunks[0].metadata)
