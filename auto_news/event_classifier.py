"""
Auto News Pipeline - Event Classifier
Classifies news articles by event type to prioritize breaking news over routine updates.
Uses Groq for fast, intelligent classification.
"""

import logging
from typing import Dict, Optional, List
from groq import Groq

from .config import GROQ_API_KEY, GROQ_CONFIG

logger = logging.getLogger(__name__)

# Event types and their publishing priority
# Priority 1 = Publish immediately (clear the queue)
# Priority 2 = Publish within 1 hour (high priority)
# Priority 3 = Batch publish (routine)
EVENT_PRIORITY = {
    "BREAKING": 1,      # Launches, model releases, new products
    "ACQUISITION": 1,   # Major M&A news
    "LAYOFFS": 1,       # Workforce changes
    "LAWSUIT": 1,       # Legal action, bans, investigations
    "FUNDING": 2,       # >$50M or known brand
    "VIRAL": 2,         # Reddit/GitHub/HN trending
    "ROUTINE": 3        # Weekly updates, minor features, opinion pieces
}

# Keywords that strongly indicate event type (used as hints for Groq)
EVENT_SIGNALS = {
    "BREAKING": [
        "launches", "released", "announces", "unveils", "introduces", "debuts",
        "now available", "ships", "rolls out", "goes live", "officially"
    ],
    "ACQUISITION": [
        "acquires", "acquisition", "buys", "bought", "merger", "deal", 
        "takes over", "purchase"
    ],
    "LAYOFFS": [
        "layoffs", "lays off", "cuts", "job cuts", "eliminates", "reduces workforce",
        "restructure", "downsizing", "firing"
    ],
    "LAWSUIT": [
        "sues", "lawsuit", "sued", "court", "legal", "antitrust", "investigation",
        "ban", "blocks", "halts", "orders", "ruling"
    ],
    "FUNDING": [
        "raises", "funding", "valuation", "series a", "series b", "series c",
        "investment", "backed", "secures"
    ],
    "VIRAL": [
        "trending", "viral", "explodes", "blows up", "everyone is talking"
    ]
}

# High-profile companies that make news more breaking
HIGH_PROFILE_ENTITIES = [
    "openai", "google", "apple", "microsoft", "meta", "amazon", "nvidia", 
    "tesla", "anthropic", "mistral", "chatgpt", "gpt-5", "gpt-4", "gemini",
    "claude", "waymo", "x.ai", "deepmind", "stability ai", "midjourney"
]


def get_groq_client() -> Optional[Groq]:
    """Initialize Groq client."""
    if not GROQ_API_KEY:
        logger.warning("GROQ_API_KEY not set.")
        return None
    return Groq(api_key=GROQ_API_KEY)


def classify_event_fast(title: str, summary: str = "") -> Dict:
    """
    Fast keyword-based pre-classification.
    Returns a hint for Groq or can be used standalone for speed.
    """
    text = f"{title} {summary}".lower()
    
    # Check for high-profile entities first
    has_high_profile = any(entity in text for entity in HIGH_PROFILE_ENTITIES)
    
    # Check for event signals
    for event_type, keywords in EVENT_SIGNALS.items():
        if any(keyword in text for keyword in keywords):
            return {
                "event_type": event_type,
                "priority": EVENT_PRIORITY[event_type],
                "confidence": "keyword_match",
                "high_profile": has_high_profile
            }
    
    # Default to routine
    return {
        "event_type": "ROUTINE",
        "priority": EVENT_PRIORITY["ROUTINE"],
        "confidence": "default",
        "high_profile": has_high_profile
    }


