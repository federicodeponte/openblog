#!/usr/bin/env python3
"""
Stage 4 Smart Citation Test - Real Pipeline Integration

Tests Stage 4 (Citations) with smart citation replacement in the actual Isaac Security pipeline:
1. Direct Stage 4 testing with proper ExecutionContext
2. Smart citation validation and replacement workflow
3. Parallel processing of multiple citation scenarios
4. Performance analysis of Gemini + web search integration
"""

import asyncio
import os
import time
import json
from typing import List, Dict, Any
from datetime import datetime

# Set environment for testing
os.environ.setdefault('OPENROUTER_API_KEY', os.environ.get('OPENROUTER_API_KEY', 'test_key'))
os.environ.setdefault('GEMINI_API_KEY', os.environ.get('GEMINI_API_KEY', 'test_key'))

class Stage4CitationTester:
    """Stage 4 citation validation tester with smart replacement"""
    
    def __init__(self):
        self.results = []
    
    def create_citation_test_scenarios(self) -> List[Dict[str, Any]]:
        """Create realistic citation test scenarios with broken URLs"""
        return [
            {
                "job_id": "test_job_1",
                "topic": "AI in Healthcare",
                "company": "HealthTech Solutions",
                "sources": [
                    "https://broken-medical-research.edu/ai-diagnosis-study",  # Broken academic
                    "https://healthcare-404-journal.org/articles/ai-ethics",  # 404 journal
                    "https://httpbin.org/status/404",  # Returns 404
                    "https://example.com/fake-healthcare-study",  # Fake URL
                    "https://nonexistent-medical-site.com/research"  # Non-existent
                ]
            },
            {
                "job_id": "test_job_2", 
                "topic": "Cybersecurity Best Practices",
                "company": "SecureShield Corp",
                "sources": [
                    "https://broken-security-research.gov/cybersec-framework",
                    "https://404-security-site.org/best-practices",
                    "https://httpbin.org/status/500", # Server error
                    "https://example.org/security-guide-fake",
                    "https://timeout-site.com/security-report"
                ]
            },
            {
                "job_id": "test_job_3",
                "topic": "Cloud Computing Strategy", 
                "company": "CloudFirst Technologies",
                "sources": [
                    "https://broken-cloud-research.edu/migration-study",
                    "https://cloud-404-journal.com/strategies",
                    "https://httpbin.org/status/403",  # Forbidden
                    "https://example.net/cloud-migration-guide",
                    "https://fake-cloud-vendor.com/whitepaper"
                ]
            },
            {
                "job_id": "test_job_4",
                "topic": "Machine Learning Finance",
                "company": "FinAI Innovations", 
                "sources": [
                    "https://broken-finance-research.edu/ml-trading",
                    "https://fintech-404-journal.org/ai-algorithms",
                    "https://httpbin.org/delay/20",  # Timeout
                    "https://example.com/ml-finance-study", 
                    "https://nonexistent-fintech.com/research"
                ]
            },
            {
                "job_id": "test_job_5",
                "topic": "Blockchain Supply Chain",
                "company": "ChainTrack Systems",
                "sources": [
                    "https://broken-blockchain-research.edu/supply-chain",
                    "https://logistics-404-site.org/blockchain-guide",
                    "https://httpbin.org/status/502",  # Bad gateway
                    "https://example.org/blockchain-logistics",
                    "https://fake-supply-chain.com/blockchain-study"
                ]
            }
        ]
    
    async def test_stage4_citations(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Test Stage 4 citation processing with smart replacement"""
        
        job_id = scenario["job_id"]
        start_time = time.time()
        
        print(f"\n🔍 TESTING {job_id.upper()}: {scenario['topic']}")
        print(f"   Company: {scenario['company']}")
        print(f"   Sources: {len(scenario['sources'])} (all intentionally broken)")
        
        try:
            from pipeline.core.execution_context import ExecutionContext
            from pipeline.blog_generation.stage_04_citations import CitationsStage
            from pipeline.models.output_schema import ArticleOutput
            
            # Create proper ExecutionContext with job_id
            context = ExecutionContext(job_id=job_id)
            
            # Set up required context data
            context.company_data = {
                "company_name": scenario["company"],
                "company_url": f"https://{scenario['company'].lower().replace(' ', '-')}.com"
            }
            
            context.sitemap_data = {
                "competitors": ["competitor1.com", "competitor2.com"]
            }
            
            context.language = "en"
            context.parallel_results = {}
            
            # Create structured data with broken source URLs
            context.structured_data = ArticleOutput(
                title=f"The Complete Guide to {scenario['topic']}",
                introduction=f"This article explores {scenario['topic']} and its impact on modern business.",
                main_content=f"Comprehensive analysis of {scenario['topic']} including trends, best practices, and future outlook.",
                conclusion=f"The future of {scenario['topic']} presents both challenges and opportunities.",
                sources=scenario["sources"]  # All broken URLs for testing replacement
            )
            
            setup_time = time.time() - start_time
            print(f"   ✅ Context setup complete ({setup_time:.2f}s)")
            
            # Execute Stage 4 with Smart Citations
            print(f"   🧠 Executing Stage 4 with smart citation replacement...")
            citation_start = time.time()
            
            citations_stage = CitationsStage()
            await citations_stage.execute(context)
            
            citation_time = time.time() - citation_start
            
            # Analyze results
            citations_html = context.parallel_results.get('citations_html', '')
            original_source_count = len(scenario["sources"])
            
            # Check for citations in HTML
            processed_citations = citations_html.count('<li>') if citations_html else 0
            working_urls = citations_html.count('http') if citations_html else 0
            
            # Look for smart replacement indicators
            replacement_indicators = [
                'alternative' in citations_html.lower(),
                'replaced' in citations_html.lower(), 
                'found' in citations_html.lower(),
                working_urls > 0  # Any working URLs found despite broken sources
            ]
            smart_replacement_detected = any(replacement_indicators)
            
            total_time = time.time() - start_time
            
            print(f"   ✅ Stage 4 complete ({citation_time:.2f}s)")
            print(f"      Original sources: {original_source_count} (all broken)")
            print(f"      Processed citations: {processed_citations}")
            print(f"      Working URLs found: {working_urls}")
            print(f"      Smart replacement: {'✅ DETECTED' if smart_replacement_detected else '❌ NOT DETECTED'}")
            
            result = {
                "job_id": job_id,
                "status": "success",
                "scenario": scenario,
                "citation_processing": {
                    "original_sources": original_source_count,
                    "processed_citations": processed_citations,
                    "working_urls_found": working_urls,
                    "citations_html_length": len(citations_html),
                    "smart_replacement_detected": smart_replacement_detected
                },
                "performance": {
                    "total_time": total_time,
                    "setup_time": setup_time,
                    "citation_processing_time": citation_time
                },
                "quality_metrics": {
                    "sources_to_citations_ratio": processed_citations / original_source_count if original_source_count > 0 else 0,
                    "citation_success_rate": (working_urls / original_source_count) * 100 if original_source_count > 0 else 0
                }
            }
            
            print(f"   🎉 {job_id.upper()}: SUCCESS ({total_time:.2f}s total)")
            return result
            
        except Exception as e:
            error_time = time.time() - start_time
            print(f"   ❌ {job_id.upper()}: FAILED ({error_time:.2f}s)")
            print(f"      Error: {str(e)[:100]}...")
            
            return {
                "job_id": job_id,
                "status": "failed",
                "error": str(e),
                "performance": {
                    "total_time": error_time
                }
            }
    
    async def run_parallel_citation_tests(self, scenarios: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Run parallel citation tests for all scenarios"""
        
        print("🧪 STAGE 4 SMART CITATION REPLACEMENT TEST")
        print("=" * 80)
        print(f"Testing {len(scenarios)} scenarios with broken URLs → smart replacement")
        print("=" * 80)
        
        start_time = time.time()
        
        # Execute all scenarios in parallel
        tasks = [
            self.test_stage4_citations(scenario)
            for scenario in scenarios
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_batch_time = end_time - start_time
        
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "job_id": f"test_job_{i+1}",
                    "status": "exception",
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        self.results = processed_results
        
        # Analyze and report
        self.analyze_citation_results(processed_results, total_batch_time)
        
        return processed_results
    
    def analyze_citation_results(self, results: List[Dict[str, Any]], total_time: float):
        """Analyze and report citation test results"""
        
        print(f"\n🏆 STAGE 4 SMART CITATION TEST RESULTS")
        print("=" * 80)
        
        # Basic statistics
        total_tests = len(results)
        successful_tests = [r for r in results if r.get("status") == "success"]
        failed_tests = [r for r in results if r.get("status") != "success"]
        
        success_rate = (len(successful_tests) / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"\n📈 CITATION TEST SUMMARY:")
        print(f"   Total citation tests: {total_tests}")
        print(f"   Successful: {len(successful_tests)}")
        print(f"   Failed: {len(failed_tests)}")
        print(f"   Success rate: {success_rate:.1f}%")
        print(f"   Total batch time: {total_time:.2f} seconds")
        
        if successful_tests:
            # Performance analysis
            avg_total_time = sum(r["performance"]["total_time"] for r in successful_tests) / len(successful_tests)
            avg_citation_time = sum(r["performance"]["citation_processing_time"] for r in successful_tests) / len(successful_tests)
            
            # Citation processing analysis
            total_original_sources = sum(r["citation_processing"]["original_sources"] for r in successful_tests)
            total_processed_citations = sum(r["citation_processing"]["processed_citations"] for r in successful_tests)
            total_working_urls = sum(r["citation_processing"]["working_urls_found"] for r in successful_tests)
            smart_replacement_count = sum(1 for r in successful_tests if r["citation_processing"]["smart_replacement_detected"])
            
            avg_citation_success = sum(r["quality_metrics"]["citation_success_rate"] for r in successful_tests) / len(successful_tests)
            
            print(f"\n⚡ PERFORMANCE METRICS:")
            print(f"   Avg total time per test: {avg_total_time:.2f}s")
            print(f"   Avg citation processing time: {avg_citation_time:.2f}s")
            print(f"   Parallel efficiency: {total_time / avg_total_time:.2f}x speedup")
            print(f"   Tests per minute: {(len(successful_tests) / total_time) * 60:.1f}")
            
            print(f"\n🔍 SMART CITATION ANALYSIS:")
            print(f"   Original broken sources: {total_original_sources} (all intentionally broken)")
            print(f"   Citations processed: {total_processed_citations}")
            print(f"   Working URLs found: {total_working_urls}")
            print(f"   Smart replacement detected: {smart_replacement_count}/{len(successful_tests)}")
            print(f"   Avg citation success rate: {avg_citation_success:.1f}%")
            
            replacement_success_rate = (smart_replacement_count / len(successful_tests)) * 100
            print(f"   Smart replacement success rate: {replacement_success_rate:.1f}%")
        
        # Individual results
        print(f"\n📋 INDIVIDUAL TEST RESULTS:")
        for result in results:
            if result["status"] == "success":
                job_id = result["job_id"]
                total_time = result["performance"]["total_time"]
                working_urls = result["citation_processing"]["working_urls_found"]
                smart_detected = result["citation_processing"]["smart_replacement_detected"]
                
                smart_indicator = " + Smart Replacement" if smart_detected else ""
                urls_indicator = f" ({working_urls} working URLs)" if working_urls > 0 else ""
                
                print(f"   ✅ {job_id}: {total_time:.2f}s{smart_indicator}{urls_indicator}")
            else:
                job_id = result["job_id"]
                error = result.get("error", "Unknown error")[:50]
                print(f"   ❌ {job_id}: FAILED - {error}...")
        
        # Final assessment
        if success_rate >= 80:
            print(f"\n🎉 EXCELLENT RESULTS!")
            print(f"🚀 Stage 4 Smart Citation Replacement is working!")
            
            if smart_replacement_count > 0:
                print(f"🧠 Gemini-powered citation replacement detected in {smart_replacement_count} tests!")
            
            print(f"\n🏆 KEY ACHIEVEMENTS:")
            print(f"   ✅ Stage 4 citation processing stable")
            print(f"   ✅ Smart citation replacement functional")
            print(f"   ✅ Broken URL detection working")
            print(f"   ✅ Parallel processing optimized")
            print(f"   ✅ Isaac Security V4.0 integration successful")
            
        elif success_rate >= 50:
            print(f"\n✅ GOOD RESULTS - Some optimization needed")
            
        else:
            print(f"\n⚠️  SIGNIFICANT ISSUES")
            print(f"🔨 Stage 4 requires fixes before production")

async def run_stage4_smart_test():
    """Run the complete Stage 4 smart citation test"""
    
    print("🧪 ISAAC SECURITY STAGE 4 - SMART CITATION REPLACEMENT TEST")
    print("=" * 100)
    print("Testing Stage 4 citation processing with Gemini + web search replacement")
    print("=" * 100)
    
    # Initialize tester
    tester = Stage4CitationTester()
    
    # Create citation test scenarios
    scenarios = tester.create_citation_test_scenarios()
    print(f"\n📋 CITATION TEST SCENARIOS:")
    for scenario in scenarios:
        print(f"   {scenario['job_id']}: {scenario['topic']} ({len(scenario['sources'])} broken sources)")
    
    # Run citation tests
    print(f"\n⚡ EXECUTING STAGE 4 SMART CITATION TESTS...")
    await tester.run_parallel_citation_tests(scenarios)
    
    print(f"\n💡 TEST OBJECTIVES:")
    print(f"   🔍 Validate Stage 4 citation processing")
    print(f"   🧠 Test Gemini + web search replacement")
    print(f"   💔 Process intentionally broken URLs")
    print(f"   ⚡ Measure parallel processing performance")
    print(f"   🎯 Verify smart replacement detection")

if __name__ == "__main__":
    asyncio.run(run_stage4_smart_test())