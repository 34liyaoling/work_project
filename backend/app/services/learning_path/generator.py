"""学习路径生成器

基于 gap_skills + 用户已掌握技能 + 知识图谱 DEPENDS_ON 关系，
生成按学习阶段排序的学习路径。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from app.core.logger import log
from app.services.learning_path.dep_resolver import DepResolver
from app.services.learning_path.graph_planner import GraphPlanner


# 每个技能对应的推荐学习资源（mock）
LEARNING_RESOURCES: Dict[str, List[Dict[str, str]]] = {
    "Python": [
        {"type": "course", "title": "Python 官方教程", "url": "https://docs.python.org/3/tutorial/"},
        {"type": "book", "title": "Fluent Python"},
    ],
    "PyTorch": [
        {"type": "course", "title": "PyTorch 官方入门", "url": "https://pytorch.org/tutorials/"},
    ],
    "LangChain": [
        {"type": "course", "title": "LangChain 文档", "url": "https://python.langchain.com/"},
    ],
    "Kubernetes": [
        {"type": "course", "title": "Kubernetes 官方教程"},
    ],
    "MySQL": [
        {"type": "course", "title": "MySQL 8 官方文档"},
    ],
    "Redis": [
        {"type": "course", "title": "Redis 官方文档"},
    ],
    "Docker": [
        {"type": "course", "title": "Docker Get Started"},
    ],
}


class LearningPathGenerator:
    """学习路径生成器"""

    def __init__(
        self,
        planner: Optional[GraphPlanner] = None,
        resolver: Optional[DepResolver] = None,
    ):
        self.planner = planner or GraphPlanner()
        self.resolver = resolver or DepResolver()

    def generate(
        self,
        gap_skills: Sequence[Dict[str, Any]],
        user_skills: Optional[Sequence[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """生成学习路径

        :return: {"phases":[{"phase":1, "skills":[...], "estimated_hours":...}],
                  "total_skills": N, "estimated_total_hours": H}
        """
        user_skill_names = {self._norm(s) for s in user_skills or []}
        # 1. 收集所有 gap 技能 + 隐性先修
        all_skills: List[str] = []
        for g in gap_skills or []:
            name = g.get("skill")
            if not name:
                continue
            if self._norm(name) in user_skill_names:
                continue
            all_skills.append(name)
            # 找先修
            prereqs = self.resolver.resolve(name)
            for p in prereqs:
                if self._norm(p) not in user_skill_names and p not in all_skills:
                    all_skills.append(p)

        # 2. 拓扑排序得到阶段
        stages = self.planner.plan_stages(all_skills)
        # 3. 组装每个阶段的学习项
        phases: List[Dict[str, Any]] = []
        total_hours = 0
        for idx, stage_skills in enumerate(stages, 1):
            items: List[Dict[str, Any]] = []
            hours = 0
            for sname in stage_skills:
                priority = "P0" if self._is_p0(sname, gap_skills) else "P1"
                resources = LEARNING_RESOURCES.get(sname, [
                    {"type": "search", "title": f"{sname} 学习资料（自行搜索）"}
                ])
                h = self._estimate_hours(sname)
                hours += h
                items.append({
                    "skill": sname,
                    "priority": priority,
                    "estimated_hours": h,
                    "resources": resources,
                })
            total_hours += hours
            phases.append({
                "phase": idx,
                "skills": stage_skills,
                "items": items,
                "estimated_hours": hours,
            })

        log.info(f"学习路径生成: {len(phases)} 阶段 / {len(all_skills)} 技能 / {total_hours}h")
        return {
            "phases": phases,
            "total_skills": len(all_skills),
            "estimated_total_hours": total_hours,
        }

    @staticmethod
    def _norm(skill: Any) -> str:
        if isinstance(skill, dict):
            return (skill.get("skill") or skill.get("standard_name") or "").strip().lower()
        return str(skill or "").strip().lower()

    @staticmethod
    def _is_p0(skill_name: str, gap_skills: Sequence[Dict[str, Any]]) -> bool:
        for g in gap_skills or []:
            if (g.get("skill") or "").lower() == skill_name.lower():
                return g.get("priority") == "P0"
        return False

    @staticmethod
    def _estimate_hours(skill: str) -> int:
        # 简单估算：基础技能 8h，AI 框架 24h
        if any(kw in skill for kw in ["LangChain", "PyTorch", "TensorFlow", "Kubernetes", "Spark", "Flink"]):
            return 24
        return 8


_singleton: Optional[LearningPathGenerator] = None


def get_learning_path_generator() -> LearningPathGenerator:
    global _singleton
    if _singleton is None:
        _singleton = LearningPathGenerator()
    return _singleton
