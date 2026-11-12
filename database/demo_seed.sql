\set ON_ERROR_STOP on

-- Synthetic postings for a deterministic demo, separate from database initialization.
SELECT saved.*
FROM (VALUES
    ('Demo Board A', 'Data Engineer', 'Example A', 'TP. HCM', '20 - 30 triệu/tháng',
     'Python, SQL and Apache Spark', DATE '2026-08-24', 'a-1'),
    ('Demo Board A', 'Analytics Engineer', 'Example A', 'Hồ Chí Minh', '25 - 35 triệu/tháng',
     'SQL and dbt', DATE '2026-08-25', 'a-2'),
    ('Demo Board B', 'Junior Data Engineer', 'Example B', 'Ha Noi', NULL,
     'Python and Docker', DATE '2026-08-26', 'b-1'),
    ('Demo Board B', 'Data Platform Engineer', 'Example B', NULL, NULL,
     'Apache Kafka and Spark', NULL, 'b-2')
) AS demo(source, job_title, company_name, location, salary_text, description, posted_date, external_id)
CROSS JOIN LATERAL public.upsert_raw_job(
    demo.source, demo.job_title, demo.company_name, demo.location, demo.salary_text,
    demo.description, demo.posted_date, NULL, demo.external_id
) AS saved;
