"""职业路径页面"""
import streamlit as st
import plotly.graph_objects as go


def render_career_path():
    st.header("💼 职业路径模拟器")
    st.markdown("基于知识图谱中的岗位衍生关系，模拟你的**职业发展路径**")

    if st.session_state.get("resume_profile") is None:
        st.warning("⚠️ 请先上传并解析简历")
        return

    start_role = st.text_input("起点岗位（当前或目标）", value="", placeholder="例如: 初级Python开发")

    if st.button("🗺️ 生成职业路径", type="primary", use_container_width=True):
        if start_role:
            _generate_path(start_role)
        else:
            # 自动根据简历推断
            profile = st.session_state["resume_profile"]
            current = profile.current_position or "开发者"
            _generate_path(current)


def _generate_path(start: str):
    with st.spinner("正在分析职业发展路径..."):
        # 模拟路径数据
        paths = [
            {
                "name": "技术专家路线",
                "steps": [
                    ("初级开发", 0, "当前阶段"),
                    ("中级开发", 1, "1-2年"),
                    ("高级开发/技术负责人", 2, "3-5年"),
                    ("架构师", 3, "5-8年"),
                    ("CTO/技术VP", 4, "8年+"),
                ],
                "success_rate": 0.75,
                "salary_range": (12, 80),
            },
            {
                "name": "AI转型路线",
                "steps": [
                    (start or "开发者", 0, "当前"),
                    ("AI应用开发工程师", 1, "1-2年"),
                    ("AI平台工程师", 2, "2-4年"),
                    ("AI架构师", 3, "4-7年"),
                    ("AI技术总监", 4, "7年+"),
                ],
                "success_rate": 0.65,
                "salary_range": (20, 100),
            },
            {
                "name": "管理路线",
                "steps": [
                    (start or "开发者", 0, "当前"),
                    ("技术组长", 1, "2-3年"),
                    ("研发经理", 2, "3-5年"),
                    ("技术总监", 3, "5-8年"),
                    ("CTO/工程副总裁", 4, "8年+"),
                ],
                "success_rate": 0.55,
                "salary_range": (18, 120),
            },
        ]

        st.session_state["career_paths"] = paths


if "career_paths" in st.session_state:
    paths = st.session_state["career_paths"]

    for pi, path in enumerate(paths):
        with st.expander(f"🛤️ 路线{pi+1}: **{path['name']}** (成功率 {path['success_rate']:.0%})"):
            # 路径可视化
            fig = go.Figure()

            names = [s[0] for s in path["steps"]]
            positions = [s[1] for s in path["steps"]]
            times = [s[2] for s in path["steps"]]

            fig.add_trace(go.Scatter(
                x=list(range(len(names))), y=positions,
                mode='lines+markers+text',
                text=names,
                textposition="top center",
                line=dict(color='#667eea', width=3),
                marker=dict(size=15, color=positions, colorscale='Viridis'),
                name=path["name"],
            ))

            fig.update_layout(
                height=300,
                xaxis_visible=False,
                yaxis_visible=False,
                showlegend=False,
                title=f"{path['name']} — 预期薪资: {path['salary_range'][0]}K ~ {path['salary_range'][1]}K",
                margin=dict(l=50, r=50, t=50, b=50),
            )
            st.plotly_chart(fig, use_container_width=True)

            # 步骤详情
            for i, (name, pos, time_info) in enumerate(path["steps"]):
                status = "✅" if pos == 0 else ("📍" if pos == 1 else "⬜")
                st.write(f"{status} **{name}** — {time_info}")
