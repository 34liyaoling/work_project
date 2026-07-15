"""讯飞星火大模型 WebSocket 客户端

特性：
    1. HMAC-SHA256 鉴权 URL 构造（符合讯飞官方协议）
    2. 支持流式 / 非流式调用
    3. 凭据缺失或环境变量 ``MOCK_LLM=true`` 时自动降级到 mock
    4. 可选降级到 OpenAI 兼容 HTTP 模式（不同 SPARK_WS_URL 协议）

注意：websockets 库做软依赖；未安装时真实模式不可用但 mock 仍可跑。
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import os
import re
from datetime import datetime
from time import mktime
from typing import Any, AsyncIterator, Dict, List, Optional
from urllib.parse import urlencode, urlparse

import httpx

from app.core.config import settings
from app.core.logger import log


# 软依赖
try:
    import websockets  # type: ignore
    HAS_WEBSOCKETS = True
except Exception:  # noqa: BLE001
    websockets = None  # type: ignore
    HAS_WEBSOCKETS = False


class SparkAuthError(RuntimeError):
    """Spark 鉴权失败"""


class SparkAPIError(RuntimeError):
    """Spark 接口调用失败"""


class MockLLMError(RuntimeError):
    """Mock LLM 调用错误（向后兼容旧 llm_client.py 提供的异常）"""


def _is_mock_mode() -> bool:
    """统一读取 MOCK_LLM 开关"""
    return str(os.getenv("MOCK_LLM", "true")).lower() in ("1", "true", "yes")


# ============================================================
# SparkClient
# ============================================================
class SparkClient:
    """讯飞星火大模型客户端

    用法:
        client = SparkClient()
        text = await client.chat([
            {"role": "system", "content": "..."},
            {"role": "user",   "content": "..."},
        ])
    """

    def __init__(
        self,
        app_id: Optional[str] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        domain: Optional[str] = None,
        ws_url: Optional[str] = None,
        timeout: float = 60.0,
        mock: Optional[bool] = None,
        openai_compatible: bool = False,
    ) -> None:
        self.app_id = app_id or settings.SPARK_APP_ID
        self.api_key = api_key or settings.SPARK_API_KEY
        self.api_secret = api_secret or settings.SPARK_API_SECRET
        self.domain = domain or settings.SPARK_DOMAIN
        self.ws_url = ws_url or settings.SPARK_WS_URL
        self.timeout = float(timeout)
        self.openai_compatible = bool(openai_compatible)
        self.mock = mock if mock is not None else _is_mock_mode()
        # 关键凭据缺失时强制 mock
        if not self.openai_compatible and not (self.app_id and self.api_key and self.api_secret):
            log.warning("Spark 凭据不完整，自动启用 MOCK 模式")
            self.mock = True

    # ----------------- 鉴权 -----------------
    def _build_authorization_url(self) -> str:
        """构造带鉴权参数的 WebSocket URL"""
        if self.mock or self.openai_compatible:
            return self.ws_url
        parsed = urlparse(self.ws_url)
        host = parsed.hostname or ""
        path = parsed.path or "/"
        now = datetime.utcnow()
        date = now.strftime("%a, %d %b %Y %H:%M:%S GMT")
        signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"
        signature_sha = hmac.new(
            self.api_secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        signature = base64.b64encode(signature_sha).decode("utf-8")
        authorization_origin = (
            f'api_key="{self.api_key}", algorithm="hmac-sha256", '
            f'headers="host date request-line", signature="{signature}"'
        )
        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")
        params = {"authorization": authorization, "date": date, "host": host}
        return f"{self.ws_url}?{urlencode(params)}"

    # ----------------- 公共接口 -----------------
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2048,
        user_id: str = "default",
    ) -> str:
        """非流式对话，返回完整文本"""
        if self.mock:
            return await self._mock_chat(messages, temperature, max_tokens)
        if self.openai_compatible:
            return await self._call_openai_http(messages, temperature, max_tokens, user_id)
        return await self._call_spark(messages, temperature, max_tokens, user_id, stream=False)

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2048,
        user_id: str = "default",
    ) -> AsyncIterator[str]:
        """流式对话，异步迭代每个 chunk"""
        if self.mock:
            text = await self._mock_chat(messages, temperature, max_tokens)
            for chunk in self._chunk_text(text, 30):
                yield chunk
                await asyncio.sleep(0.01)
            return
        if self.openai_compatible:
            text = await self._call_openai_http(messages, temperature, max_tokens, user_id)
            for chunk in self._chunk_text(text, 30):
                yield chunk
            return
        async for chunk in self._call_spark_stream(messages, temperature, max_tokens, user_id):
            yield chunk

    # ----------------- 真实 API（WebSocket） -----------------
    async def _call_spark(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        user_id: str,
        stream: bool,
    ) -> str:
        if not HAS_WEBSOCKETS:
            raise SparkAPIError("websockets 库未安装，无法调用真实 Spark API")
        auth_url = self._build_authorization_url()
        payload = {
            "header": {"app_id": self.app_id, "uid": user_id},
            "parameter": {
                "chat": {
                    "domain": self.domain,
                    "temperature": max(0.0, min(temperature, 1.0)),
                    "max_tokens": max_tokens,
                    "auditing": "default",
                }
            },
            "payload": {"message": {"text": messages}},
        }
        collected: List[str] = []
        async with websockets.connect(auth_url, ping_interval=None, close_timeout=10) as ws:  # type: ignore
            await ws.send(json.dumps(payload))
            async for raw in ws:
                data = json.loads(raw)
                code = data.get("header", {}).get("code", 0)
                if code != 0:
                    raise SparkAPIError(
                        f"Spark 错误 code={code}: {data.get('header', {}).get('message')}"
                    )
                choices = data.get("payload", {}).get("choices", {})
                status = choices.get("status", 0)
                text_list = choices.get("text", []) or []
                for item in text_list:
                    content = item.get("content", "")
                    if content:
                        collected.append(content)
                if status == 2:
                    break
        return "".join(collected)

    async def _call_spark_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        user_id: str,
    ) -> AsyncIterator[str]:
        text = await self._call_spark(messages, temperature, max_tokens, user_id, stream=True)
        for chunk in self._chunk_text(text, 30):
            yield chunk
            await asyncio.sleep(0.01)

    # ----------------- OpenAI 兼容 HTTP 模式 -----------------
    async def _call_openai_http(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        user_id: str,
    ) -> str:
        """通过 OpenAI 兼容 HTTP 接口调用（适用于 OpenAI / 代理 / 第三方兼容服务）"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    self.ws_url,  # 这里 ws_url 实际是 http(s) URL
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.domain,
                        "messages": messages,
                        "temperature": max(0.0, min(temperature, 1.0)),
                        "max_tokens": max_tokens,
                        "user": user_id,
                        "stream": False,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:  # noqa: BLE001
            raise SparkAPIError(f"OpenAI 兼容接口调用失败: {e}") from e

    # ----------------- Mock 模式 -----------------
    async def _mock_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """基于规则和输入动态生成结构化响应

        策略: 解析 messages 中最后一条 user 消息，识别任务类型
        （jd_parse / role_definition / resume_parse / skill_extract / generic），
        然后基于 JD/简历文本中的关键词动态构造 JSON。
        """
        await asyncio.sleep(0.05)  # 模拟网络延迟
        user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_msg = m.get("content", "")
                break
        task = self._infer_task(user_msg)
        if task == "jd_parse":
            return self._mock_jd_response(user_msg)
        if task == "role_definition":
            return self._mock_role_response(user_msg)
        if task == "skill_extract":
            return self._mock_skill_response(user_msg)
        if task == "resume_parse":
            return self._mock_resume_response(user_msg)
        return json.dumps({"text": f"[MOCK LLM] 收到 {len(user_msg)} 字符"}, ensure_ascii=False)

    @staticmethod
    def _infer_task(user_msg: str) -> str:
        text = user_msg
        if "聚类信息" in text or "簇 id" in text.lower():
            return "role_definition"
        if "JD 原文" in text or "schema 严格输出" in text or "招聘 JD" in text:
            return "jd_parse"
        if "简历文本" in text or "候选人简历" in text:
            return "resume_parse"
        if "技术技能名词" in text or "识别" in text and "技能" in text:
            return "skill_extract"
        return "generic"

    @staticmethod
    def _extract_jd_text(user_msg: str) -> str:
        m = re.search(r"【JD 原文】\s*(.+?)\s*【输出】", user_msg, re.DOTALL)
        if m:
            return m.group(1)
        m = re.search(r"【JD 原文】\s*(.+)", user_msg, re.DOTALL)
        if m:
            return m.group(1)
        return user_msg

    @staticmethod
    def _extract_cluster_info(user_msg: str) -> Dict[str, str]:
        info: Dict[str, str] = {}
        for key in ["簇 ID", "簇大小", "跨公司数", "涉及平台", "技能组合", "代表性 JD 摘要"]:
            m = re.search(rf"-\s*{key}[^:]*:\s*([^\n]*)", user_msg)
            if m:
                info[key] = m.group(1).strip()
        return info

    def _mock_jd_response(self, user_msg: str) -> str:
        """根据 JD 文本动态构造解析结果"""
        jd_text = self._extract_jd_text(user_msg)
        title = self._extract_title(jd_text)
        category = self._detect_category(jd_text)
        level = self._detect_level(jd_text)
        responsibilities = self._extract_responsibilities(jd_text)
        required = self._extract_skills(jd_text, kind="required")
        preferred = self._extract_skills(jd_text, kind="preferred")
        scenarios = self._detect_scenarios(jd_text)
        confidence = self._estimate_confidence(jd_text)
        result = {
            "job_title": title,
            "category": category,
            "level": level,
            "core_responsibilities": responsibilities,
            "required_skills": required,
            "preferred_skills": preferred,
            "typical_scenarios": scenarios,
            "confidence": confidence,
        }
        return json.dumps(result, ensure_ascii=False)

    def _mock_role_response(self, user_msg: str) -> str:
        """根据聚类信息动态生成新兴岗位定义"""
        info = self._extract_cluster_info(user_msg)
        skill_freq = info.get("技能组合", "")
        skills: List[Dict[str, Any]] = []
        for token in re.split(r"[,、;；\s]+", skill_freq):
            token = token.strip()
            if not token:
                continue
            weight = 0.7 + (hash(token) % 25) / 100.0
            weight = round(min(weight, 0.95), 2)
            skills.append({"skill": token, "level": "熟练", "weight": weight})
        if not skills:
            skills = [{"skill": "Python", "level": "熟练", "weight": 0.8}]
        required = [s for s in skills if s["weight"] >= 0.7][:6]
        preferred = [s for s in skills if s["weight"] < 0.7][:4]
        confidence = round(sum(s["weight"] for s in required) / max(len(required), 1) * 0.9, 2)
        result = {
            "job_title": info.get("簇 ID", "新兴技术岗"),
            "category": "AI工程师",
            "level": "中级",
            "core_responsibilities": [
                f"基于 {','.join(s['skill'] for s in required[:3])} 设计系统方案",
                "推进跨团队技术落地与性能优化",
            ],
            "required_skills": required,
            "preferred_skills": preferred,
            "typical_scenarios": ["智能客服系统", "数据驱动决策"],
            "confidence": confidence,
        }
        return json.dumps(result, ensure_ascii=False)

    def _mock_skill_response(self, user_msg: str) -> str:
        text = user_msg.split("【文本】")[-1] if "【文本】" in user_msg else user_msg
        candidates = re.findall(r"[A-Za-z][A-Za-z0-9+#.\-]{1,15}", text)
        seen = set()
        skills = []
        for c in candidates:
            key = c.lower()
            if key in seen:
                continue
            seen.add(key)
            skills.append({
                "skill": c,
                "category": "工具",
                "confidence": 0.75,
                "evidence": c,
            })
            if len(skills) >= 10:
                break
        if not skills:
            skills = [{"skill": "Python", "category": "语言", "confidence": 0.8, "evidence": "Python"}]
        return json.dumps({"skills": skills}, ensure_ascii=False)

    def _mock_resume_response(self, user_msg: str) -> str:
        text = user_msg.split("【简历文本】")[-1] if "【简历文本】" in user_msg else user_msg
        skills = []
        for token in re.findall(r"[A-Za-z][A-Za-z0-9+#.\-]{1,15}", text):
            if token.lower() in {s["skill"].lower() for s in skills}:
                continue
            skills.append({"skill": token, "level": "熟练", "confidence": 0.75, "evidence": token})
            if len(skills) >= 8:
                break
        result = {
            "name": "候选人",
            "email": "candidate@example.com",
            "phone": "13800000000",
            "education": [],
            "work_experience": [],
            "projects": [],
            "skills": skills or [{"skill": "Python", "level": "熟练", "confidence": 0.8, "evidence": "Python"}],
        }
        return json.dumps(result, ensure_ascii=False)

    # ----------------- 辅助 -----------------
    @staticmethod
    def _chunk_text(text: str, size: int):
        for i in range(0, len(text), size):
            yield text[i: i + size]

    @staticmethod
    def _extract_title(jd_text: str) -> str:
        for line in jd_text.splitlines():
            line = line.strip()
            if not line:
                continue
            if any(kw in line for kw in ["岗位", "职位", "招聘", "Engineer", "Developer", "Manager"]):
                return line[:64]
        return jd_text.splitlines()[0][:64] if jd_text else "未知岗位"

    @staticmethod
    def _detect_category(jd_text: str) -> str:
        mapping = {
            "算法": "算法工程师", "AI": "AI工程师", "深度学习": "AI工程师",
            "前端": "前端开发", "React": "前端开发", "Vue": "前端开发",
            "后端": "后端开发", "Java": "后端开发", "Go": "后端开发", "Python": "后端开发",
            "数据": "数据科学", "数据工程": "数据工程",
            "测试": "测试开发", "QA": "测试开发",
            "运维": "运维", "SRE": "运维", "DevOps": "DevOps",
            "产品": "产品经理", "设计": "设计师", "运营": "运营", "市场": "市场",
            "HR": "HR", "芯片": "芯片", "嵌入式": "嵌入式", "IC": "芯片",
        }
        for kw, cat in mapping.items():
            if kw in jd_text:
                return cat
        return "其它"

    @staticmethod
    def _detect_level(jd_text: str) -> str:
        if any(kw in jd_text for kw in ["资深", "专家", "Staff", "Principal"]):
            return "资深"
        if any(kw in jd_text for kw in ["高级", "Senior", "Sr."]):
            return "高级"
        if any(kw in jd_text for kw in ["中级", "Intermediate", "P5", "P6"]):
            return "中级"
        if any(kw in jd_text for kw in ["初级", "Junior", "应届", "实习"]):
            return "初级"
        return "中级"

    @staticmethod
    def _extract_responsibilities(jd_text: str) -> List[str]:
        duties = []
        keywords = ["负责", "Requirements", "Responsibilities", "职责"]
        for line in jd_text.splitlines():
            s = line.strip(" \t-•·*")
            if not s:
                continue
            if any(s.startswith(k) for k in keywords) or (10 < len(s) < 120 and "。" in s):
                duties.append(s[:200])
            if len(duties) >= 6:
                break
        if not duties:
            duties = ["完成团队交付的研发任务"]
        return duties

    @staticmethod
    def _extract_skills(jd_text: str, kind: str) -> List[Dict[str, Any]]:
        tech_keywords = [
            "Python", "Java", "Go", "C++", "Rust", "Scala", "JavaScript", "TypeScript",
            "React", "Vue", "Angular", "Node.js", "Spring", "Django", "Flask", "FastAPI",
            "MySQL", "PostgreSQL", "MongoDB", "Redis", "Kafka", "Elasticsearch", "ClickHouse",
            "Docker", "Kubernetes", "Helm", "Istio", "Prometheus", "Grafana", "Jenkins",
            "PyTorch", "TensorFlow", "Hugging Face", "LangChain", "LLM", "RAG",
            "Spark", "Flink", "Hadoop", "Hive", "Airflow", "dbt",
            "AWS", "GCP", "Azure", "阿里云", "腾讯云",
            "Git", "Linux", "CI/CD", "Agile", "Scrum",
        ]
        found = []
        for token in tech_keywords:
            if token in jd_text:
                level = "熟练" if kind == "required" else "基础"
                weight = round(0.6 + (hash(token + kind) % 35) / 100.0, 2)
                found.append({"skill": token, "level": level, "weight": weight})
            if len(found) >= 6:
                break
        return found

    @staticmethod
    def _detect_scenarios(jd_text: str) -> List[str]:
        scenarios = []
        for line in jd_text.splitlines():
            if any(kw in line for kw in ["场景", "应用", "业务", "负责", "System"]):
                s = line.strip(" \t-•·*")
                if 5 < len(s) < 80:
                    scenarios.append(s)
            if len(scenarios) >= 3:
                break
        if not scenarios:
            scenarios = ["业务研发", "系统建设"]
        return scenarios

    @staticmethod
    def _estimate_confidence(jd_text: str) -> float:
        n_keywords = sum(
            1
            for kw in ["必须", "要求", "优先", "职责", "Requirements", "Responsibilities"]
            if kw in jd_text
        )
        base = 0.55 + n_keywords * 0.07
        return round(min(base, 0.95), 2)


# ============================================================
# 顶层便捷
# ============================================================
_singleton: Optional[SparkClient] = None


def get_spark_client() -> SparkClient:
    """全局单例"""
    global _singleton
    if _singleton is None:
        _singleton = SparkClient()
    return _singleton


__all__ = [
    "SparkClient",
    "SparkAuthError",
    "SparkAPIError",
    "get_spark_client",
    "HAS_WEBSOCKETS",
]
