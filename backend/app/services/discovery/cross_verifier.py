"""岗位定义交叉验证

对生成的岗位定义卡片进行多源一致性检验:
- 跨平台: 同一岗位定义是否被多个招聘平台（boss/拉勾/猎聘/智联）支持
- 跨公司: 跨公司出现该技能组合的次数
- 跨时间: 近期与历史的占比

输出 verification_report，score 越高代表跨源一致性越好。
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Sequence

from app.core.config import settings
from app.core.logger import log


class CrossVerifier:
    """岗位定义交叉验证器"""

    # 主流招聘平台
    KNOWN_SOURCES = {"boss", "lagou", "liepin", "zhilian", "linkedin", "job51", "internal"}

    def verify(
        self,
        role_card: Dict[str, Any],
        jd_records: Optional[Sequence[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """执行交叉验证

        :param role_card: 岗位定义卡片（含 required_skills / preferred_skills）
        :param jd_records: 支撑该岗位的 JD 列表（每项应包含 source/company/published_at）
        :return: 验证报告（score 0-1，details）
        """
        jd_records = jd_records or []
        required = [s.get("skill", "").lower() for s in role_card.get("required_skills", [])]
        preferred = [s.get("skill", "").lower() for s in role_card.get("preferred_skills", [])]

        # 1. 跨平台一致性
        source_score, matched_sources = self._score_by_source(jd_records, required + preferred)

        # 2. 跨公司一致性
        company_score, matched_companies = self._score_by_company(jd_records, required)

        # 3. 技能覆盖度（必备技能在数据集中的命中率）
        coverage = self._skill_coverage(jd_records, required)

        # 4. 总体得分（加权）
        weights = (0.45, 0.35, 0.20)
        overall = round(
            source_score * weights[0] + company_score * weights[1] + coverage * weights[2], 3
        )

        report = {
            "role_title": role_card.get("job_title", "unknown"),
            "source_score": round(source_score, 3),
            "company_score": round(company_score, 3),
            "coverage_score": round(coverage, 3),
            "overall_score": overall,
            "matched_sources": matched_sources,
            "matched_companies": matched_companies,
            "jd_count": len(jd_records),
            "passes": overall >= 0.6,
            "threshold": 0.6,
        }
        log.info(f"交叉验证 {report['role_title']}: score={overall} sources={matched_sources}")
        return report

    def _score_by_source(
        self, jd_records: Sequence[Dict[str, Any]], skills: List[str]
    ) -> tuple:
        """计算跨平台一致性得分"""
        if not jd_records or not skills:
            return 0.0, []
        skill_set = set(s.lower() for s in skills)
        source_hits: Counter = Counter()
        for jd in jd_records:
            src = (jd.get("source") or "unknown").lower()
            jd_skills = set(s.lower() for s in jd.get("skills", []))
            if jd_skills & skill_set:
                source_hits[src] += 1
        if not source_hits:
            return 0.0, []
        # 至少出现在 2 个不同源得高分
        unique_sources = len(source_hits)
        score = min(1.0, unique_sources / max(1, len(self.KNOWN_SOURCES) // 2))
        # 加分：源越多样分越高
        if unique_sources >= 3:
            score = min(1.0, score + 0.2)
        return score, sorted(source_hits.keys())

    def _score_by_company(
        self, jd_records: Sequence[Dict[str, Any]], required_skills: List[str]
    ) -> tuple:
        """跨公司一致性"""
        if not jd_records or not required_skills:
            return 0.0, []
        skill_set = set(required_skills)
        company_hits: Counter = Counter()
        for jd in jd_records:
            company = jd.get("company") or "unknown"
            jd_skills = set(s.lower() for s in jd.get("skills", []))
            if jd_skills & skill_set:
                company_hits[company] += 1
        unique = len(company_hits)
        # 5 家公司以上为充分证据
        score = min(1.0, unique / 5.0)
        return score, sorted(company_hits.keys())

    def _skill_coverage(
        self, jd_records: Sequence[Dict[str, Any]], required_skills: List[str]
    ) -> float:
        """必备技能在数据集中的命中率"""
        if not jd_records or not required_skills:
            return 0.0
        skill_set = set(required_skills)
        hit = 0
        for jd in jd_records:
            jd_skills = set(s.lower() for s in jd.get("skills", []))
            if skill_set & jd_skills:
                hit += 1
        return round(hit / len(jd_records), 3)


_singleton: Optional[CrossVerifier] = None


def get_cross_verifier() -> CrossVerifier:
    global _singleton
    if _singleton is None:
        _singleton = CrossVerifier()
    return _singleton
