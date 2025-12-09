#!/usr/bin/env python3
"""
Run ACTUAL Isaac Security V4.0 Full Pipeline
All 12 stages with smart citation validation
"""
import sys
import os
import json
import time
from datetime import datetime

# Set API key for Isaac Security
os.environ['GEMINI_API_KEY'] = 'YOUR_GEMINI_API_KEY_HERE'

async def run_full_isaac_pipeline():
    """Run FULL Isaac Security pipeline with all stages."""
    
    print("🛡️ ISAAC SECURITY V4.0 - FULL PIPELINE TEST")
    print("=" * 50)
    print("🔄 Running ALL 12 stages with smart citation validation")
    print("⏱️ Expected time: 5-8 minutes for complete generation")
    print()
    
    start_time = time.time()
    
    try:
        # Import Isaac Security components
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
        
        print("✅ All Isaac Security modules imported successfully")
        
        # Create execution context
        context = ExecutionContext(
            job_id="full-pipeline-test-001"
        )
        
        # Set job config
        context.job_config = {
            "primary_keyword": "enterprise cybersecurity automation",
            "language": "en",
            "content_generation_instruction": "Write a comprehensive guide about AI-powered cybersecurity automation for enterprise security teams",
            "company_url": "https://securenext.tech",
            "batch_siblings": [
                {"title": "Zero Trust Architecture Implementation Guide", "url": "/magazine/zero-trust-implementation", "description": "Complete guide to implementing zero trust security frameworks"},
                {"title": "SIEM Automation Best Practices", "url": "/magazine/siem-automation-guide", "description": "Advanced SIEM automation strategies for enterprise security"},
                {"title": "Cloud Security Compliance Framework", "url": "/magazine/cloud-security-compliance", "description": "Comprehensive cloud security compliance and governance"},
                {"title": "Threat Detection AI Integration", "url": "/magazine/ai-threat-detection", "description": "AI-powered threat detection and incident response"}
            ]
        }
        
        # Set company data
        context.company_data = {
            "company_name": "SecureNext Technologies",
            "company_url": "https://securenext.tech",
            "company_info": {
                "industry": "Cybersecurity Solutions", 
                "target_audience": "Enterprise IT security teams",
                "description": "Leading provider of AI-powered cybersecurity automation platforms"
            }
        }
        
        # Set blog page data
        context.blog_page = {
            "primary_keyword": "enterprise cybersecurity automation",
            "competitors": ["crowdstrike.com", "paloaltonetworks.com", "fortinet.com"],
            "internal_pages": [
                "/solutions/threat-detection",
                "/products/ai-siem", 
                "/resources/security-automation",
                "/company/about-us",
                "/blog/security-trends"
            ]
        }
        
        # Add sitemap_data for citation validation
        context.sitemap_data = {
            "competitors": ["crowdstrike.com", "paloaltonetworks.com", "fortinet.com"]
        }
        
        print("✅ Execution context initialized")
        
        # Initialize and run all stages
        stages = [
            DataFetchStage(),
            PromptBuildStage(),
            GeminiCallStage(),
            QualityRefinementStage(),
            ExtractionStage(),
            CitationsStage(),  # 🔍 This should run smart citation validation
            InternalLinksStage(),
            TableOfContentsStage(),
            MetadataStage(),
            FAQPAAStage(),
            ImageStage(),
            CleanupStage(),
            StorageStage()
        ]
        
        print(f"\n🔄 Running {len(stages)} stages sequentially...")
        print("📝 Stage details:")
        
        for i, stage in enumerate(stages, 1):
            stage_start = time.time()
            print(f"   {i:2d}. {stage.__class__.__name__:<20}")
            
            try:
                context = await stage.execute(context)
                stage_time = time.time() - stage_start
                print(f"       ✅ Completed in {stage_time:.1f}s")
                
                # Log key results
                if stage.stage_num == 2:  # Gemini call
                    word_count = len(context.raw_content.split()) if hasattr(context, 'raw_content') else 0
                    print(f"       📊 Generated {word_count} words")
                elif stage.stage_num == 4:  # Citations  
                    citation_count = len(context.parallel_results.get('citations_html', [])) if hasattr(context, 'parallel_results') else 0
                    print(f"       🔗 Processed {citation_count} citations")
                elif stage.stage_num == 11:  # Storage
                    if hasattr(context, 'final_html'):
                        print(f"       📄 Final HTML ready: {len(context.final_html)} chars")
                
            except Exception as e:
                print(f"       ❌ Failed: {e}")
                raise
        
        total_time = time.time() - start_time
        
        print(f"\n🎉 FULL PIPELINE COMPLETED!")
        print(f"⏱️ Total time: {total_time:.1f} seconds")
        
        # Save results 
        if hasattr(context, 'final_html'):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"isaac_security_FULL_PIPELINE_{timestamp}.html"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(context.final_html)
            
            print(f"📁 Saved to: {output_file}")
            
            # Count citations and references
            citation_count = context.final_html.count('<a href=')
            ref_section = 'references' in context.final_html.lower() or 'sources' in context.final_html.lower()
            
            print(f"🔍 Analysis:")
            print(f"   📊 Word count: {len(context.final_html.split())} words")
            print(f"   🔗 Citation links: {citation_count}")
            print(f"   📚 References section: {'✅ Yes' if ref_section else '❌ No'}")
            
            # Open in browser
            os.system(f"open {output_file}")
            
            return output_file
        else:
            print("❌ No final HTML generated")
            return None
            
    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_full_isaac_pipeline())