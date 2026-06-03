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
    query = f"SELECT * FROM {table_name};"
    return pd.read_sql(query, engine)


st.set_page_config(
    page_title="Job Market Analytics Dashboard",
    layout="wide"
)

st.title("Job Market Analytics Dashboard")
st.caption(
    "Data Engineering portfolio project: "
    "API/Crawler → PostgreSQL → ETL → Analytics → Dashboard"
)

if st.button("Refresh data"):
    st.cache_data.clear()
    st.rerun()

top_skills_df = load_table("mart_top_skills")
salary_df = load_table("mart_salary_summary")
stg_jobs_df = load_table("stg_jobs")

col1, col2, col3, col4 = st.columns(4)

total_jobs = len(stg_jobs_df)
total_skills = len(top_skills_df)
total_locations = stg_jobs_df["clean_location"].nunique()

if not top_skills_df.empty:
    top_skill = top_skills_df.iloc[0]["skill_name"]
else:
    top_skill = "N/A"

col1.metric("Total Jobs", total_jobs)
col2.metric("Total Skills", total_skills)
col3.metric("Total Locations", total_locations)
col4.metric("Top Skill", top_skill)

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Top Skills")

    if top_skills_df.empty:
        st.info("No skill data available.")
    else:
        fig = px.bar(
            top_skills_df,
            x="skill_name",
            y="total_jobs",
            text="total_jobs"
        )
        fig.update_layout(
            xaxis_title="Skill",
            yaxis_title="Total Jobs"
        )
        st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Average Salary by Location")

    if salary_df.empty:
        st.info("No salary data available.")
    else:
        fig = px.bar(
            salary_df,
            x="clean_location",
            y="avg_salary",
            text="avg_salary"
        )
        fig.update_layout(
            xaxis_title="Location",
            yaxis_title="Average Salary"
        )
        st.plotly_chart(fig, use_container_width=True)

st.divider()

st.subheader("Cleaned Job Data")
st.dataframe(stg_jobs_df, use_container_width=True)