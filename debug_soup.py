from bs4 import BeautifulSoup
import re

ORIGINAL_DOMAIN = 'globaldigitaltimes.com'
file_path = r'c:\Users\ANMOL\Downloads\website\revived_site\index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

soup = BeautifulSoup(content, 'html.parser')
links_found = 0
for a_tag in soup.find_all('a', href=True):
    href = a_tag['href']
    if ORIGINAL_DOMAIN in href:
        print(f"MATCH: {href}")
        links_found += 1
    else:
        # print(f"NO MATCH: {href}")
        pass

print(f"Total found: {links_found}")
