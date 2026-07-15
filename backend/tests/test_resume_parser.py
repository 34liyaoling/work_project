"""简历解析测试 - 验证解析准确率 ≥ 90%"""
import pytest

from app.services.monitor import METRIC_RESUME_PARSE, accuracy_monitor
from app.services.resume_parser import ResumeParser


def _set_overlap_f1(a, b) -> float:
    sa, sb = set(a or []), set(b or [])
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    if inter == 0:
        return 0.0
    p, r = inter / len(sa), inter / len(sb)
    return 2 * p * r / (p + r)


def test_resume_skill_extraction(resume_corpus, accuracy_monitor):
    parser = ResumeParser()
    if not resume_corpus:
        pytest.skip("resume_corpus 为空")
    correct = 0
    total = 0
    for r in resume_corpus:
        parsed = parser.parse(r["raw_text"])
        if not isinstance(parsed, dict):
            total += 1
            continue
        f1 = _set_overlap_f1(parsed.get("skills"), r.get("skills"))
        ok = f1 >= 0.7
        accuracy_monitor.record_one(METRIC_RESUME_PARSE, ok)
        correct += int(ok)
        total += 1
    acc = correct / total if total else 0
    print(f"\n[简历解析] 准确率 = {acc:.2%}  ({correct}/{total})")
    assert acc >= 0.90, f"简历解析准确率 {acc:.2%} < 90%"


def test_resume_basic_fields(resume_corpus):
    parser = ResumeParser()
    for r in resume_corpus[:10]:
        parsed = parser.parse(r["raw_text"])
        assert isinstance(parsed, dict)
        assert "skills" in parsed
        assert isinstance(parsed["skills"], list)


def test_resume_corpus_size(resume_corpus):
    assert len(resume_corpus) >= 20, f"简历测试集 {len(resume_corpus)} < 20"
