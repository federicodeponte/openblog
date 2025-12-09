#!/usr/bin/env python3
"""
ISAAC SECURITY V4.0 - 5-BLOG PARALLEL BATCH TEST
Complete pipeline test with deep logging and citation validation audit
"""
import sys
import os
import json
import asyncio
import time
from datetime import datetime
from pathlib import Path

# Set API key for Isaac Security
os.environ['GEMINI_API_KEY'] = 'YOUR_GEMINI_API_KEY_HERE'

# Configure deep logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('batch_test_5_deep_audit.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Test configurations for 5 diverse cybersecurity blogs
BATCH_CONFIGS = [
    {
        "job_id": "batch-test-001-zero-trust",
        "primary_keyword": "zero trust security architecture",
        "company_name": "CyberGuard Solutions", 
        "company_url": "https://cyberguard.tech",
        "industry": "Enterprise Security",
        "content_instruction": "Write a comprehensive guide about implementing zero trust security architecture for enterprise networks"
    },
    {
        "job_id": "batch-test-002-siem-automation", 
        "primary_keyword": "SIEM automation and orchestration",
        "company_name": "SecureOps Technologies",
        "company_url": "https://secureops.io", 
        "industry": "Security Operations",
        "content_instruction": "Create an in-depth analysis of SIEM automation tools and orchestration platforms for SOC teams"
    },
    {
        "job_id": "batch-test-003-cloud-compliance",
        "primary_keyword": "cloud security compliance frameworks", 
        "company_name": "CloudSec Advisors",
        "company_url": "https://cloudsec.expert",
        "industry": "Cloud Security",
        "content_instruction": "Develop a detailed guide on cloud security compliance frameworks and governance strategies"
    },
    {
        "job_id": "batch-test-004-threat-intelligence",
        "primary_keyword": "threat intelligence automation platforms",
        "company_name": "ThreatScope Analytics", 
        "company_url": "https://threatscope.ai",
        "industry": "Threat Intelligence",
        "content_instruction": "Write an expert guide on threat intelligence automation platforms and AI-driven threat analysis"
    },
    {
        "job_id": "batch-test-005-devsecops",
        "primary_keyword": "DevSecOps security integration tools",
        "company_name": "SecureDev Solutions",
        "company_url": "https://securedev.cloud", 
        "industry": "DevSecOps",
        "content_instruction": "Create a comprehensive overview of DevSecOps security integration tools and pipeline automation"
    }
]

