"""
LangGraph Checkpointer backed by Upstash Redis.
Utilizes the official `langgraph-checkpoint-upstash-redis` module with an async bridge
to support LangGraph async streaming execution (astream_events / astream) while retaining
serverless REST persistence.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Sequence, Tuple, AsyncIterator
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    Checkpoint,
    CheckpointMetadata,
    ChannelVersions,
    CheckpointTuple,
)
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.upstash_redis import UpstashRedisSaver

from backend.config import UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN
from backend.services.redis import DEFAULT_TTL_SECONDS

logger = logging.getLogger(__name__)


class AsyncUpstashRedisSaver(UpstashRedisSaver):
    """
    Subclass of UpstashRedisSaver that bridges synchronous REST calls to async
    (aget_tuple, aput, aput_writes, alist) via asyncio.to_thread, enabling seamless
    LangGraph astream_events and async Pregel loop execution.
    """

    async def aget_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        return await asyncio.to_thread(self.get_tuple, config)

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        return await asyncio.to_thread(self.put, config, checkpoint, metadata, new_versions)

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[Tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        return await asyncio.to_thread(self.put_writes, config, writes, task_id, task_path)

    async def alist(
        self,
        config: Optional[RunnableConfig],
        *,
        filter: Optional[Dict[str, Any]] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None,
    ) -> AsyncIterator[CheckpointTuple]:
        loop = asyncio.get_running_loop()
        tuples = await loop.run_in_executor(
            None, lambda: list(self.list(config, filter=filter, before=before, limit=limit))
        )
        for t in tuples:
            yield t


def get_redis_checkpointer(
    url: Optional[str] = None,
    token: Optional[str] = None,
    ttl: Optional[int] = DEFAULT_TTL_SECONDS,
):
    """Factory to initialize the official LangGraph Upstash Redis checkpointer.

    Uses `AsyncUpstashRedisSaver` with REST API connection info.
    Falls back gracefully to InMemorySaver if credentials are not configured or upon connection error.
    """
    rest_url = url or UPSTASH_REDIS_REST_URL
    rest_token = token or UPSTASH_REDIS_REST_TOKEN

    if rest_url and rest_token:
        try:
            saver = AsyncUpstashRedisSaver.from_conn_info(
                url=rest_url,
                token=rest_token,
                ttl=ttl,
            )
            logger.info("Initialized official LangGraph AsyncUpstashRedisSaver checkpointer.")
            return saver
        except Exception as e:
            logger.error(
                f"Failed to initialize official AsyncUpstashRedisSaver checkpointer ({e}). "
                "Falling back to InMemorySaver.",
                exc_info=True,
            )
            return InMemorySaver()

    # Try from_env() if configured via environment variables
    try:
        saver = AsyncUpstashRedisSaver.from_env(ttl=ttl)
        logger.info("Initialized official LangGraph AsyncUpstashRedisSaver from environment.")
        return saver
    except Exception:
        pass

    logger.warning("Upstash Redis credentials not configured. Falling back to InMemorySaver.")
    return InMemorySaver()
