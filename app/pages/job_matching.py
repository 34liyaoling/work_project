"""智能匹配页面"""

import streamlit as st
import pandas as pd
import plotly.express as px


def render_job_matching():
    st.header("🎯 智能岗位匹配")
    st.markdown("基于**混合匹配引擎**（图谱推理 + 向量检索 + LLM排序），为你找到最匹配的岗位")

    # 检查是否有简历
    if st.session_state.get("resume_profile") is None:
        st.warning("⚠️ 请先在「简历分析」页面上传并解析简历")
        if st.button("前往简历分析 →"):
            st.switch_page("pages/resume_analysis.py")
        return

    # 匹配参数设置
    with st.expander("⚙️ 匹配参数设置"):
        col1, col2 = st.columns(2)
        top_n = col1.slider("返回结果数量", min_value=3, max_value=20, value=10)
        domain_filter = col2.multiselect(
            "领域过滤",
            options=["人工智能", "大数据", "云计算", "软件开发", "DevOps", "区块链/Web3"],
            default=[]
        )

    if st.button("🚀 开始匹配分析", type="primary", use_container_width=True):
        with st.spinner("正在运行混合匹配引擎..."):
            _run_matching(top_n)

    # 显示历史结果
    if "match_results" in st.session_state and st.session_state["match_results"]:
        _render_match_results()


def _run_matching(top_n: int = 10):
    """执行匹配"""
    profile = st.session_state["resume_profile"]

    resume_dict = {
        "skills": profile.skills_explicit + profile.skills_implicit,
        "implicit_skills": profile.skills_implicit,
        "embedding": profile.embedding_vector,
        "skills_with_credibility": [s.model_dump() for s in profile.skills_with_credibility],
    }

    try:
        from agents.matching_agent import MatchingAgent
        matcher = MatchingAgent()
        result = matcher.find_matches(resume_dict, top_n=top_n)

        st.session_state["match_results"] = result.get("matches", [])
        st.session_state["match_summary"] = {
            "total_scanned": result.get("total_jobs_scanned", 0),
            "best_match": result.get("best_match"),
        }

        st.success(f"✅ 匹配完成！扫描了 **{result.get('total_jobs_scanned', 0)}** 个岗位，返回 **{len(result.get('matches', []))}** 个最佳匹配")
    except Exception as e:
        st.error(f"匹配过程出错: {e}")


def _render_match_results():
    """渲染匹配结果"""
    results = st.session_state["match_results"]
    summary = st.session_state.get("match_summary", {})

    # 最佳匹配高亮显示
    if summary.get("best_match"):
        best = summary["best_match"]
        st.markdown(f"### 🏆 最佳匹配: **{best['job_title']}** (匹配度 **{best['match_score']:.1%}**)")

        col1, col2, col3 = st.columns(3)
        col1.metric("匹配技能数", len(best.get("matched_skills", [])))
        col2.metric("关键差距", len(best.get("missing_critical", [])))
        col3.metric("可选补充", len(best.get("missing_optional", [])))

        with st.expander("查看详细解释"):
            st.markdown(best.get("explanation", ""))

    st.markdown("---")

    # 所有匹配结果表格
    st.subheader("📋 完整匹配排名")

    display_data = []
    for i, m in enumerate(results):
        display_data.append({
            "排名": i + 1,
            "岗位": m["job_title"],
            "匹配度": f"{m['match_score']:.1%}",
            "技能匹配": f"{m['breakdown'].get('skill', 0):.1%}",
            "图谱关联": f"{m['breakdown'].get('graph', 0):.1%}",
            "语义相似": f"{m['breakdown'].get('vector', 0):.1%}",
            "趋势红利": f"{m['breakdown'].get('trend', 0):.1%}",
            "已匹配技能": ", ".join(m["matched_skills"][:5]),
            "关键差距": ", ".join(m["missing_critical"][:3]) if m["missing_critical"] else "无",
        })

    df = pd.DataFrame(display_data)
    st.dataframe(df, use_container_width=True, hide_index=True,
                 column_config={"排名": st.column_config.TextColumn(width="small")})

    # 匹配度可视化
    if results:
        fig = px.bar(
            x=[r["job_title"] for r in results[:8]],
            y=[r["match_score"] for r in results[:8]],
            color=[r["match_score"] for r in results[:8]],
            color_continuous_scale="RdYlGn",
            range_x=[0, 1],
            title="匹配度对比 (前8名)",
            labels={"x": "岗位", "y": "匹配度"},
        )
        fig.update_layout(height=400, xaxis_tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)

    # 操作按钮
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📈 对最佳匹配做差距分析"):
            st.session_state["gap_target"] = results[0]["job_title"] if results else None
            st.switch_page("pages/gap_analysis.py")
    with col2:
        if st.button("⚡ What-If模拟"):
            st.switch_page("pages/what_if_analysis.py")
