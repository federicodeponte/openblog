#!/usr/bin/env python3
"""
FINAL Real Blog Generation - Isaac Security V4.0
Works with actual Isaac Security function signatures and parameters
"""
import sys
import os
import json
import time
from datetime import datetime

# Set API key for Isaac Security
os.environ['GEMINI_API_KEY'] = 'YOUR_GEMINI_API_KEY_HERE'

def run_real_generation():
    """Run REAL Isaac Security blog generation with correct parameters."""
    
    print("🛡️ ISAAC SECURITY V4.0 - FINAL REAL BLOG GENERATION")
    print("=" * 65)
    print("⏱️ Estimated time: 3-5 minutes for REAL Gemini API generation...")
    print("🔄 Using actual Isaac Security pipeline with correct parameters")
    print()
    
    start_time = time.time()
    
    try:
        # Import Isaac Security components
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from pipeline.models.gemini_client import GeminiClient
        from pipeline.prompts.main_article import get_main_article_prompt
        
        print("✅ Isaac Security modules imported successfully")
        
        # Initialize Gemini client with API key
        gemini_client = GeminiClient()
        print("✅ Gemini client initialized")
        
        # Stage 1: Generate article prompt using correct Isaac Security parameters
        print("\n📝 Stage 1: Building article prompt with correct parameters...")
        
        # Use correct parameter names from Isaac Security
        prompt = get_main_article_prompt(
            primary_keyword="cybersecurity automation",
            company_name="CyberShield Technologies", 
            company_info={
                "industry": "Cybersecurity",
                "website": "https://cybershield-tech.com",
                "target_audience": "IT security professionals"
            },
            language="en",
            country="US",
            competitors=["crowdstrike.com", "paloaltonetworks.com"],
            custom_instructions="Focus on enterprise-level cybersecurity automation solutions and best practices."
        )
        
        print(f"✅ Isaac Security prompt generated ({len(prompt):,} characters)")
        
        # Stage 2: Generate content with Gemini API
        print("\n🧠 Stage 2: Calling Gemini API for REAL content generation...")
        print("⏱️ This will take 2-4 minutes - generating high-quality content...")
        print("🚀 Please wait while Gemini processes the full prompt...")
        print()
        
        generation_start = time.time()
        
        # Call Gemini with enable_tools for web search
        import asyncio
        response = asyncio.run(gemini_client.generate_content(prompt, enable_tools=True))
        
        generation_time = time.time() - generation_start
        
        print(f"✅ Gemini API generation completed in {generation_time:.1f} seconds")
        
        if not response:
            raise Exception("No response from Gemini API")
        
        print(f"✅ Response received: {len(response):,} characters")
        
        # Parse response (try JSON first, fallback to text)
        article_data = {}
        content = response
        
        try:
            article_data = json.loads(response)
            content = article_data.get('Content', response)
            headline = article_data.get('Headline', 'Advanced Cybersecurity Automation for Enterprise Security')
            teaser = article_data.get('Teaser', 'Comprehensive guide to implementing cybersecurity automation.')
            print("✅ Response parsed as structured JSON")
        except json.JSONDecodeError:
            headline = "The Complete Guide to Cybersecurity Automation in 2024"
            teaser = "Learn how to implement advanced cybersecurity automation strategies for enterprise-level protection."
            print("✅ Response processed as text content")
        
        word_count = len(content.split())
        print(f"✅ Content analysis: {word_count:,} words generated")
        
        # Stage 3: Smart citation analysis
        print("\n🔍 Stage 3: Smart citation analysis...")
        
        import re
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        found_urls = re.findall(url_pattern, content)
        
        replacements_made = 0
        if found_urls:
            print(f"🔗 Found {len(found_urls)} URLs in generated content")
            
            # Try smart citation validation
            try:
                from pipeline.processors.ultimate_citation_validator import SmartCitationValidator
                
                validator = SmartCitationValidator(gemini_client=gemini_client, timeout=5.0)
                
                # Quick validation sample
                sample_citations = [{'url': url, 'title': f'Source {i+1}', 'authors': [], 'doi': '', 'year': 0} 
                                  for i, url in enumerate(found_urls[:3])]  # Test first 3 URLs only
                
                citation_start = time.time()
                import asyncio
                validation_results = asyncio.run(validator.validate_citations_simple(
                    sample_citations,
                    company_url="https://cybershield-tech.com",
                    competitors=["crowdstrike.com", "paloaltonetworks.com"]
                ))
                citation_time = time.time() - citation_start
                
                replacements_made = sum(1 for result in validation_results 
                                      if hasattr(result, 'validation_type') and 
                                      'alternative' in str(result.validation_type))
                
                print(f"✅ Smart citation validation completed in {citation_time:.1f} seconds")
                print(f"🔄 Smart replacements: {replacements_made}/{len(sample_citations)} tested")
                
            except Exception as e:
                print(f"⚠️ Smart citation validation skipped: {e}")
                replacements_made = 0
        else:
            print("ℹ️ No URLs found in content")
        
        # Stage 4: Create professional HTML output
        print("\n🎨 Stage 4: Creating professional HTML blog presentation...")
        
        # Ensure content has HTML formatting
        if not any(tag in content for tag in ['<p>', '<h2>', '<h3>', '<ul>', '<ol>']):
            # Add basic HTML formatting to plain text
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            formatted_content = '\n'.join([f'<p>{p}</p>' for p in paragraphs])
            content = formatted_content
        
        # Create premium HTML presentation
        html_blog = f"""<!DOCTYPE html>
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
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        
        .blog-container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            min-height: 100vh;
            box-shadow: 0 20px 60px rgba(0,0,0,0.2);
        }}
        
        .hero-section {{
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 80px 50px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }}
        
        .hero-section::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(45deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
        }}
        
        .hero-content {{
            position: relative;
            z-index: 1;
        }}
        
        .hero-section h1 {{
            font-size: 3.2em;
            font-weight: 800;
            margin-bottom: 25px;
            line-height: 1.2;
            text-shadow: 0 2px 10px rgba(0,0,0,0.3);
        }}
        
        .hero-section .teaser {{
            font-size: 1.4em;
            opacity: 0.95;
            max-width: 700px;
            margin: 0 auto 30px;
            line-height: 1.6;
        }}
        
        .generation-badge {{
            background: rgba(255,255,255,0.2);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.3);
            color: white;
            padding: 12px 30px;
            border-radius: 30px;
            display: inline-block;
            font-weight: 600;
            font-size: 0.9em;
            letter-spacing: 0.5px;
        }}
        
        .article-meta {{
            background: #f8f9fa;
            padding: 40px 50px;
            border-left: 6px solid #667eea;
        }}
        
        .meta-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 25px;
            margin-top: 25px;
        }}
        
        .meta-card {{
            background: white;
            padding: 25px;
            border-radius: 12px;
            border: 1px solid #e9ecef;
            box-shadow: 0 5px 15px rgba(0,0,0,0.05);
            transition: transform 0.3s ease;
        }}
        
        .meta-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        }}
        
        .meta-card-title {{
            color: #667eea;
            font-weight: 700;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }}
        
        .meta-card-value {{
            color: #2c3e50;
            font-size: 1.1em;
            font-weight: 600;
        }}
        
        .content-section {{
            padding: 60px 50px;
            font-size: 1.1em;
            line-height: 1.8;
            max-width: none;
        }}
        
        .content-section p {{
            margin-bottom: 25px;
            text-align: justify;
        }}
        
        .content-section h2 {{
            color: #2c3e50;
            font-size: 2.2em;
            font-weight: 700;
            margin: 50px 0 25px 0;
            padding-bottom: 15px;
            border-bottom: 3px solid #667eea;
            position: relative;
        }}
        
        .content-section h3 {{
            color: #34495e;
            font-size: 1.6em;
            font-weight: 600;
            margin: 35px 0 20px 0;
        }}
        
        .stats-showcase {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 50px;
            text-align: center;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 30px;
            margin-top: 30px;
        }}
        
        .stat-card {{
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            padding: 30px 20px;
            border-radius: 15px;
            border: 1px solid rgba(255,255,255,0.2);
            transition: all 0.3s ease;
        }}
        
        .stat-card:hover {{
            background: rgba(255,255,255,0.2);
            transform: translateY(-5px);
        }}
        
        .stat-number {{
            font-size: 3em;
            font-weight: 800;
            display: block;
            margin-bottom: 10px;
            text-shadow: 0 2px 10px rgba(0,0,0,0.3);
        }}
        
        .stat-label {{
            font-size: 1em;
            opacity: 0.9;
            font-weight: 500;
            letter-spacing: 0.5px;
        }}
        
        .footer-section {{
            background: #2c3e50;
            color: white;
            padding: 60px 50px;
            text-align: center;
        }}
        
        .footer-title {{
            font-size: 2em;
            font-weight: 700;
            margin-bottom: 20px;
        }}
        
        .footer-subtitle {{
            font-size: 1.2em;
            opacity: 0.8;
            margin-bottom: 30px;
        }}
        
        .powered-by {{
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            padding: 15px 35px;
            border-radius: 30px;
            display: inline-block;
            font-weight: 700;
            font-size: 1em;
            letter-spacing: 0.5px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.3);
        }}
        
        @media (max-width: 768px) {{
            .hero-section, .article-meta, .content-section, .stats-showcase, .footer-section {{
                padding: 40px 25px;
            }}
            
            .hero-section h1 {{
                font-size: 2.5em;
            }}
            
            .meta-grid, .stats-grid {{
                grid-template-columns: 1fr;
                gap: 20px;
            }}
            
            .content-section {{
                font-size: 1em;
            }}
        }}
    </style>
</head>
<body>
    <div class="blog-container">
        <!-- Hero Section -->
        <section class="hero-section">
            <div class="hero-content">
                <h1>{headline}</h1>
                <div class="teaser">{teaser}</div>
                <div class="generation-badge">🛡️ Isaac Security V4.0 • Real-Time Generated</div>
            </div>
        </section>
        
        <!-- Article Metadata -->
        <section class="article-meta">
            <h3>📊 Article Details</h3>
            <div class="meta-grid">
                <div class="meta-card">
                    <div class="meta-card-title">Company</div>
                    <div class="meta-card-value">CyberShield Technologies</div>
                </div>
                <div class="meta-card">
                    <div class="meta-card-title">Industry Focus</div>
                    <div class="meta-card-value">Enterprise Cybersecurity</div>
                </div>
                <div class="meta-card">
                    <div class="meta-card-title">Target Keyword</div>
                    <div class="meta-card-value">cybersecurity automation</div>
                </div>
                <div class="meta-card">
                    <div class="meta-card-title">Generated</div>
                    <div class="meta-card-value">{datetime.now().strftime('%B %d, %Y at %I:%M %p')}</div>
                </div>
            </div>
        </section>
        
        <!-- Main Content -->
        <section class="content-section">
            {content}
        </section>
        
        <!-- Generation Statistics -->
        <section class="stats-showcase">
            <h3>📈 Real-Time Generation Statistics</h3>
            <div class="stats-grid">
                <div class="stat-card">
                    <span class="stat-number">{word_count:,}</span>
                    <div class="stat-label">Words Generated</div>
                </div>
                <div class="stat-card">
                    <span class="stat-number">{generation_time:.1f}s</span>
                    <div class="stat-label">Gemini API Time</div>
                </div>
                <div class="stat-card">
                    <span class="stat-number">{len(found_urls) if found_urls else 0}</span>
                    <div class="stat-label">URLs Found</div>
                </div>
                <div class="stat-card">
                    <span class="stat-number">{replacements_made}</span>
                    <div class="stat-label">Smart Replacements</div>
                </div>
            </div>
        </section>
        
        <!-- Footer -->
        <section class="footer-section">
            <h3 class="footer-title">Isaac Security V4.0</h3>
            <div class="footer-subtitle">Premium AI-powered content generation with smart citation technology</div>
            <div class="powered-by">
                REAL GENERATION • GEMINI-POWERED • PRODUCTION QUALITY
            </div>
        </section>
    </div>
</body>
</html>"""
        
        # Save the real blog
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"isaac_security_REAL_blog_{timestamp}.html"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_blog)
        
        total_time = time.time() - start_time
        
        # Display final results
        print("\n" + "🎉" * 3 + " REAL ISAAC SECURITY BLOG COMPLETE! " + "🎉" * 3)
        print("=" * 75)
        print(f"📰 Headline: {headline}")
        print(f"📝 Word Count: {word_count:,} words")
        print(f"⏱️ Total Time: {total_time:.1f} seconds")
        print(f"🧠 Gemini Generation: {generation_time:.1f} seconds") 
        print(f"🔗 URLs Found: {len(found_urls) if found_urls else 0}")
        print(f"🔄 Smart Replacements: {replacements_made}")
        print(f"📁 Saved As: {filename}")
        print("=" * 75)
        print(f"🌐 VIEW YOUR BLOG: open {filename}")
        print("=" * 75)
        
        # Auto-open in browser
        os.system(f"open {filename}")
        
        return {
            'success': True,
            'filename': filename,
            'headline': headline, 
            'word_count': word_count,
            'generation_time': generation_time,
            'total_time': total_time
        }
        
    except Exception as e:
        print(f"\n❌ Error in real generation: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("🚀 Starting REAL Isaac Security blog generation...")
    result = run_real_generation()
    
    if result:
        print(f"\n✅ SUCCESS! Blog saved as: {result['filename']}")
        print("🌐 Opening in your browser...")
    else:
        print("\n❌ Generation failed - see errors above")