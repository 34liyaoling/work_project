"""简历测试集与评估函数

提供 ResumeTestCase 数据结构、build_test_dataset 构造多类型样本、
evaluate_field_parser 计算字段抽取的精确率/召回率。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from app.core.logger import log


@dataclass
class ResumeTestCase:
    """单个简历测试用例"""
    case_id: str
    text: str
    file_type: str = "txt"  # txt/pdf/docx
    language: str = "zh"  # zh / en
    layout: str = "single"  # single / multi-column
    expected: Dict[str, Any] = field(default_factory=dict)
    # expected 字段: name, email, phone, skills:["Python",...]


def build_test_dataset() -> List[ResumeTestCase]:
    """构造一组覆盖 PDF/Word/中文/英文/多栏布局的测试样本（纯文本模拟）"""
    cases: List[ResumeTestCase] = []

    # 1. 中文单栏
    cases.append(ResumeTestCase(
        case_id="zh_single_1",
        text=(
            "姓名: 张三\n"
            "Email: zhangsan@example.com\n"
            "电话: 13800138000\n"
            "教育经历: 2015-2019 北京大学 计算机科学 本科\n"
            "工作经历: 2019-2023 字节跳动 后端工程师\n"
            "技能: Python, Django, MySQL, Redis, Docker, Kubernetes"
        ),
        file_type="txt", language="zh", layout="single",
        expected={
            "name": "张三", "email": "zhangsan@example.com", "phone": "13800138000",
            "skills": ["Python", "Django", "MySQL", "Redis", "Docker", "Kubernetes"],
        },
    ))

    # 2. 英文 PDF 模拟
    cases.append(ResumeTestCase(
        case_id="en_single_1",
        text=(
            "Name: John Smith\n"
            "Email: john.smith@gmail.com\n"
            "Phone: +1-415-555-0100\n"
            "Education: 2014-2018 MIT, B.S. in Computer Science\n"
            "Skills: Python, PyTorch, TensorFlow, AWS, Docker, Kubernetes"
        ),
        file_type="pdf", language="en", layout="single",
        expected={
            "name": "John Smith", "email": "john.smith@gmail.com", "phone": "+1-415-555-0100",
            "skills": ["Python", "PyTorch", "TensorFlow", "AWS", "Docker", "Kubernetes"],
        },
    ))

    # 3. 中文双栏（用换行+特殊分隔模拟）
    cases.append(ResumeTestCase(
        case_id="zh_multi_1",
        text=(
            "个人信息    | 项目经历\n"
            "姓名: 李四    | 智能客服系统 (2022)\n"
            "Email: lisi@qq.com | 负责 RAG 检索模块开发\n"
            "电话: 13900139000 | 技能: LangChain, LLM, Elasticsearch"
        ),
        file_type="docx", language="zh", layout="multi-column",
        expected={
            "name": "李四", "email": "lisi@qq.com", "phone": "13900139000",
            "skills": ["LangChain", "LLM", "Elasticsearch"],
        },
    ))

    # 4. 中文 极简
    cases.append(ResumeTestCase(
        case_id="zh_minimal_1",
        text=(
            "王五\nwangwu@163.com\n18600000000\n"
            "Java, Spring, MySQL, Kafka"
        ),
        file_type="txt", language="zh", layout="single",
        expected={
            "name": "王五", "email": "wangwu@163.com", "phone": "18600000000",
            "skills": ["Java", "Spring", "MySQL", "Kafka"],
        },
    ))

    log.info(f"测试集已构建: {len(cases)} 个用例")
    return cases


def evaluate_field_parser(
    parser_output: List[Dict[str, Any]],
    test_cases: List[ResumeTestCase],
) -> Dict[str, float]:
    """评估字段解析的精确率 / 召回率

    parser_output: 每个 case 对应一个 dict（来自 FieldParser.parse 输出）
    :return: {"name_precision":..., "skill_precision":..., "name_recall":..., "macro_f1":...}
    """
    if not test_cases or not parser_output:
        return {"macro_f1": 0.0}
    n = min(len(parser_output), len(test_cases))

    # 字段级 TP/FP/FN
    field_metrics: Dict[str, Dict[str, int]] = {}
    for i in range(n):
        pred = parser_output[i] or {}
        exp = test_cases[i].expected or {}
        for field_name, exp_val in exp.items():
            m = field_metrics.setdefault(field_name, {"tp": 0, "fp": 0, "fn": 0})
            pred_val = pred.get(field_name)
            if isinstance(exp_val, list):
                pred_set = set(_normalize(s) for s in (pred_val or []))
                exp_set = set(_normalize(s) for s in exp_val)
                tp = len(pred_set & exp_set)
                fp = len(pred_set - exp_set)
                fn = len(exp_set - pred_set)
                m["tp"] += tp; m["fp"] += fp; m["fn"] += fn
            else:
                if _normalize(pred_val) == _normalize(exp_val):
                    m["tp"] += 1
                else:
                    m["fn"] += 1
                    if pred_val:
                        m["fp"] += 1

    field_f1: List[float] = []
    for fname, m in field_metrics.items():
        precision = m["tp"] / max(1, m["tp"] + m["fp"])
        recall = m["tp"] / max(1, m["tp"] + m["fn"])
        f1 = 2 * precision * recall / max(1e-6, precision + recall)
        field_f1.append(f1)
    macro_f1 = sum(field_f1) / max(1, len(field_f1))
    log.info(f"简历解析评估 macro_f1={macro_f1:.3f}")
    return {
        "macro_f1": round(macro_f1, 3),
        "fields": {
            fname: {
                "tp": m["tp"], "fp": m["fp"], "fn": m["fn"],
            }
            for fname, m in field_metrics.items()
        },
    }


def _normalize(val: Any) -> str:
    return str(val or "").strip().lower()
