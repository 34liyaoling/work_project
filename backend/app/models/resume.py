"""简历数据模型（MySQL）"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float
from sqlalchemy.sql import func

from app.core.database import Base


class ResumeRecord(Base):
    """简历记录"""
    __tablename__ = "resume_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resume_id = Column(String(64), unique=True, index=True, comment="简历唯一ID")
    file_name = Column(String(256), comment="原始文件名")
    file_type = Column(String(16), comment="pdf/docx")
    file_size = Column(Integer, comment="文件大小（字节）")
    file_path = Column(String(512), comment="存储路径")
    raw_text = Column(Text, comment="提取的原始文本")
    parsed_data = Column(JSON, comment="解析后的结构化数据")
    name = Column(String(64), index=True, comment="姓名")
    education = Column(JSON, comment="教育经历")
    work_experience = Column(JSON, comment="工作经历")
    projects = Column(JSON, comment="项目经历")
    skills = Column(JSON, comment="技能列表（含标准名+水平）")
    skill_vector = Column(JSON, comment="技能向量（序列化为list存储）")
    uploaded_at = Column(DateTime, server_default=func.now())
    parsed_at = Column(DateTime, nullable=True)
    parse_status = Column(String(16), default="pending", comment="pending/parsing/success/failed")
    parse_accuracy = Column(Float, comment="解析准确率（测试用）")


class MatchRecord(Base):
    """人岗匹配记录"""
    __tablename__ = "match_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resume_id = Column(String(64), index=True)
    target_id = Column(String(64), index=True, comment="目标JD ID 或 岗位方向ID")
    target_type = Column(String(16), comment="jd / role")
    overall_score = Column(Float, comment="总体匹配率")
    required_score = Column(Float, comment="必备技能匹配率")
    preferred_score = Column(Float, comment="加分技能匹配率")
    depth_score = Column(Float, comment="技能深度匹配")
    domain_score = Column(Float, comment="领域契合度")
    breakdown = Column(JSON, comment="分维度匹配详情")
    gap_skills = Column(JSON, comment="技能差距分析")
    recommendations = Column(JSON, comment="改进建议")
    created_at = Column(DateTime, server_default=func.now())
