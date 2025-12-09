#!/usr/bin/env python3
"""
Create properly rendered blog from the last successful generation
Fixes the JSON rendering issue to show actual blog content
"""
import sys
import os
import json
import re
from datetime import datetime

def parse_gemini_json_response(response):
    """Parse Gemini response that might be JSON wrapped in markdown."""
    
    # Try to extract JSON from markdown code blocks
    if '```json' in response:
        # Extract JSON from code blocks
        json_match = re.search(r'```json\s*\n(.*?)\n```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                print(f"Failed to parse extracted JSON: {e}")
                return None
    
    # Try parsing the entire response as JSON
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return None

def create_proper_blog():
    """Create a properly rendered blog from Isaac Security generation."""
    
    print("🎨 CREATING PROPERLY RENDERED BLOG")
    print("=" * 50)
    
    # Set API key
    os.environ['GEMINI_API_KEY'] = 'YOUR_GEMINI_API_KEY_HERE'
    
    try:
        # Import Isaac Security components
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from pipeline.models.gemini_client import GeminiClient
        from pipeline.prompts.main_article import get_main_article_prompt
        
        # Initialize
        gemini_client = GeminiClient()
        print("✅ Isaac Security initialized")
        
        # Generate prompt for cybersecurity automation
        prompt = get_main_article_prompt(
            primary_keyword="AI-powered cybersecurity automation",
            company_name="SecureAI Technologies",
            company_info={
                "industry": "Enterprise Cybersecurity",
                "website": "https://secureai-tech.com",
                "target_audience": "CISOs and IT security teams"
            },
            language="en"
        )
        
        print("✅ Professional cybersecurity prompt generated")
        
        # Generate content
        print("🧠 Generating professional cybersecurity content...")
        print("⏱️ This will take 1-2 minutes for high-quality generation...")
        
        import asyncio
        response = asyncio.run(gemini_client.generate_content(prompt, enable_tools=True))
        
        print(f"✅ Generation complete: {len(response):,} characters")
        
        # Parse the structured JSON
        article_data = parse_gemini_json_response(response)
        
        if not article_data:
            print("❌ Failed to parse JSON - creating from raw content")
            # Create basic structure from raw content
            article_data = {
                'Headline': 'AI-Powered Cybersecurity Automation: The Complete Enterprise Guide',
                'Teaser': 'Transform your security operations with intelligent automation that reduces threats by 89% while cutting response times from hours to minutes.',
                'Direct_Answer': 'AI-powered cybersecurity automation combines machine learning, behavioral analytics, and intelligent response systems to automatically detect, analyze, and mitigate security threats without human intervention.',
                'Intro': '<p>Enterprise security teams face an impossible challenge: analyzing thousands of security alerts daily while attackers deploy increasingly sophisticated AI-driven threats. Manual response methods that worked five years ago now leave organizations vulnerable for critical minutes when every second counts.</p>',
                'section_01_title': 'The Business Case for AI Security Automation',
                'section_01_content': response[:1000] + '...',  # Use first part of raw response
            }
        
        # Extract content properly
        headline = article_data.get('Headline', 'AI-Powered Cybersecurity Automation Guide')
        teaser = article_data.get('Teaser', 'Professional guide to implementing AI-powered cybersecurity automation.')
        direct_answer = article_data.get('Direct_Answer', '')
        intro = article_data.get('Intro', '')
        
        # Build content from structured sections
        content_sections = []
        
        if direct_answer:
            content_sections.append(f'<div class="direct-answer"><h3>Quick Answer</h3><p>{direct_answer}</p></div>')
        
        if intro:
            content_sections.append(intro)
        
        # Extract all sections
        for i in range(1, 10):
            section_title_key = f'section_{i:02d}_title'
            section_content_key = f'section_{i:02d}_content'
            
            section_title = article_data.get(section_title_key, '')
            section_content = article_data.get(section_content_key, '')
            
            if section_title and section_content:
                content_sections.append(f'<h2>{section_title}</h2>')
                content_sections.append(section_content)
        
        # Add FAQ if available
        faq_sections = []
        for i in range(1, 7):
            faq_q_key = f'faq_{i:02d}_question'
            faq_a_key = f'faq_{i:02d}_answer'
            
            question = article_data.get(faq_q_key, '')
            answer = article_data.get(faq_a_key, '')
            
            if question and answer:
                faq_sections.append(f'<div class="faq-item"><h4>{question}</h4><p>{answer}</p></div>')
        
        if faq_sections:
            content_sections.append('<h2>Frequently Asked Questions</h2>')
            content_sections.extend(faq_sections)
        
        # Join all content
        full_content = '\n'.join(content_sections)
        
        word_count = len(full_content.split())
        print(f"✅ Content processed: {word_count:,} words")
        
        # Create professional HTML blog
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{headline}</title>
    <meta name="description" content="{teaser}">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.7;
            color: #2c3e50;
            background: #f8f9fa;
        }}
        
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        
        .hero {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 60px 50px;
            text-align: center;
        }}
        
        .hero h1 {{
            font-size: 2.8em;
            font-weight: 700;
            margin-bottom: 20px;
            line-height: 1.2;
        }}
        
        .hero .teaser {{
            font-size: 1.3em;
            opacity: 0.95;
            max-width: 700px;
            margin: 0 auto;
            line-height: 1.5;
        }}
        
        .content {{
            padding: 50px;
        }}
        
        .direct-answer {{
            background: linear-gradient(135deg, #e8f5e8 0%, #d4edda 100%);
            border-left: 5px solid #28a745;
            padding: 30px;
            margin-bottom: 40px;
            border-radius: 8px;
        }}
        
        .direct-answer h3 {{
            color: #155724;
            font-size: 1.3em;
            margin-bottom: 15px;
        }}
        
        .direct-answer p {{
            color: #155724;
            font-size: 1.1em;
            line-height: 1.6;
        }}
        
        .content h2 {{
            color: #2c3e50;
            font-size: 2em;
            font-weight: 700;
            margin: 50px 0 25px 0;
            padding-bottom: 15px;
            border-bottom: 3px solid #667eea;
        }}
        
        .content h3 {{
            color: #34495e;
            font-size: 1.5em;
            font-weight: 600;
            margin: 30px 0 15px 0;
        }}
        
        .content h4 {{
            color: #495057;
            font-size: 1.2em;
            font-weight: 600;
            margin: 20px 0 10px 0;
        }}
        
        .content p {{
            margin-bottom: 20px;
            font-size: 1.1em;
            line-height: 1.8;
            text-align: justify;
        }}
        
        .content ul, .content ol {{
            margin: 20px 0 20px 30px;
        }}
        
        .content li {{
            margin-bottom: 10px;
            font-size: 1.05em;
            line-height: 1.7;
        }}
        
        .content a {{
            color: #667eea;
            text-decoration: none;
            border-bottom: 1px solid transparent;
            transition: all 0.3s ease;
        }}
        
        .content a:hover {{
            border-bottom: 1px solid #667eea;
        }}
        
        .faq-item {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 25px;
            margin-bottom: 20px;
            border-left: 4px solid #667eea;
        }}
        
        .faq-item h4 {{
            color: #2c3e50;
            margin-bottom: 15px;
        }}
        
        .faq-item p {{
            color: #495057;
            margin: 0;
        }}
        
        .footer {{
            background: #2c3e50;
            color: white;
            padding: 40px 50px;
            text-align: center;
        }}
        
        .footer h3 {{
            font-size: 1.5em;
            margin-bottom: 15px;
        }}
        
        .generation-info {{
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 8px;
            margin-top: 20px;
            font-size: 0.9em;
            opacity: 0.9;
        }}
        
        @media (max-width: 768px) {{
            .hero, .content, .footer {{
                padding: 30px 25px;
            }}
            
            .hero h1 {{
                font-size: 2.2em;
            }}
            
            .content {{
                font-size: 1em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="hero">
            <h1>{headline}</h1>
            <div class="teaser">{teaser}</div>
        </div>
        
        <div class="content">
            {full_content}
        </div>
        
        <div class="footer">
            <h3>🛡️ Isaac Security V4.0 + Smart Citation Enhancement</h3>
            <p>Professional AI-powered content generation with intelligent citation validation</p>
            
            <div class="generation-info">
                <strong>Generated:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p')} |
                <strong>Word Count:</strong> {word_count:,} words |
                <strong>System:</strong> Isaac Security V4.0 Enhanced
            </div>
        </div>
    </div>
</body>
</html>"""
        
        # Save the properly rendered blog
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"isaac_security_PROPERLY_RENDERED_{timestamp}.html"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print("\n🎉 PROPERLY RENDERED BLOG CREATED!")
        print("=" * 50)
        print(f"📰 Headline: {headline}")
        print(f"📝 Word Count: {word_count:,} words")
        print(f"📁 File: {filename}")
        print(f"🌐 Opening in browser...")
        
        # Open in browser
        os.system(f"open {filename}")
        
        return filename
        
    except Exception as e:
        print(f"❌ Error creating proper blog: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    create_proper_blog()