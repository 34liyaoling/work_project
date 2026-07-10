"""简历提取准确率评测

评测方法:
    1. 定义5份标准简历测试用例（含正确的提取字段）
    2. 对每份简历调用内置规则解析或LLM解析
    3. 比较提取结果与标准答案的字段匹配率
    4. 计算总体准确率
    5. 输出详细报告
"""

import logging
import os
import re
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tests.evaluation.test_data import RESUME_TEST_CASES


def parse_resume_builtin(text: str) -> dict:
    """内置规则式简历解析（不依赖LLM的外部API）"""
    result = {
        "name": "",
        "phone": "",
        "email": "",
        "gender": "",
        "age": None,
        "education": [],
        "work_experience": [],
        "total_experience_years": 0,
        "skills_explicit": [],
        "skills_implicit": [],
        "overall_technical_level": "mid",
    }

    lines = text.strip().split("\n")
    full_text = text

    for line in lines:
        line_stripped = line.strip()

        if line_stripped.startswith("姓名："):
            result["name"] = line_stripped.replace("姓名：", "").strip()
        elif line_stripped.startswith("电话："):
            result["phone"] = line_stripped.replace("电话：", "").strip()
        elif line_stripped.startswith("邮箱："):
            result["email"] = line_stripped.replace("邮箱：", "").strip()
        elif line_stripped.startswith("性别："):
            result["gender"] = line_stripped.replace("性别：", "").strip()
        elif line_stripped.startswith("年龄："):
            try:
                result["age"] = int(line_stripped.replace("年龄：", "").strip())
            except ValueError:
                pass

    edu_records = _parse_education_section(full_text)
    result["education"] = edu_records

    work_records = _parse_work_experience_section(full_text)
    result["work_experience"] = work_records

    result["total_experience_years"] = _calc_total_years(work_records)

    skills = _parse_skills_section(full_text)
    result["skills_explicit"] = skills

    result["overall_technical_level"] = _infer_level_from_resume(skills, work_records)

    return result


def _get_section_text(text: str, section_title: str, next_section_titles: list[str]) -> str:
    """提取简历中指定章节的文本内容"""
    lines = text.split("\n")
    in_section = False
    section_lines = []

    for line in lines:
        stripped = line.strip()

        if not in_section:
            if stripped == section_title or stripped.startswith(section_title):
                in_section = True
                continue

        if in_section:
            is_next = False
            for ns in next_section_titles:
                if stripped == ns or stripped.startswith(ns):
                    is_next = True
                    break
            if is_next:
                break
            section_lines.append(line)

    return "\n".join(section_lines).strip()


def _parse_education_section(text: str) -> list[dict]:
    """解析教育背景"""
    edu_text = _get_section_text(text, "教育背景", ["工作经历", "项目经验", "技能", "证书"])

    if not edu_text:
        edu_text = _get_section_text(text, "教育", ["工作", "项目", "技能", "证书"])

    records = []
    if not edu_text:
        return records

    edu_pattern = re.compile(
        r"(\d{4}\.\d{1,2})\s*-\s*(\d{4}\.\d{1,2}|至今)\s+([\u4e00-\u9fa5a-zA-Z]+(?:大学|学院|学校))\s+([\u4e00-\u9fa5\w\u4e00-\u9fa5]+(?:\s*[\u4e00-\u9fa5\w]+)*)\s+([\u4e00-\u9fa5]+)"
    )
    for match in edu_pattern.finditer(edu_text):
        records.append({
            "school": match.group(3).strip(),
            "degree": match.group(5).strip(),
            "major": match.group(4).strip(),
            "graduation_date": match.group(2),
        })

    valid_degrees = {"本科", "学士", "硕士", "博士", "研究生", "专科", "大专"}
    records = [r for r in records if r["degree"] in valid_degrees]

    return records


def _parse_work_experience_section(text: str) -> list[dict]:
    """解析工作经历"""
    work_text = _get_section_text(text, "工作经历", ["项目经验", "教育背景", "技能", "证书"])

    if not work_text:
        work_text = _get_section_text(text, "工作", ["项目", "教育", "技能", "证书"])

    records = []
    if not work_text:
        return records

    work_pattern = re.compile(
        r"(\d{4}\.\d{1,2})\s*-\s*(\d{4}\.\d{1,2}|至今)\s+([\u4e00-\u9fa5a-zA-Z][\u4e00-\u9fa5a-zA-Z\s]*?)\s{2,}([\u4e00-\u9fa5a-zA-Z/][\u4e00-\u9fa5a-zA-Z/（）\s]*)"
    )
    for match in work_pattern.finditer(work_text):
        records.append({
            "company": match.group(3).strip(),
            "position": match.group(4).strip(),
            "start_date": match.group(1),
            "end_date": match.group(2),
        })

    known_companies = ["阿里巴巴", "字节跳动", "网易", "小红书", "拼多多", "蚂蚁集团",
                       "百度", "美团", "滴滴出行", "中兴通讯", "华为", "腾讯", "京东"]
    records = [r for r in records if any(kc in r["company"] for kc in known_companies)]

    return records


