import sys
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "etl"))

from analytics.build_daily_job_stats import build_daily_job_stats
from analytics.build_salary_summary import build_salary_summary
from analytics.build_top_skills import build_top_skills
from quality.quality_checks import validate_analytics
from transform.transform_jobs import extract_skills, normalize_salary, transform_jobs


RAW_COLUMNS = [
    "job_id", "source", "job_title", "location", "salary_text", "description",
    "posted_date", "ingested_at",
]


class AnalyticsTests(unittest.TestCase):
    def test_salary_keeps_units_and_rejects_ambiguous_amounts(self):
        self.assertEqual(normalize_salary("20,5–30 triệu đồng/tháng"),
                         (20_500_000, 30_000_000, "VND", "month"))
        self.assertEqual(normalize_salary("USD 1,500.50 - 2,000 per month"),
                         (Decimal("1500.50"), 2000, "USD", "month"))
        self.assertEqual(normalize_salary("25.000.000 VND/month"),
                         (25_000_000, 25_000_000, "VND", "month"))
        for value in (
            "20 - 30", "20 - 30 triệu", "30–20 triệu/tháng",
            "USD 1000–2000 EUR/month", "VND 10,00,000/month",
            "up to 2500 USD/month", "$2000/month", "Negotiable",
        ):
            with self.subTest(value=value):
                self.assertEqual(normalize_salary(value), (None,) * 4)

    def test_skills_match_aliases_without_substring_false_positives(self):
        self.assertEqual(extract_skills("draws diagrams and posts on GitHub"), [])
        self.assertEqual(extract_skills("Python3.11, PostgreSQL, PySpark and Amazon Web Services"),
                         ["python", "spark", "aws", "postgresql"])

    def test_marts_reconcile_with_staging_at_their_respective_grains(self):
        raw = pd.DataFrame([
            (1, "A", "Senior DE", "TP.HCM", "20–30 triệu/tháng",
             "<p>Python and SQL</p>", date(2026, 1, 1), None),
            (2, "B", "International role", "Ho Chi Minh City", "USD 2000/month",
             "<p>&nbsp;</p>", None, None),
            (3, "A", "Internship", "Hồ Chí Minh", "30000000 VND/month",
             "Python Python", date(2026, 1, 1), None),
            (4, "A", "", None, "USD 120000/year", None, date(2026, 1, 1), None),
        ], columns=RAW_COLUMNS)

        staging = transform_jobs(raw)
        daily = build_daily_job_stats(staging)
        skills = build_top_skills(staging)
        salaries = build_salary_summary(staging)
        validate_analytics(raw, staging, daily, skills, salaries)

        self.assertEqual(staging["clean_location"].tolist(),
                         ["Hồ Chí Minh", "Hồ Chí Minh", "Hồ Chí Minh", "Unknown"])
        self.assertEqual(staging["has_description"].tolist(), [True, False, True, False])
        self.assertEqual(staging["seniority"].tolist(), ["Senior", "Unknown", "Intern", "Unknown"])
        self.assertEqual(daily.to_dict("records"), [{"posted_date": date(2026, 1, 1), "total_jobs": 3}])
        self.assertEqual(skills.set_index("skill_name")["total_jobs"].to_dict(), {"python": 2, "sql": 1})
        grouped = salaries.set_index(["salary_currency", "salary_period"])
        self.assertEqual(grouped["avg_salary"].to_dict(),
                         {("USD", "month"): 2000, ("USD", "year"): 120_000, ("VND", "month"): 27_500_000})
        self.assertEqual(grouped["sample_count"].to_dict(),
                         {("USD", "month"): 1, ("USD", "year"): 1, ("VND", "month"): 2})

        with self.assertRaisesRegex(ValueError, "Daily postings"):
            validate_analytics(raw, staging, daily.iloc[0:0], skills, salaries)

    def test_empty_input_keeps_all_analytics_schemas(self):
        raw = pd.DataFrame(columns=RAW_COLUMNS)
        staging = transform_jobs(raw)
        daily = build_daily_job_stats(staging)
        skills = build_top_skills(staging)
        salaries = build_salary_summary(staging)
        validate_analytics(raw, staging, daily, skills, salaries)
        self.assertEqual(daily.columns.tolist(), ["posted_date", "total_jobs"])
        self.assertEqual(skills.columns.tolist(), ["skill_name", "total_jobs"])
        self.assertEqual(salaries.columns.tolist(),
                         ["clean_location", "salary_currency", "salary_period", "avg_salary", "sample_count"])
        self.assertTrue(all(table.empty for table in (staging, daily, skills, salaries)))
