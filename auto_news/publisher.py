"""
Auto News Pipeline - Static Site Publisher
Generates HTML files and updates the site index.
"""

import logging
import json
import re
from typing import Dict, List, Optional
from datetime import datetime, timezone
from pathlib import Path
from jinja2 import Template
import markdown

from .config import (
    SITE_DIR, ARTICLES_DIR, ASSETS_DIR, DATA_DIR,
    SITE_NAME, SITE_URL, AUTHOR_NAME
)

logger = logging.getLogger(__name__)

# Article history file
ARTICLES_DB = DATA_DIR / "articles.json"


def markdown_to_html(content: str) -> str:
    """Convert markdown content to HTML."""
    # Convert markdown to HTML
    html = markdown.markdown(content, extensions=['extra', 'codehilite', 'toc'])
    return html


def get_article_template() -> str:
    """
    HTML template for article pages.
    Matches the existing GlobalDigitalTimes design.
    """
    return '''<!DOCTYPE html>
<html dir="ltr" lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ meta_title }} | {{ site_name }}</title>
    <meta name="description" content="{{ meta_description }}">
    <meta name="keywords" content="{{ keywords }}">
    <meta name="author" content="{{ author }}">
    
    <!-- Open Graph -->
    <meta property="og:title" content="{{ og_title }}">
    <meta property="og:description" content="{{ og_description }}">
    <meta property="og:image" content="{{ site_url }}/{{ image_path }}">
    <meta property="og:url" content="{{ site_url }}/articles/{{ slug }}.html">
    <meta property="og:type" content="article">
    
    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{{ og_title }}">
    <meta name="twitter:description" content="{{ og_description }}">
    <meta name="twitter:image" content="{{ site_url }}/{{ image_path }}">
    
    <!-- Canonical -->
    <link rel="canonical" href="{{ site_url }}/articles/{{ slug }}.html">
    
    <!-- Favicon -->
    <link href="../assets/GLOB.png" rel="icon" type="image/png">
    
    <!-- Styles -->
    <link href="../assets/1SOFpFkUmGg.css" rel="stylesheet">
    <style>
        body { font-family: Roboto, Arial, sans-serif; line-height: 1.6; color: #333; }
        .article-container { max-width: 800px; margin: 0 auto; padding: 20px; }
        .article-header { margin-bottom: 30px; }
        .article-title { font-size: 2em; color: #000; margin-bottom: 10px; }
        .article-meta { color: #666; font-size: 0.9em; margin-bottom: 20px; }
        .article-image { width: 100%; max-height: 400px; object-fit: cover; border-radius: 8px; margin-bottom: 20px; }
        .article-content { font-size: 1.1em; }
        .article-content h2 { color: #B51200; margin-top: 30px; }
        .article-content h3 { color: #333; margin-top: 20px; }
        .article-content p { margin-bottom: 15px; }
        .article-content blockquote { border-left: 4px solid #B51200; padding-left: 20px; margin: 20px 0; font-style: italic; }
        .article-content ul, .article-content ol { margin-bottom: 15px; padding-left: 30px; }
        .article-footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; }
        .back-link { color: #B51200; text-decoration: none; }
        .back-link:hover { text-decoration: underline; }
        .reading-time { color: #888; }
        .source-link { color: #B51200; }
        
        @media (max-width: 600px) {
            .article-title { font-size: 1.5em; }
            .article-content { font-size: 1em; }
        }
    </style>
    
    <!-- Schema.org -->
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": "{{ site_url }}/articles/{{ slug }}.html"
        },
        "headline": "{{ title }}",
        "description": "{{ meta_description }}",
        "image": "{{ site_url }}/{{ image_path }}",
        "author": {
            "@type": "Organization",
            "name": "{{ author }}"
        },
        "publisher": {
            "@type": "Organization",
            "name": "{{ site_name }}",
            "logo": {
                "@type": "ImageObject",
                "url": "{{ site_url }}/assets/GLOB.png"
            }
        },
        "datePublished": "{{ published_date }}",
        "dateModified": "{{ published_date }}"
    }
    </script>
</head>
<body>
    <!-- Header -->
    <div id="header-container" style="background: #fff; padding: 10px 0; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
        <div style="max-width: 1000px; margin: 0 auto; padding: 0 20px;">
            <a href="../index.html" style="text-decoration: none;">
                <img src="../assets/GLOB.png" alt="{{ site_name }}" height="50">
            </a>
        </div>
    </div>
    
    <!-- Article -->
    <main class="article-container">
        <article>
            <header class="article-header">
                <h1 class="article-title">{{ title }}</h1>
                <div class="article-meta">
                    <span>{{ site_name }}</span> • 
                    <span>{{ formatted_date }}</span> • 
                    <span class="reading-time">{{ reading_time }} min read</span>
                </div>
            </header>
            
            <img class="article-image" src="../{{ image_path }}" alt="{{ image_alt }}">
            
            <div class="article-content">
                {{ content_html | safe }}
            </div>
            
            <footer class="article-footer">
                <p><a href="../index.html" class="back-link">← Back to Home</a></p>
                <p style="color: #666; font-size: 0.9em;">
                    Originally sourced from: <a href="{{ original_link }}" class="source-link" target="_blank">{{ original_source }}</a>
                </p>
            </footer>
        </article>
    </main>
    
    <!-- Footer -->
    <footer style="background: #f5f5f5; padding: 20px; text-align: center; margin-top: 40px;">
        <p style="color: #666;">© {{ year }} {{ site_name }}. All rights reserved.</p>
    </footer>
</body>
</html>'''


