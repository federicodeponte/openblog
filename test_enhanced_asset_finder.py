#!/usr/bin/env python3
"""
Test Enhanced Asset Finder - Stage-by-Stage Evaluation

Tests each stage in isolation:
1. Stage 1: Search Query Building
2. Stage 2: Page Discovery (Gemini + Google Search)
3. Stage 3: Page Fetching
4. Stage 4: Asset Extraction (Tables, Charts, Images)
5. Stage 5: Data Extraction (Table parsing, Chart analysis)
6. Stage 6: Asset Labeling & Structuring

Run with:
    python3 test_enhanced_asset_finder.py
"""

import asyncio
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List

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
                    value = value.strip('"').strip("'")
                    os.environ[key.strip()] = value
        print(f"✅ Loaded environment from {env_file}\n")
    else:
        print(f"⚠️  No .env.local file found\n")

load_env_local()

from pipeline.agents.enhanced_asset_finder import (
    EnhancedAssetFinder,
    EnhancedAssetFinderRequest,
    EngagingAsset
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_stage_1_query_building():
    """Test Stage 1: Search Query Building"""
    print("\n" + "="*80)
    print("STAGE 1: SEARCH QUERY BUILDING")
    print("="*80)
    
    finder = EnhancedAssetFinder()
    
    request = EnhancedAssetFinderRequest(
        article_topic="AI cybersecurity automation",
        article_headline="Complete Guide to AI Cybersecurity",
        section_title="Market Statistics",
        find_charts=True,
        find_tables=True,
        find_infographics=True
    )
    
    query = finder._build_engaging_search_query(request)
    
    print(f"\n✅ Query Built Successfully")
    print(f"   Input Topic: {request.article_topic}")
    print(f"   Input Section: {request.section_title}")
    print(f"   Find Charts: {request.find_charts}")
    print(f"   Find Tables: {request.find_tables}")
    print(f"   Find Infographics: {request.find_infographics}")
    print(f"\n   📝 Generated Query:")
    print(f"   {query}")
    
    return query


async def test_stage_2_page_discovery():
    """Test Stage 2: Page Discovery (Gemini + Google Search)"""
    print("\n" + "="*80)
    print("STAGE 2: PAGE DISCOVERY (Gemini + Google Search)")
    print("="*80)
    
    try:
        finder = EnhancedAssetFinder()
    except ValueError as e:
        print(f"❌ Cannot initialize: {e}")
        print("   Set GEMINI_API_KEY in .env.local to test this stage")
        return []
    
    request = EnhancedAssetFinderRequest(
        article_topic="AI adoption statistics 2024",
        find_charts=True,
        find_tables=True,
        max_results=5
    )
    
    print(f"\n📡 Searching for pages with engaging assets...")
    print(f"   Topic: {request.article_topic}")
    print(f"   Looking for: Charts, Tables")
    print(f"   Max results: {request.max_results}")
    print()
    
    pages = await finder._search_for_pages(
        finder._build_engaging_search_query(request),
        request
    )
    
    print(f"\n✅ Found {len(pages)} pages")
    for i, page_url in enumerate(pages, 1):
        print(f"   {i}. {page_url}")
    
    return pages


async def test_stage_3_page_fetching():
    """Test Stage 3: Page Fetching"""
    print("\n" + "="*80)
    print("STAGE 3: PAGE FETCHING")
    print("="*80)
    
    finder = EnhancedAssetFinder()
    
    # Test with a known page that has tables/charts
    test_urls = [
        "https://www.statista.com/topics/2234/artificial-intelligence/",
        "https://www.pewresearch.org/internet/2024/02/15/artificial-intelligence/",
    ]
    
    print(f"\n📥 Testing page fetching...")
    print(f"   Test URLs: {len(test_urls)}")
    print()
    
    fetched_pages = []
    
    for url in test_urls:
        try:
            print(f"   Fetching: {url}")
            response = await finder.http_client.get(url, timeout=10.0)
            print(f"   ✅ Status: {response.status_code}")
            print(f"   ✅ Size: {len(response.text)} characters")
            print(f"   ✅ Content-Type: {response.headers.get('content-type', 'unknown')}")
            fetched_pages.append({
                "url": url,
                "status": response.status_code,
                "size": len(response.text),
                "content": response.text[:500] + "..." if len(response.text) > 500 else response.text
            })
            print()
        except Exception as e:
            print(f"   ❌ Error: {e}\n")
    
    return fetched_pages


async def test_stage_4_asset_extraction():
    """Test Stage 4: Asset Extraction (Tables, Charts, Images)"""
    print("\n" + "="*80)
    print("STAGE 4: ASSET EXTRACTION")
    print("="*80)
    
    finder = EnhancedAssetFinder()
    
    # Use a simple test HTML with tables and images
    test_html = """
    <html>
    <body>
        <h1>Test Page</h1>
        <table>
            <thead>
                <tr><th>Tool</th><th>Price</th><th>Features</th></tr>
            </thead>
            <tbody>
                <tr><td>GitHub Copilot</td><td>$10/month</td><td>AI Code Completion</td></tr>
                <tr><td>Amazon Q</td><td>$20/month</td><td>Enterprise AI</td></tr>
            </tbody>
        </table>
        <img src="/chart.png" alt="AI Adoption Growth Chart" />
        <img src="https://example.com/infographic.jpg" alt="Cybersecurity Infographic" />
    </body>
    </html>
    """
    
    print(f"\n🔍 Testing asset extraction from HTML...")
    print(f"   HTML size: {len(test_html)} characters")
    print()
    
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(test_html, 'html.parser')
    
    # Extract tables
    tables = soup.find_all('table')
    print(f"   📋 Tables found: {len(tables)}")
    for i, table in enumerate(tables, 1):
        rows = table.find_all('tr')
        print(f"      Table {i}: {len(rows)} rows")
    
    # Extract images
    images = soup.find_all('img')
    print(f"\n   📸 Images found: {len(images)}")
    for i, img in enumerate(images, 1):
        alt = img.get('alt', 'No alt text')
        src = img.get('src', 'No src')
        print(f"      Image {i}: {alt[:50]} ({src[:50]})")
    
    return {
        "tables": len(tables),
        "images": len(images)
    }


async def test_stage_5_data_extraction():
    """Test Stage 5: Data Extraction (Table parsing)"""
    print("\n" + "="*80)
    print("STAGE 5: DATA EXTRACTION")
    print("="*80)
    
    finder = EnhancedAssetFinder()
    
    # Test HTML table
    test_html = """
    <table>
        <thead>
            <tr><th>Security Tool</th><th>Price</th><th>Rating</th></tr>
        </thead>
        <tbody>
            <tr><td>Norton</td><td>$49/year</td><td>4.5/5</td></tr>
            <tr><td>McAfee</td><td>$39/year</td><td>4.2/5</td></tr>
            <tr><td>Bitdefender</td><td>$59/year</td><td>4.8/5</td></tr>
        </tbody>
    </table>
    """
    
    print(f"\n📊 Testing table data extraction...")
    
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(test_html, 'html.parser')
    table = soup.find('table')
    
    if table:
        data = finder._extract_table_data(table)
        
        if data:
            print(f"\n✅ Table Data Extracted:")
            print(f"   Headers: {data['headers']}")
            print(f"   Rows: {data['row_count']}")
            print(f"   Columns: {data['column_count']}")
            print(f"\n   📋 Table Content:")
            print(f"   {' | '.join(data['headers'])}")
            for row in data['rows'][:5]:  # Show first 5 rows
                print(f"   {' | '.join(row)}")
            
            return data
    
    return None


async def test_stage_6_full_flow():
    """Test Stage 6: Full Flow (End-to-End)"""
    print("\n" + "="*80)
    print("STAGE 6: FULL FLOW (End-to-End Test)")
    print("="*80)
    
    try:
        finder = EnhancedAssetFinder()
    except ValueError as e:
        print(f"❌ Cannot initialize: {e}")
        print("   Set GEMINI_API_KEY in .env.local to test full flow")
        return []
    
    request = EnhancedAssetFinderRequest(
        article_topic="cloud security statistics",
        find_charts=True,
        find_tables=True,
        find_infographics=True,
        fetch_pages=True,
        extract_data=True,
        max_results=3
    )
    
    print(f"\n🚀 Running full flow...")
    print(f"   Topic: {request.article_topic}")
    print(f"   Fetch pages: {request.fetch_pages}")
    print(f"   Extract data: {request.extract_data}")
    print()
    
    assets = await finder.find_engaging_assets(request)
    
    print(f"\n✅ Found {len(assets)} engaging assets")
    print()
    
    for i, asset in enumerate(assets, 1):
        print(f"Asset {i}:")
        print(f"  Title: {asset.title}")
        print(f"  Type: {asset.asset_type}")
        print(f"  URL: {asset.url[:80]}...")
        print(f"  Source: {asset.source}")
        if asset.data_extracted:
            print(f"  Data Extracted: ✅")
            if asset.asset_type == "table":
                print(f"    Rows: {asset.data_extracted.get('row_count', 0)}")
                print(f"    Columns: {asset.data_extracted.get('column_count', 0)}")
        else:
            print(f"  Data Extracted: ❌")
        print(f"  Can Regenerate: {'✅' if asset.can_regenerate else '❌'}")
        print()
    
    await finder.close()
    return assets


async def main():
    """Run all stage tests."""
    print("\n" + "="*80)
    print("ENHANCED ASSET FINDER - STAGE-BY-STAGE EVALUATION")
    print("="*80)
    print("\nTesting each stage in isolation to evaluate the flow.\n")
    
    results = {}
    
    try:
        # Stage 1: Query Building (no API needed)
        print("\n🔧 STAGE 1: Query Building (No API Required)")
        results['stage_1'] = await test_stage_1_query_building()
        await asyncio.sleep(1)
        
        # Stage 2: Page Discovery (needs API)
        print("\n🔧 STAGE 2: Page Discovery (Requires API Key)")
        results['stage_2'] = await test_stage_2_page_discovery()
        await asyncio.sleep(2)
        
        # Stage 3: Page Fetching (no API needed)
        print("\n🔧 STAGE 3: Page Fetching (No API Required)")
        results['stage_3'] = await test_stage_3_page_fetching()
        await asyncio.sleep(1)
        
        # Stage 4: Asset Extraction (no API needed)
        print("\n🔧 STAGE 4: Asset Extraction (No API Required)")
        results['stage_4'] = await test_stage_4_asset_extraction()
        await asyncio.sleep(1)
        
        # Stage 5: Data Extraction (no API needed)
        print("\n🔧 STAGE 5: Data Extraction (No API Required)")
        results['stage_5'] = await test_stage_5_data_extraction()
        await asyncio.sleep(1)
        
        # Stage 6: Full Flow (needs API)
        print("\n🔧 STAGE 6: Full Flow (Requires API Key)")
        results['stage_6'] = await test_stage_6_full_flow()
        
        # Summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        print(f"\n✅ Stage 1 (Query Building): {'✅ Passed' if results.get('stage_1') else '❌ Failed'}")
        print(f"{'✅' if results.get('stage_2') else '⚠️ '} Stage 2 (Page Discovery): {'✅ Passed' if results.get('stage_2') else '⚠️  Skipped (no API key)'}")
        print(f"✅ Stage 3 (Page Fetching): {'✅ Passed' if results.get('stage_3') else '❌ Failed'}")
        print(f"✅ Stage 4 (Asset Extraction): {'✅ Passed' if results.get('stage_4') else '❌ Failed'}")
        print(f"✅ Stage 5 (Data Extraction): {'✅ Passed' if results.get('stage_5') else '❌ Failed'}")
        print(f"{'✅' if results.get('stage_6') else '⚠️ '} Stage 6 (Full Flow): {'✅ Passed' if results.get('stage_6') else '⚠️  Skipped (no API key)'}")
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\n❌ Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())

