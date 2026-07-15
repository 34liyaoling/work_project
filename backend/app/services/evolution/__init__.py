"""既有岗位能力动态更新服务

包含 5 个子模块:
- diff_detector: 增量采集与差异检测
- change_classifier: 变更分类（added/removed/modified/weight_changed）
- auto_router: 置信度评估与自动/人工审核路由
- snapshot_manager: 图谱版本快照保存与回滚
- timeline_tracker: 变更类型标注与时间线追踪
"""
from app.services.evolution.diff_detector import DiffDetector, get_diff_detector
from app.services.evolution.change_classifier import ChangeClassifier, get_change_classifier
from app.services.evolution.auto_router import AutoRouter, get_auto_router
from app.services.evolution.snapshot_manager import SnapshotManager, get_snapshot_manager
from app.services.evolution.timeline_tracker import TimelineTracker, get_timeline_tracker


__all__ = [
    "DiffDetector",
    "ChangeClassifier",
    "AutoRouter",
    "SnapshotManager",
    "TimelineTracker",
    "get_diff_detector",
    "get_change_classifier",
    "get_auto_router",
    "get_snapshot_manager",
    "get_timeline_tracker",
]
