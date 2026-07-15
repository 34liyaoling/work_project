"""向量数据库（Elasticsearch + ChromaDB）连接"""
from typing import Optional
from elasticsearch import Elasticsearch

from app.core.config import settings
from app.core.logger import log


class ESClient:
    """Elasticsearch 客户端封装"""

    def __init__(self):
        self._client: Optional[Elasticsearch] = None
        self._connect()

    def _connect(self):
        try:
            self._client = Elasticsearch(
                hosts=[settings.es_url],
                request_timeout=30,
                max_retries=3,
                retry_on_timeout=True
            )
            if self._client.ping():
                log.info("Elasticsearch 连接成功")
            else:
                log.warning("Elasticsearch ping 失败")
                self._client = None
        except Exception as e:
            log.error(f"Elasticsearch 连接失败: {e}")
            self._client = None

    @property
    def client(self) -> Optional[Elasticsearch]:
        return self._client

    def init_indices(self):
        """初始化索引"""
        if not self._client:
            log.warning("Elasticsearch 未连接，跳过索引初始化")
            return
        index_mappings = {
            settings.ES_INDEX_SKILL: {
                "mappings": {
                    "properties": {
                        "name": {"type": "keyword"},
                        "category": {"type": "keyword"},
                        "popularity": {"type": "float"},
                        "embedding": {"type": "dense_vector", "dims": 384},
                        "update_frequency": {"type": "integer"},
                        "last_updated": {"type": "date"}
                    }
                }
            },
            settings.ES_INDEX_JD: {
                "mappings": {
                    "properties": {
                        "jd_id": {"type": "keyword"},
                        "source": {"type": "keyword"},
                        "title": {"type": "text"},
                        "company": {"type": "text"},
                        "raw_text": {"type": "text"},
                        "skills": {"type": "keyword"},
                        "published_at": {"type": "date"},
                        "crawled_at": {"type": "date"}
                    }
                }
            }
        }
        try:
            for idx, body in index_mappings.items():
                if not self._client.indices.exists(index=idx):
                    self._client.indices.create(index=idx, body=body)
            log.info("Elasticsearch 索引初始化完成")
        except Exception as e:
            log.error(f"Elasticsearch 索引初始化失败: {e}")


es_client = ESClient()
