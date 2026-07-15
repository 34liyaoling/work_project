"""准确率监控测试"""
import json
from pathlib import Path

import pytest

from app.services.monitor import (
    ALL_METRICS,
    METRIC_JD_PARSE,
    METRIC_MATCH,
    METRIC_RESUME_PARSE,
    AccuracyMonitor,
)


def test_initial_zero():
    mon = AccuracyMonitor()
    report = mon.get_report()
    assert report["overall_status"] == "fail"  # 没有数据 -> 不算 pass
    for m in ALL_METRICS:
        assert report["metrics"][m]["cumulative_accuracy"] == 0


def test_record_and_report():
    mon = AccuracyMonitor()
    # JD 解析 100 条中 95 条正确
    mon.record(METRIC_JD_PARSE, success=95, total=100)
    # 简历 100 条中 92 条正确
    mon.record(METRIC_RESUME_PARSE, success=92, total=100)
    # 匹配 100 条中 90 条正确（边界）
    mon.record(METRIC_MATCH, success=90, total=100)

    report = mon.get_report()
    assert report["metrics"][METRIC_JD_PARSE]["cumulative_accuracy"] == 0.95
    assert report["metrics"][METRIC_RESUME_PARSE]["cumulative_accuracy"] == 0.92
    assert report["metrics"][METRIC_MATCH]["cumulative_accuracy"] == 0.90
    assert report["overall_status"] == "pass"


def test_window_accuracy():
    mon = AccuracyMonitor(window_size=10)
    for _ in range(8):
        mon.record_one(METRIC_JD_PARSE, True)
    for _ in range(2):
        mon.record_one(METRIC_JD_PARSE, False)
    report = mon.get_report()
    assert report["metrics"][METRIC_JD_PARSE]["cumulative_accuracy"] == 0.8
    assert report["metrics"][METRIC_JD_PARSE]["window_accuracy"] == 0.8


def test_export(tmp_path):
    mon = AccuracyMonitor()
    mon.record(METRIC_JD_PARSE, success=10, total=10)
    p = mon.export(path=str(tmp_path / "report.json"))
    assert p.exists()
    data = json.loads(p.read_text(encoding="utf-8"))
    assert "metrics" in data


def test_invalid_metric():
    mon = AccuracyMonitor()
    with pytest.raises(ValueError):
        mon.record("unknown", success=1, total=1)
