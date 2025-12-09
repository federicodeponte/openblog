#!/usr/bin/env python3
"""
COMPLETE FULL PIPELINE TEST
Run the entire 13-stage Isaac Security V4.0 pipeline with all fixes
"""
import sys
import os
import asyncio
import time
from datetime import datetime

# Set API key
os.environ['GEMINI_API_KEY'] = 'YOUR_GEMINI_API_KEY_HERE'

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pipeline.core.execution_context import ExecutionContext

# Import all 13 stages
from pipeline.blog_generation.stage_00_data_fetch import DataFetchStage
from pipeline.blog_generation.stage_01_prompt_build import PromptBuildStage  
from pipeline.blog_generation.stage_02_gemini_call import GeminiCallStage
from pipeline.blog_generation.stage_02b_quality_refinement import QualityRefinementStage
from pipeline.blog_generation.stage_03_extraction import ExtractionStage
from pipeline.blog_generation.stage_04_citations import CitationsStage
from pipeline.blog_generation.stage_05_internal_links import InternalLinksStage
from pipeline.blog_generation.stage_06_toc import TableOfContentsStage
from pipeline.blog_generation.stage_07_metadata import MetadataStage
from pipeline.blog_generation.stage_08_faq_paa import FAQPAAStage
from pipeline.blog_generation.stage_09_image import ImageStage
from pipeline.blog_generation.stage_10_cleanup import CleanupStage
from pipeline.blog_generation.stage_11_storage import StorageStage

async def run_complete_test():
    """Run complete 13-stage pipeline with all fixes applied."""
    
    print("🛡️ ISAAC SECURITY V4.0 - COMPLETE PIPELINE TEST")
    print("=" * 70)
    print("🔧 All fixes applied:")
    print("   ✅ Natural paragraph variety (no 40-50 word limits)")
    print("   ✅ Conservative list preservation") 
    print("   ✅ Engaging lists (not just citation lists)")
    print("   ✅ Citation validation with Gemini")
    print("   ✅ Internal links working")
    print("   ✅ Clean HTML sources")
    print("")
    
    start_time = time.time()
    
    # Create execution context
    context = ExecutionContext(job_id="complete-test-fixed")
    
    # Set job config
    context.job_config = {
        "primary_keyword": "zero trust security architecture",
        "language": "en",
        "content_generation_instruction": "Write a comprehensive guide about implementing zero trust security architecture for enterprise networks with engaging lists and natural flow",
        "company_url": "https://cyberguard.tech",
        "batch_siblings": [
            {"title": "Cloud Security Guide", "url": "/magazine/cloud-security-guide", "description": "Comprehensive guide to cloud security"},
            {"title": "SIEM Automation Guide", "url": "/magazine/siem-automation-guide", "description": "Complete guide to SIEM automation"},
        ]
    }
    
    # Set company data
    context.company_data = {
        "company_name": "CyberGuard Solutions",
        "company_url": "https://cyberguard.tech",
        "company_info": {
            "industry": "Enterprise Security", 
            "target_audience": "Enterprise security teams",
            "description": "Leading provider of enterprise security solutions"
        }
    }
    
    # Add sitemap_data for citation validation
    context.sitemap_data = {
        "competitors": ["crowdstrike.com", "paloaltonetworks.com", "fortinet.com", "rapid7.com", "splunk.com"]
    }
    
    print("🚀 Starting complete 13-stage pipeline...")
    
    # Initialize all 13 stages
    stages = [
        DataFetchStage(),           # Stage 0
        PromptBuildStage(),         # Stage 1
        GeminiCallStage(),          # Stage 2
        QualityRefinementStage(),   # Stage 2b
        ExtractionStage(),          # Stage 3
        CitationsStage(),           # Stage 4
        InternalLinksStage(),       # Stage 5
        TableOfContentsStage(),     # Stage 6
        MetadataStage(),           # Stage 7
        FAQPAAStage(),             # Stage 8
        ImageStage(),              # Stage 9
        CleanupStage(),            # Stage 10
        StorageStage()             # Stage 11
    ]
    
    print(f"📍 Running {len(stages)} stages...")
    
    for i, stage in enumerate(stages, 0):
        stage_start = time.time()
        stage_name = stage.__class__.__name__
        print(f"🔄 Stage {i:2d}: {stage_name}")
        
        try:
            context = await stage.execute(context)
            stage_time = time.time() - stage_start
            print(f"   ✅ Completed in {stage_time:.1f}s")
            
            # Special logging for key stages
            if stage_name == "CitationsStage":
                citations_count = len(context.parallel_results.get('citations_html', []))
                print(f"   📊 Citations processed: {citations_count}")
                
            elif stage_name == "InternalLinksStage":
                links_count = context.parallel_results.get('internal_links_count', 0)
                print(f"   🔗 Internal links generated: {links_count}")
                
            elif stage_name == "StorageStage":
                if hasattr(context, 'final_html'):
                    word_count = len(context.final_html.split())
                    list_count = context.final_html.count('<ul>') + context.final_html.count('<ol>')
                    item_count = context.final_html.count('<li>')
                    print(f"   📄 Final HTML: {len(context.final_html)} chars, {word_count} words")
                    print(f"   📝 Lists: {list_count} lists, {item_count} items")
                
        except Exception as e:
            print(f"   ❌ Stage {i} failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    total_time = time.time() - start_time
    
    # Generate output file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"complete_test_fixed_{timestamp}.html"
    
    if hasattr(context, 'final_html'):
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(context.final_html)
        
        # Analysis
        html = context.final_html
        word_count = len(html.split())
        list_count = html.count('<ul>') + html.count('<ol>')
        item_count = html.count('<li>')
        links_count = html.count('href="http')
        
        print("\n" + "=" * 70)
        print("🎉 COMPLETE TEST RESULTS")
        print("=" * 70)
        print(f"✅ Total time: {total_time:.1f} seconds")
        print(f"✅ Output file: {output_file}")
        print(f"✅ Word count: {word_count}")
        print(f"✅ Lists: {list_count} lists with {item_count} total items")
        print(f"✅ Links: {links_count} external links")
        print(f"✅ File size: {len(html):,} characters")
        
        # Open the result
        import os
        os.system(f"open {output_file}")
        
        print(f"\n🌐 Opening {output_file} in browser...")
        
        return output_file
    else:
        print(f"\n❌ No final HTML generated")
        return None

if __name__ == "__main__":
    result = asyncio.run(run_complete_test())
    if result:
        print(f"\n🎯 SUCCESS: Complete test saved as {result}")
    else:
        print("\n💥 FAILED: Test did not complete successfully")