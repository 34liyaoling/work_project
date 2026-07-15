"""Pydantic 请求/响应模型定义

集中管理所有 API 的请求与响应数据模型，保证接口契约一致性。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ====================== 通用响应 ======================

class CommonResponse(BaseModel):
    """统一响应格式"""
    code: int = 0
    message: str = "success"
    data: Optional[Any] = None


class Pagination(BaseModel):
    """分页结构"""
    page: int = 1
    page_size: int = 20
    total: int = 0


class PageResponse(BaseModel):
    """分页响应"""
    items: List[Any] = []
    pagination: Pagination = Field(default_factory=Pagination)


# ====================== JD 相关 ======================

class JDCreateRequest(BaseModel):
    """创建 JD 请求"""
    source: str = Field(..., description="数据来源：拉勾/Boss直聘/猎聘 等")
    source_url: Optional[str] = None
    company: str = Field(..., description="公司名")
    title: str = Field(..., description="岗位名称")
    category: Optional[str] = None
    level: Optional[str] = None
    location: Optional[str] = None
    salary_range: Optional[str] = None
    raw_text: str = Field(..., description="JD 原始文本")
    published_at: Optional[datetime] = None


class JDResponse(BaseModel):
    """JD 详情响应"""
    jd_id: str
    source: str
    source_url: Optional[str] = None
    company: str
    title: str
    category: Optional[str] = None
    level: Optional[str] = None
    location: Optional[str] = None
    salary_range: Optional[str] = None
    raw_text: str
    parsed_data: Optional[Dict[str, Any]] = None
    skills: List[str] = []
    published_at: Optional[datetime] = None
    crawled_at: Optional[datetime] = None
    is_processed: int = 0
    credibility_score: float = 0.5


class JDBatchParseRequest(BaseModel):
    """批量 JD 解析请求"""
    jd_ids: List[str] = Field(..., description="待解析的 JD ID 列表")
    force: bool = Field(default=False, description="是否强制重解析")


class JDParseTaskResponse(BaseModel):
    """JD 解析任务响应"""
    task_id: str
    total: int
    success: int = 0
    failed: int = 0
    results: List[Dict[str, Any]] = []


# ====================== 简历相关 ======================

class ResumeResponse(BaseModel):
    """简历详情响应"""
    resume_id: str
    file_name: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    name: Optional[str] = None
    education: List[Dict[str, Any]] = []
    work_experience: List[Dict[str, Any]] = []
    projects: List[Dict[str, Any]] = []
    skills: List[Dict[str, Any]] = []
    uploaded_at: Optional[datetime] = None
    parsed_at: Optional[datetime] = None
    parse_status: str = "pending"
    parse_accuracy: Optional[float] = None


class ResumeSkillItem(BaseModel):
    """简历中的技能条目"""
    name: str
    standard_name: Optional[str] = None
    category: Optional[str] = None
    level: str = Field(default="intermediate", description="beginner/intermediate/advanced")
    years: Optional[float] = None
    source: Optional[str] = None


class ResumeParseRequest(BaseModel):
    """触发解析请求"""
    force: bool = False


# ====================== 图谱相关 ======================

class GraphNode(BaseModel):
    """图谱节点"""
    id: str
    label: str
    type: str = Field(..., description="skill/jobrole/tool/industry")
    category: Optional[str] = None
    level: Optional[str] = None
    popularity: float = 0.0
    properties: Dict[str, Any] = {}


class GraphEdge(BaseModel):
    """图谱边"""
    source: str
    target: str
    relation: str = Field(..., description="requires/related_to/belongs_to")
    weight: float = 1.0
    properties: Dict[str, Any] = {}


class GraphData(BaseModel):
    """图谱数据（供 G6 渲染）"""
    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []
    metadata: Dict[str, Any] = {}


class SkillDependencyItem(BaseModel):
    """技能依赖节点"""
    name: str
    level: int = 0
    relation: str
    category: Optional[str] = None


class SkillTimelineItem(BaseModel):
    """技能时间线节点"""
    date: str
    event_type: str = Field(..., description="added/removed/weight_changed/usage_changed")
    skill_name: str
    change_detail: Dict[str, Any] = {}
    confidence: float = 1.0


class GraphSnapshotRequest(BaseModel):
    """图谱快照请求"""
    description: str = Field(..., description="快照说明")


class GraphSnapshotResponse(BaseModel):
    """图谱快照响应"""
    snapshot_id: str
    description: str
    node_count: int
    edge_count: int
    created_at: datetime


# ====================== 匹配相关 ======================

class MatchJDRequest(BaseModel):
    """与具体 JD 匹配请求"""
    resume_id: str
    jd_id: str
    weights: Optional[Dict[str, float]] = Field(
        default=None,
        description="自定义权重：required/preferred/depth/domain"
    )


class MatchRoleRequest(BaseModel):
    """与岗位方向匹配请求"""
    resume_id: str
    top_n: int = Field(default=10, ge=1, le=50)
    weights: Optional[Dict[str, float]] = None


class MatchBreakdownItem(BaseModel):
    """分维度匹配详情"""
    dimension: str
    score: float
    weight: float
    matched_skills: List[str] = []
    missing_skills: List[str] = []


class GapSkillItem(BaseModel):
    """技能差距项"""
    skill_name: str
    standard_name: Optional[str] = None
    category: Optional[str] = None
    status: str = Field(..., description="missing/met/exceeded")
    importance: float = 1.0
    suggestion: Optional[str] = None


class MatchResultResponse(BaseModel):
    """匹配结果响应"""
    match_id: int
    resume_id: str
    target_id: str
    target_type: str
    target_name: Optional[str] = None
    overall_score: float
    required_score: float
    preferred_score: float
    depth_score: float
    domain_score: float
    breakdown: List[MatchBreakdownItem] = []
    gap_skills: List[GapSkillItem] = []
    recommendations: List[str] = []
    learning_path: List[Dict[str, Any]] = []
    created_at: datetime


# ====================== 采集相关 ======================

class CrawlStartRequest(BaseModel):
    """启动采集请求"""
    source: str = Field(..., description="拉勾/Boss直聘/猎聘/LinkedIn")
    keywords: List[str] = Field(..., description="搜索关键词列表")
    max_count: int = Field(default=100, ge=1, le=10000)
    task_type: str = Field(default="incremental", description="full/incremental")
    location: Optional[str] = None


class CrawlTaskResponse(BaseModel):
    """采集任务响应"""
    task_id: str
    source: str
    status: str
    total_count: int = 0
    success_count: int = 0
    failed_count: int = 0
    started_at: datetime
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None


class CrawlLogItem(BaseModel):
    """采集日志项"""
    id: int
    source: str
    task_type: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    total_count: int
    success_count: int
    failed_count: int
    status: str
    error_message: Optional[str] = None


class MockDataRequest(BaseModel):
    """生成模拟数据请求"""
    jd_count: int = Field(default=50, ge=1, le=1000)
    resume_count: int = Field(default=20, ge=1, le=200)
    role_count: int = Field(default=10, ge=1, le=100)


# ====================== 岗位管理相关 ======================

class JobRoleResponse(BaseModel):
    """岗位响应"""
    role_id: str
    name: str
    category: Optional[str] = None
    level: Optional[str] = None
    core_responsibilities: List[str] = []
    required_skills: List[Dict[str, Any]] = []
    preferred_skills: List[Dict[str, Any]] = []
    typical_scenarios: List[str] = []
    confidence: float
    evidence_sources: List[str] = []
    is_new: int = 0
    is_reviewed: int = 0
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class RoleDiscoverRequest(BaseModel):
    """岗位发现请求"""
    days: int = Field(default=30, description="回溯天数")
    min_source_count: int = Field(default=3, description="最少证据来源数")


class RoleReviewRequest(BaseModel):
    """岗位审核请求"""
    action: str = Field(..., description="approve/reject/modify")
    reviewer: Optional[str] = None
    comment: Optional[str] = None
    modified_data: Optional[Dict[str, Any]] = None


class AuditQueueItem(BaseModel):
    """审核队列项"""
    id: int
    entity_type: str
    entity_id: str
    entity_data: Dict[str, Any]
    reason: Optional[str] = None
    status: str
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_comment: Optional[str] = None
    created_at: datetime
