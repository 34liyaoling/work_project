"""JD 解析测试集与评估函数

构建 100 条 JD 解析测试集，覆盖：
* 不同岗位类别（AI / 后端 / 前端 / 数据 / 产品 / 设计 / 运维 / 测试 / 嵌入式）
* 不同级别（初级 / 中级 / 高级 / 资深）
* 包含典型关键词的 JD 文本
* 期望结构化输出

提供：
* :data:`TEST_CASES` - 内置测试用例（100 条）
* :func:`build_test_dataset` - 动态扩展到 100 条
* :func:`evaluate_parser` - 评估函数，返回 准确率 / 字段级指标 / 错误样例
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

from app.core.logger import log
from app.services.llm.jd_parser import JDParser, ParsedJD


# ============================================================
# 测试用例模板
# ============================================================
@dataclass
class JDEvalCase:
    """单条评估用例"""

    jd_text: str
    expected_category: str
    expected_level: str
    expected_skills: List[str] = field(default_factory=list)  # 期望出现的主要技能
    case_id: str = ""
    description: str = ""


# 内置 10 条样例 + 模板（用于自动扩展到 100 条）
_SAMPLE_CASES: List[JDEvalCase] = [
    JDEvalCase(
        jd_text=(
            "# AI应用工程师 - 字节跳动\n\n"
            "## 岗位职责：\n"
            "1. 负责 LLM 应用研发，基于 LangChain / RAG 搭建智能问答系统\n"
            "2. 设计 Prompt 模板与 Agent 框架\n"
            "3. 与算法团队协作优化模型效果\n\n"
            "## 任职要求：\n"
            "1. 本科及以上，3年以上工作经验\n"
            "2. 精通 Python、PyTorch，必须熟悉 LangChain / RAG\n"
            "3. 熟悉 Milvus / Faiss 等向量数据库\n"
            "4. 有大语言模型微调经验者优先\n"
        ),
        expected_category="AI工程师",
        expected_level="高级",
        expected_skills=["Python", "PyTorch", "LangChain", "RAG"],
        case_id="ai_01",
        description="高级 AI 应用工程师",
    ),
    JDEvalCase(
        jd_text=(
            "# Python后端开发 - 阿里巴巴\n\n"
            "## 岗位职责：\n"
            "1. 负责电商核心系统后端开发\n"
            "2. 参与系统架构设计与性能优化\n\n"
            "## 任职要求：\n"
            "1. 5年以上 Python 开发经验\n"
            "2. 精通 Django / FastAPI、MySQL、Redis\n"
            "3. 熟悉 Kafka、Elasticsearch\n"
        ),
        expected_category="后端开发",
        expected_level="资深",
        expected_skills=["Python", "Django", "FastAPI", "MySQL", "Redis"],
        case_id="be_01",
        description="资深 Python 后端",
    ),
    JDEvalCase(
        jd_text=(
            "# 前端开发工程师 - 腾讯\n\n"
            "## 岗位职责：\n"
            "1. 负责微信小程序 / H5 前端开发\n"
            "2. 与产品 / 设计协作完成页面实现\n\n"
            "## 任职要求：\n"
            "1. 本科及以上，2年以上 React / Vue 开发经验\n"
            "2. 精通 JavaScript / TypeScript\n"
            "3. 熟悉 Webpack / Vite\n"
        ),
        expected_category="前端开发",
        expected_level="中级",
        expected_skills=["React", "Vue", "JavaScript", "TypeScript"],
        case_id="fe_01",
        description="中级前端开发",
    ),
    JDEvalCase(
        jd_text=(
            "# 数据分析师 - 美团\n\n"
            "## 岗位职责：\n"
            "1. 业务数据分析与报表\n"
            "2. 撰写分析报告\n\n"
            "## 任职要求：\n"
            "1. 熟练 SQL、Python\n"
            "2. 熟悉 Tableau / Power BI\n"
            "3. 有 A/B 测试经验优先\n"
        ),
        expected_category="数据分析",
        expected_level="中级",
        expected_skills=["SQL", "Python", "Tableau"],
        case_id="da_01",
        description="中级数据分析师",
    ),
    JDEvalCase(
        jd_text=(
            "# 机器学习工程师 - 商汤\n\n"
            "## 岗位职责：\n"
            "1. 计算机视觉算法研发\n"
            "2. 模型训练与部署\n\n"
            "## 任职要求：\n"
            "1. 硕士及以上，3年以上\n"
            "2. 精通 PyTorch / TensorFlow\n"
            "3. 熟悉 OpenCV / NumPy\n"
        ),
        expected_category="AI工程师",
        expected_level="高级",
        expected_skills=["PyTorch", "TensorFlow", "OpenCV"],
        case_id="ml_01",
        description="高级 ML 工程师",
    ),
    JDEvalCase(
        jd_text=(
            "# 初级后端开发 - 某创业公司\n\n"
            "## 岗位职责：\n"
            "1. 配合高级工程师完成开发\n"
            "2. 编写单元测试\n\n"
            "## 任职要求：\n"
            "1. 应届或 1 年以下经验\n"
            "2. 了解 Java / Spring Boot\n"
            "3. 学习能力强\n"
        ),
        expected_category="后端开发",
        expected_level="初级",
        expected_skills=["Java", "Spring Boot"],
        case_id="be_junior",
        description="初级 Java 后端",
    ),
    JDEvalCase(
        jd_text=(
            "# DevOps 工程师 - 京东\n\n"
            "## 岗位职责：\n"
            "1. CI/CD 流水线建设\n"
            "2. Kubernetes 集群运维\n\n"
            "## 任职要求：\n"
            "1. 4年以上 SRE / DevOps 经验\n"
            "2. 精通 Docker / Kubernetes / Helm\n"
            "3. 熟悉 Prometheus / Grafana\n"
        ),
        expected_category="DevOps",
        expected_level="高级",
        expected_skills=["Docker", "Kubernetes", "Helm", "Prometheus"],
        case_id="devops_01",
        description="高级 DevOps",
    ),
    JDEvalCase(
        jd_text=(
            "# 产品经理 - 小红书\n\n"
            "## 岗位职责：\n"
            "1. 负责社区增长方向产品规划\n"
            "2. 撰写 PRD\n\n"
            "## 任职要求：\n"
            "1. 3年以上产品经验\n"
            "2. 熟悉 SQL / 数据分析\n"
            "3. 优秀沟通能力\n"
        ),
        expected_category="产品经理",
        expected_level="高级",
        expected_skills=["SQL"],
        case_id="pm_01",
        description="高级产品经理",
    ),
    JDEvalCase(
        jd_text=(
            "# UI 设计师 - 蚂蚁集团\n\n"
            "## 岗位职责：\n"
            "1. 负责金融产品 UI 设计\n"
            "2. 与产品协作完成视觉规范\n\n"
            "## 任职要求：\n"
            "1. 2年以上 UI 经验\n"
            "2. 精通 Figma / Sketch\n"
            "3. 有金融 / 工具类产品经验优先\n"
        ),
        expected_category="设计师",
        expected_level="中级",
        expected_skills=["Figma", "Sketch"],
        case_id="design_01",
        description="中级 UI 设计师",
    ),
    JDEvalCase(
        jd_text=(
            "# 测试开发工程师 - 网易\n\n"
            "## 岗位职责：\n"
            "1. 自动化测试框架开发\n"
            "2. 接口 / UI 自动化\n\n"
            "## 任职要求：\n"
            "1. 3年以上测试开发\n"
            "2. 熟悉 Selenium / Pytest\n"
            "3. 了解 CI/CD\n"
        ),
        expected_category="测试开发",
        expected_level="高级",
        expected_skills=["Selenium", "Pytest"],
        case_id="qa_01",
        description="高级测试开发",
    ),
]


# 动态扩展模板（用于凑到 100 条）
_EXTENSION_TEMPLATES: List[Dict[str, Any]] = [
    {
        "category": "AI工程师",
        "level": "高级",
        "skills": ["Python", "PyTorch", "LangChain", "RAG", "Milvus"],
        "title": "AI 算法工程师",
    },
    {
        "category": "后端开发",
        "level": "中级",
        "skills": ["Java", "Spring Boot", "MySQL", "Redis"],
        "title": "Java 后端工程师",
    },
    {
        "category": "前端开发",
        "level": "初级",
        "skills": ["Vue", "JavaScript", "CSS3"],
        "title": "初级前端工程师",
    },
    {
        "category": "数据科学",
        "level": "高级",
        "skills": ["Python", "SQL", "机器学习", "XGBoost"],
        "title": "高级数据科学家",
    },
    {
        "category": "运维",
        "level": "中级",
        "skills": ["Linux", "Nginx", "Shell", "Ansible"],
        "title": "运维工程师",
    },
    {
        "category": "嵌入式",
        "level": "中级",
        "skills": ["C", "C++", "RTOS", "STM32"],
        "title": "嵌入式工程师",
    },
    {
        "category": "产品经理",
        "level": "初级",
        "skills": ["Axure", "用户调研", "需求分析"],
        "title": "初级产品经理",
    },
    {
        "category": "运营",
        "level": "中级",
        "skills": ["内容运营", "用户增长", "数据分析"],
        "title": "运营专员",
    },
    {
        "category": "芯片",
        "level": "高级",
        "skills": ["Verilog", "数字电路", "ASIC"],
        "title": "芯片设计工程师",
    },
    {
        "category": "数据工程",
        "level": "高级",
        "skills": ["Spark", "Flink", "Kafka", "Airflow"],
        "title": "高级数据工程师",
    },
]


def _compose_jd_text(tpl: Dict[str, Any], idx: int) -> str:
    """根据模板合成 JD 文本"""
    skills_str = "、".join(tpl["skills"])
    years_map = {"初级": "1年以内", "中级": "3", "高级": "5", "资深": "8"}
    years = years_map.get(tpl["level"], "3")
    return (
        f"# {tpl['title']} - 公司{idx}\n\n"
        "## 岗位职责：\n"
        f"1. 负责{tpl['title']}相关核心模块的设计与开发\n"
        "2. 参与系统架构设计与技术选型\n"
        "3. 持续优化系统性能\n\n"
        "## 任职要求：\n"
        f"1. {years}年以上相关经验\n"
        f"2. 熟练掌握：{skills_str}\n"
        "3. 良好的沟通能力与团队协作精神\n\n"
        "## 加分项：\n"
        "- 有大型分布式系统经验者优先\n"
    )


def build_test_dataset(n: int = 100, seed: int = 42) -> List[JDEvalCase]:
    """构建 n 条测试集（默认 100）"""
    random.seed(seed)
    cases: List[JDEvalCase] = list(_SAMPLE_CASES)
    i = 0
    while len(cases) < n:
        tpl = random.choice(_EXTENSION_TEMPLATES)
        i += 1
        text = _compose_jd_text(tpl, i)
        cases.append(JDEvalCase(
            jd_text=text,
            expected_category=tpl["category"],
            expected_level=tpl["level"],
            expected_skills=list(tpl["skills"]),
            case_id=f"gen_{i:03d}",
            description=f"{tpl['category']} / {tpl['level']}",
        ))
    return cases[:n]


# 模块级 100 条测试集（懒构建）
TEST_CASES: List[JDEvalCase] = build_test_dataset(100)


# ============================================================
# 评估函数
# ============================================================
@dataclass
class EvalReport:
    """评估报告"""

    total: int
    parsed_ok: int
    parse_accuracy: float
    category_accuracy: float
    level_accuracy: float
    skill_precision: float
    skill_recall: float
    skill_f1: float
    avg_confidence: float
    errors: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "parsed_ok": self.parsed_ok,
            "parse_accuracy": round(self.parse_accuracy, 4),
            "category_accuracy": round(self.category_accuracy, 4),
            "level_accuracy": round(self.level_accuracy, 4),
            "skill_precision": round(self.skill_precision, 4),
            "skill_recall": round(self.skill_recall, 4),
            "skill_f1": round(self.skill_f1, 4),
            "avg_confidence": round(self.avg_confidence, 4),
            "errors": self.errors[:20],  # 只保留前 20 个
        }


def _safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def _evaluate_one(predicted: ParsedJD, case: JDEvalCase) -> Dict[str, float]:
    """单条评估"""
    pred_skills = set(s.lower() for s in predicted.skill_names())
    exp_skills = set(s.lower() for s in case.expected_skills)
    if not pred_skills and not exp_skills:
        skill_tp = skill_fp = skill_fn = 0
    else:
        skill_tp = len(pred_skills & exp_skills)
        skill_fp = len(pred_skills - exp_skills)
        skill_fn = len(exp_skills - pred_skills)
    precision = _safe_div(skill_tp, skill_tp + skill_fp)
    recall = _safe_div(skill_tp, skill_tp + skill_fn)
    return {
        "parsed_ok": 1.0 if predicted.job_title and predicted.confidence >= 0 else 0.0,
        "category_ok": 1.0 if predicted.category == case.expected_category else 0.0,
        "level_ok": 1.0 if predicted.level == case.expected_level else 0.0,
        "skill_tp": float(skill_tp),
        "skill_fp": float(skill_fp),
        "skill_fn": float(skill_fn),
        "precision": precision,
        "recall": recall,
        "confidence": float(predicted.confidence or 0.0),
    }


def evaluate_parser(
    parser: JDParser,
    cases: Optional[List[JDEvalCase]] = None,
    sample_size: Optional[int] = None,
) -> EvalReport:
    """评估 :class:`JDParser` 在测试集上的表现

    Args:
        parser: JD 解析器实例
        cases: 测试用例（默认 :data:`TEST_CASES`）
        sample_size: 采样数量（用于快速测试）

    Notes:
        本函数为同步入口；批量异步解析请使用 :func:`evaluate_parser_async`。
    """
    import asyncio
    return asyncio.run(evaluate_parser_async(parser, cases, sample_size))


async def evaluate_parser_async(
    parser: JDParser,
    cases: Optional[List[JDEvalCase]] = None,
    sample_size: Optional[int] = None,
) -> EvalReport:
    """评估 :class:`JDParser` 在测试集上的表现（异步）"""
    cases = list(cases or TEST_CASES)
    if sample_size is not None and sample_size < len(cases):
        random.seed(123)
        cases = random.sample(cases, sample_size)
    log.info(f"开始评估 JD Parser，样本数={len(cases)}")

    # 串行解析（避免 LLM 限频）；如需并发可改为 asyncio.gather
    parsed_results: List[ParsedJD] = []
    for c in cases:
        try:
            p = await parser.parse(c.jd_text)
        except Exception as e:  # noqa: BLE001
            log.error(f"解析 case={c.case_id} 失败: {e}")
            p = ParsedJD(job_title="", category="其它", level="中级", confidence=0.0)
        parsed_results.append(p)

    # 累计指标
    n = len(cases)
    parsed_ok = 0
    cat_ok = 0
    lvl_ok = 0
    total_tp = total_fp = total_fn = 0
    total_conf = 0.0
    errors: List[Dict[str, Any]] = []

    for case, pred in zip(cases, parsed_results):
        m = _evaluate_one(pred, case)
        parsed_ok += int(m["parsed_ok"])
        cat_ok += int(m["category_ok"])
        lvl_ok += int(m["level_ok"])
        total_tp += m["skill_tp"]
        total_fp += m["skill_fp"]
        total_fn += m["skill_fn"]
        total_conf += m["confidence"]
        if m["category_ok"] == 0 or m["level_ok"] == 0:
            errors.append({
                "case_id": case.case_id,
                "expected_category": case.expected_category,
                "predicted_category": pred.category,
                "expected_level": case.expected_level,
                "predicted_level": pred.level,
                "expected_skills": case.expected_skills,
                "predicted_skills": pred.skill_names(),
            })

    precision = _safe_div(total_tp, total_tp + total_fp)
    recall = _safe_div(total_tp, total_tp + total_fn)
    f1 = _safe_div(2 * precision * recall, precision + recall)

    report = EvalReport(
        total=n,
        parsed_ok=parsed_ok,
        parse_accuracy=_safe_div(parsed_ok, n),
        category_accuracy=_safe_div(cat_ok, n),
        level_accuracy=_safe_div(lvl_ok, n),
        skill_precision=precision,
        skill_recall=recall,
        skill_f1=f1,
        avg_confidence=_safe_div(total_conf, n),
        errors=errors,
    )
    log.info(f"评估完成：{report.to_dict()}")
    return report


__all__ = [
    "JDEvalCase",
    "TEST_CASES",
    "build_test_dataset",
    "evaluate_parser",
    "evaluate_parser_async",
    "EvalReport",
]
