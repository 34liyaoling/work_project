"""一键运行所有评测

依次运行3个评测:
    1. JD解析准确率评测
    2. 简历提取准确率评测
    3. 人岗匹配准确率评测

汇总3个准确率指标，判断是否达到90%，输出评测报告到 data/evaluation_reports/ 目录。
"""

import json
import logging
import os
import sys
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tests.evaluation.jd_accuracy_test import run as run_jd_eval
from tests.evaluation.resume_accuracy_test import run as run_resume_eval
from tests.evaluation.matching_accuracy_test import run as run_matching_eval


REPORT_DIR = os.path.join(PROJECT_ROOT, "data", "evaluation_reports")


def ensure_report_dir():
    """确保报告目录存在"""
    os.makedirs(REPORT_DIR, exist_ok=True)


def run_all_evals(use_llm: bool = False, use_real_match_engine: bool = False) -> list[dict]:
    """依次运行所有评测"""
    logger.info("=" * 70)
    logger.info("  开始一键运行所有评测")
    logger.info(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)

    reports = []

    logger.info("\n" + "=" * 70)
    logger.info("  评测 1/3: JD解析准确率评测")
    logger.info("=" * 70)
    try:
        jd_report = run_jd_eval(use_llm=use_llm)
        reports.append(jd_report)
    except Exception as e:
        logger.error(f"JD解析评测失败: {e}")
        reports.append({
            "test_type": "JD解析准确率评测",
            "error": str(e),
            "overall_accuracy": 0.0,
            "passed": False,
        })

    logger.info("\n" + "=" * 70)
    logger.info("  评测 2/3: 简历提取准确率评测")
    logger.info("=" * 70)
    try:
        resume_report = run_resume_eval(use_llm=use_llm)
        reports.append(resume_report)
    except Exception as e:
        logger.error(f"简历提取评测失败: {e}")
        reports.append({
            "test_type": "简历提取准确率评测",
            "error": str(e),
            "overall_accuracy": 0.0,
            "passed": False,
        })

    logger.info("\n" + "=" * 70)
    logger.info("  评测 3/3: 人岗匹配准确率评测")
    logger.info("=" * 70)
    try:
        matching_report = run_matching_eval(use_real_engine=use_real_match_engine)
        reports.append(matching_report)
    except Exception as e:
        logger.error(f"人岗匹配评测失败: {e}")
        reports.append({
            "test_type": "人岗匹配准确率评测",
            "error": str(e),
            "accuracy": 0.0,
            "passed": False,
        })

    return reports


def generate_summary(reports: list[dict]) -> dict:
    """生成汇总结果"""
    summary = {
        "evaluation_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "overall_status": True,
        "metrics": {},
        "details": [],
    }

    for report in reports:
        test_type = report.get("test_type", "未知评测")
        accuracy_key = "accuracy" if "accuracy" in report else "overall_accuracy"
        accuracy = report.get(accuracy_key, 0.0)
        passed = report.get("passed", False)

        metric = {
            "test_type": test_type,
            "accuracy": accuracy,
            "passed": passed,
            "target": "≥90%",
        }

        if "precision" in report:
            metric["precision"] = report["precision"]
            metric["recall"] = report["recall"]
            metric["f1_score"] = report["f1_score"]

        if "total_cases" in report:
            metric["total_cases"] = report["total_cases"]

        summary["metrics"][test_type] = metric
        summary["details"].append(report)

        if not passed:
            summary["overall_status"] = False

    summary["all_passed"] = all(
        r.get("passed", False) for r in reports
    )

    return summary


