"""LLM 技能推断服务 - 兜底推断未知技能的同义词和先修关系

工作流程：
1. 硬编码规则优先（skill_taxonomy.py + entity_normalizer.py）
2. 硬编码未命中时，调用 LLM 推断
3. 推断结果缓存到 Neo4j 图谱（synonym_of / prerequisite_for 关系）
4. 下次遇到相同技能时直接从图谱读取，不重复调用 LLM
"""

import json
import logging
import re
from typing import Optional

from core.llm_service import get_llm_service
from core.graph_service import get_graph_service

logger = logging.getLogger(__name__)


# 已知的"根技能"列表（用于 LLM 推断时校验先修关系是否合理）
ROOT_SKILLS = {
    "Python", "Java", "Go", "C++", "JavaScript", "TypeScript", "Rust",
    "SQL", "Linux", "HTML", "CSS", "Shell", "Git",
    "数学基础", "统计学", "线性代数",
}


class LLMSkillInferrer:
    """LLM 技能推断器 - 兜底处理未知技能"""

    def __init__(self):
        self.llm = get_llm_service()
        self.graph = get_graph_service()
        # 内存缓存（同一次会话内避免重复调用）
        self._synonym_cache: dict[str, str] = {}
        self._prerequisite_cache: dict[str, list[str]] = {}

    # ==================== 同义词推断 ====================

    def infer_synonym(self, skill_name: str) -> Optional[str]:
        """推断技能的标准名称（同义词归一）

        Returns:
            标准技能名，推断失败返回 None
        """
        if not skill_name or not self.llm.is_ready:
            return None

        # 内存缓存命中
        if skill_name in self._synonym_cache:
            return self._synonym_cache[skill_name]

        # 图谱缓存命中：检查该技能是否已有 synonym_of 关系
        cached = self._lookup_synonym_from_graph(skill_name)
        if cached:
            self._synonym_cache[skill_name] = cached
            return cached

        # 调用 LLM 推断
        prompt = self._build_synonym_prompt(skill_name)
        try:
            response = self.llm.chat_completion(
                messages=[
                    {"role": "system", "content": "你是技能名称标准化专家。只返回JSON，不要其他内容。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=200,
                response_format={"type": "json_object"},
            )

            result = self._parse_json_response(response)
            if not result:
                return None

            standard_name = result.get("standard_name", "").strip()
            is_synonym = result.get("is_synonym", False)
            confidence = float(result.get("confidence", 0.5))

            # 置信度太低不采纳
            if confidence < 0.6 or not standard_name:
                self._synonym_cache[skill_name] = None
                return None

            # 如果是同义词，缓存到图谱
            if is_synonym and standard_name != skill_name:
                self._save_synonym_to_graph(skill_name, standard_name, confidence)
                logger.info(f"LLM推断同义词: {skill_name} → {standard_name} (置信度={confidence})")

            self._synonym_cache[skill_name] = standard_name
            return standard_name

        except Exception as e:
            logger.warning(f"LLM同义词推断失败 [{skill_name}]: {e}")
            self._synonym_cache[skill_name] = None
            return None

    def _build_synonym_prompt(self, skill_name: str) -> str:
        """构建同义词推断的提示词"""
        return f"""请分析技能名称「{skill_name}」，判断它是否是某个标准技能名的同义词或缩写。

返回JSON格式：
{{
    "standard_name": "标准技能名",
    "is_synonym": true/false,
    "confidence": 0.0-1.0,
    "reason": "判断依据"
}}

示例：
- 输入"k8s" → {{"standard_name": "Kubernetes", "is_synonym": true, "confidence": 0.95, "reason": "k8s是Kubernetes的常见缩写"}}
- 输入"PyTorch" → {{"standard_name": "PyTorch", "is_synonym": false, "confidence": 0.9, "reason": "已是标准名称"}}
- 输入"大模型" → {{"standard_name": "大语言模型", "is_synonym": true, "confidence": 0.85, "reason": "大模型通常指大语言模型LLM"}}

只返回JSON，不要其他内容。"""

    def _lookup_synonym_from_graph(self, skill_name: str) -> Optional[str]:
        """从图谱中查找已缓存的同义词推断结果"""
        if not self.graph.is_connected:
            return None
        try:
            cypher = """
            MATCH (s:Skill {name: $name})-[:synonym_of]->(target:Skill)
            RETURN target.name AS standard_name
            LIMIT 1
            """
            with self.graph._get_session() as session:
                result = session.run(cypher, name=skill_name)
                record = result.single()
                if record:
                    return record["standard_name"]
        except Exception as e:
            logger.debug(f"图谱同义词查询失败: {e}")
        return None

    def _save_synonym_to_graph(self, alias: str, standard: str, confidence: float):
        """将同义词推断结果保存到图谱"""
        if not self.graph.is_connected:
            return
        try:
            # 确保 standard 节点存在
            self.graph.create_skill_node({"name": standard})
            # 创建 alias 节点并建立 synonym_of 关系
            self.graph.create_skill_node({"name": alias})
            self.graph.create_synonym_relation(alias, standard)
        except Exception as e:
            logger.debug(f"保存同义词到图谱失败: {e}")

    # ==================== 先修关系推断 ====================

    def infer_prerequisites(self, skill_name: str,
                             known_skills: list[str] = None) -> list[str]:
        """推断技能的先修技能

        Args:
            skill_name: 待推断的技能名
            known_skills: 图谱中已有的技能列表（用于让 LLM 选择已存在的技能作为先修）

        Returns:
            先修技能列表，推断失败返回空列表
        """
        if not skill_name or not self.llm.is_ready:
            return []

        # 内存缓存命中
        if skill_name in self._prerequisite_cache:
            return self._prerequisite_cache[skill_name]

        # 图谱缓存命中：检查该技能是否已有 prerequisite_for 关系
        cached = self._lookup_prerequisites_from_graph(skill_name)
        if cached is not None:
            self._prerequisite_cache[skill_name] = cached
            return cached

        # 调用 LLM 推断
        prompt = self._build_prerequisite_prompt(skill_name, known_skills or [])
        try:
            response = self.llm.chat_completion(
                messages=[
                    {"role": "system", "content": "你是技术学习路径规划专家。只返回JSON，不要其他内容。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=300,
                response_format={"type": "json_object"},
            )

            result = self._parse_json_response(response)
            if not result:
                self._prerequisite_cache[skill_name] = []
                return []

            prerequisites = result.get("prerequisites", [])
            confidence = float(result.get("confidence", 0.5))

            # 置信度太低不采纳
            if confidence < 0.6 or not prerequisites:
                self._prerequisite_cache[skill_name] = []
                return []

            # 过滤掉不合理的推断（如自身、空字符串）
            prerequisites = [
                p.strip() for p in prerequisites
                if p and p.strip() and p.strip() != skill_name
            ]

            # 保存到图谱
            if prerequisites:
                self._save_prerequisites_to_graph(skill_name, prerequisites)
                logger.info(f"LLM推断先修关系: {skill_name} ← {prerequisites} (置信度={confidence})")

            self._prerequisite_cache[skill_name] = prerequisites
            return prerequisites

        except Exception as e:
            logger.warning(f"LLM先修关系推断失败 [{skill_name}]: {e}")
            self._prerequisite_cache[skill_name] = []
            return []

    def _build_prerequisite_prompt(self, skill_name: str,
                                    known_skills: list[str]) -> str:
        """构建先修关系推断的提示词"""
        # 只取前50个已知技能，避免 prompt 过长
        known_sample = known_skills[:50]
        known_str = "、".join(known_sample) if known_sample else "无"

        return f"""请分析学习「{skill_name}」这个技能之前，需要先掌握哪些基础技能。

已知图谱中存在的技能列表（优先从中选择先修技能）：
{known_str}

规则：
1. 先修技能应该是学习「{skill_name}」的必要基础，不是相关技能
2. 优先从已知技能列表中选择，如果列表中没有合适的也可以推荐其他
3. 通常1-3个先修技能即可，不要超过5个
4. 根技能（如Python/Java/Linux/SQL）通常是其他技能的先修

返回JSON格式：
{{
    "prerequisites": ["先修技能1", "先修技能2"],
    "confidence": 0.0-1.0,
    "reason": "判断依据"
}}

示例：
- 输入"LangChain" → {{"prerequisites": ["Python", "Prompt Engineering"], "confidence": 0.9, "reason": "LangChain是Python库，且需要Prompt工程基础"}}
- 输入"LoRA" → {{"prerequisites": ["PyTorch", "Fine-tuning"], "confidence": 0.85, "reason": "LoRA是微调技术，需要PyTorch和微调基础"}}
- 输入"Python" → {{"prerequisites": [], "confidence": 0.95, "reason": "Python是基础编程语言，无需先修"}}

只返回JSON，不要其他内容。"""

    def _lookup_prerequisites_from_graph(self, skill_name: str) -> Optional[list[str]]:
        """从图谱中查找已缓存的先修关系推断结果"""
        if not self.graph.is_connected:
            return None
        try:
            cypher = """
            MATCH (s:Skill {name: $name})-[:prerequisite_for]->(pre:Skill)
            RETURN collect(pre.name) AS prerequisites
            """
            with self.graph._get_session() as session:
                result = session.run(cypher, name=skill_name)
                record = result.single()
                if record:
                    return list(record["prerequisites"])
        except Exception as e:
            logger.debug(f"图谱先修关系查询失败: {e}")
        return None

    def _save_prerequisites_to_graph(self, skill: str, prerequisites: list[str]):
        """将先修关系推断结果保存到图谱"""
        if not self.graph.is_connected:
            return
        try:
            # 确保所有节点存在
            self.graph.create_skill_node({"name": skill})
            for pre in prerequisites:
                self.graph.create_skill_node({"name": pre})
                # pre 是 skill 的先修：pre → prerequisite_for → skill
                self.graph.create_prerequisite_relation(pre, skill)
        except Exception as e:
            logger.debug(f"保存先修关系到图谱失败: {e}")

    # ==================== 工具方法 ====================

    def _parse_json_response(self, response: str) -> Optional[dict]:
        """解析 LLM 的 JSON 响应"""
        if not response:
            return None

        # 尝试直接解析
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # 尝试从 markdown 代码块中提取
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试提取第一个 { ... } 块
        match = re.search(r"\{[\s\S]*\}", response)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        logger.warning(f"LLM响应JSON解析失败: {response[:200]}")
        return None


# 单例
_inferrer: Optional[LLMSkillInferrer] = None


def get_llm_skill_inferrer() -> LLMSkillInferrer:
    """获取 LLM 技能推断器单例"""
    global _inferrer
    if _inferrer is None:
        _inferrer = LLMSkillInferrer()
    return _inferrer
