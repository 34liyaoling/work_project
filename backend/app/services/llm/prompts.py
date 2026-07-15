"""LLM 提示词模板 + JSON Schema

每个模板都包含：
* version: 版本号（便于 A/B 试验和回滚）
* purpose: 用途说明
* system: 系统角色提示
* user_template: 用户提示（接受参数化渲染）
* schema: 输出 JSON Schema（用于校验）

模板：
* jd_parse          - JD 解析
* role_definition   - 新兴岗位定义生成
* resume_parse      - 简历解析
* skill_extract     - 技能提取
"""
from __future__ import annotations

import json
from string import Template
from typing import Any, Dict


# ============================================================
# JD 输出 JSON Schema（严格）
# ============================================================
JD_OUTPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": [
        "job_title",
        "category",
        "level",
        "core_responsibilities",
        "required_skills",
        "preferred_skills",
        "typical_scenarios",
        "confidence",
    ],
    "properties": {
        "job_title": {"type": "string", "minLength": 1},
        "category": {"type": "string"},
        "level": {"type": "string", "enum": ["初级", "中级", "高级", "资深"]},
        "core_responsibilities": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
        },
        "required_skills": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["skill", "level", "weight"],
                "properties": {
                    "skill": {"type": "string", "minLength": 1},
                    "level": {"type": "string", "enum": ["基础", "熟练", "精通"]},
                    "weight": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                },
            },
        },
        "preferred_skills": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["skill", "level", "weight"],
                "properties": {
                    "skill": {"type": "string", "minLength": 1},
                    "level": {"type": "string", "enum": ["基础", "熟练", "精通"]},
                    "weight": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                },
            },
        },
        "typical_scenarios": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    },
    "additionalProperties": False,
}


# ============================================================
# 提示词文本
# ============================================================
JD_PARSE_SYSTEM = "你是一名资深的招聘行业专家，擅长从原始 JD 文本中精确提取结构化岗位信息。"

JD_PARSE_USER = Template("""请阅读以下招聘 JD 文本，输出**严格符合 JSON Schema** 的结构化结果。

【规则】
1. 技能必须**具体**（如 "Python"、"PyTorch"、"Kubernetes"），拒绝"编程能力"、"学习能力"等泛化词。
2. 区分必备（required）与加分（preferred）；必备技能指 JD 明确写"必须"、"要求"、"具备"等强需求词的能力。
3. level 字段必须是 "基础" / "熟练" / "精通" 之一。
4. weight 在 [0, 1] 区间，数值越高代表在岗位中越关键。
5. confidence 是你对本次抽取结果的整体把握度（0-1）。
6. **置信度 < 0.7 的技能不要列入 required_skills**，可以放入 preferred_skills。
7. category 限定为以下之一: 后端开发、前端开发、算法工程师、数据科学、测试开发、运维、DevOps、产品经理、设计师、运营、市场、HR、数据分析、数据工程、嵌入式、AI工程师、芯片、其它。
8. level 限定为: 初级 / 中级 / 高级 / 资深。

【JSON Schema 严格输出】
$schema

【JD 原文】
$jd_text

【输出】仅输出一个 JSON 对象，不要包裹 markdown 代码块、不要任何解释。
""")

ROLE_GEN_SYSTEM = "你是岗位定义生成助手，根据聚类得到的技能组合生成完整的新兴岗位定义。"

ROLE_GEN_USER = Template("""根据下列聚类得到的技能组合与代表性 JD 摘要，生成一份新兴岗位定义卡片。

【要求】
1. 输出严格符合下方 JSON Schema。
2. 技能需具体、可验证；泛化词（"编程能力"等）禁止出现。
3. 区分必备与加分；必备技能要求在 ≥3 个聚类样本中共同出现。
4. 置信度 = 必备技能平均置信度 × 数据源权重；技能自身置信度 < 0.7 不放入必备。
5. typical_scenarios 给出 2-4 个真实业务场景。

【JSON Schema】
$schema

【聚类信息】
- 簇 ID: $cluster_id
- 簇大小 (JD 数量): $cluster_size
- 跨公司数: $company_count
- 涉及平台: $sources
- 技能组合 (频次): $skill_freq
- 代表性 JD 摘要:
$jd_samples
""")

RESUME_PARSE_SYSTEM = "你是一名简历解析专家，能够从候选人简历中提取结构化信息。"

