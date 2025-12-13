#!/usr/bin/env python3
"""
Quick Stage 4 Verification Test

Tests Stage 4 citations with various company_data scenarios to verify null checks.
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

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


async def test_stage4_scenarios():
    """Test Stage 4 with different company_data scenarios"""
    print("="*70)
    print("QUICK STAGE 4 VERIFICATION TEST")
    print("="*70)
    print()
    
    engine = WorkflowEngine()
    stages = create_production_pipeline_stages()
    engine.register_stages(stages)
    
    test_scenarios = [
        {
            "name": "Normal (with company_data)",
            "company_data": {
                "company_name": "Test Company",
                "company_url": "https://test.example.com"
            },
            "expected": "Should work"
        },
        {
            "name": "Missing company_data",
            "company_data": None,
            "expected": "Should handle gracefully (no crash)"
        },
        {
            "name": "Empty company_data",
            "company_data": {},
            "expected": "Should handle gracefully"
        }
    ]
    
    results = []
    
    for scenario in test_scenarios:
        print(f"\n{'='*70}")
        print(f"Testing: {scenario['name']}")
        print(f"{'='*70}")
        print(f"Expected: {scenario['expected']}")
        
        job_config = {
            "primary_keyword": "API security testing",
            "company_url": "https://test.example.com",
            "language": "en",
            "country": "US",
            "company_data": scenario["company_data"],
            "word_count": 500  # Smaller for quick test
        }
        
        job_id = f"quick-test-{scenario['name'].lower().replace(' ', '-')}"
        
        try:
            # Create context manually to test Stage 4 directly
            context = ExecutionContext(job_id=job_id, job_config=job_config)
            context.company_data = scenario["company_data"]
            
            # Run stages 0-3 to get to Stage 4 (using execute method)
            # We'll create a minimal context with structured_data for Stage 4
            from pipeline.models.output_schema import ArticleOutput
            
            # Create minimal article data
            context.structured_data = ArticleOutput(
                Headline="Test Article",
                Intro="Test intro",
                Sources="[1]: https://example.com – Test source"
            )
            
            # Now test Stage 4
            stage_4 = engine.stages.get(4)
            if not stage_4:
                print("  ❌ Stage 4 not found")
                results.append({"scenario": scenario["name"], "success": False, "error": "Stage 4 not found"})
                continue
            
            print(f"  🔍 Running Stage 4...")
            start_time = asyncio.get_event_loop().time()
            
            try:
                context = await stage_4.execute(context)
                duration = asyncio.get_event_loop().time() - start_time
                
                print(f"  ✅ Stage 4 completed successfully in {duration:.2f}s")
                results.append({"scenario": scenario["name"], "success": True, "duration": duration})
                
            except AttributeError as e:
                if "'NoneType' object has no attribute 'get'" in str(e):
                    print(f"  ❌ FAILED: Null check issue - {e}")
                    results.append({"scenario": scenario["name"], "success": False, "error": str(e)})
                else:
                    print(f"  ⚠️  Other error: {e}")
                    results.append({"scenario": scenario["name"], "success": False, "error": str(e)})
            except Exception as e:
                print(f"  ⚠️  Error: {e}")
                results.append({"scenario": scenario["name"], "success": False, "error": str(e)})
                
        except Exception as e:
            print(f"  ❌ Setup failed: {e}")
            results.append({"scenario": scenario["name"], "success": False, "error": str(e)})
    
    # Summary
    print("\n" + "="*70)
    print("QUICK VERIFICATION SUMMARY")
    print("="*70)
    
    passed = sum(1 for r in results if r.get("success"))
    total = len(results)
    
    print(f"\nResults: {passed}/{total} scenarios passed")
    print()
    
    for result in results:
        status = "✅" if result.get("success") else "❌"
        print(f"{status} {result['scenario']}")
        if not result.get("success"):
            print(f"   Error: {result.get('error', 'Unknown')}")
        elif "duration" in result:
            print(f"   Duration: {result['duration']:.2f}s")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(test_stage4_scenarios())
    sys.exit(0 if success else 1)

