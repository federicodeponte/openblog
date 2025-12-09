#!/usr/bin/env python3
"""
Test internal links generation with batch siblings
"""
import sys
import os
import asyncio
import time

# Set API key
os.environ['GEMINI_API_KEY'] = 'YOUR_GEMINI_API_KEY_HERE'

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pipeline.core.execution_context import ExecutionContext
from pipeline.blog_generation.stage_05_internal_links import InternalLinksStage
from pipeline.models.output_schema import ArticleOutput

async def test_internal_links():
    """Test just the internal links stage with batch siblings."""
    
    print("🔗 TESTING INTERNAL LINKS STAGE")
    print("="*50)
    
    # Create execution context
    context = ExecutionContext(job_id="test-internal-links")
    
    # Set batch siblings (same as in batch test)
    batch_siblings = [
        {"title": "SIEM Automation Guide", "url": "/magazine/siem-guide", "description": "Comprehensive guide to SIEM automation and orchestration"},
        {"title": "Cloud Compliance Guide", "url": "/magazine/cloud-guide", "description": "Comprehensive guide to cloud security compliance frameworks"},
        {"title": "Threat Intelligence Guide", "url": "/magazine/threat-guide", "description": "Comprehensive guide to threat intelligence automation platforms"},
        {"title": "DevSecOps Guide", "url": "/magazine/devsecops-guide", "description": "Comprehensive guide to DevSecOps security integration tools"}
    ]
    
    # Set job config with batch siblings
    context.job_config = {
        "primary_keyword": "zero trust security architecture",
        "batch_siblings": batch_siblings
    }
    
    # Create a simple mock article object for testing
    class MockArticle:
        def __init__(self):
            self.Headline = "Implementing Zero Trust Security Architecture: A 2025 Guide"
            self.section_01_title = "Core Principles of Zero Trust"
            self.section_02_title = "Identity as the New Perimeter"
            self.section_03_title = "Network Micro-segmentation"
            self.section_04_title = "Continuous Monitoring"
            # Add empty sections to avoid AttributeError
            for i in range(5, 10):
                setattr(self, f"section_{i:02d}_title", "")
    
    context.structured_data = MockArticle()
    
    # Initialize internal links stage
    stage = InternalLinksStage()
    
    print(f"Batch siblings configured: {len(batch_siblings)}")
    for i, sibling in enumerate(batch_siblings, 1):
        print(f"  {i}. {sibling['title']} → {sibling['url']}")
    
    print("\nExecuting internal links stage...")
    
    # Execute the stage
    start_time = time.time()
    context = await stage.execute(context)
    execution_time = time.time() - start_time
    
    # Check results
    internal_links_html = context.parallel_results.get("internal_links_html", "")
    internal_links_count = context.parallel_results.get("internal_links_count", 0)
    
    print(f"\n✅ RESULTS:")
    print(f"   Execution time: {execution_time:.2f}s")
    print(f"   Links generated: {internal_links_count}")
    print(f"   HTML size: {len(internal_links_html)} characters")
    
    if internal_links_html:
        print(f"\nGenerated HTML:")
        print("-" * 30)
        print(internal_links_html)
        print("-" * 30)
    else:
        print("\n❌ No internal links HTML generated")
    
    return internal_links_count > 0

if __name__ == "__main__":
    success = asyncio.run(test_internal_links())
    if success:
        print("\n🎉 Internal links test PASSED!")
    else:
        print("\n❌ Internal links test FAILED!")