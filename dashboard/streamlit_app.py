import os

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/job_market_db"
)


@st.cache_data(ttl=30)
def load_table(table_name: str):
    engine = create_engine(DATABASE_URL)
    return pd.read_sql(f"SELECT * FROM {table_name};", engine)


def style_plotly(fig):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117",
        font=dict(
            family="Inter, Arial, sans-serif",
            size=13,
            color="#E5E7EB"
        ),
        margin=dict(l=20, r=20, t=40, b=30),
        height=420,
    )
    return fig


st.set_page_config(
    page_title="Job Market Analytics Dashboard",
    page_icon="📊",
    layout="wide"
)

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #0E1117 0%, #111827 100%);
        color: #E5E7EB;
    }

    h1, h2, h3 {
        font-family: 'Inter', Arial, sans-serif;
        font-weight: 800;
    }

    .block-container {
        padding-top: 3rem;
        padding-bottom: 3rem;
    }

    [data-testid="stMetric"] {
        background: #111827;
        border: 1px solid #1F2937;
        padding: 18px;
        border-radius: 16px;
        box-shadow: 0 4px 18px rgba(0,0,0,0.25);
    }

    [data-testid="stMetricLabel"] {
        color: #9CA3AF;
        font-size: 14px;
    }

    [data-testid="stMetricValue"] {
        color: #F9FAFB;
        font-size: 30px;
        font-weight: 800;
    }

    .section-card {
        background: #111827;
        padding: 20px;
        border-radius: 18px;
        border: 1px solid #1F2937;
        margin-bottom: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("📊 Job Market Analytics Dashboard")
st.caption(
    "End-to-end Data Engineering pipeline: "
    "Crawler/API → PostgreSQL → ETL → Analytics Marts → Streamlit"
)

if st.button("🔄 Refresh data"):
    st.cache_data.clear()
    st.rerun()

top_skills_df = load_table("mart_top_skills")
salary_df = load_table("mart_salary_summary")
daily_stats_df = load_table("mart_daily_job_stats")
stg_jobs_df = load_table("stg_jobs")
raw_jobs_df = load_table("raw_jobs")

# Sidebar filters
st.sidebar.header("🔎 Filters")

sources = sorted(raw_jobs_df["source"].dropna().unique().tolist())
selected_sources = st.sidebar.multiselect(
    "Source",
    sources,
    default=sources
)

locations = sorted(stg_jobs_df["clean_location"].dropna().unique().tolist())
selected_locations = st.sidebar.multiselect(
    "Location",
    locations,
    default=locations
)

filtered_raw_df = raw_jobs_df[
    raw_jobs_df["source"].isin(selected_sources)
]

filtered_jobs_df = stg_jobs_df[
    stg_jobs_df["clean_location"].isin(selected_locations)
]

# KPI
total_jobs = len(filtered_jobs_df)
total_sources = filtered_raw_df["source"].nunique()
total_skills = len(top_skills_df)
total_locations = filtered_jobs_df["clean_location"].nunique()

top_skill = (
    top_skills_df.iloc[0]["skill_name"]
    if not top_skills_df.empty
    else "N/A"
)

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Total Jobs", total_jobs)
col2.metric("Sources", total_sources)
col3.metric("Skills", total_skills)
col4.metric("Locations", total_locations)
col5.metric("Top Skill", top_skill)

st.divider()

# Row 1
left, right = st.columns([1, 2])

with left:
    st.subheader("📌 Jobs by Source")

    source_df = (
        filtered_raw_df
        .groupby("source")
        .size()
        .reset_index(name="total_jobs")
        .sort_values("total_jobs", ascending=False)
    )

    if source_df.empty:
        st.info("No source data available.")
    else:
        fig = px.pie(
            source_df,
            names="source",
            values="total_jobs",
            hole=0.55,
            color_discrete_sequence=[
                "#60A5FA",
                "#A78BFA",
                "#34D399",
                "#FBBF24"
            ]
        )
        fig.update_traces(
            textposition="inside",
            textinfo="percent+label"
        )
        fig = style_plotly(fig)
        st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("🔥 Top Skills")

    if top_skills_df.empty:
        st.info("No skill data available.")
    else:
        fig = px.bar(
            top_skills_df.sort_values("total_jobs", ascending=True),
            x="total_jobs",
            y="skill_name",
            orientation="h",
            text="total_jobs",
            color="total_jobs",
            color_continuous_scale="Blues"
        )
        fig.update_traces(
            textposition="outside",
            marker_line_width=0
        )
        fig.update_layout(
            xaxis_title="Total Jobs",
            yaxis_title="Skill",
            showlegend=False,
            coloraxis_showscale=False
        )
        fig = style_plotly(fig)
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# Row 2
left, right = st.columns(2)

with left:
    st.subheader("📍 Jobs by Location")

    location_df = (
        filtered_jobs_df
        .groupby("clean_location")
        .size()
        .reset_index(name="total_jobs")
        .sort_values("total_jobs", ascending=False)
    )

    if location_df.empty:
        st.info("No location data available.")
    else:
        fig = px.bar(
            location_df,
            x="clean_location",
            y="total_jobs",
            text="total_jobs",
            color="total_jobs",
            color_continuous_scale="Teal"
        )
        fig.update_layout(
            xaxis_title="Location",
            yaxis_title="Total Jobs",
            showlegend=False,
            coloraxis_showscale=False
        )
        fig.update_traces(textposition="outside")
        fig = style_plotly(fig)
        st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("📈 Hiring Trend")

    if daily_stats_df.empty:
        st.info("No daily job trend data available.")
    else:
        daily_stats_df["posted_date"] = pd.to_datetime(
            daily_stats_df["posted_date"]
        ).dt.date

        fig = px.line(
            daily_stats_df,
            x="posted_date",
            y="total_jobs",
            markers=True,
        )
        fig.update_traces(
            line=dict(width=4, color="#60A5FA"),
            marker=dict(size=10, color="#FBBF24")
        )
        fig.update_layout(
            xaxis_title="Posted Date",
            yaxis_title="Total Jobs"
        )
        fig = style_plotly(fig)
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# Salary
st.subheader("💰 Salary Analytics")

if salary_df.empty:
    st.info(
        "No salary data available. "
        "Some Vietnamese job boards hide exact salary or show it as negotiable."
    )
else:
    fig = px.bar(
        salary_df,
        x="clean_location",
        y="avg_salary",
        text="avg_salary",
        color="avg_salary",
        color_continuous_scale="Viridis"
    )
    fig.update_layout(
        xaxis_title="Location",
        yaxis_title="Average Salary",
        coloraxis_showscale=False
    )
    fig = style_plotly(fig)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# Table
st.subheader("🧾 Cleaned Job Data")

search_keyword = st.text_input("Search job title or skills")

table_df = filtered_jobs_df.copy()

if search_keyword:
    keyword = search_keyword.lower()

    table_df = table_df[
        table_df["clean_title"].str.lower().str.contains(keyword, na=False)
        |
        table_df["skills"].astype(str).str.lower().str.contains(keyword, na=False)
    ]

st.dataframe(
    table_df,
    use_container_width=True,
    hide_index=True
)