"""
Auto News Pipeline - Main Orchestrator
Runs the complete pipeline: Fetch → Classify → Generate → Publish
"""

import logging
import sys
import argparse
from datetime import datetime, timezone
from typing import List, Dict

from .config import LOG_FILE, LOG_LEVEL, ARTICLE_CONFIG
from .rss_fetcher import fetch_and_process_feeds
from .classifier import classify_articles, filter_relevant_articles, select_top_articles
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


def run_pipeline(
    test_mode: bool = False,
    limit: int = None,
    skip_images: bool = False
) -> Dict:
    """
    Run the complete news automation pipeline.
    
    Args:
        test_mode: If True, don't actually publish (dry run)
        limit: Maximum number of articles to process
        skip_images: Skip image generation
    
    Returns:
        Dict with pipeline results
    """
    start_time = datetime.now(timezone.utc)
    logger.info("=" * 60)
    logger.info(f"Starting Auto News Pipeline - {start_time.isoformat()}")
    logger.info("=" * 60)
    
    results = {
        "start_time": start_time.isoformat(),
        "articles_fetched": 0,
        "articles_classified": 0,
        "articles_relevant": 0,
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
        
        # Step 2: Classify articles
        logger.info("\n🔍 Step 2: Classifying articles...")
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
        
        # Step 4: Select top articles for processing
        max_articles = limit or ARTICLE_CONFIG['articles_per_run']
        selected = select_top_articles(relevant, max_articles)
        logger.info(f"Selected top {len(selected)} articles for processing")
        
        # Filter out already published articles
        new_articles = [a for a in selected if not article_exists(a['id'])]
        if len(new_articles) < len(selected):
            logger.info(f"Skipping {len(selected) - len(new_articles)} already published articles")
        
        if not new_articles:
            logger.info("All selected articles already published. Exiting.")
            return results
        
        # Step 5: Generate full articles
        logger.info("\n✍️ Step 5: Generating articles...")
        generated_articles = []
        
        for i, article in enumerate(new_articles, 1):
            logger.info(f"\n--- Processing article {i}/{len(new_articles)} ---")
            logger.info(f"Title: {article['title'][:60]}...")
            
            try:
                # Generate article content
                generated = generate_full_article(article)
                
                if generated:
                    # Step 6: Generate featured image
                    if not skip_images:
                        logger.info("🖼️ Generating featured image...")
                        generated = generate_image_for_article(generated)
                    else:
                        generated['featured_image'] = {
                            "generated": False,
                            "assets_path": "assets/GD.PNG"
                        }
                    
                    generated_articles.append(generated)
                    logger.info(f"✅ Article generated: {generated['metadata']['slug']}")
                else:
                    logger.error(f"Failed to generate article: {article['title'][:50]}")
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
                logger.info(f"  Would publish: {article['metadata']['slug']}")
                results["published_articles"].append({
                    "slug": article['metadata']['slug'],
                    "title": article['title']
                })
        else:
            logger.info("\n📤 Step 7: Publishing articles...")
            published_count = publish_articles(generated_articles)
            results["articles_published"] = published_count
            
            for article in generated_articles:
                results["published_articles"].append({
                    "slug": article['metadata']['slug'],
                    "title": article['title']
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
    logger.info(f"  Articles Classified: {results['articles_classified']}")
    logger.info(f"  Articles Relevant:   {results['articles_relevant']}")
    logger.info(f"  Articles Generated:  {results['articles_generated']}")
    logger.info(f"  Articles Published:  {results['articles_published']}")
    logger.info(f"  Duration:            {duration:.1f} seconds")
    logger.info(f"  Errors:              {len(results['errors'])}")
    
    if results["published_articles"]:
        logger.info("\n📝 Published Articles:")
        for article in results["published_articles"]:
            logger.info(f"  - {article['title'][:50]}...")
    
    logger.info("=" * 60)
    
    return results


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description='Auto News Pipeline')
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
