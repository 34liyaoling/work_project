"""JD 解析服务

输入：原始 JD 文本
输出：结构化 :class:`ParsedJD`（含岗位名称 / 类别 / 级别 / 技能 / 置信度）

实现策略：
    1. 使用 :class:`SparkClient` 调用星火大模型（或 mock 模式）
    2. 用 :class:`JSONValidator` 做 JSON Schema 强制校验
    3. 失败时自动重试 + 降级到 mock
    4. 与 :mod:`cleaning` 协作，做技能标准化、O*NET 对照
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from app.core.logger import log
from app.services.llm.spark_client import SparkClient, get_spark_client
from app.services.llm.prompts import render, get_schema, get_version
from app.services.llm.json_validator import JSONValidator, ValidationOutcome, parse_json


# ============================================================
# 数据结构
# ============================================================
@dataclass
class ParsedJD:
    """解析后的 JD"""

    job_title: str
    category: str
    level: str
    core_responsibilities: List[str] = field(default_factory=list)
    required_skills: List[Dict[str, Any]] = field(default_factory=list)
    preferred_skills: List[Dict[str, Any]] = field(default_factory=list)
    typical_scenarios: List[str] = field(default_factory=list)
    confidence: float = 0.0

    # 扩展元数据
    raw: str = ""
    parse_time_ms: float = 0.0
    parser_version: str = ""
    attempt: int = 1
    fallback_used: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def skill_names(self) -> List[str]:
        """提取所有技能名（required + preferred）"""
        out: List[str] = []
        for s in self.required_skills or []:
            if isinstance(s, dict) and s.get("skill"):
                out.append(s["skill"])
        for s in self.preferred_skills or []:
            if isinstance(s, dict) and s.get("skill"):
                out.append(s["skill"])
        return out


# ============================================================
# JDParser
# ============================================================
class JDParser:
    """JD 解析服务

    用法:
        parser = JDParser()
        result = await parser.parse(jd_text)
    """

    def __init__(
        self,
        client: Optional[SparkClient] = None,
        template: str = "jd_parse",
        max_retries: int = 3,
        use_normalizer: bool = True,
    ) -> None:
        self.client = client or get_spark_client()
        self.template = template
        self.max_retries = int(max_retries)
        self.use_normalizer = bool(use_normalizer)
        self.schema = get_schema(template) or {}
        self.version = get_version(template)

    # -------------------------------------------------------- 同步入口
    def parse_sync(self, jd_text: str) -> ParsedJD:
        """同步入口（内部用 asyncio.run）"""
        import asyncio
        return asyncio.run(self.parse(jd_text))

    # -------------------------------------------------------- 异步入口
    async def parse(self, jd_text: str) -> ParsedJD:
        """解析一条 JD 文本"""
        if not jd_text or not jd_text.strip():
            return ParsedJD(
                job_title="", category="其它", level="中级",
                confidence=0.0, raw=jd_text, parser_version=self.version,
            )

        start = time.time()
        messages = self._build_messages(jd_text)
        validator = JSONValidator(self.schema)

        # 调用 LLM + 自动重试 + mock 降级
        outcome = await self._invoke_with_fallback(messages, validator, jd_text)

        if not outcome.success:
            log.warning(f"JDParser 解析失败: {outcome.errors[:3]}")
            return ParsedJD(
                job_title="未知岗位",
                category="其它",
                level="中级",
                confidence=0.0,
                raw=outcome.raw,
                parse_time_ms=(time.time() - start) * 1000,
                parser_version=self.version,
                attempt=outcome.attempt,
                fallback_used=True,
            )

        data = outcome.data
        # 字段补全（防止 mock 返回缺字段）
        data.setdefault("job_title", "未知岗位")
        data.setdefault("category", "其它")
        data.setdefault("level", "中级")
        data.setdefault("core_responsibilities", [])
        data.setdefault("required_skills", [])
        data.setdefault("preferred_skills", [])
        data.setdefault("typical_scenarios", [])
        data.setdefault("confidence", 0.5)

        # 技能标准化（可选）
        if self.use_normalizer:
            from app.services.cleaning.skill_normalizer import get_normalizer
            norm = get_normalizer()
            data["required_skills"] = self._normalize_skills(data["required_skills"], norm)
            data["preferred_skills"] = self._normalize_skills(data["preferred_skills"], norm)

        # O*NET 校验（增强 confidence 字段）
        try:
            from app.services.cleaning.onet_verifier import get_onet_verifier
            ver = get_onet_verifier().verify_skills(
                [s["skill"] for s in data["required_skills"] + data["preferred_skills"]]
            )
            # 用覆盖率微调 confidence
            coverage = ver.coverage
            data["confidence"] = round(min(1.0, float(data.get("confidence", 0.5)) * 0.7 + coverage * 0.3), 4)
            data["onet_coverage"] = coverage
            data["onet_unverified"] = ver.unverified
        except Exception as e:  # noqa: BLE001
            log.debug(f"O*NET 校验跳过: {e}")

        return ParsedJD(
            job_title=str(data["job_title"])[:128],
            category=str(data["category"])[:64],
            level=str(data["level"])[:32],
            core_responsibilities=[str(x)[:256] for x in data["core_responsibilities"]],
            required_skills=data["required_skills"],
            preferred_skills=data["preferred_skills"],
            typical_scenarios=[str(x)[:128] for x in data["typical_scenarios"]],
            confidence=float(data["confidence"]),
            raw=outcome.raw,
            parse_time_ms=(time.time() - start) * 1000,
            parser_version=self.version,
            attempt=outcome.attempt,
            fallback_used=False,
        )

    # -------------------------------------------------------- 批处理
    async def parse_batch(self, jd_texts: List[str]) -> List[ParsedJD]:
        """并发解析多条 JD"""
        import asyncio
        return await asyncio.gather(*[self.parse(t) for t in jd_texts])

    # -------------------------------------------------------- 内部
    def _build_messages(self, jd_text: str) -> List[Dict[str, str]]:
        """根据模板构造 LLM 消息"""
        tpl = render(self.template, jd_text=jd_text)
        return [
            {"role": "system", "content": tpl["system"]},
            {"role": "user", "content": tpl["user"]},
        ]

    async def _invoke_with_fallback(
        self,
        messages: List[Dict[str, str]],
        validator: JSONValidator,
        jd_text: str,
    ) -> ValidationOutcome:
        """调用 LLM + 重试 + mock 降级"""
        last_errors: List[str] = []

        for attempt in range(1, self.max_retries + 1):
            try:
                # 第 1 次直接调用；后续把错误反馈加到 user 消息
                if attempt == 1:
                    raw = await self.client.chat(messages, temperature=0.2, max_tokens=2048)
                else:
                    feedback = (
                        "\n\n【上次校验失败】请严格按以下错误修正输出：\n"
                        + "\n".join(f"- {e}" for e in last_errors[:5])
                    )
                    raw = await self.client.chat(
                        messages + [{"role": "user", "content": feedback}],
                        temperature=0.2,
                        max_tokens=2048,
                    )
                outcome = validator.validate_text(raw)
                if outcome.success:
                    outcome.attempt = attempt
                    return outcome
                last_errors = outcome.errors
                log.warning(f"JDParser 第 {attempt}/{self.max_retries} 次校验失败: {last_errors[:3]}")
            except Exception as e:  # noqa: BLE001
                last_errors = [f"llm_error: {e}"]
                log.warning(f"JDParser 第 {attempt} 次调用异常: {e}")

        # 降级到 mock：如果客户端本身已是 mock，这里相当于再生成一次
        if not self.client.mock:
            log.warning("JDParser 降级到 mock 模式")
            try:
                mock_client = SparkClient(mock=True)
                raw = await mock_client.chat(messages, temperature=0.2, max_tokens=2048)
                outcome = validator.validate_text(raw)
                outcome.attempt = self.max_retries
                return outcome
            except Exception as e:  # noqa: BLE001
                last_errors.append(f"mock_fallback_error: {e}")
        return ValidationOutcome(success=False, errors=last_errors, raw="", attempt=self.max_retries)

    @staticmethod
    def _normalize_skills(
        skills: List[Dict[str, Any]],
        normalizer,
    ) -> List[Dict[str, Any]]:
        """对解析出的技能做标准化，去重"""
        out: List[Dict[str, Any]] = []
        seen: set = set()
        for s in skills or []:
            if not isinstance(s, dict):
                continue
            raw_name = (s.get("skill") or "").strip()
            if not raw_name:
                continue
            std, cat = normalizer.normalize(raw_name)
            if std in seen:
                continue
            seen.add(std)
            out.append({
                "skill": std,
                "category": cat,
                "level": s.get("level", "熟练"),
                "weight": float(s.get("weight", 0.5)),
            })
        return out


# ============================================================
# 便捷
# ============================================================
_default_parser: Optional[JDParser] = None


def get_jd_parser() -> JDParser:
    global _default_parser
    if _default_parser is None:
        _default_parser = JDParser()
    return _default_parser


__all__ = ["JDParser", "ParsedJD", "get_jd_parser"]
