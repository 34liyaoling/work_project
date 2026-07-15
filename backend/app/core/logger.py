"""日志配置"""
import sys
from loguru import logger

from app.core.config import settings


def setup_logger():
    """配置全局日志"""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO" if settings.APP_ENV != "development" else "DEBUG"
    )
    logger.add(
        "./logs/app_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="30 days",
        encoding="utf-8",
        level="INFO"
    )
    return logger


log = setup_logger()
