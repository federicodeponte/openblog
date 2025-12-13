#!/usr/bin/env python3
"""
Full Pipeline Deep Inspection Test

Tests both single and batch generation with comprehensive output analysis:
- All 13 stages execution
- Content quality validation
- HTML structure analysis
- Citation validation
- Image generation
- Internal links
- Quality metrics
"""

import os
import sys
import asyncio
import time
import re
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, List

# Load environment
env_file = Path(__file__).parent / ".env.local"
if env_file.exists():
    load_dotenv(env_file)
    if "GOOGLE_GEMINI_API_KEY" in os.environ and "GEMINI_API_KEY" not in os.environ:
        os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_GEMINI_API_KEY"]
else:
    load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from pipeline.core.workflow_engine import WorkflowEngine
from pipeline.core.stage_factory import create_production_pipeline_stages
from pipeline.core.execution_context import ExecutionContext


class DeepInspector:
    """Deep inspection of generated content"""
    
    def inspect_html(self, html: str, context: ExecutionContext) -> Dict[str, Any]:
        """Deep inspection of HTML output"""
        inspection = {
            "structure": {},
            "content_quality": {},
            "citations": {},
            "links": {},
            "images": {},
            "issues": [],
            "metrics": {}
        }
        
        # Structure analysis
        h1_count = len(re.findall(r'<h1[^>]*>', html))
        h2_count = len(re.findall(r'<h2[^>]*>', html))
        h3_count = len(re.findall(r'<h3[^>]*>', html))
        p_count = len(re.findall(r'<p[^>]*>', html))
        ul_count = len(re.findall(r'<ul[^>]*>', html))
        
        inspection["structure"] = {
            "h1_count": h1_count,
            "h2_count": h2_count,
            "h3_count": h3_count,
            "paragraph_count": p_count,
            "list_count": ul_count,
            "has_proper_structure": h1_count == 1 and h2_count >= 3
        }
        
        # Content quality checks
        em_dash_count = html.count('—') + html.count('–')
        academic_citations = len(re.findall(r'\[\d+\]', html))
        bold_tags = len(re.findall(r'<(?:strong|b)>', html))
        word_count = len(re.sub(r'<[^>]+>', '', html).split())
        
        inspection["content_quality"] = {
            "em_dash_count": em_dash_count,
            "no_em_dashes": em_dash_count == 0,
            "academic_citation_count": academic_citations,
            "no_academic_citations": academic_citations == 0,
            "bold_tags_count": bold_tags,
            "word_count": word_count,
            "has_sufficient_content": word_count >= 1000
        }
        
        if em_dash_count > 0:
            inspection["issues"].append(f"Found {em_dash_count} em/en dashes")
        if academic_citations > 0:
            inspection["issues"].append(f"Found {academic_citations} academic citations [N]")
        
        # Citation analysis
        external_links = re.findall(r'href="(https?://[^"]+)"', html)
        full_urls = [url for url in external_links if len(url.split('/')) > 3]
        domain_only = [url for url in external_links if len(url.split('/')) <= 3]
        
        inspection["citations"] = {
            "total_external_links": len(external_links),
            "full_urls": len(full_urls),
            "domain_only_urls": len(domain_only),
            "full_url_percentage": (len(full_urls) / len(external_links) * 100) if external_links else 0,
            "has_full_urls": len(full_urls) > len(domain_only)
        }
        
        if len(domain_only) > len(full_urls):
            inspection["issues"].append(f"Too many domain-only URLs ({len(domain_only)} vs {len(full_urls)} full URLs)")
        
        # Internal links
        internal_links = re.findall(r'href="(/[^"]*|#[^"]*)"', html)
        inspection["links"] = {
            "internal_links_count": len(internal_links),
            "has_internal_links": len(internal_links) > 0
        }
        
        if len(internal_links) == 0:
            inspection["issues"].append("No internal links found")
        
        # Images
        img_tags = re.findall(r'<img[^>]+src="([^"]+)"', html)
        inspection["images"] = {
            "image_count": len(img_tags),
            "has_images": len(img_tags) > 0,
            "image_sources": img_tags[:3] if img_tags else []
        }
        
        if len(img_tags) == 0:
            inspection["issues"].append("No images found")
        
        # Quality metrics from context
        if hasattr(context, 'quality_report') and context.quality_report:
            qr = context.quality_report
            inspection["metrics"] = {
                "aeo_score": qr.get('metrics', {}).get('aeo_score', 0),
                "critical_issues": len(qr.get('critical_issues', [])),
                "warnings": len(qr.get('warnings', [])),
                "passed": qr.get('passed', False)
            }
        else:
            inspection["metrics"] = {
                "aeo_score": None,
                "critical_issues": None,
                "warnings": None,
                "passed": None
            }
        
        return inspection
    
    def inspect_stages(self, context: ExecutionContext) -> Dict[str, Any]:
        """Inspect stage execution"""
        stage_info = {
            "stages_executed": [],
            "execution_times": {},
            "errors": {},
            "stage_count": 0
        }
        
        # Get execution times
        if hasattr(context, 'execution_times'):
            stage_info["execution_times"] = context.execution_times
            stage_info["stages_executed"] = list(context.execution_times.keys())
            stage_info["stage_count"] = len(context.execution_times)
        
        # Get errors
        if hasattr(context, 'errors'):
            stage_info["errors"] = {k: str(v) for k, v in context.errors.items()}
        
        return stage_info


