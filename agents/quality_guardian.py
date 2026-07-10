"""质量守卫Agent - 全流程质量保障与合规审计"""

import logging
from typing import Any
from .base_agent import BaseKnowledgeAgent
from core.graph_service import get_graph_service
from core.hallucination_guard import FactChecker

logger = logging.getLogger(__name__)


class QualityGuardianAgent(BaseKnowledgeAgent):
    """质量守卫Agent

    职责：
    1. 数据质量检查
    2. 图谱质量检查
    3. 输出质量检查
    4. 合规检查
    5. 审计日志
    """

    agent_name = "quality_guardian"
    agent_description = "质量守卫 - 保障系统输出的准确性、公平性和合规性"

    def __init__(self):
        super().__init__()
        self.graph = get_graph_service()
        self.fact_checker = FactChecker(self.graph)
        self.audit_log: list[dict] = []

    def _setup_tools(self):
        pass

    def run_full_check(self) -> dict:
        """运行全面质量检查"""
        results = {
            "data_quality": self._check_data_quality(),
            "graph_quality": self._check_graph_quality(),
            "compliance": self._check_compliance(),
            "overall_status": "unknown",
            "issues_found": 0,
            "recommendations": [],
        }

        total_issues = sum(v.get("issue_count", 0) for v in results.values() if isinstance(v, dict))
        results["issues_found"] = total_issues

        if total_issues == 0:
            results["overall_status"] = "healthy"
            results["recommendations"].append("系统运行正常，无需干预")
        elif total_issues <= 10:
            results["overall_status"] = "warning"
            results["recommendations"].append(f"发现{total_issues}个小问题，建议关注")
        else:
            results["overall_status"] = "attention_needed"
            results["recommendations"].append(f"发现{total_issues}个问题，需要处理")

        self.audit_log.append({"check_time": __import__('datetime').datetime.now().isoformat(), "results": results})
        return results

    def _check_data_quality(self) -> dict:
        """数据质量检查"""
        issues = []

        # 检查图谱中的数据完整性
        jobs_without_skills = self.graph.execute_query("""
            MATCH (j:Job) WHERE NOT (j)-[:requires]->() RETURN j.title AS title
        """)
        if jobs_without_skills:
            details = [j.get("title", "") for j in jobs_without_skills[:5] if j.get("title")]
            issues.append({"type": "missing_skills", "count": len(jobs_without_skills),
                          "details": details})

        # 检查低置信度节点
        low_conf_skills = self.graph.execute_query("""
            MATCH (s:Skill) WHERE s.confidence < 0.5 RETURN s.name AS name, s.confidence AS confidence LIMIT 20
        """)
        if low_conf_skills:
            issues.append({"type": "low_confidence", "count": len(low_conf_skills)})

        return {"status": "ok" if not issues else "issues_found", "issue_count": len(issues), "issues": issues}

    def _check_graph_quality(self) -> dict:
        """图谱质量检查"""
        stats = self.graph.get_graph_stats()
        issues = []

        # 孤立节点检测
        orphan_ratio = 0
        total_nodes = stats.get("total_nodes", 0)
        if total_nodes > 0:
            # 简化检查
            pass

        # 关系密度
        relations = stats.get("total_relations", 0)
        density = relations / max(total_nodes * (total_nodes - 1), 1) if total_nodes > 1 else 0

        if density < 0.01 and total_nodes > 10:
            issues.append({"type": "sparse_graph", "detail": "图谱过于稀疏"})

        return {"status": "ok" if not issues else "issues_found", "issue_count": len(issues),
                "graph_stats": stats, "density": round(density, 4), "issues": issues}

    def _check_compliance(self) -> dict:
        """合规检查"""
        issues = []

        # 检查是否有敏感数据泄露风险
        person_nodes = self.graph.execute_query("""
            MATCH (p:Person) RETURN p.name AS name, p.phone AS phone, p.email AS email LIMIT 10
        """)
        sensitive_found = 0
        for p in person_nodes:
            if p.get("phone") or p.get("email"):
                sensitive_found += 1

        if sensitive_found > 0:
            issues.append({"type": "privacy_risk", "count": sensitive_found,
                          "detail": f"{sensitive_found}条个人敏感信息需脱敏"})

        return {"status": "ok" if not issues else "issues_found", "issue_count": len(issues), "issues": issues}

    def verify_output(self, output: dict) -> dict:
        """验证特定输出结果的质量"""
        checks = {
            "has_content": bool(output and any(v for v in output.values() if v)),
            "no_empty_arrays": all(isinstance(v, list) and len(v) > 0 for v in output.values() if isinstance(v, list)),
            "scores_valid": all(0 <= v <= 1 for v in output.values() if isinstance(v, (int, float))),
        }

        passed = sum(checks.values())
        total = len(checks)

        return {
            "passed_checks": passed,
            "total_checks": total,
            "pass_rate": passed / max(total, 1),
            "details": checks,
            "verdict": "approved" if passed == total else "needs_review" if passed >= total * 0.7 else "rejected",
        }

    def get_audit_log(self, limit: int = 10) -> list[dict]:
        """获取审计日志"""
        return self.audit_log[-limit:]

    def _form_hypothesis(self, task_input: Any, perception: dict) -> dict:
        return {"strategy": "comprehensive_quality_audit"}

    def _act(self, hypothesis: Any, task_input: Any, **kwargs) -> Any:
        check_type = kwargs.get("check_type", "full")
        if check_type == "full":
            return self.run_full_check()
        elif check_type == "verify":
            output = kwargs.get("output")
            return self.verify_output(output) if output else {"error": "需要output参数"}
        return self.run_full_check()