def generate_article_html(article: Dict) -> str:
    """Generate HTML for an article."""
    template = Template(get_article_template())
    
    metadata = article.get('metadata', {})
    image = article.get('featured_image', {})
    
    # Convert markdown content to HTML
    content_html = markdown_to_html(article.get('content', ''))
    
    # Format date
    generated_at = article.get('generated_at', datetime.now(timezone.utc).isoformat())
    try:
        dt = datetime.fromisoformat(generated_at.replace('Z', '+00:00'))
        formatted_date = dt.strftime('%B %d, %Y')
        published_date = dt.isoformat()
    except:
        formatted_date = datetime.now().strftime('%B %d, %Y')
        published_date = datetime.now(timezone.utc).isoformat()
    
    html = template.render(
        title=article.get('title', ''),
        meta_title=metadata.get('meta_title', article.get('title', '')),
        meta_description=metadata.get('meta_description', '')[:160],
        og_title=metadata.get('og_title', article.get('title', '')),
        og_description=metadata.get('og_description', '')[:200],
        keywords=', '.join(metadata.get('keywords', [])),
        slug=metadata.get('slug', 'article'),
        image_path=image.get('assets_path', 'assets/GD.PNG'),
        image_alt=metadata.get('image_alt', f"Featured image for {article.get('title', '')}"),
        content_html=content_html,
        author=AUTHOR_NAME,
        site_name=SITE_NAME,
        site_url=SITE_URL,
        reading_time=metadata.get('reading_time_minutes', 5),
        formatted_date=formatted_date,
        published_date=published_date,
        original_link=article.get('original_link', '#'),
        original_source=article.get('original_source', 'Source'),
        year=datetime.now().year
    )
    
    return html


def save_article_html(article: Dict) -> Optional[Path]:
    """Save article HTML to file."""
    slug = article.get('metadata', {}).get('slug', article.get('id', 'article'))
    filename = f"{slug}.html"
    filepath = ARTICLES_DIR / filename
    
    try:
        html = generate_article_html(article)
        filepath.write_text(html, encoding='utf-8')
        logger.info(f"Saved article: {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Error saving article HTML: {e}")
        return None


def get_index_article_entry(article: Dict) -> str:
    """Generate HTML snippet for the index page."""
    metadata = article.get('metadata', {})
    image = article.get('featured_image', {})
    slug = metadata.get('slug', 'article')
    
    # Truncate summary
    content = article.get('content', '')
    summary = content[:150].rsplit(' ', 1)[0] + '...' if len(content) > 150 else content
    # Remove markdown
    summary = re.sub(r'[#*_`\[\]]', '', summary)
    summary = re.sub(r'\n+', ' ', summary)
    
    return f'''
              <div class="post-outer">
                <article class="post">
                  <div class="img-thumbnail-wrap">
                    <div class="img-thumbnail" style="overflow: hidden; display: flex; align-items: center; justify-content: center;">
                      <a href="articles/{slug}.html">
                        <img alt="{article.get('title', '')}" style="width: 100%; height: 162px; object-fit: cover; object-position: center;" src="{image.get('assets_path', 'assets/GD.PNG')}"
                          title="{article.get('title', '')}">
                        <div class="lazy-loading"></div>
                      </a>
                    </div>
                  </div>
                  <h2 class="post-title entry-title">
                    <a href="articles/{slug}.html">{article.get('title', '')}</a>
                  </h2>
                  <div class="post-body entry-content">
                    <div class="post-snippet">
                      {summary}
                      <a class="read-more-link" href="articles/{slug}.html" title="{article.get('title', '')}">
                        Read more »
                      </a>
                    </div>
                  </div>
                  <div class="post-info info-1">
                  </div>
                </article>
              </div>'''


