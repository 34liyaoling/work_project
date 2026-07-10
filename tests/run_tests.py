"""一键测试运行脚本 - 自动发现、运行所有测试、汇总结果、生成覆盖率报告"""

import sys
import os
import subprocess
import time
from pathlib import Path

# 确保项目根目录在 Python 路径中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def print_header(text: str):
    """打印带格式的标题"""
    width = 70
    print()
    print("=" * width)
    print(f"  {text}")
    print("=" * width)


def run_tests() -> bool:
    """运行所有测试并返回是否全部通过"""
    print_header("📦 知识图谱系统 - 自动化测试套件")
    print(f"  项目根目录: {PROJECT_ROOT}")
    print(f"  开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 设置 pytest 参数
    pytest_args = [
        sys.executable, "-m", "pytest",
        os.path.join(PROJECT_ROOT, "tests"),
        "-v",                    # 详细输出
        "--tb=short",           # 简短回溯
        "--strict-markers",     # 严格标记
        "-p", "no:cacheprovider",  # 禁用缓存
        "--ignore=" + os.path.join(PROJECT_ROOT, "tests", "evaluation"),  # 跳过评测目录
    ]

    # 检查是否安装了 pytest-cov
    coverage_available = False
    try:
        import pytest_cov
        coverage_available = True
        print("  ✅ pytest-cov 已安装，将生成覆盖率报告")
    except ImportError:
        print("  ⚠️  pytest-cov 未安装，跳过覆盖率分析")
        print("     安装: pip install pytest-cov")
        print()

    if coverage_available:
        report_dir = os.path.join(PROJECT_ROOT, "tests", "coverage_reports")
        os.makedirs(report_dir, exist_ok=True)
        pytest_args.extend([
            "--cov=" + os.path.join(PROJECT_ROOT, "core"),
            "--cov=" + os.path.join(PROJECT_ROOT, "models"),
            "--cov-report=term",
            f"--cov-report=html:{report_dir}",
            "--cov-fail-under=60",
            "--ignore=" + os.path.join(PROJECT_ROOT, "tests", "test_agents.py"),
            "--ignore=" + os.path.join(PROJECT_ROOT, "tests", "test_db.py"),
            "--ignore=" + os.path.join(PROJECT_ROOT, "tests", "evaluation"),
        ])

    print("  运行命令:")
    print(f"    {' '.join(pytest_args)}")
    print()

    start_time = time.time()
    result = subprocess.run(pytest_args, capture_output=False, cwd=PROJECT_ROOT)
    elapsed = time.time() - start_time

    print()
    print("-" * 70)

    if result.returncode == 0:
        print(f"  ✅ 所有测试通过！耗时: {elapsed:.1f} 秒")
        if coverage_available:
            print(f"  📊 HTML 覆盖率报告: {os.path.join(report_dir, 'index.html')}")
        return True
    else:
        print(f"  ❌ 测试未全部通过 (退出码: {result.returncode}) 耗时: {elapsed:.1f} 秒")
        return False


def collect_test_summary() -> dict:
    """收集测试汇总信息（不运行测试，只分析文件结构）"""
    tests_dir = os.path.join(PROJECT_ROOT, "tests")
    test_files = sorted(Path(tests_dir).glob("test_*.py"))

    summary = {
        "total_files": 0,
        "test_files": [],
        "estimated_test_count": 0,
    }

    for f in test_files:
        if f.name == "run_tests.py":
            continue
        summary["total_files"] += 1
        summary["test_files"].append(f.name)

        # 估算测试数量（每个以 test_ 开头的方法算一个）
        with open(f, "r", encoding="utf-8") as fh:
            content = fh.read()
            test_count = content.count("def test_")
            summary["estimated_test_count"] += test_count

    return summary


def print_summary():
    """打印测试文件结构摘要"""
    summary = collect_test_summary()
    print_header("📋 测试文件结构")
    print(f"  测试文件总数: {summary['total_files']}")
    print(f"  估算测试总数: {summary['estimated_test_count']}")
    print()
    for fname in summary["test_files"]:
        print(f"    📄 {fname}")
    print()
    if summary["estimated_test_count"] > 0:
        print(f"  🎯 共 {summary['estimated_test_count']}+ 个测试用例")


if __name__ == "__main__":
    print_summary()
    print()
    success = run_tests()
    print()
    sys.exit(0 if success else 1)
