"""前瞻性信号引入机制

将尚未在 JD 中高频出现、但出现在行业报告/政策中的"前瞻性"技能引入
到趋势预测体系，标记为 emerging / watchlist。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from app.core.logger import log


# 已知的前瞻性信号 → 阶段标签
WATCHLIST_SKILLS: Dict[str, str] = {
    "Agent": "adopting",
    "Function Calling": "adopting",
    "MCP": "watchlist",
    "RAG": "mainstream",
    "向量数据库": "mainstream",
    "Prompt Engineering": "mainstream",
    "数字孪生": "watchlist",
    "工业 AI": "adopting",
    "边缘计算": "adopting",
    "WebGPU": "watchlist",
    "Solid.js": "watchlist",
    "MoE": "adopting",
    "Diffusion": "mainstream",
    "多模态": "adopting",
}


class SignalIntroducer:
    """前瞻性信号引入器"""

    def introduce(
        self,
        trend_keywords: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """对每个趋势词补充引入前瞻性信号

        :return: [{"keyword":"...", "phase":"mainstream|adopting|watchlist", "rationale":"..."}]
        """
        results: List[Dict[str, Any]] = []
        for kw in trend_keywords or []:
            term = (kw.get("keyword") or "").strip()
            phase = WATCHLIST_SKILLS.get(term, "adopting")
            results.append({
                "keyword": term,
                "phase": phase,
                "category": kw.get("category", "其它"),
                "trend_weight": float(kw.get("weight", 0.5) or 0.5),
                "rationale": self._rationale(phase),
            })
        log.info(f"前瞻性信号: {len(results)} 条")
        return results

    @staticmethod
    def _rationale(phase: str) -> str:
        return {
            "mainstream": "已在多个行业广泛使用，可直接纳入必备候选",
            "adopting": "市场采纳中，建议作为加分项并提前布局",
            "watchlist": "早期阶段，建议保持关注与试点",
        }.get(phase, "默认采纳阶段")


_singleton: Optional[SignalIntroducer] = None


def get_signal_introducer() -> SignalIntroducer:
    global _singleton
    if _singleton is None:
        _singleton = SignalIntroducer()
    return _singleton
