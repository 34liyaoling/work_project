"""分析工具集 - 各种分析能力"""

import json
import logging
from typing import Optional
from langchain_core.tools import BaseTool
from core.llm_service import get_llm_service
from core.semantic_analyzer import SemanticAnalyzer
from core.credibility_scorer import CredibilityScorer

logger = logging.getLogger(__name__)


class TextAnalysisTool(BaseTool):
    """文本深度分析工具"""
    name: str = "text_analysis"
    description: str = "对文本进行深度分析，包括技能推断、复杂度评估、Red Flag检测"

    def _run(self, text: str, analysis_type: str = "full") -> str:
        analyzer = SemanticAnalyzer()

        if analysis_type == "full":
            result = analyzer.analyze_text_semantics(text)
        elif analysis_type == "implicit_skills":
            skills = analyzer.infer_implicit_skills(text)
            result = {"implicit_skills": skills}
        elif analysis_type == "complexity":
            result = analyzer.evaluate_project_complexity(text)
        elif analysis_type == "red_flags":
            result = {"red_flags": analyzer.detect_red_flags(text)}
        else:
            result = analyzer.analyze_text_semantics(text)

        return json.dumps(result, ensure_ascii=False, default=str)


class CredibilityAnalysisTool(BaseTool):
    """可信度分析工具"""
    name: str = "credibility_analysis"
    description: str = "评估技能声明的可信度"

    def _run(self, skill_name: str, context: str = "", location: str = "skills_section") -> str:
        scorer = CredibilityScorer()
        result = scorer.assess_skill(skill_name, context, location)
        return json.dumps({
            "skill": result.skill_name,
            "level": result.credibility_level.value,
            "score": result.credibility_score,
            "proficiency": result.proficiency_level,
        }, ensure_ascii=False)


class LLMSimpleQueryTool(BaseTool):
    """LLM简单查询工具"""
    name: str = "llm_query"
    description: str = "使用大模型回答问题或分析文本"

    def _run(self, question: str, context: str = "", temperature: float = 0.5) -> str:
        llm = get_llm_service()

        messages = [{"role": "system", "content": "你是新一代信息技术领域的专家顾问。"}]
        if context:
            messages.append({"role": "system", "content": f"参考上下文:\n{context}"})
        messages.append({"role": "user", "content": question})

        response = llm.chat_completion(messages, temperature=temperature)
        return response
