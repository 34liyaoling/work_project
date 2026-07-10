"""系统管理面板"""
import streamlit as st
import pandas as pd


def render_admin_panel():
    st.header("⚙️ 系统管理与配置")

    tab1, tab2, tab3, tab4 = st.tabs(["📊 系统状态", "🔄 数据管理", "🛡 质量控制", "📋 审核队列"])

    with tab1:
        st.subheader("系统组件状态")

        components = [
            ("Neo4j 图数据库", "bolt://localhost:7687", "🟢 已连接" if _check_neo4j() else "🔴 未连接"),
            ("ChromaDB 向量库", "localhost:8001", "🟢 已连接" if _check_chroma() else "🔴 未连接"),
            ("LLM 服务", "OpenAI/Ollama", "🟢 已配置" if _check_llm() else "🔴 未配置"),
            ("数据采集器", "内置", "🟢 就绪"),
            ("智能体系统", "CrewAI", "🟢 就绪"),
        ]

        for name, endpoint, status in components:
            col1, col2, col3 = st.columns([2, 2, 1])
            col1.write(f"**{name}**")
            col2.code(endpoint)
            col3.write(status)

        st.markdown("---")
        st.subheader("本地数据库 (SQLite)")
        try:
            from backend.storage import get_db
            db = get_db()
            db_stats = db.get_db_stats()
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("简历数", db_stats.get("resume_count", 0))
            c2.metric("岗位数", db_stats.get("job_count", 0))
            c3.metric("分析记录", db_stats.get("analysis_count", 0))
            c4.metric("待审核", db_stats.get("pending_audit_count", 0))
            db_size = db_stats.get("db_size_bytes", 0)
            st.caption(f"数据库大小: {db_size / 1024:.1f} KB | 路径: data/kg_system.db")
        except Exception as e:
            st.caption(f"数据库状态: 未初始化 ({e})")

        st.markdown("---")
        if st.button("🔄 一键健康检查", type="primary"):
            _run_health_check()

    with tab2:
        st.subheader("数据管理操作")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("📥 触发数据采集", type="primary"):
                with st.spinner("采集中..."):
                    from agents.data_collector import DataCollectorAgent
                    agent = DataCollectorAgent()
                    result = agent.collect_all_sources()
                    st.json(result.get("stats", {}))

        with c2:
            if st.button("🏗 重建知识图谱"):
                with st.spinner("构建中..."):
                    from agents.graph_builder import GraphBuilderAgent
                    builder = GraphBuilderAgent()
                    result = builder.initialize_full_graph()
                    st.json(result)

        st.markdown("---")
        st.subheader("数据统计")
        try:
            from core.graph_service import get_graph_service
            graph = get_graph_service()
            stats = graph.get_graph_stats()
            st.json(stats)
        except Exception as e:
            st.error(f"获取统计失败: {e}")

    with tab3:
        st.subheader("质量控制")

        if st.button("🛡 运行质量检查", type="primary"):
            with st.spinner("检查中..."):
                from agents.quality_guardian import QualityGuardianAgent
                guardian = QualityGuardianAgent()
                result = guardian.run_full_check()
                st.session_state["quality_report"] = result

        if "quality_report" in st.session_state:
            report = st.session_state["quality_report"]
            st.metric("整体状态", report.get("overall_status", "未知").upper())
            st.metric("发现问题", report.get("issues_found", 0))

            for rec in report.get("recommendations", []):
                st.info(rec)

    with tab4:
        st.subheader("人工审核队列")

        try:
            from core.hallucination_guard import HallucinationGuard
            from core.graph_service import get_graph_service
            guard = HallucinationGuard(get_graph_service())
            queue_status = guard.get_review_queue_status()

            st.json(queue_status)

            pending = guard.review_queue.get_pending()
            if pending:
                st.write(f"待审核: **{len(pending)}** 条")
                for item in pending[:5]:
                    st.code(str(item)[:200])
        except Exception as e:
            st.error(f"获取审核队列失败: {e}")


def _check_neo4j() -> bool:
    try:
        from core.graph_service import get_graph_service
        return get_graph_service().is_connected
    except:
        return False

def _check_chroma() -> bool:
    try:
        from core.vector_service import get_vector_service
        return get_vector_service().is_connected
    except:
        return False

def _check_llm() -> bool:
    try:
        from core.llm_service import get_llm_service
        ok, msg = get_llm_service().test_connection()
        return ok
    except:
        return False

def _run_health_check():
    from agents.quality_guardian import QualityGuardianAgent
    guardian = QualityGuardianAgent()
    result = guardian.run_full_check()
    st.session_state["quality_report"] = result
    st.json(result)
