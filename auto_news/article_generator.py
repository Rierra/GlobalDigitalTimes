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
    
    NEW: Focus on SEARCH-INTENT headlines that people would actually Google.
    """
    prompt = f"""Generate 5 headline options that pass this test:
"Would someone type this EXACT phrase into Google?"

ORIGINAL TITLE: {article['title']}
SUMMARY: {article['summary']}
TOPIC: {article.get('classification', {}).get('primary_topic', 'Technology')}

BAD HEADLINES (marketing-speak, no one Googles these):
- "Transforming Transportation: Waymo's Gemini AI Assistant Unveiled"
- "The Future of AI: Revolutionary Breakthroughs Await"
- "Unlock the Power of Machine Learning Today"

GOOD HEADLINES (search-intent, people actually Google these):
- "Waymo robotaxis now use Gemini AI — here's what changed"
- "OpenAI GPT-5 release date and new features explained"
- "Google Gemini vs ChatGPT: which AI is better in 2025"

RULES:
1. Lead with the product/company name (most important keyword first)
2. Use "now", "today", "just", "finally" for breaking news
3. Use conversational phrasing, NOT marketing buzzwords
4. 8-12 words max
5. Include the ACTUAL thing people will search for
6. Avoid: "revolutionary", "game-changing", "unlock", "transform", "power of"

Respond with JSON array:
[
    {{"title": "Your Title Here", "score": 85, "keywords": ["key1", "key2"]}},
    ...
]

Rank by SEARCHABILITY - how likely someone would Google this exact phrase.
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


