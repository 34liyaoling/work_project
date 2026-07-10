"""数据驾驶舱页面"""

import json
import logging
import time
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

logger = logging.getLogger(__name__)


def render_dashboard():
    st.header("📊 全景数据驾驶舱")

    # 初始化按钮
    col_init = st.columns(1)
    with col_init[0]:
        if st.button("🔄 一键初始化系统（首次使用必点）", type="primary", use_container_width=True):
            with st.spinner("正在初始化图谱、向量库和示例数据..."):
                _do_init()
                st.success("✅ 系统初始化完成！", icon="🎉")
                st.rerun()

    # 顶部KPI指标
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

    with kpi_col1:
        st.metric("📊 图谱节点总数", value=_get_stat("nodes", 128), delta="+12 本周")
    with kpi_col2:
        st.metric("💼 在线岗位数", value=_get_stat("jobs", 26), delta="+3 本月")
    with kpi_col3:
        st.metric("🛠 技能覆盖数", value=_get_stat("skills", 156), delta="+18 本月")
    with kpi_col4:
        st.metric("🔗 关系数量", value=_get_stat("relations", 342), delta="+45 本周")

    st.markdown("---")

    # 数据采集状态
    _render_collection_status()

    # 第二行：图表区域
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("🏆 技能热度 Top 15")
        skill_df = _get_skill_trend_data()
        fig = px.bar(
            skill_df.head(15), x="trend_score", y="name",
            orientation="h", color="trend_score",
            color_continuous_scale="Viridis",
            title="技术趋势热度排名",
            labels={"name": "技能", "trend_score": "趋势分数"},
        )
        fig.update_layout(height=450, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig, use_container_width=True)

    with chart_col2:
        st.subheader("📋 各领域岗位分布")
        domain_df = _get_domain_distribution()
        fig = go.Figure(data=[go.Pie(
            labels=domain_df["domain"], values=domain_df["count"],
            hole=0.4, textinfo="label+percent",
            marker_colors=px.colors.qualitative.Set3,
        )])
        fig.update_layout(height=450, title_text="岗位领域分布", showlegend=True)
        st.plotly_chart(fig, use_container_width=True)

    # 第三行：更多图表
    row3_col1, row3_col2, row3_col3 = st.columns(3)

    with row3_col1:
        st.subheader("💰 薪资分布")
        salary_df = _get_salary_data()
        fig = px.box(
            salary_df, x="domain", y="avg_salary",
            color="domain", title="各领域薪资分布(K/月)",
            labels={"avg_salary": "平均薪资(K)", "domain": "领域"},
        )
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

    with row3_col2:
        st.subheader("📍 城市需求热力")
        city_df = _get_city_data()
        fig = px.bar(
            city_df, x="count", y="city", orientation="h",
            color="count", title="各城市岗位需求",
            labels={"count": "岗位数量", "city": "城市"},
            color_continuous_scale="Blues",
        )
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

    with row3_col3:
        st.subheader("📈 技术生命周期")
        lifecycle_df = _get_lifecycle_data()
        fig = px.scatter(
            lifecycle_df, x="age_months", y="demand_index",
            size="skill_count", color="stage",
            hover_name="category", size_max=50,
            title="技术生命周期定位",
            labels={"age_months": "存在时间(月)", "demand_index": "需求指数", "stage": "阶段"},
        )
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

    # 第四行：最近活动
    st.subheader("🕐 最近系统活动")
    activity_data = [
        {"time": "10:32", "event": "📊 数据采集完成", "detail": "从6个数据源采集了89条记录"},
        {"time": "10:28", "event": "🔮 发现候选新岗位", "detail": "\"AI Agent开发工程师\" 待审核"},
        {"time": "10:15", "event": "📄 解析简历", "detail": "张三_简历.pdf → 提取23项技能"},
        {"time": "09:50", "event": "🎯 完成匹配分析", "detail": "最佳匹配: 大模型应用工程师 (82%)"},
        {"time": "09:30", "event": "🛡 幻觉防控扫描", "detail": "检测到3条低置信度条目，已入审核队列"},
    ]
    act_df = pd.DataFrame(activity_data)
    st.dataframe(act_df, use_container_width=True, hide_index=True)


def _get_stat(key: str, default: int) -> int:
    """获取统计数据（带缓存）"""
    cache_key = f"stat_{key}"
    if cache_key not in st.session_state:
        try:
            from core.graph_service import get_graph_service
            graph = get_graph_service()
            if graph.is_connected:
                stats = graph.get_graph_stats()
                mapping = {"nodes": "total_nodes", "jobs": "job_nodes", "skills": "skill_nodes", "relations": "total_relations"}
                st.session_state[cache_key] = stats.get(mapping.get(key, key), default)
            else:
                st.session_state[cache_key] = default
        except:
            st.session_state[cache_key] = default
    return st.session_state[cache_key]


