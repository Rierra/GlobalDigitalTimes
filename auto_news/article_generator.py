"""
Auto News Pipeline - Article Generator
Uses Groq to generate SEO-optimized articles from news sources.
"""

import logging
import json
from typing import Dict, List, Optional
from datetime import datetime, timezone
from slugify import slugify
from groq import Groq

from .config import GROQ_API_KEY, GROQ_CONFIG, SITE_NAME, ARTICLE_CONFIG

logger = logging.getLogger(__name__)


def get_groq_client() -> Optional[Groq]:
    """Initialize Groq client."""
    if not GROQ_API_KEY:
        logger.warning("GROQ_API_KEY not set.")
        return None
    return Groq(api_key=GROQ_API_KEY)


def generate_seo_titles(client: Groq, article: Dict) -> List[Dict]:
    """
    Generate 5 SEO-optimized title options for the article.
    Returns list of titles with scores.
    """
    prompt = f"""Based on this news article, generate 5 SEO-optimized blog title ideas.

ORIGINAL TITLE: {article['title']}
SUMMARY: {article['summary']}
TOPIC: {article.get('classification', {}).get('primary_topic', 'Technology')}

Requirements:
- Long-tail SEO friendly (8-12 words)
- Include power words that drive clicks
- Include numbers when appropriate
- Target search intent
- Make it compelling and unique

Respond with JSON array:
[
    {{"title": "Your Title Here", "score": 85, "keywords": ["key1", "key2"]}},
    ...
]

Rank by uniqueness and expected performance (score 0-100).
Only respond with the JSON array, no other text."""

    try:
        response = client.chat.completions.create(
            model=GROQ_CONFIG['model'],
            messages=[
                {"role": "system", "content": "You are an SEO expert and headline writer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=1000
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Clean markdown formatting
        if result_text.startswith('```'):
            result_text = result_text.split('\n', 1)[1]
            result_text = result_text.rsplit('```', 1)[0]
        
        titles = json.loads(result_text)
        
        # Sort by score
        titles.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        logger.info(f"Generated {len(titles)} title options")
        return titles
        
    except Exception as e:
        logger.error(f"Title generation error: {e}")
        # Fallback to original title
        return [{"title": article['title'], "score": 50, "keywords": []}]


def generate_outline(client: Groq, article: Dict, selected_title: str) -> Dict:
    """
    Generate a structured blog outline with H1, H2 headers.
    """
    prompt = f"""Create a detailed blog outline for this article.

TITLE: {selected_title}
TOPIC: {article.get('classification', {}).get('primary_topic', 'Technology')}
SOURCE SUMMARY: {article['summary']}

Create an outline with:
- H1 (main title)
- 4-6 H2 sections
- Key points for each section
- FAQ section (3 questions)
- Optimized for featured snippets

Respond with JSON:
{{
    "h1": "Main Title",
    "intro_hook": "Opening sentence to grab attention",
    "sections": [
        {{"h2": "Section Title", "key_points": ["point1", "point2", "point3"]}},
        ...
    ],
    "faq": [
        {{"question": "Q1?", "answer_preview": "Brief answer"}},
        ...
    ],
    "target_keywords": ["keyword1", "keyword2", "keyword3"],
    "meta_description_hint": "Key message for meta description"
}}

Only respond with JSON."""

    try:
        response = client.chat.completions.create(
            model=GROQ_CONFIG['model'],
            messages=[
                {"role": "system", "content": "You are a content strategist and SEO expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        
        result_text = response.choices[0].message.content.strip()
        
        if result_text.startswith('```'):
            result_text = result_text.split('\n', 1)[1]
            result_text = result_text.rsplit('```', 1)[0]
        
        outline = json.loads(result_text)
        logger.info(f"Generated outline with {len(outline.get('sections', []))} sections")
        return outline
        
    except Exception as e:
        logger.error(f"Outline generation error: {e}")
        return {
            "h1": selected_title,
            "intro_hook": article['summary'][:100],
            "sections": [],
            "faq": [],
            "target_keywords": [],
            "meta_description_hint": article['summary'][:150]
        }


def generate_article_content(client: Groq, article: Dict, outline: Dict) -> str:
    """
    Generate the full article content (1000-1500 words).
    """
    sections_text = "\n".join([
        f"- {s['h2']}: {', '.join(s.get('key_points', []))}" 
        for s in outline.get('sections', [])
    ])
    
    faq_text = "\n".join([
        f"- {f['question']}" 
        for f in outline.get('faq', [])
    ])
    
    prompt = f"""Write a complete, engaging blog article based on this outline.

TITLE: {outline['h1']}
INTRO HOOK: {outline.get('intro_hook', '')}

SECTIONS TO COVER:
{sections_text}

FAQ TO INCLUDE:
{faq_text}

SOURCE INFORMATION:
{article['summary']}
Source: {article['source']}

REQUIREMENTS:
1. Write 1000-1500 words
2. Use conversational but professional tone
3. Include the H1 title at the start
4. Use H2 headers for each section
5. Include relevant examples and analogies
6. Add a compelling introduction
7. End with a strong conclusion
8. Include the FAQ section with full answers
9. Cite the source appropriately
10. Use markdown formatting

Write the complete article now:"""

    try:
        response = client.chat.completions.create(
            model=GROQ_CONFIG['model'],
            messages=[
                {"role": "system", "content": f"You are a senior tech journalist writing for {SITE_NAME}. Write engaging, informative content with proper structure."},
                {"role": "user", "content": prompt}
            ],
            temperature=GROQ_CONFIG['temperature'],
            max_tokens=GROQ_CONFIG['max_tokens']
        )
        
        content = response.choices[0].message.content.strip()
        
        # Add source citation if not present
        if article['source'] not in content:
            content += f"\n\n---\n*Source: [{article['source']}]({article['link']})*"
        
        word_count = len(content.split())
        logger.info(f"Generated article: {word_count} words")
        
        return content
        
    except Exception as e:
        logger.error(f"Article generation error: {e}")
        return f"# {outline['h1']}\n\n{article['summary']}\n\n*Source: {article['source']}*"


def generate_seo_metadata(client: Groq, article: Dict, title: str, content: str) -> Dict:
    """
    Generate SEO metadata for the article.
    """
    prompt = f"""Generate SEO metadata for this blog article.

TITLE: {title}
CONTENT PREVIEW: {content[:500]}...

Generate:
{{
    "meta_title": "SEO title (50-60 chars)",
    "meta_description": "Compelling description (150-160 chars)",
    "slug": "url-friendly-slug",
    "image_alt": "Descriptive alt text for featured image",
    "og_title": "Open Graph title",
    "og_description": "Open Graph description",
    "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
    "reading_time_minutes": 5
}}

Only respond with JSON."""

    try:
        response = client.chat.completions.create(
            model=GROQ_CONFIG['model'],
            messages=[
                {"role": "system", "content": "You are an SEO specialist."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=500
        )
        
        result_text = response.choices[0].message.content.strip()
        
        if result_text.startswith('```'):
            result_text = result_text.split('\n', 1)[1]
            result_text = result_text.rsplit('```', 1)[0]
        
        metadata = json.loads(result_text)
        
        # Ensure slug is properly formatted
        if 'slug' in metadata:
            metadata['slug'] = slugify(metadata['slug'])
        else:
            metadata['slug'] = slugify(title)
        
        logger.info(f"Generated SEO metadata: {metadata['slug']}")
        return metadata
        
    except Exception as e:
        logger.error(f"Metadata generation error: {e}")
        return {
            "meta_title": title[:60],
            "meta_description": content[:160],
            "slug": slugify(title),
            "image_alt": f"Featured image for {title}",
            "og_title": title,
            "og_description": content[:200],
            "keywords": [],
            "reading_time_minutes": 5
        }


def generate_full_article(article: Dict) -> Optional[Dict]:
    """
    Main function: Generate a complete article with all components.
    """
    client = get_groq_client()
    
    if not client:
        logger.error("Cannot generate article without Groq API key")
        return None
    
    logger.info(f"Generating article for: {article['title'][:50]}...")
    
    # Step 1: Generate SEO titles
    titles = generate_seo_titles(client, article)
    selected_title = titles[0]['title'] if titles else article['title']
    
    # Step 2: Generate outline
    outline = generate_outline(client, article, selected_title)
    
    # Step 3: Generate content
    content = generate_article_content(client, article, outline)
    
    # Step 4: Generate SEO metadata
    metadata = generate_seo_metadata(client, article, selected_title, content)
    
    # Compile final article
    generated_article = {
        "id": article['id'],
        "original_title": article['title'],
        "original_link": article['link'],
        "original_source": article['source'],
        "title": selected_title,
        "title_options": titles,
        "outline": outline,
        "content": content,
        "metadata": metadata,
        "classification": article.get('classification', {}),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "word_count": len(content.split())
    }
    
    logger.info(f"Article generation complete: {metadata['slug']}")
    return generated_article


if __name__ == "__main__":
    # Test the generator
    logging.basicConfig(level=logging.INFO)
    
    test_article = {
        "id": "test123",
        "title": "OpenAI Releases GPT-5 with Revolutionary Features",
        "summary": "OpenAI announced GPT-5 today, featuring advanced reasoning capabilities and multi-modal understanding that significantly surpasses GPT-4.",
        "link": "https://example.com/gpt5",
        "source": "TechCrunch",
        "classification": {
            "primary_topic": "AI",
            "relevance_score": 95
        }
    }
    
    result = generate_full_article(test_article)
    
    if result:
        print(f"\n{'='*60}")
        print(f"Generated Article: {result['title']}")
        print(f"Slug: {result['metadata']['slug']}")
        print(f"Word Count: {result['word_count']}")
        print(f"{'='*60}")
        print(f"\n{result['content'][:500]}...")
