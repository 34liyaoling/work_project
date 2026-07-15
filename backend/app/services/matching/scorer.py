"""综合匹配得分计算

score = α × required_score + β × preferred_score + γ × depth_score + δ × domain_score
权重从 core.config 读取
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.core.config import settings
from app.core.logger import log


class Scorer:
    """综合评分器"""

    def __init__(
        self,
        w_required: Optional[float] = None,
        w_preferred: Optional[float] = None,
        w_depth: Optional[float] = None,
        w_domain: Optional[float] = None,
    ):
        self.w_required = w_required if w_required is not None else settings.W_REQUIRED
        self.w_preferred = w_preferred if w_preferred is not None else settings.W_PREFERRED
        self.w_depth = w_depth if w_depth is not None else settings.W_DEPTH
        self.w_domain = w_domain if w_domain is not None else settings.W_DOMAIN
        total = self.w_required + self.w_preferred + self.w_depth + self.w_domain
        if abs(total - 1.0) > 0.05:
            log.warning(f"权重之和 {total:.2f} ≠ 1.0, 将自动归一化")
            self._normalize()

    def _normalize(self) -> None:
        total = self.w_required + self.w_preferred + self.w_depth + self.w_domain
        if total <= 0:
            return
        self.w_required /= total
        self.w_preferred /= total
        self.w_depth /= total
        self.w_domain /= total

    def compute(self, breakdown: Dict[str, float]) -> Dict[str, Any]:
        """计算加权综合分

        breakdown: {"required":0.8, "preferred":0.6, "depth":0.5, "domain":0.9}
        """
        r = float(breakdown.get("required", 0.0))
        p = float(breakdown.get("preferred", 0.0))
        d = float(breakdown.get("depth", 0.0))
        dm = float(breakdown.get("domain", 0.0))
        score = (
            self.w_required * r
            + self.w_preferred * p
            + self.w_depth * d
            + self.w_domain * dm
        )
        score = round(max(0.0, min(score, 1.0)), 4)
        return {
            "overall_score": score,
            "breakdown": {
                "required": round(r, 4),
                "preferred": round(p, 4),
                "depth": round(d, 4),
                "domain": round(dm, 4),
            },
            "weights": {
                "required": self.w_required,
                "preferred": self.w_preferred,
                "depth": self.w_depth,
                "domain": self.w_domain,
            },
        }


_singleton: Optional[Scorer] = None


def get_scorer() -> Scorer:
    global _singleton
    if _singleton is None:
        _singleton = Scorer()
    return _singleton
