import requests
from bs4 import BeautifulSoup

url = "https://remoteok.com/remote-data-jobs"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(url, headers=headers, timeout=30)
soup = BeautifulSoup(response.text, "html.parser")

jobs = soup.select("tr.job:not(.placeholder)")

print("Job rows:", len(jobs))

if jobs:
    first_job = jobs[0]

    print(first_job.prettify()[:3000])