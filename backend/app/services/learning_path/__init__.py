"""学习路径规划服务

包含 4 个子模块:
- generator: 基于技能差距生成学习路径
- graph_planner: 结合图谱 DEPENDS_ON 关系规划学习顺序
- dep_resolver: 先修技能依赖关系识别
- recommender: 改进建议生成
"""
from app.services.learning_path.generator import LearningPathGenerator, get_learning_path_generator
from app.services.learning_path.graph_planner import GraphPlanner, get_graph_planner
from app.services.learning_path.dep_resolver import DepResolver, get_dep_resolver
from app.services.learning_path.recommender import Recommender, get_recommender


__all__ = [
    "LearningPathGenerator",
    "GraphPlanner",
    "DepResolver",
    "Recommender",
    "get_learning_path_generator",
    "get_graph_planner",
    "get_dep_resolver",
    "get_recommender",
]
