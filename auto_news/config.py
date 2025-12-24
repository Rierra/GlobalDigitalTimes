"""
Auto News Pipeline - Configuration
Central configuration for RSS feeds, API settings, and site config.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# =============================================================================
# PATHS
# =============================================================================
BASE_DIR = Path(__file__).parent.parent
SITE_DIR = BASE_DIR / "revived_site"
ARTICLES_DIR = SITE_DIR / "articles"
ASSETS_DIR = SITE_DIR / "assets"
DATA_DIR = BASE_DIR / "data"
IMAGES_DIR = DATA_DIR / "generated_images"

# Create directories if they don't exist
ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# =============================================================================
# API KEYS
# =============================================================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
LEONARDO_API_KEY = os.getenv("LEONARDO_API_KEY", "")

# =============================================================================
# SITE CONFIGURATION
# =============================================================================
SITE_NAME = os.getenv("SITE_NAME", "Global Digital Times")
SITE_URL = os.getenv("SITE_URL", "https://globaldigitaltimes.onrender.com")
AUTHOR_NAME = "Global Digital Times"

# =============================================================================
# RSS FEED SOURCES
# =============================================================================
RSS_FEEDS = [
    {
        "name": "BBC Technology",
        "url": "http://feeds.bbci.co.uk/news/technology/rss.xml",
        "category": "tech"
    },
    {
        "name": "TechCrunch",
        "url": "https://techcrunch.com/feed/",
        "category": "tech"
    },
    {
        "name": "Wired",
        "url": "https://www.wired.com/feed/rss",
        "category": "tech"
    },
    {
        "name": "MIT Technology Review",
        "url": "https://www.technologyreview.com/feed/",
        "category": "ai"
    },
    {
        "name": "The Verge",
        "url": "https://www.theverge.com/rss/index.xml",
        "category": "tech"
    },
    {
        "name": "Ars Technica",
        "url": "https://feeds.arstechnica.com/arstechnica/index",
        "category": "tech"
    }
]

# =============================================================================
# TOPIC CONFIGURATION
# =============================================================================
TARGET_TOPICS = [
    "artificial intelligence",
    "AI",
    "machine learning",
    "robotics",
    "automation",
    "tech policy",
    "regulation",
    "OpenAI",
    "Google AI",
    "ChatGPT",
    "GPT",
    "neural network",
    "deep learning",
    "LLM",
    "large language model"
]

TOPIC_CATEGORIES = {
    "AI": ["artificial intelligence", "AI", "machine learning", "deep learning", 
           "neural network", "OpenAI", "ChatGPT", "GPT", "LLM", "large language model"],
    "Robotics": ["robotics", "automation", "robot", "autonomous"],
    "Tech Policy": ["policy", "regulation", "law", "government", "privacy", "antitrust"]
}

# =============================================================================
# ARTICLE GENERATION SETTINGS
# =============================================================================
ARTICLE_CONFIG = {
    "min_words": 1000,
    "max_words": 1500,
    "min_relevance_score": 70,  # 0-100 scale
    "articles_per_run": 2,
    "hours_lookback": 24
}

# =============================================================================
# GROQ SETTINGS
# =============================================================================
GROQ_CONFIG = {
    "model": "llama-3.3-70b-versatile",
    "temperature": 0.7,
    "max_tokens": 4096
}

# =============================================================================
# LEONARDO AI SETTINGS
# =============================================================================
LEONARDO_CONFIG = {
    "model_id": "de7d3faf-762f-48e0-b3b7-9d0ac3a3fcf3",  # Leonardo Phoenix 1.0
    "width": 1472,   # Must be multiple of 8, close to 16:9 for OG images
    "height": 832,   # Must be multiple of 8
    "num_images": 1
}

# =============================================================================
# LOGGING
# =============================================================================
LOG_FILE = BASE_DIR / "auto_news.log"
LOG_LEVEL = "INFO"
