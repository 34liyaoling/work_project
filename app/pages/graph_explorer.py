"""图谱浏览器页面"""
import streamlit as st
import pandas as pd


def render_graph_explorer():
    st.header("🔍 知识图谱浏览器")
    st.markdown("交互式浏览**动态知识图谱**，探索技能、岗位、领域之间的关系网络")

    # 搜索框
    search_term = st.text_input("🔎 搜索节点（技能名/岗位名/领域名）", placeholder="例如: Python, AI工程师...")

    # 过滤选项
    col1, col2, col3 = st.columns(3)
    node_type = col1.selectbox("节点类型", ["全部", "技能", "岗位", "领域"])
    domain_filter = col2.selectbox("领域过滤", ["全部", "人工智能", "大数据", "云计算", "软件开发", "DevOps"])
    relation_type = col3.selectbox("关系类型", ["全部", "需要", "偏好", "相似于", "属于", "演进为"])

    # 查询按钮
    if st.button("🔍 查询图谱", type="primary"):
        _execute_query(search_term, node_type, domain_filter, relation_type)

    # 快捷操作
    st.markdown("---")
    st.subheader("⚡ 快捷操作")
    quick_col1, quick_col2, quick_col3 = st.columns(3)
    with quick_col1:
        if st.button("📊 查看图谱统计"):
            _show_stats()
    with quick_col2:
        if st.button("🔗 查看热门关系"):
            _show_popular_relations()
    with quick_col3:
        if st.button("🌳 查看技能树"):
            _show_skill_tree()

    # 结果展示区
    if "graph_query_results" in st.session_state:
        _display_results()


def _execute_query(term, ntype, domain, reltype):
    """执行图谱查询"""
    try:
        from core.graph_service import get_graph_service
        graph = get_graph_service()

        if term:
            # 搜索相关节点
            cypher = f"""
            MATCH (n) WHERE n.name CONTAINS $term
            OPTIONAL MATCH (n)-[r]-(related)
            RETURN n.name as name, labels(n)[0] as type,
                   type(r) as relation, related.name as related_name
            LIMIT 30
            """
            results = graph.execute_query(cypher, {"term": term})
            st.session_state["graph_query_results"] = results
        elif reltype != "全部":
            cypher = f"MATCH (a)-[:{reltype}]->(b) RETURN a.name, type(r), b.name LIMIT 30"
            results = graph.execute_query(cypher)
            st.session_state["graph_query_results"] = results
        else:
            _show_stats()
    except Exception as e:
        st.error(f"查询失败: {e}")


def _show_stats():
    """显示图谱统计"""
    try:
        from core.graph_service import get_graph_service
        graph = get_graph_service()
        stats = graph.get_graph_stats()

        st.json(stats)

        # 可视化
        import plotly.graph_objects as go
        fig = go.Figure(data=[go.Bar(
            x=list(stats.keys()), y=list(stats.values()),
            marker_color=px.colors.qualitative.Pastel,
        )])
        fig.update_layout(title="图谱统计概览", height=300)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"获取统计失败: {e}")


def _show_popular_relations():
    """显示热门关系"""
    try:
        from core.graph_service import get_graph_service
        graph = get_graph_service()
        results = graph.execute_query("""
        MATCH ()-[r]->() RETURN type(r) as relation, count(*) as count ORDER BY count DESC LIMIT 10
        """)
        df = pd.DataFrame(results)
        st.dataframe(df, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"查询失败: {e}")


def _show_skill_tree():
    """显示技能树"""
    from models.skill_taxonomy import DOMAINS
    st.json({k: list(v["subcategories"].keys()) for k, v in DOMAINS.items()})


def _display_results():
    """显示查询结果"""
    results = st.session_state["graph_query_results"]
    if not results:
        st.info("无查询结果")
        return

    df = pd.DataFrame(results)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # 简单的网络图可视化
    try:
        import networkx as nx
        G = nx.Graph()
        for r in results[:20]:
            if r.get("name"):
                G.add_node(r["name"], type=r.get("type", "unknown"))
            if r.get("related_name"):
                G.add_edge(r.get("name", ""), r["related_name"], label=r.get("relation", ""))

        if G.number_of_nodes() > 0:
            st.caption(f"📊 展示了 {G.number_of_nodes()} 个节点, {G.number_of_edges()} 条关系的子图预览")

            # 使用pyvis渲染
            try:
                from pyvis.network import Network
                net = Network(height="400px", width="100%", bgcolor="#ffffff", font_color="black")
                net.from_nx(G)
                net.save_graph("temp_graph.html")
                with open("temp_graph.html", "r", encoding="utf-8") as f:
                    html = f.read()
                st.components.v1.html(html, height=400)
            except:
                st.info("安装 pyvis 以启用交互式图谱可视化: pip install pyvis")
    except Exception as e:
        st.debug(f"可视化生成失败: {e}")
