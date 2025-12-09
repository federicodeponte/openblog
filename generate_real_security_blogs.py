#!/usr/bin/env python3
"""
Generate REAL security blogs using Isaac Security V4.0 pipeline
This will take several minutes per blog - generating actual content with Gemini
"""

import sys
import os
import json
import asyncio
import time
from datetime import datetime
from pathlib import Path

# Add the current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import Isaac Security pipeline
from pipeline.core.execution_context import ExecutionContext
from pipeline.blog_generation.stage_01_prompt_build import PromptBuildStage
from pipeline.blog_generation.stage_02_gemini_call import GeminiCallStage
from pipeline.blog_generation.stage_03_extraction import ExtractionStage
from pipeline.blog_generation.stage_04_citations import CitationsStage
from pipeline.blog_generation.stage_10_cleanup import CleanupStage
from pipeline.models.gemini_client import GeminiClient

class RealBlogGenerator:
    """Generate real security blogs using Isaac Security V4.0"""
    
    def __init__(self):
        self.results = []
        self.output_dir = Path("generated_blogs")
        self.output_dir.mkdir(exist_ok=True)
        
    def create_security_topics(self):
        """Create 3 high-value security topics for real generation"""
        return [
            {
                "id": 1,
                "primary_keyword": "AI cybersecurity threats 2024",
                "company_name": "SecureAI Technologies",
                "company_url": "https://secureai-tech.com",
                "language": "en",
                "country": "US",
                "word_count": 2500,
                "focus": "AI-powered cyber attack detection and prevention strategies"
            },
            {
                "id": 2,
                "primary_keyword": "zero trust architecture implementation",
                "company_name": "ZeroTrust Solutions",
                "company_url": "https://zerotrust-solutions.com", 
                "language": "en",
                "country": "US",
                "word_count": 3000,
                "focus": "Enterprise zero trust security framework deployment"
            },
            {
                "id": 3,
                "primary_keyword": "ransomware prevention strategies",
                "company_name": "RansomShield Pro",
                "company_url": "https://ransomshield-pro.com",
                "language": "en", 
                "country": "US",
                "word_count": 2800,
                "focus": "Advanced ransomware detection and response systems"
            }
        ]
    
    async def generate_real_blog(self, topic):
        """Generate a single REAL blog using Isaac Security pipeline"""
        
        blog_id = topic["id"]
        start_time = time.time()
        
        print(f"\n🚀 BLOG {blog_id}: Starting REAL generation")
        print(f"   Topic: {topic['primary_keyword']}")
        print(f"   Company: {topic['company_name']}")
        print(f"   Target: {topic['word_count']} words")
        print(f"   This will take 3-8 minutes for real AI generation...")
        
        try:
            # Create execution context with proper job_id
            context = ExecutionContext(job_id=f"blog_{blog_id}_{int(time.time())}")
            
            # Set context data
            context.primary_keyword = topic["primary_keyword"]
            context.company_name = topic["company_name"] 
            context.website = topic["company_url"]
            context.language = topic["language"]
            context.country = topic["country"]
            context.word_count = topic["word_count"]
            
            # Initialize data structures
            context.company_data = {
                "company_name": topic["company_name"],
                "company_url": topic["company_url"],
                "focus_area": topic["focus"]
            }
            
            context.sitemap_data = {
                "competitors": ["competitor1.com", "competitor2.com"],
                "pages": []
            }
            
            context.parallel_results = {}
            
            # Stage 1: Prompt Building
            print(f"   📝 Stage 1: Building market-aware prompt...")
            stage1_start = time.time()
            prompt_stage = PromptBuildStage()
            await prompt_stage.execute(context)
            stage1_time = time.time() - stage1_start
            print(f"   ✅ Prompt built ({stage1_time:.2f}s)")
            
            # Stage 2: Gemini AI Generation (This is the long one!)
            print(f"   🤖 Stage 2: Gemini AI content generation...")
            print(f"      This stage generates {topic['word_count']} words of high-quality content...")
            stage2_start = time.time()
            gemini_stage = GeminiCallStage()
            await gemini_stage.execute(context)
            stage2_time = time.time() - stage2_start
            print(f"   ✅ AI content generated ({stage2_time:.2f}s)")
            
            # Stage 3: Content Extraction  
            print(f"   🔍 Stage 3: Extracting structured content...")
            stage3_start = time.time()
            extraction_stage = ExtractionStage()
            await extraction_stage.execute(context)
            stage3_time = time.time() - stage3_start
            print(f"   ✅ Content extracted ({stage3_time:.2f}s)")
            
            # Stage 4: Smart Citation Validation
            print(f"   📚 Stage 4: Smart citation validation...")
            stage4_start = time.time()
            citations_stage = CitationsStage()
            await citations_stage.execute(context)
            stage4_time = time.time() - stage4_start
            print(f"   ✅ Citations processed ({stage4_time:.2f}s)")
            
            # Stage 10: HTML Generation and Cleanup
            print(f"   🎨 Stage 10: HTML generation and cleanup...")
            stage10_start = time.time()
            cleanup_stage = CleanupStage()
            await cleanup_stage.execute(context)
            stage10_time = time.time() - stage10_start
            print(f"   ✅ HTML generated ({stage10_time:.2f}s)")
            
            # Get the final results
            final_html = context.parallel_results.get('final_html', '')
            structured_data = context.structured_data
            citations_html = context.parallel_results.get('citations_html', '')
            
            total_time = time.time() - start_time
            
            # Save the complete blog to file
            blog_filename = f"blog_{blog_id}_{topic['primary_keyword'].replace(' ', '_')}.html"
            blog_path = self.output_dir / blog_filename
            
            with open(blog_path, 'w', encoding='utf-8') as f:
                f.write(final_html)
            
            # Count actual content metrics
            word_count = len(final_html.split()) if final_html else 0
            citation_count = len(structured_data.sources) if structured_data and structured_data.sources else 0
            
            result = {
                "blog_id": blog_id,
                "status": "success",
                "topic": topic["primary_keyword"],
                "company": topic["company_name"],
                "title": structured_data.title if structured_data else f"Complete Guide to {topic['primary_keyword'].title()}",
                "file_path": str(blog_path),
                "content": {
                    "word_count": word_count,
                    "has_html": bool(final_html),
                    "html_length": len(final_html) if final_html else 0
                },
                "citations": {
                    "total_sources": citation_count,
                    "citations_html_length": len(citations_html),
                    "has_citations": bool(citations_html)
                },
                "performance": {
                    "total_time": total_time,
                    "stage1_prompt_time": stage1_time,
                    "stage2_ai_generation_time": stage2_time,
                    "stage3_extraction_time": stage3_time,
                    "stage4_citations_time": stage4_time,
                    "stage10_html_time": stage10_time
                },
                "pipeline_stages": {
                    "prompt_building": "completed",
                    "ai_content_generation": "completed",
                    "content_extraction": "completed", 
                    "citation_validation": "completed",
                    "html_generation": "completed"
                }
            }
            
            print(f"   🎉 BLOG {blog_id}: REAL SUCCESS ({total_time:.2f}s total)")
            print(f"      File: {blog_filename}")
            print(f"      Content: {word_count} words")
            print(f"      Citations: {citation_count} sources")
            
            return result
            
        except Exception as e:
            error_time = time.time() - start_time
            print(f"   ❌ BLOG {blog_id}: FAILED ({error_time:.2f}s)")
            print(f"      Error: {str(e)}")
            
            return {
                "blog_id": blog_id,
                "status": "failed",
                "topic": topic["primary_keyword"],
                "error": str(e),
                "performance": {
                    "total_time": error_time,
                    "error_stage": "unknown"
                }
            }
    
    async def generate_batch(self, topics):
        """Generate a batch of real blogs"""
        
        print("🛡️  ISAAC SECURITY V4.0 - REAL BLOG GENERATION")
        print("=" * 80)
        print(f"Generating {len(topics)} REAL security blogs with full AI content")
        print("Each blog will take 3-8 minutes for complete generation")
        print("Total estimated time: 10-25 minutes")
        print("=" * 80)
        
        start_time = time.time()
        
        # Generate blogs sequentially to avoid API rate limits
        results = []
        for i, topic in enumerate(topics, 1):
            print(f"\n📍 GENERATING BLOG {i}/{len(topics)}")
            result = await self.generate_real_blog(topic)
            results.append(result)
            
            # Small delay between blogs
            if i < len(topics):
                print(f"   ⏳ Waiting 30s before next blog...")
                await asyncio.sleep(30)
        
        total_time = time.time() - start_time
        
        # Analyze results
        successful_blogs = [r for r in results if r.get("status") == "success"]
        failed_blogs = [r for r in results if r.get("status") != "success"]
        
        print(f"\n🏆 REAL BLOG GENERATION COMPLETE")
        print("=" * 60)
        print(f"Total time: {total_time/60:.1f} minutes")
        print(f"Successful: {len(successful_blogs)}/{len(topics)}")
        print(f"Failed: {len(failed_blogs)}")
        
        if successful_blogs:
            avg_time = sum(r["performance"]["total_time"] for r in successful_blogs) / len(successful_blogs)
            avg_words = sum(r["content"]["word_count"] for r in successful_blogs) / len(successful_blogs)
            total_citations = sum(r["citations"]["total_sources"] for r in successful_blogs)
            
            print(f"Average time per blog: {avg_time/60:.1f} minutes")
            print(f"Average word count: {avg_words:.0f} words")
            print(f"Total citations: {total_citations}")
        
        print(f"\n📂 Generated blogs saved to: {self.output_dir}/")
        for result in successful_blogs:
            print(f"   📄 {result['file_path']}")
        
        # Save results summary
        results_file = self.output_dir / f"generation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump({
                "summary": {
                    "total_blogs": len(topics),
                    "successful": len(successful_blogs),
                    "failed": len(failed_blogs),
                    "total_time_minutes": total_time/60
                },
                "detailed_results": results
            }, f, indent=2)
        
        print(f"📊 Results summary: {results_file}")
        
        return results

