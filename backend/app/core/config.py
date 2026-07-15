"""应用配置管理"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # 应用
    APP_NAME: str = "CompetencyGraph"
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # MySQL
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "root"
    MYSQL_DATABASE: str = "competency_graph"

    # Neo4j
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "neo4j123"

    # Elasticsearch
    ES_HOST: str = "localhost"
    ES_PORT: int = 9200
    ES_INDEX_SKILL: str = "skill_index"
    ES_INDEX_JD: str = "jd_index"

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./data/chroma_db"

    # 讯飞星火
    SPARK_APP_ID: str = ""
    SPARK_API_KEY: str = ""
    SPARK_API_SECRET: str = ""
    SPARK_DOMAIN: str = "4.0Ultra"
    SPARK_WS_URL: str = "wss://spark-api.xf-yun.com/v4.0/chat"

    # 业务配置
    SKILL_DICT_PATH: str = "./data/skill_dictionary.json"
    SIMHASH_THRESHOLD: float = 0.85
    CONFIDENCE_THRESHOLD: float = 0.7
    HIGH_CONFIDENCE_SOURCES: int = 5
    STALE_JD_YEARS: int = 2

    # 匹配权重
    W_REQUIRED: float = 0.4
    W_PREFERRED: float = 0.2
    W_DEPTH: float = 0.25
    W_DOMAIN: float = 0.15

    @property
    def mysql_url(self) -> str:
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}?charset=utf8mb4"

    @property
    def es_url(self) -> str:
        return f"http://{self.ES_HOST}:{self.ES_PORT}"


settings = Settings()
