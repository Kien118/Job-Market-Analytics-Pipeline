import json
import re
from datetime import datetime

from bs4 import BeautifulSoup


def find_job_postings(payload):
    if isinstance(payload, dict):
        job_type = payload.get("@type")
        if job_type == "JobPosting" or (isinstance(job_type, list) and "JobPosting" in job_type):
            yield payload
        for value in payload.values():
            yield from find_job_postings(value)
    elif isinstance(payload, list):
        for value in payload:
            yield from find_job_postings(value)


def extract_job_posting(soup):
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            payload = json.loads(script.string or script.get_text(" ", strip=True))
        except json.JSONDecodeError:
            continue
        for posting in find_job_postings(payload):
            return posting
    return {}


def posted_date(posting):
    value = posting.get("datePosted")
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            pass
    return None


def description(posting):
    value = posting.get("description")
    if isinstance(value, str):
        return BeautifulSoup(value, "html.parser").get_text(" ", strip=True)
    return ""


def location(soup, posting):
    places = posting.get("jobLocation", [])
    if isinstance(places, dict):
        places = [places]
    localities = []
    if isinstance(places, list):
        for place in places:
            address = place.get("address") if isinstance(place, dict) else None
            if isinstance(address, dict):
                address = address.get("addressLocality") or address.get("addressRegion")
            if isinstance(address, str) and address.strip():
                localities.append(address.strip())
    if localities:
        return " / ".join(dict.fromkeys(localities))
    if posting.get("jobLocationType") == "TELECOMMUTE":
        return "Remote"
    node = soup.select_one("[itemprop=jobLocation], .job-location, .location-name")
    return node.get_text(" ", strip=True) if node else None


_NUMBER = r"\d+(?:[.,]\d+)*"
_RANGE = rf"{_NUMBER}(?:\s*[-–—]\s*{_NUMBER})?"
_CURRENCY = r"(?:triệu(?:\s*(?:đồng|VND))?|VND|VNĐ|đồng|₫|USD)"
_PERIOD = r"(?:giờ|ngày|tuần|tháng|năm|hour|day|week|month|year)"
_SALARY_WITH_PERIOD = re.compile(
    rf"(?<!\w)(?:{_RANGE}\s*{_CURRENCY}|(?:USD|\$)\s*{_RANGE})"
    rf"\s*(?:/\s*|(?:mỗi|per)\s+){_PERIOD}\b",
    re.IGNORECASE,
)


def _salary_amount(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    return str(value) if re.fullmatch(_NUMBER, str(value)) else None


def _structured_salary(salary):
    if isinstance(salary, str):
        return salary.strip() or None
    if not isinstance(salary, dict):
        return None

    value = salary.get("value")
    amount = _salary_amount(value)
    period = salary.get("unitText")
    if isinstance(value, dict):
        period = value.get("unitText", period)
        minimum = _salary_amount(value.get("minValue"))
        maximum = _salary_amount(value.get("maxValue"))
        amount = _salary_amount(value.get("value"))
        if minimum and maximum:
            amount = f"{minimum} - {maximum}"
        elif minimum:
            amount = f"min {minimum}"
        elif maximum:
            amount = f"max {maximum}"
    if amount is None:
        return None

    currency = salary.get("currency")
    if isinstance(currency, str) and currency.strip():
        amount += f" {currency.strip().upper()}"
    if isinstance(period, str) and period.strip():
        amount += f"/{period.strip().lower()}"
    return amount


def extract_salary(soup, posting):
    salary = _structured_salary(posting.get("baseSalary"))
    if salary:
        return salary
    for node in soup.select("[itemprop=baseSalary], .job-salary, .salary"):
        text = node.get_text(" ", strip=True)
        if re.search(_NUMBER, text) or text.lower() in {"thỏa thuận", "cạnh tranh", "negotiable", "competitive"}:
            return text
    match = _SALARY_WITH_PERIOD.search(soup.get_text(" ", strip=True))
    return match.group() if match else None
