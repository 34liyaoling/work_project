"""ChromaDB 向量存储

提供 collection 粒度的 add/query 封装；当 chromadb 不可用时退化为内存模式。
"""
from __future__ import annotations

import os
import uuid
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logger import log


try:
    import chromadb  # type: ignore
    from chromadb.config import Settings as ChromaSettings  # type: ignore
    HAS_CHROMA = True
except Exception:  # pragma: no cover
    chromadb = None  # type: ignore
    ChromaSettings = None  # type: ignore
    HAS_CHROMA = False


class ChromaStore:
    """ChromaDB 持久化向量存储"""

    def __init__(self, persist_dir: Optional[str] = None, collection_name: str = "competency_chunks"):
        self.persist_dir = persist_dir or settings.CHROMA_PERSIST_DIR
        self.collection_name = collection_name
        self._client = None
        self._collection = None
        self._init()

    def _init(self) -> None:
        if not HAS_CHROMA:
            log.warning("chromadb 未安装，进入内存 mock 模式")
            self._memory: Dict[str, Dict[str, Any]] = {}
            return
        try:
            os.makedirs(self.persist_dir, exist_ok=True)
            self._client = chromadb.PersistentClient(path=self.persist_dir)
            self._collection = self._client.get_or_create_collection(self.collection_name)
            log.info(f"Chroma 集合已就绪: {self.collection_name}")
        except Exception as e:
            log.error(f"Chroma 初始化失败: {e}")
            self._client = None
            self._collection = None
            self._memory = {}

    # ----------------- 写入 -----------------
    def add(
        self,
        documents: List[str],
        embeddings: Optional[List[List[float]]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """写入文档 + 向量"""
        if not documents:
            return []
        ids = ids or [str(uuid.uuid4()) for _ in documents]
        metadatas = metadatas or [{} for _ in documents]

        if self._collection is not None:
            try:
                self._collection.add(
                    documents=documents,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    ids=ids,
                )
                log.info(f"Chroma add: {len(documents)} 条")
                return ids
            except Exception as e:
                log.error(f"Chroma add 失败: {e}")

        # 内存降级
        for i, doc in enumerate(documents):
            self._memory[ids[i]] = {
                "document": doc,
                "embedding": embeddings[i] if embeddings else None,
                "metadata": metadatas[i],
            }
        return ids

    # ----------------- 查询 -----------------
    def query(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """向量检索"""
        if self._collection is not None:
            try:
                res = self._collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k,
                    where=where,
                )
                items: List[Dict[str, Any]] = []
                for i, doc in enumerate(res.get("documents", [[]])[0]):
                    items.append({
                        "id": res["ids"][0][i] if res.get("ids") else None,
                        "document": doc,
                        "metadata": (res.get("metadatas") or [[]])[0][i] if res.get("metadatas") else {},
                        "distance": (res.get("distances") or [[]])[0][i] if res.get("distances") else 0.0,
                    })
                return items
            except Exception as e:
                log.error(f"Chroma query 失败: {e}")
        return self._memory_query(query_embedding, top_k, where)

    def count(self) -> int:
        if self._collection is not None:
            try:
                return int(self._collection.count())
            except Exception:
                return 0
        return len(getattr(self, "_memory", {}))

    # ----------------- 内部: 内存降级 -----------------
    def _memory_query(
        self,
        query_embedding: List[float],
        top_k: int,
        where: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        import math
        memory = getattr(self, "_memory", {})
        scored: List[Dict[str, Any]] = []
        for _id, item in memory.items():
            emb = item.get("embedding")
            if not emb:
                continue
            # cosine similarity
            dot = sum(a * b for a, b in zip(query_embedding, emb))
            norm_a = math.sqrt(sum(a * a for a in query_embedding)) or 1.0
            norm_b = math.sqrt(sum(b * b for b in emb)) or 1.0
            sim = dot / (norm_a * norm_b)
            scored.append({
                "id": _id,
                "document": item.get("document"),
                "metadata": item.get("metadata", {}),
                "score": sim,
            })
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]


_singleton: Optional[ChromaStore] = None


def get_chroma_store() -> ChromaStore:
    global _singleton
    if _singleton is None:
        _singleton = ChromaStore()
    return _singleton
