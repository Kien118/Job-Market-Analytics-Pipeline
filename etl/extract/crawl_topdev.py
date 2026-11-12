import logging
import re
import time
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

from extract.job_posting import description, extract_job_posting, extract_salary, location, posted_date
from extract.source_batch import SourceBatch


logger = logging.getLogger(__name__)
BASE_URL = "https://topdev.vn"
LISTING_URLS = [
    f"{BASE_URL}/it-jobs",
    f"{BASE_URL}/jobs/search?keyword=backend",
    f"{BASE_URL}/jobs/search?keyword=frontend",
    f"{BASE_URL}/jobs/search?keyword=data",
    f"{BASE_URL}/jobs/search?keyword=python",
    f"{BASE_URL}/jobs/search?keyword=java",
    f"{BASE_URL}/jobs/search?keyword=devops",
]

IT_KEYWORDS = [
    "developer", "software", "backend", "frontend", "fullstack", "data", "engineer",
    "devops", "database", "system", "python", "java", ".net", "nodejs", "react",
    "tester", "qa", "machine learning", "cloud",
]


def is_it_job(title):
    title = title.lower()
    return any(keyword in title for keyword in IT_KEYWORDS) or bool(re.search(r"\bai\b", title))


def crawl_topdev_jobs(limit=50):
    headers = {"User-Agent": "Mozilla/5.0"}
    batch = SourceBatch()
    seen_urls = set()
    for index, listing_url in enumerate(LISTING_URLS):
        try:
            response = requests.get(listing_url, headers=headers, timeout=30)
            response.raise_for_status()
        except requests.RequestException as error:
            logger.warning("TopDev listing request failed: %s", error)
            batch.failed_pages += 1
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        recognized = False
        for link in soup.select("a[href]"):
            href = link["href"]
            if "/detail-jobs/" not in href:
                continue
            job_url = urljoin(BASE_URL, href)
            parts = urlsplit(job_url)
            if (
                parts.hostname not in {"topdev.vn", "www.topdev.vn"}
                or parts.scheme not in {"http", "https"}
                or "/detail-jobs/" not in parts.path
            ):
                continue
            recognized = True
            title = link.get_text(" ", strip=True)
            if len(title) < 10 or not is_it_job(title) or job_url in seen_urls:
                continue

            seen_urls.add(job_url)
            try:
                batch.add(crawl_topdev_job_detail(job_url, title, headers))
            except (requests.RequestException, ValueError) as error:
                batch.reject(error)
            if len(batch.jobs) + batch.rejected >= limit:
                return batch
            time.sleep(1)

        if index == 0 and not recognized:
            logger.warning("TopDev primary listing contained no recognizable job links")
            batch.failed_pages += 1

    if not seen_urls and not batch.failed_pages:
        logger.warning("TopDev listings contained no job links matching the IT filter")
        batch.failed_pages += 1
    return batch


def crawl_topdev_job_detail(job_url, fallback_title, headers):
    response = requests.get(job_url, headers=headers, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    posting = extract_job_posting(soup)
    heading = soup.select_one("h1")
    if not posting and heading is None:
        raise ValueError("unrecognized TopDev detail page")

    title = heading.get_text(" ", strip=True) if heading else ""
    company = extract_company(soup)
    return {
        "source": "TopDev",
        "job_title": title or fallback_title[:150],
        "company_name": company,
        "location": location(soup, posting),
        "salary_text": extract_salary(soup, posting),
        "description": description(posting),
        "posted_date": posted_date(posting),
        "source_url": job_url,
    }


def extract_company(soup):
    selectors = ["a[href*='/companies/']", "a[href*='/company/']", ".company-name", ".job-detail__company"]
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            company = node.get_text(" ", strip=True)
            if company:
                return company[:150]
    return None
