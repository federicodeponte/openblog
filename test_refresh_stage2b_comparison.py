#!/usr/bin/env python3
"""
Test Content Refresh - Stage 2b Comparison

Tests that refresh functionality works like stage 2b:
- Uses structured JSON output (prevents hallucinations)
- Properly refreshes content based on instructions
- Maintains content structure and quality
"""

import os
import sys
import asyncio
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env.local
env_file = Path(__file__).parent / ".env.local"
if env_file.exists():
    load_dotenv(env_file)
    # Map GOOGLE_GEMINI_API_KEY to GEMINI_API_KEY if needed
    if "GOOGLE_GEMINI_API_KEY" in os.environ and "GEMINI_API_KEY" not in os.environ:
        os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_GEMINI_API_KEY"]
else:
    load_dotenv()

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from service.content_refresher import ContentParser, ContentRefresher
from pipeline.models.gemini_client import GeminiClient


async def test_refresh_with_structured_output():
    """Test 1: Verify refresh uses structured JSON output like stage 2b"""
    print("\n" + "="*60)
    print("TEST 1: Structured JSON Output (Stage 2b Comparison)")
    print("="*60)
    
    # Check API key
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_GEMINI_API_KEY")
    if not api_key:
        print("❌ ERROR: No API key found. Set GOOGLE_API_KEY or GEMINI_API_KEY")
        return False
    
    # Initialize components
    gemini_client = GeminiClient(api_key=api_key)
    refresher = ContentRefresher(gemini_client)
    
    # Test content with known issues (like stage 2b would detect)
    test_content = {
        "headline": "AI Security Trends",
        "sections": [
            {
                "heading": "Introduction",
                "content": "<p>In 2023, approximately 45% of companies adopted AI security solutions. The market was valued at $150 billion globally.</p>"
            },
            {
                "heading": "Key Benefits",
                "content": "<p>AI security provides automation and speed. Machine learning enables real-time detection.</p><ul><li>AI security provides automation</li><li>Speed</li><li>Real-time detection</li></ul>"
            }
        ],
        "meta_description": "AI security trends in 2023"
    }
    
    instructions = [
        "Update all 2023 statistics to 2025 data",
        "Remove duplicate bullet lists that repeat paragraph content",
        "Make the tone more conversational"
    ]
    
    print(f"\n📝 Original Content:")
    print(f"   Sections: {len(test_content['sections'])}")
    for i, section in enumerate(test_content['sections']):
        print(f"   Section {i}: {section['heading']}")
        print(f"      Content: {section['content'][:80]}...")
    
    print(f"\n🔧 Instructions:")
    for inst in instructions:
        print(f"   - {inst}")
    
    print(f"\n🤖 Calling Gemini with structured JSON output...")
    
    try:
        refreshed_content = await refresher.refresh_content(
            content=test_content,
            instructions=instructions,
            target_sections=[0, 1]  # Refresh both sections
        )
        
        print(f"\n✅ Refresh completed successfully!")
        print(f"\n📊 Results:")
        print(f"   Sections refreshed: {len(refreshed_content.get('sections', []))}")
        
        # Check for hallucinations (common issues stage 2b fixes)
        hallucinations_found = []
        for section in refreshed_content.get('sections', []):
            content = section.get('content', '')
            heading = section.get('heading', '')
            
            # Check for common hallucinations
            if 'You can aI' in content or 'You can a I' in content:
                hallucinations_found.append(f"'{heading}': 'You can aI' pattern")
            if 'What is How' in content or 'What is Why' in content:
                hallucinations_found.append(f"'{heading}': Double prefix pattern")
            if 'change_summary' in section:
                print(f"   ✅ Section '{heading}': {section.get('change_summary', 'N/A')}")
        
        if hallucinations_found:
            print(f"\n❌ HALLUCINATIONS DETECTED:")
            for h in hallucinations_found:
                print(f"   - {h}")
            return False
        else:
            print(f"\n✅ No hallucinations detected (structured output working!)")
        
        # Verify structure is maintained
        if len(refreshed_content.get('sections', [])) == len(test_content['sections']):
            print(f"✅ Structure preserved ({len(test_content['sections'])} sections)")
        else:
            print(f"⚠️  Structure changed: {len(test_content['sections'])} → {len(refreshed_content.get('sections', []))}")
        
        # Check if instructions were followed
        all_content = ' '.join([s.get('content', '') for s in refreshed_content.get('sections', [])])
        
        checks = {
            "2025 data": "2025" in all_content.lower(),
            "No duplicate lists": "<ul>" not in all_content or all_content.count("<ul>") <= 1,
            "Conversational tone": any(phrase in all_content.lower() for phrase in ["you", "your", "here's", "let's"])
        }
        
        print(f"\n📋 Instruction Compliance:")
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"   {status} {check}")
        
        # Show sample refreshed content
        print(f"\n📄 Sample Refreshed Content:")
        for i, section in enumerate(refreshed_content.get('sections', [])[:2]):
            print(f"\n   Section {i+1}: {section.get('heading', 'N/A')}")
            content_preview = section.get('content', '')[:200]
            print(f"   {content_preview}...")
        
        return all(checks.values())
        
    except Exception as e:
        print(f"\n❌ Error during refresh: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_refresh_vs_stage2b_approach():
    """Test 2: Compare refresh approach to stage 2b quality refinement"""
    print("\n" + "="*60)
    print("TEST 2: Refresh vs Stage 2b Approach Comparison")
    print("="*60)
    
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_GEMINI_API_KEY")
    if not api_key:
        print("❌ ERROR: No API key found")
        return False
    
    gemini_client = GeminiClient(api_key=api_key)
    refresher = ContentRefresher(gemini_client)
    
    # Content with quality issues that stage 2b would detect
    problematic_content = {
        "headline": "Cloud Security Best Practices",
        "sections": [
            {
                "heading": "Overview",
                "content": "<p>Cloud security is crucial—organizations must protect their data. Here are key points:</p><ul><li>Cloud security is crucial</li><li>Organizations must protect data</li></ul><p>This </p>"
            },
            {
                "heading": "Implementation",
                "content": "<p>According to Gartner [1], 67% of companies use cloud security. IBM [2] reports similar findings.</p>"
            }
        ]
    }
    
    # Stage 2b would fix:
    # 1. Em dashes (—)
    # 2. Duplicate bullet lists
    # 3. Academic citations [1], [2]
    # 4. Orphaned paragraphs ("This ")
    
    instructions = [
        "Remove em dashes and replace with commas or hyphens",
        "Remove duplicate bullet lists that repeat paragraph content",
        "Convert academic citations [1], [2] to natural language like 'according to Gartner'",
        "Remove orphaned incomplete paragraphs"
    ]
    
    print(f"\n🔍 Testing refresh with Stage 2b-style quality fixes...")
    print(f"   Issues to fix:")
    print(f"   - Em dashes (—)")
    print(f"   - Duplicate bullet lists")
    print(f"   - Academic citations [N]")
    print(f"   - Orphaned paragraphs")
    
    try:
        refreshed = await refresher.refresh_content(
            content=problematic_content,
            instructions=instructions,
            target_sections=[0, 1]
        )
        
        all_content = ' '.join([s.get('content', '') for s in refreshed.get('sections', [])])
        
        # Check fixes
        fixes_applied = {
            "Em dashes removed": "—" not in all_content,
            "Duplicate lists removed": all_content.count("<ul>") <= 1,
            "Academic citations converted": "[" not in all_content or "[1]" not in all_content,
            "Orphaned paragraphs removed": "<p>This </p>" not in all_content
        }
        
        print(f"\n📊 Quality Fixes Applied:")
        all_fixed = True
        for fix, applied in fixes_applied.items():
            status = "✅" if applied else "❌"
            print(f"   {status} {fix}")
            if not applied:
                all_fixed = False
        
        if all_fixed:
            print(f"\n✅ All Stage 2b-style quality issues fixed!")
            return True
        else:
            print(f"\n⚠️  Some quality issues remain")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_refresh_json_structure():
    """Test 3: Verify JSON structure matches stage 2b expectations"""
    print("\n" + "="*60)
    print("TEST 3: JSON Structure Validation")
    print("="*60)
    
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_GEMINI_API_KEY")
    if not api_key:
        print("❌ ERROR: No API key found")
        return False
    
    gemini_client = GeminiClient(api_key=api_key)
    refresher = ContentRefresher(gemini_client)
    
    test_content = {
        "headline": "Test Article",
        "sections": [
            {
                "heading": "Section One",
                "content": "<p>Original content here.</p>"
            }
        ]
    }
    
    instructions = ["Add more detail to this section"]
    
    try:
        refreshed = await refresher.refresh_content(
            content=test_content,
            instructions=instructions,
            target_sections=[0]
        )
        
        # Verify structure
        required_fields = ['headline', 'sections']
        structure_valid = all(field in refreshed for field in required_fields)
        
        if structure_valid:
            print(f"✅ Required top-level fields present: {required_fields}")
        else:
            missing = [f for f in required_fields if f not in refreshed]
            print(f"❌ Missing fields: {missing}")
            return False
        
        # Verify section structure
        if refreshed.get('sections'):
            section = refreshed['sections'][0]
            section_fields = ['heading', 'content']
            section_valid = all(field in section for field in section_fields)
            
            if section_valid:
                print(f"✅ Section structure valid: {section_fields}")
                print(f"   Heading: {section.get('heading', 'N/A')}")
                print(f"   Content length: {len(section.get('content', ''))} chars")
                if 'change_summary' in section:
                    print(f"   Change summary: {section.get('change_summary', 'N/A')}")
                return True
            else:
                missing = [f for f in section_fields if f not in section]
                print(f"❌ Section missing fields: {missing}")
                return False
        else:
            print(f"❌ No sections in response")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all refresh tests"""
    print("\n" + "="*60)
    print("CONTENT REFRESH - STAGE 2B COMPARISON TESTS")
    print("="*60)
    print("\nTesting that refresh works like stage 2b:")
    print("  ✓ Uses structured JSON output")
    print("  ✓ Prevents hallucinations")
    print("  ✓ Maintains content quality")
    print("  ✓ Follows instructions correctly")
    
    results = []
    
    try:
        # Test 1: Structured JSON output
        result1 = await test_refresh_with_structured_output()
        results.append(("Structured JSON Output", result1))
        
        # Test 2: Stage 2b comparison
        result2 = await test_refresh_vs_stage2b_approach()
        results.append(("Stage 2b Quality Fixes", result2))
        
        # Test 3: JSON structure
        result3 = await test_refresh_json_structure()
        results.append(("JSON Structure Validation", result3))
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{status}: {test_name}")
        
        print(f"\n📊 Results: {passed}/{total} tests passed ({(passed/total*100):.1f}%)")
        
        if passed == total:
            print("\n🎉 ALL TESTS PASSED!")
            print("Refresh functionality works correctly like stage 2b.")
        else:
            print(f"\n⚠️  {total - passed} test(s) failed. Review output above.")
        
        return passed == total
        
    except Exception as e:
        print(f"\n❌ Testing failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

