"""智能问答助手页面"""
import streamlit as st


def render_qa_assistant():
    st.header("❓ 智能问答助手")
    st.markdown("基于**知识图谱 + RAG + LLM** 的智能问答系统")

    # 问题输入
    question = st.text_area(
        "💬 输入你的问题",
        height=100,
        placeholder="例如:\n- RAG和Fine-tuning有什么区别？\n- Python后端转AI有前景吗？\n- 学完Python下一步学什么？\n- AI工程师需要掌握哪些技能？"
    )

    col1, col2 = st.columns([3, 1])
    with col1:
        submit = st.button("🤖 提问", type="primary", use_container_width=True)
    with col2:
        clear = st.button("🗑️ 清空对话")

    if clear:
        if "qa_history" in st.session_state:
            del st.session_state["qa_history"]

    # 对话历史
    if "qa_history" not in st.session_state:
        st.session_state["qa_history"] = []

    for i, (q, a) in enumerate(st.session_state["qa_history"]):
        st.chat_message("user", avatar="👤").write(q)
        st.chat_message("assistant", avatar="🤖").write(a)

    if submit and question.strip():
        with st.spinner("正在思考..."):
            answer = _answer_question(question)
            st.session_state["qa_history"].append((question, answer))
            st.rerun()


def _answer_question(question: str) -> str:
    """回答问题"""
    try:
        from core.llm_service import get_llm_service
        llm = get_llm_service()

        # 构建知识上下文
        context = """
你是新一代信息技术领域的专家顾问。你可以访问以下知识：
- 8大技术领域：人工智能、大数据、云计算、软件开发、DevOps、区块链/Web3、网络安全、物联网
- 每个领域下有详细的技能分类和技术栈
- 岗位市场数据和薪资信息
- 技术趋势和生命周期信息

请基于专业知识给出准确、实用的回答。如果涉及具体技术比较，尽量给出客观的优缺点分析。
"""

        messages = [
            {"role": "system", "content": context},
            {"role": "user", "content": question},
        ]

        response = llm.chat_completion(messages, temperature=0.5)
        return response or "抱歉，我暂时无法回答这个问题。"
    except Exception as e:
        return f"回答生成出错: {e}"
