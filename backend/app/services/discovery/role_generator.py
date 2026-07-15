"""新兴岗位定义生成服务

将聚类得到的"技能组合簇"输入到大模型，由大模型生成结构化岗位定义卡片。
若启用 mock 模式或 LLM 不可用，则基于规则动态构造合理响应。
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logger import log
from app.services.llm_client import SparkClient
from app.services.prompt_templates import get_schema, render


class RoleGenerator:
    """岗位定义生成器

    典型用法:
        gen = RoleGenerator()
        card = await gen.generate(cluster_info)
    """

    def __init__(self, spark_client: Optional[SparkClient] = None):
        self.spark = spark_client or SparkClient()

    async def generate(self, cluster_info: Dict[str, Any]) -> Dict[str, Any]:
        """根据聚类信息生成岗位定义卡片

        :param cluster_info: cluster_analyzer.cluster() 返回的簇信息
        :return: 严格符合 JD_OUTPUT_SCHEMA 的岗位定义字典
        """
        messages = self._build_messages(cluster_info)
        try:
            text = await self.spark.chat(messages, temperature=0.2, max_tokens=1500)
            data = self._safe_parse(text)
            data.setdefault("confidence", 0.7)
            return data
        except Exception as e:
            log.error(f"RoleGenerator 调用 LLM 失败: {e}")
            return self._fallback(cluster_info)

    def _build_messages(self, info: Dict[str, Any]) -> List[Dict[str, str]]:
        schema = get_schema("role_definition") or {}
        schema_json = json.dumps(schema, ensure_ascii=False)
        skill_freq = info.get("skill_freq", {})
        skill_freq_str = ", ".join([f"{k}({v})" for k, v in list(skill_freq.items())[:30]])
        jd_samples = info.get("jd_samples") or "(代表性 JD 文本见上方技能组合)"
        rendered = render(
            "role_definition",
            schema=schema_json,
            cluster_id=info.get("cluster_id", "cluster_0"),
            cluster_size=info.get("size", 0),
            company_count=info.get("company_count", 0),
            sources=",".join(info.get("sources", [])),
            skill_freq=skill_freq_str or "(无)",
            jd_samples=jd_samples,
        )
        return [
            {"role": "system", "content": rendered["system"]},
            {"role": "user", "content": rendered["user"]},
        ]

    @staticmethod
    def _safe_parse(text: str) -> Dict[str, Any]:
        """从模型输出中提取 JSON"""
        text = (text or "").strip()
        if not text:
            return {}
        # 兼容 ```json ... ``` 包裹
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
            if "```" in text:
                text = text.split("```", 1)[0]
        try:
            return json.loads(text)
        except Exception as e:
            log.warning(f"RoleGenerator JSON 解析失败: {e}")
            return {}

    @staticmethod
    def _fallback(info: Dict[str, Any]) -> Dict[str, Any]:
        """LLM 不可用时的降级方案：基于规则构造"""
        skills = info.get("skills", [])[:6] or ["Python"]
        required = [{"skill": s, "level": "熟练", "weight": 0.75} for s in skills[:5]]
        preferred = [{"skill": s, "level": "基础", "weight": 0.5} for s in skills[5:10]]
        return {
            "job_title": info.get("cluster_id", "新兴技术岗"),
            "category": "AI工程师",
            "level": "中级",
            "core_responsibilities": [
                f"基于 {','.join(skills[:3])} 设计系统方案",
                "推进跨团队技术落地与性能优化",
            ],
            "required_skills": required,
            "preferred_skills": preferred,
            "typical_scenarios": ["智能客服系统", "数据驱动决策"],
            "confidence": round(min(0.7 + info.get("size", 1) * 0.01, 0.95), 2),
            "evidence_sources": info.get("sample_jd_indices", []),
        }


_singleton: Optional[RoleGenerator] = None


def get_role_generator() -> RoleGenerator:
    """获取全局单例"""
    global _singleton
    if _singleton is None:
        _singleton = RoleGenerator()
    return _singleton
