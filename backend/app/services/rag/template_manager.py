"""提示词模板管理

支持为不同业务（技能验证 / 趋势洞察 / 政策对照）注册和渲染 RAG 模板。
"""
from __future__ import annotations

from string import Template
from typing import Any, Dict, List, Optional


# 通用 RAG 系统提示
DEFAULT_RAG_SYSTEM = (
    "你是严谨的招聘与行业研究助手，仅基于提供的资料片段回答。"
)

# 技能验证模板
SKILL_VERIFY_SYSTEM = "你是一名技能鉴定专家，根据参考资料判断某项技能是否属于某岗位的合理必备项。"
SKILL_VERIFY_USER = Template("""请判断技能「$skill」是否应作为岗位「$role」($category, $level) 的必备项。

【参考资料】
$context

【判断要点】
- 是否在 ≥3 个独立来源中共同出现？
- 是否有具体可验证的描述？
- 是否符合该岗位级别的合理范围？

【输出 JSON】
{
  "is_required": true/false,
  "confidence": 0.0-1.0,
  "reasons": ["原因1","原因2"],
  "evidence": ["参考片段引用 1", "参考片段引用 2"]
}
仅输出一个 JSON 对象。
""")

# 行业趋势模板
TREND_INSIGHT_SYSTEM = "你是行业趋势分析师，根据参考资料输出技术趋势洞察。"
TREND_INSIGHT_USER = Template("""请基于下列资料，输出「$domain」领域的近期技术趋势洞察。

【资料】
$context

【输出 JSON】
{
  "hot_skills": [{"skill":"", "growth":"rising|stable|declining", "evidence":""}],
  "signals": ["信号 1","信号 2"],
  "summary": "≤ 200 字总结"
}
""")

# 政策对照模板
POLICY_CHECK_SYSTEM = "你是政策合规顾问，根据政策原文判断岗位描述是否合规。"
POLICY_CHECK_USER = Template("""请对照下列政策片段判断岗位描述「$role_desc」是否合规。

【政策片段】
$context

【输出】
{
  "compliant": true/false,
  "issues": ["..."],
  "policy_refs": ["片段引用"]
}
""")


_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "skill_verify": {
        "system": SKILL_VERIFY_SYSTEM,
        "user_template": SKILL_VERIFY_USER,
    },
    "trend_insight": {
        "system": TREND_INSIGHT_SYSTEM,
        "user_template": TREND_INSIGHT_USER,
    },
    "policy_check": {
        "system": POLICY_CHECK_SYSTEM,
        "user_template": POLICY_CHECK_USER,
    },
    "default": {
        "system": DEFAULT_RAG_SYSTEM,
        "user_template": Template("【问题】\n$query\n\n【参考片段】\n$context\n"),
    },
}


class TemplateManager:
    """RAG 提示词模板管理器"""

    def register(self, name: str, system: str, user_template: Template) -> None:
        _TEMPLATES[name] = {"system": system, "user_template": user_template}

    def render(
        self,
        name: str,
        query: str = "",
        context: str = "",
        **kwargs: Any,
    ) -> Dict[str, str]:
        """渲染指定模板为 system/user 消息"""
        if name not in _TEMPLATES:
            raise KeyError(f"未注册的 RAG 模板: {name}")
        tpl = _TEMPLATES[name]
        user = tpl["user_template"].substitute(
            query=query, context=context, **kwargs
        )
        return {"system": tpl["system"], "user": user}

    def available(self) -> List[str]:
        return list(_TEMPLATES.keys())


_singleton: Optional[TemplateManager] = None


def get_template_manager() -> TemplateManager:
    global _singleton
    if _singleton is None:
        _singleton = TemplateManager()
    return _singleton
