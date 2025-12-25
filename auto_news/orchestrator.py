"""
Auto News Pipeline - Main Orchestrator
Runs the complete pipeline: Fetch → Classify Events → Prioritize → Generate → Publish

NEW: Priority queue system that ensures breaking news beats routine updates.
"""

import logging
import sys
import argparse
from datetime import datetime, timezone
from typing import List, Dict

from .config import LOG_FILE, LOG_LEVEL, ARTICLE_CONFIG
from .rss_fetcher import fetch_and_process_feeds
from .classifier import classify_articles, filter_relevant_articles
from .event_classifier import classify_article, get_publishing_queues
from .article_generator import generate_full_article
from .image_generator import generate_image_for_article
from .publisher import publish_articles, article_exists

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Publishing limits per queue
QUEUE_LIMITS = {
    "breaking": 5,      # Publish ALL breaking news (up to 5)
    "high": 3,          # Publish up to 3 high-priority articles
    "routine": 1        # Only 1 routine article if no urgent news
}


def run_pipeline(
    test_mode: bool = False,
    limit: int = None,
    skip_images: bool = False
) -> Dict:
    """
    Run the complete news automation pipeline with priority queue system.
    
    NEW FLOW:
    1. Fetch RSS feeds
    2. Classify by topic relevance
    3. Classify by EVENT TYPE (BREAKING/ACQUISITION/LAYOFFS/FUNDING/ROUTINE)
    4. Organize into priority queues
    5. Process breaking queue first, then high, then routine
    
    Args:
        test_mode: If True, don't actually publish (dry run)
        limit: Maximum total articles to process (overrides queue limits)
        skip_images: Skip image generation
    
    Returns:
        Dict with pipeline results
    """
    start_time = datetime.now(timezone.utc)
    logger.info("=" * 60)
    logger.info(f"🚀 NEWS RADAR PIPELINE - {start_time.isoformat()}")
    logger.info("=" * 60)
    
    results = {
        "start_time": start_time.isoformat(),
        "articles_fetched": 0,
        "articles_classified": 0,
        "articles_relevant": 0,
        "breaking_count": 0,
        "high_priority_count": 0,
        "routine_count": 0,
        "articles_generated": 0,
        "articles_published": 0,
        "errors": [],
        "published_articles": []
    }
    
    try:
        # Step 1: Fetch RSS feeds
        logger.info("\n📡 Step 1: Fetching RSS feeds...")
        articles = fetch_and_process_feeds()
        results["articles_fetched"] = len(articles)
        logger.info(f"Fetched {len(articles)} articles")
        
        if not articles:
            logger.warning("No articles fetched. Exiting.")
            return results
        
        # Step 2: Classify articles by topic
        logger.info("\n🔍 Step 2: Classifying by topic...")
        articles = classify_articles(articles)
        results["articles_classified"] = len(articles)
        
        # Step 3: Filter relevant articles
        logger.info("\n🎯 Step 3: Filtering relevant articles...")
        relevant = filter_relevant_articles(articles)
        results["articles_relevant"] = len(relevant)
        logger.info(f"Found {len(relevant)} relevant articles")
        
        if not relevant:
            logger.warning("No relevant articles found. Exiting.")
            return results
        
        # Filter out already published articles EARLY
        new_articles = [a for a in relevant if not article_exists(a['id'])]
        skipped = len(relevant) - len(new_articles)
        if skipped > 0:
            logger.info(f"Skipping {skipped} already published articles")
        
        if not new_articles:
            logger.info("All articles already published. Exiting.")
            return results
        
        # Step 4: EVENT CLASSIFICATION (NEW!)
        logger.info("\n⚡ Step 4: Classifying by EVENT TYPE...")
        for article in new_articles:
            classify_article(article, use_groq=True)
        
        # Step 5: Organize into priority queues
        logger.info("\n📊 Step 5: Organizing priority queues...")
        queues = get_publishing_queues(new_articles)
        
        results["breaking_count"] = len(queues["breaking"])
        results["high_priority_count"] = len(queues["high"])
        results["routine_count"] = len(queues["routine"])
        
        logger.info(f"  🔴 BREAKING: {len(queues['breaking'])} articles")
        logger.info(f"  🟡 HIGH:     {len(queues['high'])} articles")
        logger.info(f"  ⚪ ROUTINE:  {len(queues['routine'])} articles")
        
        # Build processing list based on queue priority
        to_process = []
        
        # Breaking news: process ALL (up to limit)
        breaking_limit = QUEUE_LIMITS["breaking"]
        for article in queues["breaking"][:breaking_limit]:
            to_process.append(article)
            logger.info(f"  🔴 BREAKING: {article['title'][:50]}...")
        
        # High priority: process if room
        high_limit = QUEUE_LIMITS["high"]
        for article in queues["high"][:high_limit]:
            to_process.append(article)
            logger.info(f"  🟡 HIGH: {article['title'][:50]}...")
        
        # Routine: only if no urgent news
        if len(queues["breaking"]) == 0 and len(queues["high"]) == 0:
            routine_limit = QUEUE_LIMITS["routine"]
            for article in queues["routine"][:routine_limit]:
                to_process.append(article)
                logger.info(f"  ⚪ ROUTINE: {article['title'][:50]}...")
        elif len(to_process) < 2:
            # If very few articles, add one routine
            for article in queues["routine"][:1]:
                to_process.append(article)
                logger.info(f"  ⚪ ROUTINE (filler): {article['title'][:50]}...")
        
        # Apply manual limit if specified
        if limit:
            to_process = to_process[:limit]
        
        if not to_process:
            logger.info("No articles to process after queue filtering.")
            return results
        
        logger.info(f"\n📝 Processing {len(to_process)} total articles")
        
        # Step 6: Generate articles
        logger.info("\n✍️ Step 6: Generating articles...")
        generated_articles = []
        
        for i, article in enumerate(to_process, 1):
            ec = article.get('event_classification', {})
            event_type = ec.get('event_type', 'UNKNOWN')
            
            logger.info(f"\n--- [{event_type}] Article {i}/{len(to_process)} ---")
            logger.info(f"Title: {article['title'][:60]}...")
            
            try:
                # Generate article content
                generated = generate_full_article(article)
                
                if generated:
                    # Carry over event classification
                    generated['event_classification'] = ec
                    
                    # Generate featured image
                    if not skip_images:
                        logger.info("🖼️ Generating featured image...")
                        generated = generate_image_for_article(generated)
                    else:
                        generated['featured_image'] = {
                            "generated": False,
                            "assets_path": "assets/GD.PNG"
                        }
                    
                    generated_articles.append(generated)
                    logger.info(f"✅ Generated: {generated['metadata']['slug']}")
                else:
                    logger.error(f"Failed to generate: {article['title'][:50]}")
                    results["errors"].append(f"Generation failed: {article['id']}")
                    
            except Exception as e:
                logger.error(f"Error processing article: {e}")
                results["errors"].append(f"Error: {article['id']} - {str(e)}")
        
        results["articles_generated"] = len(generated_articles)
        
        if not generated_articles:
            logger.warning("No articles generated. Exiting.")
            return results
        
        # Step 7: Publish articles
        if test_mode:
            logger.info("\n🧪 TEST MODE: Skipping publish step")
            for article in generated_articles:
                ec = article.get('event_classification', {})
                logger.info(f"  Would publish: [{ec.get('event_type', '?')}] {article['metadata']['slug']}")
                results["published_articles"].append({
                    "slug": article['metadata']['slug'],
                    "title": article['title'],
                    "event_type": ec.get('event_type', 'UNKNOWN')
                })
        else:
            logger.info("\n📤 Step 7: Publishing articles...")
            published_count = publish_articles(generated_articles)
            results["articles_published"] = published_count
            
            for article in generated_articles:
                ec = article.get('event_classification', {})
                results["published_articles"].append({
                    "slug": article['metadata']['slug'],
                    "title": article['title'],
                    "event_type": ec.get('event_type', 'UNKNOWN')
                })
        
    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        results["errors"].append(str(e))
    
    # Finalize
    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()
    results["end_time"] = end_time.isoformat()
    results["duration_seconds"] = duration
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 PIPELINE SUMMARY")
    logger.info("=" * 60)
    logger.info(f"  Articles Fetched:    {results['articles_fetched']}")
    logger.info(f"  Articles Relevant:   {results['articles_relevant']}")
    logger.info(f"  🔴 Breaking News:    {results['breaking_count']}")
    logger.info(f"  🟡 High Priority:    {results['high_priority_count']}")
    logger.info(f"  ⚪ Routine:          {results['routine_count']}")
    logger.info(f"  Articles Generated:  {results['articles_generated']}")
    logger.info(f"  Articles Published:  {results['articles_published']}")
    logger.info(f"  Duration:            {duration:.1f} seconds")
    logger.info(f"  Errors:              {len(results['errors'])}")
    
    if results["published_articles"]:
        logger.info("\n📝 Published Articles:")
        for article in results["published_articles"]:
            logger.info(f"  [{article.get('event_type', '?')}] {article['title'][:50]}...")
    
    logger.info("=" * 60)
    
    return results


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description='Auto News Radar Pipeline')
    parser.add_argument('--test', action='store_true', help='Test mode (no publishing)')
    parser.add_argument('--limit', type=int, help='Max articles to process')
    parser.add_argument('--skip-images', action='store_true', help='Skip image generation')
    
    args = parser.parse_args()
    
    results = run_pipeline(
        test_mode=args.test,
        limit=args.limit,
        skip_images=args.skip_images
    )
    
    # Exit with error code if no articles published (useful for CI)
    if results["articles_published"] == 0 and not args.test:
        if results["errors"]:
            sys.exit(1)
    
    return results


if __name__ == "__main__":
    main()
