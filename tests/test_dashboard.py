from datetime import date
from pathlib import Path
import os
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from dashboard.metrics import (
    daily_postings,
    filter_postings,
    monthly_vnd_salaries,
    search_postings,
    skill_counts,
)


DAY = date(2026, 1, 1)
APP = Path(__file__).resolve().parents[1] / "dashboard" / "streamlit_app.py"


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.postings = pd.DataFrame(
            [
                (1, "A", "HCM", DAY, "Data Engineer [SQL]", ["python", "sql", "sql"], True, "VND", "month", 20_000_000, 30_000_000),
                (2, "B", "HCM", DAY, "SQL Engineer", ["sql"], True, "USD", "month", 2_000, 3_000),
                (3, "A", "HCM", None, "New Grad", [], False, "VND", "year", 120_000_000, 240_000_000),
                (4, "A", "Unknown", DAY, "QA Analyst", [], True, None, None, None, None),
                (5, "A", "HCM", DAY, "Ops Engineer", [], True, "VND", None, 10_000_000, 20_000_000),
            ],
            columns=[
                "job_id", "source", "clean_location", "posted_date", "clean_title",
                "skills", "has_description", "salary_currency", "salary_period", "min_salary", "max_salary",
            ],
        ).assign(seniority="Unknown")

    def test_metrics_use_filtered_postings(self):
        cohort = filter_postings(self.postings, ["A"], ["HCM"], ())
        self.assertEqual(cohort["job_id"].tolist(), [1, 3, 5])
        self.assertEqual(daily_postings(cohort)["total_jobs"].tolist(), [2])
        skills, described = skill_counts(cohort)
        self.assertEqual(described, 2)
        self.assertEqual(
            skills[["skill_name", "total_jobs", "share"]].values.tolist(),
            [["python", 1, 0.5], ["sql", 1, 0.5]],
        )
        salaries = monthly_vnd_salaries(self.postings)
        self.assertEqual(salaries[["avg_salary", "total_jobs"]].values.tolist(), [[25_000_000, 1]])
        dated = filter_postings(self.postings, ["A"], ["HCM"], (DAY, DAY))
        self.assertEqual(dated["job_id"].tolist(), [1, 5])
        self.assertEqual(search_postings(cohort, "[")["job_id"].tolist(), [1])

    @patch.dict(os.environ, {"DATABASE_URL": "postgresql://example/audit"})
    @patch("pandas.read_sql")
    def test_app_uses_one_serving_query_and_refreshes_cohort(self, read_sql):
        read_sql.return_value = self.postings
        app = AppTest.from_file(str(APP)).run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(read_sql.call_count, 1)
        self.assertIn("FROM stg_jobs", read_sql.call_args.args[0])
        self.assertNotIn("raw_jobs", read_sql.call_args.args[0])
        self.assertEqual(app.metric[0].value, "5")

        app.sidebar.checkbox[0].set_value(True).run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "4")

        app.sidebar.multiselect[0].set_value(["B"]).run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "1")
        self.assertEqual(app.metric[4].value, "sql")
        self.assertIn("No comparable monthly VND salaries", app.info[0].value)

        app.sidebar.multiselect[0].set_value([]).run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "0")
