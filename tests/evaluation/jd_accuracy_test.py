"""JD解析准确率评测

评测方法:
    1. 定义10条标准JD测试用例（含正确的结构化字段）
    2. 对每条JD调用LLM解析或内置规则解析
    3. 比较解析结果与标准答案的字段匹配率
    4. 计算总体准确率
    5. 输出详细报告（每条JD的每个字段是否匹配）
"""

import json
import logging
import os
import sys
import re
import traceback

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tests.evaluation.test_data import JD_TEST_CASES


def parse_jd_builtin(text: str) -> dict:
    """内置规则式JD解析（不依赖LLM的外部API）

    适用于无API Key环境下的评测，模拟LLM解析的输出格式。
    """
    result = {
        "job_title": "",
        "company_name": "",
        "salary_min": None,
        "salary_max": None,
        "location": "",
        "experience_min": None,
        "experience_max": None,
        "education": "",
        "required_skills": [],
        "optional_skills": [],
        "industry": "",
        "job_description": "",
    }

    lines = text.strip().split("\n")
    current_section = ""
    full_text = text

    for line in lines:
        line_stripped = line.strip()

        if line_stripped.startswith("【职位名称】"):
            result["job_title"] = line_stripped.replace("【职位名称】", "").strip()
        elif line_stripped.startswith("【公司名称】"):
            result["company_name"] = line_stripped.replace("【公司名称】", "").strip()
        elif line_stripped.startswith("【薪资范围】"):
            salary_text = line_stripped.replace("【薪资范围】", "").strip()
            numbers = re.findall(r"(\d+)K", salary_text)
            if len(numbers) >= 2:
                result["salary_min"] = int(numbers[0])
                result["salary_max"] = int(numbers[1])
        elif line_stripped.startswith("【工作地点】"):
            location_text = line_stripped.replace("【工作地点】", "").strip()
            for city in ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "南京", "东莞", "苏州"]:
                if city in location_text:
                    result["location"] = city
                    break
        elif line_stripped.startswith("【岗位职责】"):
            current_section = "responsibility"
        elif line_stripped.startswith("【任职要求】"):
            current_section = "requirement"
        elif line_stripped.startswith("【加分项】"):
            current_section = "plus"
        elif line_stripped.startswith("【"):
            current_section = ""

    exp_match = re.search(r"(\d+)-(\d+)年", full_text)
    if exp_match:
        result["experience_min"] = int(exp_match.group(1))
        result["experience_max"] = int(exp_match.group(2))

    exp_match_single = re.search(r"(\d+)年以上", full_text)
    if exp_match_single and result["experience_min"] is None:
        result["experience_min"] = int(exp_match_single.group(1))
        result["experience_max"] = int(exp_match_single.group(1))

    edu_keywords = {"本科": "本科", "硕士": "硕士", "博士": "博士", "专科": "专科"}
    for keyword, value in edu_keywords.items():
        if keyword in full_text:
            result["education"] = value
            break

    all_skills = _extract_skills_from_text(full_text)

    content_after_requirement = _get_section_text(full_text, "【任职要求】", "【加分项】")
    plus_section = _get_section_text(full_text, "【加分项】", None)

    required_skills = _extract_skills_from_text(content_after_requirement)
    plus_skills = _extract_skills_from_text(plus_section)

    all_mentioned = set()
    for skill in required_skills:
        all_mentioned.add(skill)
    for skill in plus_skills:
        all_mentioned.add(skill)

    if result["job_title"]:
        job_title_lower = result["job_title"].lower()
        if "python" in job_title_lower or "后端" in job_title_lower:
            all_mentioned.update(["Python", "后端开发"])
        elif "前端" in job_title_lower or "react" in job_title_lower:
            all_mentioned.update(["JavaScript", "前端开发"])
        elif "算法" in job_title_lower or "推荐" in job_title_lower:
            all_mentioned.update(["算法", "机器学习"])

    known_required = set(all_skills) & set(required_skills) if required_skills else set(all_skills)
    known_plus = set(all_skills) & set(plus_skills) if plus_skills else set()

    industry_keywords = {
        "互联网": ["互联网", "科技", "技术", "软件"],
        "电商": ["电商", "零售", "商品", "订单"],
        "金融": ["金融", "支付", "银行", "保险"],
        "企业服务": ["企业服务", "SaaS", "ERP", "CRM", "B端", "用友"],
        "通信/IT": ["通信", "华为", "中兴", "5G"],
    }
    for industry, keywords in industry_keywords.items():
        if any(kw in full_text for kw in keywords):
            result["industry"] = industry
            break

    desc_match = re.search(r"【岗位职责】\s*(.*?)(?=【任职要求】|【加分项】|$)", full_text, re.DOTALL)
    if desc_match:
        result["job_description"] = desc_match.group(1).strip().replace("\n", "，")

    result["required_skills"] = sorted(list(known_required)) if known_required else sorted(list(all_mentioned))
    result["optional_skills"] = sorted(list(known_plus)) if known_plus else []

    return result


