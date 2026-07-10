"""
知识图谱系统配置模块
基于 Pydantic BaseSettings 实现，支持从环境变量和 .env 文件加载配置。
"""

from functools import lru_cache
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    """LLM 相关配置 - 支持多 provider（星火/DeepSeek），通过 LLM_PROVIDER 切换

    星火配置用 SPARK_ 前缀，DeepSeek 配置用 DEEPSEEK_ 前缀。
    LLM_PROVIDER=spark 或 deepseek 决定当前用哪个。
    """

    provider: str = Field(
        default="spark",
        description="当前使用的 LLM provider: spark / deepseek",
        validation_alias="LLM_PROVIDER",
    )

    # ===== 星火配置 =====
    api_key: str = Field(
        default="", description="星火 API Key（从讯飞开放平台获取）"
    )
    api_base: str = Field(
        default="https://spark-api-open.xf-yun.com/v1",
        description="星火 API 基础 URL（OpenAI 兼容格式）"
    )
    chat_model: str = Field(
        default="generalv3", description="星火对话模型: generalv3 / generalv3.5 / 4.0Ultra"
    )
    embedding_model: str = Field(
        default="generalv3", description="星火 Embedding 模型"
    )

    # ===== DeepSeek 配置 =====
    deepseek_api_key: str = Field(
        default="", description="DeepSeek API Key",
        validation_alias="DEEPSEEK_API_KEY",
    )
    deepseek_api_base: str = Field(
        default="https://api.deepseek.com/v1",
        description="DeepSeek API 基础 URL",
        validation_alias="DEEPSEEK_API_BASE",
    )
    deepseek_chat_model: str = Field(
        default="deepseek-chat", description="DeepSeek 对话模型: deepseek-chat / deepseek-reasoner",
        validation_alias="DEEPSEEK_CHAT_MODEL",
    )

    max_tokens: int = Field(default=4096, description="最大 Token 数")
    temperature: float = Field(default=0.7, description="生成温度")

    model_config = SettingsConfigDict(env_prefix="SPARK_", env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def active_api_key(self) -> str:
        """根据 provider 返回当前生效的 API Key"""
        if self.provider == "deepseek":
            return self.deepseek_api_key
        return self.api_key

    @property
    def active_api_base(self) -> str:
        """根据 provider 返回当前生效的 base URL"""
        if self.provider == "deepseek":
            return self.deepseek_api_base
        return self.api_base

    @property
    def active_chat_model(self) -> str:
        """根据 provider 返回当前生效的对话模型"""
        if self.provider == "deepseek":
            return self.deepseek_chat_model
        return self.chat_model


class Neo4jSettings(BaseSettings):
    """Neo4j 图数据库配置"""

    uri: str = Field(default="bolt://localhost:7687", description="Neo4j 连接 URI")
    user: str = Field(default="neo4j", description="Neo4j 用户名")
    password: str = Field(default="kg_password_2024", description="Neo4j 密码")
    database: str = Field(default="neo4j", description="数据库名称")

    @property
    def connection_params(self) -> dict:
        """返回连接参数字典"""
        return {
            "uri": self.uri,
            "auth": (self.user, self.password),
            "database": self.database,
        }

    model_config = SettingsConfigDict(env_prefix="NEO4J_", env_file=".env", env_file_encoding="utf-8", extra="ignore")


class ChromaDBSettings(BaseSettings):
    """ChromaDB 向量数据库配置"""

    host: str = Field(default="localhost", description="ChromaDB 主机地址")
    port: int = Field(default=8001, description="ChromaDB 端口")

    @property
    def connection_url(self) -> str:
        """返回连接 URL"""
        return f"http://{self.host}:{self.port}"

    model_config = SettingsConfigDict(env_prefix="CHROMA_", extra="ignore")


class AppSettings(BaseSettings):
    """应用基础配置"""

    host: str = Field(default="localhost", description="应用监听主机")
    port: int = Field(default=8501, description="Streamlit 应用端口")
    api_port: int = Field(default=8000, description="FastAPI API 端口")
    debug: bool = Field(default=True, description="调试模式")
    log_level: str = Field(default="INFO", description="日志级别")

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore")


class CrawlerSettings(BaseSettings):
    """数据采集配置"""

    update_interval_hours: int = Field(
        default=24, description="数据更新间隔（小时）"
    )
    max_crawl_pages: int = Field(default=50, description="最大爬取页面数")
    request_delay_seconds: float = Field(
        default=1.5, description="请求间隔秒数"
    )

    # Playwright 浏览器爬虫（可选增强）
    enable_playwright: bool = Field(
        default=False, description="是否启用 Playwright 浏览器爬虫（需要先运行 playwright install chromium）"
    )

    # 搜索 API 配置（可选，不配置则使用免费搜索方式）
    serpapi_api_key: str = Field(
        default="", description="SerpAPI 密钥（可选，提供后可获得更稳定的搜索服务）"
    )
    bing_api_key: str = Field(
        default="", description="Bing Search API 密钥（可选）"
    )

    # 爬取目标网站配置
    target_sites: list[str] = Field(
        default=["linkedin.com/jobs", "cn.indeed.com", "zhipin.com", "lagou.com"],
        description="目标招聘网站列表"
    )

    model_config = SettingsConfigDict(env_prefix="DATA_", extra="ignore")


class Settings(BaseSettings):
    """
    全局设置聚合类
    从 .env 文件和环境变量加载所有配置项
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 子配置模块
    llm: LLMSettings = Field(default_factory=LLMSettings)
    neo4j: Neo4jSettings = Field(default_factory=Neo4jSettings)
    chromadb: ChromaDBSettings = Field(default_factory=ChromaDBSettings)
    app: AppSettings = Field(default_factory=AppSettings)
    crawler: CrawlerSettings = Field(default_factory=CrawlerSettings)

    # 项目根目录（自动检测）
    project_name: str = Field(default="knowledge-graph-system", description="项目名称")


@lru_cache()
def get_settings() -> Settings:
    """
    获取全局配置单例（带缓存）
    使用 lru_cache 确保整个应用生命周期内只创建一次 Settings 实例
    """
    return Settings()


# 导出便捷访问
settings = get_settings()
