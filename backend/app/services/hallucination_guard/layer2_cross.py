"""第二层 - 交叉验证

- 至少 3 个独立数据源同时支持某条信息 → 高置信
- 与 O*NET 公开职业标准对照，差异过大则降权
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Sequence

from app.core.logger import log


# 模拟 O*NET 标准化技能参考集（按 category）
ONET_REFERENCE: Dict[str, List[str]] = {
    "AI工程师": ["Python", "PyTorch", "深度学习", "机器学习", "Linux", "Git"],
    "后端开发": ["Java", "Python", "MySQL", "Redis", "Linux", "Git"],
    "前端开发": ["JavaScript", "TypeScript", "React", "Vue", "CSS", "HTML"],
    "数据科学": ["Python", "SQL", "Pandas", "统计学", "机器学习", "可视化"],
    "数据工程": ["Python", "SQL", "Spark", "Flink", "Airflow", "Kafka"],
    "测试开发": ["Python", "Java", "Selenium", "Linux", "Shell", "Git"],
    "运维": ["Linux", "Shell", "Docker", "Kubernetes", "Prometheus", "Ansible"],
    "DevOps": ["Docker", "Kubernetes", "Jenkins", "Terraform", "AWS", "Prometheus"],
    "嵌入式": ["C", "C++", "RTOS", "Linux", "ARM", "单片机"],
    "芯片": ["Verilog", "VHDL", "数字电路", "SystemVerilog", "UVM", "脚本"],
}


class CrossValidator:
    """第二层交叉验证器"""

    def __init__(self, min_sources: int = 3, onet_overlap_threshold: float = 0.5):
        self.min_sources = min_sources
        self.onet_overlap_threshold = onet_overlap_threshold

    def validate_skill(
        self,
        skill: str,
        jd_records: Sequence[Dict[str, Any]],
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """验证某条技能是否被多源支持"""
        sources = set()
        for jd in jd_records or []:
            jd_skills = set(s.lower() for s in jd.get("skills", []) or [])
            if skill.lower() in jd_skills:
                src = (jd.get("source") or "unknown").lower()
                sources.add(src)
        onet_overlap = self._onet_overlap(skill, category)
        high_conf = len(sources) >= self.min_sources
        return {
            "skill": skill,
            "source_count": len(sources),
            "sources": sorted(sources),
            "onet_match": onet_overlap >= self.onet_overlap_threshold,
            "onet_overlap": round(onet_overlap, 3),
            "high_confidence": high_conf and onet_overlap >= 0.3,
        }

    def validate_role(
        self,
        role_card: Dict[str, Any],
        jd_records: Sequence[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """验证岗位定义的交叉一致性"""
        category = role_card.get("category")
        required = [s.get("skill") for s in role_card.get("required_skills", []) if s.get("skill")]
        skill_reports = [self.validate_skill(s, jd_records, category) for s in required]

        high_count = sum(1 for r in skill_reports if r["high_confidence"])
        onet_match_count = sum(1 for r in skill_reports if r["onet_match"])
        total = max(1, len(skill_reports))
        onet_score = round(onet_match_count / total, 3)
        confidence_score = round(high_count / total, 3)

        passes = onet_score >= 0.3 and confidence_score >= 0.3
        return {
            "role_title": role_card.get("job_title", "unknown"),
            "skill_reports": skill_reports,
            "onet_score": onet_score,
            "confidence_score": confidence_score,
            "high_confidence_count": high_count,
            "passes": passes,
        }

    # ----------------- 内部 -----------------
    def _onet_overlap(self, skill: str, category: Optional[str]) -> float:
        if not category:
            return 0.0
        ref = ONET_REFERENCE.get(category, [])
        if not ref:
            return 0.0
        return 1.0 if skill in ref else 0.0


_singleton: Optional[CrossValidator] = None


def get_cross_validator() -> CrossValidator:
    global _singleton
    if _singleton is None:
        _singleton = CrossValidator()
    return _singleton