def _get_section_text(text: str, start_marker: str, end_marker: str | None) -> str:
    """提取标记之间的文本"""
    start_idx = text.find(start_marker)
    if start_idx == -1:
        return ""
    start_idx += len(start_marker)

    if end_marker:
        end_idx = text.find(end_marker, start_idx)
        if end_idx == -1:
            return text[start_idx:].strip()
        return text[start_idx:end_idx].strip()
    return text[start_idx:].strip()


def _extract_skills_from_text(text: str) -> list[str]:
    """从文本中提取技能关键词"""
    common_skills = [
        "Python", "Java", "Go", "C\\+\\+", "JavaScript", "TypeScript", "Rust", "Scala",
        "React", "Vue", "Angular", "Node\\.js", "Spring Boot", "Spring Cloud", "Spring",
        "Django", "Flask", "FastAPI", "Express",
        "MySQL", "Redis", "Elasticsearch", "MongoDB", "PostgreSQL",
        "Docker", "Kubernetes", "K8s", "Prometheus", "Grafana", "Jenkins",
        "TensorFlow", "PyTorch", "Scikit-learn", "Pandas", "NumPy",
        "Kafka", "Flink", "Spark", "Hadoop", "Flink",
        "Terraform", "Ansible", "GitLab CI", "Git",
        "Selenium", "Appium", "Cypress", "JMeter", "Locust",
        "Burp Suite", "Nmap",
        "Tableau", "FineBI", "QuickBI",
        "RocketMQ", "ZooKeeper", "Netty", "Dubbo", "gRPC",
        "Istio", "Helm", "Argo", "Chaos Mesh",
        "HTML5", "CSS3", "Webpack", "Vite", "Redux", "Socket\\.io",
        "Airflow", "SPSS", "XGBoost",
        "Shell", "Linux", "AWS",
        "微服务", "高并发", "分布式", "消息队列", "数据分析",
        "机器学习", "深度学习", "推荐系统", "协同过滤",
        "AIGC", "大模型", "LLM",
        "产品设计", "用户研究", "PRD", "B端产品", "SaaS",
        "前端工程化", "自动化测试", "性能测试", "接口测试",
        "渗透测试", "Web安全", "移动安全", "云安全", "代码审计", "SDL",
        "CI/CD", "SRE", "ELK",
        "OWASP Top10", "CISSP", "零信任",
        "WebAssembly", "Flutter", "React Native",
        "数据仓库", "数据建模", "用户增长",
        "假设检验", "回归分析", "聚类分析", "数据可视化",
        "系统设计", "架构设计", "分布式系统",
        "安全测试", "AI测试", "AI产品",
        "低代码", "零代码", "图神经网络", "GNN",
        "多模态推荐", "Kotlin", "R",
    ]

    found = []
    for skill_pattern in common_skills:
        pattern = skill_pattern.replace("\\+", "+").replace("\\.", ".").replace("\\ ", " ")
        if pattern.lower() in text.lower():
            found.append(pattern)
    return found


