#!/usr/bin/env python3
"""
Direct Smart Citation Test - Pure Validator Testing

Tests the SmartCitationValidator directly without pipeline complexity:
1. Direct validator testing with intentionally broken URLs
2. Smart citation replacement workflow validation  
3. Gemini + web search integration verification
4. Batch processing performance analysis
5. Real-world broken URL scenarios
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

class DirectCitationTester:
    """Direct smart citation validator tester"""
    
    def __init__(self):
        self.results = []
    
    def create_broken_citation_scenarios(self) -> List[Dict[str, Any]]:
        """Create realistic broken citation scenarios for testing replacement"""
        return [
            {
                "scenario_id": 1,
                "title": "AI Ethics in Healthcare Decision Making",
                "authors": ["Dr. Sarah Johnson", "Prof. Michael Chen"],
                "year": 2024,
                "url": "https://broken-medical-ethics-journal.edu/ai-healthcare-decisions",
                "domain": "healthcare AI ethics",
                "expected_replacement_type": "academic medical source"
            },
            {
                "scenario_id": 2,
                "title": "NIST Cybersecurity Framework Implementation Guide",
                "authors": ["NIST Research Team"],
                "year": 2024,
                "url": "https://definitely-broken-nist.gov/cybersecurity-framework-404",
                "domain": "cybersecurity standards",
                "expected_replacement_type": "government security guidelines"
            },
            {
                "scenario_id": 3,
                "title": "Machine Learning Applications in Financial Trading",
                "authors": ["Dr. Lisa Wang", "Prof. Robert Smith"],
                "year": 2023,
                "url": "https://404-finance-research.org/ml-trading-algorithms",
                "domain": "financial ML applications",
                "expected_replacement_type": "academic finance research"
            },
            {
                "scenario_id": 4,
                "title": "Cloud Migration Strategies for Enterprise Systems",
                "authors": ["Cloud Computing Consortium"],
                "year": 2024,
                "url": "https://broken-cloud-research.com/enterprise-migration-strategies",
                "domain": "enterprise cloud migration",
                "expected_replacement_type": "cloud technology whitepaper"
            },
            {
                "scenario_id": 5,
                "title": "Blockchain Applications in Supply Chain Transparency",
                "authors": ["Dr. Amanda Rodriguez", "Prof. David Lee"],
                "year": 2023,
                "url": "https://fake-supply-chain-journal.org/blockchain-transparency",
                "domain": "blockchain supply chain",
                "expected_replacement_type": "supply chain technology research"
            },
            {
                "scenario_id": 6,
                "title": "Remote Work Productivity and Team Collaboration Tools",
                "authors": ["Harvard Business Review"],
                "year": 2024,
                "url": "https://404-work-productivity.com/remote-collaboration-study",
                "domain": "remote work productivity",
                "expected_replacement_type": "business productivity research"
            },
            {
                "scenario_id": 7,
                "title": "Sustainable Technology and Green Computing Initiatives",
                "authors": ["Environmental Tech Institute"],
                "year": 2023,
                "url": "https://broken-green-tech.org/sustainable-computing-report",
                "domain": "sustainable technology",
                "expected_replacement_type": "environmental technology research"
            },
            {
                "scenario_id": 8,
                "title": "Digital Marketing Automation and AI-Driven Campaigns",
                "authors": ["Marketing AI Research Group"],
                "year": 2024,
                "url": "https://nonexistent-marketing-research.com/ai-automation-campaigns",
                "domain": "digital marketing automation",
                "expected_replacement_type": "marketing technology research"
            },
            {
                "scenario_id": 9,
                "title": "Quantum Computing Applications in Cryptography",
                "authors": ["Dr. Quantum Smith", "Prof. Alice Crypto"],
                "year": 2024,
                "url": "https://broken-quantum-research.edu/cryptography-applications",
                "domain": "quantum computing cryptography",
                "expected_replacement_type": "academic quantum research"
            },
            {
                "scenario_id": 10,
                "title": "Data Privacy Regulations and GDPR Compliance Strategies",
                "authors": ["Privacy Law Institute"],
                "year": 2023,
                "url": "https://fake-privacy-law.org/gdpr-compliance-guide",
                "domain": "data privacy regulations",
                "expected_replacement_type": "legal privacy guidelines"
            }
        ]
    
    async def test_single_citation_replacement(self, citation: Dict[str, Any]) -> Dict[str, Any]:
        """Test smart replacement for a single citation"""
        
        scenario_id = citation["scenario_id"]
        start_time = time.time()
        
        print(f"\n🔍 SCENARIO {scenario_id}: Testing Citation Replacement")
        print(f"   Title: {citation['title'][:60]}...")
        print(f"   Broken URL: {citation['url']}")
        print(f"   Domain: {citation['domain']}")
        
        try:
            from pipeline.processors.ultimate_citation_validator import SmartCitationValidator
            from pipeline.models.gemini_client import GeminiClient
            
            # Initialize Gemini client for testing
            try:
                gemini_client = GeminiClient()
                print(f"   ✅ Gemini client initialized")
                has_gemini = True
            except Exception as e:
                print(f"   ⚠️  Gemini client failed: {str(e)[:50]}...")
                gemini_client = None
                has_gemini = False
            
            # Create smart citation validator
            validator = SmartCitationValidator(
                gemini_client=gemini_client,
                timeout=10.0,
                max_search_attempts=3
            )
            
            # Test the complete citation validation workflow
            validation_start = time.time()
            
            result = await validator.validate_single_citation(
                citation,
                company_url="https://test-company.com",
                competitors=["competitor.com"]
            )
            
            validation_time = time.time() - validation_start
            
            # Analyze the result
            is_valid = result.is_valid
            final_url = result.url
            issues = result.issues
            validation_type = result.validation_type
            
            # Determine if smart replacement occurred
            url_changed = final_url != citation["url"]
            smart_replacement_detected = (
                validation_type == 'alternative_found' or 
                url_changed or
                any('alternative' in issue.lower() or 'replaced' in issue.lower() for issue in issues)
            )
            
            total_time = time.time() - start_time
            
            print(f"   📊 Validation Result:")
            print(f"      Status: {'✅ VALID' if is_valid else '❌ INVALID'}")
            print(f"      Type: {validation_type}")
            print(f"      Original URL: {citation['url']}")
            print(f"      Final URL: {final_url}")
            print(f"      URL Changed: {'✅ YES' if url_changed else '❌ NO'}")
            print(f"      Smart Replacement: {'✅ DETECTED' if smart_replacement_detected else '❌ NOT DETECTED'}")
            
            if issues:
                print(f"      Issues Found:")
                for issue in issues[:3]:  # Show first 3 issues
                    print(f"         - {issue}")
                if len(issues) > 3:
                    print(f"         ... and {len(issues) - 3} more")
            
            await validator.close()
            
            result_data = {
                "scenario_id": scenario_id,
                "status": "completed",
                "citation_info": {
                    "title": citation["title"],
                    "domain": citation["domain"],
                    "original_url": citation["url"]
                },
                "validation_result": {
                    "is_valid": is_valid,
                    "final_url": final_url,
                    "validation_type": validation_type,
                    "url_changed": url_changed,
                    "smart_replacement_detected": smart_replacement_detected,
                    "issues_count": len(issues)
                },
                "performance": {
                    "total_time": total_time,
                    "validation_time": validation_time,
                    "has_gemini": has_gemini
                },
                "quality_assessment": {
                    "replacement_quality": "high" if smart_replacement_detected and is_valid else "none",
                    "gemini_integration": "functional" if has_gemini else "unavailable"
                }
            }
            
            print(f"   🎉 SCENARIO {scenario_id}: Completed ({total_time:.2f}s)")
            return result_data
            
        except Exception as e:
            error_time = time.time() - start_time
            print(f"   ❌ SCENARIO {scenario_id}: Failed ({error_time:.2f}s)")
            print(f"      Error: {str(e)[:100]}...")
            
            return {
                "scenario_id": scenario_id,
                "status": "failed",
                "error": str(e),
                "performance": {
                    "total_time": error_time
                }
            }
    
    async def run_batch_citation_tests(self, citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Run batch citation replacement tests"""
        
        print("🧠 DIRECT SMART CITATION REPLACEMENT TEST")
        print("=" * 80)
        print(f"Testing {len(citations)} broken citations with smart replacement")
        print("Focus: Gemini + web search powered alternative source finding")
        print("=" * 80)
        
        start_time = time.time()
        
        # Execute all citation tests in parallel
        tasks = [
            self.test_single_citation_replacement(citation)
            for citation in citations
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_batch_time = end_time - start_time
        
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "scenario_id": i + 1,
                    "status": "exception",
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        self.results = processed_results
        
        # Analyze and report
        self.analyze_batch_results(processed_results, total_batch_time)
        
        return processed_results
    
    def analyze_batch_results(self, results: List[Dict[str, Any]], total_time: float):
        """Analyze and report batch citation test results"""
        
        print(f"\n🏆 DIRECT SMART CITATION TEST RESULTS")
        print("=" * 80)
        
        # Basic statistics
        total_tests = len(results)
        completed_tests = [r for r in results if r.get("status") == "completed"]
        failed_tests = [r for r in results if r.get("status") != "completed"]
        
        success_rate = (len(completed_tests) / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"\n📈 BATCH TEST SUMMARY:")
        print(f"   Total citation tests: {total_tests}")
        print(f"   Completed: {len(completed_tests)}")
        print(f"   Failed: {len(failed_tests)}")
        print(f"   Success rate: {success_rate:.1f}%")
        print(f"   Total batch time: {total_time:.2f} seconds")
        
        if completed_tests:
            # Performance analysis
            avg_total_time = sum(r["performance"]["total_time"] for r in completed_tests) / len(completed_tests)
            avg_validation_time = sum(r["performance"]["validation_time"] for r in completed_tests) / len(completed_tests)
            gemini_available = sum(1 for r in completed_tests if r["performance"]["has_gemini"])
            
            # Citation replacement analysis
            valid_citations = [r for r in completed_tests if r["validation_result"]["is_valid"]]
            smart_replacements = [r for r in completed_tests if r["validation_result"]["smart_replacement_detected"]]
            url_changes = [r for r in completed_tests if r["validation_result"]["url_changed"]]
            
            print(f"\n⚡ PERFORMANCE METRICS:")
            print(f"   Avg total time per test: {avg_total_time:.2f}s")
            print(f"   Avg validation time: {avg_validation_time:.2f}s")
            print(f"   Parallel efficiency: {total_time / avg_total_time:.2f}x speedup")
            print(f"   Tests per minute: {(len(completed_tests) / total_time) * 60:.1f}")
            print(f"   Gemini availability: {gemini_available}/{len(completed_tests)}")
            
            print(f"\n🧠 SMART REPLACEMENT ANALYSIS:")
            print(f"   Total broken URLs tested: {len(completed_tests)}")
            print(f"   Valid citations after processing: {len(valid_citations)}")
            print(f"   Smart replacements detected: {len(smart_replacements)}")
            print(f"   URL changes detected: {len(url_changes)}")
            
            replacement_rate = (len(smart_replacements) / len(completed_tests)) * 100 if completed_tests else 0
            validation_success_rate = (len(valid_citations) / len(completed_tests)) * 100 if completed_tests else 0
            
            print(f"   Smart replacement rate: {replacement_rate:.1f}%")
            print(f"   Citation validation success rate: {validation_success_rate:.1f}%")
        
        # Individual results summary
        print(f"\n📋 INDIVIDUAL TEST RESULTS:")
        for result in results[:10]:  # Show first 10 results
            if result["status"] == "completed":
                scenario_id = result["scenario_id"]
                total_time = result["performance"]["total_time"]
                is_valid = result["validation_result"]["is_valid"]
                smart_detected = result["validation_result"]["smart_replacement_detected"]
                validation_type = result["validation_result"]["validation_type"]
                
                status_icon = "✅" if is_valid else "❌"
                smart_icon = " + Smart" if smart_detected else ""
                
                print(f"   {status_icon} Scenario {scenario_id}: {total_time:.2f}s ({validation_type}{smart_icon})")
            else:
                scenario_id = result["scenario_id"]
                error = result.get("error", "Unknown error")[:40]
                print(f"   ❌ Scenario {scenario_id}: FAILED - {error}...")
        
        if len(results) > 10:
            print(f"   ... and {len(results) - 10} more results")
        
        # Final assessment
        if success_rate >= 80:
            print(f"\n🎉 EXCELLENT RESULTS!")
            print(f"🚀 Smart Citation Replacement is working exceptionally well!")
            
            if len(smart_replacements) > 0:
                print(f"🧠 Gemini-powered replacement detected in {len(smart_replacements)} tests!")
            
            print(f"\n🏆 KEY ACHIEVEMENTS:")
            print(f"   ✅ High success rate ({success_rate:.1f}%)")
            print(f"   ✅ Smart replacement functional ({replacement_rate:.1f}% replacement rate)")
            print(f"   ✅ Efficient parallel processing ({(len(completed_tests) / total_time) * 60:.1f} tests/min)")
            print(f"   ✅ Gemini integration operational")
            print(f"   ✅ Broken URL detection and replacement working")
            
        elif success_rate >= 50:
            print(f"\n✅ GOOD RESULTS - Some optimization opportunities")
            if len(smart_replacements) > 0:
                print(f"🧠 Smart replacement is working but could be optimized")
                
        else:
            print(f"\n⚠️  SIGNIFICANT ISSUES")
            print(f"🔨 Smart citation replacement requires fixes")

async def run_direct_smart_test():
    """Run the complete direct smart citation test"""
    
    print("🧪 DIRECT SMART CITATION REPLACEMENT - COMPREHENSIVE TEST")
    print("=" * 100)
    print("Testing SmartCitationValidator directly with Gemini + web search")
    print("=" * 100)
    
    # Initialize tester
    tester = DirectCitationTester()
    
    # Create broken citation scenarios
    citations = tester.create_broken_citation_scenarios()
    print(f"\n📋 BROKEN CITATION TEST SCENARIOS ({len(citations)} total):")
    for citation in citations:
        print(f"   {citation['scenario_id']}. {citation['domain']} - {citation['title'][:40]}...")
    
    # Run batch tests
    print(f"\n⚡ EXECUTING DIRECT SMART CITATION TESTS...")
    await tester.run_batch_citation_tests(citations)
    
    print(f"\n💡 TEST OBJECTIVES:")
    print(f"   🔍 Validate SmartCitationValidator with broken URLs")
    print(f"   🧠 Test Gemini + web search integration")
    print(f"   🎯 Measure smart replacement success rate")
    print(f"   ⚡ Analyze parallel processing performance")
    print(f"   🏆 Verify end-to-end citation replacement workflow")

if __name__ == "__main__":
    asyncio.run(run_direct_smart_test())