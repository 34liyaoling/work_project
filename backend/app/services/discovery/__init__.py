"""新兴岗位发现服务

包含 4 个子模块:
- cluster_analyzer: 技能组合聚类（KMeans + DBSCAN）
- role_generator: 大模型岗位定义生成
- cross_verifier: 多平台交叉验证
- confidence_evaluator: 置信度评估

提供 mock 模式（即使未安装 sklearn/未连通 LLM 也能运行）。
"""
from app.services.discovery.cluster_analyzer import ClusterAnalyzer, get_cluster_analyzer
from app.services.discovery.role_generator import RoleGenerator, get_role_generator
from app.services.discovery.cross_verifier import CrossVerifier, get_cross_verifier
from app.services.discovery.confidence_evaluator import ConfidenceEvaluator, get_confidence_evaluator


__all__ = [
    "ClusterAnalyzer",
    "RoleGenerator",
    "CrossVerifier",
    "ConfidenceEvaluator",
    "get_cluster_analyzer",
    "get_role_generator",
    "get_cross_verifier",
    "get_confidence_evaluator",
]
