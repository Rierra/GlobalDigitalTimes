"""
Auto News Pipeline - AI Classifier
Uses Groq to classify articles by relevance to target topics.
"""

import logging
from typing import List, Dict, Optional
from groq import Groq

from .config import GROQ_API_KEY, GROQ_CONFIG, TARGET_TOPICS, TOPIC_CATEGORIES, ARTICLE_CONFIG

logger = logging.getLogger(__name__)


def get_groq_client() -> Optional[Groq]:
    """Initialize Groq client."""
    if not GROQ_API_KEY:
        logger.warning("GROQ_API_KEY not set. Classification will be skipped.")
        return None
    return Groq(api_key=GROQ_API_KEY)


def classify_article(client: Groq, article: Dict) -> Dict:
    """
    Classify a single article for relevance to AI/Robotics/Tech Policy.
    Returns the article with added classification data.
    """
    prompt = f"""Analyze this news article and determine its relevance to our target topics.

ARTICLE TITLE: {article['title']}

ARTICLE SUMMARY: {article['summary']}

TARGET TOPICS: AI, Machine Learning, Robotics, Automation, Tech Policy, Regulation

Respond in this exact JSON format:
{{
    "relevant": true/false,
    "relevance_score": 0-100,
    "primary_topic": "AI" or "Robotics" or "Tech Policy" or "Other",
    "keywords": ["keyword1", "keyword2", "keyword3"],
    "reason": "Brief explanation of why this article is or isn't relevant"
}}

Only respond with the JSON, no other text."""

    try:
        response = client.chat.completions.create(
            model=GROQ_CONFIG['model'],
            messages=[
                {"role": "system", "content": "You are a news classifier. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Parse JSON response
        import json
        # Clean up potential markdown formatting
        if result_text.startswith('```'):
            result_text = result_text.split('\n', 1)[1]
            result_text = result_text.rsplit('```', 1)[0]
        
        classification = json.loads(result_text)
        
        # Add classification to article
        article['classification'] = {
            'relevant': classification.get('relevant', False),
            'relevance_score': classification.get('relevance_score', 0),
            'primary_topic': classification.get('primary_topic', 'Other'),
            'keywords': classification.get('keywords', []),
            'reason': classification.get('reason', '')
        }
        
        logger.info(f"Classified: {article['title'][:50]}... -> Score: {article['classification']['relevance_score']}")
        
    except Exception as e:
        logger.error(f"Classification error for {article['title'][:50]}: {e}")
        article['classification'] = {
            'relevant': False,
            'relevance_score': 0,
            'primary_topic': 'Error',
            'keywords': [],
            'reason': str(e)
        }
    
    return article


def classify_articles(articles: List[Dict]) -> List[Dict]:
    """
    Classify all articles and filter to relevant ones.
    """
    client = get_groq_client()
    
    if not client:
        logger.warning("No Groq client. Using keyword-based fallback classification.")
        return keyword_fallback_classify(articles)
    
    classified = []
    for article in articles:
        classified_article = classify_article(client, article)
        classified.append(classified_article)
    
    return classified


def keyword_fallback_classify(articles: List[Dict]) -> List[Dict]:
    """
    Fallback classification using keyword matching (when API not available).
    """
    for article in articles:
        text = f"{article['title']} {article['summary']}".lower()
        
        score = 0
        matched_keywords = []
        primary_topic = "Other"
        
        # Check for topic keywords
        for topic, keywords in TOPIC_CATEGORIES.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    score += 15
                    matched_keywords.append(keyword)
                    if primary_topic == "Other":
                        primary_topic = topic
        
        # Cap score at 100
        score = min(score, 100)
        
        article['classification'] = {
            'relevant': score >= ARTICLE_CONFIG['min_relevance_score'],
            'relevance_score': score,
            'primary_topic': primary_topic,
            'keywords': matched_keywords[:5],
            'reason': 'Keyword-based classification (API not available)'
        }
    
    return articles


def filter_relevant_articles(articles: List[Dict], min_score: int = None) -> List[Dict]:
    """Filter to only relevant articles above minimum score."""
    if min_score is None:
        min_score = ARTICLE_CONFIG['min_relevance_score']
    
    relevant = [
        a for a in articles 
        if a.get('classification', {}).get('relevance_score', 0) >= min_score
    ]
    
    # Sort by relevance score
    relevant.sort(key=lambda x: x['classification']['relevance_score'], reverse=True)
    
    logger.info(f"Filtered to {len(relevant)} relevant articles (score >= {min_score})")
    return relevant


def select_top_articles(articles: List[Dict], count: int = None) -> List[Dict]:
    """Select top N articles for content generation."""
    if count is None:
        count = ARTICLE_CONFIG['articles_per_run']
    
    return articles[:count]


if __name__ == "__main__":
    # Test the classifier
    logging.basicConfig(level=logging.INFO)
    
    # Test with sample article
    test_article = {
        "title": "OpenAI Releases GPT-5 with Revolutionary Reasoning Capabilities",
        "summary": "OpenAI announced the release of GPT-5, featuring advanced reasoning and multi-modal understanding that surpasses previous models.",
        "link": "https://example.com/gpt5",
        "source": "Test"
    }
    
    client = get_groq_client()
    if client:
        result = classify_article(client, test_article)
        print(f"\nClassification Result:")
        print(f"  Relevant: {result['classification']['relevant']}")
        print(f"  Score: {result['classification']['relevance_score']}")
        print(f"  Topic: {result['classification']['primary_topic']}")
        print(f"  Reason: {result['classification']['reason']}")
    else:
        print("No API key set. Test with fallback:")
        result = keyword_fallback_classify([test_article])[0]
        print(f"  Score: {result['classification']['relevance_score']}")
