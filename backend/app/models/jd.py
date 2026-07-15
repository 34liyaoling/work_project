"""JD 数据模型（MySQL）"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, Index
from sqlalchemy.sql import func

from app.core.database import Base


class JDRecord(Base):
    """招聘JD记录"""
    __tablename__ = "jd_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    jd_id = Column(String(64), unique=True, index=True, comment="JD唯一标识")
    source = Column(String(32), index=True, comment="数据来源平台")
    source_url = Column(String(512), comment="原始URL")
    company = Column(String(128), index=True, comment="公司名")
    title = Column(String(256), comment="岗位名称")
    category = Column(String(64), index=True, comment="岗位类别")
    level = Column(String(32), comment="级别：初级/中级/高级/资深")
    location = Column(String(64), comment="工作地点")
    salary_range = Column(String(64), comment="薪资范围")
    raw_text = Column(Text, comment="原始JD文本")
    parsed_data = Column(JSON, comment="LLM解析后的结构化数据")
    skills = Column(JSON, comment="提取的技能列表")
    published_at = Column(DateTime, comment="JD发布时间")
    crawled_at = Column(DateTime, server_default=func.now(), comment="采集时间")
    simhash = Column(String(64), index=True, comment="SimHash指纹")
    credibility_score = Column(Float, default=0.5, comment="数据可信度评分 0-1")
    is_processed = Column(Integer, default=0, comment="是否已处理 0/1")
    is_duplicate = Column(Integer, default=0, comment="是否重复 0/1")

    __table_args__ = (
        Index("idx_source_published", "source", "published_at"),
    )


class SkillSynonym(Base):
    """技能同义词映射"""
    __tablename__ = "skill_synonyms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alias = Column(String(128), unique=True, index=True, comment="别名/缩写")
    standard_name = Column(String(128), index=True, comment="标准名称")
    category = Column(String(64), comment="技能分类")
    created_at = Column(DateTime, server_default=func.now())


class DataCrawlLog(Base):
    """数据采集日志"""
    __tablename__ = "data_crawl_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(32), index=True)
    task_type = Column(String(32), comment="任务类型: full/incremental")
    started_at = Column(DateTime, server_default=func.now())
    finished_at = Column(DateTime, nullable=True)
    total_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    status = Column(String(16), default="running", comment="running/success/failed")
