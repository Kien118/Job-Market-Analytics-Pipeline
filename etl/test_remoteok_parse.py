import requests
from bs4 import BeautifulSoup

url = "https://remoteok.com/remote-data-jobs"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(url, headers=headers, timeout=30)
print("Status:", response.status_code)

soup = BeautifulSoup(response.text, "html.parser")

jobs = soup.select("tr.job")

print("Job rows:", len(jobs))

for job in jobs[:5]:
    title = job.select_one("h2")
    company = job.select_one("h3")
    location = job.select_one(".location")

    print("-" * 50)
    print("Title:", title.get_text(strip=True) if title else None)
    print("Company:", company.get_text(strip=True) if company else None)
    print("Location:", location.get_text(strip=True) if location else "Remote")