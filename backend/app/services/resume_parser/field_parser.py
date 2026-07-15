"""字段结构化解析

结合大模型（首选）与正则规则（兜底）从简历文本中提取:
- 姓名 / 邮箱 / 电话
- 教育经历
- 工作经历
- 项目经历
- 技能列表
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from app.core.logger import log
from app.services.llm_client import SparkClient
from app.services.prompt_templates import render


EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(?:\+?86[-\s]?)?1[3-9]\d{9}")
NAME_RE = re.compile(r"(?:姓名|Name|名前)[:：\s]+([^\n]{2,10})")


class FieldParser:
    """字段结构化解析器"""

    def __init__(self, spark_client: Optional[SparkClient] = None):
        self.spark = spark_client or SparkClient()

    async def parse(self, resume_text: str) -> Dict[str, Any]:
        """解析简历文本"""
        if not resume_text:
            return self._empty_result()
        try:
            # 优先 LLM
            llm_result = await self._llm_parse(resume_text)
        except Exception as e:
            log.warning(f"LLM 解析失败, 启用规则: {e}")
            llm_result = {}

        # 规则兜底
        rule_result = self._rule_parse(resume_text)
        merged = self._merge(llm_result, rule_result)
        return merged

    # ----------------- LLM 解析 -----------------
    async def _llm_parse(self, text: str) -> Dict[str, Any]:
        rendered = render("resume_parse", resume_text=text[:6000])
        messages = [
            {"role": "system", "content": rendered["system"]},
            {"role": "user", "content": rendered["user"]},
        ]
        raw = await self.spark.chat(messages, temperature=0.1, max_tokens=1500)
        return self._safe_json(raw)

    @staticmethod
    def _safe_json(text: str) -> Dict[str, Any]:
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
        except Exception as e:
            log.warning(f"简历 JSON 解析失败: {e}")
            return {}

    # ----------------- 规则解析 -----------------
    def _rule_parse(self, text: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {}

        # 姓名
        name_match = NAME_RE.search(text)
        result["name"] = name_match.group(1).strip() if name_match else None

        # 邮箱
        email_match = EMAIL_RE.search(text)
        result["email"] = email_match.group(0) if email_match else None

        # 电话
        phone_match = PHONE_RE.search(text)
        result["phone"] = phone_match.group(0) if phone_match else None

        # 简易分段
        result["education"] = self._extract_section(text, ["教育", "Education", "学历"])
        result["work_experience"] = self._extract_section(text, ["工作", "Work", "Experience", "经历"])
        result["projects"] = self._extract_section(text, ["项目", "Project"])

        # 技能：以 "技能" 段落或显式列表形式
        skills: List[Dict[str, Any]] = []
        skill_section = re.search(r"(技能|Skills?)[:：\s]+([^\n]+(?:\n[^\n]+){0,4})", text, re.IGNORECASE)
        if skill_section:
            block = skill_section.group(2)
            tokens = re.split(r"[,，、;；/|\s]+", block)
            seen = set()
            for token in tokens:
                token = token.strip().strip("·•-")
                if not token or token.lower() in seen:
                    continue
                seen.add(token.lower())
                if len(token) < 2 or len(token) > 30:
                    continue
                skills.append({"skill": token, "level": "熟练", "confidence": 0.7, "evidence": token})
        result["skills"] = skills
        return result

    @staticmethod
    def _extract_section(text: str, keys: List[str]) -> List[Dict[str, Any]]:
        """提取某段落下的若干行作为条目（按换行切分）"""
        for key in keys:
            pattern = re.compile(rf"{re.escape(key)}[^\n]*\n((?:[^\n]+\n?){{0,8}})", re.IGNORECASE)
            m = pattern.search(text)
            if not m:
                continue
            block = m.group(1).strip()
            lines = [l.strip() for l in block.splitlines() if l.strip()]
            entries: List[Dict[str, Any]] = []
            for line in lines:
                entries.append({"raw": line})
            if entries:
                return entries
        return []

    # ----------------- 合并 -----------------
    def _merge(self, llm: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, Any]:
        merged: Dict[str, Any] = {**rule, **{k: v for k, v in llm.items() if v}}
        # skills 合并去重
        seen = set()
        skills: List[Dict[str, Any]] = []
        for s in (rule.get("skills", []) or []) + (llm.get("skills", []) or []):
            key = (s.get("skill") or "").lower().strip()
            if not key or key in seen:
                continue
            seen.add(key)
            skills.append(s)
        merged["skills"] = skills
        merged.setdefault("name", "候选人")
        merged.setdefault("email", None)
        merged.setdefault("phone", None)
        return merged

    @staticmethod
    def _empty_result() -> Dict[str, Any]:
        return {
            "name": None, "email": None, "phone": None,
            "education": [], "work_experience": [], "projects": [],
            "skills": [],
        }


_singleton: Optional[FieldParser] = None


def get_field_parser() -> FieldParser:
    global _singleton
    if _singleton is None:
        _singleton = FieldParser()
    return _singleton
