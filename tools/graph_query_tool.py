"""图谱查询工具 - 用于Agent查询知识图谱"""

import json
import logging
from typing import Optional
from langchain_core.tools import BaseTool
from core.graph_service import get_graph_service

logger = logging.getLogger(__name__)


class GraphQueryTool(BaseTool):
    """Neo4j知识图谱查询工具"""
    name: str = "graph_query"
    description: str = "查询知识图谱中的技能、岗位、关系等信息"

    def _run(self, query_type: str = "stats", **kwargs) -> str:
        """执行图谱查询"""
        graph = get_graph_service()

        try:
            handlers = {
                "stats": lambda: json.dumps(graph.get_graph_stats(), ensure_ascii=False, indent=2),
                "jobs": lambda: json.dumps(graph.get_all_jobs(kwargs.get("status", "active")),
                                          ensure_ascii=False, indent=2),
                "skills": lambda: json.dumps(graph.get_all_skills(domain=kwargs.get("domain")),
                                            ensure_ascii=False, indent=2),
                "job_skills": lambda: json.dumps(graph.get_job_required_skills(kwargs.get("job_title", "")),
                                                ensure_ascii=False, indent=2),
                "similar_skills": lambda: json.dumps(graph.find_similar_skills(kwargs.get("skill", ""),
                                                    kwargs.get("limit", 10)), ensure_ascii=False, indent=2),
                "path": lambda: json.dumps(graph.find_path_between_skills(
                    kwargs.get("skill_a", ""), kwargs.get("skill_b", "")), ensure_ascii=False, indent=2),
                "custom": lambda: json.dumps(graph.execute_query(kwargs.get("cypher", ""), kwargs.get("params", {})),
                                           ensure_ascii=False, indent=2),
            }

            handler = handlers.get(query_type, handlers["stats"])
            result = handler()
            return result

        except Exception as e:
            logger.error(f"图谱查询失败: {e}")
            return json.dumps({"error": str(e)}, ensure_ascii=False)


class GraphWriteTool(BaseTool):
    """Neo4j知识图谱写入工具"""
    name: str = "graph_write"
    description: str = "向知识图谱中添加新的节点或关系"

    def _run(self, operation: str = "add_skill", **kwargs) -> str:
        """执行图谱写入"""
        graph = get_graph_service()

        try:
            if operation == "add_skill":
                success = graph.create_skill_node(kwargs)
                return json.dumps({"success": success, "operation": "add_skill"})

            elif operation == "add_job":
                success = graph.create_job_node(kwargs)
                return json.dumps({"success": success, "operation": "add_job"})

            elif operation == "add_relation":
                success = graph.create_requires_relation(
                    kwargs.get("job_title", ""), kwargs.get("skill_name", ""),
                    required=kwargs.get("required", True),
                    confidence=kwargs.get("confidence", 0.8)
                )
                return json.dumps({"success": success, "operation": "add_relation"})

            else:
                return json.dumps({"error": f"不支持的操作: {operation}"})

        except Exception as e:
            return json.dumps({"error": str(e)})
