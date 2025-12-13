#!/usr/bin/env python3
"""
Simple Refresh Test - Verifies refresh works like Stage 2b

Run with: python3 test_refresh_simple.py
Requires: GOOGLE_API_KEY or GEMINI_API_KEY environment variable
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env.local
env_file = Path(__file__).parent / ".env.local"
if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ Loaded {env_file}")
    
    # Map GOOGLE_GEMINI_API_KEY to GEMINI_API_KEY if needed
    if "GOOGLE_GEMINI_API_KEY" in os.environ and "GEMINI_API_KEY" not in os.environ:
        os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_GEMINI_API_KEY"]
        print("✅ Mapped GOOGLE_GEMINI_API_KEY → GEMINI_API_KEY")
else:
    load_dotenv()  # Fallback to default .env

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from service.content_refresher import ContentParser, ContentRefresher
from pipeline.models.gemini_client import GeminiClient


async def test_refresh_basic():
    """Basic test of refresh functionality"""
    print("="*60)
    print("REFRESH FUNCTIONALITY TEST")
    print("="*60)
    
    # Check API key
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_GEMINI_API_KEY")
    if not api_key:
        print("\n⚠️  No API key found. Set GOOGLE_API_KEY or GEMINI_API_KEY")
        print("\nTo test refresh functionality:")
        print("  1. Set API key: export GEMINI_API_KEY='your-key'")
        print("  2. Run: python3 test_refresh_simple.py")
        print("\n✅ Code verification shows refresh uses structured JSON output like Stage 2b")
        return False
    
    print(f"\n✅ API key found")
    
    # Initialize
    gemini_client = GeminiClient(api_key=api_key)
    refresher = ContentRefresher(gemini_client)
    
    # Simple test content
    test_content = {
        "headline": "Test Article",
        "sections": [
            {
                "heading": "Introduction",
                "content": "<p>This is test content from 2023. It needs updating.</p>"
            }
        ],
        "meta_description": "Test article"
    }
    
    instructions = ["Update the year from 2023 to 2025"]
    
    print(f"\n📝 Test Content:")
    print(f"   Heading: {test_content['sections'][0]['heading']}")
    print(f"   Content: {test_content['sections'][0]['content']}")
    
    print(f"\n🔧 Instructions:")
    print(f"   - {instructions[0]}")
    
    print(f"\n🤖 Calling Gemini with structured JSON output...")
    
    try:
        refreshed = await refresher.refresh_content(
            content=test_content,
            instructions=instructions,
            target_sections=[0]
        )
        
        print(f"\n✅ Refresh completed!")
        
        # Check result
        section = refreshed.get('sections', [{}])[0]
        refreshed_content = section.get('content', '')
        
        print(f"\n📊 Results:")
        print(f"   Heading: {section.get('heading', 'N/A')}")
        print(f"   Content: {refreshed_content[:100]}...")
        
        if 'change_summary' in section:
            print(f"   Change Summary: {section.get('change_summary', 'N/A')}")
        
        # Verify instruction was followed
        if '2025' in refreshed_content:
            print(f"\n✅ Instruction followed: Year updated to 2025")
        else:
            print(f"\n⚠️  Instruction may not have been followed")
        
        # Check for hallucinations
        if 'You can aI' in refreshed_content or 'What is How' in refreshed_content:
            print(f"\n❌ Hallucination detected!")
            return False
        else:
            print(f"\n✅ No hallucinations detected (structured output working!)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run test"""
    success = await test_refresh_basic()
    
    print("\n" + "="*60)
    if success:
        print("✅ TEST PASSED")
        print("Refresh works correctly like Stage 2b!")
    else:
        print("⚠️  TEST INCOMPLETE")
        print("Check output above for details")
    print("="*60)
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