RESUME_PARSE_USER = Template("""请从以下简历文本中提取候选人的关键信息，输出 JSON。

【要求】
1. 技能必须**具体**（如 "React"、"TensorFlow"），禁止泛化词。
2. 工作经历列出 start/end、公司、职位、职责要点。
3. 项目经历列出项目名、角色、关键成果（量化优先）。
4. 技能置信度反映该技能证据的强弱。

【简历文本】
$resume_text

【输出 JSON Schema 概述】
{
  "name": "string",
  "email": "string",
  "phone": "string",
  "education": [{"school":"","degree":"","major":"","start":"","end":""}],
  "work_experience": [{"company":"","title":"","start":"","end":"","responsibilities":[]}],
  "projects": [{"name":"","role":"","description":"","achievements":[]}],
  "skills": [{"skill":"","level":"基础/熟练/精通","confidence":0.0-1.0,"evidence":""}]
}

仅输出一个 JSON 对象。
""")

SKILL_EXTRACT_SYSTEM = "你是一名技术技能词典专家，能从文本中识别具体技术名词。"

SKILL_EXTRACT_USER = Template("""从下列文本中识别**具体可验证**的技术技能名词（如 Python、Kubernetes、PyTorch、Tableau）。

【规则】
- 泛化词（"编程能力"、"沟通能力"）禁止出现。
- 区分技能 vs 工具 vs 框架；统一登记为 skill。
- 输出 JSON: {"skills":[{"skill":"","category":"","confidence":0.0-1.0,"evidence":""}]}

【文本】
$text
""")


# ============================================================
# 模板注册表
# ============================================================
TEMPLATES: Dict[str, Dict[str, Any]] = {
    "jd_parse": {
        "version": "1.0.0",
        "purpose": "将原始 JD 文本解析为结构化 JSON",
        "system": JD_PARSE_SYSTEM,
        "user_template": JD_PARSE_USER,
        "schema": JD_OUTPUT_SCHEMA,
    },
    "role_definition": {
        "version": "1.0.0",
        "purpose": "根据聚类结果生成新兴岗位定义卡片",
        "system": ROLE_GEN_SYSTEM,
        "user_template": ROLE_GEN_USER,
        "schema": JD_OUTPUT_SCHEMA,
    },
    "resume_parse": {
        "version": "1.0.0",
        "purpose": "从候选人简历提取结构化信息",
        "system": RESUME_PARSE_SYSTEM,
        "user_template": RESUME_PARSE_USER,
        "schema": None,
    },
    "skill_extract": {
        "version": "1.0.0",
        "purpose": "从短文本中提取技术技能名词",
        "system": SKILL_EXTRACT_SYSTEM,
        "user_template": SKILL_EXTRACT_USER,
        "schema": None,
    },
}


# ============================================================
# 渲染工具
# ============================================================
def render(template_name: str, **kwargs) -> Dict[str, str]:
    """渲染指定模板为 system/user 消息字典

    Args:
        template_name: 模板名（``jd_parse`` / ``role_definition`` 等）
        **kwargs: 模板占位符参数

    Returns:
        {"system": "...", "user": "..."}
    """
    if template_name not in TEMPLATES:
        raise KeyError(f"未注册的提示词模板: {template_name}")
    tpl = TEMPLATES[template_name]
    # schema 序列化为 JSON 字符串以便嵌入 prompt
    safe_kwargs = dict(kwargs)
    if "schema" in tpl and tpl["schema"] is not None and "schema" not in safe_kwargs:
        safe_kwargs["schema"] = json.dumps(tpl["schema"], ensure_ascii=False, indent=2)
    user = tpl["user_template"].safe_substitute(**safe_kwargs)
    return {"system": tpl["system"], "user": user}


def get_schema(template_name: str) -> Dict[str, Any]:
    """获取指定模板的 JSON Schema"""
    if template_name not in TEMPLATES:
        raise KeyError(f"未注册的提示词模板: {template_name}")
    return TEMPLATES[template_name]["schema"]


def get_version(template_name: str) -> str:
    """获取模板版本号"""
    if template_name not in TEMPLATES:
        raise KeyError(f"未注册的提示词模板: {template_name}")
    return TEMPLATES[template_name]["version"]


__all__ = [
    "JD_OUTPUT_SCHEMA",
    "TEMPLATES",
    "render",
    "get_schema",
    "get_version",
]
