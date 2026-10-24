"""Qdrant Cloud vector store and persistent video embedding cache."""

import asyncio
import logging
import uuid
from typing import Any

from langchain_core.documents import Document
from qdrant_client import QdrantClient, models

from backend.config import QDRANT_API_KEY, QDRANT_CLUSTER_ENDPOINT, QDRANT_COLLECTION
from backend.core.ingestion.embeddings import load_embeddings

logger = logging.getLogger(__name__)


class QdrantUnavailable(RuntimeError):
    """Raised when Qdrant is not configured or a Cloud request cannot complete."""


def _filter_for(video_id: str, kind: str):
    return models.Filter(
        must=[
            models.FieldCondition(key="video_id", match=models.MatchValue(value=video_id)),
            models.FieldCondition(key="kind", match=models.MatchValue(value=kind)),
        ]
    )


class QdrantRetriever:
    """Minimal LangChain-compatible retriever used by the existing hybrid workflow."""

    def __init__(self, client, collection_name: str, video_id: str, k: int):
        self.client = client
        self.collection_name = collection_name
        self.video_id = video_id
        self.k = k
        self.embeddings = load_embeddings()

    async def ainvoke(self, query: str) -> list[Document]:
        return await asyncio.to_thread(self.invoke, query)

    def invoke(self, query: str) -> list[Document]:
        query_vector = self.embeddings.embed_query(query)
        result = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=_filter_for(self.video_id, "chunk"),
            limit=self.k,
            with_payload=True,
        )
        points = getattr(result, "points", result)
        return [
            Document(
                page_content=str(point.payload.get("text", "")),
                metadata=dict(point.payload.get("metadata") or {}),
            )
            for point in points
            if point.payload and point.payload.get("text")
        ]


class QdrantVideoVectorStore:
    """Vector store adapter exposing ``as_retriever`` for hybrid retrieval."""

    def __init__(self, client, collection_name: str, video_id: str):
        self.client = client
        self.collection_name = collection_name
        self.video_id = video_id

    def as_retriever(self, search_kwargs: dict | None = None):
        return QdrantRetriever(
            self.client,
            self.collection_name,
            self.video_id,
            int((search_kwargs or {}).get("k", 5)),
        )


class QdrantVideoCache:
    """Persist and load a video's transcript chunks and embeddings in Qdrant Cloud."""

    def __init__(self, endpoint: str = QDRANT_CLUSTER_ENDPOINT, api_key: str = QDRANT_API_KEY):
        self.endpoint = endpoint
        self.api_key = api_key
        self.collection_name = QDRANT_COLLECTION
        self._client = None

    @property
    def enabled(self) -> bool:
        return bool(self.endpoint and self.api_key)

    def _get_client(self):
        if not self.enabled:
            raise QdrantUnavailable(
                "Qdrant Cloud is not configured. Please set QDRANT_CLUSTER_ENDPOINT and QDRANT_API_KEY."
            )
        if self._client is None:
            self._client = QdrantClient(url=self.endpoint, api_key=self.api_key, timeout=10)
        return self._client

    def ping(self) -> bool:
        """Make one inexpensive authenticated request to Qdrant Cloud."""
        try:
            self._get_client().get_collections()
            return True
        except Exception as exc:
            logger.warning("Qdrant Cloud is unavailable: %s", exc)
            return False

    def load_video(self, video_id: str) -> dict[str, Any] | None:
        """Return a persisted video manifest and chunk documents, or ``None`` on a cache miss."""
        client = self._get_client()
        try:
            manifest_points, _ = client.scroll(
                collection_name=self.collection_name,
                scroll_filter=_filter_for(video_id, "manifest"),
                limit=1,
                with_payload=True,
                with_vectors=False,
            )
        except Exception as exc:
            raise QdrantUnavailable(f"Qdrant lookup failed: {exc}") from exc
        if not manifest_points:
            return None

        documents = []
        offset = None
        while True:
            try:
                points, offset = client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=_filter_for(video_id, "chunk"),
                    limit=256,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                )
            except Exception as exc:
                raise QdrantUnavailable(f"Qdrant chunk load failed: {exc}") from exc
            documents.extend(
                Document(page_content=str(p.payload.get("text", "")), metadata=dict(p.payload.get("metadata") or {}))
                for p in points
                if p.payload and p.payload.get("text")
            )
            if offset is None:
                break

        if not documents:
            logger.warning("Qdrant manifest for %s had no chunks; treating it as a cache miss.", video_id)
            return None
        manifest = manifest_points[0].payload.get("manifest") or {}
        return {"documents": documents, **manifest}

    def store_video(
        self,
        video_id: str,
        documents: list[Document],
        metadata: dict[str, Any],
        transcript_text: str,
        transcript_segments: list[dict[str, Any]],
    ) -> QdrantVideoVectorStore:
        """Embed once, upsert chunks, then write a manifest last to mark the video ready."""
        if not documents:
            raise ValueError("Cannot persist an empty video index.")
        client = self._get_client()
        embeddings = load_embeddings()
        vectors = embeddings.embed_documents([document.page_content for document in documents])
        if not vectors:
            raise ValueError("Embedding provider returned no vectors.")
        try:
            if not client.collection_exists(self.collection_name):
                client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(size=len(vectors[0]), distance=models.Distance.COSINE),
                )
            points = [
                models.PointStruct(
                    id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"youtube:{video_id}:chunk:{index}")),
                    vector=vector,
                    payload={
                        "kind": "chunk",
                        "video_id": video_id,
                        "text": document.page_content,
                        "metadata": document.metadata,
                    },
                )
                for index, (document, vector) in enumerate(zip(documents, vectors, strict=True))
            ]
            client.upsert(collection_name=self.collection_name, points=points, wait=True)
            # Writing this last means a future reader only treats fully-uploaded videos as cache hits.
            manifest = {"metadata": metadata, "transcript_text": transcript_text, "transcript_segments": transcript_segments}
            client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"youtube:{video_id}:manifest")),
                        vector=[0.0] * len(vectors[0]),
                        payload={"kind": "manifest", "video_id": video_id, "manifest": manifest},
                    )
                ],
                wait=True,
            )
        except Exception as exc:
            raise QdrantUnavailable(f"Qdrant upload failed: {exc}") from exc
        return QdrantVideoVectorStore(client, self.collection_name, video_id)

    def vector_store_for(self, video_id: str) -> QdrantVideoVectorStore:
        return QdrantVideoVectorStore(self._get_client(), self.collection_name, video_id)