async def main():
    """Main function to run real blog generation"""
    
    # Check for required environment variables
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ ERROR: GEMINI_API_KEY environment variable not set")
        print("Please set your Gemini API key:")
        print("export GEMINI_API_KEY='your-key-here'")
        return
    
    print("🔑 Gemini API key found")
    
    generator = RealBlogGenerator()
    topics = generator.create_security_topics()
    
    print(f"\n📋 REAL SECURITY BLOG TOPICS:")
    for topic in topics:
        print(f"   {topic['id']}. {topic['primary_keyword']} - {topic['company_name']} ({topic['word_count']} words)")
    
    print(f"\n⚠️  WARNING: This will make real API calls and generate actual content!")
    print(f"Estimated cost: $2-5 for 3 blogs")
    print(f"Estimated time: 15-25 minutes")
    
    # Confirm before proceeding
    confirm = input("\n🤔 Proceed with REAL blog generation? (yes/no): ")
    if confirm.lower() != 'yes':
        print("❌ Generation cancelled")
        return
    
    # Generate the real blogs
    results = await generator.generate_batch(topics)
    
    # Create browser viewer for real results
    create_real_blog_viewer(results, generator.output_dir)

def create_real_blog_viewer(results, output_dir):
    """Create HTML viewer for real blog results"""
    
    successful_blogs = [r for r in results if r.get("status") == "success"]
    
    if not successful_blogs:
        print("❌ No successful blogs to display")
        return
    
    viewer_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Isaac Security V4.0 - Real Blog Generation Results</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        
        .header {{
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        
        .real-badge {{
            background: #38a169;
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            margin: 10px 0;
            display: inline-block;
        }}
        
        .blog-card {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }}
        
        .blog-card:hover {{
            transform: translateY(-5px);
        }}
        
        .blog-title {{
            font-size: 1.5rem;
            font-weight: bold;
            color: #2d3748;
            margin-bottom: 15px;
        }}
        
        .blog-meta {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
            padding: 15px;
            background: #f7fafc;
            border-radius: 8px;
        }}
        
        .meta-item {{
            color: #718096;
        }}
        
        .meta-value {{
            font-weight: bold;
            color: #2d3748;
        }}
        
        .view-btn {{
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 1rem;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            transition: background 0.3s ease;
        }}
        
        .view-btn:hover {{
            background: #5a67d8;
        }}
        
        .performance-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        
        .perf-card {{
            background: rgba(255,255,255,0.9);
            border-radius: 10px;
            padding: 20px;
            text-align: center;
        }}
        
        .perf-value {{
            font-size: 2rem;
            font-weight: bold;
            color: #2d3748;
        }}
        
        .perf-label {{
            color: #718096;
            margin-top: 5px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🛡️ Isaac Security V4.0</h1>
        <div class="real-badge">✅ REAL BLOG GENERATION COMPLETE</div>
        <p>Generated {len(successful_blogs)} complete security blogs with AI content</p>
    </div>
    
    <div class="performance-grid">
        <div class="perf-card">
            <div class="perf-value">{len(successful_blogs)}</div>
            <div class="perf-label">Real Blogs Generated</div>
        </div>
        <div class="perf-card">
            <div class="perf-value">{sum(r["content"]["word_count"] for r in successful_blogs)}</div>
            <div class="perf-label">Total Words Generated</div>
        </div>
        <div class="perf-card">
            <div class="perf-value">{sum(r["citations"]["total_sources"] for r in successful_blogs)}</div>
            <div class="perf-label">Citations Processed</div>
        </div>
    </div>
"""
    
    for blog in successful_blogs:
        viewer_html += f"""
    <div class="blog-card">
        <div class="blog-title">{blog['title']}</div>
        <div class="blog-meta">
            <div class="meta-item">
                <div class="meta-value">{blog['company']}</div>
                <div>Company</div>
            </div>
            <div class="meta-item">
                <div class="meta-value">{blog['content']['word_count']:,}</div>
                <div>Words Generated</div>
            </div>
            <div class="meta-item">
                <div class="meta-value">{blog['performance']['total_time']/60:.1f} min</div>
                <div>Generation Time</div>
            </div>
            <div class="meta-item">
                <div class="meta-value">{blog['citations']['total_sources']}</div>
                <div>Citations</div>
            </div>
        </div>
        <a href="{Path(blog['file_path']).name}" target="_blank" class="view-btn">📄 View Full Blog</a>
    </div>
"""
    
    viewer_html += """
</body>
</html>"""
    
    # Save viewer
    viewer_path = output_dir / "blog_viewer.html"
    with open(viewer_path, 'w', encoding='utf-8') as f:
        f.write(viewer_html)
    
    print(f"\n🌐 Blog viewer created: {viewer_path}")
    print(f"📂 Open in browser to view all generated blogs")
    
    # Try to open in browser
    import subprocess
    try:
        subprocess.run(['open', str(viewer_path)], check=False)
        print("🚀 Opening in browser...")
    except:
        print(f"Please open manually: {viewer_path}")

if __name__ == "__main__":
    asyncio.run(main())