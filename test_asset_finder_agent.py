#!/usr/bin/env python3
"""
Test script for Asset Finder Agent

Tests the asset finder agent in isolation:
1. Finding assets from the internet
2. Optionally recreating them in company design system

Run with:
    python test_asset_finder_agent.py

Loads API key from .env.local file automatically.
"""

import asyncio
import os
import json
import logging
from typing import Dict, Any
from pathlib import Path

# Load environment variables from .env.local
def load_env_local():
    """Load environment variables from .env.local file."""
    env_file = Path(__file__).parent / ".env.local"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    # Remove quotes if present
                    value = value.strip('"').strip("'")
                    os.environ[key.strip()] = value
        print(f"✅ Loaded environment from {env_file}")
    else:
        print(f"⚠️  No .env.local file found at {env_file}")

# Load .env.local before importing anything that needs API keys
load_env_local()

from pipeline.agents.asset_finder import (
    AssetFinderAgent,
    AssetFinderRequest,
    AssetFinderResponse
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_find_assets_only():
    """Test 1: Find assets from internet (no recreation)."""
    print("\n" + "="*80)
    print("TEST 1: Finding Assets from Internet")
    print("="*80)
    print("\nTechnology Used:")
    print("  - Gemini AI with Google Search grounding")
    print("  - Automatic web search for free stock images")
    print("  - JSON parsing of search results")
    print()
    
    try:
        agent = AssetFinderAgent()
    except ValueError as e:
        print(f"❌ Cannot initialize agent: {e}")
        print("   Set GEMINI_API_KEY environment variable to test")
        return None
    
    request = AssetFinderRequest(
        article_topic="AI cybersecurity automation",
        article_headline="Complete Guide to AI Cybersecurity Automation Platforms",
        section_title="Benefits of AI-Powered Security",
        max_results=5,
        recreate_in_design_system=False  # Just find, don't recreate
    )
    
    response = await agent.find_assets(request)
    
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    print(f"✅ Success: {response.success}")
    print(f"🔍 Search Query: {response.search_query_used}")
    print(f"📦 Found {len(response.assets)} assets\n")
    
    for i, asset in enumerate(response.assets, 1):
        print(f"Asset {i}:")
        print(f"  Title: {asset.title}")
        print(f"  URL: {asset.url}")
        print(f"  Source: {asset.source}")
        print(f"  Type: {asset.image_type}")
        print(f"  Description: {asset.description[:100]}...")
        if asset.license_info:
            print(f"  License: {asset.license_info}")
        print()
    
    return response


async def test_find_and_recreate():
    """Test 2: Find assets AND recreate in design system."""
    print("\n" + "="*80)
    print("TEST 2: Finding Assets + Recreating in Design System")
    print("="*80)
    
    agent = AssetFinderAgent()
    
    # Sample company data with design system info
    company_data = {
        "company_name": "TechSecure Inc",
        "industry": "Technology",
        "brand_tone": "modern professional",
        "description": "Enterprise cybersecurity solutions",
        "project_folder_id": None  # Optional: Google Drive folder ID
    }
    
    request = AssetFinderRequest(
        article_topic="cloud security best practices",
        article_headline="Top 10 Cloud Security Best Practices for 2025",
        section_title="Multi-Factor Authentication",
        company_data=company_data,
        max_results=3,  # Limit for recreation (takes longer)
        recreate_in_design_system=True  # Enable recreation
    )
    
    response = await agent.find_assets(request)
    
    print(f"\n✅ Success: {response.success}")
    print(f"🔍 Search Query: {response.search_query_used}")
    print(f"📦 Found {len(response.assets)} assets")
    print(f"🎨 Recreated {len(response.recreated_assets)} assets\n")
    
    # Show original assets
    print("Original Assets Found:")
    for i, asset in enumerate(response.assets, 1):
        print(f"  {i}. {asset.title} ({asset.source})")
        print(f"     {asset.url}")
    
    # Show recreated assets
    if response.recreated_assets:
        print("\n🎨 Recreated Assets:")
        for i, recreated in enumerate(response.recreated_assets, 1):
            print(f"  {i}. Original: {recreated['original_title']}")
            print(f"     Recreated URL: {recreated['recreated_url']}")
            print(f"     Success: {recreated['success']}")
    
    return response


async def test_design_system_extraction():
    """Test 3: Test design system extraction from company data."""
    print("\n" + "="*80)
    print("TEST 3: Design System Extraction")
    print("="*80)
    print("\nThis test shows how design system is extracted from company data.")
    print("No API key needed - this is pure logic.\n")
    
    try:
        agent = AssetFinderAgent()
    except ValueError:
        # Create a minimal agent just for design system extraction
        from pipeline.models.gemini_client import GeminiClient
        from pipeline.models.google_imagen_client import GoogleImagenClient
        
        class MockAgent:
            def _extract_design_system(self, company_data):
                # Copy the method logic
                design_system = {
                    "colors": [],
                    "style": "professional",
                    "industry": company_data.get("industry", "")
                }
                
                industry = company_data.get("industry", "").lower()
                industry_colors = {
                    "technology": ["#0066CC", "#00CCFF", "#333333"],
                    "finance": ["#1A472A", "#2D5016", "#FFD700"],
                    "healthcare": ["#0066CC", "#00CC99", "#FFFFFF"],
                    "retail": ["#FF6B6B", "#4ECDC4", "#FFE66D"],
                    "education": ["#4A90E2", "#50C878", "#FFA500"],
                }
                
                for key, colors in industry_colors.items():
                    if key in industry:
                        design_system["colors"] = colors
                        break
                
                if not design_system["colors"]:
                    design_system["colors"] = ["#6366F1", "#8B5CF6", "#EC4899"]
                
                brand_tone = company_data.get("brand_tone", "").lower()
                if "modern" in brand_tone or "contemporary" in brand_tone:
                    design_system["style"] = "modern minimalist"
                elif "classic" in brand_tone or "traditional" in brand_tone:
                    design_system["style"] = "classic professional"
                elif "creative" in brand_tone or "bold" in brand_tone:
                    design_system["style"] = "creative vibrant"
                
                return design_system
        
        agent = MockAgent()
    
    # Test different industries
    test_companies = [
        {
            "company_name": "FinanceCorp",
            "industry": "Finance",
            "brand_tone": "classic professional"
        },
        {
            "company_name": "HealthTech",
            "industry": "Healthcare",
            "brand_tone": "modern clean"
        },
        {
            "company_name": "CreativeStudio",
            "industry": "Creative",
            "brand_tone": "creative vibrant"
        }
    ]
    
    for company in test_companies:
        design_system = agent._extract_design_system(company)
        print(f"\nCompany: {company['company_name']}")
        print(f"  Industry: {design_system['industry']}")
        print(f"  Colors: {design_system['colors']}")
        print(f"  Style: {design_system['style']}")


async def test_section_specific_search():
    """Test 4: Find assets for a specific section."""
    print("\n" + "="*80)
    print("TEST 4: Section-Specific Asset Search")
    print("="*80)
    
    agent = AssetFinderAgent()
    
    request = AssetFinderRequest(
        article_topic="data analytics",
        article_headline="How to Build a Data Analytics Dashboard",
        section_title="Choosing the Right Visualization Tools",
        image_types=["diagram", "infographic"],  # Specific types for this section
        max_results=3
    )
    
    response = await agent.find_assets(request)
    
    print(f"\n✅ Success: {response.success}")
    print(f"🔍 Search Query: {response.search_query_used}")
    print(f"📦 Found {len(response.assets)} assets\n")
    
    for asset in response.assets:
        print(f"  • {asset.title} ({asset.image_type})")
        print(f"    {asset.url}")


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("ASSET FINDER AGENT - ISOLATED TESTING")
    print("="*80)
    print("\nThis script tests the Asset Finder Agent in isolation.")
    print("It can find assets from the internet and optionally recreate")
    print("them using Gemini Imagen in your company's design system.\n")
    
    # Check for API key (already loaded from .env.local)
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("⚠️  WARNING: No GOOGLE_API_KEY or GEMINI_API_KEY found")
        print("   Add GEMINI_API_KEY to .env.local file to test fully.\n")
    else:
        print(f"✅ API key loaded from .env.local (key: {api_key[:10]}...)\n")
    
    try:
        # Run tests
        await test_find_assets_only()
        await asyncio.sleep(2)  # Rate limiting
        
        await test_design_system_extraction()
        await asyncio.sleep(2)
        
        await test_section_specific_search()
        await asyncio.sleep(2)
        
        # Only run recreation test if API key available
        if api_key:
            await test_find_and_recreate()
        else:
            print("\n" + "="*80)
            print("SKIPPING: Find + Recreate Test (no API key)")
            print("="*80)
            print("Set GOOGLE_API_KEY to test image recreation feature.")
        
        print("\n" + "="*80)
        print("✅ ALL TESTS COMPLETE")
        print("="*80)
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\n❌ Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())