def classify_event_groq(client: Groq, title: str, summary: str = "") -> Dict:
    """
    Use Groq for intelligent event classification.
    More accurate but slightly slower than keyword matching.
    """
    # First do fast classification for hint
    fast_result = classify_event_fast(title, summary)
    
    prompt = f"""Classify this news article into exactly ONE category.

Categories:
- BREAKING: New product launches, model releases, feature announcements, things people will Google TODAY
- ACQUISITION: Company buys/acquires another company
- LAYOFFS: Job cuts, workforce reductions, restructuring
- LAWSUIT: Legal action, bans, investigations, court rulings
- FUNDING: Investment rounds, valuations (only if >$50M or well-known company)
- VIRAL: Trending on social media, generating buzz
- ROUTINE: Regular updates, opinion pieces, minor features, not time-sensitive

TITLE: {title}
SUMMARY: {summary[:300] if summary else 'N/A'}

Think: "Will people start Googling this within the next few hours?"
If yes → BREAKING, ACQUISITION, LAYOFFS, LAWSUIT, or FUNDING
If no → ROUTINE

Reply with ONLY the category name (one word)."""

    try:
        response = client.chat.completions.create(
            model=GROQ_CONFIG['model'],
            messages=[
                {"role": "system", "content": "You are a news editor who identifies breaking news that will drive search traffic."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Low temperature for consistent classification
            max_tokens=20
        )
        
        result = response.choices[0].message.content.strip().upper()
        
        # Validate result
        if result in EVENT_PRIORITY:
            event_type = result
        else:
            # Try to extract valid event type from response
            for et in EVENT_PRIORITY.keys():
                if et in result:
                    event_type = et
                    break
            else:
                event_type = fast_result["event_type"]  # Fall back to keyword match
        
        return {
            "event_type": event_type,
            "priority": EVENT_PRIORITY[event_type],
            "confidence": "groq",
            "high_profile": fast_result["high_profile"]
        }
        
    except Exception as e:
        logger.error(f"Groq classification error: {e}")
        return fast_result  # Fall back to keyword-based classification


def classify_article(article: Dict, use_groq: bool = True) -> Dict:
    """
    Main classification function. Adds event classification to article dict.
    
    Args:
        article: Article dict with 'title' and 'summary'
        use_groq: Whether to use Groq (more accurate) or just keywords (faster)
    
    Returns:
        Article dict with 'event_classification' added
    """
    title = article.get('title', '')
    summary = article.get('summary', '')
    
    if use_groq:
        client = get_groq_client()
        if client:
            classification = classify_event_groq(client, title, summary)
        else:
            classification = classify_event_fast(title, summary)
    else:
        classification = classify_event_fast(title, summary)
    
    # Boost priority for high-profile entities with breaking keywords
    if classification["high_profile"] and classification["event_type"] in ["BREAKING", "ACQUISITION", "LAYOFFS"]:
        classification["boost"] = True
        logger.info(f"BOOSTED: {title[:50]}... → {classification['event_type']}")
    
    article['event_classification'] = classification
    
    logger.info(f"Classified: {title[:40]}... → {classification['event_type']} (P{classification['priority']})")
    
    return article


def sort_by_priority(articles: List[Dict]) -> List[Dict]:
    """
    Sort articles by event priority (1 = highest = publish first).
    Within same priority, high-profile entities come first.
    """
    def sort_key(article: Dict):
        ec = article.get('event_classification', {})
        priority = ec.get('priority', 3)
        # High-profile gets slight boost (lower = first)
        high_profile_boost = 0 if ec.get('high_profile') else 0.5
        return priority + high_profile_boost
    
    return sorted(articles, key=sort_key)


def get_publishing_queues(articles: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Organize articles into publishing queues by priority.
    
    Returns:
        {
            "breaking": [...],   # Priority 1 - publish ALL immediately
            "high": [...],       # Priority 2 - publish up to 3
            "routine": [...]     # Priority 3 - publish if no urgent news
        }
    """
    queues = {
        "breaking": [],
        "high": [],
        "routine": []
    }
    
    for article in articles:
        ec = article.get('event_classification', {})
        priority = ec.get('priority', 3)
        
        if priority == 1:
            queues["breaking"].append(article)
        elif priority == 2:
            queues["high"].append(article)
        else:
            queues["routine"].append(article)
    
    # Sort each queue (high-profile first within priority)
    for queue_name in queues:
        queues[queue_name] = sort_by_priority(queues[queue_name])
    
    return queues


if __name__ == "__main__":
    # Test the classifier
    logging.basicConfig(level=logging.INFO)
    
    test_articles = [
        {"title": "OpenAI launches GPT-5 with revolutionary reasoning capabilities", "summary": "New model available today"},
        {"title": "Google acquires AI startup for $2 billion", "summary": "Acquisition announced"},
        {"title": "Meta lays off 10,000 employees in restructuring", "summary": "Workforce reduction"},
        {"title": "Italy tells Meta to halt WhatsApp AI restrictions", "summary": "Legal order issued"},
        {"title": "Anthropic raises $2B at $60B valuation", "summary": "Funding round"},
        {"title": "Weekly AI newsletter: Updates from the ecosystem", "summary": "Regular roundup"},
    ]
    
    print("Testing Event Classifier\n" + "="*50)
    
    for article in test_articles:
        result = classify_article(article, use_groq=True)
        ec = result['event_classification']
        print(f"\n{article['title'][:50]}...")
        print(f"  → {ec['event_type']} (Priority {ec['priority']}, {ec['confidence']})")
    
    print("\n" + "="*50)
    print("\nSorted by priority:")
    sorted_articles = sort_by_priority(test_articles)
    for i, article in enumerate(sorted_articles, 1):
        ec = article['event_classification']
        print(f"{i}. [{ec['event_type']}] {article['title'][:50]}...")
