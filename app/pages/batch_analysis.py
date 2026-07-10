"""批量分析页面"""
import streamlit as st
import pandas as pd


def render_batch_analysis():
    st.header("🤖 批量分析与对比")
    st.markdown("同时上传**多份简历**，进行团队技能分析和对比")

    uploaded_files = st.file_uploader(
        "📁 上传多份简历 (支持批量)",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
        help="可一次上传多份简历进行批量分析"
    )

    if uploaded_files:
        st.info(f"已选择 **{len(uploaded_files)}** 份简历")

        if st.button("🚀 开始批量分析", type="primary", use_container_width=True):
            with st.spinner(f"正在分析 {len(uploaded_files)} 份简历..."):
                results = []
                for i, f in enumerate(uploaded_files):
                    import tempfile
                    suffix = f.name.rsplit(".")[-1] if "." in f.name else "txt"
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{suffix}") as tmp:
                        tmp.write(f.getvalue())

                    try:
                        from agents.resume_parser import ResumeParserAgent
                        parser = ResumeParserAgent()
                        profile = parser.parse_resume(tmp.name)
                        results.append({
                            "序号": i + 1,
                            "文件名": f.name,
                            "姓名": profile.name or f"候选人{i+1}",
                            "技能数": len(profile.skills_with_credibility),
                            "水平": profile.overall_technical_level.upper(),
                            "年限": f"{profile.total_experience_years:.1f}年",
                            "hash": profile.resume_hash,
                        })
                        st.session_state[f"profile_{i}"] = profile
                    except Exception as e:
                        results.append({"序号": i + 1, "文件名": f.name, "错误": str(e)})

                st.session_state["batch_results"] = results
                st.success(f"✅ 完成 {len(results)} 份简历的分析")

    if "batch_results" in st.session_state:
        results = st.session_state["batch_results"]
        df = pd.DataFrame([r for r in results if "错误" not in r])
        st.dataframe(df, use_container_width=True, hide_index=True)

        # 团队技能热力
        if len(df) > 0:
            st.subheader("🔥 团队技能覆盖矩阵")
            all_skills = set()
            for i in range(len(results)):
                prof = st.session_state.get(f"profile_{i}")
                if prof and hasattr(prof, 'skills_explicit'):
                    all_skills.update(prof.skills_explicit)

            top_skills = list(all_skills)[:15]
            matrix_data = []
            for i in range(min(len(results), 5)):
                prof = st.session_state.get(f"profile_{i}")
                if prof:
                    row = {"候选人": prof.name or f"C{i+1}"}
                    for skill in top_skills:
                        row[skill] = "✅" if skill in (prof.skills_explicit + prof.skills_implicit) else "❌"
                    matrix_data.append(row)

            if matrix_data:
                st.dataframe(pd.DataFrame(matrix_data), use_container_width=True)
