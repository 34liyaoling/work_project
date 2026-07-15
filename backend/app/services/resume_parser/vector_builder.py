"""技能向量构建

将候选人的技能列表编码为稠密向量（拼接多源 embedding 后取平均），
用于人岗匹配阶段的余弦相似度计算。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from app.core.logger import log
from app.services.rag.embeddings import EmbeddingService


class VectorBuilder:
    """技能向量构建器"""

    def __init__(self, embedder: Optional[EmbeddingService] = None):
        self.embedder = embedder or EmbeddingService()

    def build_skill_vector(
        self,
        skills: Sequence[Dict[str, Any]],
    ) -> List[float]:
        """将技能列表编码为单一向量（取平均 + 归一化）"""
        if not skills:
            return [0.0] * self.embedder.dim
        # 使用每个技能的标准名 embedding
        vecs: List[List[float]] = []
        weights: List[float] = []
        for s in skills:
            name = (s.get("standard_name") or s.get("skill") or "").strip()
            if not name:
                continue
            emb = self.embedder.embed(name)
            w = float(s.get("weight", 0.7) or 0.7)
            vecs.append(emb)
            weights.append(w)
        if not vecs:
            return [0.0] * self.embedder.dim
        return self._weighted_mean(vecs, weights)

    def build_resume_vector(
        self,
        skills: Sequence[Dict[str, Any]],
        raw_text: str = "",
    ) -> List[float]:
        """融合技能 + 全文 embedding（技能权重更高）"""
        skill_vec = self.build_skill_vector(skills)
        if raw_text:
            text_vec = self.embedder.embed(raw_text[:2000])
        else:
            text_vec = [0.0] * self.embedder.dim
        # 7:3 加权
        return self._blend(skill_vec, text_vec, 0.7, 0.3)

    # ----------------- 内部 -----------------
    @staticmethod
    def _weighted_mean(vecs: List[List[float]], weights: List[float]) -> List[float]:
        if not vecs:
            return []
        total_w = sum(weights) or 1.0
        dim = len(vecs[0])
        mean = [0.0] * dim
        for v, w in zip(vecs, weights):
            for i in range(dim):
                mean[i] += v[i] * w / total_w
        # 归一化
        norm = sum(x * x for x in mean) ** 0.5 or 1.0
        return [x / norm for x in mean]

    @staticmethod
    def _blend(a: List[float], b: List[float], wa: float, wb: float) -> List[float]:
        if not a:
            return b
        if not b:
            return a
        dim = min(len(a), len(b))
        out = [a[i] * wa + b[i] * wb for i in range(dim)]
        norm = sum(x * x for x in out) ** 0.5 or 1.0
        return [x / norm for x in out]


_singleton: Optional[VectorBuilder] = None


def get_vector_builder() -> VectorBuilder:
    global _singleton
    if _singleton is None:
        _singleton = VectorBuilder()
    return _singleton
