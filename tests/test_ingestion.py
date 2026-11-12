import unittest
from datetime import date
from unittest.mock import Mock, patch

import requests
from bs4 import BeautifulSoup

from extract.crawl_careerviet import crawl_careerviet_jobs
from extract.crawl_topdev import crawl_topdev_jobs
from extract.extract_arbeitnow import extract_arbeitnow_jobs
from extract.job_posting import extract_job_posting, extract_salary, location
from extract.source_batch import ingest_batch


def response(html="", payload=None, error=None):
    return Mock(text=html, json=Mock(return_value=payload), raise_for_status=Mock(side_effect=error))


class IngestionTest(unittest.TestCase):
    @patch("extract.crawl_careerviet.requests.get", return_value=response("<html>Changed layout</html>"))
    @patch("extract.source_batch.load_raw_jobs")
    def test_crawler_empty_html_does_not_publish(self, load, get):
        batch = crawl_careerviet_jobs()
        with self.assertRaisesRegex(RuntimeError, "failed_pages': 1"):
            ingest_batch("CareerViet", batch)
        load.assert_not_called()

    @patch("extract.crawl_topdev.time.sleep")
    @patch("extract.crawl_topdev.requests.get")
    @patch("extract.crawl_topdev.LISTING_URLS", ["https://topdev.vn/it-jobs"])
    @patch("extract.source_batch.load_raw_jobs")
    def test_crawler_partial_details_do_not_publish(self, load, get, sleep):
        get.side_effect = [
            response("""
                <a href="/detail-jobs/1">Python Developer I</a>
                <a href="/detail-jobs/2">Python Developer II</a>
                <a href="https://example.org/detail-jobs/3">Other Python Developer</a>
            """),
            response("<h1>Python Developer I</h1>"),
            response(error=requests.HTTPError("503")),
        ]
        batch = crawl_topdev_jobs()
        with self.assertRaisesRegex(RuntimeError, "accepted': 1, 'rejected': 1"):
            ingest_batch("TopDev", batch)
        self.assertEqual(get.call_count, 3)
        load.assert_not_called()

    @patch("extract.extract_arbeitnow.requests.get")
    @patch("extract.source_batch.load_raw_jobs")
    def test_explicit_empty_api_response_is_distinct_from_missing_data(self, load, get):
        get.return_value = response(payload={"data": []})
        load.return_value = {"written": 0, "unchanged": 0}
        self.assertEqual(ingest_batch("Arbeitnow", extract_arbeitnow_jobs())["accepted"], 0)
        get.return_value = response(payload={"error": "missing data"})
        with self.assertRaisesRegex(ValueError, "data array"):
            extract_arbeitnow_jobs()

    @patch("extract.extract_arbeitnow.requests.get")
    def test_api_validates_candidates_and_uses_utc_dates(self, get):
        get.return_value = response(payload={"data": [
            {"title": "Engineer", "created_at": 1767225600, "slug": "job-1"},
            {"title": "Wrong Date", "created_at": "today"},
            {"title": "Wrong Shape", "location": []},
        ]})
        batch = extract_arbeitnow_jobs()
        self.assertEqual(batch.jobs[0]["posted_date"], date(2026, 1, 1))
        self.assertEqual(batch.rejected, 2)

    def test_salary_preserves_structured_unit_and_original_text(self):
        soup = BeautifulSoup("""
            <script type="application/ld+json">
            {"@graph": [{"@type": "JobPosting", "baseSalary": {"currency": "VND",
             "value": {"minValue": 20000000, "maxValue": 30000000, "unitText": "MONTH"}}}]}
            </script>
            <p>20 - 30 triệu/tháng</p>
        """, "html.parser")
        self.assertEqual(extract_salary(soup, extract_job_posting(soup)), "20000000 - 30000000 VND/month")
        self.assertEqual(extract_salary(soup, {}), "20 - 30 triệu/tháng")
        self.assertIsNone(extract_salary(BeautifulSoup("Millions of records", "html.parser"), {}))

    def test_location_does_not_use_the_footer(self):
        soup = BeautifulSoup("<footer>Hà Nội</footer>", "html.parser")
        posting = {"jobLocation": {"address": {"addressLocality": "Đà Nẵng"}}}
        self.assertEqual(location(soup, posting), "Đà Nẵng")
        self.assertIsNone(location(soup, {}))
