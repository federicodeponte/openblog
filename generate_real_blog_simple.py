#!/usr/bin/env python3
"""
Generate ONE REAL Blog using Isaac Security Pipeline
Full pipeline with actual Gemini API calls - will take 3-5 minutes
"""
import sys
import os
import json
import time
from datetime import datetime

# Set API key
os.environ['GOOGLE_API_KEY'] = 'YOUR_GEMINI_API_KEY_HERE'

def generate_single_real_blog():
    """Generate one real blog with full Isaac Security pipeline."""
    
    print("🛡️ ISAAC SECURITY V4.0 - REAL BLOG GENERATION")
    print("=" * 60)
    print("⏱️ This will take 3-5 minutes for REAL generation...")
    print("🔄 Starting full pipeline with actual Gemini API calls")
    print()
    
    start_time = time.time()
    
    # Blog configuration
    company_data = {
        "company_name": "CyberShield Technologies",
        "company_url": "https://cybershield-tech.com",
        "industry": "Cybersecurity",
        "primary_keyword": "cybersecurity automation",
        "target_audience": "IT security professionals",
        "content_focus": "enterprise security solutions"
    }
    
    sitemap_data = {
        "sitemap_urls": [
            "https://cybershield-tech.com/products",
            "https://cybershield-tech.com/solutions",
            "https://cybershield-tech.com/resources"
        ],
        "competitors": [
            "https://crowdstrike.com",
            "https://paloaltonetworks.com",
            "https://fortinet.com"
        ]
    }
    
    try:
        # Import Isaac Security components
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from pipeline.models.gemini_client import GeminiClient
        from pipeline.prompts.main_article import get_main_article_prompt
        from pipeline.models.output_schema import build_article_response_schema, ArticleOutput
        
        print("✅ Isaac Security modules imported successfully")
        
        # Initialize Gemini client
        gemini_client = GeminiClient()
        print("✅ Gemini client initialized with API key")
        
        # Stage 1: Generate article prompt
        print("\n📝 Stage 1: Building article prompt...")
        prompt = get_main_article_prompt(
            company_data=company_data,
            sitemap_data=sitemap_data,
            language="en"
        )
        print(f"✅ Prompt generated ({len(prompt):,} characters)")
        
        # Stage 2: Call Gemini with structured JSON schema
        print("\n🧠 Stage 2: Calling Gemini with V4.0 structured JSON...")
        print("⏱️ This may take 2-3 minutes for high-quality generation...")
        
        schema = build_article_response_schema(ArticleOutput)
        
        generation_start = time.time()
        response = gemini_client.generate_content(prompt, response_schema=schema)
        generation_time = time.time() - generation_start
        
        print(f"✅ Gemini generation completed in {generation_time:.1f} seconds")
        
        if not response:
            raise Exception("No response from Gemini")
        
        # Parse JSON response
        if isinstance(response, str):
            try:
                article_data = json.loads(response)
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing failed: {e}")
                print("Raw response preview:", response[:500])
                return None
        else:
            article_data = response
        
        print("✅ Article JSON parsed successfully")
        
        # Stage 3: Extract and validate content
        print("\n📊 Stage 3: Extracting content...")
        
        headline = article_data.get('Headline', 'Untitled Article')
        teaser = article_data.get('Teaser', '')
        content = article_data.get('Content', '')
        
        if not content:
            raise Exception("No content generated")
        
        word_count = len(content.split())
        print(f"✅ Content extracted: {word_count} words")
        
        # Stage 4: Enhanced Smart Citation Processing
        print("\n🔍 Stage 4: Smart Citation Processing with Gemini...")
        
        # Import smart citation validator
        from pipeline.processors.ultimate_citation_validator import SmartCitationValidator, ValidationResult
        
        # Initialize smart validator with Gemini
        citation_validator = SmartCitationValidator(
            gemini_client=gemini_client,
            timeout=8.0
        )
        
        # Extract citations from content (simplified)
        import re
        citation_matches = re.findall(r'<a href="([^"]+)"[^>]*>([^<]+)</a>', content)
        
        if citation_matches:
            print(f"🔗 Found {len(citation_matches)} citations to validate...")
            
            # Convert to citation format
            citations_for_validation = []
            for i, (url, title) in enumerate(citation_matches, 1):
                citations_for_validation.append({
                    'url': url,
                    'title': title,
                    'authors': [],
                    'doi': '',
                    'year': 0
                })
            
            # Run smart citation validation
            validation_start = time.time()
            import asyncio
            validation_results = asyncio.run(citation_validator.validate_citations_simple(
                citations_for_validation,
                company_url=company_data['company_url'],
                competitors=sitemap_data['competitors']
            ))
            validation_time = time.time() - validation_start
            
            # Count replacements
            replacements_made = 0
            for result in validation_results:
                if hasattr(result, 'validation_type') and result.validation_type == 'alternative_found':
                    replacements_made += 1
            
            print(f"✅ Citation validation completed in {validation_time:.1f} seconds")
            print(f"🔄 Smart replacements made: {replacements_made}/{len(citation_matches)}")
        else:
            print("ℹ️ No citations found in content")
        
        # Stage 5: Generate HTML output
        print("\n🎨 Stage 5: Generating HTML output...")
        
        # Create professional HTML blog
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{headline}</title>
    <meta name="description" content="{teaser}">
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
            background-color: #fafafa;
        }}
        .article-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        .article-header h1 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 700;
        }}
        .teaser {{
            font-size: 1.2em;
            opacity: 0.9;
            margin-top: 15px;
        }}
        .article-content {{
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }}
        .meta {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            border-left: 4px solid #667eea;
        }}
        .meta h3 {{
            margin: 0 0 10px 0;
            color: #667eea;
        }}
        .citation-info {{
            background: #e8f5e8;
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
            border-left: 4px solid #28a745;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            background: #667eea;
            color: white;
            border-radius: 10px;
        }}
    </style>