def _get_skill_trend_data() -> pd.DataFrame:
    """获取技能趋势数据"""
    data = [
        ("Python", 0.92), ("LangChain", 0.89), ("RAG系统设计", 0.87),
        ("PyTorch", 0.85), ("AI Agent开发", 0.83), ("Kubernetes", 0.78),
        ("Docker", 0.75), ("Redis", 0.73), ("Prompt Engineering", 0.71),
        ("微服务架构", 0.69), ("MySQL", 0.67), ("Go语言", 0.65),
        ("React/Vue", 0.63), ("Spark", 0.58), ("Flink", 0.55),
        ("DeepSpeed", 0.52), ("LoRA", 0.50), ("vLLM", 0.48),
        ("Function Calling", 0.46), ("多智能体协作", 0.44),
    ]
    return pd.DataFrame(data, columns=["name", "trend_score"]).sort_values("trend_score", ascending=False)


def _get_domain_distribution() -> pd.DataFrame:
    """获取领域分布数据"""
    return pd.DataFrame([
        ("人工智能", 9), ("软件开发", 5), ("大数据", 4),
        ("云计算/DevOps", 3), ("区块链/Web3", 1), ("网络安全", 1),
    ], columns=["domain", "count"])


def _get_salary_data() -> pd.DataFrame:
    """获取薪资数据"""
    data = []
    domains = ["人工智能", "大数据", "云计算", "软件开发", "DevOps", "区块链"]
    for d in domains:
        base = 25 if d != "人工智能" else 30
        for i in range(5):
            data.append({"domain": d, "avg_salary": base + __import__("random").randint(-5, 15)})
    return pd.DataFrame(data)


def _get_city_data() -> pd.DataFrame:
    """获取城市需求数据"""
    return pd.DataFrame([
        ("北京", 320), ("上海", 280), ("深圳", 250), ("杭州", 180),
        ("成都", 120), ("广州", 110), ("南京", 90), ("武汉", 80),
    ], columns=["city", "count"])


def _get_lifecycle_data() -> pd.DataFrame:
    """获取生命周期数据"""
    import random
    stages = ["emerging", "growing", "mature", "declining"]
    categories = ["LLM应用", "RAG系统", "AI Agent", "云原生", "微服务", "大数据", "区块链"]
    data = []
    for cat in categories:
        stage = random.choice(stages)
        data.append({
            "category": cat, "stage": stage,
            "age_months": random.randint(3, 60),
            "demand_index": random.uniform(0.3, 1.0) * (4 - stages.index(stage)),
            "skill_count": random.randint(5, 20),
        })
    return pd.DataFrame(data)


def _render_collection_status():
    """渲染数据采集状态面板"""
    st.subheader("📡 数据采集状态")

    # 初始化session state中的采集状态
    if "collection_stats" not in st.session_state:
        st.session_state.collection_stats = _load_collection_stats()

    stats = st.session_state.collection_stats

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        last_time = stats.get("last_collection", "尚未采集")
        if last_time and last_time != "尚未采集":
            try:
                dt = datetime.fromisoformat(last_time)
                last_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                pass
        st.metric("🕐 最近采集", last_time)

    with col2:
        total = stats.get("total_collected", 0)
        st.metric("📦 累计采集", total)

    with col3:
        by_source = stats.get("by_source", {})
        source_count = len(by_source)
        st.metric("🔀 数据源数", source_count)

    with col4:
        sources_detail = " | ".join([f"{k}:{v}" for k, v in by_source.items()]) if by_source else "无"
        st.caption(f"各源详情: {sources_detail}")

    # 采集控制按钮
    btn_col1, btn_col2 = st.columns([1, 4])
    with btn_col1:
        if st.button("🚀 一键采集数据", type="primary", use_container_width=True):
            with st.spinner("正在从各数据源采集数据..."):
                result = _trigger_collection()
                if result:
                    st.session_state.collection_stats = result["stats"]
                    st.success(
                        f"✅ 采集完成！共采集 {result['total_raw']} 条，"
                        f"去重后 {result['total_deduplicated']} 条"
                    )
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ 采集失败，请检查网络连接")

    with btn_col2:
        st.caption(
            "点击按钮从搜索引擎采集最新岗位数据。"
            "如网络不可用，将自动使用内置演示数据。"
        )

    st.markdown("---")


def _load_collection_stats() -> dict:
    """从session或数据库加载采集统计"""
    try:
        from agents.data_collector import DataCollectorAgent
        collector = DataCollectorAgent()
        return collector.get_collection_stats()
    except Exception as e:
        logger.warning(f"加载采集统计失败: {e}")
        return {
            "total_collected": 0,
            "by_source": {},
            "last_collection": None,
        }


def _trigger_collection() -> dict:
    """触发一次数据采集"""
    try:
        from agents.data_collector import DataCollectorAgent
        from agents.graph_builder import GraphBuilderAgent

        collector = DataCollectorAgent()
        collection = collector.collect_all_sources()

        processed_data = collection.get("processed_data", [])
        if processed_data:
            builder = GraphBuilderAgent()
            builder.build_from_data(processed_data)

        return collection
    except Exception as e:
        logger.error(f"数据采集失败: {e}")
        return None


def _do_init():
    """执行系统初始化"""
    from agents.graph_builder import GraphBuilderAgent
    from agents.data_collector import DataCollectorAgent

    builder = GraphBuilderAgent()
    result = builder.initialize_full_graph()

    # 采集并构建
    collector = DataCollectorAgent()
    collection = collector.collect_all_sources()
    builder.build_from_data(collection["processed_data"])

    st.session_state["initialized"] = True
