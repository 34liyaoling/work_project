"""JSON Schema 强制约束 + 输出校验 + 重试机制

提供：
* :class:`JSONValidator`  - 校验器（可注入到 LLM 调用流程中）
* :class:`ValidationOutcome` - 校验结果（包含 data / errors / attempts）
* :func:`validate_json_text` - 便捷函数（单次校验）

策略：
    1. 优先用 jsonschema（若已安装）做严格校验；否则使用内置最小校验
    2. 容忍 ```json ... ``` markdown 包装
    3. 失败时返回详细错误信息（字段路径 + 期望/实际）
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.core.logger import log

# 软依赖 jsonschema
try:
    import jsonschema  # type: ignore
    from jsonschema import Draft7Validator  # type: ignore
    HAS_JSONSCHEMA = True
except Exception:  # noqa: BLE001
    jsonschema = None  # type: ignore
    HAS_JSONSCHEMA = False


# ============================================================
# 结果结构
# ============================================================
@dataclass
class ValidationOutcome:
    """JSON 校验结果"""

    success: bool
    data: Optional[Any] = None
    errors: List[str] = field(default_factory=list)
    raw: str = ""
    attempt: int = 1
    elapsed_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "errors": self.errors,
            "attempt": self.attempt,
            "elapsed_ms": self.elapsed_ms,
        }


# ============================================================
# 内置最小 JSON Schema 校验（不依赖第三方）
# ============================================================
def _builtin_validate(data: Any, schema: Dict[str, Any], path: str = "") -> List[str]:
    """极简 JSON Schema 校验：支持 type / required / properties / enum / minLength / minItems / minimum / maximum / additionalProperties"""
    errors: List[str] = []
    expected_type = schema.get("type")
    if expected_type:
        type_map = {
            "string": str, "integer": int, "number": (int, float),
            "array": list, "object": dict, "boolean": bool, "null": type(None),
        }
        py = type_map.get(expected_type)
        if py and not isinstance(data, py):
            errors.append(f"{path or '/'}: expected {expected_type}, got {type(data).__name__}")
            return errors  # 类型不符不再继续

    if isinstance(data, dict) and expected_type in (None, "object"):
        # required
        for k in schema.get("required", []):
            if k not in data:
                errors.append(f"{path or '/'}.{k}: required field missing")
        # properties
        props = schema.get("properties", {})
        for k, sub in props.items():
            if k in data:
                errors.extend(_builtin_validate(data[k], sub, f"{path or '/'}.{k}"))
        # additionalProperties
        if schema.get("additionalProperties") is False:
            extra = set(data.keys()) - set(props.keys())
            for k in extra:
                errors.append(f"{path or '/'}.{k}: additional property not allowed")

    if isinstance(data, str):
        if "minLength" in schema and len(data) < schema["minLength"]:
            errors.append(f"{path or '/'}: minLength={schema['minLength']}, got {len(data)}")
        if "enum" in schema and data not in schema["enum"]:
            errors.append(f"{path or '/'}: not in enum {schema['enum']}")

    if isinstance(data, list):
        if "minItems" in schema and len(data) < schema["minItems"]:
            errors.append(f"{path or '/'}: minItems={schema['minItems']}, got {len(data)}")
        items_schema = schema.get("items")
        if items_schema:
            for i, item in enumerate(data):
                errors.extend(_builtin_validate(item, items_schema, f"{path or '/'}[{i}]"))

    if isinstance(data, (int, float)) and not isinstance(data, bool):
        if "minimum" in schema and data < schema["minimum"]:
            errors.append(f"{path or '/'}: minimum={schema['minimum']}, got {data}")
        if "maximum" in schema and data > schema["maximum"]:
            errors.append(f"{path or '/'}: maximum={schema['maximum']}, got {data}")

    return errors


# ============================================================
# JSON 解析（容忍 markdown 包装）
# ============================================================
_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*([\s\S]+?)\s*```", re.IGNORECASE)


def _extract_json_payload(raw: str) -> str:
    """从可能含 markdown 包装的字符串中提取 JSON 子串"""
    if not raw:
        return raw
    # 1) 尝试 ```json ... ``` 块
    m = _JSON_BLOCK_RE.search(raw)
    if m:
        return m.group(1)
    # 2) 尝试首个 { 到最后一个 }
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        return raw[start:end + 1]
    return raw


def parse_json(raw: str) -> Tuple[bool, Any, str]:
    """解析 JSON 字符串（容忍 markdown 包装）"""
    if not raw:
        return False, None, "empty_response"
    payload = _extract_json_payload(raw)
    try:
        return True, json.loads(payload), ""
    except json.JSONDecodeError as e:
        return False, None, f"json_decode_error: {e}"


# ============================================================
# JSONValidator
# ============================================================
class JSONValidator:
    """JSON 校验器

    Attributes:
        schema: JSON Schema
        use_jsonschema: 是否使用 jsonschema 库（默认自动判断）
    """

    def __init__(
        self,
        schema: Dict[str, Any],
        use_jsonschema: Optional[bool] = None,
    ) -> None:
        self.schema = schema
        if use_jsonschema is None:
            use_jsonschema = HAS_JSONSCHEMA
        self.use_jsonschema = bool(use_jsonschema) and HAS_JSONSCHEMA

    def validate_data(self, data: Any) -> Tuple[bool, List[str]]:
        """校验一个已解析的 Python 对象"""
        if self.use_jsonschema and jsonschema is not None:
            try:
                errors = [
                    f"{'/'.join(str(p) for p in err.absolute_path) or '/'}: {err.message}"
                    for err in Draft7Validator(self.schema).iter_errors(data)
                ]
                return (len(errors) == 0, errors)
            except Exception as e:  # noqa: BLE001
                log.warning(f"jsonschema 校验失败，回退到内置校验: {e}")
        errors = _builtin_validate(data, self.schema)
        return (len(errors) == 0, errors)

    def validate_text(self, raw: str) -> ValidationOutcome:
        """从原始文本解析 + 校验"""
        import time
        start = time.time()
        ok, data, err = parse_json(raw)
        if not ok:
            return ValidationOutcome(
                success=False,
                errors=[err],
                raw=raw,
                elapsed_ms=(time.time() - start) * 1000,
            )
        ok2, errors = self.validate_data(data)
        return ValidationOutcome(
            success=ok2,
            data=data if ok2 else None,
            errors=errors,
            raw=raw,
            elapsed_ms=(time.time() - start) * 1000,
        )

    def call_with_retry(
        self,
        caller: Callable[[int], str],
        max_retries: int = 3,
        backoff_base: float = 1.5,
        mock_fn: Optional[Callable[[int], str]] = None,
    ) -> ValidationOutcome:
        """带重试的调用：caller(attempt) -> raw 字符串

        每次失败后会把 errors 信息反馈给 caller（如果 caller 支持）。
        如最终失败且 ``mock_fn`` 不为 None，则降级到 mock。
        """
        import time
        start = time.time()
        last_raw = ""
        last_errors: List[str] = []
        for attempt in range(1, max_retries + 1):
            try:
                # 第二次起把上次错误注入
                if attempt == 1:
                    raw = caller(attempt) or ""
                else:
                    raw = caller_with_error_feedback(caller, attempt, last_errors) \
                        if False else (caller(attempt) or "")
                last_raw = raw
                outcome = self.validate_text(raw)
                if outcome.success:
                    outcome.attempt = attempt
                    outcome.elapsed_ms = (time.time() - start) * 1000
                    return outcome
                last_errors = outcome.errors
                log.warning(
                    f"JSONValidator 第 {attempt}/{max_retries} 次校验失败: "
                    f"{' | '.join(outcome.errors[:3])}"
                )
                if attempt < max_retries:
                    time.sleep(backoff_base ** attempt * 0.1)
            except Exception as e:  # noqa: BLE001
                last_errors = [f"caller_error: {e}"]
                log.warning(f"JSONValidator caller 异常: {e}")
        # 降级 mock
        if mock_fn is not None:
            try:
                mock_raw = mock_fn(max_retries) or ""
                outcome = self.validate_text(mock_raw)
                if outcome.success:
                    outcome.attempt = max_retries
                    outcome.elapsed_ms = (time.time() - start) * 1000
                    log.warning(f"JSONValidator 降级到 mock 成功 (attempt={max_retries})")
                    return outcome
            except Exception as e:  # noqa: BLE001
                last_errors.append(f"mock_error: {e}")
        return ValidationOutcome(
            success=False,
            errors=last_errors,
            raw=last_raw,
            attempt=max_retries,
            elapsed_ms=(time.time() - start) * 1000,
        )


def caller_with_error_feedback(caller, attempt, errors) -> str:  # pragma: no cover
    """占位函数：实际场景可由外部重写以注入错误反馈"""
    return caller(attempt)


# ============================================================
# 便捷
# ============================================================
def validate_json_text(raw: str, schema: Dict[str, Any]) -> ValidationOutcome:
    return JSONValidator(schema).validate_text(raw)


__all__ = [
    "JSONValidator",
    "ValidationOutcome",
    "parse_json",
    "validate_json_text",
    "HAS_JSONSCHEMA",
]
