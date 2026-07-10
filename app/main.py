"""Streamlit 前端应用主入口"""

import streamlit as st

st.set_page_config(
    page_title="新一代信息技术全景图谱系统",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1rem 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
    }
</style>
""", unsafe_allow_html=True)

# 侧边栏
with st.sidebar:
    st.image("https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=abstract%20technology%20knowledge%20graph%20network%20visualization%20with%20glowing%20nodes%20and%20connections%2C%20dark%20blue%20purple%20gradient%2C%20futuristic%20digital%20interface&image_size=square_hd", width=200)
    st.title("🧠 知识图谱系统")
    st.markdown("---")

    nav = st.radio(
        "**导航菜单**",
        ["📊 数据驾驶舱", "🔍 图谱浏览器", "📄 简历分析",
         "🎯 智能匹配", "🔮 新岗位发现", "📈 差距分析",
         "💼 职业路径", "🌐 市场情报", "⚡ What-If分析",
         "🤖 批量分析", "❓ 智能问答", "⚙️ 系统管理"],
        label_visibility="collapsed",
    )

# 主标题
st.markdown('<div class="main-header">🧠 新一代信息技术全景图谱系统</div>', unsafe_allow_html=True)
st.markdown("**多源数据采集 → 动态知识图谱 → 智能匹配与差距分析 | 全流程闭环**")

# 页面路由映射
page_map = {
    "📊 数据驾驶舱": "dashboard",
    "🔍 图谱浏览器": "graph_explorer",
    "📄 简历分析": "resume_analysis",
    "🎯 智能匹配": "job_matching",
    "🔮 新岗位发现": "job_discovery",
    "📈 差距分析": "gap_analysis",
    "💼 职业路径": "career_path",
    "🌐 市场情报": "market_intelligence",
    "⚡ What-If分析": "what_if_analysis",
    "🤖 批量分析": "batch_analysis",
    "❓ 智能问答": "qa_assistant",
    "⚙️ 系统管理": "admin_panel",
}

current_page = page_map.get(nav, "dashboard")

# 动态导入页面模块
try:
    if current_page == "dashboard":
        from app.pages.dashboard import render_dashboard
        render_dashboard()
    elif current_page == "graph_explorer":
        from app.pages.graph_explorer import render_graph_explorer
        render_graph_explorer()
    elif current_page == "resume_analysis":
        from app.pages.resume_analysis import render_resume_analysis
        render_resume_analysis()
    elif current_page == "job_matching":
        from app.pages.job_matching import render_job_matching
        render_job_matching()
    elif current_page == "job_discovery":
        from app.pages.job_discovery import render_job_discovery
        render_job_discovery()
    elif current_page == "gap_analysis":
        from app.pages.gap_analysis import render_gap_analysis
        render_gap_analysis()
    elif current_page == "career_path":
        from app.pages.career_path import render_career_path
        render_career_path()
    elif current_page == "market_intelligence":
        from app.pages.market_intelligence import render_market_intelligence
        render_market_intelligence()
    elif current_page == "what_if_analysis":
        from app.pages.what_if_analysis import render_what_if_analysis
        render_what_if_analysis()
    elif current_page == "batch_analysis":
        from app.pages.batch_analysis import render_batch_analysis
        render_batch_analysis()
    elif current_page == "qa_assistant":
        from app.pages.qa_assistant import render_qa_assistant
        render_qa_assistant()
    elif current_page == "admin_panel":
        from app.pages.admin_panel import render_admin_panel
        render_admin_panel()

except ImportError as e:
    st.error(f"页面模块加载失败: {e}\n\n请确保所有页面文件都已创建。")
    st.info("正在开发中，敬请期待...")

except Exception as e:
    st.error(f"页面渲染错误: {e}")

# 页脚
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: gray; font-size: 0.85rem;">
    🚀 新一代信息技术全景图谱系统 v1.0 | 多智能体协作 + 动态知识图谱 + RAG增强检索<br>
    Powered by Python · CrewAI · Neo4j · ChromaDB · LangChain · Streamlit
</div>
""", unsafe_allow_html=True)