async def run_single_blog(config: dict, batch_index: int) -> dict:
    """Run a single blog generation with full pipeline and deep logging."""
    
    logger.info(f"🚀 Starting Blog {batch_index + 1}/5: {config['job_id']}")
    logger.info(f"   Primary Keyword: {config['primary_keyword']}")
    logger.info(f"   Company: {config['company_name']}")
    logger.info(f"   URL: {config['company_url']}")
    
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
        
        # Create execution context
        context = ExecutionContext(job_id=config["job_id"])
        
        # Set job config
        context.job_config = {
            "primary_keyword": config["primary_keyword"],
            "language": "en",
            "content_generation_instruction": config["content_instruction"],
            "company_url": config["company_url"],
            "batch_siblings": [
                {"title": other["primary_keyword"].title() + " Guide", 
                 "url": f"/magazine/{other['job_id'].split('-')[-1]}-guide", 
                 "description": f"Comprehensive guide to {other['primary_keyword']}"}
                for other in BATCH_CONFIGS if other["job_id"] != config["job_id"]
            ][:4]  # Max 4 siblings
        }
        
        # Set company data
        context.company_data = {
            "company_name": config["company_name"],
            "company_url": config["company_url"],
            "company_info": {
                "industry": config["industry"], 
                "target_audience": "Enterprise security teams",
                "description": f"Leading provider of {config['industry'].lower()} solutions"
            }
        }
        
        # Add sitemap_data for citation validation
        context.sitemap_data = {
            "competitors": ["crowdstrike.com", "paloaltonetworks.com", "fortinet.com", "rapid7.com", "splunk.com"]
        }
        
        logger.info(f"✅ Blog {batch_index + 1}: Execution context initialized")
        
        # Initialize and run all stages
        stages = [
            DataFetchStage(),
            PromptBuildStage(),
            GeminiCallStage(),
            QualityRefinementStage(),
            ExtractionStage(),
            CitationsStage(),  # 🔍 Citation validation with Gemini
            InternalLinksStage(),
            TableOfContentsStage(),
            MetadataStage(),
            FAQPAAStage(),
            ImageStage(),
            CleanupStage(),
            StorageStage()
        ]
        
        logger.info(f"🔄 Blog {batch_index + 1}: Running {len(stages)} stages...")
        
        citation_metrics = {}
        
        for i, stage in enumerate(stages, 1):
            stage_start = time.time()
            logger.info(f"📍 Blog {batch_index + 1} - Stage {i:2d}: {stage.__class__.__name__}")
            
            try:
                context = await stage.execute(context)
                stage_time = time.time() - stage_start
                logger.info(f"   ✅ Blog {batch_index + 1} - Stage {i} completed in {stage_time:.1f}s")
                
                # Deep logging for citation stage
                if stage.__class__.__name__ == "CitationsStage":
                    citations_html = context.parallel_results.get('citations_html', '')
                    citation_count = len(context.parallel_results.get('citations_html', []))
                    logger.info(f"   📊 Blog {batch_index + 1} - Citations: {citation_count} processed")
                    
                    # Extract citation metrics for audit
                    if hasattr(context, 'citation_validation_results'):
                        validation_results = context.citation_validation_results
                        total_citations = len(validation_results)
                        valid_citations = sum(1 for r in validation_results if r.is_valid)
                        citation_metrics = {
                            "total_citations": total_citations,
                            "valid_citations": valid_citations,
                            "invalid_citations": total_citations - valid_citations,
                            "success_rate": (valid_citations / total_citations * 100) if total_citations > 0 else 0,
                            "gemini_calls": sum(1 for r in validation_results if "alternative" in r.validation_type.lower())
                        }
                        logger.info(f"   🔍 Blog {batch_index + 1} - Citation Validation:")
                        logger.info(f"       Total: {total_citations}")
                        logger.info(f"       Valid: {valid_citations}")
                        logger.info(f"       Success Rate: {citation_metrics['success_rate']:.1f}%")
                        logger.info(f"       Gemini Searches: {citation_metrics['gemini_calls']}")
                
            except Exception as e:
                logger.error(f"   ❌ Blog {batch_index + 1} - Stage {i} failed: {e}")
                raise
        
        total_time = time.time() - start_time
        
        # Generate output file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"batch_test_{batch_index + 1}_{config['job_id']}_{timestamp}.html"
        
        result_metrics = {
            "job_id": config["job_id"],
            "batch_index": batch_index + 1,
            "primary_keyword": config["primary_keyword"],
            "company_name": config["company_name"],
            "total_time": total_time,
            "output_file": output_file,
            "success": True,
            "citation_metrics": citation_metrics
        }
        
        if hasattr(context, 'final_html'):
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(context.final_html)
            
            # Count external links for audit
            external_links = context.final_html.count('href="http')
            word_count = len(context.final_html.split())
            
            result_metrics.update({
                "word_count": word_count,
                "external_links": external_links,
                "file_size": len(context.final_html)
            })
            
            logger.info(f"🎉 Blog {batch_index + 1} COMPLETED!")
            logger.info(f"   ⏱️ Total time: {total_time:.1f}s")
            logger.info(f"   📄 Output: {output_file}")
            logger.info(f"   📊 Word count: {word_count}")
            logger.info(f"   🔗 External links: {external_links}")
            
        else:
            logger.error(f"❌ Blog {batch_index + 1}: No final HTML generated")
            result_metrics["success"] = False
            
        return result_metrics
        
    except Exception as e:
        logger.error(f"❌ Blog {batch_index + 1} failed: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "job_id": config["job_id"],
            "batch_index": batch_index + 1,
            "success": False,
            "error": str(e),
            "total_time": time.time() - start_time
        }

