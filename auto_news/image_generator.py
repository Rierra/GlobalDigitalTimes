"""
Auto News Pipeline - Leonardo AI Image Generator
Generates featured images for articles using Leonardo AI.
"""

import logging
import time
import requests
from typing import Dict, Optional
from pathlib import Path

from .config import LEONARDO_API_KEY, LEONARDO_CONFIG, IMAGES_DIR, ASSETS_DIR

logger = logging.getLogger(__name__)

LEONARDO_API_BASE = "https://cloud.leonardo.ai/api/rest/v1"


def get_headers() -> Dict:
    """Get API headers."""
    return {
        "Authorization": f"Bearer {LEONARDO_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }


def generate_image_prompt(article: Dict) -> str:
    """
    Generate a descriptive prompt for the featured image.
    """
    topic = article.get('classification', {}).get('primary_topic', 'Technology')
    title = article.get('title', '')
    
    base_prompts = {
        "AI": "Futuristic artificial intelligence concept, neural networks, digital brain visualization, glowing blue and purple circuits, professional tech blog style",
        "Robotics": "Advanced robotics technology, humanoid robot, mechanical precision, sleek metallic design, futuristic laboratory, professional tech photography",
        "Tech Policy": "Technology and government regulation concept, digital scales of justice, cybersecurity symbols, professional corporate style, blue tones"
    }
    
    base = base_prompts.get(topic, "Modern technology concept, digital innovation, professional tech blog style, blue gradient")
    
    # Add title context
    prompt = f"{base}, representing '{title[:50]}', 16:9 aspect ratio, high quality, photorealistic"
    
    return prompt


def create_generation(prompt: str) -> Optional[str]:
    """
    Start an image generation job on Leonardo AI.
    Returns the generation ID.
    """
    if not LEONARDO_API_KEY:
        logger.warning("LEONARDO_API_KEY not set. Skipping image generation.")
        return None
    
    url = f"{LEONARDO_API_BASE}/generations"
    
    payload = {
        "prompt": prompt,
        "modelId": LEONARDO_CONFIG['model_id'],
        "width": LEONARDO_CONFIG['width'],
        "height": LEONARDO_CONFIG['height'],
        "num_images": LEONARDO_CONFIG['num_images'],
        "promptMagic": True,
        "public": False
    }
    
    try:
        response = requests.post(url, headers=get_headers(), json=payload)
        response.raise_for_status()
        
        data = response.json()
        generation_id = data.get('sdGenerationJob', {}).get('generationId')
        
        logger.info(f"Started image generation: {generation_id}")
        return generation_id
        
    except Exception as e:
        logger.error(f"Error starting image generation: {e}")
        return None


def wait_for_generation(generation_id: str, max_wait: int = 120) -> Optional[str]:
    """
    Wait for generation to complete and return the image URL.
    """
    url = f"{LEONARDO_API_BASE}/generations/{generation_id}"
    
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(url, headers=get_headers())
            response.raise_for_status()
            
            data = response.json()
            generation = data.get('generations_by_pk', {})
            status = generation.get('status')
            
            if status == 'COMPLETE':
                images = generation.get('generated_images', [])
                if images:
                    image_url = images[0].get('url')
                    logger.info(f"Image generation complete: {image_url[:50]}...")
                    return image_url
                return None
            
            elif status == 'FAILED':
                logger.error("Image generation failed")
                return None
            
            # Still processing, wait and retry
            time.sleep(5)
            
        except Exception as e:
            logger.error(f"Error checking generation status: {e}")
            time.sleep(5)
    
    logger.error("Image generation timed out")
    return None


def download_image(url: str, filename: str) -> Optional[Path]:
    """
    Download image from URL and save to disk.
    """
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Save to generated images directory
        filepath = IMAGES_DIR / filename
        filepath.write_bytes(response.content)
        
        # Also copy to assets directory for the site
        assets_path = ASSETS_DIR / filename
        assets_path.write_bytes(response.content)
        
        logger.info(f"Image saved: {filepath}")
        return filepath
        
    except Exception as e:
        logger.error(f"Error downloading image: {e}")
        return None


def generate_featured_image(article: Dict) -> Optional[Dict]:
    """
    Main function: Generate and download a featured image for an article.
    """
    if not LEONARDO_API_KEY:
        logger.warning("Leonardo API key not set. Using placeholder.")
        return create_placeholder_result(article)
    
    logger.info(f"Generating image for: {article.get('title', '')[:50]}...")
    
    # Generate prompt
    prompt = generate_image_prompt(article)
    logger.info(f"Image prompt: {prompt[:100]}...")
    
    # Start generation
    generation_id = create_generation(prompt)
    if not generation_id:
        return create_placeholder_result(article)
    
    # Wait for completion
    image_url = wait_for_generation(generation_id)
    if not image_url:
        return create_placeholder_result(article)
    
    # Download image
    slug = article.get('metadata', {}).get('slug', article.get('id', 'article'))
    filename = f"{slug}.png"
    
    filepath = download_image(image_url, filename)
    if not filepath:
        return create_placeholder_result(article)
    
    return {
        "generated": True,
        "prompt": prompt,
        "url": image_url,
        "local_path": str(filepath),
        "filename": filename,
        "assets_path": f"assets/{filename}"
    }


def create_placeholder_result(article: Dict) -> Dict:
    """
    Create a placeholder result when image generation is skipped.
    """
    # Use a default placeholder image
    return {
        "generated": False,
        "prompt": "",
        "url": "",
        "local_path": "",
        "filename": "default-tech.png",
        "assets_path": "assets/GD.PNG"  # Use existing site asset
    }


def generate_image_for_article(article: Dict) -> Dict:
    """
    Wrapper that adds image data to the article dict.
    """
    image_result = generate_featured_image(article)
    article['featured_image'] = image_result
    return article


if __name__ == "__main__":
    # Test the image generator
    logging.basicConfig(level=logging.INFO)
    
    test_article = {
        "id": "test123",
        "title": "OpenAI Releases GPT-5 with Revolutionary Features",
        "metadata": {"slug": "gpt5-features-2024"},
        "classification": {"primary_topic": "AI"}
    }
    
    if LEONARDO_API_KEY:
        result = generate_featured_image(test_article)
        print(f"\nImage Result:")
        print(f"  Generated: {result['generated']}")
        print(f"  Filename: {result['filename']}")
        print(f"  Path: {result['assets_path']}")
    else:
        print("Leonardo API key not set. Skipping test.")
        result = create_placeholder_result(test_article)
        print(f"Placeholder: {result['assets_path']}")
