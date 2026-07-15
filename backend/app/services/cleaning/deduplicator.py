"""去重器 - SimHash + 余弦相似度

策略：
    1. **SimHash 指纹**：对文本分词 → 加权 hash → 合并 → 64 位指纹
    2. **海明距离初筛**：SimHash 距离 ≤ 3 视为候选重复
    3. **余弦相似度精筛**：对候选用 TF-IDF / 词袋 + 余弦相似度复核（阈值 0.85）
    4. **技能组合指纹**：除文本外，单独计算技能集合指纹，避免"文本不同但技能相同"
"""
from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from app.core.config import settings
from app.core.logger import log


# 简易停用词（中英文常见无意义词）
_STOPWORDS_ZH: Set[str] = {
    "的", "了", "和", "是", "在", "我", "有", "以及", "并", "等", "与", "或",
    "对", "为", "于", "上", "下", "中", "本", "可", "能", "要", "将", "我们",
    "你", "他", "她", "它", "这", "那", "通过", "进行", "完成", "参与", "负责",
    "使用", "具备", "熟悉", "掌握", "精通", "了解", "优先", "以上", "以下",
}
_STOPWORDS_EN: Set[str] = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "is", "are", "be", "as", "by", "this", "that", "we", "you", "they",
    "i", "he", "she", "it", "at", "from", "have", "has", "had",
}
_STOPWORDS: Set[str] = _STOPWORDS_ZH | _STOPWORDS_EN


# ============================================================
# 1. 简易分词（不依赖 jieba，避免额外依赖）
# ============================================================
_TOKEN_RE = re.compile(
    r"[A-Za-z][A-Za-z0-9+#.\-]{1,15}"           # 英文 / 技术词
    r"|[\u4e00-\u9fff]{2,}"                      # 连续中文（2字及以上）
)


def tokenize(text: str) -> List[str]:
    """简单分词：英文连续 / 中文连续 2 字以上"""
    if not text:
        return []
    tokens = [t.lower() for t in _TOKEN_RE.findall(text) if t.lower() not in _STOPWORDS]
    return tokens


# ============================================================
# 2. SimHash 实现
# ============================================================
def _hash_token(token: str) -> int:
    """对 token 做 64-bit hash（SHA-1 截断）"""
    h = hashlib.sha1(token.encode("utf-8")).digest()
    # 取前 8 字节拼成 64-bit
    return int.from_bytes(h[:8], "big", signed=False)


def simhash(text: str, tokens: Optional[List[str]] = None) -> int:
    """计算 SimHash 指纹（64-bit）"""
    if tokens is None:
        tokens = tokenize(text)
    if not tokens:
        return 0
    # 词频作为权重
    weights = Counter(tokens)
    v = [0] * 64
    for tok, w in weights.items():
        h = _hash_token(tok)
        for i in range(64):
            if (h >> i) & 1:
                v[i] += w
            else:
                v[i] -= w
    # 重组为 64-bit 整数
    fp = 0
    for i in range(64):
        if v[i] > 0:
            fp |= (1 << i)
    return fp


def hamming_distance(a: int, b: int) -> int:
    """SimHash 海明距离（异或后 popcount）"""
    x = a ^ b
    # Python 3.10+ 有 int.bit_count()
    return x.bit_count()


# ============================================================
# 3. 余弦相似度
# ============================================================
def _cosine(a: Counter, b: Counter) -> float:
    """两个稀疏 Counter 的余弦相似度"""
    if not a or not b:
        return 0.0
    common = set(a.keys()) & set(b.keys())
    num = sum(a[k] * b[k] for k in common)
    den_a = sum(v * v for v in a.values()) ** 0.5
    den_b = sum(v * v for v in b.values()) ** 0.5
    if den_a == 0 or den_b == 0:
        return 0.0
    return num / (den_a * den_b)


def cosine_similarity(text_a: str, text_b: str) -> float:
    """两段文本的余弦相似度（基于词袋）"""
    return _cosine(Counter(tokenize(text_a)), Counter(tokenize(text_b)))


# ============================================================
# 4. 技能组合指纹
# ============================================================
def skill_fingerprint(skills: Iterable[str]) -> int:
    """对技能集合计算 simhash（去重 + 排序后拼接）"""
    sorted_skills = sorted({s.strip().lower() for s in skills if s and s.strip()})
    if not sorted_skills:
        return 0
    return simhash(" ".join(sorted_skills))


