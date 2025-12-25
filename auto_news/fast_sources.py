"""
Auto News Pipeline - Fast Signal Sources
Detects trending topics from Reddit, Hacker News, and GitHub.
These are used as SIGNALS to boost priority of matching RSS articles.

Strategy: Signal → Find Real Source → Generate
- Reddit/HN tells us WHAT's trending
- We find the actual news article from RSS
- We generate from the real source with VIRAL priority
"""

import logging
import requests
from typing import Dict, List, Set, Optional
from datetime import datetime, timezone
import re

logger = logging.getLogger(__name__)

# Reddit subreddits to monitor
REDDIT_SUBREDDITS = [
    "technology",
    "artificial", 
    "MachineLearning",
    "programming"
]

# Minimum upvotes/score to consider "trending"
REDDIT_MIN_SCORE = 100
HN_MIN_SCORE = 50


def fetch_reddit_trending() -> List[Dict]:
    """
    Fetch hot posts from tech-related subreddits.
    Returns list of trending topics with keywords.
    """
    trending = []
    
    for subreddit in REDDIT_SUBREDDITS:
        try:
            url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=15"
            headers = {"User-Agent": "NewsRadar/1.0"}
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            posts = data.get("data", {}).get("children", [])
            
            for post in posts:
                post_data = post.get("data", {})
                score = post_data.get("score", 0)
                
                # Only high-engagement posts
                if score >= REDDIT_MIN_SCORE:
                    title = post_data.get("title", "")
                    trending.append({
                        "source": "reddit",
                        "subreddit": subreddit,
                        "title": title,
                        "score": score,
                        "url": f"https://reddit.com{post_data.get('permalink', '')}",
                        "keywords": extract_keywords(title),
                        "fetched_at": datetime.now(timezone.utc).isoformat()
                    })
            
            logger.info(f"Reddit r/{subreddit}: {len([p for p in trending if p['subreddit'] == subreddit])} trending posts")
            
        except Exception as e:
            logger.error(f"Error fetching Reddit r/{subreddit}: {e}")
    
    return trending


def fetch_hackernews_trending() -> List[Dict]:
    """
    Fetch top stories from Hacker News.
    Returns list of trending topics with keywords.
    """
    trending = []
    
    try:
        # Get top story IDs
        url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        story_ids = response.json()[:20]  # Top 20
        
        for story_id in story_ids:
            try:
                item_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                item_response = requests.get(item_url, timeout=5)
                item = item_response.json()
                
                if item and item.get("type") == "story":
                    score = item.get("score", 0)
                    
                    if score >= HN_MIN_SCORE:
                        title = item.get("title", "")
                        trending.append({
                            "source": "hackernews",
                            "title": title,
                            "score": score,
                            "url": item.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
                            "keywords": extract_keywords(title),
                            "fetched_at": datetime.now(timezone.utc).isoformat()
                        })
                        
            except Exception as e:
                logger.debug(f"Error fetching HN item {story_id}: {e}")
        
        logger.info(f"Hacker News: {len(trending)} trending stories")
        
    except Exception as e:
        logger.error(f"Error fetching Hacker News: {e}")
    
    return trending


def fetch_github_trending() -> List[Dict]:
    """
    Fetch trending repositories from GitHub.
    Uses the search API to find recently created repos with high stars.
    """
    trending = []
    
    try:
        # Search for recently created repos with stars, sorted by stars
        # This captures tools gaining traction
        url = "https://api.github.com/search/repositories"
        params = {
            "q": "created:>2024-12-01 stars:>50",
            "sort": "stars",
            "order": "desc",
            "per_page": 15
        }
        headers = {"Accept": "application/vnd.github.v3+json"}
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        repos = data.get("items", [])
        
        for repo in repos:
            name = repo.get("name", "")
            description = repo.get("description", "") or ""
            stars = repo.get("stargazers_count", 0)
            
            # Focus on AI/ML/tech tools
            full_text = f"{name} {description}".lower()
            tech_keywords = ["ai", "llm", "gpt", "ml", "machine learning", "neural", "agent", "automation"]
            
            if any(kw in full_text for kw in tech_keywords):
                trending.append({
                    "source": "github",
                    "title": f"{name}: {description[:100]}",
                    "score": stars,
                    "url": repo.get("html_url", ""),
                    "keywords": extract_keywords(f"{name} {description}"),
                    "language": repo.get("language", ""),
                    "fetched_at": datetime.now(timezone.utc).isoformat()
                })
        
        logger.info(f"GitHub: {len(trending)} trending AI/ML repos")
        
    except Exception as e:
        logger.error(f"Error fetching GitHub trending: {e}")
    
    return trending


