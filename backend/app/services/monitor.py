"""准确率监控看板

跟踪三个 90% 准确率指标：
1. JD 解析准确率
2. 简历解析准确率
3. 双方式匹配准确率

提供：
- record(metric, success, total) 记录一次批次
- get_report()  返回 JSON 格式监控报告
- export(path)  落盘到 logs/monitor/
"""
from __future__ import annotations

import json
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional


METRIC_JD_PARSE = "jd_parse"
METRIC_RESUME_PARSE = "resume_parse"
METRIC_MATCH = "match"
ALL_METRICS = [METRIC_JD_PARSE, METRIC_RESUME_PARSE, METRIC_MATCH]

TARGET_ACCURACY = 0.90
WINDOW_SIZE = 200  # 滑动窗口大小


@dataclass
class Sample:
    success: bool
    total: int
    ts: float = field(default_factory=time.time)


class AccuracyMonitor:
    """三个 90% 准确率指标实时跟踪"""

    def __init__(self, window_size: int = WINDOW_SIZE, target: float = TARGET_ACCURACY):
        self.window_size = window_size
        self.target = target
        self._samples: Dict[str, Deque[Sample]] = {m: deque(maxlen=window_size) for m in ALL_METRICS}
        self._cumulative: Dict[str, Dict[str, int]] = {
            m: {"success": 0, "total": 0} for m in ALL_METRICS
        }

    def record(self, metric: str, success: int, total: int = 1) -> None:
        """记录一次样本结果（按条数批量记录）"""
        if metric not in ALL_METRICS:
            raise ValueError(f"unknown metric: {metric}")
        success = max(0, min(int(success), int(total)))
        self._samples[metric].append(Sample(success=success == total, total=total))
        self._cumulative[metric]["success"] += success
        self._cumulative[metric]["total"] += total

    def record_one(self, metric: str, is_correct: bool) -> None:
        """记录单条预测是否正确"""
        self.record(metric, success=1 if is_correct else 0, total=1)

    def _accuracy(self, metric: str) -> float:
        c = self._cumulative[metric]
        if c["total"] == 0:
            return 0.0
        return c["success"] / c["total"]

    def _window_accuracy(self, metric: str) -> Optional[float]:
        s = self._samples[metric]
        if not s:
            return None
        total_correct = sum(1 for x in s if x.success)
        total = sum(x.total for x in s)
        if total == 0:
            return None
        return total_correct / total

    def get_report(self) -> Dict[str, Any]:
        """返回 JSON 格式的监控报告"""
        metrics_block: Dict[str, Any] = {}
        for m in ALL_METRICS:
            cur = self._accuracy(m)
            win = self._window_accuracy(m)
            status = "pass" if cur >= self.target else "fail"
            metrics_block[m] = {
                "cumulative_accuracy": round(cur, 4),
                "window_accuracy": round(win, 4) if win is not None else None,
                "samples": self._cumulative[m]["total"],
                "window_size": len(self._samples[m]),
                "target": self.target,
                "status": status,
            }

        overall_pass = all(v["status"] == "pass" for v in metrics_block.values())
        return {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "target": self.target,
            "overall_status": "pass" if overall_pass else "fail",
            "metrics": metrics_block,
        }

    def export(self, path: str = "logs/monitor/accuracy.json") -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            json.dump(self.get_report(), f, ensure_ascii=False, indent=2)
        return p

    def reset(self) -> None:
        for m in ALL_METRICS:
            self._samples[m].clear()
            self._cumulative[m] = {"success": 0, "total": 0}


# 全局单例
accuracy_monitor = AccuracyMonitor()