# ============================================================
# 5. 去重器
# ============================================================
@dataclass
class DedupResult:
    """去重单条结果"""

    keep: bool
    duplicate_of: Optional[str] = None
    similarity: float = 0.0
    reason: str = ""


class SimHashDeduplicator:
    """SimHash + 余弦相似度去重器

    Attributes:
        threshold: 余弦相似度阈值（默认 0.85）
        hamming_threshold: SimHash 海明距离初筛阈值
        use_skill_fingerprint: 是否同时校验技能组合指纹

    用法:
        dedup = SimHashDeduplicator(threshold=0.85)
        kept = dedup.deduplicate(jd_items, text_key="raw_text", skill_key="skills")
    """

    def __init__(
        self,
        threshold: Optional[float] = None,
        hamming_threshold: int = 5,
        use_skill_fingerprint: bool = True,
    ) -> None:
        self.threshold = threshold if threshold is not None else settings.SIMHASH_THRESHOLD
        self.hamming_threshold = int(hamming_threshold)
        self.use_skill_fingerprint = bool(use_skill_fingerprint)
        # 内部存储：id -> (text, simhash, skill_fp, skills)
        self._seen: Dict[str, Tuple[str, int, int, List[str]]] = {}

    # -------------------------------------------------------- 单条判重
    def check(self, jd_id: str, text: str, skills: Optional[Sequence[str]] = None) -> DedupResult:
        """判断单条 JD 是否与已入库的重复"""
        if not text:
            return DedupResult(keep=True, reason="empty_text")
        tokens = tokenize(text)
        fp = simhash(text, tokens=tokens)
        skill_list = list(skills or [])
        skill_fp = skill_fingerprint(skill_list) if self.use_skill_fingerprint else 0

        for seen_id, (seen_text, seen_fp, seen_skill_fp, seen_skills) in self._seen.items():
            # 1) 文本 SimHash 海明距离
            hd = hamming_distance(fp, seen_fp)
            # 2) 技能组合指纹
            if self.use_skill_fingerprint and seen_skill_fp:
                shd = hamming_distance(skill_fp, seen_skill_fp)
            else:
                shd = 64
            # 任一相似即视为候选
            if hd > self.hamming_threshold and shd > self.hamming_threshold:
                continue
            # 3) 余弦相似度精筛
            sim = cosine_similarity(text, seen_text)
            if sim >= self.threshold:
                return DedupResult(
                    keep=False,
                    duplicate_of=seen_id,
                    similarity=round(sim, 4),
                    reason=f"simhash_hd={hd} skill_hd={shd} cosine={sim:.3f}",
                )
            # 技能组合完全一致也算重复（允许文本略不同）
            if self.use_skill_fingerprint and shd <= 2 and len(skill_list) >= 3:
                return DedupResult(
                    keep=False,
                    duplicate_of=seen_id,
                    similarity=1.0,
                    reason=f"skill_fingerprint_match skill_hd={shd}",
                )

        # 通过：入库
        self._seen[jd_id] = (text, fp, skill_fp, skill_list)
        return DedupResult(keep=True, reason="ok")

    # -------------------------------------------------------- 批量
    def deduplicate(
        self,
        items: List[Dict],
        text_key: str = "raw_text",
        skill_key: str = "skills",
        id_key: str = "jd_id",
    ) -> List[Dict]:
        """批量去重，返回去重后的列表（标记 is_duplicate=1 的被丢弃）"""
        kept: List[Dict] = []
        dropped = 0
        for item in items:
            jd_id = str(item.get(id_key, ""))
            text = item.get(text_key, "") or ""
            skills = item.get(skill_key, []) or []
            if not jd_id:
                # 没有 ID 的给个临时 ID
                jd_id = f"tmp-{len(self._seen)}-{hash(text) & 0xFFFFFFFF}"
            result = self.check(jd_id, text, skills)
            if result.keep:
                kept.append(item)
            else:
                dropped += 1
                log.debug(
                    f"丢弃重复 JD id={jd_id} 重复于 {result.duplicate_of} sim={result.similarity}"
                )
        log.info(f"SimHash 去重：输入 {len(items)}，保留 {len(kept)}，丢弃 {dropped}")
        return kept

    def reset(self) -> None:
        self._seen.clear()


__all__ = [
    "tokenize",
    "simhash",
    "hamming_distance",
    "cosine_similarity",
    "skill_fingerprint",
    "SimHashDeduplicator",
    "DedupResult",
]
