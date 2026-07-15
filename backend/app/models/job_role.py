"""岗位定义卡片与审计日志（MySQL）"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float
from sqlalchemy.sql import func

from app.core.database import Base


class JobRoleCard(Base):
    """岗位定义卡片（图谱中的岗位节点）"""
    __tablename__ = "job_role_cards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role_id = Column(String(64), unique=True, index=True, comment="岗位唯一ID")
    name = Column(String(128), comment="岗位名称")
    category = Column(String(64), index=True, comment="岗位类别")
    level = Column(String(32), comment="级别")
    core_responsibilities = Column(JSON, comment="核心职责列表")
    required_skills = Column(JSON, comment="必备技能（含级别与权重）")
    preferred_skills = Column(JSON, comment="加分技能")
    typical_scenarios = Column(JSON, comment="典型应用场景")
    confidence = Column(Float, comment="岗位定义置信度 0-1")
    evidence_sources = Column(JSON, comment="证据来源（JDs）")
    is_new = Column(Integer, default=0, comment="是否新兴岗位 0/1")
    is_reviewed = Column(Integer, default=0, comment="是否人工审核通过 0/1")
    reviewed_by = Column(String(64), nullable=True, comment="审核人")
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class GraphChangeLog(Base):
    """图谱变更日志（动态演化追踪）"""
    __tablename__ = "graph_change_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    change_type = Column(String(16), index=True, comment="added/removed/modified/weight_changed")
    node_type = Column(String(32), comment="jobrole/skill/tool")
    node_id = Column(String(64), index=True)
    node_name = Column(String(128))
    change_detail = Column(JSON, comment="变更详情")
    confidence = Column(Float, comment="置信度")
    source_count = Column(Integer, default=1, comment="数据源数量")
    is_auto_applied = Column(Integer, default=0, comment="是否自动应用 0/1")
    snapshot_id = Column(String(64), nullable=True, comment="图谱版本快照ID")
    created_at = Column(DateTime, server_default=func.now())


class GraphSnapshot(Base):
    """图谱版本快照（支持回滚）"""
    __tablename__ = "graph_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(String(64), unique=True, index=True)
    description = Column(String(256), comment="快照说明")
    node_count = Column(Integer, default=0)
    edge_count = Column(Integer, default=0)
    snapshot_data = Column(JSON, comment="快照数据（节点+边）")
    created_at = Column(DateTime, server_default=func.now())


class AuditLog(Base):
    """人工审核日志（低置信度节点审核队列）"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String(32), comment="实体类型: jobrole/skill/edge")
    entity_id = Column(String(64), index=True)
    entity_data = Column(JSON, comment="待审核数据")
    reason = Column(String(256), comment="进入审核的原因")
    status = Column(String(16), default="pending", comment="pending/approved/rejected")
    reviewed_by = Column(String(64), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_comment = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
