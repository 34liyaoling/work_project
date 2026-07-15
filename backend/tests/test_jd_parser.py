"""JD 解析测试 - 验证解析准确率 ≥ 90%"""
import json
from pathlib import Path

import pytest

from app.services.jd_parser import JdParser
from app.services.monitor import METRIC_JD_PARSE, accuracy_monitor


JD_FIELDS = ["title", "category", "level", "location", "skills"]


def _f1(pred_set, gold_set) -> float:
    if not pred_set and not gold_set:
        return 1.0
    if not pred_set or not gold_set:
        return 0.0
    inter = len(pred_set & gold_set)
    if inter == 0:
        return 0.0
    precision = inter / len(pred_set)
    recall = inter / len(gold_set)
    return 2 * precision * recall / (precision + recall)


def test_field_level_f1(jd_corpus, accuracy_monitor):
    """字段级 F1：title / category / level / location / skills"""
    parser = JdParser()
    if not jd_corpus:
        pytest.skip("jd_corpus 为空")

    correct = 0
    total = 0
    per_field_correct = {f: 0 for f in JD_FIELDS}
    per_field_total = {f: 0 for f in JD_FIELDS}

    sample_size = min(50, len(jd_corpus))
    for jd in jd_corpus[:sample_size]:
        parsed = parser.parse(jd["raw_text"])
        if not isinstance(parsed, dict):
            continue

        # 整体判定：所有字段都通过则算 1 条正确
        all_ok = True
        for f in JD_FIELDS:
            per_field_total[f] += 1
            pred = parsed.get(f)
            gold = jd.get(f)
            if f == "skills":
                pred_set = set(pred or [])
                gold_set = set(gold or [])
                f1 = _f1(pred_set, gold_set)
                ok = f1 >= 0.7
            else:
                ok = (pred or "").strip() == (gold or "").strip()
            if ok:
                per_field_correct[f] += 1
            else:
                all_ok = False
        if all_ok:
            correct += 1
        total += 1
        accuracy_monitor.record_one(METRIC_JD_PARSE, all_ok)

    accuracy = correct / total if total else 0.0
    print(f"\n[JD 解析] 准确率 = {accuracy:.2%}  ({correct}/{total})")
    for f in JD_FIELDS:
        acc = per_field_correct[f] / per_field_total[f] if per_field_total[f] else 0
        print(f"  - {f}: {acc:.2%}")
    assert accuracy >= 0.90, f"JD 解析准确率 {accuracy:.2%} < 90%"


def test_skills_extraction_accuracy(jd_corpus, accuracy_monitor):
    """技能提取准确率专项测试"""
    parser = JdParser()
    if not jd_corpus:
        pytest.skip("jd_corpus 为空")

    correct = 0
    total = 0
    for jd in jd_corpus[:30]:
        parsed = parser.parse(jd["raw_text"])
        if not isinstance(parsed, dict):
            total += 1
            continue
        pred = set(parsed.get("skills") or [])
        gold = set(jd.get("skills") or [])
        f1 = _f1(pred, gold)
        ok = f1 >= 0.7
        accuracy_monitor.record_one(METRIC_JD_PARSE, ok)
        correct += int(ok)
        total += 1
    acc = correct / total if total else 0
    assert acc >= 0.90, f"技能提取准确率 {acc:.2%} < 90%"


def test_jd_corpus_size(jd_corpus):
    """验证 JD 测试集 ≥ 100 条"""
    assert len(jd_corpus) >= 100, f"JD 测试集 {len(jd_corpus)} < 100"
