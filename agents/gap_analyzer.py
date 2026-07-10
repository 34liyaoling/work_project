"""差距分析Agent - 学习路径规划与ROI分析"""

import logging
from typing import Any
from .base_agent import BaseKnowledgeAgent
from core.graph_service import get_graph_service
from core.llm_service import get_llm_service

logger = logging.getLogger(__name__)


class GapAnalyzerAgent(BaseKnowledgeAgent):
    """差距分析Agent

    分析维度：
    1. 技能缺口清单
    2. 能力等级差距
    3. 学习成本评估
    4. 学习ROI分析
    5. 最优学习路径规划
    """

    agent_name = "gap_analyzer"
    agent_description = "差距分析与学习规划专家 - 科学的能力提升路线图"

    def __init__(self):
        super().__init__()
        self.graph = get_graph_service()
        self.llm = get_llm_service()

    def _setup_tools(self):
        pass

    def analyze_gaps(self, resume_profile: dict, target_job: str) -> dict:
        """分析指定目标的差距"""
        # 获取目标岗位要求（使用模糊搜索）
        job_skills = self.graph.get_job_required_skills(target_job, fuzzy=True)
        
        # 如果没有找到匹配，返回提示信息
        if not job_skills:
            # 尝试在所有岗位中搜索最接近的
            all_jobs = self.graph.get_all_jobs(status="all")
            matched_job = None
            for job in all_jobs:
                job_title = job.get("title", "").lower()
                target = target_job.lower().replace("招聘", "").strip()
                if target in job_title or job_title[:10] in target:
                    matched_job = job.get("title")
                    job_skills = self.graph.get_job_required_skills(matched_job, fuzzy=False)
                    if job_skills:
                        break
            
            if not job_skills:
                return {
                    "target_job": target_job,
                    "actual_matched_job": None,
                    "overall_match_rate": 0,
                    "matched_skills": [],
                    "missing_critical": [],
                    "missing_optional": [],
                    "learning_path": [],
                    "roi_analysis": {
                        "total_effort_weeks": 0,
                        "total_effort_months": 0,
                        "expected_salary_increase_pct": 0,
                        "per_skill_analysis": [],
                        "recommendation_priority": [],
                    },
                    "summary": f"未找到与「{target_job}」相关的岗位数据，请先采集相关岗位数据或尝试其他岗位名称。",
                }
        
        # 获取实际匹配的岗位名称
        actual_job = job_skills[0].get("matched_title", target_job) if job_skills else target_job
        
        # 去重处理
        required = list(dict.fromkeys([s["skill_name"] for s in job_skills if s.get("relation_type") == "requires"]))
        optional = list(dict.fromkeys([s["skill_name"] for s in job_skills if s.get("relation_type") == "prefers"]))

        resume_skills = set(resume_profile.get("skills", [])) | set(resume_profile.get("implicit_skills", []))

        # 缺口分析
        missing_critical = [s for s in required if s not in resume_skills]
        missing_optional = [s for s in optional if s not in resume_skills]
        matched_required = [s for s in required if s in resume_skills]

        # 学习路径
        learning_path = self._plan_learning_path(missing_critical + missing_optional, resume_skills)

        # ROI分析
        roi_analysis = self._analyze_learning_roi(missing_critical, actual_job)

        return {
            "target_job": target_job,
            "actual_matched_job": actual_job,
            "overall_match_rate": len(matched_required) / max(len(required), 1),
            "matched_skills": matched_required,
            "missing_critical": missing_critical,
            "missing_optional": missing_optional,
            "learning_path": learning_path,
            "roi_analysis": roi_analysis,
            "summary": self._gen_gap_summary(matched_required, missing_critical, actual_job),
        }

    def full_gap_analysis(self, resume_profile: dict) -> dict:
        """全面差距分析（对所有可能的目标岗位）"""
        jobs = self.graph.get_all_jobs(status="active")

        all_gaps = []
        for job in jobs[:15]:  # 取前15个岗位分析
            title = job.get("title", "")
            gap = self.analyze_gaps(resume_profile, title)
            gap["match_rate"] = gap["overall_match_rate"]
            all_gaps.append(gap)

        # 按匹配度排序
        all_gaps.sort(key=lambda x: x["match_rate"], reverse=True)

        return {
            "best_matches": all_gaps[:5],
            "hardest_targets": all_gaps[-3:] if len(all_gaps) > 3 else [],
            "average_match": sum(g["match_rate"] for g in all_gaps) / max(len(all_gaps), 1),
            "recommendations": self._gen_recommendations(all_gaps[:5]),
        }

    def _plan_learning_path(self, missing_skills: list[str], current_skills: set) -> list[dict]:
        """规划最优学习路径"""
        if not missing_skills:
            return []

        steps = []
        for i, skill in enumerate(missing_skills):
            # 查询前置技能
            prerequisites = self._find_prerequisites(skill, current_skills)

            # 估算学习时间
            difficulty = self._estimate_difficulty(skill)
            duration_weeks = difficulty * 2  # 简化估计

            # 查找学习资源
            resources = self._suggest_resources(skill)

            # 计算该技能的市场价值
            market_value = self._get_skill_market_value(skill)

            steps.append({
                "step": i + 1,
                "skill": skill,
                "duration_weeks": duration_weeks,
                "difficulty": difficulty,
                "prerequisites": prerequisites,
                "resources": resources,
                "market_value": market_value,
                "roi_estimate": market_value / max(duration_weeks, 1),
            })

        # 按ROI排序
        steps.sort(key=lambda x: x["roi_estimate"], reverse=True)

        # 重编号
        for i, step in enumerate(steps):
            step["step"] = i + 1

        total_weeks = sum(s["duration_weeks"] for s in steps)

        return {
            "steps": steps,
            "total_weeks": total_weeks,
            "total_months": round(total_weeks / 4.33, 1),
            "phase_breakdown": {
                "foundation": [s for s in steps if s["difficulty"] <= 3],
                "intermediate": [s for s in steps if 4 <= s["difficulty"] <= 6],
                "advanced": [s for s in steps if s["difficulty"] > 6],
            },
        }

    def _analyze_learning_roi(self, missing_critical: list[str], target_job: str) -> dict:
        """分析学习投入产出比"""
        total_effort = 0
        total_value = 0

        skill_analysis = []
        for skill in missing_critical:
            difficulty = self._estimate_difficulty(skill)
            effort = difficulty * 2  # 周数
            value = self._get_skill_market_value(skill)

            skill_analysis.append({
                "skill": skill,
                "effort_weeks": effort,
                "market_value": value,
                "roi": value / max(effort, 1),
            })

            total_effort += effort
            total_value += value

        return {
            "total_effort_weeks": total_effort,
            "total_effort_months": round(total_effort / 4.33, 1),
            "expected_salary_increase_pct": min(total_value * 2, 80),  # 估算薪资涨幅
            "per_skill_analysis": sorted(skill_analysis, key=lambda x: x["roi"], reverse=True),
            "recommendation_priority": [s["skill"] for s in sorted(skill_analysis, key=lambda x: x["roi"], reverse=True)[:5]],
        }

    def _find_prerequisites(self, skill: str, current_skills: set) -> list[str]:
        """查找前置技能"""
        prereq_map = {
            "LangChain": ["Python", "API设计"],
            "RAG": ["Python", "向量数据库", "Embedding", "LLM基础"],
            "Kubernetes": ["Docker", "Linux"],
            "PyTorch": ["Python", "NumPy", "线性代数"],
            "微服务": ["编程语言", "数据库", "HTTP协议"],
            "Flink": ["Java/Scala", "流式计算概念"],
            "Spark": ["Scala/Python", "Hadoop基础"],
            "DeepSpeed": ["PyTorch", "分布式训练概念"],
            "LoRA": ["PyTorch", "微调概念"],
        }

        prereqs = prereq_map.get(skill, [])
        return [p for p in prereqs if p not in current_skills]

    def _estimate_difficulty(self, skill: str) -> int:
        """估算技能学习难度(1-10)"""
        easy = {"HTML", "CSS", "Markdown", "Git", "SQL基础", "Excel"}
        medium = {"Python", "JavaScript", "Java", "Docker", "Redis", "MySQL", "Linux"}
        hard = {"Kubernetes", "PyTorch", "TensorFlow", "Flink", "Spark", "RAG系统设计"}
        very_hard = {"DeepSpeed", "分布式系统设计", "编译原理", "密码学"}

        skill_lower = skill.lower()
        if any(e.lower() in skill_lower for e in very_hard):
            return 9
        if any(h.lower() in skill_lower for h in hard):
            return 7
        if any(m.lower() in skill_lower for m in medium):
            return 5
        if any(e_.lower() in skill_lower for e_ in easy):
            return 2
        return 5  # 默认中等

    def _suggest_resources(self, skill: str) -> list[str]:
        """推荐学习资源"""
        resource_map = {
            "Python": ["Python官方教程", "LeetCode", "Real Python"],
            "LangChain": ["LangChain官方文档", "LangChain Cookbook"],
            "RAG": ["RAG实战指南", "LlamaIndex教程", "向量数据库入门"],
            "PyTorch": ["PyTorch官方教程", "动手学深度学习"],
            "Kubernetes": ["Kubernetes官方文档", "Kubernetes in Action中文版"],
            "Docker": ["Docker从入门到实践", "Docker官方教程"],
            "LLM": ["吴恩达深度学习课程", "李沐《动手学深度学习》"],
        }

        base = resource_map.get(skill, [f"{skill}官方文档", f"{skill}实战教程", "相关GitHub项目"])
        return base

    def _get_skill_market_value(self, skill: str) -> float:
        """获取技能市场价值（薪资溢价估算）"""
        premium_map = {
            "LangChain": 12, "RAG系统设计": 10, "AI Agent开发": 12,
            "PyTorch": 8, "Kubernetes": 8, "Flink": 7,
            "DeepSpeed": 10, "LoRA": 8, "Prompt Engineering": 6,
            "多智能体协作": 11, "vLLM": 9, "模型蒸馏": 9,
        }
        return premium_map.get(skill, 5)

    def _gen_gap_summary(self, matched: list, missing: list, target: str) -> str:
        """生成差距摘要"""
        if not missing:
            return f"恭喜！您已经基本满足「{target}」的要求，匹配度很高。"

        total = len(matched) + len(missing)
        rate = len(matched) / max(total, 1)

        return (f"「{target}」匹配度{rate:.0%}，已掌握{len(matched)}/{total}项核心技能，"
                f"还需补齐{len(missing)}项关键技能。最优先学习: {', '.join(missing[:3])}。")

    def _gen_recommendations(self, top_matches: list[dict]) -> list[str]:
        """生成推荐"""
        recs = []
        for m in top_matches[:3]:
            target = m.get("target_job", "")
            rate = m.get("match_rate", 0)
            if rate >= 0.7:
                recs.append(f"「{target}」匹配度高({rate:.0%})，可以尝试投递")
            elif rate >= 0.4:
                recs.append(f"「{target}」有一定基础({rate:.0%})，补齐{len(m.get('missing_critical', []))}项技能后可尝试")
        return recs

    def _form_hypothesis(self, task_input: Any, perception: dict) -> dict:
        return {"strategy": "multi_dimensional_gap_analysis"}

    def _act(self, hypothesis: Any, task_input: Any, **kwargs) -> Any:
        resume = kwargs.get("resume_profile")
        target = kwargs.get("target_job")

        if resume and target:
            return self.analyze_gaps(resume, target)
        elif resume:
            return self.full_gap_analysis(resume)
        return {"error": "需要提供resume_profile参数"}
