import requests
from bs4 import BeautifulSoup

sites = {
    "TopCV": "https://www.topcv.vn/tim-viec-lam-it-phan-mem-c10026",
    "CareerViet": "https://careerviet.vn/viec-lam/it-phan-mem-c1-vi.html",
    "TopDev": "https://topdev.vn/it-jobs"
}

headers = {
    "User-Agent": "Mozilla/5.0"
}

for name, url in sites.items():
    print("=" * 60)
    print(name)
    print(url)

    response = requests.get(url, headers=headers, timeout=30)
    print("Status:", response.status_code)

    soup = BeautifulSoup(response.text, "html.parser")

    print("Title:", soup.title.get_text(strip=True) if soup.title else None)

    text = soup.get_text(" ", strip=True).lower()

    keywords = ["python", "java", "developer", "data", "backend", "frontend", "tester"]

    for keyword in keywords:
        print(keyword, ":", keyword in text)

    links = soup.select("a[href]")

    job_links = []

    for link in links:
        href = link.get("href", "")
        label = link.get_text(" ", strip=True)

        if any(k in href.lower() for k in ["viec-lam", "jobs", "it-jobs"]):
            if len(label) > 10:
                job_links.append((label[:100], href))

    print("Possible job links:", len(job_links))

    for label, href in job_links[:10]:
        print("-", label, "|", href)