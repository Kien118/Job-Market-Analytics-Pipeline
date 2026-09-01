CREATE TABLE raw_jobs (
    job_id SERIAL PRIMARY KEY,

    source VARCHAR(100),

    job_title TEXT,

    company_name TEXT,

    location TEXT,

    salary_text TEXT,

    description TEXT,

    posted_date DATE,

    source_url TEXT,

    external_id TEXT,

    job_hash VARCHAR(32) NOT NULL UNIQUE,

    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE stg_jobs (

    job_id INT PRIMARY KEY,

    clean_title TEXT,

    clean_location TEXT,

    min_salary NUMERIC,

    max_salary NUMERIC,

    seniority VARCHAR(50),

    skills TEXT[],

    transformed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE dim_company (

    company_id SERIAL PRIMARY KEY,

    company_name TEXT UNIQUE
);

CREATE TABLE dim_location (

    location_id SERIAL PRIMARY KEY,

    location_name TEXT UNIQUE
);

CREATE TABLE dim_skill (

    skill_id SERIAL PRIMARY KEY,

    skill_name TEXT UNIQUE
);

CREATE TABLE fact_job_posting (

    fact_id SERIAL PRIMARY KEY,

    company_id INT,

    location_id INT,

    posted_date DATE,

    salary NUMERIC
);

CREATE TABLE mart_top_skills (

    skill_name TEXT,

    total_jobs INT
);

CREATE TABLE mart_salary_summary (

    clean_location TEXT,

    avg_salary NUMERIC
);

CREATE TABLE mart_daily_job_stats (

    posted_date DATE,

    total_jobs INT
);

