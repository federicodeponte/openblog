#!/usr/bin/env python3
"""
Investigation script to compare raw Gemini output with final HTML.

This script helps identify where errors are introduced in the pipeline.
"""

import json
import re
from pathlib import Path

def analyze_article_errors(html_file: str):
    """Analyze errors in the final HTML output."""
    
    html_path = Path(html_file)
    if not html_path.exists():
        print(f"❌ HTML file not found: {html_file}")
        return
    
    print("=" * 80)
    print("ARTICLE ERROR ANALYSIS")
    print("=" * 80)
    print()
    
    # Read HTML
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Extract headline
    headline_match = re.search(r'<h1>(.*?)</h1>', html_content)
    headline = headline_match.group(1) if headline_match else "Not found"
    
    print("🔍 CRITICAL ISSUES FOUND:")
    print()
    
    # Issue 1: Double-encoded ampersand
    if '&amp;amp;' in headline:
        print("1. ❌ DOUBLE ENCODING ERROR (Line 303)")
        print(f"   Found: {headline}")
        print(f"   Issue: &amp;amp; should be &amp; or &")
        print(f"   Source: Likely Gemini output '&amp;' which was then escaped again")
        print()
    
    # Issue 2: Grammatical errors in intro
    intro_match = re.search(r'<div class="intro">(.*?)</div>', html_content, re.DOTALL)
    if intro_match:
        intro = intro_match.group(1)
        
        # Check for "Here's that's not"
        if "Here's that's not" in intro:
            print("2. ❌ GRAMMATICAL ERROR (Line 316)")
            print("   Found: 'Here's that's not'")
            print("   Should be: 'Here's why that's not' or 'That's not'")
            print("   Source: Gemini output (not fixed by cleanup)")
            print()
        
        # Check for broken paragraph structure
        if intro.count('<p>') > intro.count('</p>'):
            print("3. ❌ BROKEN HTML STRUCTURE (Line 316)")
            print("   Found: Unclosed <p> tags in intro")
            print("   Source: Gemini output or cleanup processor")
            print()
    
    # Issue 3: Content errors
    article_match = re.search(r'<article>(.*?)</article>', html_content, re.DOTALL)
    if article_match:
        article_content = article_match.group(1)
        
        errors = [
            (r'flows,capture', 'Missing space: "flows, capture"'),
            (r'You can effective', 'Broken phrase: "Effective"'),
            (r'A strong Complete Guide', 'Incomplete sentence'),
            (r"You'll find The top", 'Awkward phrasing: "Here are the top"'),
            (r'real-world implementations validate', 'Missing intro phrase'),
            (r'When you list hygiene', 'Broken phrase: "List hygiene"'),
            (r'Future-proofing your so you can strategy', 'Broken text: "Future-proofing your strategy"'),
            (r'This is complete Guide', 'Missing article: "This is a complete Guide"'),
        ]
        
        for pattern, description in errors:
            if re.search(pattern, article_content, re.IGNORECASE):
                print(f"4. ❌ CONTENT ERROR")
                print(f"   Pattern: {pattern}")
                print(f"   Issue: {description}")
                print(f"   Source: Gemini output (not caught by cleanup)")
                print()
    
    print("=" * 80)
    print("ERROR SOURCE ANALYSIS")
    print("=" * 80)
    print()
    print("Based on code analysis:")
    print()
    print("1. DOUBLE ENCODING (&amp;amp;):")
    print("   - Location: HTML renderer _escape_html() function")
    print("   - Cause: If Gemini outputs '&amp;' in JSON, _escape_html() converts it to '&amp;amp;'")
    print("   - Fix: Check if text is already HTML-encoded before escaping")
    print()
    print("2. GRAMMATICAL ERRORS:")
    print("   - Location: Gemini raw output (Stage 2)")
    print("   - Cause: Gemini generates these errors despite prompt instructions")
    print("   - Current cleanup: html_renderer._cleanup_content() tries to fix some patterns")
    print("   - Missing fixes: These specific errors aren't caught by cleanup regex")
    print()
    print("3. INCOMPLETE SENTENCES:")
    print("   - Location: Gemini raw output")
    print("   - Cause: Context loss during generation")
    print("   - Current cleanup: Some patterns fixed in _cleanup_content()")
    print("   - Missing: More comprehensive sentence completion validation needed")
    print()
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print()
    print("1. Fix double encoding in html_renderer._escape_html():")
    print("   - Check if text already contains HTML entities before escaping")
    print("   - Or decode entities first, then escape")
    print()
    print("2. Enhance cleanup in html_renderer._cleanup_content():")
    print("   - Add regex patterns for the specific grammatical errors found")
    print("   - Add sentence completion validation")
    print()
    print("3. Improve prompt in main_article.py:")
    print("   - Add more explicit examples of forbidden patterns")
    print("   - Add validation checklist that Gemini must follow")
    print()
    print("4. Add validation stage after extraction:")
    print("   - Check for common grammatical errors")
    print("   - Flag incomplete sentences")
    print("   - Optionally trigger regeneration if errors found")
    print()

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python investigate_errors.py <path-to-html-file>")
        print("Example: python investigate_errors.py output/article/index.html")
        sys.exit(1)
    html_file = sys.argv[1]
    analyze_article_errors(html_file)
