from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import requests

URL = 'https://web.archive.org/web/20240321180905/https://www.globaldigitaltimes.com/'
ORIGINAL_DOMAIN = 'globaldigitaltimes.com'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

retry = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retry)
http = requests.Session()
http.mount("https://", adapter)
http.mount("http://", adapter)
http.headers.update(HEADERS)

print(f"Fetching {URL}...")
response = http.get(URL)
print(f"Status: {response.status_code}")

soup = BeautifulSoup(response.text, 'html.parser')

# Simulate cleaning
for element in soup.select('#wm-ipp-base-anchor, #wm-ipp, #donato, #wm-tls, #wm-cap, script'):
    if element.name == 'script':
        src = element.get('src', '')
        if 'archive.org' in src or 'analytics' in src or 'wombat' in src:
            element.decompose()
        elif element.string and ('archive.org' in element.string or 'wombat' in element.string):
            element.decompose()
    else:
        element.decompose()

for comment in soup.find_all(string=lambda text: isinstance(text,  str) and ('Wayback' in text or 'archive.org' in text)):
    comment.extract()

links = soup.find_all('a', href=True)
print(f"Total links after cleaning: {len(links)}")

for i, a in enumerate(links[:20]):
    print(f"LINK {i}: {a['href']}")