</head>
<body>
    <div class="article-header">
        <h1>{headline}</h1>
        <div class="teaser">{teaser}</div>
    </div>
    
    <div class="meta">
        <h3>📊 Article Metrics</h3>
        <p><strong>Company:</strong> {company_data['company_name']}</p>
        <p><strong>Industry:</strong> {company_data['industry']}</p>
        <p><strong>Target Keyword:</strong> {company_data['primary_keyword']}</p>
        <p><strong>Word Count:</strong> {word_count:,} words</p>
        <p><strong>Generated:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
        <p><strong>Generation Time:</strong> {generation_time:.1f} seconds</p>
    </div>
    
    <div class="article-content">
        {content}
    </div>
    
    <div class="citation-info">
        <h3>🔍 Smart Citation Processing</h3>
        <p><strong>Citations Processed:</strong> {len(citation_matches) if 'citation_matches' in locals() else 0}</p>
        <p><strong>Smart Replacements:</strong> {replacements_made if 'replacements_made' in locals() else 0}</p>
        <p><strong>Validation System:</strong> Isaac Security V4.0 with Gemini-powered source replacement</p>
    </div>
    
    <div class="footer">
        <h3>🛡️ Generated by Isaac Security V4.0</h3>
        <p>Premium content generation with smart citation replacement</p>
    </div>
</body>
</html>"""
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"isaac_security_blog_{timestamp}.html"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        total_time = time.time() - start_time
        
        # Print final results
        print("\n" + "="*60)
        print("🎉 REAL BLOG GENERATION COMPLETE!")
        print("="*60)
        print(f"📝 Headline: {headline}")
        print(f"📊 Word Count: {word_count:,} words")
        print(f"⏱️ Total Generation Time: {total_time:.1f} seconds")
        print(f"🧠 Gemini Processing Time: {generation_time:.1f} seconds")
        print(f"🔗 Citations Processed: {len(citation_matches) if 'citation_matches' in locals() else 0}")
        print(f"📁 File Saved: {filename}")
        print(f"🌐 Open in browser: file://{os.path.abspath(filename)}")
        print("="*60)
        
        return {
            'success': True,
            'filename': filename,
            'headline': headline,
            'word_count': word_count,
            'generation_time': generation_time,
            'total_time': total_time,
            'citations_processed': len(citation_matches) if 'citation_matches' in locals() else 0
        }
        
    except Exception as e:
        print(f"\n❌ Error generating blog: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = generate_single_real_blog()
    if result:
        print("\n✅ Blog generation successful!")
        print(f"Open this file in your browser: {result['filename']}")
    else:
        print("\n❌ Blog generation failed")