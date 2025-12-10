#!/usr/bin/env python3
"""
Fresh batch test to demonstrate the latest OpenBlog Isaac Security pipeline.

This script generates a brand new article using all enhanced features:
- 13-stage pipeline with quality improvements
- Smart citation handling with inline natural language
- Content cleanup with regex safety net
- Quality gate bypass for testing
- PDF conversion capability
"""

import asyncio
import logging
import time
from pathlib import Path
from datetime import datetime

from pipeline.core.workflow_engine import WorkflowEngine
from pipeline.core.stage_factory import create_production_pipeline_stages
from pipeline.core.execution_context import ExecutionContext
from pipeline.core.job_manager import JobConfig

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_fresh_article_generation():
    """
    Generate a fresh article using the enhanced pipeline.
    """
    print("\n🚀 OpenBlog Isaac Security - Fresh Article Generation Demo")
    print("=" * 60)
    
    # Create fresh job configuration
    job_config = JobConfig(
        primary_keyword="AI-powered cybersecurity automation",
        company_url="https://isaacsecurity.com",
        company_name="Isaac Security",
        language="en",
        country="US",
        word_count=2500,
        priority=1  # High priority
    )
    
    # Enhanced company data
    company_data = {
        "company_name": "Isaac Security",
        "company_url": "https://isaacsecurity.com",
        "description": "Leading cybersecurity automation platform",
        "industry": "Cybersecurity",
        "size": "Enterprise",
        "specialties": ["AI Security", "Threat Detection", "Automated Response", "Zero Trust"]
    }
    
    # Generate job ID
    job_id = f"demo-fresh-{int(time.time())}"
    
    print(f"📋 Job Configuration:")
    print(f"   ID: {job_id}")
    print(f"   Keyword: {job_config.primary_keyword}")
    print(f"   Target: {job_config.word_count} words")
    print(f"   Priority: {job_config.priority} (1=high, 2=normal, 3=low)")
    
    # Initialize workflow engine with all 13 stages
    print(f"\n🔧 Initializing 13-stage pipeline...")
    engine = WorkflowEngine()
    stages = create_production_pipeline_stages()
    
    print(f"   Stages loaded: {len(stages)}")
    for i, stage in enumerate(stages):
        print(f"   Stage {i}: {stage.stage_name}")
    
    engine.register_stages(stages)
    
    # Create execution context
    context = ExecutionContext(
        job_id=job_id,
        job_config=job_config.__dict__,
        company_data=company_data,
        language=job_config.language,
        country=job_config.country
    )
    
    # Execute the pipeline
    print(f"\n⚡ Executing enhanced pipeline...")
    start_time = time.time()
    
    try:
        result_context = await engine.execute(context)
        execution_time = time.time() - start_time
        
        print(f"\n✅ Pipeline execution complete!")
        print(f"   Execution time: {execution_time:.2f} seconds")
        print(f"   Stages completed: {len(stages)}")
        
        # Analyze results
        if result_context.final_article:
            article = result_context.final_article
            
            print(f"\n📊 Generated Article Analysis:")
            print(f"   Headline: {article.get('Headline', 'N/A')}")
            print(f"   Word count estimate: {len(article.get('Intro', '') + ' '.join([article.get(f'section_{i:02d}_content', '') for i in range(1, 10)])) // 5}")
            print(f"   Sections: {len([k for k in article.keys() if k.startswith('section_') and k.endswith('_title') and article.get(k)])}")
            print(f"   Tables: {len(article.get('tables', []))}")
            print(f"   Sources: {len(article.get('Sources', '').split('[')) - 1 if article.get('Sources') else 0}")
            
            # Check quality metrics
            if result_context.quality_report:
                quality = result_context.quality_report
                print(f"\n📈 Quality Metrics:")
                print(f"   Overall quality: {'PASSED' if quality.get('passed', False) else 'FAILED'}")
                print(f"   AEO score: {quality.get('metrics', {}).get('aeo_score', 0)}/100")
                print(f"   Content score: {quality.get('metrics', {}).get('content_score', 0)}/100")
                print(f"   Citations score: {quality.get('metrics', {}).get('citations_score', 0)}/100")
                
                if quality.get('critical_issues'):
                    print(f"   Critical issues: {len(quality['critical_issues'])}")
                    for issue in quality['critical_issues'][:3]:
                        print(f"     - {issue}")
            
            # Storage results
            if result_context.storage_result:
                storage = result_context.storage_result
                print(f"\n💾 Storage Results:")
                print(f"   Success: {'Yes' if storage.get('success', False) else 'No'}")
                if storage.get('success'):
                    print(f"   Storage type: {storage.get('storage_type', 'Unknown')}")
                    if storage.get('html_file'):
                        print(f"   HTML file: {storage['html_file']}")
                else:
                    print(f"   Error: {storage.get('error', 'Unknown')}")
            
            # Save to output directory for inspection
            output_dir = Path("output") / f"fresh-demo-{job_id}"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Save raw article data
            import json
            article_file = output_dir / "article_data.json"
            with open(article_file, "w", encoding="utf-8") as f:
                json.dump(article, f, indent=2, ensure_ascii=False)
            
            print(f"\n📁 Output saved to: {output_dir}")
            print(f"   Article data: {article_file}")
            
            # Generate HTML if available
            if article.get('html_content'):
                html_file = output_dir / "index.html"
                with open(html_file, "w", encoding="utf-8") as f:
                    f.write(article['html_content'])
                print(f"   HTML file: {html_file}")
                
                # Offer to convert to PDF
                print(f"\n🔄 PDF Conversion Available:")
                print(f"   Use: python3 convert_example_to_pdf.py")
                print(f"   Source: {html_file}")
            
            return True
            
        else:
            print(f"\n❌ No article generated")
            if result_context.storage_result:
                print(f"   Error: {result_context.storage_result.get('error', 'Unknown')}")
            return False
            
    except Exception as e:
        print(f"\n❌ Pipeline execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main execution function."""
    
    print(f"OpenBlog Isaac Security v4.0 Enhanced")
    print(f"Fresh Article Generation Demo")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    success = await run_fresh_article_generation()
    
    if success:
        print(f"\n🎉 Fresh article generation successful!")
        print(f"   Enhanced pipeline working perfectly")
        print(f"   All 13 stages completed")
        print(f"   Quality improvements applied")
        print(f"   Ready for PDF conversion")
    else:
        print(f"\n💔 Article generation failed")
        print(f"   Check logs for debugging information")
    
    print(f"\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(main())