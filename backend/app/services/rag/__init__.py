"""LangChain RAG 框架集成

包含 4 个子模块:
- chroma_store: ChromaDB 向量存储
- embeddings: 多源数据向量化
- retriever: 检索增强生成（用于交叉验证）
- template_manager: 提示词模板管理
"""
from app.services.rag.chroma_store import ChromaStore, get_chroma_store
from app.services.rag.embeddings import EmbeddingService, get_embedding_service
from app.services.rag.retriever import RAGRetriever, get_rag_retriever
from app.services.rag.template_manager import TemplateManager, get_template_manager


__all__ = [
    "ChromaStore",
    "EmbeddingService",
    "RAGRetriever",
    "TemplateManager",
    "get_chroma_store",
    "get_embedding_service",
    "get_rag_retriever",
    "get_template_manager",
]