def update_index_page(articles: List[Dict]) -> bool:
    """Add new articles to the index.html page."""
    index_path = SITE_DIR / "index.html"
    
    try:
        # Read current index
        content = index_path.read_text(encoding='utf-8')
        
        # Generate new article entries
        new_entries = '\n'.join([get_index_article_entry(a) for a in articles])
        
        # Find insertion point (after "blog-posts" div opening)
        # Insert after the "Postingan Terbaru" section
        marker = '<div class="blog-posts">'
        if marker in content:
            parts = content.split(marker, 1)
            # Insert our new articles right after the blog-posts div
            new_content = parts[0] + marker + '\n' + new_entries + parts[1]
            
            index_path.write_text(new_content, encoding='utf-8')
            logger.info(f"Updated index.html with {len(articles)} new articles")
            return True
        else:
            logger.warning("Could not find insertion point in index.html")
            return False
            
    except Exception as e:
        logger.error(f"Error updating index.html: {e}")
        return False


def load_articles_db() -> Dict:
    """Load the articles database."""
    if ARTICLES_DB.exists():
        try:
            return json.loads(ARTICLES_DB.read_text(encoding='utf-8'))
        except:
            pass
    return {"articles": [], "last_updated": None}


def save_articles_db(db: Dict) -> bool:
    """Save the articles database."""
    try:
        db['last_updated'] = datetime.now(timezone.utc).isoformat()
        ARTICLES_DB.write_text(json.dumps(db, indent=2), encoding='utf-8')
        return True
    except Exception as e:
        logger.error(f"Error saving articles database: {e}")
        return False


def article_exists(article_id: str) -> bool:
    """Check if an article already exists."""
    db = load_articles_db()
    return any(a.get('id') == article_id for a in db.get('articles', []))


def save_article_to_db(article: Dict) -> bool:
    """Save article metadata to the database."""
    db = load_articles_db()
    
    # Add summary entry (not full content)
    entry = {
        "id": article.get('id'),
        "title": article.get('title'),
        "slug": article.get('metadata', {}).get('slug'),
        "original_link": article.get('original_link'),
        "original_source": article.get('original_source'),
        "topic": article.get('classification', {}).get('primary_topic'),
        "generated_at": article.get('generated_at'),
        "word_count": article.get('word_count')
    }
    
    db['articles'].insert(0, entry)  # Add to beginning
    
    # Keep only last 500 articles
    db['articles'] = db['articles'][:500]
    
    return save_articles_db(db)


def publish_article(article: Dict) -> bool:
    """
    Main function: Publish an article to the static site.
    """
    logger.info(f"Publishing: {article.get('title', '')[:50]}...")
    
    # Check if already published
    if article_exists(article.get('id')):
        logger.warning(f"Article already exists: {article.get('id')}")
        return False
    
    # Save article HTML
    filepath = save_article_html(article)
    if not filepath:
        return False
    
    # Save to database
    save_article_to_db(article)
    
    logger.info(f"Article published: {filepath.name}")
    return True


def publish_articles(articles: List[Dict]) -> int:
    """Publish multiple articles and update index."""
    published_count = 0
    published_articles = []
    
    for article in articles:
        if publish_article(article):
            published_count += 1
            published_articles.append(article)
    
    # Update index page
    if published_articles:
        update_index_page(published_articles)
        
        # Update sitemap.xml
        try:
            from .sitemap_generator import update_sitemap
            update_sitemap()
            logger.info("Sitemap updated")
        except Exception as e:
            logger.warning(f"Sitemap update failed: {e}")
    
    logger.info(f"Published {published_count} articles")
    return published_count


if __name__ == "__main__":
    # Test the publisher
    logging.basicConfig(level=logging.INFO)
    
    test_article = {
        "id": "test123",
        "title": "Test Article: AI Revolution in 2024",
        "content": "# Test Article\n\nThis is a test article about AI.\n\n## Introduction\n\nAI is changing the world...",
        "original_link": "https://example.com",
        "original_source": "Test Source",
        "metadata": {
            "slug": "test-ai-revolution-2024",
            "meta_title": "Test Article: AI Revolution",
            "meta_description": "A test article about AI",
            "og_title": "Test Article",
            "og_description": "Test description",
            "keywords": ["AI", "test"],
            "image_alt": "AI concept image",
            "reading_time_minutes": 3
        },
        "featured_image": {
            "assets_path": "assets/GD.PNG"
        },
        "classification": {
            "primary_topic": "AI"
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "word_count": 100
    }
    
    html = generate_article_html(test_article)
    print(f"Generated HTML length: {len(html)} characters")
    print(f"\nFirst 500 chars:\n{html[:500]}...")
