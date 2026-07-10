"""数据库操作工具 - 向量数据库CRUD等"""

import json
import logging
from typing import Optional
from langchain_core.tools import BaseTool
from core.vector_service import get_vector_service
from core.llm_service import get_llm_service

logger = logging.getLogger(__name__)


class VectorDBTool(BaseTool):
    """ChromaDB向量数据库操作工具"""
    name: str = "vector_db"
    description: str = "操作向量数据库，添加/搜索/删除向量数据"

    def _run(self, operation: str = "search", **kwargs) -> str:
        """执行向量数据库操作"""
        vector = get_vector_service()

        try:
            if operation == "search":
                query_emb = kwargs.get("query_embedding")
                if not query_emb and kwargs.get("query_text"):
                    llm = get_llm_service()
                    query_emb = llm.generate_embedding(kwargs["query_text"])

                if not query_emb:
                    return json.dumps({"error": "需要query_embedding或query_text"})

                result = vector.search(
                    collection=kwargs.get("collection", "resumes"),
                    query_embedding=query_emb,
                    n_results=kwargs.get("n_results", 5),
                )
                return json.dumps(result, ensure_ascii=False, default=str)

            elif operation == "add":
                ids = kwargs.get("ids", [])
                embeddings = kwargs.get("embeddings", [])
                metadatas = kwargs.get("metadatas", [])
                documents = kwargs.get("documents", [])

                success = vector.add_vectors(
                    collection=kwargs.get("collection", "resumes"),
                    ids=ids, embeddings=embeddings,
                    metadatas=metadatas, documents=documents,
                )
                return json.dumps({"success": success, "count": len(ids)})

            elif operation == "stats":
                coll = kwargs.get("collection", "resumes")
                stats = vector.get_collection_stats(coll)
                return json.dumps(stats)

            else:
                return json.dumps({"error": f"不支持的操作: {operation}"})

        except Exception as e:
            return json.dumps({"error": str(e)})


class EmbeddingTool(BaseTool):
    """文本向量化工具"""
    name: str = "embedding"
    description: str = "将文本转换为向量表示"

    def _run(self, text: str) -> str:
        llm = get_llm_service()
        embedding = llm.generate_embedding(text)
        if embedding:
            return json.dumps({
                "success": True,
                "dimension": len(embedding),
                "embedding_preview": embedding[:5],  # 只返回前5维预览
            })
        return json.dumps({"success": False, "error": "向量化失败"})
