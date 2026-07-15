"""数据清洗与交叉验证子包

包含：
* :mod:`preprocessor`     - 文本预处理（HTML / 特殊字符 / 统一格式）
* :mod:`deduplicator`     - SimHash + 余弦相似度去重
* :mod:`skill_normalizer` - 技能标准化映射
* :mod:`cross_validator`  - 多平台交叉验证
* :mod:`credibility_scorer` - 可信度评分
* :mod:`onet_verifier`    - O*NET 行业标准对照
* :mod:`pipeline`         - 完整清洗流程编排
"""
from __future__ import annotations

from app.services.cleaning.preprocessor import TextPreprocessor
from app.services.cleaning.deduplicator import SimHashDeduplicator, simhash
from app.services.cleaning.skill_normalizer import SkillNormalizer
from app.services.cleaning.cross_validator import CrossValidator
from app.services.cleaning.credibility_scorer import CredibilityScorer
from app.services.cleaning.onet_verifier import OnetVerifier
from app.services.cleaning.pipeline import (
    CleaningPipeline,
    CleanedRecord,
    run_cleaning_pipeline,
)

__all__ = [
    "TextPreprocessor",
    "SimHashDeduplicator",
    "simhash",
    "SkillNormalizer",
    "CrossValidator",
    "CredibilityScorer",
    "OnetVerifier",
    "CleaningPipeline",
    "CleanedRecord",
    "run_cleaning_pipeline",
]
