"""第三层 - LLM 自检

让 LLM 对已生成的岗位定义卡片做"自我审视":
- 技能是否具体可验证
- 是否有充分的证据来源
- 与常识是否冲突
- 自打分 0-10，要求模型在回答中给出每个评分的依据
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from app.core.logger import log
from app.services.llm_client import SparkClient


SELFCHECK_SYSTEM = (
    "你是一名严格的招聘内容审核员。对给出的岗位定义卡片逐项打 0-10 分，"
    "并指出每项的证据来源（来自 evidence_sources）。"
)

SELFCHECK_USER_TEMPLATE = """请对下面的岗位定义卡片执行自检，给出 0-10 分评分。

【评分维度】
1. specificity: 技能是否具体可验证（拒绝"编程能力"等泛化词）
2. evidence: 每条技能是否在 evidence_sources 中有支撑
3. consistency: 必备 vs 加分划分是否合理
4. confidence_calibration: 整体 confidence 与证据强度是否一致

【岗位定义 JSON】
{role_card}

【输出 Schema】
{{
  "specificity": 0-10,
  "evidence": 0-10,
  "consistency": 0-10,
  "confidence_calibration": 0-10,
  "overall": 0-10,
  "issues": ["问题1", "问题2"],
  "source_mapping": {{"skill名": ["来源 jd_id", ...]}}
}}
仅输出一个 JSON 对象。
"""


class LLMSelfChecker:
    """LLM 自检器"""

    def __init__(self, spark_client: Optional[SparkClient] = None):
        self.spark = spark_client or SparkClient()

    async def check(self, role_card: Dict[str, Any]) -> Dict[str, Any]:
        """对岗位定义卡片做自检"""
        try:
            text = await self.spark.chat(
                [
                    {"role": "system", "content": SELFCHECK_SYSTEM},
                    {"role": "user", "content": SELFCHECK_USER_TEMPLATE.format(
                        role_card=json.dumps(role_card, ensure_ascii=False)
                    )},
                ],
                temperature=0.1,
                max_tokens=1200,
            )
            data = self._parse(text)
            data.setdefault("overall", 0)
            data.setdefault("issues", [])
            return data
        except Exception as e:
            log.error(f"LLM 自检失败: {e}")
            return self._fallback(role_card)

    # ----------------- 内部 -----------------
    @staticmethod
    def _parse(text: str) -> Dict[str, Any]:
        if not text:
            return {}
        text = text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
            if "```" in text:
                text = text.split("```", 1)[0]
        try:
            return json.loads(text)
        except Exception:
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(0))
                except Exception:
                    pass
        return {}

    @staticmethod
    def _fallback(role_card: Dict[str, Any]) -> Dict[str, Any]:
        """LLM 不可用时基于规则给出基础评分"""
        required = role_card.get("required_skills", []) or []
        generic_terms = {"编程能力", "沟通能力", "学习能力", "团队合作", "执行力"}
        spec_score = 10
        issues: List[str] = []
        for s in required:
            if s.get("skill") in generic_terms:
                spec_score -= 2
                issues.append(f"泛化技能词: {s.get('skill')}")
        evidence_count = len(role_card.get("evidence_sources", []) or [])
        evidence_score = min(10, evidence_count)
        consistency_score = 8 if any(s.get("weight", 0) > 0.7 for s in required) else 5
        conf_declared = float(role_card.get("confidence", 0.5))
        calib_score = 7 if 0.3 <= conf_declared <= 0.95 else 4
        overall = round((spec_score + evidence_score + consistency_score + calib_score) / 4, 1)
        return {
            "specificity": max(0, spec_score),
            "evidence": evidence_score,
            "consistency": consistency_score,
            "confidence_calibration": calib_score,
            "overall": overall,
            "issues": issues,
            "source_mapping": {},
        }


_singleton: Optional[LLMSelfChecker] = None


def get_self_checker() -> LLMSelfChecker:
    global _singleton
    if _singleton is None:
        _singleton = LLMSelfChecker()
    return _singleton
