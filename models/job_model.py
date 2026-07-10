"""岗位相关数据模型"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class JobPostSource(str, Enum):
    """招聘岗位数据来源"""
    BOSS_ZHIPIN = "boss_zhipin"
    LAGOU = "lagou"
    LIEPIN = "liepin"
    ZHAOPIN = "zhaopin"
    GITHUB = "github"
    REPORT = "report"
    MANUAL = "manual"
    SAMPLE = "sample"
    WEB_SEARCH = "web_search"


class JobPostRaw(BaseModel):
    """原始岗位帖子数据"""
    source: JobPostSource = Field(..., description="数据来源")
    source_confidence: float = Field(default=0.8, description="来源置信度")
    timestamp: datetime = Field(default_factory=datetime.now)
    raw_content: str = Field("", description="原始内容")

    # 提取后的结构化字段
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    skills: list[str] = Field(default_factory=list)
    salary_min: Optional[int] = None  # K/月
    salary_max: Optional[int] = None
    location: Optional[str] = None
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    education: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    job_description: Optional[str] = None

    # 质量指标
    completeness_score: float = Field(default=0.0, description="完整度分数")
    freshness_score: float = Field(default=1.0, description="新鲜度分数")


class JobDiscoveryCandidate(BaseModel):
    """候选新岗位发现结果"""
    suggested_title: str = Field(..., description="建议的岗位标题")
    skill_cluster: list[str] = Field(..., description="关联的技能簇")
    confidence: float = Field(..., description="发现置信度")
    evidence_sources: list[str] = Field(default_factory=list, description="证据来源")
    growth_rate: float = Field(default=0.0, description="增长率")
    similar_existing_jobs: list[str] = Field(default_factory=list, description="相似的已有岗位")
    suggested_definition: Optional[dict] = Field(default=None, description="建议的完整定义")
    discovery_reason: str = Field(default="", description="发现原因说明")
    timestamp: datetime = Field(default_factory=datetime.now)


class JobMarketIntelligence(BaseModel):
    """岗位市场情报"""
    job_title: str
    total_openings: int = 0
    openings_change_30d: float = 0.0  # 30天变化百分比
    avg_salary_min: int = 0
    avg_salary_max: int = 0
    competition_level: str = "medium"  # low/medium/high
    top_companies: list[str] = Field(default_factory=list)
    top_skills: list[dict] = Field(default_factory=list)  # [{skill, frequency}]
    city_distribution: dict[str, int] = Field(default_factory=dict)  # {city: count}
    demand_forecast: str = "stable"  # rising/stable/falling
