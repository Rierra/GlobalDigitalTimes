"""
Script to update existing articles with new Leonardo AI images.
"""
import os
import re

articles_dir = "revived_site/articles"

# Mapping of slugs to their new image filenames
image_mapping = {
    "ai-revolutionizes-gaming-2025": "ai-revolutionizes-gaming-2025.png",
    "unlock-ai-coding-secrets": "unlock-ai-coding-secrets.png", 
    "italy-orders-meta-to-halt-whatsapp-ai-chatbot-restrictions": "italy-orders-meta-to-halt-whatsapp-ai-chatbot-restrictions.png",
    "waymo-gemini-ai-transforming-transportation": "waymo-gemini-ai-transforming-transportation.png",
    "waymo-robotaxis-dark-stoplights": "waymo-robotaxis-dark-stoplights.png"
}

for slug, image_filename in image_mapping.items():
    html_file = os.path.join(articles_dir, f"{slug}.html")
    
    if os.path.exists(html_file):
        print(f"Updating: {slug}.html")
        
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace old placeholder with new image - handle different contexts
        # 1. OG and Twitter image meta tags (absolute URL)
        content = re.sub(
            r'(content="https://globaldigitaltimes\.onrender\.com/)assets/GD\.PNG"',
            rf'\1assets/{image_filename}"',
            content
        )
        
        # 2. Schema.org image (absolute URL)
        content = re.sub(
            r'("image": "https://globaldigitaltimes\.onrender\.com/)assets/GD\.PNG"',
            rf'\1assets/{image_filename}"',
            content
        )
        
        # 3. Article image in body (relative path)
        content = re.sub(
            r'src="\.\./assets/GD\.PNG"',
            rf'src="../assets/{image_filename}"',
            content
        )
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"  ✓ Updated with {image_filename}")
    else:
        print(f"  ✗ File not found: {html_file}")

print("\n✅ Done updating all article HTML files!")
