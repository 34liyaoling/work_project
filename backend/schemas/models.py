"""FastAPI API 数据模型"""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


# ====== 通用响应模型 ======

class ApiResponse(BaseModel):
    """统一API响应格式"""
    success: bool = True
    message: str = "ok"
    data: Optional[Any] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    error: str = "Unknown error"
    detail: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


# ====== 数据采集相关 ======

class CollectionRequest(BaseModel):
    """数据采集请求"""
    sources: Optional[list[str]] = None  # 指定数据源，None表示全部
    limit_per_source: int = 50
    force_refresh: bool = False


class CollectionResponse(BaseModel):
    """数据采集响应"""
    total_collected: int
    total_deduplicated: int
    sources_detail: dict
    duration_seconds: float


# ====== 简历解析相关 ======

class ResumeUploadResponse(BaseModel):
    """简历上传响应"""
    resume_id: str
    name: Optional[str] = None
    skill_count: int
    credibility_score: float
    technical_level: str
    parsing_time_ms: int


class ResumeProfileResponse(BaseModel):
    """简历画像响应"""
    name: Optional[str]
    skills_explicit: list[str]
    skills_implicit: list[str]
    skills_with_credibility: list[dict]
    projects: list[dict]
    experience_years: float
    technical_level: str
    embedding_available: bool


# ====== 匹配相关 ======

class MatchRequest(BaseModel):
    """匹配请求"""
    resume_id: str
    top_n: int = 10
    filters: Optional[dict] = None  # {domain, salary_range, location}


class MatchResultItem(BaseModel):
    """单条匹配结果"""
    job_title: str
    match_score: float
    breakdown: dict
    matched_skills: list[str]
    missing_critical: list[str]
    explanation: str


class MatchResponse(BaseModel):
    """匹配响应"""
    matches: list[MatchResultItem]
    total_scanned: int
    best_match: Optional[MatchResultItem] = None


# ====== 差距分析相关 ======

class GapAnalysisRequest(BaseModel):
    """差距分析请求"""
    resume_id: str
    target_job: Optional[str] = None  # 不指定则做全面分析


class GapAnalysisResponse(BaseModel):
    """差距分析响应"""
    target_job: str
    match_rate: float
    matched_skills: list[str]
    missing_critical: list[str]
    missing_optional: list[str]
    learning_path: dict
    roi_analysis: dict
    summary: str


# ====== 岗位发现相关 ======

class JobDiscoveryResponse(BaseModel):
    """岗位发现响应"""
    candidates: list[dict]
    discovered_count: int
    discovery_time: str


class JobApproveRequest(BaseModel):
    """岗位审核请求"""
    candidate_title: str
    approved: bool
    reviewer: str = "admin"
    comment: str = ""


# ====== 图谱相关 ======

class GraphStatsResponse(BaseModel):
    """图谱统计响应"""
    nodes: dict
    edges: dict
    domains: list[dict]
    last_updated: str


class GraphQueryRequest(BaseModel):
    """图谱查询请求"""
    query_type: str  # stats/jobs/skills/path/custom
    params: dict = {}


# ====== 市场情报相关 ======

class MarketIntelResponse(BaseModel):
    """市场情报响应"""
    job_title: str
    openings: int
    salary_range: tuple[int, int]
    trend: str
    top_skills: list[dict]
    city_distribution: dict[str, int]


# ====== What-If 分析相关 ======

class WhatIfRequest(BaseModel):
    """What-If分析请求"""
    resume_id: str
    added_skills: list[str]


class WhatIfResponse(BaseModel):
    """What-If分析响应"""
    original_top3: list[dict]
    enhanced_top3: list[dict]
    comparison: dict
    recommendation: str


# ====== 质量检查相关 ======

class QualityCheckResponse(BaseModel):
    """质量检查响应"""
    overall_status: str
    data_quality: dict
    graph_quality: dict
    compliance: dict
    issues_found: int
    recommendations: list[str]
