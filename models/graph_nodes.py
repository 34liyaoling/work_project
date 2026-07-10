"""图谱节点与关系的数据模型定义"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class SkillCategory(str, Enum):
    """技能类别"""
    PROGRAMMING_LANGUAGE = "programming_language"
    FRAMEWORK = "framework"
    TOOL = "tool"
    DATABASE = "database"
    MIDDLEWARE = "middleware"
    CLOUD_SERVICE = "cloud_service"
    AI_ML = "ai_ml"
    SOFT_SKILL = "soft_skill"
    DOMAIN_KNOWLEDGE = "domain_knowledge"
    OTHER = "other"


class SkillDomain(str, Enum):
    """技术领域"""
    ARTIFICIAL_INTELLIGENCE = "人工智能"
    BIG_DATA = "大数据"
    CLOUD_COMPUTING = "云计算"
    BLOCKCHAIN = "区块链"
    IOT = "物联网"
    CYBERSECURITY = "网络安全"
    SOFTWARE_DEVELOPMENT = "软件开发"
    MOBILE_DEVELOPMENT = "移动开发"
    DEVOPS = "DevOps"
    DATA_SCIENCE = "数据科学"


class LifecycleStage(str, Enum):
    """生命周期阶段"""
    EMERGING = "emerging"       # 新兴
    GROWING = "growing"         # 成长
    MATURE = "mature"           # 成熟
    DECLINING = "declining"     # 衰退
    OBSOLETE = "obsolete"       # 过时


class JobStatus(str, Enum):
    """岗位状态"""
    ACTIVE = "active"           # 活跃
    CANDIDATE = "candidate"     # 候选（待审核）
    ARCHIVED = "archived"       # 归档


class SkillNode(BaseModel):
    """技能节点模型"""
    name: str = Field(..., description="技能名称")
    category: SkillCategory = Field(..., description="技能类别")
    domain: SkillDomain = Field(..., description="所属领域")
    difficulty: int = Field(default=5, ge=1, le=10, description="难度等级(1-10)")
    trend_score: float = Field(default=0.0, ge=-1.0, le=1.0, description="趋势分数(-1到1)")
    lifecycle: LifecycleStage = Field(default=LifecycleStage.GROWING, description="生命周期阶段")
    version: str = Field(default="1.0", description="版本号")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="置信度")
    sources: list[str] = Field(default_factory=list, description="数据来源列表")
    last_updated: datetime = Field(default_factory=datetime.now, description="最后更新时间")
    related_jobs: list[str] = Field(default_factory=list, description="相关岗位列表")
    description: Optional[str] = Field(default=None, description="技能描述")
    aliases: list[str] = Field(default_factory=list, description="别名/同义词")

    class Config:
        from_attributes = True


class JobNode(BaseModel):
    """岗位节点模型"""
    title: str = Field(..., description="岗位标题")
    domain: SkillDomain = Field(..., description="所属领域")
    status: JobStatus = Field(default=JobStatus.ACTIVE, description="岗位状态")
    required_skills: list[str] = Field(default_factory=list, description="必备技能列表")
    optional_skills: list[str] = Field(default_factory=list, description="可选技能列表")
    avg_salary_min: Optional[int] = Field(default=None, description="最低平均薪资(K)")
    avg_salary_max: Optional[int] = Field(default=None, description="最高平均薪资(K)")
    experience_range: tuple[int, int] = Field(default=(1, 3), description="经验要求范围(年)")
    education_requirement: str = Field(default="本科", description="学历要求")
    demand_trend: str = Field(default="stable", description="需求趋势(rising/stable/falling)")
    discovered_date: Optional[datetime] = Field(default=None, description="发现日期")
    definition_source: str = Field(default="manual", description="定义来源(manual/auto_discovered/updated)")
    version: float = Field(default=1.0, description="版本号")
    description: Optional[str] = Field(default=None, description="岗位描述")
    responsibilities: list[str] = Field(default_factory=list, description="职责列表")
    companies_hiring: list[str] = Field(default_factory=list, description="招聘公司示例")

    class Config:
        from_attributes = True


class DomainNode(BaseModel):
    """领域节点模型"""
    name: str = Field(..., description="领域名称")
    parent_domain: Optional[str] = Field(default=None, description="父领域")
    description: Optional[str] = Field(default=None, description="领域描述")
    trend_score: float = Field(default=0.0, description="趋势分数")

    class Config:
        from_attributes = True


class PersonNode(BaseModel):
    """人员节点模型（简历解析后生成）"""
    name: Optional[str] = Field(default=None, description="姓名")
    skills: list[str] = Field(default_factory=list, description="技能列表")
    experience_years: int = Field(default=0, description="工作年限")
    education: str = Field(default="", description="学历")
    current_position: Optional[str] = Field(default=None, description="当前职位")
    resume_hash: str = Field(default="", description="简历哈希(用于去重)")
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True


class GraphTriple(BaseModel):
    """知识三元组模型"""
    head: str = Field(..., description="头实体")
    relation: str = Field(..., description="关系类型")
    tail: str = Field(..., description="尾实体")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="置信度")
    source_id: Optional[str] = Field(default=None, description="来源ID")
    evidence: Optional[str] = Field(default=None, description="原始证据片段")
    timestamp: datetime = Field(default_factory=datetime.now)
    properties: dict[str, Any] = Field(default_factory=dict, description="附加属性")

    class Config:
        from_attributes = True
