"""
Regenerate Articles Script
Regenerates articles that failed or are incomplete.
"""

import json
import logging
import time
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import article generation and publishing
from auto_news.article_generator import generate_full_article
from auto_news.publisher import save_article_html, update_index_page, load_articles_db
from auto_news.image_generator import generate_featured_image

# Paths
SITE_DIR = Path("revived_site")
ARTICLES_DIR = SITE_DIR / "articles"
DATA_DIR = Path("data")
ARTICLES_DB = DATA_DIR / "articles.json"

# Minimum word count threshold - articles below this are considered incomplete
MIN_WORD_COUNT = 500


def get_incomplete_articles():
    """Find articles with incomplete content (word count < threshold)."""
    incomplete = []
    
    for html_file in ARTICLES_DIR.glob("*.html"):
        content = html_file.read_text(encoding='utf-8')
        
        # Extract article body text (rough estimate)
        # Count words in the article-content div
        if 'class="article-content"' in content:
            start = content.find('class="article-content"')
            end = content.find('</footer>', start)
            body = content[start:end] if end > start else ""
            
            # Strip HTML tags for word count
            import re
            text = re.sub(r'<[^>]+>', ' ', body)
            word_count = len(text.split())
            
            if word_count < MIN_WORD_COUNT:
                logger.info(f"Incomplete: {html_file.name} ({word_count} words)")
                incomplete.append({
                    'file': html_file,
                    'slug': html_file.stem,
                    'word_count': word_count
                })
    
    return incomplete


def get_article_source_info(slug: str):
    """Get original source info from articles.json."""
    if ARTICLES_DB.exists():
        db = json.loads(ARTICLES_DB.read_text(encoding='utf-8'))
        for article in db.get('articles', []):
            if article.get('slug') == slug:
                return article
    return None


def regenerate_article(source_info: dict):
    """
    Regenerate a single article from its source info.
    """
    if not source_info:
        return None
    
    # Build article input from source info
    article_input = {
        'id': source_info.get('id', f"regen-{source_info['slug']}"),
        'title': source_info.get('title', 'Article'),
        'summary': source_info.get('title', 'Article summary'),  # Fallback
        'link': source_info.get('original_link', '#'),
        'source': source_info.get('original_source', 'Unknown'),
        'classification': {
            'primary_topic': source_info.get('topic', 'Technology'),
            'relevance_score': 90
        }
    }
    
    logger.info(f"Regenerating: {article_input['title'][:50]}...")
    
    try:
        # Generate full article
        generated = generate_full_article(article_input)
        
        if not generated or generated.get('word_count', 0) < MIN_WORD_COUNT:
            logger.error(f"Failed to generate sufficient content")
            return None
        
        # Generate image
        image_result = generate_featured_image(generated)
        if image_result:
            generated['featured_image'] = image_result
        
        # Save HTML
        filepath = save_article_html(generated)
        
        if filepath:
            logger.info(f"Regenerated: {filepath.name} ({generated['word_count']} words)")
            return generated
        
    except Exception as e:
        logger.error(f"Error regenerating article: {e}")
    
    return None


def regenerate_all_incomplete():
    """Regenerate all incomplete articles."""
    incomplete = get_incomplete_articles()
    
    if not incomplete:
        logger.info("No incomplete articles found!")
        return
    
    logger.info(f"Found {len(incomplete)} incomplete articles to regenerate")
    
    regenerated = []
    for i, article in enumerate(incomplete):
        logger.info(f"\n[{i+1}/{len(incomplete)}] Processing: {article['slug']}")
        
        # Get source info
        source_info = get_article_source_info(article['slug'])
        
        if not source_info:
            logger.warning(f"No source info found for {article['slug']}")
            continue
        
        # Wait between articles to prevent rate limiting
        if i > 0:
            logger.info("Waiting 10s before next article...")
            time.sleep(10)
        
        # Regenerate
        result = regenerate_article(source_info)
        if result:
            regenerated.append(result)
    
    logger.info(f"\nRegenerated {len(regenerated)}/{len(incomplete)} articles")
    return regenerated


if __name__ == "__main__":
    regenerate_all_incomplete()
