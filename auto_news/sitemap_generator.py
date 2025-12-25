"""
Auto News Pipeline - Sitemap Generator
Automatically generates/updates sitemap.xml when articles are published.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from .config import SITE_DIR, SITE_URL, DATA_DIR

SITEMAP_PATH = SITE_DIR / "sitemap.xml"
ARTICLES_JSON = DATA_DIR / "articles.json"


def generate_sitemap() -> str:
    """
    Generate sitemap.xml content from articles.json.
    Called automatically after publishing new articles.
    """
    
    # Load published articles
    articles = []
    if ARTICLES_JSON.exists():
        with open(ARTICLES_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
            articles = data.get('articles', [])
    
    # Start XML
    xml = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    xml.append('        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">')
    
    # Homepage
    xml.append('  <url>')
    xml.append(f'    <loc>{SITE_URL}/</loc>')
    xml.append('    <changefreq>hourly</changefreq>')
    xml.append('    <priority>1.0</priority>')
    xml.append('  </url>')
    
    # Articles
    for article in articles:
        slug = article.get('slug', '')
        generated_at = article.get('generated_at', '')
        
        # Parse date for lastmod
        try:
            dt = datetime.fromisoformat(generated_at.replace('Z', '+00:00'))
            lastmod = dt.strftime('%Y-%m-%d')
        except:
            lastmod = datetime.now().strftime('%Y-%m-%d')
        
        xml.append('  <url>')
        xml.append(f'    <loc>{SITE_URL}/articles/{slug}.html</loc>')
        xml.append(f'    <lastmod>{lastmod}</lastmod>')
        xml.append('    <changefreq>weekly</changefreq>')
        xml.append('    <priority>0.8</priority>')
        xml.append('  </url>')
    
    # Trust pages
    trust_pages = ['about.html', 'privacy.html', 'editorial-policy.html']
    for page in trust_pages:
        xml.append('  <url>')
        xml.append(f'    <loc>{SITE_URL}/{page}</loc>')
        xml.append('    <changefreq>monthly</changefreq>')
        xml.append('    <priority>0.4</priority>')
        xml.append('  </url>')
    
    xml.append('</urlset>')
    
    return '\n'.join(xml)


def update_sitemap() -> None:
    """
    Update the sitemap.xml file.
    """
    content = generate_sitemap()
    
    with open(SITEMAP_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Sitemap updated: {SITEMAP_PATH}")
    print(f"Total URLs: {content.count('<url>')}")


if __name__ == "__main__":
    update_sitemap()
