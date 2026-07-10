"""简历相关数据模型"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class CredibilityLevel(str, Enum):
    """可信度级别"""
    EXPLICIT_CERTIFIED = "explicit_certified"      # 有证书认证
    EXPLICIT_PROJECT = "explicit_project"            # 项目经验明确提及
    IMPLICIT_INFERRED = "implicit_inferred"          # 从项目推断
    MENTIONED_ONLY = "mentioned_only"               # 仅在技能栏提及
    SELF_CLAIMED = "self_claimed"                   # 自称无佐证


class SkillWithCredibility(BaseModel):
    """带可信度的技能条目"""
    skill_name: str
    credibility_level: CredibilityLevel
    credibility_score: float = Field(ge=0.0, le=1.0)
    evidence: Optional[str] = None  # 证据文本
    proficiency_level: Optional[int] = Field(default=None, ge=1, le=10)  # 熟练度


class ProjectExperience(BaseModel):
    """项目经验"""
    project_name: str
    role: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: str = ""
    technologies_used: list[str] = Field(default_factory=list)
    complexity_score: float = Field(default=0.5, ge=0.0, le=1.0)  # 复杂度评分
    tech_depth_scores: dict[str, int] = Field(default_factory=dict)  # 技术深度 {skill: level}
    red_flags: list[str] = Field(default_factory=list)  # 警告标志
    strengths: list[str] = Field(default_factory=list)


class WorkExperience(BaseModel):
    """工作经验"""
    company: str
    position: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None  # "至今" 或具体日期
    description: str = ""
    department: Optional[str] = None


class EducationRecord(BaseModel):
    """教育记录"""
    school: str
    degree: str  # 学士/硕士/博士等
    major: str
    graduation_date: Optional[str] = None
    gpa: Optional[float] = None


class ResumeProfile(BaseModel):
    """完整的简历画像"""
    # 基本信息
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None

    # 教育背景
    education: list[EducationRecord] = Field(default_factory=list)

    # 工作经历
    work_experience: list[WorkExperience] = Field(default_factory=list)
    total_experience_years: float = Field(default=0.0)

    # 项目经验
    projects: list[ProjectExperience] = Field(default_factory=list)

    # 技能（核心）
    skills_explicit: list[str] = Field(default_factory=list)  # 显性技能
    skills_implicit: list[str] = Field(default_factory=list)   # 隐含推断技能
    skills_with_credibility: list[SkillWithCredibility] = Field(default_factory=list)

    # 向量表示
    embedding_vector: Optional[list[float]] = Field(default=None)

    # 元数据
    file_path: Optional[str] = None
    file_type: Optional[str] = None  # pdf/docx/txt/image
    parsed_at: datetime = Field(default_factory=datetime.now)
    resume_hash: str = Field(default="")

    # 综合评估
    overall_technical_level: str = Field(default="mid")  # junior/mid/senior/expert
    diversity_score: float = Field(default=0.0)  # 技能多样性
    growth_potential: float = Field(default=0.5)  # 成长潜力