def print_summary(summary: dict):
    """打印汇总报告"""
    sep = "=" * 70

    print(f"\n{sep}")
    print(f"  📊 知识图谱系统评测汇总报告")
    print(f"{sep}")
    print(f"  评测时间: {summary['evaluation_time']}")
    print(f"{sep}\n")

    for test_type, metric in summary["metrics"].items():
        accuracy = metric["accuracy"]
        passed = metric["passed"]
        status_icon = "✓" if passed else "✗"
        status_text = "通过" if passed else "未通过"
        bar = "█" * int(accuracy * 30) + "░" * (30 - int(accuracy * 30))
        print(f"  {status_icon} {test_type}")
        print(f"    准确率: {accuracy:.2%} {bar}")
        print(f"    目标:   {metric['target']}")
        if "precision" in metric:
            print(f"    精确率: {metric['precision']:.2%}")
            print(f"    召回率: {metric['recall']:.2%}")
            print(f"    F1:     {metric['f1_score']:.4f}")
        print(f"    状态:   {status_text}")

        if not passed:
            gap = 0.90 - accuracy
            print(f"    差距:   还差 {gap:.2%}")
        print()

    print(f"{sep}")
    all_passed = summary["all_passed"]
    if all_passed:
        print(f"  ✅ 最终判定: 所有评测全部通过！")
        print(f"  🎉 三个90%目标均已达成")
    else:
        print(f"  ❌ 最终判定: 存在未通过评测")
        failed = [k for k, v in summary["metrics"].items() if not v["passed"]]
        print(f"  未通过项: {', '.join(failed)}")
        print(f"  请检查解析/匹配逻辑并优化后重新评测")
    print(f"{sep}\n")


def save_report(summary: dict):
    """保存评测报告到文件"""
    ensure_report_dir()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(REPORT_DIR, f"eval_report_{timestamp}.json")
    txt_path = os.path.join(REPORT_DIR, f"eval_report_{timestamp}.txt")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
    logger.info(f"JSON报告已保存: {json_path}")

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("  知识图谱系统评测报告\n")
        f.write(f"  时间: {summary['evaluation_time']}\n")
        f.write("=" * 70 + "\n\n")

        for test_type, metric in summary["metrics"].items():
            f.write(f"  {'✓' if metric['passed'] else '✗'} {test_type}\n")
            f.write(f"    准确率: {metric['accuracy']:.2%}\n")
            f.write(f"    目标:   {metric['target']}\n")
            if "precision" in metric:
                f.write(f"    精确率: {metric['precision']:.2%}\n")
                f.write(f"    召回率: {metric['recall']:.2%}\n")
                f.write(f"    F1:     {metric['f1_score']:.4f}\n")
            f.write(f"    状态:   {'通过' if metric['passed'] else '未通过'}\n\n")

        f.write("=" * 70 + "\n")
        if summary["all_passed"]:
            f.write("  最终判定: 所有评测全部通过！三个90%目标均已达成\n")
        else:
            f.write("  最终判定: 存在未通过评测\n")
            failed = [k for k, v in summary["metrics"].items() if not v["passed"]]
            f.write(f"  未通过项: {', '.join(failed)}\n")
        f.write("=" * 70 + "\n")

    logger.info(f"文本报告已保存: {txt_path}")
    return json_path, txt_path


def run(use_llm: bool = False, use_real_match_engine: bool = False, save: bool = True):
    """一键运行所有评测"""
    logger.info("=" * 70)
    logger.info("  知识图谱系统 - 一键评测启动")
    logger.info("=" * 70)

    reports = run_all_evals(
        use_llm=use_llm,
        use_real_match_engine=use_real_match_engine,
    )

    summary = generate_summary(reports)
    print_summary(summary)

    if save:
        json_path, txt_path = save_report(summary)

    logger.info("=" * 70)
    logger.info("  所有评测已完成！")
    if save:
        logger.info(f"  报告已保存至: {REPORT_DIR}")
        logger.info(f"    - JSON: {os.path.basename(json_path)}")
        logger.info(f"    - TXT:  {os.path.basename(txt_path)}")
    logger.info("=" * 70)

    return summary


def main():
    import argparse
    parser = argparse.ArgumentParser(description="一键运行知识图谱系统所有评测")
    parser.add_argument("--use-llm", action="store_true", help="使用LLM解析JD和简历（默认使用内置规则）")
    parser.add_argument("--use-real-match-engine", action="store_true", help="使用实际匹配引擎（默认使用内置规则）")
    parser.add_argument("--no-save", action="store_true", help="不保存报告到文件")
    args = parser.parse_args()

    run(
        use_llm=args.use_llm,
        use_real_match_engine=args.use_real_match_engine,
        save=not args.no_save,
    )


if __name__ == "__main__":
    main()