def generate_image_prompt(client: Groq, article: Dict, title: str, topic: str) -> Dict:
    """
    Generate a Leonardo AI-ready image prompt using Groq.
    Returns: {prompt, filename, alt_text, confidence}
    
    Uses PHOTOREALISTIC style guidelines for natural, believable imagery.
    Falls back to static prompts if confidence is low.
    """
    summary = article.get('summary', title)[:500]
    
    system_prompt = """You are an expert visual director for a tech news publication.
Generate PHOTOREALISTIC image prompts for Leonardo AI.

STRICT RULES:
- 1-2 sentences only
- No neon colors, no abstract circuit brains, no text overlays, no CGI look
- Prioritize realism, natural lighting, real-world materials
- Include human presence only if it naturally fits the story
- Use emotional realism: concern, focus, calm, urgency — never staged smiles
- Specify framing (close-up / medium / wide)
- Mention lighting condition (window light, dusk, overcast, office LED, etc.)
- AVOID buzzwords like "futuristic", "cyberpunk", "AI glow", "holographic"

Human context rules by topic:
- Autonomous vehicles / consumer tech: Yes — user, passenger, worker
- Regulation / corporate lawsuits: Only if it adds meaning
- Infrastructure / cyber incidents: Environment first
- Software releases / backend tools: Device or screen focus, no people

Output JSON only."""

    user_prompt = f"""Generate a Leonardo PHOTOREALISTIC image prompt for this article:

TITLE: {title}
TOPIC: {topic}
SUMMARY: {summary}

Respond with JSON:
{{
    "prompt": "1-2 sentence Leonardo prompt",
    "filename": "lowercase-hyphenated-filename",
    "alt_text": "One sentence alt text with main keyword",
    "confidence": 0.0-1.0 (how confident you are this prompt will produce a good, unique image)
}}

Only respond with JSON."""

    try:
        response = client.chat.completions.create(
            model=GROQ_CONFIG['model'],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        result_text = response.choices[0].message.content.strip()
        
        if result_text.startswith('```'):
            result_text = result_text.split('\n', 1)[1]
            result_text = result_text.rsplit('```', 1)[0]
        
        result = json.loads(result_text)
        
        # Ensure confidence is a float
        result['confidence'] = float(result.get('confidence', 0.5))
        
        # If confidence is high enough, use the generated prompt
        if result['confidence'] >= 0.75:
            logger.info(f"Using Groq-generated image prompt (confidence: {result['confidence']:.2f})")
            result['source'] = 'groq'
            return result
        else:
            logger.info(f"Low confidence ({result['confidence']:.2f}), using fallback prompt")
            return get_fallback_image_prompt(topic, title)
        
    except Exception as e:
        logger.error(f"Image prompt generation error: {e}")
        return get_fallback_image_prompt(topic, title)


def get_fallback_image_prompt(topic: str, title: str) -> Dict:
    """
    Get a static fallback image prompt based on topic category.
    These are pre-designed PHOTOREALISTIC prompts that avoid the "AI brain" look.
    """
    fallback_prompts = {
        "AI": {
            "prompt": "Close-up of a developer's hands typing on a laptop in a quiet co-working space, code editor open on screen, soft window light, shallow depth of field, realistic candid photography — no stylization.",
            "filename": "ai-software-development",
            "alt_text": "Developer working on AI software in modern office"
        },
        "Robotics": {
            "prompt": "Medium shot of a self-driving car paused at a city intersection, dashboard sensors visible, one calm passenger in the back seat, street lamps reflecting on wet asphalt, natural dusk lighting, photorealistic — no neon, no text.",
            "filename": "autonomous-vehicle-city",
            "alt_text": "Self-driving vehicle navigating urban intersection"
        },
        "Tech Policy": {
            "prompt": "Wide shot of a modern corporate headquarters building exterior under overcast skies, employees entering the lobby, natural urban environment, documentary photography style — no dramatic lighting.",
            "filename": "tech-company-headquarters",
            "alt_text": "Technology company headquarters following regulatory announcement"
        },
        "Gaming": {
            "prompt": "Medium shot of a focused gamer with headphones in a dimly lit room, multiple monitors showing gameplay, subtle RGB lighting from peripherals, natural candid moment, realistic photography — no exaggerated effects.",
            "filename": "gaming-setup-player",
            "alt_text": "Gamer playing on high-end gaming setup"
        },
        "Big Tech": {
            "prompt": "Wide shot of a modern glass-facade tech campus building, employees walking on landscaped pathways, overcast sky, clean corporate architecture, documentary style photography — no dramatic effects.",
            "filename": "big-tech-campus",
            "alt_text": "Major technology company headquarters campus"
        },
        "Mobile": {
            "prompt": "Close-up of hands holding a smartphone in a coffee shop, natural daylight from window, screen showing app interface, shallow depth of field with blurred background, authentic lifestyle photography.",
            "filename": "smartphone-user-lifestyle",
            "alt_text": "Person using smartphone application in everyday setting"
        },
        "Cloud": {
            "prompt": "Wide shot of a modern data center interior, rows of servers with subtle blue LED indicators, technician walking between aisles, industrial lighting, documentary style photography — no sci-fi effects.",
            "filename": "data-center-infrastructure",
            "alt_text": "Cloud infrastructure data center facility"
        },
        "Cybersecurity": {
            "prompt": "Medium shot of a security analyst at a workstation with multiple monitors showing dashboards, focused expression, office environment with ambient lighting, realistic workplace photography.",
            "filename": "cybersecurity-analyst",
            "alt_text": "Cybersecurity professional monitoring threat dashboard"
        },
        "Startups": {
            "prompt": "Medium shot of a small team collaborating around a whiteboard in a minimalist office, laptops open, natural daylight, casual startup atmosphere, candid documentary photography — no staged poses.",
            "filename": "startup-team-meeting",
            "alt_text": "Startup team collaborating in modern office"
        },
        "Default": {
            "prompt": "Medium shot of a modern open-plan tech office, employees collaborating at standing desks, large windows with natural light, plants and minimalist decor, authentic workplace photography — no staged poses.",
            "filename": "tech-office-workspace",
            "alt_text": "Modern technology company workspace"
        }
    }
    
    # Get the appropriate fallback or use default
    fallback = fallback_prompts.get(topic, fallback_prompts["Default"])
    
    # Customize filename with title keywords
    slug_title = slugify(title)[:30]
    
    return {
        "prompt": fallback["prompt"],
        "filename": f"{fallback['filename']}-{slug_title}",
        "alt_text": fallback["alt_text"],
        "confidence": 0.6,  # Static prompts get moderate confidence
        "source": "fallback"
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
    
    # Step 5: Generate image prompt (NEW - hybrid Groq + fallback)
    topic = article.get('classification', {}).get('primary_topic', 'Technology')
    image_prompt_data = generate_image_prompt(client, article, selected_title, topic)
    
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
        "word_count": len(content.split()),
        "image_prompt": image_prompt_data  # NEW: Contains prompt, filename, alt_text, confidence, source
    }
    
    logger.info(f"Article generation complete: {metadata['slug']} (image prompt source: {image_prompt_data.get('source', 'unknown')})")
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
