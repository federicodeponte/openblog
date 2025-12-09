#!/usr/bin/env python3
"""
Apply our regex fixes to existing HTML content to test the results
"""
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pipeline.processors.html_renderer import HTMLRenderer

# Read an existing batch output
html_file = "/Users/federicodeponte/openblog-isaac-security/output/batch-test-001-zero-trust/index.html"

with open(html_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Extract just the article content (between <article> tags)
import re
article_match = re.search(r'<article>(.*?)</article>', content, re.DOTALL)
if article_match:
    article_content = article_match.group(1)
    
    print("🔍 ORIGINAL ARTICLE CONTENT (snippet):")
    print("="*60)
    print(article_content[:1000] + "..." if len(article_content) > 1000 else article_content)
    
    print("\n" + "="*60)
    print("🧹 APPLYING REGEX FIXES...")
    
    # Apply our cleanup method
    cleaned_content = HTMLRenderer._cleanup_content(article_content)
    
    print("\n🎯 CLEANED ARTICLE CONTENT (snippet):")
    print("="*60)
    print(cleaned_content[:1000] + "..." if len(cleaned_content) > 1000 else cleaned_content)
    
    # Save the cleaned version for comparison
    timestamp = "fixed"
    output_file = f"test_cleaned_output_{timestamp}.html"
    
    # Reconstruct the full HTML with cleaned content
    new_html = content.replace(article_content, cleaned_content)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(new_html)
    
    print(f"\n✅ Cleaned version saved to: {output_file}")
    print("🌐 Opening both versions for comparison...")
    
    # Open both files for comparison
    os.system(f"open {html_file}")
    os.system(f"open {output_file}")
else:
    print("❌ Could not find article content in HTML file")