async def run_batch_test():
    """Run 5 blogs in parallel with comprehensive logging and auditing."""
    
    logger.info("🛡️ ISAAC SECURITY V4.0 - 5-BLOG PARALLEL BATCH TEST")
    logger.info("=" * 70)
    logger.info("🔄 Testing complete pipeline with Gemini citation validation")
    logger.info("📝 Deep logging enabled for comprehensive audit")
    logger.info("")
    
    batch_start = time.time()
    
    # Run all 5 blogs in parallel
    logger.info("🚀 Starting 5 blogs in parallel...")
    
    tasks = [
        run_single_blog(config, i)
        for i, config in enumerate(BATCH_CONFIGS)
    ]
    
    # Wait for all blogs to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    batch_time = time.time() - batch_start
    
    # Aggregate results and create audit report
    logger.info("\n" + "=" * 70)
    logger.info("📊 BATCH TEST RESULTS SUMMARY")
    logger.info("=" * 70)
    
    successful_blogs = []
    failed_blogs = []
    total_citations = 0
    total_valid_citations = 0
    total_gemini_calls = 0
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Blog {i + 1}: Exception occurred - {result}")
            failed_blogs.append({"batch_index": i + 1, "error": str(result)})
            continue
            
        if result.get("success"):
            successful_blogs.append(result)
            if "citation_metrics" in result:
                cm = result["citation_metrics"]
                total_citations += cm.get("total_citations", 0)
                total_valid_citations += cm.get("valid_citations", 0)
                total_gemini_calls += cm.get("gemini_calls", 0)
        else:
            failed_blogs.append(result)
    
    # Final audit summary
    success_rate = (len(successful_blogs) / len(BATCH_CONFIGS)) * 100
    citation_success_rate = (total_valid_citations / total_citations * 100) if total_citations > 0 else 0
    
    logger.info(f"✅ Successful blogs: {len(successful_blogs)}/{len(BATCH_CONFIGS)} ({success_rate:.1f}%)")
    logger.info(f"❌ Failed blogs: {len(failed_blogs)}")
    logger.info(f"⏱️ Total batch time: {batch_time:.1f} seconds")
    logger.info(f"⏱️ Average time per blog: {batch_time / len(BATCH_CONFIGS):.1f} seconds")
    logger.info("")
    logger.info("🔍 CITATION VALIDATION AUDIT:")
    logger.info(f"   📊 Total citations processed: {total_citations}")
    logger.info(f"   ✅ Valid citations: {total_valid_citations}")
    logger.info(f"   📈 Citation success rate: {citation_success_rate:.1f}%")
    logger.info(f"   🧠 Gemini searches performed: {total_gemini_calls}")
    
    # Save detailed audit report
    audit_report = {
        "test_timestamp": datetime.now().isoformat(),
        "batch_metrics": {
            "total_blogs": len(BATCH_CONFIGS),
            "successful_blogs": len(successful_blogs),
            "failed_blogs": len(failed_blogs),
            "success_rate": success_rate,
            "total_batch_time": batch_time,
            "average_time_per_blog": batch_time / len(BATCH_CONFIGS)
        },
        "citation_metrics": {
            "total_citations": total_citations,
            "valid_citations": total_valid_citations,
            "invalid_citations": total_citations - total_valid_citations,
            "citation_success_rate": citation_success_rate,
            "gemini_searches": total_gemini_calls
        },
        "successful_results": successful_blogs,
        "failed_results": failed_blogs
    }
    
    audit_filename = f"batch_test_5_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(audit_filename, 'w', encoding='utf-8') as f:
        json.dump(audit_report, f, indent=2, ensure_ascii=False)
    
    logger.info(f"📋 Detailed audit report saved: {audit_filename}")
    logger.info(f"📋 Deep logs saved: batch_test_5_deep_audit.log")
    
    # Open first successful blog if any
    if successful_blogs:
        first_blog = successful_blogs[0]["output_file"]
        logger.info(f"🌐 Opening first blog: {first_blog}")
        os.system(f"open {first_blog}")
    
    return audit_report

if __name__ == "__main__":
    asyncio.run(run_batch_test())