#!/usr/bin/env python3
"""
Generate ONE REAL Blog using Isaac Security Pipeline - SIMPLIFIED APPROACH
This works with the actual Isaac Security codebase structure
"""
import sys
import os
import json
import time
from datetime import datetime

# Set API key
os.environ['GOOGLE_API_KEY'] = 'YOUR_GEMINI_API_KEY_HERE'

def generate_real_isaac_blog():
    """Generate one real blog with actual Isaac Security components."""
    
    print("🛡️ ISAAC SECURITY V4.0 - REAL BLOG GENERATION")
    print("=" * 60)
    print("⏱️ Estimated time: 3-5 minutes for REAL generation...")
    print("🔄 Starting full pipeline with actual Gemini API calls")
    print()
    
    start_time = time.time()
    
    # Blog configuration for cybersecurity topic
    company_data = {
        "company_name": "CyberShield Technologies",
        "company_url": "https://cybershield-tech.com",
        "industry": "Cybersecurity",
        "primary_keyword": "cybersecurity automation",
        "target_audience": "IT security professionals"
    }
    
    sitemap_data = {
        "sitemap_urls": [],
        "competitors": ["https://crowdstrike.com", "https://paloaltonetworks.com"]
    }
    
    try:
        # Import Isaac Security components
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from pipeline.models.gemini_client import GeminiClient
        from pipeline.prompts.main_article import get_main_article_prompt
        from pipeline.models.output_schema import ArticleOutput
        
        print("✅ Isaac Security modules imported successfully")
        
        # Initialize Gemini client
        gemini_client = GeminiClient()
        print("✅ Gemini client initialized with API key")
        
        # Stage 1: Generate article prompt using Isaac Security prompt
        print("\n📝 Stage 1: Building Isaac Security article prompt...")
        prompt = get_main_article_prompt(
            company_data=company_data,
            sitemap_data=sitemap_data,
            language="en"
        )
        print(f"✅ Prompt generated ({len(prompt):,} characters)")
        
        # Stage 2: Call Gemini for REAL content generation
        print("\n🧠 Stage 2: Calling Gemini API for REAL content...")
        print("⏱️ This will take 2-4 minutes for high-quality generation...")
        print("🔄 Please wait - generating professional cybersecurity content...")
        
        generation_start = time.time()
        
        # Use Isaac Security's Gemini client to generate content
        response = gemini_client.generate_content(prompt)
        
        generation_time = time.time() - generation_start
        
        print(f"✅ Gemini generation completed in {generation_time:.1f} seconds")
        
        if not response:
            raise Exception("No response from Gemini")
        
        # Try to parse as JSON first, if that fails use as text
        article_data = {}
        try:
            article_data = json.loads(response)
            print("✅ Response parsed as JSON successfully")
        except json.JSONDecodeError:
            print("ℹ️ Response is text format, extracting content...")
            # If not JSON, treat as content and create basic structure
            article_data = {
                'Headline': f'The Complete Guide to {company_data["primary_keyword"].title()} in 2024',
                'Teaser': 'Stay ahead of cybersecurity threats with advanced automation strategies.',
                'Content': response,
                'Meta_Title': f'{company_data["primary_keyword"].title()} Guide 2024 | {company_data["company_name"]}',
                'Meta_Description': f'Learn {company_data["primary_keyword"]} best practices and implementation strategies.'
            }
        
        # Extract key fields with fallbacks
        headline = article_data.get('Headline', f'Advanced {company_data["primary_keyword"].title()} Strategies for 2024')
        teaser = article_data.get('Teaser', 'Comprehensive guide to implementing advanced cybersecurity automation.')
        content = article_data.get('Content', response)  # Use raw response if no specific content field
        
        if not content:
            raise Exception("No content generated - empty response from Gemini")
        
        word_count = len(content.split())
        print(f"✅ Content extracted: {word_count:,} words")
        
        # Stage 3: Smart Citation Processing (if content has links)
        print("\n🔍 Stage 3: Analyzing citations in content...")
        
        # Extract any URLs from the content
        import re
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        found_urls = re.findall(url_pattern, content)
        
        if found_urls:
            print(f"🔗 Found {len(found_urls)} URLs in content")
            
            # Import smart citation validator
            try:
                from pipeline.processors.ultimate_citation_validator import SmartCitationValidator
                
                validator = SmartCitationValidator(gemini_client=gemini_client, timeout=8.0)
                print("✅ Smart citation validator initialized")
                
                # Prepare citations for validation
                citations_for_validation = []
                for i, url in enumerate(found_urls, 1):
                    citations_for_validation.append({
                        'url': url,
                        'title': f'Source {i}',
                        'authors': [],
                        'doi': '',
                        'year': 0
                    })
                
                # Run validation
                citation_start = time.time()
                import asyncio
                validation_results = asyncio.run(validator.validate_citations_simple(
                    citations_for_validation,
                    company_url=company_data['company_url'],
                    competitors=sitemap_data['competitors']
                ))
                citation_time = time.time() - citation_start
                
                replacements_made = sum(1 for result in validation_results 
                                      if hasattr(result, 'validation_type') and 
                                      result.validation_type == 'alternative_found')
                
                print(f"✅ Citation validation completed in {citation_time:.1f} seconds")
                print(f"🔄 Smart replacements made: {replacements_made}/{len(found_urls)}")
                
            except Exception as e:
                print(f"⚠️ Citation validation skipped: {e}")
                replacements_made = 0
        else:
            print("ℹ️ No URLs found in content for citation validation")
            replacements_made = 0
        
        # Stage 4: Generate professional HTML output
        print("\n🎨 Stage 4: Creating professional HTML blog...")
        
        # Clean content for HTML
        if not content.startswith('<'):
            # If content is plain text, add basic HTML formatting
            paragraphs = content.split('\n\n')
            formatted_paragraphs = [f'<p>{p.strip()}</p>' for p in paragraphs if p.strip()]
            content = '\n'.join(formatted_paragraphs)
        
        # Create comprehensive HTML blog
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
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            min-height: 100vh;
            box-shadow: 0 0 30px rgba(0,0,0,0.1);
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 60px 40px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 2.8em;
            font-weight: 700;
            margin-bottom: 20px;
            line-height: 1.2;
        }}
        .header .teaser {{
            font-size: 1.3em;
            opacity: 0.9;
            max-width: 600px;
            margin: 0 auto;
        }}
        .meta-info {{
            background: #f8f9fa;
            padding: 30px 40px;
            border-left: 5px solid #667eea;
            margin: 0;
        }}
        .meta-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .meta-item {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #e9ecef;
        }}
        .meta-item strong {{
            color: #667eea;
            display: block;
            margin-bottom: 5px;
        }}
        .article-content {{
            padding: 50px 40px;
            font-size: 1.1em;
            line-height: 1.8;
        }}
        .article-content p {{
            margin-bottom: 20px;
        }}
        .article-content h2 {{
            color: #2c3e50;
            font-size: 1.8em;
            margin: 40px 0 20px 0;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }}
        .article-content h3 {{
            color: #34495e;
            font-size: 1.4em;
            margin: 30px 0 15px 0;
        }}
        .article-content ul, .article-content ol {{
            margin: 20px 0 20px 30px;
        }}
        .article-content li {{
            margin-bottom: 10px;
        }}
        .stats-section {{
            background: #e8f5e8;
            padding: 30px 40px;
            border-left: 5px solid #28a745;
            margin: 0;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .stat-item {{
            text-align: center;
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }}
        .stat-number {{
            font-size: 2.5em;
            font-weight: 700;
            color: #28a745;
            display: block;
        }}
        .stat-label {{
            color: #6c757d;
            margin-top: 5px;
        }}
        .footer {{
            background: #2c3e50;
            color: white;
            padding: 40px;
            text-align: center;
        }}
        .footer h3 {{
            font-size: 1.5em;
            margin-bottom: 15px;
        }}
        .generation-badge {{
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            padding: 10px 20px;
            border-radius: 25px;
            display: inline-block;
            margin-top: 20px;
            font-weight: 600;
        }}
        @media (max-width: 768px) {{
            .header, .article-content, .meta-info, .stats-section, .footer {{
                padding: 30px 20px;
            }}
            .header h1 {{
                font-size: 2.2em;
            }}
            .meta-grid, .stats-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{headline}</h1>
            <div class="teaser">{teaser}</div>
        </div>
        
        <div class="meta-info">
            <h3>📊 Article Information</h3>
            <div class="meta-grid">
                <div class="meta-item">
                    <strong>Company</strong>
                    {company_data['company_name']}
                </div>
                <div class="meta-item">
                    <strong>Industry</strong>
                    {company_data['industry']}
                </div>
                <div class="meta-item">
                    <strong>Target Keyword</strong>
                    {company_data['primary_keyword']}
                </div>
                <div class="meta-item">
                    <strong>Generated</strong>
                    {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
                </div>
            </div>
        </div>
        
        <div class="article-content">
            {content}
        </div>
        
        <div class="stats-section">
            <h3>📈 Generation Statistics</h3>
            <div class="stats-grid">
                <div class="stat-item">
                    <span class="stat-number">{word_count:,}</span>
                    <div class="stat-label">Words Generated</div>
                </div>
                <div class="stat-item">
                    <span class="stat-number">{generation_time:.1f}s</span>
                    <div class="stat-label">Gemini Generation Time</div>
                </div>
                <div class="stat-item">
                    <span class="stat-number">{len(found_urls) if 'found_urls' in locals() else 0}</span>
                    <div class="stat-label">URLs Analyzed</div>
                </div>
                <div class="stat-item">
                    <span class="stat-number">{replacements_made}</span>
                    <div class="stat-label">Smart Replacements</div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <h3>🛡️ Isaac Security V4.0</h3>
            <p>Premium content generation with smart citation replacement technology</p>
            <div class="generation-badge">
                REAL Blog Generation • API-Powered • Production Quality
            </div>
        </div>
    </div>
</body>
</html>"""
        
        # Save to file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"isaac_security_real_blog_{timestamp}.html"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        total_time = time.time() - start_time
        
        # Print comprehensive results
        print("\n" + "="*70)
        print("🎉 REAL ISAAC SECURITY BLOG GENERATION COMPLETE!")
        print("="*70)
        print(f"📝 Headline: {headline}")
        print(f"📊 Word Count: {word_count:,} words")
        print(f"⏱️ Total Generation Time: {total_time:.1f} seconds")
        print(f"🧠 Gemini Processing Time: {generation_time:.1f} seconds")
        print(f"🔗 URLs Found: {len(found_urls) if 'found_urls' in locals() else 0}")
        print(f"🔄 Smart Replacements: {replacements_made}")
        print(f"📁 File Saved: {filename}")
        print(f"🌐 Full Path: {os.path.abspath(filename)}")
        print("="*70)
        print("📖 TO VIEW THE BLOG:")
        print(f"   Open this file in your browser: {filename}")
        print("   Or run: open " + filename)
        print("="*70)
        
        return {
            'success': True,
            'filename': filename,
            'headline': headline,
            'word_count': word_count,
            'generation_time': generation_time,
            'total_time': total_time,
            'urls_found': len(found_urls) if 'found_urls' in locals() else 0,
            'replacements_made': replacements_made
        }
        
    except Exception as e:
        print(f"\n❌ Error generating blog: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = generate_real_isaac_blog()
    if result:
        print(f"\n🎉 SUCCESS! Open this file to view your blog: {result['filename']}")
        # Auto-open in browser
        os.system(f"open {result['filename']}")
    else:
        print("\n❌ Blog generation failed - check errors above")