"""简历解析Agent - 深度语义解析"""

import hashlib
import logging
from typing import Any, Optional
from pathlib import Path
from .base_agent import BaseKnowledgeAgent
from core.semantic_analyzer import SemanticAnalyzer
from core.credibility_scorer import CredibilityScorer
from core.llm_service import get_llm_service
from models.resume_model import (
    ResumeProfile, EducationRecord, WorkExperience, ProjectExperience,
    SkillWithCredibility, CredibilityLevel
)

logger = logging.getLogger(__name__)


class ResumeParserAgent(BaseKnowledgeAgent):
    """简历解析Agent

    能力：
    1. 多格式文件解析(PDF/DOCX/TXT/Image)
    2. 信息分段与结构化
    3. 显式技能提取
    4. 隐含技能推断（创新点）
    5. 可信度评分
    6. 项目深度分析
    7. 向量化
    """

    agent_name = "resume_parser"
    agent_description = "简历深度解析专家 - 超越关键词匹配的语义级简历理解"

    def __init__(self):
        super().__init__()
        self.semantic = SemanticAnalyzer()
        self.credibility = CredibilityScorer()
        self.llm = get_llm_service()
        self._ocr_engine = None
        self.parse_stats = {"total_parsed": 0, "avg_time_ms": 0}

    def _setup_tools(self):
        pass

    def parse_resume(self, file_path: str) -> ResumeProfile:
        """解析简历主入口"""
        logger.info(f"[ResumeParser] 解析简历: {file_path}")

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"简历文件不存在: {file_path}")

        file_type = path.suffix.lower().replace(".", "")
        file_hash = self._compute_file_hash(file_path)

        # Step 1: 文件解析为文本
        text = self._parse_file(file_path, file_type)
        if not text or len(text.strip()) < 50:
            raise ValueError("文件内容过短或无法解析")

        # Step 2: LLM结构化分段
        sections = self._segment_with_llm(text)

        # Step 3: 提取基本信息
        profile = ResumeProfile(
            file_path=file_path,
            file_type=file_type,
            resume_hash=file_hash,
        )

        # 从 basic_info 段落提取姓名/电话/邮箱
        if "basic_info" in sections:
            basic = self._parse_basic_info(sections["basic_info"])
            profile.name = basic.get("name")
            profile.phone = basic.get("phone")
            profile.email = basic.get("email")

        # 教育背景
        if "education" in sections:
            profile.education = self._parse_education(sections["education"])

        # 工作经历
        if "work_experience" in sections:
            profile.work_experience = self._parse_work_experience(sections["work_experience"])
            profile.total_experience_years = self._calc_total_exp(profile.work_experience)

        # 项目经验
        if "projects" in sections:
            profile.projects = self._parse_projects(sections["projects"])

        # Step 4: 显式技能提取
        explicit_skills = self._extract_explicit_skills(text, sections)
        profile.skills_explicit = explicit_skills

        # Step 5: 隐含技能推断 ⭐核心创新点
        implicit_results = []
        full_text_for_inference = text
        for proj in profile.projects:
            full_text_for_inference += "\n" + proj.description

        implicit_skills = self.semantic.infer_implicit_skills(
            full_text_for_inference, explicit_skills
        )
        profile.skills_implicit = [s["skill"] for s in implicit_skills]

        # Step 6: 可信度评分
        skills_with_context = []
        for skill in explicit_skills:
            skills_with_context.append((skill, self._find_skill_context(text, skill), "skills_section"))

        for iskill in implicit_skills:
            skills_with_context.append((
                iskill["skill"],
                iskill.get("evidence", ""),
                "inferred"
            ))

        profile.skills_with_credibility = self.credibility.assess_batch(skills_with_context)

        # Step 7: 项目深度分析
        analyzed_projects = []
        for proj in profile.projects:
            analysis = self.semantic.evaluate_project_complexity(proj.description, proj.technologies_used)
            red_flags = self.semantic.detect_red_flags(proj.description)

            proj.complexity_score = min(analysis["score"] / 10.0, 1.0)
            proj.tech_depth_scores = {t: min(int(analysis["score"]), 10) for t in proj.technologies_used}
            proj.red_flags = red_flags
            proj.strengths = [f"项目涉及{len(proj.technologies_used)}项技术"] if proj.technologies_used else []
            analyzed_projects.append(proj)
        profile.projects = analyzed_projects

        # Step 8: 向量化
        all_skills_text = ", ".join(profile.skills_explicit + profile.skills_implicit)
        embedding = self.llm.generate_embedding(all_skills_text)
        if embedding:
            profile.embedding_vector = embedding

        # Step 9: 综合评估
        cred_overall = self.credibility.get_overall_credibility(profile.skills_with_credibility)
        profile.overall_technical_level = self._infer_level(cred_overall["overall_score"])
        profile.diversity_score = len(set(profile.skills_explicit + profile.skills_implicit)) / 30  # 归一化
        profile.growth_potential = min(cred_overall["overall_score"] * 1.2, 1.0)

        self.parse_stats["total_parsed"] += 1
        logger.info(f"[ResumeParser] 解析完成: {profile.name or '匿名'}, "
                   f"技能数={len(profile.skills_with_credibility)}, "
                   f"可信度={cred_overall['overall_score']:.2f}")

        return profile

    def _parse_file(self, file_path: str, file_type: str) -> str:
        """解析文件为纯文本"""
        text = ""

        try:
            if file_type == "pdf":
                import fitz  # PyMuPDF
                doc = fitz.open(file_path)
                for page in doc:
                    text += page.get_text()
                doc.close()
                # 图片型PDF（扫描/截图导出）文本层为空，走OCR fallback
                if not text.strip():
                    text = self._ocr_pdf(file_path)
            elif file_type == "docx":
                from docx import Document
                doc = Document(file_path)
                for para in doc.paragraphs:
                    text += para.text + "\n"
            elif file_type in ("txt", "md"):
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            elif file_type in ("png", "jpg", "jpeg"):
                # 图片直接走OCR
                text = self._ocr_image(file_path)
            else:
                # 尝试UTF-8读取
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
        except Exception as e:
            logger.error(f"[ResumeParser] 文件解析失败: {e}")
            raise

        return text.strip()

    def _get_ocr_engine(self):
        """懒加载 RapidOCR 引擎（纯pip安装，含中英文模型，无需额外装软件）"""
        if self._ocr_engine is None:
            from rapidocr_onnxruntime import RapidOCR
            logger.info("[ResumeParser] 初始化 RapidOCR 引擎...")
            self._ocr_engine = RapidOCR()
        return self._ocr_engine

    def _ocr_pdf(self, file_path: str) -> str:
        """对图片型PDF做OCR：每页渲染成高分辨率图片再识别"""
        try:
            import fitz  # PyMuPDF
        except ImportError as e:
            raise ValueError("图片型PDF解析需要 PyMuPDF：pip install pymupdf") from e

        engine = self._get_ocr_engine()
        logger.info("[ResumeParser] 检测到图片型PDF，启动 RapidOCR 识别...")

        text = ""
        doc = fitz.open(file_path)
        for i, page in enumerate(doc):
            # 300 DPI 渲染，简历文字清晰度足够
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")
            result, elapse = engine(img_bytes)
            page_text = "\n".join(r[1] for r in result) if result else ""
            text += page_text + "\n"
            logger.info(f"[ResumeParser] OCR 第{i+1}页完成，文本长度={len(page_text)}，耗时={elapse}")
        doc.close()
        return text

    def _ocr_image(self, file_path: str) -> str:
        """对单张图片做OCR"""
        engine = self._get_ocr_engine()
        result, _ = engine(file_path)
        return "\n".join(r[1] for r in result) if result else ""

    def _segment_with_llm(self, text: str) -> dict:
        """使用LLM对简历文本进行分段"""
        prompt = f"""请将以下简历文本按段落类型进行分类整理。

输出JSON格式:
{{
    "basic_info": "个人信息部分原文",
    "education": "教育背景部分原文",
    "work_experience": "工作经验部分原文",
    "projects": "项目经验部分原文",
    "skills_section": "技能列表部分原文",
    "other": "其他部分原文"
}}

简历原文:
{text[:6000]}"""

        try:
            result = self.llm.structured_extraction(
                text=text,
                extraction_schema={
                    "basic_info": {"type": "string"},
                    "education": {"type": "string"},
                    "work_experience": {"type": "string"},
                    "projects": {"type": "string"},
                    "skills_section": {"type": "string"},
                    "other": {"type": "string"},
                },
                system_prompt="你是一个简历解析专家，能够准确识别简历的各个部分。"
            )
            # 确保返回的值都是字符串类型
            if result and isinstance(result, dict):
                cleaned_result = {}
                for key, value in result.items():
                    if isinstance(value, str):
                        cleaned_result[key] = value
                    elif isinstance(value, dict):
                        cleaned_result[key] = str(value)
                    else:
                        cleaned_result[key] = str(value) if value else ""
                return cleaned_result
            return result if result else {}
        except Exception as e:
            logger.warning(f"[ResumeParser] LLM分段失败，使用简单规则: {e}")
            return self._simple_segment(text)

    def _simple_segment(self, text: str) -> dict:
        """简单的规则分段（Fallback）"""
        sections = {"other": text}
        keywords = {
            "教育": "education", "学历": "education", "大学": "education",
            "工作": "work_experience", "经历": "work_experience", "公司": "work_experience",
            "项目": "projects", "project": "projects",
            "技能": "skills_section", "skill": "skills_section", "擅长": "skills_section",
        }
        # 简化版：直接返回全文让下游处理
        return sections

    def _parse_education(self, text: str) -> list[EducationRecord]:
        """解析教育背景"""
        if not text or not isinstance(text, str):
            return []

        try:
            # 注意：星火 json_object 模式只能返回对象，不能返回数组，
            # 所以 schema 要用对象包裹数组
            result = self.llm.structured_extraction(
                text=text,
                extraction_schema={
                    "education_records": {
                        "type": "array",
                        "description": "教育经历列表",
                        "items": {
                            "type": "object",
                            "properties": {
                                "school": {"type": "string"},
                                "degree": {"type": "string"},
                                "major": {"type": "string"},
                                "graduation_date": {"type": "string"},
                            }
                        }
                    }
                },
                system_prompt="你是教育信息提取专家，从文本中提取教育经历，输出JSON对象。"
            )
            if isinstance(result, dict):
                records = result.get("education_records", [])
                # 兼容 LLM 返回中文 key 或不同英文 key 的情况
                key_map = {"学校": "school", "name": "school",
                           "学位": "degree", "学历": "degree",
                           "专业": "major", "major_name": "major",
                           "毕业时间": "graduation_date", "end_date": "graduation_date",
                           "GPA": "gpa"}
                out = []
                for item in records:
                    if not isinstance(item, dict):
                        continue
                    mapped = {key_map.get(k, k): v for k, v in item.items()}
                    if not mapped.get("school"):
                        continue
                    # gpa 可能是字符串 "3.7/4.0"，取分子转 float
                    if isinstance(mapped.get("gpa"), str):
                        try:
                            mapped["gpa"] = float(mapped["gpa"].split("/")[0])
                        except (ValueError, IndexError):
                            mapped.pop("gpa", None)
                    out.append(EducationRecord(**mapped))
                return out
        except Exception as e:
            logger.warning(f"[ResumeParser] 教育背景解析失败: {e}")
        return []

    def _parse_work_experience(self, text: str) -> list[WorkExperience]:
        """解析工作经历"""
        if not text or not isinstance(text, str):
            return []
        text_content = str(text)[:3000]

        try:
            result = self.llm.structured_extraction(
                text=text,
                extraction_schema={
                    "work_experiences": {
                        "type": "array",
                        "description": "工作经历列表",
                        "items": {
                            "type": "object",
                            "properties": {
                                "company": {"type": "string"},
                                "position": {"type": "string"},
                                "start_date": {"type": "string"},
                                "end_date": {"type": "string"},
                                "description": {"type": "string"},
                            }
                        }
                    }
                },
                system_prompt="你是工作经历提取专家，输出JSON对象。"
            )
            if isinstance(result, dict):
                records = result.get("work_experiences", [])
                # 兼容 LLM 返回中文 key 或不同英文 key
                key_map = {"公司": "company", "company_name": "company", "name": "company",
                           "职位": "position", "岗位": "position", "title": "position", "role": "position",
                           "开始时间": "start_date", "start": "start_date",
                           "结束时间": "end_date", "end": "end_date",
                           "描述": "description", "部门": "department"}
                out = []
                for item in records:
                    if not isinstance(item, dict):
                        continue
                    mapped = {key_map.get(k, k): v for k, v in item.items()}
                    if not mapped.get("company"):
                        continue
                    out.append(WorkExperience(**mapped))
                return out
        except Exception as e:
            logger.warning(f"[ResumeParser] 工作经历解析失败: {e}")
        return []

    def _parse_projects(self, text: str) -> list[ProjectExperience]:
        """解析项目经验"""
        if not text or not isinstance(text, str):
            return []
        text_content = str(text)[:3000]

        try:
            result = self.llm.structured_extraction(
                text=text,
                extraction_schema={
                    "projects": {
                        "type": "array",
                        "description": "项目经验列表",
                        "items": {
                            "type": "object",
                            "properties": {
                                "project_name": {"type": "string"},
                                "role": {"type": "string"},
                                "description": {"type": "string"},
                                "technologies_used": {"type": "array", "items": {"type": "string"}},
                            }
                        }
                    }
                },
                system_prompt="你是项目经验提取专家，注意提取所有提到的技术栈，输出JSON对象。"
            )
            if isinstance(result, dict):
                records = result.get("projects", [])
                # 兼容 LLM 返回中文 key 或不同英文 key
                key_map = {"项目名称": "project_name", "项目名": "project_name", "name": "project_name",
                           "角色": "role", "描述": "description", "详细描述": "description",
                           "技术栈": "technologies_used", "技术列表": "technologies_used",
                           "tech_stack": "technologies_used", "technologies": "technologies_used",
                           "开始时间": "start_date", "结束时间": "end_date"}
                out = []
                for item in records:
                    if not isinstance(item, dict):
                        continue
                    mapped = {key_map.get(k, k): v for k, v in item.items()}
                    if not mapped.get("project_name"):
                        continue
                    out.append(ProjectExperience(**mapped))
                return out
        except Exception as e:
            logger.warning(f"[ResumeParser] 项目经验解析失败: {e}")
        return []

    def _parse_basic_info(self, text: str) -> dict:
        """从 basic_info 段落提取姓名/电话/邮箱"""
        if not text or not isinstance(text, str):
            return {}
        text_content = str(text)[:1000]

        try:
            result = self.llm.structured_extraction(
                text=text,
                extraction_schema={
                    "name": {"type": "string", "description": "姓名"},
                    "phone": {"type": "string", "description": "电话"},
                    "email": {"type": "string", "description": "邮箱"},
                },
                system_prompt="从简历个人信息段落提取姓名、电话、邮箱，输出JSON对象。"
            )
            if isinstance(result, dict):
                # 清洗空值
                return {k: v for k, v in result.items() if v}
        except Exception as e:
            logger.warning(f"[ResumeParser] 基本信息解析失败: {e}")
        return {}

    def _extract_explicit_skills(self, full_text: str, sections: dict) -> list[str]:
        """提取显式技能"""
        skills = set()

        # 从技能段落提取
        skill_text = sections.get("skills_section", "")
        if skill_text and isinstance(skill_text, str):
            from models.skill_taxonomy import get_all_skills
            known = get_all_skills()
            for known_skill in known:
                if known_skill.lower() in skill_text.lower():
                    skills.add(known_skill)

        # 从项目经验中的技术栈提取
        projects_text = sections.get("projects", "")
        if projects_text and isinstance(projects_text, str):
            import re
            tech_pattern = re.compile(r'[A-Z][a-zA-Z+#]*|[A-Z]{2,}')
            found = tech_pattern.findall(projects_text)
            for tech in found:
                if len(tech) >= 2 and tech not in ("URL", "ID", "UI", "API", "OK"):
                    skills.add(tech)

        return list(skills)

    def _find_skill_context(self, text: str, skill: str) -> str:
        """查找技能在文本中的上下文"""
        idx = text.find(skill)
        if idx >= 0:
            start = max(0, idx - 50)
            end = min(len(text), idx + len(skill) + 100)
            return text[start:end]
        return ""

    def _compute_file_hash(self, file_path: str) -> str:
        """计算文件哈希"""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()[:16]

    def _calc_total_exp(self, work_list: list[WorkExperience]) -> float:
        """估算总工作年限"""
        total = 0.0
        for w in work_list:
            if w.start_date:
                try:
                    year = int(''.join(filter(str.isdigit, w.start_date[:4])))
                    total += max(0, 2026 - year)
                except (ValueError, IndexError):
                    total += 2.0  # 默认估计
        return total

    def _infer_level(self, score: float) -> str:
        """根据综合分数推断级别"""
        if score >= 0.85:
            return "expert"
        elif score >= 0.70:
            return "senior"
        elif score >= 0.50:
            return "mid"
        else:
            return "junior"

    def _form_hypothesis(self, task_input: Any, perception: dict) -> dict:
        return {"strategy": "deep_semantic_parsing"}

    def _act(self, hypothesis: Any, task_input: Any, **kwargs) -> Any:
        file_path = kwargs.get("file_path") or (task_input if isinstance(task_input, str) else None)
        if file_path:
            return self.parse_resume(file_path)
        return {"error": "需要提供file_path参数"}
