"""
Script to regenerate images for existing articles using Leonardo AI.
"""
import time
import sys
sys.path.insert(0, '.')

from auto_news.image_generator import generate_featured_image

articles = [
    {
        'id': '1', 
        'title': '2025: The Year AI Revolutionized Gaming Forever with 90% Adoption', 
        'metadata': {'slug': 'ai-revolutionizes-gaming-2025'}, 
        'classification': {'primary_topic': 'AI'}
    },
    {
        'id': '2', 
        'title': 'Unlock 10 AI Coding Secrets: Boosting Productivity with Agents', 
        'metadata': {'slug': 'unlock-ai-coding-secrets'}, 
        'classification': {'primary_topic': 'AI'}
    },
    {
        'id': '3', 
        'title': 'Breaking: Italy Tells Meta to Halt WhatsApp AI Chatbot Restrictions Within 10 Days', 
        'metadata': {'slug': 'italy-orders-meta-to-halt-whatsapp-ai-chatbot-restrictions'}, 
        'classification': {'primary_topic': 'Tech Policy'}
    },
    {
        'id': '4', 
        'title': 'Transforming Transportation: Waymo Gemini AI Assistant Unveiled with 1200+ Capabilities', 
        'metadata': {'slug': 'waymo-gemini-ai-transforming-transportation'}, 
        'classification': {'primary_topic': 'AI'}
    },
    {
        'id': '5', 
        'title': '7,000 Dark Stoplights No Match for Waymo Robotaxis Technology', 
        'metadata': {'slug': 'waymo-robotaxis-dark-stoplights'}, 
        'classification': {'primary_topic': 'Robotics'}
    }
]

if __name__ == "__main__":
    for i, article in enumerate(articles, 1):
        print(f"\n[{i}/5] Generating image for: {article['metadata']['slug']}")
        result = generate_featured_image(article)
        print(f"  Generated: {result['generated']}")
        print(f"  Path: {result.get('assets_path', 'N/A')}")
        if i < 5:
            print("  Waiting 10 seconds...")
            time.sleep(10)  # Rate limit courtesy

    print("\n✅ Done generating all images!")
