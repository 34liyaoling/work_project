"""人岗匹配准确率评测

评测方法:
    1. 定义20个人-岗匹配测试用例（含人工标注的匹配/不匹配标签）
    2. 对每个用例调用内置匹配引擎计算匹配度
    3. 设定阈值（≥0.5算匹配），比较预测标签与人工标签
    4. 计算准确率、精确率、召回率、F1
    5. 输出详细报告
"""

import logging
import os
import sys
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tests.evaluation.test_data import MATCH_TEST_CASES


@dataclass
class MatchEvalResult:
    score: float
    prediction: int
    ground_truth: int
    correct: bool


def calculate_match_builtin(resume: dict, job: dict) -> float:
    """内置规则匹配引擎（模拟HybridMatchEngine的核心逻辑）

    使用加权评分：
    - 技能匹配分: 必备技能覆盖率×0.6 + 可选技能覆盖率×0.25 + 可信度×0.15
    - 最终通过加权计算匹配分数
    """
    resume_skills = set(s.lower().strip() for s in resume.get("skills", []))
    resume_implicit = set(s.lower().strip() for s in resume.get("implicit_skills", []))
    all_resume_skills = resume_skills | resume_implicit

    required = set(s.lower().strip() for s in job.get("required_skills", []))
    optional = set(s.lower().strip() for s in job.get("optional_skills", []))

    if not required and not optional:
        return 0.5

    matched_required = required & all_resume_skills
    matched_optional = optional & all_resume_skills

    matched_required_fuzzy = set()
    for req in required:
        if req in matched_required:
            continue
        for r_skill in all_resume_skills:
            if req in r_skill or r_skill in req:
                matched_required_fuzzy.add(req)
                break

    matched_required_all = matched_required | matched_required_fuzzy

    matched_optional_fuzzy = set()
    for opt in optional:
        if opt in matched_optional:
            continue
        for r_skill in all_resume_skills:
            if opt in r_skill or r_skill in opt:
                matched_optional_fuzzy.add(opt)
                break

    matched_optional_all = matched_optional | matched_optional_fuzzy

    all_matched = list(matched_required_all) + list(matched_optional_all)

    required_coverage = len(matched_required_all) / max(len(required), 1)

    if optional:
        optional_coverage = len(matched_optional_all) / max(len(optional), 1)
    else:
        optional_coverage = 0.5

    cred_scores = []
    for swc in resume.get("skills_with_credibility", []):
        skill_name = swc.get("skill_name", "").lower().strip()
        if skill_name in [s.lower().strip() for s in all_matched]:
            cred_scores.append(swc.get("credibility_score", 0.5))

    avg_cred = sum(cred_scores) / max(len(cred_scores), 1) if cred_scores else 0.5

    skill_score = required_coverage * 0.6 + optional_coverage * 0.25 + avg_cred * 0.15

    required_remain = len(required) - len(matched_required_all)
    penalty = required_remain * 0.05
    skill_score = max(0, skill_score - penalty)

    return round(min(1.0, skill_score), 4)


def try_match_engine(resume: dict, job: dict) -> float | None:
    """尝试使用项目实际的匹配引擎"""
    try:
        from core.match_engine import HybridMatchEngine
        engine = HybridMatchEngine()

        resume_profile = {
            "skills": resume.get("skills", []),
            "implicit_skills": resume.get("implicit_skills", []),
            "skills_with_credibility": resume.get("skills_with_credibility", []),
            "embedding": resume.get("embedding"),
        }
        job_requirement = {
            "title": job.get("title", ""),
            "required_skills": job.get("required_skills", []),
            "optional_skills": job.get("optional_skills", []),
            "embedding": job.get("embedding"),
        }
        result = engine.calculate_match(resume_profile, job_requirement)
        return result.score
    except Exception as e:
        logger.warning(f"匹配引擎调用失败，回退到内置规则: {e}")
        return None


