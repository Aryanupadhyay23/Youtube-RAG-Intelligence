import unittest
import time
from backend.services.redis import UpstashRedisMemoryService


class TestUpstashRedisMemory(unittest.TestCase):
    def setUp(self):
        self.ts = int(time.time() * 1000)
        self.test_video_id = f"test_vid_{self.ts}"
        # Use isolated non-configured instance for pure in-memory unit tests
        self.service = UpstashRedisMemoryService(rest_url="", rest_token="")

    def test_in_memory_fallback_sessions(self):
        chat_id = f"test_chat_001_{self.ts}"
        created = self.service.create_session(self.test_video_id, chat_id, "Test Title", username="testuser")
        self.assertEqual(created["chat_id"], chat_id)
        self.assertEqual(created["title"], "Test Title")

        sessions = self.service.list_sessions(self.test_video_id, username="testuser")
        self.assertTrue(any(s["chat_id"] == chat_id for s in sessions))

    def test_in_memory_fallback_messages(self):
        chat_id = f"test_chat_002_{self.ts}"
        self.service.create_session(self.test_video_id, chat_id, "Test Chat", username="testuser")
        turn = self.service.append_turn(self.test_video_id, chat_id, "What is RAG?", "RAG stands for Retrieval-Augmented Generation.", username="testuser")
        self.assertEqual(turn["user"], "What is RAG?")

        msgs = self.service.get_messages(chat_id)
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]["user"], "What is RAG?")

    def test_delete_session(self):
        chat_id = f"test_chat_003_{self.ts}"
        self.service.create_session(self.test_video_id, chat_id, "To Delete", username="testuser")
        self.service.append_turn(self.test_video_id, chat_id, "hello", "hi", username="testuser")
        self.service.delete_session(self.test_video_id, chat_id, username="testuser")
        self.assertIsNone(self.service.get_session(self.test_video_id, chat_id, username="testuser"))
        self.assertEqual(self.service.get_messages(chat_id), [])