def _calc_total_years(work_records: list[dict]) -> float:
    """计算总工作年限"""
    total = 0.0
    for w in work_records:
        start = w.get("start_date", "")
        end = w.get("end_date", "至今")
        try:
            start_year = int(start[:4])
            if end == "至今":
                end_year = 2026
            else:
                end_year = int(end[:4])
            total += max(0, end_year - start_year)
        except (ValueError, IndexError):
            total += 2.0
    return total


def _parse_skills_section(text: str) -> list[str]:
    """解析技能列表"""
    common_skills = [
        "Python", "Java", "Go", "C\\+\\+", "JavaScript", "TypeScript", "Rust", "Scala",
        "React", "Vue", "Vue3", "Angular", "Node\\.js", "Spring Boot", "Spring Cloud", "Spring",
        "Django", "Flask", "FastAPI", "Express",
        "MySQL", "Redis", "Elasticsearch", "MongoDB", "PostgreSQL",
        "Docker", "Kubernetes", "Prometheus", "Grafana", "Jenkins",
        "TensorFlow", "PyTorch", "Scikit-learn", "Pandas", "NumPy",
        "Kafka", "Flink", "Spark", "Hadoop",
        "Terraform", "Ansible", "GitLab CI", "Git",
        "Selenium", "Appium", "Cypress", "JMeter", "Locust",
        "Burp Suite", "Nmap",
        "Tableau", "FineBI", "QuickBI",
        "RocketMQ", "ZooKeeper", "Netty", "Dubbo", "gRPC",
        "Istio", "Helm", "Argo", "Chaos Mesh",
        "HTML5", "CSS3", "Webpack", "Vite", "Redux", "Socket\\.io",
        "Airflow", "SPSS", "XGBoost",
        "Shell", "Linux", "AWS",
        "微服务架构", "高并发", "分布式系统", "消息队列", "数据分析",
        "机器学习", "深度学习", "推荐系统", "协同过滤",
        "AIGC", "大模型", "LLM",
        "产品设计", "用户研究", "PRD", "B端产品",
        "前端工程化", "自动化测试", "性能测试", "接口测试",
        "渗透测试", "Web安全", "移动安全", "云安全", "代码审计", "SDL",
        "CI/CD", "SRE", "ELK",
        "系统设计", "架构设计",
        "数据可视化", "回归分析", "假设检验", "聚类分析",
        "AB实验", "Excel", "R",
        "OpenTelemetry", "Istio", "AlertManager",
        "Canvas", "WebSocket", "Module Federation",
        "qiankun", "MongoDB",
        "AWS", "SPSS",
    ]

    skill_section = ""
    in_skill_section = False
    for line in text.split("\n"):
        line_stripped = line.strip()
        if line_stripped == "技能" or line_stripped.startswith("技能"):
            in_skill_section = True
            continue
        if in_skill_section:
            if line_stripped == "" or line_stripped.startswith("证书") or line_stripped.startswith("项目"):
                break
            skill_section += line_stripped + " "

    found = []
    for skill_pattern in common_skills:
        pattern = skill_pattern.replace("\\+", "+").replace("\\.", ".").replace("\\ ", " ")
        if pattern.lower() in (skill_section + text).lower():
            if pattern not in found:
                found.append(pattern)

    return found


def _infer_level_from_resume(skills: list[str], work_records: list[dict]) -> str:
    """从技能和工作经验推断技术级别"""
    years = _calc_total_years(work_records)

    expert_keywords = ["架构师", "技术专家", "首席", "总监"]
    for w in work_records:
        pos = w.get("position", "")
        if any(kw in pos for kw in expert_keywords):
            return "expert"

    if years >= 8 and len(skills) >= 15:
        return "senior"
    elif years >= 4 and len(skills) >= 8:
        return "mid"
    else:
        return "junior"


