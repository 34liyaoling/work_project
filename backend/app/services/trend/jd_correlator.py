"""技术趋势与招聘 JD 关联分析

输入: 趋势关键词集合 + JD 列表
输出: 关联映射 (技术A → 新兴技能B) + 关联强度
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Sequence

from app.core.logger import log


# 知识库：哪些技术会"带火"哪些新兴技能
CO_OCCURRENCE_RULES: Dict[str, List[str]] = {
    "大模型": ["LangChain", "LlamaIndex", "向量数据库", "RAG", "Prompt Engineering", "Embedding"],
    "LLM": ["LangChain", "LlamaIndex", "向量数据库", "RAG", "Prompt Engineering", "Embedding"],
    "RAG": ["LangChain", "向量数据库", "Embedding", "Elasticsearch", "Milvus"],
    "Agent": ["LangChain", "Function Calling", "AutoGPT", "工具调用"],
    "数字经济": ["数据要素", "数据中台", "实时计算", "Flink", "Kafka"],
    "信创": ["达梦", "人大金仓", "麒麟 OS", "OceanBase", "TDSQL"],
    "新质生产力": ["工业互联网", "数字孪生", "工业 AI", "边缘计算"],
    "Serverless": ["AWS Lambda", "阿里云函数计算", "Vercel", "云开发"],
}


class JDCorrelator:
    """趋势-JD 关联分析器"""

    def correlate(
        self,
        trend_keywords: Sequence[Dict[str, Any]],
        jd_records: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """对每条趋势关键词，输出其带动的相关技能

        :return: [{"trend":"大模型", "emerging_skills":["LangChain",...],
                   "jd_mentions": N, "co_signals": [...] }]
        """
        results: List[Dict[str, Any]] = []
        for kw in trend_keywords or []:
            term = (kw.get("keyword") or "").strip()
            if not term:
                continue
            emerging = self._predict_emerging_skills(term)
            jd_mentions = self._count_jd_mentions(term, jd_records)
            co_signals = self._co_signals(term, emerging, jd_records)
            results.append({
                "trend": term,
                "category": kw.get("category", "其它"),
                "trend_weight": float(kw.get("weight", 0.5) or 0.5),
                "emerging_skills": emerging,
                "jd_mention_count": jd_mentions,
                "co_signals": co_signals,
            })
        log.info(f"趋势关联分析: {len(results)} 条")
        return results

    def _predict_emerging_skills(self, trend_term: str) -> List[str]:
        """基于规则库给出带动的新兴技能"""
        return CO_OCCURRENCE_RULES.get(trend_term, [])

    @staticmethod
    def _count_jd_mentions(term: str, jd_records: Sequence[Dict[str, Any]]) -> int:
        cnt = 0
        term_l = term.lower()
        for jd in jd_records or []:
            skills = " ".join(s for s in (jd.get("skills") or []))
            text = (jd.get("raw_text") or "") + " " + skills
            if term_l in text.lower():
                cnt += 1
        return cnt

    def _co_signals(
        self,
        trend_term: str,
        emerging_skills: List[str],
        jd_records: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """统计趋势词与候选技能在 JD 中的共现信号"""
        co_counter: Counter = Counter()
        for jd in jd_records or []:
            skills = set(s.lower() for s in (jd.get("skills") or []))
            text_l = (jd.get("raw_text") or "").lower()
            if trend_term.lower() in text_l:
                for es in emerging_skills:
                    if es.lower() in skills or es.lower() in text_l:
                        co_counter[es] += 1
        return [{"skill": s, "co_count": c} for s, c in co_counter.most_common()]


_singleton: Optional[JDCorrelator] = None


def get_jd_correlator() -> JDCorrelator:
    global _singleton
    if _singleton is None:
        _singleton = JDCorrelator()
    return _singleton
