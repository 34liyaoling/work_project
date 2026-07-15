"""匹配测试 - 双方式准确率 ≥ 90%"""
import pytest

from app.services.matcher import Matcher
from app.services.monitor import METRIC_MATCH, accuracy_monitor


def test_both_ways_accuracy(match_corpus, resume_corpus, jd_corpus, accuracy_monitor):
    """向量 + 图谱双方式匹配准确率"""
    if not (match_corpus and resume_corpus and jd_corpus):
        pytest.skip("匹配语料不完整")

    matcher = Matcher()
    jd_map = {j["jd_id"]: j for j in jd_corpus}
    r_map = {r["resume_id"]: r for r in resume_corpus}

    correct = 0
    total = 0
    for pair in match_corpus:
        r = r_map.get(pair["resume_id"])
        jd = jd_map.get(pair["jd_id"])
        if not r or not jd:
            continue
        result = matcher.match_both_ways(
            resume_skills=r.get("skills", []),
            top_k=5,
        )
        # 简化：取 best 命中即视为 True
        best = result[0] if result else None
        predicted = bool(best and best.get("match", False))
        expected = bool(pair.get("expected_match", False))
        ok = predicted == expected
        accuracy_monitor.record_one(METRIC_MATCH, ok)
        correct += int(ok)
        total += 1
    acc = correct / total if total else 0
    print(f"\n[匹配] 准确率 = {acc:.2%}  ({correct}/{total})")
    assert acc >= 0.90, f"匹配准确率 {acc:.2%} < 90%"


def test_vector_only_accuracy(match_corpus, resume_corpus, jd_corpus):
    """仅向量匹配"""
    if not (match_corpus and resume_corpus and jd_corpus):
        pytest.skip("匹配语料不完整")
    matcher = Matcher()
    jd_map = {j["jd_id"]: j for j in jd_corpus}
    r_map = {r["resume_id"]: r for r in resume_corpus}
    correct = 0
    total = 0
    for pair in match_corpus:
        r = r_map.get(pair["resume_id"])
        jd = jd_map.get(pair["jd_id"])
        if not r or not jd:
            continue
        result = matcher.match_vector(resume_skills=r["skills"], top_k=5)
        predicted = bool(result and result[0].get("match", False))
        expected = bool(pair.get("expected_match", False))
        correct += int(predicted == expected)
        total += 1
    acc = correct / total if total else 0
    assert acc >= 0.90, f"向量匹配准确率 {acc:.2%} < 90%"


def test_match_corpus_size(match_corpus):
    assert len(match_corpus) >= 20, f"匹配语料 {len(match_corpus)} < 20"
