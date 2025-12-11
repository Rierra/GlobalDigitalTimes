import os
import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Configuration
BASE_ARCHIVE_URL = 'https://web.archive.org/web/20240321180905/https://www.globaldigitaltimes.com/'
ORIGINAL_DOMAIN = 'globaldigitaltimes.com'
OUTPUT_DIR = 'revived_site'
ASSETS_DIR = 'assets'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

retry_strategy = Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
http = requests.Session()
http.mount("https://", adapter)
http.mount("http://", adapter)
http.headers.update(HEADERS)

visited_urls = set()
url_queue = [BASE_ARCHIVE_URL]

def setup_directories():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    assets_path = os.path.join(OUTPUT_DIR, ASSETS_DIR)
    if not os.path.exists(assets_path):
        os.makedirs(assets_path)

def get_local_path(url):
    if 'web.archive.org/web/' in url:
        parts = url.split('/web/')
        if len(parts) > 1:
            path_parts = parts[1].split('/', 1)
            if len(path_parts) > 1:
                # Find http/https
                if 'http' in path_parts[1]:
                    url = path_parts[1]
    
    parsed = urlparse(url)
    path = parsed.path
    if path.startswith('/'):
        path = path[1:]
    
    if not path or path == '/':
        return 'index.html'
    
    if not os.path.splitext(path)[1]:
        return path.rstrip('/') + '.html'
        
    return path

def download_asset(asset_url, output_dir):
    try:
        if asset_url.startswith('//'):
            asset_url = 'https:' + asset_url
        
        # Determine filename
        parsed = urlparse(asset_url)
        filename = os.path.basename(parsed.path)
        if not filename:
            return None
            
        # Avoid query params in filename
        filename = filename.split('?')[0]
        # Allow longer filenames but sanitize
        filename = "".join([c for c in filename if c.isalpha() or c.isdigit() or c in '._-']).rstrip()
        if not filename:
            filename = 'asset_' + str(int(time.time()))
            
        local_path = os.path.join(ASSETS_DIR, filename)
        full_path = os.path.join(output_dir, local_path)
        
        if os.path.exists(full_path):
            return local_path
            
        print(f"Downloading asset: {asset_url}", flush=True)
        resp = http.get(asset_url, timeout=10)
        if resp.status_code == 200:
            with open(full_path, 'wb') as f:
                f.write(resp.content)
            return local_path
    except Exception as e:
        print(f"Failed to download asset {asset_url}: {e}")
    return None

def clean_html(html_content, base_url):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Cleaning (disabled for now to rule out issues, but removing archive tags is safe usually)
    for element in soup.select('#wm-ipp-base-anchor, #wm-ipp, #donato'):
        element.decompose()
        
    links_found = 0
    added_to_queue = 0
    
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.startswith('#'): continue
            
        resolved = urljoin(base_url, href)
        
        is_internal = False
        original_url = ''
        target_archive_url = ''
        
        if 'web.archive.org/web/' in resolved:
            target_archive_url = resolved
            # Extract orig
            m = re.search(r'web\.archive\.org/web/\d+[a-z_]*/(https?://.*)', resolved)
            if m:
                original_url = m.group(1)
            else:
                original_url = resolved
        
        # Check internal
        if ORIGINAL_DOMAIN in original_url:
            is_internal = True
            
        if is_internal:
            links_found += 1
            # Localize
            local_p = get_local_path(original_url)
            # Calc relative
            curr_local = get_local_path(base_url)
            curr_dir = os.path.dirname(curr_local)
            
            # Simple approach: absolute path from root? No, relative.
            # But let's just make it work.
            # a['href'] = local_p # This handles root-relative if <base> not set.
            # Better to use relative path.
            try:
                rel = os.path.relpath(local_p, curr_dir)
                a['href'] = rel.replace('\\', '/')
            except:
                a['href'] = local_p
                
            # Queue
            if target_archive_url not in visited_urls and target_archive_url not in url_queue:
                url_queue.append(target_archive_url)
                added_to_queue += 1
        else:
            # External: restore original
            if original_url:
                a['href'] = original_url
                
    print(f"Stats: Found {links_found} internal links. Added {added_to_queue} to queue.", flush=True)
    
    # Assets
    for img in soup.find_all('img', src=True):
        src = img['src']
        full = urljoin(base_url, src)
        local = download_asset(full, OUTPUT_DIR)
        if local:
            img['src'] = local.replace('\\', '/')
            
    return str(soup)

def process_url(url):
    if url in visited_urls: return
    visited_urls.add(url)
    print(f"Processing: {url}", flush=True)
    
    try:
        resp = http.get(url, timeout=30)
        print(f"Response: {resp.status_code}, Len: {len(resp.text)}", flush=True)
        if resp.status_code != 200: return
        
        local_path = get_local_path(url)
        full_path = os.path.join(OUTPUT_DIR, local_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        clean = clean_html(resp.text, url)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(clean)
            
    except Exception as e:
        print(f"Error processing {url}: {e}", flush=True)

def main():
    setup_directories()
    while url_queue:
        u = url_queue.pop(0)
        process_url(u)
        time.sleep(1)

if __name__ == '__main__':
    main()
