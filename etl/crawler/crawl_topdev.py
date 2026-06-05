import time
from datetime import date
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://topdev.vn"
LISTING_URL = "https://topdev.vn/it-jobs"

IT_KEYWORDS = [
    "developer",
    "software",
    "backend",
    "frontend",
    "fullstack",
    "data",
    "engineer",
    "devops",
    "database",
    "system",
    "python",
    "java",
    ".net",
    "nodejs",
    "frontend",
    "react",
    "tester",
    "qa",
    "ai",
    "machine learning",
    "cloud",
]


def is_it_job(title: str) -> bool:
    title_lower = title.lower()

    return any(
        keyword in title_lower
        for keyword in IT_KEYWORDS
    )


def crawl_topdev_jobs(limit=20):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(
        LISTING_URL,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    links = soup.select("a[href]")

    jobs = []
    seen_urls = set()

    for link in links:
        href = link.get("href", "")
        title = link.get_text(" ", strip=True)

        if "/detail-jobs/" not in href:
            continue

        if len(title) < 10:
            continue

        if not is_it_job(title):
            continue

        job_url = urljoin(BASE_URL, href)

        if job_url in seen_urls:
            continue

        seen_urls.add(job_url)

        job = crawl_topdev_job_detail(
            job_url=job_url,
            fallback_title=title,
            headers=headers
        )

        if job:
            jobs.append(job)

        if len(jobs) >= limit:
            break

        time.sleep(1)

    return jobs


def crawl_topdev_job_detail(job_url, fallback_title, headers):
    try:
        response = requests.get(
            job_url,
            headers=headers,
            timeout=30
        )

        if response.status_code != 200:
            return None

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        page_text = soup.get_text(" ", strip=True)

        title = extract_title(
            soup,
            fallback_title
        )

        company = extract_company(
            soup,
            page_text
        )

        location = extract_location(
            page_text
        )

        salary = extract_salary(
            page_text
        )

        return {
            "source": "TopDev Crawler",
            "job_title": title,
            "company_name": company,
            "location": location,
            "salary_text": salary,
            "description": page_text[:5000],
            "posted_date": date.today()
        }

    except Exception as e:
        print(f"Failed to crawl detail page {job_url}: {e}")
        return None


def extract_title(soup, fallback_title):
    h1 = soup.select_one("h1")

    if h1:
        title = h1.get_text(" ", strip=True)

        if title:
            return title

    return fallback_title[:150]


def extract_company(soup, page_text):
    selectors = [
        "a[href*='/companies/']",
        "a[href*='/company/']",
        ".company-name",
        ".job-detail__company",
    ]

    for selector in selectors:
        item = soup.select_one(selector)

        if item:
            text = item.get_text(" ", strip=True)

            if text:
                return text[:150]

    return "Unknown"


def extract_location(text):
    locations = [
        "Hồ Chí Minh",
        "Ho Chi Minh",
        "Hà Nội",
        "Ha Noi",
        "Đà Nẵng",
        "Da Nang",
        "Bình Dương",
        "Đồng Nai",
        "Remote",
    ]

    text_lower = text.lower()

    for location in locations:
        if location.lower() in text_lower:
            return location

    return "Viet Nam"


def extract_salary(text):
    text_lower = text.lower()

    if "usd" in text_lower:
        return "USD salary mentioned"

    if "triệu" in text_lower:
        return "VND salary mentioned"

    if "thỏa thuận" in text_lower:
        return "Negotiable"

    if "cạnh tranh" in text_lower:
        return "Competitive"

    return "Not specified"