"""LLM 大模型统一接口 - 使用讯飞星火大模型 (Spark/Xinghuo)"""

import json
import logging
import re
from typing import Optional

from openai import OpenAI
from config.settings import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class LLMService:
    """统一LLM接口 - 基于星火大模型 OpenAI 兼容 API"""

    def __init__(self):
        self._client: Optional[OpenAI] = None
        self._init_client()

    def _init_client(self):
        """初始化 LLM 客户端（根据 provider 切换星火/DeepSeek）"""
        api_key = settings.llm.active_api_key
        base_url = settings.llm.active_api_base
        provider = settings.llm.provider

        if not api_key:
            logger.warning(f"[{provider}] API Key 未配置，请在 .env 中设置")
            return

        try:
            self._client = OpenAI(
                api_key=api_key,
                base_url=base_url,
            )
            logger.info(f"LLM 客户端已初始化 [{provider}]: {base_url}, model={settings.llm.active_chat_model}")
        except Exception as e:
            logger.error(f"LLM 客户端初始化失败 [{provider}]: {e}")

    @property
    def model_name(self) -> str:
        """当前使用的模型名（根据 provider）"""
        return settings.llm.active_chat_model

    @property
    def is_ready(self) -> bool:
        """客户端是否就绪"""
        return self._client is not None

    @property
    def provider(self) -> str:
        """当前 provider: spark / deepseek"""
        return settings.llm.provider

    def chat_completion(
        self,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: Optional[dict] = None,
    ) -> str:
        """聊天补全"""
        if not self._client:
            logger.error("星火客户端未初始化，请检查 API Key 配置")
            return ""

        kwargs = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature if temperature is not None else settings.llm.temperature,
            "max_tokens": max_tokens or settings.llm.max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        try:
            response = self._client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"星火 API 调用失败: {e}")
            return ""

    def chat_completion_json(
        self,
        messages: list[dict],
        temperature: float = 0.3,
    ) -> Optional[dict]:
        """聊天补全并返回 JSON 格式结果"""
        raw_response = self.chat_completion(
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"},
        )

        if not raw_response:
            return None

        try:
            return json.loads(raw_response)
        except json.JSONDecodeError:
            json_match = re.search(r'\{[\s\S]*\}', raw_response)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            logger.warning(f"星火返回的不是有效 JSON: {raw_response[:200]}")
            return None

    def structured_extraction(
        self,
        text: str,
        extraction_schema: dict,
        system_prompt: str = "",
    ) -> Optional[dict]:
        """结构化信息抽取"""
        # 把 schema 转成"字段: 描述"列表，避免 LLM 把 schema 当答案原样回填
        field_lines = []
        for key, spec in extraction_schema.items():
            if isinstance(spec, dict):
                desc = spec.get("description", key)
                ftype = spec.get("type", "string")
                field_lines.append(f"- {key}({ftype}): {desc}")
            else:
                field_lines.append(f"- {key}: {spec}")
        fields_text = "\n".join(field_lines)

        # 构造示例，用占位值让 LLM 明确知道要填实际值而非 schema
        example = {k: ("示例值" if (isinstance(v, dict) and v.get("type") == "string") else
                       [] if (isinstance(v, dict) and v.get("type") == "array") else "")
                    for k, v in extraction_schema.items()}

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        user_msg = (
            f"请从以下文本中提取结构化信息。\n\n"
            f"需要提取的字段:\n{fields_text}\n\n"
            f"输出示例(JSON格式，请用从文本中提取的实际值替换):\n"
            f"{json.dumps(example, ensure_ascii=False, indent=2)}\n\n"
            f"待分析文本:\n{text}\n\n"
            f"请严格按照上述 JSON 格式输出，填入实际值，不要添加任何额外解释。"
        )
        messages.append({"role": "user", "content": user_msg})

        return self.chat_completion_json(messages, temperature=0.1)

    def generate_embedding(self, text: str) -> Optional[list[float]]:
        """生成文本向量

        注意：DeepSeek 不提供 embedding 端点，返回 None。
        向量检索功能在无 embedding 时自动降级为关键词检索。
        """
        if not self._client:
            return None

        # DeepSeek 没有 embedding 模型，直接跳过
        if self.provider == "deepseek":
            logger.debug("DeepSeek 不支持 embedding，跳过向量生成")
            return None

        try:
            model = settings.llm.embedding_model
            response = self._client.embeddings.create(
                model=model,
                input=text[:8000],
            )
            return response.data[0].embedding
        except AttributeError:
            logger.warning("API 不支持 embeddings 端点，跳过向量生成")
            return None
        except Exception as e:
            logger.error(f"Embedding 生成失败: {e}")
            return None

    def batch_generate_embeddings(self, texts: list[str]) -> list[Optional[list[float]]]:
        """批量生成向量"""
        results = []
        for text in texts:
            emb = self.generate_embedding(text)
            results.append(emb)
        return results

    def analyze_text(self, text: str, analysis_type: str = "general") -> str:
        """通用文本分析"""
        prompts = {
            "sentiment": "请分析以下文本的情感倾向（正面/负面/中性），并给出置信度。",
            "skills": "请从以下文本中提取所有技术技能，以 JSON 数组形式输出。",
            "complexity": "请评估以下项目的复杂度(1-10分)，并给出理由。",
            "credibility": "请评估以下技能声明的可信度，考虑是否有足够细节支撑。",
            "general": "请对以下文本进行深入分析。",
        }

        system_prompt = prompts.get(analysis_type, prompts["general"])
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ]
        return self.chat_completion(messages, temperature=0.3)

    def test_connection(self) -> tuple[bool, str]:
        """测试星火 API 连接"""
        if not self._client:
            return False, "星火客户端未初始化（请配置 SPARK_API_KEY）"

        try:
            response = self.chat_completion(
                messages=[{"role": "user", "content": "回复 OK 即可"}],
                max_tokens=10,
            )
            if response and len(response.strip()) > 0:
                return True, f"星火大模型连接正常，模型: {self.model_name}"
            return False, "星火 API 无响应"
        except Exception as e:
            return False, f"星火 API 连接失败: {str(e)}"


# 全局单例
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """获取 LLM 服务单例"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
