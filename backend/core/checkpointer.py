"""
LangGraph Checkpointer backed by Upstash Redis.
Utilizes the official `langgraph-checkpoint-upstash-redis` module to provide
persistent, serverless-ready conversation checkpointing.
"""

import logging
from typing import Optional
from langgraph.checkpoint.memory import InMemorySaver

from backend.config import UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN
from backend.services.redis import DEFAULT_TTL_SECONDS

logger = logging.getLogger(__name__)


def get_redis_checkpointer(
    url: Optional[str] = None,
    token: Optional[str] = None,
    ttl: Optional[int] = DEFAULT_TTL_SECONDS,
):
    """Factory to initialize the official LangGraph Upstash Redis checkpointer.

    Uses `langgraph-checkpoint-upstash-redis` (UpstashRedisSaver) with REST API connection info.
    Falls back gracefully to InMemorySaver if credentials are not configured or upon connection error.
    """
    rest_url = url or UPSTASH_REDIS_REST_URL
    rest_token = token or UPSTASH_REDIS_REST_TOKEN

    if rest_url and rest_token:
        try:
            from langgraph.checkpoint.upstash_redis import UpstashRedisSaver
            saver = UpstashRedisSaver.from_conn_info(
                url=rest_url,
                token=rest_token,
                ttl=ttl,
            )
            logger.info("Initialized official LangGraph UpstashRedisSaver checkpointer.")
            return saver
        except Exception as e:
            logger.error(
                f"Failed to initialize official UpstashRedisSaver checkpointer ({e}). "
                "Falling back to InMemorySaver.",
                exc_info=True,
            )
            return InMemorySaver()

    # Try from_env() if configured via environment variables
    try:
        from langgraph.checkpoint.upstash_redis import UpstashRedisSaver
        saver = UpstashRedisSaver.from_env(ttl=ttl)
        logger.info("Initialized official LangGraph UpstashRedisSaver from environment.")
        return saver
    except Exception:
        pass

    logger.warning("Upstash Redis credentials not configured. Falling back to InMemorySaver.")
    return InMemorySaver()
