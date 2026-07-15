"""O*NET 行业标准对照

把候选技能列表与 O*NET 行业标准技能集做对照：
* 命中标准技能 → 标记为"verified"
* 拼写/大小写变体但语义一致 → 模糊匹配
* 不在标准集 → 标记为"unverified"，可能为新出现的技术或噪声

提供：
* :class:`OnetVerifier` - 单条 JD 验证
* :func:`verify_skills` - 技能列表验证
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set, Tuple

from app.core.logger import log

# 复用 :mod:`onet_crawler` 中的标准技能集
from app.services.crawler.onet_crawler import ONET_STANDARD_SKILLS


@dataclass
class OnetVerifyResult:
    """O*NET 验证结果"""

    verified: List[str] = field(default_factory=list)
    unverified: List[str] = field(default_factory=list)
    fuzzy_matched: Dict[str, str] = field(default_factory=dict)  # 原值 -> 标准名
    coverage: float = 0.0
    novelty_score: float = 0.0  # 候选中"新技能"占比

    def to_dict(self) -> Dict:
        return {
            "verified": self.verified,
            "unverified": self.unverified,
            "fuzzy_matched": self.fuzzy_matched,
            "coverage": round(self.coverage, 4),
            "novelty_score": round(self.novelty_score, 4),
        }


class OnetVerifier:
    """与 O*NET 行业标准做对照"""

    def __init__(self, standard_skills: Optional[List[str]] = None) -> None:
        self.standard = [s.lower() for s in (standard_skills or ONET_STANDARD_SKILLS)]
        self.standard_set: Set[str] = set(self.standard)

    # -------------------------------------------------------- 匹配
    def _normalize_key(self, s: str) -> str:
        return re.sub(r"[\s()（）·/／,，、\-_.]+", "", s.lower())

    def _lookup(self, skill: str) -> Tuple[bool, Optional[str]]:
        """返回 (是否完全匹配, 匹配到的标准名)"""
        if not skill:
            return False, None
        key = skill.strip().lower()
        if key in self.standard_set:
            return True, skill.strip()
        # 模糊：去空格 / 去括号 / 全半角归一
        key2 = self._normalize_key(skill)
        for std in self.standard:
            if self._normalize_key(std) == key2:
                return True, std
        return False, None

    def verify_skills(self, skills: Iterable[str]) -> OnetVerifyResult:
        """验证一批技能"""
        verified: List[str] = []
        unverified: List[str] = []
        fuzzy: Dict[str, str] = {}
        total = 0
        for raw in skills or []:
            raw = (raw or "").strip()
            if not raw:
                continue
            total += 1
            ok, std = self._lookup(raw)
            if ok:
                # 如果是模糊匹配，std 可能是小写形式
                if std and std.lower() != raw.lower():
                    fuzzy[raw] = std
                verified.append(raw)
            else:
                unverified.append(raw)
        coverage = len(verified) / total if total else 0.0
        novelty = len(unverified) / total if total else 0.0
        return OnetVerifyResult(
            verified=verified,
            unverified=unverified,
            fuzzy_matched=fuzzy,
            coverage=round(coverage, 4),
            novelty_score=round(novelty, 4),
        )

    def verify_jd(self, jd: Dict) -> OnetVerifyResult:
        """验证一条 JD：技能 + 标题关键词"""
        skills = jd.get("skills") or []
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(",") if s.strip()]
        # 标题里的常见技术词也加入
        title = jd.get("title") or ""
        title_tokens = re.findall(r"[A-Za-z][A-Za-z0-9+#.\-]{1,15}", title)
        all_skills = list(skills) + title_tokens
        return self.verify_skills(all_skills)


# ============================================================
# 便捷
# ============================================================
_default_verifier: Optional[OnetVerifier] = None


def get_onet_verifier() -> OnetVerifier:
    global _default_verifier
    if _default_verifier is None:
        _default_verifier = OnetVerifier()
    return _default_verifier


def verify_skills(skills: Iterable[str]) -> OnetVerifyResult:
    return get_onet_verifier().verify_skills(skills)


__all__ = [
    "OnetVerifier",
    "OnetVerifyResult",
    "get_onet_verifier",
    "verify_skills",
]