async def test_single_article():
    """Test single article generation with deep inspection"""
    print("\n" + "="*70)
    print("SINGLE ARTICLE GENERATION TEST")
    print("="*70)
    
    inspector = DeepInspector()
    
    # Create workflow engine
    engine = WorkflowEngine()
    stages = create_production_pipeline_stages()
    engine.register_stages(stages)
    
    print(f"\n✅ Registered {len(stages)} stages")
    for stage in stages:
        print(f"   Stage {stage.stage_num:2d}: {stage.stage_name}")
    
    # Job config
    job_config = {
        "primary_keyword": "zero trust security architecture",
        "company_url": "https://cyberguard.tech",
        "language": "en",
        "country": "US",
        "company_data": {
            "company_name": "CyberGuard Solutions",
            "company_info": "Leading provider of enterprise security solutions"
        },
        "word_count": 2000
    }
    
    job_id = f"test-single-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    print(f"\n📝 Generating article:")
    print(f"   Keyword: {job_config['primary_keyword']}")
    print(f"   Company: {job_config['company_data']['company_name']}")
    print(f"   Target: {job_config['word_count']} words")
    
    start_time = time.time()
    
    try:
        # Execute pipeline
        context = await engine.execute(job_id=job_id, job_config=job_config)
        
        duration = time.time() - start_time
        
        print(f"\n✅ Pipeline completed in {duration:.2f}s")
        
        # Get HTML output
        html = ""
        if hasattr(context, 'final_html') and context.final_html:
            html = context.final_html
        elif hasattr(context, 'validated_article'):
            # Try to extract HTML from validated_article
            if isinstance(context.validated_article, dict):
                article_dict = context.validated_article
            elif hasattr(context.validated_article, 'model_dump'):
                article_dict = context.validated_article.model_dump()
            elif hasattr(context.validated_article, '__dict__'):
                article_dict = dict(context.validated_article.__dict__)
            else:
                article_dict = {}
            # Would need to render HTML from article_dict
        
        # Inspect stages
        stage_inspection = inspector.inspect_stages(context)
        print(f"\n📊 Stage Execution:")
        print(f"   Stages executed: {stage_inspection['stage_count']}")
        print(f"   Expected: 13 stages (0-12)")
        
        if stage_inspection['stage_count'] < 13:
            print(f"   ⚠️  Missing stages!")
        
        total_stage_time = sum(stage_inspection['execution_times'].values())
        print(f"   Total stage time: {total_stage_time:.2f}s")
        
        # Show stage times
        print(f"\n   Stage Execution Times:")
        for stage_name, stage_time in sorted(stage_inspection['execution_times'].items()):
            print(f"      {stage_name:20s}: {stage_time:6.2f}s")
        
        # Check for errors
        if stage_inspection['errors']:
            print(f"\n   ⚠️  Errors found:")
            for stage, error in stage_inspection['errors'].items():
                print(f"      {stage}: {error}")
        else:
            print(f"\n   ✅ No stage errors")
        
        # Inspect HTML if available
        if html:
            html_inspection = inspector.inspect_html(html, context)
            
            print(f"\n📄 HTML Content Inspection:")
            print(f"   Structure:")
            print(f"      H1: {html_inspection['structure']['h1_count']}")
            print(f"      H2: {html_inspection['structure']['h2_count']}")
            print(f"      Paragraphs: {html_inspection['structure']['paragraph_count']}")
            print(f"      Lists: {html_inspection['structure']['list_count']}")
            
            print(f"\n   Content Quality:")
            print(f"      Word count: {html_inspection['content_quality']['word_count']}")
            print(f"      Em dashes: {html_inspection['content_quality']['em_dash_count']} {'✅' if html_inspection['content_quality']['no_em_dashes'] else '❌'}")
            print(f"      Academic citations: {html_inspection['content_quality']['academic_citation_count']} {'✅' if html_inspection['content_quality']['no_academic_citations'] else '❌'}")
            print(f"      Bold tags: {html_inspection['content_quality']['bold_tags_count']}")
            
            print(f"\n   Citations:")
            print(f"      External links: {html_inspection['citations']['total_external_links']}")
            print(f"      Full URLs: {html_inspection['citations']['full_urls']} ({html_inspection['citations']['full_url_percentage']:.1f}%)")
            print(f"      Domain-only: {html_inspection['citations']['domain_only_urls']}")
            
            print(f"\n   Links & Images:")
            print(f"      Internal links: {html_inspection['links']['internal_links_count']}")
            print(f"      Images: {html_inspection['images']['image_count']}")
            
            print(f"\n   Quality Metrics:")
            if html_inspection['metrics']['aeo_score']:
                print(f"      AEO Score: {html_inspection['metrics']['aeo_score']}")
            print(f"      Critical issues: {html_inspection['metrics']['critical_issues']}")
            print(f"      Passed: {html_inspection['metrics']['passed']}")
            
            if html_inspection['issues']:
                print(f"\n   ⚠️  Issues Found:")
                for issue in html_inspection['issues']:
                    print(f"      - {issue}")
            else:
                print(f"\n   ✅ No issues found")
        
        return {
            "success": True,
            "duration": duration,
            "stage_inspection": stage_inspection,
            "html_inspection": html_inspection if html else None,
            "context": context
        }
        
    except Exception as e:
        duration = time.time() - start_time
        print(f"\n❌ Pipeline failed after {duration:.2f}s")
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "duration": duration,
            "error": str(e)
        }


