import json
import time
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://careerviet.vn"

LISTING_URL = "https://careerviet.vn/viec-lam/it-phan-mem-c1-vi.html"


def crawl_careerviet_jobs(limit=50):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(
        LISTING_URL,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    links = soup.select("a[href]")

    jobs = []
    seen_urls = set()

    for link in links:
        href = link.get("href", "")
        text = link.get_text(" ", strip=True)

        if "/vi/tim-viec-lam/" not in href:
            continue

        if len(text) < 20:
            continue

        job_url = urljoin(BASE_URL, href)

        if job_url in seen_urls:
            continue

        seen_urls.add(job_url)

        job = crawl_careerviet_job_detail(
            job_url=job_url,
            fallback_title=text,
            headers=headers
        )

        if job:
            jobs.append(job)

        if len(jobs) >= limit:
            break

        time.sleep(1)

    return jobs


def crawl_careerviet_job_detail(job_url, fallback_title, headers):
    try:
        response = requests.get(
            job_url,
            headers=headers,
            timeout=30
        )

        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        page_text = soup.get_text(" ", strip=True)

        title = extract_title(soup, fallback_title)
        company = extract_company(soup)
        location = extract_location(page_text)
        salary = extract_salary(page_text)
        posted_date = extract_posted_date(soup)
        description = extract_job_description(soup)

        return {
            "source": "CareerViet Crawler",
            "job_title": title,
            "company_name": company,
            "location": location,
            "salary_text": salary,
            "description": description,
            "posted_date": posted_date,
            "source_url": job_url,
            "external_id": None
        }

    except Exception as e:
        print(f"Failed detail page: {job_url} - {e}")
        return None


def extract_title(soup, fallback_title):
    h1 = soup.select_one("h1")

    if h1:
        title = h1.get_text(" ", strip=True)

        if title:
            return title

    return fallback_title[:150]


def extract_company(soup):
    candidates = soup.select(
        ".company-name, .job-company-name, a[href*='nha-tuyen-dung']"
    )

    for item in candidates:
        text = item.get_text(" ", strip=True)

        if text:
            return text[:150]

    return "Unknown"


def extract_location(text):
    locations = [
        "Hồ Chí Minh",
        "Ha Noi",
        "Hà Nội",
        "Đà Nẵng",
        "Da Nang",
        "Bình Dương",
        "Đồng Nai",
        "Remote"
    ]

    for location in locations:
        if location.lower() in text.lower():
            return location

    return "Viet Nam"


def extract_salary(text):
    lower_text = text.lower()

    if "cạnh tranh" in lower_text:
        return "Competitive"

    if "thỏa thuận" in lower_text:
        return "Negotiable"

    if "triệu" in lower_text:
        return "VND salary mentioned"

    if "usd" in lower_text:
        return "USD salary mentioned"

    return "Not specified"


def extract_posted_date(soup):
    for script in soup.find_all("script", type="application/ld+json"):
        raw_json = script.string or script.get_text(" ", strip=True)

        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError:
            continue

        for job_posting in find_job_postings(payload):
            raw_date = job_posting.get("datePosted")

            if not isinstance(raw_date, str):
                continue

            try:
                return datetime.fromisoformat(
                    raw_date.replace("Z", "+00:00")
                ).date()
            except ValueError:
                continue

    return None


def extract_job_description(soup):
    for script in soup.find_all("script", type="application/ld+json"):
        raw_json = script.string or script.get_text(" ", strip=True)

        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError:
            continue

        for job_posting in find_job_postings(payload):
            raw_description = job_posting.get("description")

            if isinstance(raw_description, str) and raw_description.strip():
                return BeautifulSoup(
                    raw_description,
                    "html.parser"
                ).get_text(" ", strip=True)

    fallback_sections = soup.select(".detail-row.reset-bullet")
    fallback_description = " ".join(
        section.get_text(" ", strip=True)
        for section in fallback_sections
    )

    return fallback_description


def find_job_postings(payload):
    if isinstance(payload, dict):
        job_type = payload.get("@type")

        if job_type == "JobPosting" or (
            isinstance(job_type, list) and "JobPosting" in job_type
        ):
            yield payload

        for value in payload.values():
            yield from find_job_postings(value)

    elif isinstance(payload, list):
        for value in payload:
            yield from find_job_postings(value)
