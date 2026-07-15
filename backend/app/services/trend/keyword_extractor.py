"""行业研究报告/政策文件技术趋势关键词提取

结合 LLM 抽取 + 词典匹配，输出带权重的关键词列表。
"""
from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Sequence

from app.core.logger import log
from app.services.llm_client import SparkClient
from app.services.prompt_templates import render


# 内置趋势关键词词典（按主题分类）
TREND_DICTIONARY: Dict[str, List[str]] = {
    "AI模型": ["大模型", "LLM", "GPT", "扩散模型", "多模态", "MoE", "Agent", "RAG", "提示工程"],
    "AI工程": ["LangChain", "LlamaIndex", "向量数据库", "Embedding", "Hugging Face", "模型微调", "RLHF"],
    "云原生": ["Kubernetes", "Docker", "Service Mesh", "Istio", "Serverless", "微服务"],
    "数据": ["数据湖", "湖仓一体", "DataOps", "实时计算", "Flink", "Kafka", "Iceberg"],
    "前端": ["Vue 3", "React 18", "Server Components", "微前端", "Vite", "Solid"],
    "安全": ["零信任", "SASE", "DevSecOps", "供应链安全", "SBOM"],
    "硬件": ["RISC-V", "Chiplet", "3D 封装", "光计算"],
    "政策": ["数字化转型", "新质生产力", "数字经济", "数据要素", "信创"],
}


class KeywordExtractor:
    """趋势关键词提取器"""

    def __init__(self, spark: Optional[SparkClient] = None):
        self.spark = spark or SparkClient()

    async def extract(
        self,
        documents: Sequence[str],
        doc_type: str = "report",  # report / policy / news
    ) -> List[Dict[str, Any]]:
        """从多份文档中提取趋势关键词

        :return: [{"keyword":..., "weight":..., "category":..., "evidence_count":...}]
        """
        if not documents:
            return []
        # 1. 词典匹配做基线
        dict_hits = self._dict_match(documents)
        # 2. LLM 补充
        try:
            llm_hits = await self._llm_extract(documents, doc_type)
        except Exception as e:
            log.warning(f"LLM 关键词提取失败: {e}")
            llm_hits = []
        return self._merge(dict_hits, llm_hits)

    def _dict_match(self, documents: Sequence[str]) -> List[Dict[str, Any]]:
        """基于词典统计出现频次"""
        counter: Counter = Counter()
        for doc in documents:
            for category, kws in TREND_DICTIONARY.items():
                for kw in kws:
                    if kw.lower() in doc.lower():
                        counter[(kw, category)] += 1
        return [
            {"keyword": kw, "category": cat, "weight": cnt, "evidence_count": cnt}
            for (kw, cat), cnt in counter.most_common()
        ]

    async def _llm_extract(
        self, documents: Sequence[str], doc_type: str
    ) -> List[Dict[str, Any]]:
        text = "\n---\n".join([(d or "")[:2000] for d in documents[:5]])
        sys_prompt = "你是技术趋势分析专家，擅长从行业报告/政策文件中识别关键趋势词。"
        user_prompt = (
            f"以下是一组{doc_type}片段，请提取 ≤ 20 个核心技术趋势关键词，"
            f"输出 JSON: {{'keywords':[{{'keyword':'','category':'','weight':0.0-1.0,'evidence':''}}]}}\n\n"
            f"【文档】\n{text}\n仅输出一个 JSON。"
        )
        raw = await self.spark.chat(
            [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1, max_tokens=1200,
        )
        data = self._safe_json(raw)
        return [
            {
                "keyword": k.get("keyword", ""),
                "category": k.get("category", "其它"),
                "weight": float(k.get("weight", 0.5) or 0.5),
                "evidence_count": 1,
            }
            for k in data.get("keywords", []) if k.get("keyword")
        ]

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
        except Exception:
            return {}

    def _merge(
        self,
        a: List[Dict[str, Any]],
        b: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        merged: Dict[str, Dict[str, Any]] = {}
        for src in a + b:
            k = (src.get("keyword") or "").strip().lower()
            if not k:
                continue
            entry = merged.setdefault(k, {"keyword": src["keyword"], "category": src.get("category", "其它"),
                                          "weight": 0.0, "evidence_count": 0})
            entry["weight"] += float(src.get("weight", 0.5) or 0.5)
            entry["evidence_count"] += int(src.get("evidence_count", 0) or 0)
        result = sorted(merged.values(), key=lambda x: x["weight"], reverse=True)
        log.info(f"关键词合并: {len(result)} 个")
        return result


_singleton: Optional[KeywordExtractor] = None


def get_keyword_extractor() -> KeywordExtractor:
    global _singleton
    if _singleton is None:
        _singleton = KeywordExtractor()
    return _singleton
