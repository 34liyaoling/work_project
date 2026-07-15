"""简历解析服务

包含 6 个子模块:
- pdf_extractor: PDF 文本提取（PyMuPDF，多栏布局）
- docx_extractor: Word 文本提取（python-docx）
- field_parser: 字段结构化解析（LLM + 正则双重提取）
- skill_mapper: 技能标准化映射
- vector_builder: 技能向量构建
- test_dataset: 测试集与评估函数
"""
from app.services.resume_parser.pdf_extractor import PDFExtractor, get_pdf_extractor
from app.services.resume_parser.docx_extractor import DocxExtractor, get_docx_extractor
from app.services.resume_parser.field_parser import FieldParser, get_field_parser
from app.services.resume_parser.skill_mapper import SkillMapper, get_skill_mapper
from app.services.resume_parser.vector_builder import VectorBuilder, get_vector_builder
from app.services.resume_parser.test_dataset import (
    build_test_dataset,
    evaluate_field_parser,
    ResumeTestCase,
)


__all__ = [
    "PDFExtractor",
    "DocxExtractor",
    "FieldParser",
    "SkillMapper",
    "VectorBuilder",
    "ResumeTestCase",
    "build_test_dataset",
    "evaluate_field_parser",
    "get_pdf_extractor",
    "get_docx_extractor",
    "get_field_parser",
    "get_skill_mapper",
    "get_vector_builder",
]
