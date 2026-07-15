"""多层幻觉防控体系

4 层防控:
- Layer 1: 数据来源过滤（可信度评分 + 时效性）
- Layer 2: 交叉验证（≥3 源高置信，O*NET 对照）
- Layer 3: LLM 自检（自打分 0-10，证据 source 追溯）
- Layer 4: 人工审核队列（低置信度 / 新岗位 / 重大变更）

由 orchestrator.HallucinationGuard 统一编排。
"""
from app.services.hallucination_guard.layer1_source import SourceFilter, get_source_filter
from app.services.hallucination_guard.layer2_cross import CrossValidator, get_cross_validator
from app.services.hallucination_guard.layer3_selfcheck import LLMSelfChecker, get_self_checker
from app.services.hallucination_guard.layer4_human import HumanReviewQueue, get_human_queue
from app.services.hallucination_guard.orchestrator import HallucinationGuard, get_guard


__all__ = [
    "SourceFilter",
    "CrossValidator",
    "LLMSelfChecker",
    "HumanReviewQueue",
    "HallucinationGuard",
    "get_source_filter",
    "get_cross_validator",
    "get_self_checker",
    "get_human_queue",
    "get_guard",
]
