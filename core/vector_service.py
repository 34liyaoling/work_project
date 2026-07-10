"""ChromaDB 向量数据库服务"""

import logging
from typing import Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from config.settings import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class VectorService:
    """ChromaDB向量检索服务封装"""

    def __init__(self):
        self._client: Optional[chromadb.ClientAPI] = None
        self._collections: dict = {}

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    def connect(self) -> bool:
        """连接ChromaDB"""
        try:
            # 优先使用持久化客户端
            self._client = chromadb.PersistentClient(
                path="./data/chroma_db",
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                )
            )

            # 初始化集合
            self._init_collections()
            logger.info("ChromaDB连接成功")
            return True
        except Exception as e:
            logger.warning(f"ChromaDB PersistentClient启动失败，尝试内存模式: {e}")
            try:
                self._client = chromadb.Client()
                self._init_collections()
                logger.info("ChromaDB内存模式连接成功")
                return True
            except Exception as e2:
                logger.error(f"ChromaDB连接完全失败: {e2}")
                return False

    def _init_collections(self):
        """初始化集合"""
        collection_names = ["skills", "jobs", "resumes"]
        for name in collection_names:
            try:
                self._collections[name] = self._client.get_or_create_collection(
                    name=name,
                    metadata={"hnsw:space": "cosine"}
                )
            except Exception as e:
                logger.error(f"创建集合[{name}]失败: {e}")

    def add_vectors(self, collection: str, ids: list[str],
                    embeddings: list[list[float]], metadatas: list[dict],
                    documents: Optional[list[str]] = None):
        """添加向量数据"""
        if collection not in self._collections:
            logger.error(f"集合[{collection}]不存在")
            return False

        try:
            self._collections[collection].add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents
            )
            return True
        except Exception as e:
            logger.error(f"添加向量失败: {e}")
            return False

    def search(self, collection: str, query_embedding: list[float],
               n_results: int = 10, where: Optional[dict] = None,
               where_document: Optional[dict] = None) -> dict:
        """向量相似度搜索"""
        if collection not in self._collections:
            logger.error(f"集合[{collection}]不存在")
            return {"ids": [], "distances": [], "metadatas": []}

        kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
        }
        if where:
            kwargs["where"] = where
        if where_document:
            kwargs["where_document"] = where_document

        try:
            results = self._collections[collection].search(**kwargs)
            return results
        except Exception as e:
            logger.error(f"向量搜索失败: {e}")
            return {"ids": [[]], "distances": [[]], "metadatas": [[]]}

    def delete(self, collection: str, ids: Optional[list[str]] = None,
               where: Optional[dict] = None):
        """删除向量数据"""
        if collection not in self._collections:
            return
        try:
            self._collections[collection].delete(ids=ids, where=where)
        except Exception as e:
            logger.error(f"删除向量失败: {e}")

    def get_collection_stats(self, collection: str) -> dict:
        """获取集合统计"""
        if collection not in self._collections:
            return {"count": 0}
        try:
            return {"count": self._collections[collection].count()}
        except Exception:
            return {"count": 0}


# 全局单例
_vector_service: Optional[VectorService] = None


def get_vector_service() -> VectorService:
    """获取向量服务单例"""
    global _vector_service
    if _vector_service is None:
        _vector_service = VectorService()
    return _vector_service
