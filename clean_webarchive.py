#!/usr/bin/env python3
"""
Script to clean Web Archive/Wayback Machine elements from a saved HTML file.
Removes all archive.org scripts, styles, and converts archived URLs to original URLs.
"""

import re

def clean_webarchive_html(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        html = f.read()
    
    original_length = len(html)
    
    # 1. Remove the Wayback Machine toolbar/banner - this is usually in a comment or specific div
    # Remove the entire <!-- BEGIN WAYBACK TOOLBAR INSERT --> ... <!-- END WAYBACK TOOLBAR INSERT --> block
    html = re.sub(r'<!-- BEGIN WAYBACK TOOLBAR INSERT -->.*?<!-- END WAYBACK TOOLBAR INSERT -->', '', html, flags=re.DOTALL)
    
    # 2. Remove script tags that reference archive.org
    patterns_to_remove = [
        r'<script[^>]*src="[^"]*archive\.org[^"]*"[^>]*>.*?</script>',
        r'<script[^>]*src="[^"]*web-static\.archive\.org[^"]*"[^>]*>.*?</script>',
        r'<script[^>]*>.*?__wm\.init.*?</script>',
        r'<script[^>]*>.*?__wm\.wombat.*?</script>',
        r'<script[^>]*>.*?archive_analytics.*?</script>',
        r'<script[^>]*>.*?window\.RufflePlayer.*?</script>',
    ]
    
    for pattern in patterns_to_remove:
        html = re.sub(pattern, '', html, flags=re.DOTALL | re.IGNORECASE)
    
    # 3. Remove link tags that reference archive.org stylesheets
    html = re.sub(r'<link[^>]*href="[^"]*web-static\.archive\.org[^"]*"[^>]*/?>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<link[^>]*href="[^"]*archive\.org[^"]*"[^>]*/?>', '', html, flags=re.IGNORECASE)
    
    # 4. Remove Wayback Machine comments
    html = re.sub(r'<!-- End Wayback Rewrite JS Include -->', '', html)
    html = re.sub(r'<!-- Wayback Rewrite JS Include -->', '', html)
    
    # 5. Remove the wombat.js related script blocks
    html = re.sub(r'<script[^>]*>\s*//archive\.org.*?</script>', '', html, flags=re.DOTALL)
    
    # 6. Clean URLs - remove web.archive.org prefix from URLs
    # Pattern: https://web.archive.org/web/TIMESTAMP/ORIGINAL_URL or https://web.archive.org/web/TIMESTAMPim_/ORIGINAL_URL
    url_patterns = [
        (r'https://web\.archive\.org/web/\d+im_/(https?://)', r'\1'),  # for images
        (r'https://web\.archive\.org/web/\d+js_/(https?://)', r'\1'),  # for javascript
        (r'https://web\.archive\.org/web/\d+cs_/(https?://)', r'\1'),  # for css
        (r'https://web\.archive\.org/web/\d+/(https?://)', r'\1'),     # general URLs
        (r'//web\.archive\.org/web/\d+im_/(https?://)', r'\1'),
        (r'//web\.archive\.org/web/\d+/(https?://)', r'\1'),
    ]
    
    for pattern, replacement in url_patterns:
        html = re.sub(pattern, replacement, html)
    
    # 7. Remove the archive.org div containers (Wayback toolbar)
    html = re.sub(r'<div[^>]*id="wm-ipp[^"]*"[^>]*>.*?</div>\s*</div>\s*</div>', '', html, flags=re.DOTALL)
    
    # 8. Remove any remaining archive.org script references
    html = re.sub(r'<script[^>]*>//archive\.org[^<]*</script>', '', html, flags=re.DOTALL)
    
    # 9. Remove inline scripts that contain archive.org references
    html = re.sub(r"<script[^>]*>\s*window\.addEventListener\('DOMContentLoaded'.*?archive_analytics.*?</script>", '', html, flags=re.DOTALL)
    
    # 10. Fix the title - remove archive.org URL from title
    html = re.sub(r'<title>https://web\.archive\.org/[^<]*</title>', '<title>Global Digital Times</title>', html)
    
    # 11. Remove playback bundle script
    html = re.sub(r'<script[^>]*bundle-playback[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    
    # 12. Remove wombat.js script  
    html = re.sub(r'<script[^>]*wombat\.js[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    
    # 13. Remove ruffle.js script (Flash player replacement)
    html = re.sub(r'<script[^>]*ruffle\.js[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    
    # 14. Remove any athena.js (archive.org analytics)
    html = re.sub(r'<script[^>]*athena\.js[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    
    # 15. Clean up extra whitespace/newlines
    html = re.sub(r'\n\s*\n\s*\n', '\n\n', html)
    
    # 16. Fix canonical URL
    html = re.sub(
        r'<link[^>]*rel="canonical"[^>]*href="https://web\.archive\.org/[^"]*"[^>]*>',
        '<link rel="canonical" href="https://www.globaldigitaltimes.com/">',
        html
    )
    
    # 17. Fix og:url
    html = re.sub(
        r'<meta[^>]*property="og:url"[^>]*content="https://web\.archive\.org/[^"]*"[^>]*>',
        '<meta property="og:url" content="https://www.globaldigitaltimes.com/">',
        html
    )
    
    # Write cleaned HTML
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"Original size: {original_length:,} bytes")
    print(f"Cleaned size: {len(html):,} bytes")
    print(f"Removed: {original_length - len(html):,} bytes")
    print(f"Saved to: {output_file}")

if __name__ == '__main__':
    clean_webarchive_html('original_from_archive.html', 'globaldigitaltimes_clean.html')
