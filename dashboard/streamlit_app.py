import os

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import URL, create_engine
from sqlalchemy.exc import SQLAlchemyError

from metrics import (
    daily_postings,
    filter_postings,
    monthly_vnd_salaries,
    search_postings,
    skill_counts,
)


@st.cache_data(ttl=30)
def load_postings(database_url):
    engine = create_engine(database_url)
    try:
        return pd.read_sql(
            """
            SELECT job_id, source, clean_title, COALESCE(clean_location, 'Unknown') AS clean_location,
                   seniority, posted_date, skills, has_description, min_salary, max_salary,
                   salary_currency, salary_period
            FROM stg_jobs
            WHERE source IS NOT NULL
            """,
            engine,
        )
    finally:
        engine.dispose()


def database_url():
    explicit_url = os.getenv("DATABASE_URL")
    if explicit_url:
        return explicit_url
    return URL.create(
        "postgresql",
        username=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.environ["POSTGRES_HOST"],
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.environ["POSTGRES_DB"],
    ).render_as_string(hide_password=False)


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
    "Each posting is counted once per source. The same vacancy can appear on multiple sites."
)

if st.button("🔄 Refresh data"):
    load_postings.clear()

try:
    postings = load_postings(database_url())
except (KeyError, ValueError, SQLAlchemyError):
    st.error("Could not read published postings. Check the dashboard database connection and schema.")
    st.stop()

if postings.empty:
    st.info("No job postings have been published yet.")
    st.stop()

# Sidebar filters
st.sidebar.header("🔎 Filters")

sources = sorted(postings["source"].dropna().unique().tolist())
selected_sources = st.sidebar.multiselect(
    "Source",
    sources,
    default=sources
)

locations = sorted(postings["clean_location"].unique().tolist())
selected_locations = st.sidebar.multiselect(
    "Location",
    locations,
    default=locations
)

posted_range = ()
known_dates = postings["posted_date"].dropna()
if not known_dates.empty and st.sidebar.checkbox("Filter by posting date"):
    earliest = known_dates.min()
    latest = known_dates.max()
    posted_range = st.sidebar.date_input(
        "Posting dates",
        value=(earliest, latest),
        min_value=earliest,
        max_value=latest,
    )
    if len(posted_range) != 2:
        st.sidebar.caption("Select a start and end date to apply the date filter.")
    else:
        st.sidebar.caption("The date filter excludes postings with an unknown date.")

filtered_jobs_df = filter_postings(postings, selected_sources, selected_locations, posted_range)
top_skills_df, described_count = skill_counts(filtered_jobs_df)
salary_df = monthly_vnd_salaries(filtered_jobs_df)
daily_stats_df = daily_postings(filtered_jobs_df)

# KPI
total_jobs = len(filtered_jobs_df)
total_sources = filtered_jobs_df["source"].nunique()
total_skills = len(top_skills_df)
total_locations = filtered_jobs_df["clean_location"].nunique()

top_skill = (
    top_skills_df.iloc[0]["skill_name"]
    if not top_skills_df.empty
    else "N/A"
)

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Postings", total_jobs)
col2.metric("Sources", total_sources)
col3.metric("Skills mentioned", total_skills)
col4.metric("Location groups", total_locations)
col5.metric("Top Skill", top_skill)

st.divider()

# Row 1
left, right = st.columns([1, 2])

with left:
    st.subheader("📌 Postings by Source")

    source_df = (
        filtered_jobs_df
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
    st.subheader("🔥 Skills Mentioned in Postings")
    st.caption(
        f"{described_count:,} of {total_jobs:,} postings have descriptions. "
        "Skill share uses postings with descriptions as the denominator. "
        "One posting can mention multiple skills."
    )

    if top_skills_df.empty:
        st.info("No tracked skills were found in the selected postings.")
    else:
        fig = px.bar(
            top_skills_df.iloc[::-1],
            x="total_jobs",
            y="skill_name",
            orientation="h",
            text="total_jobs",
            color="total_jobs",
            hover_data={"share": ":.1%"},
            labels={"share": "Share of postings with descriptions", "total_jobs": "Postings"},
            color_continuous_scale="Blues"
        )
        fig.update_traces(
            textposition="outside",
            marker_line_width=0
        )
        fig.update_layout(
            xaxis_title="Postings mentioning skill",
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
    st.subheader("📍 Postings by Location")

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
            yaxis_title="Postings",
            showlegend=False,
            coloraxis_showscale=False
        )
        fig.update_traces(textposition="outside")
        fig = style_plotly(fig)
        st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("📈 Postings by Date")
    unknown_dates = filtered_jobs_df["posted_date"].isna().sum()
    st.caption(f"{unknown_dates:,} selected postings have an unknown posting date.")

    if daily_stats_df.empty:
        st.info("No known posting dates in the selection.")
    else:
        fig = px.scatter(
            daily_stats_df,
            x="posted_date",
            y="total_jobs",
        )
        fig.update_traces(
            marker=dict(size=10, color="#FBBF24")
        )
        fig.update_layout(
            xaxis_title="Posted Date",
            yaxis_title="Postings"
        )
        fig = style_plotly(fig)
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# Salary
st.subheader("💰 Advertised Salary by Location")
st.caption(
    f"{salary_df['total_jobs'].sum():,} of {total_jobs:,} postings have usable VND/month figures. "
    "Each posting contributes the midpoint of its advertised range."
)

if salary_df.empty:
    st.info("No comparable monthly VND salaries in the selection.")
else:
    fig = px.bar(
        salary_df,
        x="clean_location",
        y="avg_salary",
        text="avg_salary",
        color="avg_salary",
        hover_data={"total_jobs": True},
        labels={"avg_salary": "Average midpoint", "total_jobs": "Postings with salary"},
        color_continuous_scale="Viridis"
    )
    fig.update_layout(
        xaxis_title="Location",
        yaxis_title="Average salary midpoint (VND/month)",
        coloraxis_showscale=False
    )
    fig.update_traces(texttemplate="%{y:,.0f}")
    fig = style_plotly(fig)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# Table
st.subheader("🧾 Selected Job Postings")

search_keyword = st.text_input("Search the table by job title or skill")

table_df = search_postings(filtered_jobs_df, search_keyword).sort_values(
    ["posted_date", "job_id"], ascending=[False, True]
)

st.dataframe(
    table_df[["source", "clean_title", "clean_location", "posted_date", "seniority", "skills"]],
    use_container_width=True,
    hide_index=True,
    column_config={
        "source": "Source",
        "clean_title": "Job title",
        "clean_location": "Location",
        "posted_date": "Posting date",
        "seniority": "Seniority",
        "skills": "Skills",
    },
)