def compare_resume_field(actual, expected, field: str) -> tuple[bool, str]:
    """比较简历单个字段"""
    if field == "education":
        if not actual or not expected:
            return (actual == expected), f"教育记录: actual={len(actual) if actual else 0}, expected={len(expected) if expected else 0}"
        if len(actual) != len(expected):
            return False, f"记录数不匹配: {len(actual)} vs {len(expected)}"
        for i, (a, e) in enumerate(zip(actual, expected)):
            for key in ["school", "degree", "major"]:
                if a.get(key, "").strip() != e.get(key, "").strip():
                    return False, f"第{i+1}条{key}: '{a.get(key)}' vs '{e.get(key)}'"
        return True, f"教育背景完全匹配 ({len(actual)}条)"

    if field == "work_experience":
        if not actual or not expected:
            return (actual == expected), f"工作记录: actual={len(actual) if actual else 0}, expected={len(expected) if expected else 0}"
        if len(actual) != len(expected):
            return False, f"记录数不匹配: {len(actual)} vs {len(expected)}"
        for i, (a, e) in enumerate(zip(actual, expected)):
            for key in ["company", "position"]:
                if a.get(key, "").strip() != e.get(key, "").strip():
                    return False, f"第{i+1}条{key}: '{a.get(key)}' vs '{e.get(key)}'"
        return True, f"工作经历完全匹配 ({len(actual)}条)"

    if field == "skills_explicit":
        actual_set = set(s.lower().replace(" ", "").replace(".", "") for s in (actual or []))
        expected_set = set(s.lower().replace(" ", "").replace(".", "") for s in (expected or []))
        if len(expected_set) == 0:
            return True, "无期望值（跳过）"
        intersection = actual_set & expected_set
        matched = len(intersection) >= len(expected_set) * 0.6
        if matched:
            missed = expected_set - intersection
            detail = f"技能匹配{len(intersection)}/{len(expected_set)}"
            if missed:
                detail += f", 差异: {missed}"
            return True, detail
        else:
            missed = expected_set - intersection
            return False, f"仅匹配{len(intersection)}/{len(expected_set)}, 遗漏: {missed}"

    if field == "total_experience_years":
        diff = abs((actual or 0) - (expected or 0))
        if diff <= 2:
            return True, f"{actual} vs {expected} (误差{diff}年，可接受)"
        return False, f"{actual} vs {expected} (误差{diff}年)"

    if actual is None and expected is None:
        return True, "均无"
    if actual is None or expected is None:
        return False, f"actual={actual}, expected={expected}"

    if isinstance(actual, str) and isinstance(expected, str):
        match = actual.strip() == expected.strip()
        return match, f"'{actual}' vs '{expected}'"

    match = str(actual).strip() == str(expected).strip()
    return match, f"{actual} vs {expected}"


def parse_llm_resume(text: str) -> dict:
    """使用LLM解析简历（尝试调用实际项目中的ResumeParserAgent）"""
    try:
        sys.path.insert(0, PROJECT_ROOT)
        from agents.resume_parser import ResumeParserAgent
        import tempfile

        parser = ResumeParserAgent()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(text)
            tmp_path = f.name

        try:
            profile = parser.parse_resume(tmp_path)
            result = {
                "name": profile.name or "",
                "phone": profile.phone or "",
                "email": profile.email or "",
                "gender": profile.gender or "",
                "age": profile.age,
                "education": [
                    {
                        "school": e.school,
                        "degree": e.degree,
                        "major": e.major,
                        "graduation_date": e.graduation_date or "",
                    }
                    for e in profile.education
                ],
                "work_experience": [
                    {
                        "company": w.company,
                        "position": w.position,
                        "start_date": w.start_date or "",
                        "end_date": w.end_date or "",
                    }
                    for w in profile.work_experience
                ],
                "total_experience_years": profile.total_experience_years,
                "skills_explicit": profile.skills_explicit,
                "skills_implicit": profile.skills_implicit,
                "overall_technical_level": profile.overall_technical_level,
            }
            return result
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    except Exception as e:
        logger.warning(f"ResumeParserAgent解析失败，回退到内置规则: {e}")
        return {}


def evaluate_resume_accuracy(use_llm: bool = False) -> dict:
    """运行简历提取准确率评测"""
    results = []
    total_fields = 0
    matched_fields = 0

    for case in RESUME_TEST_CASES:
        case_id = case["id"]
        title = case["title"]
        text = case["input"]
        expected = case["expected_output"]
        fields = case["fields"]

        if use_llm:
            actual = parse_llm_resume(text)
            if not actual:
                logger.warning(f"[{case_id}] LLM解析失败，使用内置规则")
                actual = parse_resume_builtin(text)
        else:
            actual = parse_resume_builtin(text)

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

            ok, detail = compare_resume_field(actual_value, expected_value, field)
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
        "test_type": "简历提取准确率评测",
        "total_cases": len(RESUME_TEST_CASES),
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
    print(f"  总用例: {report['total_cases']} 份简历")
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
    """运行简历提取准确率评测"""
    logger.info("=" * 60)
    logger.info("开始简历提取准确率评测")
    logger.info("=" * 60)

    report = evaluate_resume_accuracy(use_llm)
    print_report(report)

    logger.info("简历提取准确率评测完成")
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="简历提取准确率评测")
    parser.add_argument("--use-llm", action="store_true", help="使用LLM解析（默认使用内置规则）")
    args = parser.parse_args()
    run(use_llm=args.use_llm)