def extract_keywords(text: str) -> Set[str]:
    """
    Extract meaningful keywords from text for matching.
    """
    # Convert to lowercase and extract words
    text = text.lower()
    words = re.findall(r'\b[a-z]{3,}\b', text)
    
    # Remove common stop words
    stop_words = {
        "the", "and", "for", "are", "but", "not", "you", "all", "can", "had",
        "her", "was", "one", "our", "out", "day", "get", "has", "him", "his",
        "how", "its", "may", "new", "now", "old", "see", "way", "who", "did",
        "been", "have", "from", "this", "that", "with", "they", "will", "what",
        "when", "your", "said", "each", "just", "like", "over", "such", "into",
        "year", "some", "could", "them", "than", "then", "being", "about", "after"
    }
    
    # High-value tech keywords to always keep
    tech_terms = {
        "openai", "google", "apple", "microsoft", "meta", "amazon", "nvidia",
        "tesla", "anthropic", "chatgpt", "gpt", "gemini", "claude", "waymo",
        "robotaxi", "autonomous", "robot", "drone", "model", "launch", "release",
        "acquisition", "funding", "startup", "developer", "programming", "code"
    }
    
    keywords = set()
    for word in words:
        if word in tech_terms or (word not in stop_words and len(word) > 3):
            keywords.add(word)
    
    return keywords


def get_all_trending_signals() -> Dict:
    """
    Fetch all trending signals from all sources.
    Returns organized data structure with all signals.
    """
    logger.info("Fetching trending signals from fast sources...")
    
    signals = {
        "reddit": fetch_reddit_trending(),
        "hackernews": fetch_hackernews_trending(),
        "github": fetch_github_trending(),
        "fetched_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Combine all keywords for matching
    all_keywords = set()
    for source in ["reddit", "hackernews", "github"]:
        for item in signals[source]:
            all_keywords.update(item.get("keywords", set()))
    
    signals["all_keywords"] = all_keywords
    
    total = len(signals["reddit"]) + len(signals["hackernews"]) + len(signals["github"])
    logger.info(f"Total trending signals: {total}")
    
    return signals


def match_article_to_signals(article: Dict, signals: Dict, min_matches: int = 2) -> Dict:
    """
    Check if an RSS article matches any trending signals.
    Returns match info if found, None otherwise.
    
    Args:
        article: RSS article with 'title' and 'summary'
        signals: Output from get_all_trending_signals()
        min_matches: Minimum keyword matches required
    
    Returns:
        Match info dict or None
    """
    article_text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
    article_keywords = extract_keywords(article_text)
    
    best_match = None
    best_score = 0
    
    # Check against each source
    for source in ["reddit", "hackernews", "github"]:
        for signal in signals.get(source, []):
            signal_keywords = signal.get("keywords", set())
            
            # Count keyword matches
            matches = article_keywords.intersection(signal_keywords)
            match_count = len(matches)
            
            if match_count >= min_matches:
                # Score based on matches and signal engagement
                score = match_count * signal.get("score", 1)
                
                if score > best_score:
                    best_score = score
                    best_match = {
                        "matched": True,
                        "signal_source": source,
                        "signal_title": signal.get("title", "")[:100],
                        "signal_score": signal.get("score", 0),
                        "matched_keywords": list(matches),
                        "match_strength": match_count,
                        "combined_score": score
                    }
    
    return best_match


def boost_viral_articles(articles: List[Dict], signals: Dict = None) -> List[Dict]:
    """
    Check articles against trending signals and boost matching ones to VIRAL priority.
    
    Args:
        articles: List of RSS articles
        signals: Pre-fetched signals (will fetch if None)
    
    Returns:
        Articles with viral matches boosted
    """
    if signals is None:
        signals = get_all_trending_signals()
    
    boosted_count = 0
    
    for article in articles:
        match = match_article_to_signals(article, signals)
        
        if match:
            # Mark as viral
            article['viral_match'] = match
            
            # If article has event_classification, boost priority
            if 'event_classification' in article:
                old_type = article['event_classification'].get('event_type', 'ROUTINE')
                if old_type == 'ROUTINE':
                    article['event_classification']['event_type'] = 'VIRAL'
                    article['event_classification']['priority'] = 2
                    article['event_classification']['viral_boost'] = True
                    boosted_count += 1
                    logger.info(f"VIRAL BOOST: {article.get('title', '')[:50]}... (matched: {match['signal_source']})")
    
    logger.info(f"Boosted {boosted_count} articles to VIRAL priority")
    
    return articles


if __name__ == "__main__":
    # Test the fast sources
    logging.basicConfig(level=logging.INFO)
    
    print("Testing Fast Signal Sources\n" + "="*50)
    
    signals = get_all_trending_signals()
    
    print(f"\n📱 Reddit: {len(signals['reddit'])} trending posts")
    for item in signals['reddit'][:3]:
        print(f"   [{item['score']}] {item['title'][:60]}...")
    
    print(f"\n🔶 Hacker News: {len(signals['hackernews'])} trending stories")
    for item in signals['hackernews'][:3]:
        print(f"   [{item['score']}] {item['title'][:60]}...")
    
    print(f"\n🐙 GitHub: {len(signals['github'])} trending repos")
    for item in signals['github'][:3]:
        print(f"   [{item['score']}⭐] {item['title'][:60]}...")
    
    print(f"\n🔑 Total unique keywords: {len(signals['all_keywords'])}")
