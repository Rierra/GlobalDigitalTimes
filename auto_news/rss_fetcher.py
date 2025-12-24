"""
Auto News Pipeline - RSS Fetcher
Fetches and normalizes articles from multiple RSS feeds.
"""

import feedparser
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib

from .config import RSS_FEEDS, ARTICLE_CONFIG

logger = logging.getLogger(__name__)


def parse_date(date_string: str) -> Optional[datetime]:
    """Parse various date formats from RSS feeds."""
    if not date_string:
        return None
    
    # feedparser provides struct_time, convert to datetime
    try:
        if hasattr(date_string, 'tm_year'):
            return datetime(*date_string[:6], tzinfo=timezone.utc)
    except:
        pass
    
    # Try common formats
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    
    return None


def generate_article_id(url: str) -> str:
    """Generate a unique ID for an article based on its URL."""
    return hashlib.md5(url.encode()).hexdigest()[:12]


def fetch_single_feed(feed_info: Dict) -> List[Dict]:
    """Fetch articles from a single RSS feed."""
    articles = []
    
    try:
        logger.info(f"Fetching: {feed_info['name']}")
        feed = feedparser.parse(feed_info['url'])
        
        if feed.bozo and feed.bozo_exception:
            logger.warning(f"Feed error for {feed_info['name']}: {feed.bozo_exception}")
        
        for entry in feed.entries:
            # Parse publication date
            pub_date = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                pub_date = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
            
            # Extract article data
            article = {
                "id": generate_article_id(entry.get('link', '')),
                "title": entry.get('title', '').strip(),
                "link": entry.get('link', ''),
                "summary": entry.get('summary', entry.get('description', '')).strip(),
                "published": pub_date,
                "source": feed_info['name'],
                "source_category": feed_info['category'],
                "author": entry.get('author', feed_info['name']),
            }
            
            # Only include if we have required fields
            if article['title'] and article['link']:
                articles.append(article)
        
        logger.info(f"Fetched {len(articles)} articles from {feed_info['name']}")
        
    except Exception as e:
        logger.error(f"Error fetching {feed_info['name']}: {e}")
    
    return articles


def fetch_all_feeds(feeds: List[Dict] = None) -> List[Dict]:
    """Fetch articles from all RSS feeds concurrently."""
    if feeds is None:
        feeds = RSS_FEEDS
    
    all_articles = []
    
    # Use ThreadPoolExecutor for concurrent fetching
    with ThreadPoolExecutor(max_workers=6) as executor:
        future_to_feed = {
            executor.submit(fetch_single_feed, feed): feed 
            for feed in feeds
        }
        
        for future in as_completed(future_to_feed):
            articles = future.result()
            all_articles.extend(articles)
    
    logger.info(f"Total articles fetched: {len(all_articles)}")
    return all_articles


def filter_recent_articles(articles: List[Dict], hours: int = None) -> List[Dict]:
    """Filter articles to only include those from the last N hours."""
    if hours is None:
        hours = ARTICLE_CONFIG['hours_lookback']
    
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    recent = []
    for article in articles:
        if article['published'] and article['published'] > cutoff:
            recent.append(article)
        elif not article['published']:
            # Include articles without dates (assume recent)
            recent.append(article)
    
    logger.info(f"Filtered to {len(recent)} articles from last {hours} hours")
    return recent


def deduplicate_articles(articles: List[Dict]) -> List[Dict]:
    """Remove duplicate articles based on URL."""
    seen_urls = set()
    unique = []
    
    for article in articles:
        if article['link'] not in seen_urls:
            seen_urls.add(article['link'])
            unique.append(article)
    
    logger.info(f"Deduplicated: {len(articles)} -> {len(unique)} articles")
    return unique


def clean_html(text: str) -> str:
    """Remove HTML tags from text."""
    import re
    clean = re.sub(r'<[^>]+>', '', text)
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()


def normalize_articles(articles: List[Dict]) -> List[Dict]:
    """Normalize article data for processing."""
    for article in articles:
        # Clean HTML from summary
        if article.get('summary'):
            article['summary'] = clean_html(article['summary'])
            # Truncate very long summaries
            if len(article['summary']) > 500:
                article['summary'] = article['summary'][:500] + '...'
        
        # Clean title
        if article.get('title'):
            article['title'] = clean_html(article['title'])
    
    return articles


def fetch_and_process_feeds() -> List[Dict]:
    """
    Main function: Fetch all feeds, filter, deduplicate, and normalize.
    Returns processed articles ready for classification.
    """
    logger.info("Starting RSS fetch pipeline...")
    
    # Fetch all feeds
    articles = fetch_all_feeds()
    
    # Filter to recent articles
    articles = filter_recent_articles(articles)
    
    # Remove duplicates
    articles = deduplicate_articles(articles)
    
    # Normalize content
    articles = normalize_articles(articles)
    
    # Sort by date (newest first)
    articles.sort(
        key=lambda x: x['published'] if x['published'] else datetime.min.replace(tzinfo=timezone.utc),
        reverse=True
    )
    
    logger.info(f"RSS pipeline complete: {len(articles)} articles ready for processing")
    return articles


if __name__ == "__main__":
    # Test the fetcher
    logging.basicConfig(level=logging.INFO)
    articles = fetch_and_process_feeds()
    
    print(f"\n{'='*60}")
    print(f"Fetched {len(articles)} articles")
    print(f"{'='*60}\n")
    
    for i, article in enumerate(articles[:5], 1):
        print(f"{i}. [{article['source']}] {article['title']}")
        print(f"   Published: {article['published']}")
        print(f"   Link: {article['link'][:60]}...")
        print()
