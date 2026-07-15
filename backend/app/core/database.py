"""MySQL 数据库连接"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from typing import Generator

from app.core.config import settings
from app.core.logger import log


Base = declarative_base()

# 创建数据库引擎
engine = create_engine(
    settings.mysql_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """获取数据库会话（依赖注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库表"""
    try:
        # 导入所有模型以便创建表
        from app.models import jd, resume, job_role, audit_log  # noqa
        Base.metadata.create_all(bind=engine)
        log.info("MySQL 数据库表初始化完成")
    except Exception as e:
        log.error(f"MySQL 数据库初始化失败: {e}")
        raise
