#!/usr/bin/env python
"""一键启动脚本 - 支持 Streamlit 前端 / Vue 3 前端 / 后端API"""

import os
import sys
import subprocess
import threading
import time
import webbrowser

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)


def print_banner():
    banner = """
╔═══════════════════════════════════════════════════════════╗
║                                                               ║
║     🧠  新一代信息技术全景图谱系统  v1.0                  ║
║                                                               ║
║     Multi-Agent Knowledge Graph System                       ║
║                                                               ║
║     ┌─────────────────────────────────────────────┐           ║
║     │  网络数据采集 → 动态知识图谱 → 智能匹配      │           ║
║     └─────────────────────────────────────────────┘           ║
║                                                               ║
╚═══════════════════════════════════════════════════════════╝
"""
    print(banner)


def check_env():
    """检查环境变量"""
    env_file = os.path.join(PROJECT_ROOT, ".env")
    if not os.path.exists(env_file):
        print("[INFO] .env 文件不存在，创建默认配置")
        default_env = """
# ===== 讯飞星火大模型配置 =====
SPARK_API_KEY=your-spark-api-key-here
SPARK_API_BASE=https://spark-api-open.xf-yun.com/v1
SPARK_CHAT_MODEL=generalv3.5
SPARK_EMBEDDING_MODEL=generalv3.5

# ===== Neo4j 图数据库 =====
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=kg_password_2024

# ===== 数据采集 =====
DATA_ENABLE_PLAYWRIGHT=false
"""
        with open(env_file, "w", encoding="utf-8") as f:
            f.write(default_env)
        print(f"[INFO] 已创建默认 .env 文件: {env_file}")


def install_dependencies():
    """检查并安装Python依赖"""
    req_file = os.path.join(PROJECT_ROOT, "requirements.txt")
    if not os.path.exists(req_file):
        print("[WARN] requirements.txt 不存在，跳过依赖检查")
        return

    print("[INFO] 检查Python依赖...")
    try:
        import importlib
        required = ["streamlit", "fastapi", "uvicorn", "pydantic",
                    "neo4j", "chromadb", "langchain", "openai", "pandas", "plotly"]
        missing = []
        for pkg in required:
            try:
                importlib.import_module(pkg.replace("-", "_"))
            except ImportError:
                missing.append(pkg)

        if missing:
            print(f"[WARN] 缺少依赖: {', '.join(missing)}")
            print("[INFO] 正在安装依赖...")
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", req_file], check=False)
            print("[INFO] 依赖安装完成")
        else:
            print("[OK] 所有必要依赖已安装")
    except Exception as e:
        print(f"[WARN] 依赖检查异常: {e}")


def start_api_server():
    """启动FastAPI后端"""
    print("[API] 启动 FastAPI 后端服务 (端口 8000)...")
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "backend.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload",
    ])


def start_streamlit():
    """启动Streamlit前端"""
    print("[WEB] 启动 Streamlit 前端 (端口 8501)...")
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        "app/main.py",
        "--server.port", "8501",
        "--server.address", "localhost",
    ])


def start_vue_dev():
    """启动Vue 3开发服务器"""
    print("[VUE] 启动 Vue 3 开发服务器 (端口 3000)...")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    subprocess.run([npm_cmd, "run", "dev"], cwd=os.path.join(PROJECT_ROOT, "frontend"))


def main():
    print_banner()
    check_env()
    install_dependencies()

    print("\n" + "="*60)
    print("🚀 启动选项:")
    print("="*60)
    print("  1. 完整模式 (Vue3前端 + 后端API)   [推荐 - AntV G6 + ECharts]")
    print("  2. Streamlit 前端 + 后端API         [原版方案]")
    print("  3. 仅 Vue3 前端开发服务器           [需后端已在运行]")
    print("  4. 仅后端API (FastAPI)              [配合Vue前端使用]")
    print("  5. Docker模式 (docker-compose up)")
    print("-"*60)
    print("  💡 数据来源: 网络搜索引擎 (Bing/DuckDuckGo) + 招聘网站爬虫")
    print("="*60)

    choice = input("\n请选择启动模式 [1/2/3/4/5, 默认1]: ").strip() or "1"

    if choice == "1":
        api_thread = threading.Thread(target=start_api_server, daemon=True)
        api_thread.start()
        time.sleep(3)

        url = "http://localhost:3000"
        print(f"\n✅ 系统就绪! 打开浏览器访问: {url}")
        webbrowser.open(url)

        start_vue_dev()

    elif choice == "2":
        api_thread = threading.Thread(target=start_api_server, daemon=True)
        api_thread.start()
        time.sleep(3)

        url = "http://localhost:8501"
        print(f"\n✅ 系统就绪! 打开浏览器访问: {url}")
        webbrowser.open(url)

        start_streamlit()

    elif choice == "3":
        url = "http://localhost:3000"
        print(f"\n✅ 启动Vue前端: {url}")
        webbrowser.open(url)
        start_vue_dev()

    elif choice == "4":
        print("\n✅ 启动后端API: http://localhost:8000")
        print("   API文档: http://localhost:8000/docs")
        start_api_server()

    elif choice == "5":
        print("\n✅ 使用Docker启动...")
        subprocess.run(["docker-compose", "up", "-d"], cwd=PROJECT_ROOT)
        print("   前端(Streamlit): http://localhost:8501")
        print("   API:             http://localhost:8000")
        print("   Neo4j:           http://localhost:7474")

        time.sleep(5)
        webbrowser.open("http://localhost:8501")
        start_streamlit()

    else:
        print(f"未知选项: {choice}, 默认启动完整模式")
        api_thread = threading.Thread(target=start_api_server, daemon=True)
        api_thread.start()
        time.sleep(3)
        start_vue_dev()


if __name__ == "__main__":
    main()
