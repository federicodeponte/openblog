#!/usr/bin/env python3
"""
Test single blog generation to verify regex fixes
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

# Import all stages
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

async def test_single_blog():
    """Test single blog generation with regex fixes."""
    
    # Create execution context
    context = ExecutionContext(job_id="test-regex-fix")
    
    # Set job config
    context.job_config = {
        "primary_keyword": "zero trust security architecture",
        "language": "en",
        "content_generation_instruction": "Write a comprehensive guide about implementing zero trust security architecture",
        "company_url": "https://cyberguard.tech",
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
    
    print("🚀 Starting single blog test...")
    start_time = time.time()
    
    # Initialize and run all stages
    stages = [
        DataFetchStage(),
        PromptBuildStage(),
        GeminiCallStage(),
        QualityRefinementStage(),
        ExtractionStage(),
        CitationsStage(),
        InternalLinksStage(),
        TableOfContentsStage(),
        MetadataStage(),
        FAQPAAStage(),
        ImageStage(),
        CleanupStage(),
        StorageStage()
    ]
    
    for i, stage in enumerate(stages, 1):
        print(f"📍 Stage {i:2d}: {stage.__class__.__name__}")
        try:
            context = await stage.execute(context)
            print(f"   ✅ Stage {i} completed")
        except Exception as e:
            print(f"   ❌ Stage {i} failed: {e}")
            raise
    
    total_time = time.time() - start_time
    
    # Generate output file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"test_regex_fix_{timestamp}.html"
    
    if hasattr(context, 'final_html'):
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(context.final_html)
        
        print(f"🎉 Test completed!")
        print(f"⏱️ Total time: {total_time:.1f}s")
        print(f"📄 Output: {output_file}")
        print(f"📊 Size: {len(context.final_html)} characters")
        
        # Open the result
        os.system(f"open {output_file}")
        
        return output_file
    else:
        print(f"❌ No final HTML generated")
        return None

if __name__ == "__main__":
    result = asyncio.run(test_single_blog())
    if result:
        print(f"✅ Test blog saved as: {result}")
    else:
        print("❌ Test failed")