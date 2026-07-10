"""差距分析页面"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def render_gap_analysis():
    st.header("📈 能力差距分析与学习路径规划")

    if st.session_state.get("resume_profile") is None:
        st.warning("⚠️ 请先上传并解析简历")
        return

    # 目标选择
    target = st.selectbox(
        "选择目标岗位（或留空做全面分析）",
        options=["全面分析", "大模型应用开发工程师", "AI Agent开发工程师", "RAG系统工程师",
               "NLP算法工程师", "计算机视觉工程师", "推荐系统工程师",
               "MLOps工程师", "云原生开发工程师", "DevOps/SRE工程师",
               "后端开发工程师(Java)", "后端开发工程师(Go)", "全栈开发工程师",
               "数据仓库工程师", "实时计算工程师", "区块链开发工程师"],
        format_func=lambda x: x.split("(")[0].strip() if "(" in x else x
    )

    if st.button("🔍 开始差距分析", type="primary", use_container_width=True):
        _run_gap_analysis(target)

    if "gap_result" in st.session_state:
        _render_gap_result()


def _run_gap_analysis(target: str):
    with st.spinner("正在分析能力差距..."):
        try:
            profile = st.session_state["resume_profile"]
            resume_dict = {
                "skills": profile.skills_explicit + profile.skills_implicit,
                "implicit_skills": profile.skills_implicit,
            }

            from agents.gap_analyzer import GapAnalyzerAgent
            analyzer = GapAnalyzerAgent()

            actual_target = None if target == "全面分析" else target
            result = analyzer.analyze_gaps(resume_dict, actual_target) if actual_target else analyzer.full_gap_analysis(resume_dict)

            st.session_state["gap_result"] = result
            st.success("✅ 差距分析完成！")
        except Exception as e:
            st.error(f"分析失败: {e}")


def _render_gap_result():
    result = st.session_state["gap_result"]

    # 如果是全面分析
    if "best_matches" in result:
        st.subheader("🎯 最适合你的前5名岗位")
        for m in result.get("best_matches", [])[:5]:
            rate = m.get("match_rate", 0)
            st.progress(rate, text=f"**{m.get('target_job', '')}** — 匹配度 {rate:.0%}")
        return

    # 单目标分析
    target = result.get("target_job", "未知岗位")
    rate = result.get("overall_match_rate", 0)

    # 总体匹配度
    st.metric(f"与「{target}」的匹配度", f"{rate:.1%}")
    st.write(result.get("summary", ""))

    # 技能对比
    col1, col2 = st.columns(2)
    with col1:
        st.subheader(f"✅ 已掌握 ({len(result.get('matched_skills', []))})")
        for s in result.get("matched_skills", []):
            st.success(f"`{s}`")

    with col2:
        st.subheader(f"❌ 关键差距 ({len(result.get('missing_critical', []))})")
        for s in result.get("missing_critical", []):
            st.error(f"`{s}`")

        if result.get("missing_optional"):
            st.subheader(f"📝 可选补充 ({len(result['missing_optional'])})")
            for s in result["missing_optional"]:
                st.write(f"- `{s}`")

    # 学习路径
    st.markdown("---")
    st.subheader("📚 推荐学习路径")
    path = result.get("learning_path", {})
    if isinstance(path, dict) and "steps" in path:
        steps = path["steps"]
        total_weeks = path.get("total_weeks", 0)
        total_months = path.get("total_months", 0)

        st.info(f"预计总学习周期: **{total_weeks}周** (约 **{total_months}个月**)")

        for step in steps:
            with st.expander(f"第{step['step']}步: **{step['skill']}** ({step['duration_weeks']}周, 难度{step['difficulty']}/10)"):`
                c1, c2 = st.columns(2)
                c1.write(f"**前置要求:** {', '.join(step.get('prerequisites', []) or ['无'])}")
                c2.write(f"**ROI评分:** {step.get('roi_estimate', 0):.1f}")
                st.write(f"**推荐资源:** {', '.join(step.get('resources', [])[:3])}")

        # ROI分析
        st.markdown("---")
        st.subheader("💰 学习投入产出分析")
        roi = result.get("roi_analysis", {})
        st.write(f"**总投入:** 约 **{roi.get('total_effort_months', 0)}个月**")
        st.write(f"**预期薪资涨幅:** 约 **{roi.get('expected_salary_increase_pct', 0)}%**")

        priority = roi.get("recommendation_priority", [])
        if priority:
            st.write("**优先学习顺序:** " + " → ".join([f"`{p}`" for p in priority]))
