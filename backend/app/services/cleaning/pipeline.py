"""清洗与交叉验证 pipeline

完整清洗流程：

    1. 预处理（去 HTML / 特殊字符 / 标准化）
    2. 去重（SimHash + 余弦相似度 + 技能组合指纹）
    3. 技能标准化（别名 → 标准名）
    4. 质量评估（来源 / 时效 / 完整度 / 文本质量）
    5. 交叉验证（多源 / 多公司 / 频次）
    6. 幻觉检测（O*NET 对照 + 模糊匹配）

返回 :class:`CleanedRecord`，附带最终可信度评分与置信度等级。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.core.logger import log

from app.services.cleaning.preprocessor import TextPreprocessor
from app.services.cleaning.deduplicator import SimHashDeduplicator
from app.services.cleaning.skill_normalizer import SkillNormalizer
from app.services.cleaning.credibility_scorer import CredibilityScorer
from app.services.cleaning.cross_validator import CrossValidator, ValidationResult
from app.services.cleaning.onet_verifier import OnetVerifier, OnetVerifyResult


@dataclass
class CleanedRecord:
    """清洗后的单条记录"""

    data: Dict[str, Any]
    credibility: float
    confidence_level: str  # "high" / "medium" / "low"
    normalized_skills: List[Dict[str, str]] = field(default_factory=list)
    onet_result: Optional[Dict[str, Any]] = None
    validation: Optional[Dict[str, Any]] = None
    is_duplicate: bool = False


@dataclass
class CleaningPipeline:
    """清洗 pipeline 编排器"""

    preprocessor: TextPreprocessor = field(default_factory=TextPreprocessor)
    deduplicator: SimHashDeduplicator = field(default_factory=SimHashDeduplicator)
    normalizer: SkillNormalizer = field(default_factory=SkillNormalizer)
    scorer: CredibilityScorer = field(default_factory=CredibilityScorer)
    cross_validator: CrossValidator = field(default_factory=CrossValidator)
    onet_verifier: OnetVerifier = field(default_factory=OnetVerifier)

    # -------------------------------------------------------- 入口
    def run(
        self,
        items: List[Dict[str, Any]],
        reset_dedup: bool = True,
    ) -> List[CleanedRecord]:
        """执行完整 pipeline"""
        if reset_dedup:
            self.deduplicator.reset()

        # 1) 预处理
        items = [self._preprocess(it) for it in items]
        items = [it for it in items if it]  # 过滤空

        # 2) 去重
        before = len(items)
        items = self.deduplicator.deduplicate(items, text_key="raw_text", skill_key="skills", id_key="jd_id")
        log.info(f"[CleaningPipeline] 去重：{before} → {len(items)}")

        # 3) 技能标准化
        for it in items:
            skills = it.get("skills") or []
            if isinstance(skills, str):
                skills = [s.strip() for s in skills.split(",") if s.strip()]
            normalized = self.normalizer.normalize_list(skills)
            it["skills"] = [n["skill"] for n in normalized]
            it["skills_detail"] = normalized

        # 4) + 5) 质量评估 + 交叉验证（先做交叉，再把 score 注入每条）
        cross_results = self.cross_validator.validate_batch(items)
        sig_to_cross: Dict[str, ValidationResult] = {r.signature: r for r in cross_results}
        for it, vr in zip(items, cross_results):
            it["cross_source_bonus"] = vr.confidence
            it["cross_level"] = vr.level
            it["cross_signature"] = vr.signature

        # 6) 可信度评分
        for it in items:
            detail = self.scorer.score(it)
            it["credibility_score"] = detail.final_score
            it["credibility_reasons"] = detail.reasons

        # 7) O*NET 对照（幻觉检测）
        for it in items:
            r = self.onet_verifier.verify_jd(it)
            it["onet_verified_count"] = len(r.verified)
            it["onet_unverified_count"] = len(r.unverified)
            it["onet_coverage"] = r.coverage
            it["onet_novelty"] = r.novelty_score
            it["onet_fuzzy"] = r.fuzzy_matched

        # 输出 CleanedRecord
        out: List[CleanedRecord] = []
        for it in items:
            out.append(CleanedRecord(
                data=it,
                credibility=float(it.get("credibility_score", 0.0)),
                confidence_level=str(it.get("cross_level", "low")),
                normalized_skills=it.get("skills_detail", []),
                onet_result={
                    "verified_count": it.get("onet_verified_count", 0),
                    "unverified_count": it.get("onet_unverified_count", 0),
                    "coverage": it.get("onet_coverage", 0.0),
                    "novelty_score": it.get("onet_novelty", 0.0),
                    "fuzzy_matched": it.get("onet_fuzzy", {}),
                },
                validation={
                    "source_count": sig_to_cross[it["cross_signature"]].source_count,
                    "company_count": sig_to_cross[it["cross_signature"]].company_count,
                    "jd_count": sig_to_cross[it["cross_signature"]].jd_count,
                    "confidence": sig_to_cross[it["cross_signature"]].confidence,
                    "level": sig_to_cross[it["cross_signature"]].level,
                },
                is_duplicate=False,
            ))
        # 统计
        high = sum(1 for r in out if r.confidence_level == "high")
        med = sum(1 for r in out if r.confidence_level == "medium")
        low = sum(1 for r in out if r.confidence_level == "low")
        log.info(
            f"[CleaningPipeline] 完成 total={len(out)} high={high} medium={med} low={low}"
        )
        return out

    # -------------------------------------------------------- 内部
    def _preprocess(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """对原始 JD 字典做文本预处理"""
        if not item:
            return None
        # 清洗 raw_text
        rt = item.get("raw_text") or item.get("description") or ""
        if rt:
            res = self.preprocessor.process(rt)
            item["raw_text"] = res.text
        # 清洗 title / company
        for k in ("title", "company", "location", "category"):
            v = item.get(k)
            if isinstance(v, str):
                item[k] = self.preprocessor.process(v).text
        if not item.get("raw_text") and not item.get("title"):
            return None
        return item


# ============================================================
# 便捷函数
# ============================================================
_default_pipeline: Optional[CleaningPipeline] = None


def get_cleaning_pipeline() -> CleaningPipeline:
    global _default_pipeline
    if _default_pipeline is None:
        _default_pipeline = CleaningPipeline()
    return _default_pipeline


def run_cleaning_pipeline(items: List[Dict[str, Any]]) -> List[CleanedRecord]:
    return get_cleaning_pipeline().run(items)


__all__ = [
    "CleaningPipeline",
    "CleanedRecord",
    "get_cleaning_pipeline",
    "run_cleaning_pipeline",
]
