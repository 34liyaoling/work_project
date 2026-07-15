"""技能标准化映射

将简历中识别出的技能别名映射到标准词表（来自 data/skill_dictionary.json）。
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logger import log


class SkillMapper:
    """技能标准化映射器"""

    def __init__(self, dict_path: Optional[str] = None):
        self.dict_path = dict_path or settings.SKILL_DICT_PATH
        self._alias_to_standard: Dict[str, str] = {}
        self._standard_to_category: Dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.dict_path):
            log.warning(f"技能词典未找到: {self.dict_path}, 启用空映射")
            return
        try:
            with open(self.dict_path, "r", encoding="utf-8") as f:
                entries = json.load(f)
            for item in entries:
                alias = (item.get("alias") or "").strip().lower()
                std = (item.get("standard_name") or alias).strip()
                cat = (item.get("category") or "通用").strip()
                if alias:
                    self._alias_to_standard[alias] = std
                self._standard_to_category[std.lower()] = cat
            log.info(f"技能词典加载: {len(self._alias_to_standard)} 别名")
        except Exception as e:
            log.error(f"技能词典加载失败: {e}")

    def standardize(self, skill: str) -> Dict[str, str]:
        """返回 {standard_name, category}"""
        if not skill:
            return {"standard_name": "", "category": "通用"}
        key = skill.strip().lower()
        std = self._alias_to_standard.get(key, skill.strip())
        cat = self._standard_to_category.get(std.lower(), "通用")
        return {"standard_name": std, "category": cat}

    def map_skills(
        self,
        skills: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """批量标准化技能列表"""
        results: List[Dict[str, Any]] = []
        for s in skills or []:
            name = s.get("skill") if isinstance(s, dict) else str(s)
            mapped = self.standardize(name)
            item = s if isinstance(s, dict) else {"skill": name}
            item["standard_name"] = mapped["standard_name"]
            item["category"] = item.get("category") or mapped["category"]
            results.append(item)
        return results


_singleton: Optional[SkillMapper] = None


def get_skill_mapper() -> SkillMapper:
    global _singleton
    if _singleton is None:
        _singleton = SkillMapper()
    return _singleton