def evaluate_matching_accuracy(threshold: float = 0.5, use_real_engine: bool = False) -> dict:
    """运行人岗匹配准确率评测"""
    results = []

    for case in MATCH_TEST_CASES:
        case_id = case["id"]
        resume = case["resume"]
        job = case["job"]
        label = case["label"]

        if use_real_engine:
            score = try_match_engine(resume, job)
            if score is None:
                score = calculate_match_builtin(resume, job)
        else:
            score = calculate_match_builtin(resume, job)

        prediction = 1 if score >= threshold else 0
        correct = prediction == label

        results.append(MatchEvalResult(
            score=score,
            prediction=prediction,
            ground_truth=label,
            correct=correct,
        ))

    total = len(results)
    correct_count = sum(1 for r in results if r.correct)

    tp = sum(1 for r in results if r.prediction == 1 and r.ground_truth == 1)
    tn = sum(1 for r in results if r.prediction == 0 and r.ground_truth == 0)
    fp = sum(1 for r in results if r.prediction == 1 and r.ground_truth == 0)
    fn = sum(1 for r in results if r.prediction == 0 and r.ground_truth == 1)

    accuracy = correct_count / total if total > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return {
        "test_type": "人岗匹配准确率评测",
        "total_cases": total,
        "threshold": threshold,
        "correct_count": correct_count,
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "passed": accuracy >= 0.90,
        "results": [
            {
                "id": MATCH_TEST_CASES[i]["id"],
                "description": MATCH_TEST_CASES[i]["description"],
                "score": r.score,
                "prediction": r.prediction,
                "ground_truth": r.ground_truth,
                "correct": r.correct,
            }
            for i, r in enumerate(results)
        ],
    }


def print_report(report: dict):
    """打印评测报告"""
    sep = "=" * 70
    sub_sep = "-" * 70

    print(f"\n{sep}")
    print(f"  {report['test_type']}")
    print(f"{sep}")
    print(f"  总用例: {report['total_cases']} 个人-岗对")
    print(f"  判定阈值: ≥{report['threshold']}")
    print(f"")
    print(f"  混淆矩阵:")
    print(f"            预测匹配    预测不匹配")
    print(f"  实际匹配    {report['tp']:>3}          {report['fn']:>3}")
    print(f"  实际不匹配  {report['fp']:>3}          {report['tn']:>3}")
    print(f"")
    print(f"  准确率 (Accuracy):  {report['accuracy']:.2%}")
    print(f"  精确率 (Precision): {report['precision']:.2%}")
    print(f"  召回率 (Recall):    {report['recall']:.2%}")
    print(f"  F1分数:             {report['f1_score']:.4f}")
    status = "✓ PASS (≥90%)" if report["passed"] else "✗ FAIL (<90%)"
    print(f"  状态: {status}")
    print(f"{sep}\n")

    print(f"  详细结果:")
    for r in report["results"]:
        icon = "✓" if r["correct"] else "✗"
        pred_label = "匹配" if r["prediction"] == 1 else "不匹配"
        true_label = "匹配" if r["ground_truth"] == 1 else "不匹配"
        print(f"    {icon} [{r['id']}] 分数={r['score']:.3f}, "
              f"预测={pred_label}, 实际={true_label}")
        print(f"         {r['description']}")

    print(f"\n{sub_sep}")
    print(f"  摘要: 准确率={report['accuracy']:.2%}, "
          f"精确率={report['precision']:.2%}, "
          f"召回率={report['recall']:.2%}, "
          f"F1={report['f1_score']:.4f}")
    print(f"  判定: {'通过' if report['passed'] else '未通过'}")
    print(f"{sep}\n")


def run(threshold: float = 0.5, use_real_engine: bool = False) -> dict:
    """运行人岗匹配准确率评测"""
    logger.info("=" * 60)
    logger.info("开始人岗匹配准确率评测")
    logger.info("=" * 60)

    report = evaluate_matching_accuracy(threshold, use_real_engine)
    print_report(report)

    logger.info("人岗匹配准确率评测完成")
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="人岗匹配准确率评测")
    parser.add_argument("--threshold", type=float, default=0.5, help="匹配判定阈值")
    parser.add_argument("--use-real-engine", action="store_true", help="使用实际匹配引擎（默认使用内置规则）")
    args = parser.parse_args()
    run(threshold=args.threshold, use_real_engine=args.use_real_engine)
