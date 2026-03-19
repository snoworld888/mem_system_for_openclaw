"""
长期记忆管理器
- 使用 ChromaDB 做向量存储
- 使用 sentence-transformers 做本地嵌入（无需API）
- 支持语义检索、重要性过滤、访问频率权重
"""
from __future__ import annotations
import os
import json
import hashlib
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import chromadb
from chromadb.config import Settings as ChromaSettings

from src.memory.models import MemoryItem, MemoryType, ImportanceLevel
from src.utils.token_counter import count_tokens
from src.utils.embedder import EmbeddingManager

if TYPE_CHECKING:
    from src.config import Settings


class LongTermMemoryManager:
    def __init__(self, settings: "Settings"):
        self.settings = settings
        self._embedder = EmbeddingManager(settings)
        db_path = os.path.join(settings.data_dir, "chromadb")
        os.makedirs(db_path, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=db_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        # 每种记忆类型一个collection
        self._collections: dict[MemoryType, chromadb.Collection] = {}
        for mt in [MemoryType.LONG_TERM, MemoryType.PROFILE, MemoryType.RULE]:
            self._collections[mt] = self._client.get_or_create_collection(
                name=f"mem_{mt.value}",
                metadata={"hnsw:space": "cosine"},
            )

    def _embed(self, texts: list[str]) -> list[list[float]]:
        return self._embedder.encode(texts)

    def add_memory(self, item: MemoryItem) -> str:
        """添加一条长期记忆"""
        col = self._collections.get(item.memory_type)
        if col is None:
            raise ValueError(f"不支持的记忆类型: {item.memory_type}")

        text_to_embed = item.summary if item.summary else item.content
        embeddings = self._embed([text_to_embed])

        item.token_count = count_tokens(item.content)
        meta = {
            "session_id": item.session_id,
            "memory_type": item.memory_type.value,
            "importance": item.importance.value,
            "tags": json.dumps(item.tags, ensure_ascii=False),
            "created_at": item.created_at.isoformat(),
            "accessed_at": item.accessed_at.isoformat(),
            "access_count": item.access_count,
            "token_count": item.token_count,
        }

        col.upsert(
            ids=[item.id],
            embeddings=embeddings,
            documents=[item.content],
            metadatas=[meta],
        )
        return item.id

    def search(
        self,
        query: str,
        memory_type: MemoryType,
        session_id: str | None = None,
        top_k: int = 5,
        threshold: float = 0.3,
        min_importance: ImportanceLevel = ImportanceLevel.LOW,
    ) -> list[tuple[MemoryItem, float]]:
        """
        语义搜索记忆。
        返回: [(MemoryItem, score), ...] 按相关性降序
        """
        col = self._collections.get(memory_type)
        if col is None:
            return []

        if col.count() == 0:
            return []

        query_embed = self._embed([query])

        where: dict = {"importance": {"$gte": min_importance.value}}
        if session_id:
            where = {
                "$and": [
                    {"importance": {"$gte": min_importance.value}},
                    {"session_id": {"$eq": session_id}},
                ]
            }

        try:
            result = col.query(
                query_embeddings=query_embed,
                n_results=min(top_k * 2, col.count()),  # 多取一些再过滤
                where=where,
                include=["documents", "metadatas", "distances"],
            )
        except Exception:
            return []

        items_with_score: list[tuple[MemoryItem, float]] = []
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        ids = result.get("ids", [[]])[0]

        for i, (doc, meta, dist, rid) in enumerate(zip(docs, metas, distances, ids)):
            # cosine distance -> similarity
            score = 1.0 - float(dist)
            if score < threshold:
                continue
            item = MemoryItem(
                id=rid,
                session_id=meta.get("session_id", ""),
                memory_type=memory_type,
                content=doc,
                importance=ImportanceLevel(meta.get("importance", 2)),
                tags=json.loads(meta.get("tags", "[]")),
                token_count=meta.get("token_count", 0),
                access_count=meta.get("access_count", 0),
            )
            items_with_score.append((item, score))

        # 按 score * importance 排序
        items_with_score.sort(
            key=lambda x: x[1] * x[0].importance.value,
            reverse=True,
        )
        return items_with_score[:top_k]

    def get_all(
        self,
        memory_type: MemoryType,
        session_id: str | None = None,
    ) -> list[MemoryItem]:
        """获取某类型的全部记忆（用于Profile/Rule，数量少）"""
        col = self._collections.get(memory_type)
        if col is None or col.count() == 0:
            return []

        where = {}
        if session_id:
            where = {"session_id": {"$eq": session_id}}

        try:
            result = col.get(
                where=where if where else None,
                include=["documents", "metadatas"],
            )
        except Exception:
            return []

        items = []
        for rid, doc, meta in zip(
            result.get("ids", []),
            result.get("documents", []),
            result.get("metadatas", []),
        ):
            item = MemoryItem(
                id=rid,
                session_id=meta.get("session_id", ""),
                memory_type=memory_type,
                content=doc,
                importance=ImportanceLevel(meta.get("importance", 2)),
                tags=json.loads(meta.get("tags", "[]")),
                token_count=meta.get("token_count", 0),
                access_count=meta.get("access_count", 0),
            )
            items.append(item)

        # 按priority/importance排序（metadata里存的importance当priority）
        items.sort(key=lambda x: x.importance.value, reverse=True)
        return items

    def delete_memory(self, memory_type: MemoryType, memory_id: str):
        col = self._collections.get(memory_type)
        if col:
            col.delete(ids=[memory_id])

    def update_access(self, memory_type: MemoryType, memory_id: str):
        """更新访问时间和次数"""
        col = self._collections.get(memory_type)
        if not col:
            return
        try:
            result = col.get(ids=[memory_id], include=["metadatas"])
            if result["ids"]:
                meta = result["metadatas"][0]
                meta["accessed_at"] = datetime.now(timezone.utc).isoformat()
                meta["access_count"] = meta.get("access_count", 0) + 1
                col.update(ids=[memory_id], metadatas=[meta])
        except Exception:
            pass

    def get_stats(self) -> dict:
        return {
            mt.value: self._collections[mt].count()
            for mt in self._collections
        }
