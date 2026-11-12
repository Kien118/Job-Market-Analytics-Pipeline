import logging
import time
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

from extract.job_posting import description, extract_job_posting, extract_salary, location, posted_date
from extract.source_batch import SourceBatch


logger = logging.getLogger(__name__)
BASE_URL = "https://careerviet.vn"
LISTING_URL = f"{BASE_URL}/viec-lam/it-phan-mem-c1-vi.html"


def crawl_careerviet_jobs(limit=50):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(LISTING_URL, headers=headers, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    batch = SourceBatch()
    seen_urls = set()
    for link in soup.select("a[href]"):
        href = link["href"]
        if "/vi/tim-viec-lam/" not in href:
            continue
        title = link.get_text(" ", strip=True)
        job_url = urljoin(BASE_URL, href)
        parts = urlsplit(job_url)
        if (
            parts.hostname not in {"careerviet.vn", "www.careerviet.vn"}
            or parts.scheme not in {"http", "https"}
            or "/vi/tim-viec-lam/" not in parts.path
            or len(title) < 20
            or job_url in seen_urls
        ):
            continue

        seen_urls.add(job_url)
        try:
            batch.add(crawl_careerviet_job_detail(job_url, title, headers))
        except (requests.RequestException, ValueError) as error:
            batch.reject(error)
        if len(batch.jobs) + batch.rejected >= limit:
            break
        time.sleep(1)

    if not seen_urls:
        logger.warning("CareerViet listing contained no recognizable job links")
        batch.failed_pages += 1
    return batch


def crawl_careerviet_job_detail(job_url, fallback_title, headers):
    response = requests.get(job_url, headers=headers, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    posting = extract_job_posting(soup)
    heading = soup.select_one("h1")
    if not posting and heading is None:
        raise ValueError("unrecognized CareerViet detail page")

    title = heading.get_text(" ", strip=True) if heading else ""
    company = soup.select_one(".company-name, .job-company-name, a[href*='nha-tuyen-dung']")
    job_description = description(posting) or " ".join(
        section.get_text(" ", strip=True) for section in soup.select(".detail-row.reset-bullet")
    )
    return {
        "source": "CareerViet",
        "job_title": title or fallback_title[:150],
        "company_name": company.get_text(" ", strip=True)[:150] if company else None,
        "location": location(soup, posting),
        "salary_text": extract_salary(soup, posting),
        "description": job_description,
        "posted_date": posted_date(posting),
        "source_url": job_url,
    }
