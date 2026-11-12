import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from pandas.errors import DatabaseError
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "etl"))

import pipeline


TABLES = ("stg_jobs", "mart_top_skills", "mart_salary_summary", "mart_daily_job_stats")


@unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "requires a disposable job_market_test database")
class ReportingPostgresTest(unittest.TestCase):
    def test_publish_rolls_back_and_dashboard_cannot_read_raw(self):
        url = make_url(os.environ["TEST_DATABASE_URL"])
        if url.get_backend_name() != "postgresql" or url.database != "job_market_test":
            self.fail("TEST_DATABASE_URL must use the disposable PostgreSQL database job_market_test")

        engine = create_engine(url)
        self.addCleanup(engine.dispose)
        schema = f"reporting_test_{uuid4().hex}"
        with engine.begin() as connection:
            self.assertEqual(connection.scalar(text("SELECT current_database()")), "job_market_test")
            self.assertFalse(
                connection.scalar(text("SELECT EXISTS (SELECT 1 FROM public.raw_jobs)")),
                "Refusing to run against a database with existing raw jobs",
            )
            grants = connection.execute(text("""
                SELECT has_table_privilege('job_market_dashboard', 'public.stg_jobs', 'SELECT'),
                       has_table_privilege('job_market_dashboard', 'public.stg_jobs', 'INSERT'),
                       has_table_privilege('job_market_dashboard', 'public.raw_jobs', 'SELECT')
            """)).one()
            self.assertEqual(tuple(grants), (True, False, False))
            connection.execute(text(f"CREATE SCHEMA {schema}"))
            for table in ("raw_jobs", *TABLES):
                connection.execute(text(f"CREATE TABLE {schema}.{table} (LIKE public.{table} INCLUDING ALL)"))
        self.addCleanup(self.drop_schema, engine, schema)

        scoped_url = url.update_query_dict({"options": f"-csearch_path={schema}"})
        with patch.dict(os.environ, {"DATABASE_URL": scoped_url.render_as_string(hide_password=False)}):
            with engine.begin() as connection:
                connection.execute(text(f"""
                    INSERT INTO {schema}.raw_jobs
                        (job_id, source, job_title, location, description, salary_text, posted_date, job_hash)
                    VALUES (1, 'fixture', 'Analyst', 'HCM', 'Python', '20–30 triệu/tháng',
                            DATE '2026-01-01', md5('first'))
                """))
            pipeline.run_pipeline()
            published = self.snapshot(engine, schema)
            self.assertTrue(all(published.values()))

            with engine.begin() as connection:
                connection.execute(text(f"""
                    ALTER TABLE {schema}.mart_daily_job_stats
                    ADD CONSTRAINT fixture_reject_second_daily_count CHECK (total_jobs < 2)
                """))
                connection.execute(text(f"""
                    INSERT INTO {schema}.raw_jobs
                        (job_id, source, job_title, location, description, salary_text, posted_date, job_hash)
                    VALUES (2, 'fixture', 'Engineer', 'HCM', 'SQL', '30–40 triệu/tháng',
                            DATE '2026-01-01', md5('second'))
                """))
            with patch.object(pipeline.logger, "exception"), self.assertRaisesRegex(
                (IntegrityError, DatabaseError), "fixture_reject_second_daily_count"
            ):
                pipeline.run_pipeline()
            self.assertEqual(self.snapshot(engine, schema), published)

    def snapshot(self, engine, schema):
        with engine.connect() as connection:
            return {
                table: connection.execute(text(f"SELECT * FROM {schema}.{table}")).all()
                for table in TABLES
            }

    def drop_schema(self, engine, schema):
        with engine.begin() as connection:
            connection.execute(text(f"DROP SCHEMA {schema} CASCADE"))