def load_llm_parser():
    """尝试加载LLM解析器，失败则返回None"""
    try:
        from core.llm_service import get_llm_service
        llm = get_llm_service()
        if llm.is_ready:
            return llm
    except Exception as e:
        logger.warning(f"LLM服务加载失败: {e}")
    return None


def parse_with_llm(llm, text: str) -> dict:
    """使用LLM解析JD"""
    schema = {
        "job_title": "岗位名称",
        "company_name": "公司名称",
        "salary_min": "最低薪资(K/月)",
        "salary_max": "最高薪资(K/月)",
        "location": "工作地点(城市名)",
        "experience_min": "最低经验要求(年)",
        "experience_max": "最高经验要求(年)",
        "education": "学历要求",
        "required_skills": ["必备技能列表"],
        "optional_skills": ["加分技能列表"],
        "industry": "所属行业",
        "job_description": "岗位职责描述",
    }
    system_prompt = "你是一个专业JD解析器。从招聘信息中提取结构化信息，输出严格JSON。"
    try:
        result = llm.structured_extraction(text, schema, system_prompt)
        if result:
            return _normalize_jd_result(result)
    except Exception as e:
        logger.warning(f"LLM解析JD失败: {e}")
    return {}


def _normalize_jd_result(result: dict) -> dict:
    """归一化LLM输出为标准格式"""
    normalized = {
        "job_title": result.get("job_title") or "",
        "company_name": result.get("company_name") or "",
        "salary_min": result.get("salary_min"),
        "salary_max": result.get("salary_max"),
        "location": result.get("location") or "",
        "experience_min": result.get("experience_min"),
        "experience_max": result.get("experience_max"),
        "education": result.get("education") or "",
        "required_skills": [s.strip() for s in (result.get("required_skills") or []) if s],
        "optional_skills": [s.strip() for s in (result.get("optional_skills") or []) if s],
        "industry": result.get("industry") or "",
        "job_description": result.get("job_description") or "",
    }
    return normalized


def compare_field(actual, expected, field: str) -> tuple[bool, str]:
    """比较单个字段，返回(是否匹配, 详情)"""
    if field in ("required_skills", "optional_skills"):
        actual_set = set(s.lower().replace(" ", "") for s in (actual or []))
        expected_set = set(s.lower().replace(" ", "") for s in (expected or []))
        if len(expected_set) == 0:
            return True, "无期望值（跳过）"
        intersection = actual_set & expected_set
        matched = len(intersection) >= len(expected_set) * 0.6
        if matched:
            missed = expected_set - intersection
            extra = actual_set - expected_set
            detail = f"匹配{len(intersection)}/{len(expected_set)}"
            if missed:
                detail += f", 遗漏: {missed}"
            return True, detail
        else:
            missed = expected_set - intersection
            return False, f"仅匹配{len(intersection)}/{len(expected_set)}, 遗漏: {missed}"

    if field == "job_description":
        if not actual or not expected:
            return (actual == expected), f"actual={repr(actual[:50])}, expected={repr(expected[:50])}"
        actual_short = actual.replace("，", "").replace(",", "").replace(" ", "")[:80]
        expected_short = expected.replace("，", "").replace(",", "").replace(" ", "")[:80]
        match = actual_short == expected_short or actual_short in expected_short or expected_short in actual_short
        return match, f"描述匹配: {match}"

    if actual is None and expected is None:
        return True, "均无"
    if actual is None or expected is None:
        return False, f"actual={actual}, expected={expected}"

    if isinstance(actual, str) and isinstance(expected, str):
        match = actual.strip().lower() == expected.strip().lower()
        return match, f"'{actual}' vs '{expected}'"

    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        match = actual == expected
        return match, f"{actual} vs {expected}"

    match = str(actual).strip().lower() == str(expected).strip().lower()
    return match, f"{actual} vs {expected}"