async def test_batch_generation():
    """Test batch generation with deep inspection"""
    print("\n" + "="*70)
    print("BATCH GENERATION TEST")
    print("="*70)
    
    inspector = DeepInspector()
    
    # Create workflow engine
    engine = WorkflowEngine()
    stages = create_production_pipeline_stages()
    engine.register_stages(stages)
    
    # Small batch for testing
    batch_configs = [
        {
            "primary_keyword": "cloud security best practices",
            "company_url": "https://cloudsec.example.com",
            "language": "en",
            "country": "US",
            "company_data": {
                "company_name": "CloudSec Pro",
                "company_info": "Cloud security solutions provider"
            },
            "word_count": 1500
        },
        {
            "primary_keyword": "API security testing",
            "company_url": "https://apisec.example.com",
            "language": "en",
            "country": "US",
            "company_data": {
                "company_name": "APISec Labs",
                "company_info": "API security testing tools"
            },
            "word_count": 1500
        }
    ]
    
    print(f"\n📝 Generating batch of {len(batch_configs)} articles")
    
    batch_results = []
    start_time = time.time()
    
    for i, job_config in enumerate(batch_configs, 1):
        print(f"\n{'='*70}")
        print(f"ARTICLE {i}/{len(batch_configs)}: {job_config['primary_keyword']}")
        print(f"{'='*70}")
        
        job_id = f"test-batch-{i}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        article_start = time.time()
        
        try:
            context = await engine.execute(job_id=job_id, job_config=job_config)
            article_duration = time.time() - article_start
            
            # Inspect
            stage_inspection = inspector.inspect_stages(context)
            
            html = ""
            if hasattr(context, 'final_html') and context.final_html:
                html = context.final_html
            
            html_inspection = None
            if html:
                html_inspection = inspector.inspect_html(html, context)
            
            result = {
                "success": True,
                "keyword": job_config['primary_keyword'],
                "duration": article_duration,
                "stage_inspection": stage_inspection,
                "html_inspection": html_inspection
            }
            
            print(f"✅ Completed in {article_duration:.2f}s")
            print(f"   Stages: {stage_inspection['stage_count']}/13")
            if html_inspection:
                print(f"   Word count: {html_inspection['content_quality']['word_count']}")
                print(f"   Issues: {len(html_inspection['issues'])}")
            
            batch_results.append(result)
            
        except Exception as e:
            article_duration = time.time() - article_start
            print(f"❌ Failed after {article_duration:.2f}s: {e}")
            batch_results.append({
                "success": False,
                "keyword": job_config['primary_keyword'],
                "duration": article_duration,
                "error": str(e)
            })
    
    total_duration = time.time() - start_time
    
    # Batch summary
    print(f"\n{'='*70}")
    print("BATCH SUMMARY")
    print(f"{'='*70}")
    
    successful = sum(1 for r in batch_results if r.get('success'))
    failed = len(batch_results) - successful
    
    print(f"\n📊 Results:")
    print(f"   Total articles: {len(batch_results)}")
    print(f"   Successful: {successful}")
    print(f"   Failed: {failed}")
    print(f"   Total time: {total_duration:.2f}s")
    print(f"   Avg time per article: {total_duration/len(batch_configs):.2f}s")
    
    if successful > 0:
        # Analyze successful articles
        avg_word_count = sum(
            r['html_inspection']['content_quality']['word_count'] 
            for r in batch_results 
            if r.get('success') and r.get('html_inspection')
        ) / successful
        
        total_issues = sum(
            len(r['html_inspection']['issues'])
            for r in batch_results
            if r.get('success') and r.get('html_inspection')
        )
        
        print(f"\n   Average word count: {avg_word_count:.0f}")
        print(f"   Total issues: {total_issues}")
        
        # Stage execution analysis
        all_stages = set()
        for r in batch_results:
            if r.get('success') and r.get('stage_inspection'):
                all_stages.update(r['stage_inspection']['stages_executed'])
        
        print(f"\n   Stages executed across batch:")
        for stage in sorted(all_stages):
            count = sum(
                1 for r in batch_results
                if r.get('success') and stage in r.get('stage_inspection', {}).get('stages_executed', [])
            )
            print(f"      {stage:20s}: {count}/{len(batch_configs)} articles")
    
    return {
        "success": successful == len(batch_configs),
        "total_duration": total_duration,
        "results": batch_results
    }


