"""简历分析页面"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def render_resume_analysis():
    st.header("📄 简历深度解析")
    st.markdown("上传简历文件，进行**语义级深度解析**——超越关键词匹配，发现隐含技能、评估可信度、分析项目复杂度")

    # 上传区域
    uploaded_file = st.file_uploader(
        "📁 选择简历文件 (支持 PDF / DOCX / TXT)",
        type=["pdf", "docx", "txt"],
        help="支持多种格式的简历文件，系统将自动进行语义级深度解析"
    )

    if "resume_profile" not in st.session_state:
        st.session_state["resume_profile"] = None
        st.session_state["resume_id"] = None

    if uploaded_file is not None:
        # 保存文件
        import tempfile
        import os
        suffix = os.path.splitext(uploaded_file.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name

        st.info(f"📂 已选择文件: **{uploaded_file.name}** ({len(uploaded_file.getvalue())/1024:.1f} KB)")

        if st.button("🔍 开始解析", type="primary", use_container_width=True):
            with st.spinner("正在进行深度语义解析...这可能需要几秒钟"):
                try:
                    from agents.resume_parser import ResumeParserAgent
                    parser = ResumeParserAgent()
                    profile = parser.parse_resume(tmp_path)

                    st.session_state["resume_profile"] = profile
                    st.session_state["resume_id"] = profile.resume_hash

                    st.success(f"✅ 解析完成！发现 **{len(profile.skills_with_credibility)}** 项技能")
                except Exception as e:
                    st.error(f"解析失败: {e}")

    # 显示解析结果
    profile = st.session_state.get("resume_profile")
    if profile:
        _render_profile_details(profile)


def _render_profile_details(profile):
    """渲染简历详情"""
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 基本信息", "🛠 技能分析", "📂 项目经验", "📊 可信度评估", "🧠 隐含能力"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("姓名", profile.name or "匿名候选人")
            st.metric("工作年限", f"{profile.total_experience_years:.1f} 年")
            st.metric("学历", ", ".join([f"{e.degree}·{e.major}" for e in profile.education]) if profile.education else "未知")
        with col2:
            st.metric("技术水平", profile.overall_technical_level.upper())
            st.metric("技能多样性", f"{profile.diversity_score:.1%}")
            st.metric("成长潜力", f"{profile.growth_potential:.1%}")

        if profile.work_experience:
            st.subheader("💼 工作经历")
            for exp in profile.work_experience:
                with st.expander(f"**{exp.company}** — {exp.position}"):
                    st.write(f"📅 {exp.start_date or '?'} ~ {exp.end_date or '至今'}")
                    st.write(exp.description or "暂无描述")

    with tab2:
        explicit = profile.skills_explicit
        implicit = profile.skills_implicit

        c1, c2 = st.columns(2)
        with c1:
            st.subheader(f"✅ 显式技能 ({len(explicit)})")
            for skill in explicit:
                st.write(f"- `{skill}`")

        with c2:
            st.subheader(f"🔮 隐含推断技能 ({len(implicit)})")
            for skill in implicit:
                st.write(f"- 🔍 `{skill}` *(由项目经验推断)*")

        # 技能雷达图
        if profile.skills_with_credibility:
            st.subheader("🎯 技能可信度雷达")
            top_skills = sorted(profile.skills_with_credibility,
                              key=lambda x: x.credibility_score, reverse=True)[:10]

            fig = go.Figure(go.Scatterpolar(
                r=[s.credibility_score * 10 for s in top_skills],
                theta=[s.skill_name for s in top_skills],
                fill='toself',
                name='可信度'
            ))
            fig.update_layout(polar=dict(radial_axis=dict(visible=True, range=[0, 10])),
                             title="前10项技能可信度雷达图", height=400)
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        if not profile.projects:
            st.info("未检测到项目经验信息")
        else:
            for i, proj in enumerate(profile.projects):
                with st.expander(f"📂 项目{i+1}: **{proj.project_name}**"):
                    cols = st.columns(3)
                    cols[0].metric("复杂度", f"{proj.complexity_score:.1f}/10")
                    cols[1].metric("技术栈规模", f"{len(proj.technologies_used)}项")
                    cols[2].metric("风险标记", f"{len(proj.red_flags)}项")

                    if proj.technologies_used:
                        st.write("**技术栈:** " + " · ".join([f"`{t}`" for t in proj.technologies_used]))
                    st.write(proj.description)

                    if proj.red_flags:
                        st.warning("⚠️ **注意事项:** " + "; ".join(proj.red_flags))
                    if proj.strengths:
                        st.success("✨ **亮点:** " + "; ".join(proj.strengths))

    with tab4:
        from core.credibility_scorer import CredibilityScorer
        scorer = CredibilityScorer()
        overall = scorer.get_overall_credibility(profile.skills_with_credibility)

        st.metric("综合可信度评分", f"{overall['overall_score']:.2f}/1.00")

        st.subheader("📊 可信度分布")
        level_data = []
        for level, info in overall.get("breakdown", {}).items():
            level_data.append({
                "级别": level.replace("_", " ").title(),
                "数量": info.get("count", 0),
                "平均分": f"{info.get('avg_score', 0):.2f}",
            })
        st.dataframe(pd.DataFrame(level_data), use_container_width=True, hide_index=True)

        # 详细表格
        st.subheader("📝 详细技能评估")
        skill_data = [{
            "技能名称": s.skill_name,
            "可信度级别": s.credibility_level.value,
            "得分": f"{s.credibility_score:.2f}",
            "熟练度": f"{s.proficiency_level}/10" if s.proficiency_level else "-",
        } for s in sorted(profile.skills_with_credibility, key=lambda x: x.credibility_score, reverse=True)]
        st.dataframe(pd.DataFrame(skill_data), use_container_width=True, hide_index=True)

    with tab5:
        st.subheader("🧠 隐含能力洞察")
        st.info("""系统的**隐含技能推断**能力可以从你的项目描述中发现未明确提及的技术能力。
        例如：提到"高并发"→ 自动推断你可能掌握 Redis/Kafka/分布式锁等""")

        if profile.skills_implicit:
            st.write(f"🔍 从项目描述中额外推断出 **{len(profile.skills_implicit)}** 项隐含技能:")
            for skill in profile.skills_implicit:
                st.write(f"  - 🔮 `{skill}`")

            st.success("💡 这些隐含技能也会被纳入匹配分析中，让你的能力得到更全面的展示！")
        else:
            st.write("当前未检测到额外的隐含技能。可以尝试丰富项目描述中的技术细节。")
