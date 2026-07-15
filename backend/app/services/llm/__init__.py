"""讯飞星火大模型集成与 JD 解析

包含：
* :mod:`spark_client`  - 讯飞星火 WebSocket 客户端（HMAC 鉴权 / 流式 / OpenAI 兼容降级）
* :mod:`prompts`       - 提示词模板 + JSON Schema
* :mod:`jd_parser`     - JD 结构化解析服务
* :mod:`json_validator`- JSON Schema 强制校验 + 重试
* :mod:`test_dataset`  - 100 条 JD 解析测试集 + 评估函数
"""
from __future__ import annotations

from app.services.llm.spark_client import (
    SparkClient,
    SparkAuthError,
    SparkAPIError,
    MockLLMError,
    get_spark_client,
)
from app.services.llm.prompts import (
    TEMPLATES,
    JD_OUTPUT_SCHEMA,
    render,
    get_schema,
    get_version,
)
from app.services.llm.jd_parser import JDParser, ParsedJD
from app.services.llm.json_validator import JSONValidator, ValidationOutcome
from app.services.llm.test_dataset import (
    build_test_dataset,
    evaluate_parser,
    TEST_CASES,
)

__all__ = [
    # LLM 客户端
    "SparkClient",
    "SparkAuthError",
    "SparkAPIError",
    "MockLLMError",
    "get_spark_client",
    # 模板
    "TEMPLATES",
    "JD_OUTPUT_SCHEMA",
    "render",
    "get_schema",
    "get_version",
    # JD 解析
    "JDParser",
    "ParsedJD",
    # 校验
    "JSONValidator",
    "ValidationOutcome",
    # 测试集
    "build_test_dataset",
    "evaluate_parser",
    "TEST_CASES",
]
