"""关系推断引擎 - 自动推断技能间的各种关系

支持的推断类型:
- prerequisite_for: 先修关系（如 Python → PyTorch）
- belongs_to: 领域归属关系（如 PyTorch → 人工智能）
- similar_to: 相似关系（基于名称相似度）
- synonym_of: 同义词关系
"""

import logging
import re
from difflib import SequenceMatcher

from models.skill_taxonomy import PREREQUISITE_MAP, DOMAINS

logger = logging.getLogger(__name__)


class RelationInferrer:
    """关系推断引擎"""

    def __init__(self, graph_service=None, enable_llm_fallback: bool = True):
        self.graph = graph_service
        self.similarity_threshold = 0.75
        self._llm_inferrer = None
        self._enable_llm = enable_llm_fallback
        # 已处理过的技能（避免重复调用 LLM）
        self._processed_for_preq: set[str] = set()

    def _get_llm_inferrer(self):
        """延迟加载 LLM 推断器"""
        if self._llm_inferrer is None and self._enable_llm:
            try:
                from core.llm_skill_inferrer import get_llm_skill_inferrer
                self._llm_inferrer = get_llm_skill_inferrer()
            except Exception as e:
                logger.debug(f"LLM推断器加载失败: {e}")
                self._enable_llm = False
        return self._llm_inferrer

    def infer_all(self, job_data: list[dict] = None, all_skills: list[str] = None):
        """执行所有关系推断

        Args:
            job_data: 岗位数据列表（包含skills字段）
            all_skills: 所有技能名称列表
        """
        if not all_skills:
            all_skills = self._get_all_skill_names()

        logger.info(f"开始关系推断，待处理技能数: {len(all_skills)}")

        results = {
            "prerequisite_created": 0,
            "belongs_to_created": 0,
            "similar_to_created": 0,
            "total_relations": 0,
        }

        # 1. 推断先修关系
        preq_count = self._infer_prerequisites(all_skills)
        results["prerequisite_created"] = preq_count

        # 2. 推断领域归属
        domain_count = self._infer_domain_relations(all_skills)
        results["belongs_to_created"] = domain_count

        # 3. 推断相似/同义词关系
        sim_count = self._infer_similar_relations(all_skills)
        results["similar_to_created"] = sim_count

        results["total_relations"] = sum(
            [preq_count, domain_count, sim_count]
        )

        logger.info(f"关系推断完成: {results}")
        return results

    def _get_all_skill_names(self) -> list[str]:
        """获取所有技能名称"""
        if not self.graph:
            return []
        try:
            skills = self.graph.get_all_skills(limit=500)
            return [s.get("s.name", "") for s in skills if s.get("s.name")]
        except Exception as e:
            logger.warning(f"获取技能列表失败: {e}")
            return []

    def _infer_prerequisites(self, all_skills: list[str]) -> int:
        """推断先修关系 - 硬编码 PREREQUISITE_MAP 优先，LLM 兜底"""
        if not self.graph:
            return 0

        skill_set = set(all_skills)
        count = 0
        known_skills = set(PREREQUISITE_MAP.keys())

        # === 第1层：硬编码规则 ===
        applicable = skill_set & known_skills

        for skill in applicable:
            prerequisites = PREREQUISITE_MAP.get(skill, [])
            for preq in prerequisites:
                if preq not in skill_set:
                    logger.debug(f"先修技能 [{preq}] 不在图谱中，跳过")
                    continue
                ok = self.graph.create_prerequisite_relation(skill, preq)
                if ok:
                    count += 1
            self._processed_for_preq.add(skill)

        logger.info(f"硬编码先修关系推断: 创建{count}条")

        # === 第2层：LLM 兜底（仅处理硬编码未覆盖的技能）===
        llm_count = 0
        llm_inferrer = self._get_llm_inferrer()
        if llm_inferrer is None:
            return count

        uncovered = skill_set - known_skills
        # 限制单次 LLM 推断数量（避免消耗过多配额）
        max_llm_calls = min(20, len(uncovered))

        for skill in list(uncovered)[:max_llm_calls]:
            if skill in self._processed_for_preq:
                continue

            try:
                # 传入已知技能列表，让 LLM 优先选择已有的作为先修
                prerequisites = llm_inferrer.infer_prerequisites(
                    skill, known_skills=list(skill_set)
                )
                if prerequisites:
                    for preq in prerequisites:
                        # 先修技能不存在则创建
                        if preq not in skill_set:
                            self.graph.create_skill_node({"name": preq})
                            skill_set.add(preq)
                        ok = self.graph.create_prerequisite_relation(skill, preq)
                        if ok:
                            llm_count += 1
                self._processed_for_preq.add(skill)
            except Exception as e:
                logger.debug(f"LLM先修推断失败 [{skill}]: {e}")
                self._processed_for_preq.add(skill)

        if llm_count > 0:
            logger.info(f"LLM兜底先修关系推断: 创建{llm_count}条")

        return count + llm_count

    def _infer_domain_relations(self, all_skills: list[str]) -> int:
        """推断技能与领域的归属关系"""
        if not self.graph:
            return 0

        count = 0
        skill_set = set(all_skills)

        # 构建技能-领域映射
        skill_domain_map = {}
        for domain, data in DOMAINS.items():
            for cat_name, cat_skills in data["subcategories"].items():
                for skill in cat_skills:
                    skill_domain_map[skill] = domain

        for skill in skill_set:
            if skill in skill_domain_map:
                domain = skill_domain_map[skill]
                ok = self.graph.create_belongs_to_relation(skill, domain)
                if ok:
                    count += 1

        logger.info(f"领域归属关系推断完成: 创建{count}条")
        return count

    def _infer_similar_relations(self, all_skills: list[str]) -> int:
        """推断技能之间的相似关系（基于名称相似度）"""
        if not self.graph:
            return 0

        count = 0
        n = len(all_skills)

        for i in range(n):
            for j in range(i + 1, n):
                a, b = all_skills[i], all_skills[j]
                if not a or not b:
                    continue
                sim = self._name_similarity(a, b)
                if sim >= self.similarity_threshold:
                    ok = self.graph.create_similar_relation(a, b, sim)
                    if ok:
                        count += 1

        logger.info(f"相似关系推断完成: 创建{count}条")
        return count

    @staticmethod
    def _name_similarity(a: str, b: str) -> float:
        """计算两个技能名称的文本相似度"""
        if not a or not b:
            return 0.0
        
        a_lower = a.lower().replace("-", "").replace(" ", "")
        b_lower = b.lower().replace("-", "").replace(" ", "")

        # 包含关系
        if a_lower in b_lower or b_lower in a_lower:
            return 0.85

        # SequenceMatcher
        return SequenceMatcher(None, a_lower, b_lower).ratio()
