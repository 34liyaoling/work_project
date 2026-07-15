"""多源数据向量化

支持以下来源:
- JD 文本
- 行业报告
- 政策文件
- 简历文本

优先使用 sentence-transformers；不可用时使用 TF-IDF + 截断 SVD 降维做兜底。
"""
from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Sequence

from app.core.logger import log


try:
    from sentence_transformers import SentenceTransformer  # type: ignore
    HAS_SBERT = True
except Exception:  # pragma: no cover
    SentenceTransformer = None  # type: ignore
    HAS_SBERT = False


class EmbeddingService:
    """嵌入服务"""

    DEFAULT_DIM = 384

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", dim: int = DEFAULT_DIM):
        self.model_name = model_name
        self.dim = dim
        self._model = None
        if HAS_SBERT:
            try:
                self._model = SentenceTransformer(model_name)
                self.dim = self._model.get_sentence_embedding_dimension()
                log.info(f"已加载 sentence-transformers: {model_name} (dim={self.dim})")
            except Exception as e:
                log.warning(f"加载 sentence-transformers 失败，使用降级方案: {e}")
                self._model = None

    # ----------------- 公开 -----------------
    def embed(self, text: str) -> List[float]:
        """对单条文本做向量化"""
        text = (text or "").strip()
        if not text:
            return [0.0] * self.dim
        if self._model is not None:
            try:
                vec = self._model.encode([text], normalize_embeddings=True)[0]
                return [float(x) for x in vec]
            except Exception as e:
                log.warning(f"sbert encode 失败, 降级: {e}")
        return self._fallback_embed(text)

    def embed_batch(self, texts: Sequence[str]) -> List[List[float]]:
        return [self.embed(t) for t in texts]

    def embed_jd(self, jd_text: str) -> List[float]:
        return self.embed(f"招聘JD: {jd_text}")

    def embed_industry_report(self, report_text: str) -> List[float]:
        return self.embed(f"行业报告: {report_text}")

    def embed_policy(self, policy_text: str) -> List[float]:
        return self.embed(f"政策文件: {policy_text}")

    # ----------------- 降级: 哈希 + 词袋 -----------------
    def _fallback_embed(self, text: str) -> List[float]:
        tokens = self._tokenize(text)
        counter = Counter(tokens)
        if not counter:
            return [0.0] * self.dim
        # 词频向量并通过哈希投影到固定维度
        vec = [0.0] * self.dim
        total = sum(counter.values()) or 1
        for token, count in counter.items():
            idx = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % self.dim
            tf = count / total
            vec[idx] += tf
        # L2 归一化
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        text = text.lower()
        # 中英文混合：保留英文 token + 单个汉字
        tokens = re.findall(r"[A-Za-z][A-Za-z0-9+#.\-]+|[\u4e00-\u9fa5]", text)
        return tokens


_singleton: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    global _singleton
    if _singleton is None:
        _singleton = EmbeddingService()
    return _singleton
