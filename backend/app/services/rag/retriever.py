"""RAG 检索增强生成

将候选问题（技能验证 / 岗位对照 / 行业趋势）嵌入后从 ChromaStore 中检索
top-k 文档片段，与 LLM 上下文拼接后生成回答。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core.logger import log
from app.services.llm_client import SparkClient
from app.services.rag.chroma_store import ChromaStore
from app.services.rag.embeddings import EmbeddingService


DEFAULT_SYSTEM = (
    "你是一名严谨的招聘与岗位分析专家。下面会提供多个来源（JD、行业报告、政策、"
    "简历）的事实片段。请仅基于这些片段回答问题，无法回答时明确说明。"
)


class RAGRetriever:
    """RAG 检索器"""

    def __init__(
        self,
        chroma: Optional[ChromaStore] = None,
        embedder: Optional[EmbeddingService] = None,
        spark: Optional[SparkClient] = None,
        top_k: int = 5,
    ):
        self.chroma = chroma or ChromaStore()
        self.embedder = embedder or EmbeddingService()
        self.spark = spark or SparkClient()
        self.top_k = top_k

    # ----------------- 写入 -----------------
    def index(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> int:
        """索引一批文档（自动嵌入）"""
        if not documents:
            return 0
        embeddings = self.embedder.embed_batch(documents)
        ids = self.chroma.add(documents, embeddings, metadatas)
        return len(ids)

    # ----------------- 检索 -----------------
    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        emb = self.embedder.embed(query)
        return self.chroma.query(emb, top_k=top_k or self.top_k)

    # ----------------- RAG 问答 -----------------
    async def answer(
        self,
        query: str,
        top_k: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """基于检索的生成式回答"""
        items = self.retrieve(query, top_k=top_k)
        if not items:
            log.warning("RAG 检索为空，回退到 LLM 直答")
            text = await self.spark.chat(
                [{"role": "user", "content": query}],
                temperature=0.2,
                max_tokens=800,
            )
            return {"answer": text, "sources": []}

        context = self._build_context(items)
        messages = [
            {"role": "system", "content": system_prompt or DEFAULT_SYSTEM},
            {"role": "user", "content": f"【问题】\n{query}\n\n【参考片段】\n{context}\n\n请基于上述片段给出严谨回答。"},
        ]
        text = await self.spark.chat(messages, temperature=0.2, max_tokens=1200)
        return {
            "answer": text,
            "sources": [
                {"id": it.get("id"), "metadata": it.get("metadata", {}), "score": it.get("score") or it.get("distance")}
                for it in items
            ],
        }

    @staticmethod
    def _build_context(items: List[Dict[str, Any]]) -> str:
        lines = []
        for i, it in enumerate(items, 1):
            meta = it.get("metadata") or {}
            tag = meta.get("source_type") or meta.get("source") or "context"
            lines.append(f"[{i}] ({tag}) {it.get('document', '')[:500]}")
        return "\n".join(lines)


_singleton: Optional[RAGRetriever] = None


def get_rag_retriever() -> RAGRetriever:
    global _singleton
    if _singleton is None:
        _singleton = RAGRetriever()
    return _singleton