async def main():
    """Run full pipeline tests"""
    print("="*70)
    print("FULL PIPELINE DEEP INSPECTION TEST")
    print("="*70)
    print(f"\nTimestamp: {datetime.now().isoformat()}")
    print("\nTesting:")
    print("  ✅ Single article generation")
    print("  ✅ Batch generation (2 articles)")
    print("  ✅ Deep output inspection")
    print("  ✅ Stage execution validation")
    print("  ✅ Content quality analysis")
    
    results = {}
    
    # Test single article
    single_result = await test_single_article()
    results["single"] = single_result
    
    # Test batch
    batch_result = await test_batch_generation()
    results["batch"] = batch_result
    
    # Final summary
    print("\n" + "="*70)
    print("FINAL SUMMARY")
    print("="*70)
    
    print(f"\n✅ Single Article Test: {'PASSED' if single_result.get('success') else 'FAILED'}")
    if single_result.get('success'):
        print(f"   Duration: {single_result['duration']:.2f}s")
        print(f"   Stages executed: {single_result['stage_inspection']['stage_count']}")
    
    print(f"\n✅ Batch Test: {'PASSED' if batch_result.get('success') else 'FAILED'}")
    if batch_result.get('success'):
        print(f"   Total duration: {batch_result['total_duration']:.2f}s")
        print(f"   Articles: {len(batch_result['results'])}")
    
    # Save results
    output_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: {output_file}")
    
    return results


if __name__ == "__main__":
    results = asyncio.run(main())