def evaluate_jd_accuracy(use_llm: bool = False) -> dict:
    """运行JD解析准确率评测

    Args:
        use_llm: 是否使用LLM解析（如为False则使用内置规则解析）

    Returns:
        包含详细评测结果的字典
    """
    llm = None
    if use_llm:
        llm = load_llm_parser()
        if llm is None:
            logger.warning("LLM不可用，回退到内置规则解析")

    results = []
    total_fields = 0
    matched_fields = 0

    for case in JD_TEST_CASES:
        case_id = case["id"]
        title = case["title"]
        text = case["input"]
        expected = case["expected_output"]
        fields = case["fields"]

        if llm:
            actual = parse_with_llm(llm, text)
        else:
            actual = parse_jd_builtin(text)

        if not actual:
            logger.warning(f"[{case_id}] 解析失败，使用空结果")
            actual = {}

        field_results = []
        case_matched = 0
        case_total = 0

        for field in fields:
            case_total += 1
            expected_value = expected.get(field)
            actual_value = actual.get(field)

            ok, detail = compare_field(actual_value, expected_value, field)
            field_results.append({
                "field": field,
                "matched": ok,
                "actual": actual_value,
                "expected": expected_value,
                "detail": detail,
            })
            if ok:
                case_matched += 1

        case_accuracy = case_matched / case_total if case_total > 0 else 0
        total_fields += case_total
        matched_fields += case_matched

        results.append({
            "id": case_id,
            "title": title,
            "accuracy": round(case_accuracy, 4),
            "matched_fields": case_matched,
            "total_fields": case_total,
            "field_results": field_results,
        })

    overall_accuracy = matched_fields / total_fields if total_fields > 0 else 0

    return {
        "test_type": "JD解析准确率评测",
        "total_cases": len(JD_TEST_CASES),
        "total_fields": total_fields,
        "matched_fields": matched_fields,
        "overall_accuracy": round(overall_accuracy, 4),
        "passed": overall_accuracy >= 0.90,
        "results": results,
    }


def print_report(report: dict):
    """打印评测报告"""
    sep = "=" * 70
    sub_sep = "-" * 70

    print(f"\n{sep}")
    print(f"  {report['test_type']}")
    print(f"{sep}")
    print(f"  总用例: {report['total_cases']} 条JD")
    print(f"  总字段: {report['total_fields']}")
    print(f"  匹配字段: {report['matched_fields']}")
    print(f"  总体准确率: {report['overall_accuracy']:.2%}")
    status = "✓ PASS (≥90%)" if report["passed"] else "✗ FAIL (<90%)"
    print(f"  状态: {status}")
    print(f"{sep}\n")

    for r in report["results"]:
        print(f"  [{r['id']}] {r['title']}")
        print(f"      字段准确率: {r['accuracy']:.2%} ({r['matched_fields']}/{r['total_fields']})")
        for fr in r["field_results"]:
            icon = "✓" if fr["matched"] else "✗"
            print(f"        {icon} {fr['field']}: {fr['detail']}")
        print()

    print(f"{sub_sep}")
    print(f"  摘要: {report['matched_fields']}/{report['total_fields']} 字段匹配, "
          f"准确率={report['overall_accuracy']:.2%}")
    print(f"  判定: {'通过' if report['passed'] else '未通过'}")
    print(f"{sep}\n")


def run(use_llm: bool = False) -> dict:
    """运行JD解析准确率评测"""
    logger.info("=" * 60)
    logger.info("开始JD解析准确率评测")
    logger.info("=" * 60)

    report = evaluate_jd_accuracy(use_llm)
    print_report(report)

    logger.info("JD解析准确率评测完成")
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="JD解析准确率评测")
    parser.add_argument("--use-llm", action="store_true", help="使用LLM解析（默认使用内置规则）")
    args = parser.parse_args()
    run(use_llm=args.use_llm)
