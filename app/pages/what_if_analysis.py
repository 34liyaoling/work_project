"""What-If假设分析页面"""
import streamlit as st
import pandas as pd


def render_what_if_analysis():
    st.header("⚡ What-If 假设性分析")
    st.markdown("**如果我学习了某些新技能，我的匹配结果会如何变化？**")

    if st.session_state.get("resume_profile") is None:
        st.warning("⚠️ 请先上传并解析简历")
        return

    # 当前技能概览
    profile = st.session_state["resume_profile"]
    current_skills = profile.skills_explicit + profile.skills_implicit
    st.write(f"你当前的技能组合 (**{len(current_skills)}** 项):")
    st.write(", ".join([f"`{s}`" for s in current_skills[:15]]))

    st.markdown("---")

    # 选择要学习的技能
    st.subheader("➕ 选择你想学习的技能")

    suggested = ["LangChain", "RAG系统设计", "AI Agent开发", "Kubernetes", "Docker",
                "PyTorch", "Prompt Engineering", "微服务架构", "Go语言", "Flink"]

    added_skills = st.multiselect(
        "假设你已经掌握了以下技能:",
        options=suggested + current_skills,
        default=[]
    )

    # 过滤掉已有的
    new_skills = [s for s in added_skills if s not in current_skills]

    if not new_skills:
        st.info("请选择至少一项你尚未掌握的技能")
        return

    col1, col2 = st.columns([3, 1])
    with col1:
        st.write(f"将添加 **{len(new_skills)}** 项新技能: " + ", ".join([f"`{s}`" for s in new_skills]))
    with col2:
        if st.button("🔮 运行模拟", type="primary", use_container_width=True):
            _run_whatif(new_skills)

    if "whatif_result" in st.session_state:
        _render_whatif_result(new_skills)


def _run_whatif(skills):
    with st.spinner("正在模拟匹配变化..."):
        try:
            profile = st.session_state["resume_profile"]
            resume_dict = {
                "skills": profile.skills_explicit + profile.skills_implicit,
                "implicit_skills": profile.skills_implicit,
            }

            from agents.matching_agent import MatchingAgent
            matcher = MatchingAgent()
            result = matcher.simulate_what_if(resume_dict, skills)

            st.session_state["whatif_result"] = result
            st.success("✅ 模拟完成！")
        except Exception as e:
            st.error(f"模拟失败: {e}")


def _render_whatif_result(added_skills):
    result = st.session_state["whatif_result"]

    # 对比展示
    compare_col1, compare_col2 = st.columns(2)

    with compare_col1:
        st.subheader("📊 变化前 (原始)")
        orig = result.get("original_top3", [])
        for item in orig[:3]:
            score = item.get("match_score", 0)
            st.progress(score, text=f"**{item.get('job_title', '')}** ({score:.0%})")

    with compare_col2:
        st.subheader("🚀 变化后 (学习后)")
        enh = result.get("enhanced_top3", [])
        for item in enh[:3]:
            score = item.get("match_score", 0)
            st.progress(score, text=f"**{item.get('job_title', '')}** ({score:.0%})")

    # 对比总结
    comp = result.get("comparison", {})
    st.markdown("---")

    c1, c2, c3 = st.columns(3)
    unlocked = comp.get("new_unlocked_jobs", [])
    c1.metric("解锁新岗位", f"{len(unlocked)} 个")
    improved = comp.get("improved_jobs", [])
    c2.metric("提升匹配的岗位", f"{len(improved)} 个")
    avg_delta = comp.get("score_change_avg", 0)
    sign = "+" if avg_delta > 0 else ""
    c3.metric("平均分变化", f"{sign}{avg_delta:.1%}")

    if unlocked:
        st.success(f"🎉 学习这些技能后，你可以解锁: **{', '.join(unlocked[:5])}**")

    rec = result.get("recommendation", "")
    if rec:
        st.info(rec)
