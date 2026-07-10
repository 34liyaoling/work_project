"""市场情报页面"""
import streamlit as st
import pandas as pd
import plotly.express as px


def render_market_intelligence():
    st.header("🌐 岗位市场情报中心")
    st.markdown("实时了解各技术领域的**市场需求、薪资水平、竞争态势**")

    # 领域选择
    selected = st.multiselect(
        "选择关注的领域",
        ["人工智能", "大数据", "云计算", "软件开发", "DevOps", "区块链/Web3"],
        default=["人工智能", "软件开发"]
    )

    # 情报卡片
    cards = st.columns(len(selected) if selected else 3)

    market_data = {
        "人工智能": {"openings": 12847, "growth": "+15%", "avg_salary": 38, "competition": "高"},
        "大数据": {"openings": 8632, "growth": "+8%", "avg_salary": 30, "competition": "中"},
        "云计算": {"openings": 6543, "growth": "+12%", "avg_salary": 33, "competition": "中"},
        "软件开发": {"openings": 15234, "growth": "+5%", "avg_salary": 26, "competition": "高"},
        "DevOps": {"openings": 4521, "growth": "+18%", "avg_salary": 32, "competition": "中"},
        "区块链/Web3": {"openings": 1234, "growth": "-3%", "avg_salary": 35, "competition": "低"},
    }

    for i, domain in enumerate(selected[:len(cards)]):
        with cards[i]:
            data = market_data.get(domain, {})
            st.metric(f"📊 {domain}", f"{data.get('openings', 0):,} 岗位",
                     delta=data.get("growth", "N/A"))

    st.markdown("---")

    # 趋势图表
    st.subheader("📈 需求趋势（近6个月）")

    trend_data = []
    months = ["1月", "2月", "3月", "4月", "5月", "6月"]
    bases = {"人工智能": 8000, "大数据": 6000, "云计算": 5000, "软件开发": 12000}

    for domain in selected:
        base = bases.get(domain, 4000)
        for j, month in enumerate(months):
            trend_data.append({"month": month, "domain": domain, "openings": base + j * 300 + __import__('random').randint(-200, 500)})

    if trend_data:
        df = pd.DataFrame(trend_data)
        fig = px.line(df, x="month", y="openings", color="domain", markers=True,
                     title="各领域岗位需求趋势", labels={"openings": "开放职位数"})
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    # 城市热力
    st.subheader("📍 城市需求分布")
    city_data = [
        ("北京", 320, 42), ("上海", 280, 40), ("深圳", 250, 38),
        ("杭州", 180, 32), ("成都", 120, 25), ("广州", 110, 28),
        ("南京", 90, 22), ("武汉", 80, 20), ("西安", 70, 18),
    ]

    df_city = pd.DataFrame(city_data, columns=["city", "count", "avg_salary_k"])
    fig = px.bar(df_city, x="city", y="count", color="avg_salary_k",
                 title="城市岗位需求 vs 平均薪资", labels={"count": "岗位数", "avg_salary_k": "平均薪资(K)"})
    fig.update_layout(height=350)
    st.plotly_chart(fig, use_container_width=True)
