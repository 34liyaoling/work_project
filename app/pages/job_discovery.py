"""新岗位发现页面"""
import streamlit as st
import pandas as pd
import plotly.express as px


def render_job_discovery():
    st.header("🔮 新岗位发现与定义")
    st.markdown("基于**新兴技能聚类**和**市场趋势信号**，自动发现潜在的新兴岗位")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.info("""
        **发现机制:**
        1. 📈 检测高频增长的新兴技能
        2. 🔗 聚类分析技能共现模式
        3. ⭕ 定位"有技能簇无对应岗位"的空白
        4. 🤖 LLM生成标准化岗位定义
        5. ✅ 多源交叉验证确认
        """)

    with col2:
        if st.button("🚀 开始发现新岗位", type="primary", use_container_width=True):
            _run_discovery()

    st.markdown("---")

    # 已发现的候选岗位
    if "discovered_jobs" in st.session_state:
        _show_candidates()


def _run_discovery():
    """运行岗位发现"""
    with st.spinner("正在分析技术趋势，发现新兴岗位..."):
        try:
            from agents.data_collector import DataCollectorAgent
            from agents.job_discovery import JobDiscoveryAgent

            collector = DataCollectorAgent()
            collection = collector.collect_all_sources()

            discoverer = JobDiscoveryAgent()
            candidates = discoverer.discover_new_jobs(collection["processed_data"])

            st.session_state["discovered_jobs"] = candidates
            st.success(f"✅ 发现 **{len(candidates)}** 个候选新岗位！")
        except Exception as e:
            st.error(f"发现过程出错: {e}")


def _show_candidates():
    """显示候选岗位"""
    candidates = st.session_state["discovered_jobs"]

    for i, cand in enumerate(candidates):
        with st.expander(f"🆕 候选 #{i+1}: **{cand.suggested_title}** (置信度: {cand.confidence:.0%})"):
            c1, c2 = st.columns(2)
            c1.write(f"**核心技能簇:** {', '.join(cand.skill_cluster[:8])}")
            c2.write(f"**增长率:** {cand.growth_rate:.0%} | **来源:** {', '.join(cand.evidence_sources)}")

            if cand.similar_existing_jobs:
                st.write(f"**相似已有岗位:** {', '.join(cand.similar_existing_jobs)}")
            st.write(f"**发现原因:** {cand.discovery_reason}")

            if cand.suggested_definition:
                definition = cand.suggested_definition
                st.json(definition)

            # 审核按钮
            acol1, acol2 = st.columns(2)
            if acol1.button(f"✅ 批准入库", key=f"approve_{i}", type="primary"):
                from agents.job_discovery import JobDiscoveryAgent
                discoverer = JobDiscoveryAgent()
                if discoverer.approve_candidate(cand.suggested_title):
                    st.success(f"岗位「{cand.suggested_title}」已批准入库！")
                    st.rerun()
            if acol2.button(f"❌ 驳回", key=f"reject_{i}"):
                st.warning(f"已驳回候选: {cand.suggested_title}")
