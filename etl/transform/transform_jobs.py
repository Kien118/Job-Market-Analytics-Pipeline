import re
import unicodedata
from decimal import Decimal
from html import unescape

import pandas as pd
from bs4 import BeautifulSoup


SKILLS = {
    "python": r"python(?:[23](?:\.\d+)*)?",
    "sql": "sql",
    "docker": "docker",
    "airflow": "airflow",
    "spark": "spark|pyspark",
    "aws": r"aws|amazon\s+web\s+services",
    "git": "git",
    "postgresql": "postgresql|postgres",
    "fastapi": "fastapi",
    "pandas": "pandas",
}
SKILL_PATTERNS = {
    skill: re.compile(rf"(?<!\w)(?:{aliases})(?!\w)", re.IGNORECASE)
    for skill, aliases in SKILLS.items()
}

LOCATION_ALIASES = {
    "hcm": "Hồ Chí Minh",
    "hcmc": "Hồ Chí Minh",
    "tp hcm": "Hồ Chí Minh",
    "tphcm": "Hồ Chí Minh",
    "ho chi minh": "Hồ Chí Minh",
    "ho chi minh city": "Hồ Chí Minh",
    "sai gon": "Hồ Chí Minh",
    "ha noi": "Hà Nội",
    "hanoi": "Hà Nội",
    "da nang": "Đà Nẵng",
    "danang": "Đà Nẵng",
    "binh duong": "Bình Dương",
    "dong nai": "Đồng Nai",
    "viet nam": "Việt Nam",
    "vietnam": "Việt Nam",
    "remote": "Remote",
    "unknown": "Unknown",
}

PERIODS = {
    "hour": "hour", "giờ": "hour",
    "day": "day", "ngày": "day",
    "week": "week", "tuần": "week",
    "month": "month", "tháng": "month",
    "year": "year", "năm": "year",
}
CURRENCY = r"VND|USD|EUR|GBP|AUD|CAD|SGD|JPY|₫|đồng|đ"
NUMBER = r"[0-9]+(?:[.,][0-9]+)*"
SALARY_PATTERN = re.compile(
    rf"(?:(?P<prefix>{CURRENCY})\s*)?"
    rf"(?P<low>{NUMBER})(?:\s*(?:[-–—]|đến|to)\s*(?P<high>{NUMBER}))?"
    rf"(?:\s*(?P<million>triệu))?(?:\s*(?P<suffix>{CURRENCY}))?"
    rf"\s*(?:/\s*|per\s+)(?P<period>{'|'.join(PERIODS)})",
    re.IGNORECASE,
)
EMPTY_SALARY = (None, None, None, None)
SALARY_COLUMNS = ["min_salary", "max_salary", "salary_currency", "salary_period"]


def description_text(description):
    if not isinstance(description, str):
        return ""
    if re.search(r"</?[a-zA-Z][^>]*>", description):
        return BeautifulSoup(description, "html.parser").get_text(" ", strip=True)
    return unescape(description).strip()


def extract_skills(description):
    return [
        skill for skill, pattern in SKILL_PATTERNS.items()
        if isinstance(description, str) and pattern.search(description)
    ]


def normalize_location(location):
    if not isinstance(location, str) or not location.strip():
        return "Unknown"
    location = " ".join(location.split())
    normalized = unicodedata.normalize("NFKD", location.casefold()).replace("đ", "d")
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    key = " ".join(re.findall("[a-z0-9]+", normalized))
    return LOCATION_ALIASES.get(key, location)


def parse_amount(amount):
    if re.fullmatch(r"[0-9]+", amount):
        return Decimal(amount)
    for thousands, decimal in ((",", "."), (".", ",")):
        escaped = re.escape(thousands)
        if re.fullmatch(
            rf"(?:[0-9]{{1,3}}(?:{escaped}[0-9]{{3}})+|[0-9]+)"
            rf"(?:{re.escape(decimal)}[0-9]{{1,2}})?",
            amount,
        ):
            return Decimal(amount.replace(thousands, "").replace(decimal, "."))
    return None


def normalize_salary(salary_text):
    if not isinstance(salary_text, str):
        return EMPTY_SALARY
    # shortcut: accept explicit point/range amounts only, extend when a source provides more formats.
    match = SALARY_PATTERN.fullmatch(" ".join(salary_text.strip().split()))
    if not match:
        return EMPTY_SALARY

    currencies = {
        "VND" if code.casefold() in {"đ", "đồng", "₫"} else code.upper()
        for code in (match["prefix"], match["suffix"]) if code
    }
    if match["million"]:
        currencies.add("VND")
    if len(currencies) != 1:
        return EMPTY_SALARY

    minimum = parse_amount(match["low"])
    maximum = parse_amount(match["high"]) if match["high"] else minimum
    if minimum is None or maximum is None or not 0 < minimum <= maximum:
        return EMPTY_SALARY
    if match["million"]:
        minimum *= 1_000_000
        maximum *= 1_000_000
    return minimum, maximum, currencies.pop(), PERIODS[match["period"].casefold()]


def detect_seniority(title):
    if not isinstance(title, str):
        return "Unknown"
    match = re.search(r"\b(internship|intern|fresher|junior|senior)\b", title, re.IGNORECASE)
    if not match:
        return "Unknown"
    return "Intern" if match[1].casefold() == "internship" else match[1].capitalize()


def transform_jobs(raw):
    descriptions = raw["description"].map(description_text)
    salaries = pd.DataFrame(
        raw["salary_text"].map(normalize_salary).tolist(),
        columns=SALARY_COLUMNS,
        index=raw.index,
    )
    staging = raw[["job_id", "posted_date", "ingested_at"]].copy()
    staging["source"] = raw["source"].fillna("").str.strip().replace("", "Unknown")
    staging["clean_title"] = raw["job_title"].fillna("").str.strip()
    staging["clean_location"] = raw["location"].map(normalize_location)
    staging["seniority"] = raw["job_title"].map(detect_seniority)
    staging["has_description"] = descriptions.astype(bool)
    staging["skills"] = descriptions.map(extract_skills)
    return staging.join(salaries)
