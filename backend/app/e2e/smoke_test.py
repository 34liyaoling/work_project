"""烟雾测试脚本

目的：
1. 验证所有 API 端点可访问（至少根 /、/health 与每个 /api/* 至少一个端点）。
2. 验证关键服务在缺少外部依赖时仍可被实例化而不抛错。

使用方式：
    python -m app.e2e.smoke_test
"""
from __future__ import annotations

import json
import sys
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app.core.logger import log


@dataclass
class CheckResult:
    name: str
    success: bool
    detail: str = ""
    duration_ms: float = 0.0


@dataclass
class SmokeReport:
    started_at: str
    finished_at: str = ""
    results: List[CheckResult] = field(default_factory=list)

    def add(self, name: str, success: bool, detail: str = "", duration_ms: float = 0.0) -> None:
        self.results.append(CheckResult(name=name, success=success, detail=detail, duration_ms=round(duration_ms, 2)))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "summary": {
                "total": len(self.results),
                "passed": sum(1 for r in self.results if r.success),
                "failed": sum(1 for r in self.results if not r.success),
            },
            "results": [r.__dict__ for r in self.results],
        }


def _timeit(fn: Callable[[], Any]) -> tuple[bool, str, float]:
    start = time.time()
    try:
        fn()
        return True, "", (time.time() - start) * 1000
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}", (time.time() - start) * 1000


# ---------------- API 端点 ----------------
def check_api_endpoints(report: SmokeReport, base_url: str) -> None:
    try:
        import httpx
    except ImportError:
        report.add("API端点", False, "httpx 未安装")
        return

    endpoints = [
        ("GET", "/"),
        ("GET", "/health"),
        ("GET", "/api/jd/"),
        ("GET", "/api/resume/"),
        ("GET", "/api/graph/"),
        ("GET", "/api/match/"),
        ("GET", "/api/crawl/"),
        ("GET", "/api/role/"),
    ]

    def call() -> None:
        with httpx.Client(base_url=base_url, timeout=3.0) as client:
            for method, path in endpoints:
                resp = client.request(method, path)
                if resp.status_code >= 500:
                    raise RuntimeError(f"{method} {path} -> {resp.status_code}")

    ok, detail, ms = _timeit(call)
    report.add(f"API端点({len(endpoints)}个)", ok, detail, ms)


# ---------------- 关键服务实例化 ----------------
SERVICE_CLASSES = [
    ("DataCleaner", "app.services.cleaner", "DataCleaner"),
    ("JdParser", "app.services.jd_parser", "JdParser"),
    ("ResumeParser", "app.services.resume_parser", "ResumeParser"),
    ("SkillNormalizer", "app.services.skill_normalizer", "SkillNormalizer"),
    ("Matcher", "app.services.matcher", "Matcher"),
    ("GraphBuilder", "app.services.graph_builder", "GraphBuilder"),
    ("GraphUpdater", "app.services.graph_updater", "GraphUpdater"),
    ("RoleDiscoveryService", "app.services.role_discovery", "RoleDiscoveryService"),
    ("CrawlerService", "app.services.crawler", "CrawlerService"),
    ("AuditService", "app.services.audit", "AuditService"),
    ("GapAnalyzer", "app.services.gap_analyzer", "GapAnalyzer"),
    ("LearningPathService", "app.services.learning_path", "LearningPathService"),
    ("RiskHandler", "app.services.risk_handler", "RiskHandler"),
]


def check_services(report: SmokeReport) -> None:
    import importlib

    for name, module_path, class_name in SERVICE_CLASSES:
        def make_check() -> Callable[[], None]:
            def _check() -> None:
                mod = importlib.import_module(module_path)
                cls = getattr(mod, class_name)
                # 仅尝试无参实例化
                try:
                    cls()
                except TypeError:
                    # 构造函数需要参数时跳过
                    pass
            return _check

        ok, detail, ms = _timeit(make_check())
        report.add(f"服务实例化:{name}", ok, detail, ms)


# ---------------- 数据库连接检查 ----------------
def check_db_connections(report: SmokeReport) -> None:
    def check_mysql() -> None:
        from app.core.database import engine
        with engine.connect() as conn:
            conn.execute("SELECT 1")

    ok, detail, ms = _timeit(check_mysql)
    report.add("MySQL连接", ok, detail, ms)

    def check_neo4j() -> None:
        from app.core.neo4j_db import neo4j_client
        if neo4j_client._driver is None:
            neo4j_client._connect()
        if neo4j_client._driver is None:
            raise RuntimeError("Neo4j 驱动为空")
        with neo4j_client.get_session() as s:
            s.run("RETURN 1").single()

    ok, detail, ms = _timeit(check_neo4j)
    report.add("Neo4j连接", ok, detail, ms)

    def check_es() -> None:
        from app.core.es_client import es_client
        if es_client.client is None:
            raise RuntimeError("ES 客户端为空")
        es_client.client.info()

    ok, detail, ms = _timeit(check_es)
    report.add("ES连接", ok, detail, ms)


# ---------------- 配置加载 ----------------
def check_config(report: SmokeReport) -> None:
    def _check() -> None:
        from app.core.config import settings
        assert settings.APP_NAME and settings.APP_PORT > 0
    ok, detail, ms = _timeit(_check)
    report.add("配置加载", ok, detail, ms)


def run_smoke(base_url: str = "http://127.0.0.1:8000", output_path: Optional[str] = None) -> SmokeReport:
    """执行完整烟雾测试并输出报告"""
    from datetime import datetime

    report = SmokeReport(started_at=datetime.now().isoformat(timespec="seconds"))
    log.info("=== 烟雾测试开始 ===")

    check_config(report)
    check_db_connections(report)
    check_services(report)
    check_api_endpoints(report, base_url=base_url)

    report.finished_at = datetime.now().isoformat(timespec="seconds")
    passed = sum(1 for r in report.results if r.success)
    total = len(report.results)
    log.info(f"=== 烟雾测试结束: {passed}/{total} 通过 ===")

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)

    return report


def main() -> int:
    report = run_smoke(output_path="logs/smoke/smoke_report.json")
    failed = [r for r in report.results if not r.success]
    for r in report.results:
        marker = "✓" if r.success else "✗"
        print(f"{marker} {r.name} ({r.duration_ms:.1f}ms) {r.detail}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
