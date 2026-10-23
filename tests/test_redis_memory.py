import unittest
import time
import json as json_lib
from unittest.mock import Mock, patch
import requests
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
        turn = self.service.append_turn(
            self.test_video_id,
            chat_id,
            "What is RAG?",
            "RAG stands for Retrieval-Augmented Generation.",
            username="testuser",
        )
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

    def test_get_user_session_scoping(self):
        chat_id = f"test_chat_004_{self.ts}"
        self.service.create_session(self.test_video_id, chat_id, "Scoped Chat", username="alice")
        # Alice should see her session
        alice_sess = self.service.get_user_session(chat_id, username="alice")
        self.assertIsNotNone(alice_sess)
        self.assertEqual(alice_sess["title"], "Scoped Chat")
        # Bob should not see Alice's session
        bob_sess = self.service.get_user_session(chat_id, username="bob")
        self.assertIsNone(bob_sess)

    @patch("backend.services.redis.service.requests.post", side_effect=requests.ConnectionError("offline"))
    def test_configured_redis_outage_uses_memory_for_chat_history(self, _post):
        service = UpstashRedisMemoryService(rest_url="https://redis.example", rest_token="token")
        chat_id = f"offline_chat_{self.ts}"

        service.create_session(self.test_video_id, chat_id, "Offline chat", username="testuser")
        service.append_turn(self.test_video_id, chat_id, "Question", "Answer", username="testuser")

        self.assertEqual(len(service.list_sessions(self.test_video_id, username="testuser")), 1)
        self.assertEqual(service.get_messages(chat_id)[0]["ai"], "Answer")

    @patch("backend.services.redis.service.requests.post")
    def test_fallback_writes_replay_when_redis_recovers(self, post):
        service = UpstashRedisMemoryService(rest_url="https://redis.example", rest_token="token")
        chat_id = f"replay_chat_{self.ts}"
        with patch(
            "backend.services.redis.service.requests.post",
            side_effect=requests.ConnectionError("offline"),
        ):
            service.create_session(self.test_video_id, chat_id, "Recovered chat", username="testuser")

        session = {
            "chat_id": chat_id,
            "video_id": self.test_video_id,
            "title": "Recovered chat",
            "created_at": 1,
            "updated_at": 1,
            "message_count": 0,
            "username": "testuser",
        }

        def redis_response(_url, json, **_kwargs):
            response = Mock(status_code=200)
            if json[0] == "PING":
                response.json.return_value = {"result": "PONG"}
            elif json[0] == "HGETALL":
                response.json.return_value = {"result": {chat_id: json_lib.dumps(session)}}
            else:
                response.json.return_value = {"result": "OK"}
            return response

        post.side_effect = redis_response
        service._redis_retry_after = 0

        self.assertEqual(service.list_sessions(self.test_video_id, username="testuser")[0]["chat_id"], chat_id)
        self.assertTrue(any(call.kwargs["json"][0] == "HSET" for call in post.call_args_list))
