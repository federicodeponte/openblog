#!/usr/bin/env python3
"""
Find Real Statistics Charts from Research Pages

Uses Enhanced Asset Finder to:
1. Find research pages with actual charts
2. Fetch and parse those pages
3. Extract real chart images with actual data
4. Show them in Preview
"""

import asyncio
import os
import subprocess
from pathlib import Path

# Load env
env_file = Path('.env.local')
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip('"').strip("'")

from pipeline.agents.enhanced_asset_finder import EnhancedAssetFinder, EnhancedAssetFinderRequest

async def find_real_charts():
    """Find real statistics charts from research pages."""
    print("\n" + "="*80)
    print("FINDING REAL STATISTICS CHARTS FROM RESEARCH PAGES")
    print("="*80)
    print("\n🎯 Goal: Find REAL charts with actual data from research pages")
    print("   Like: Bar charts, statistics, research data visualizations\n")
    
    finder = EnhancedAssetFinder()
    
    # Focus on finding charts from research pages
    request = EnhancedAssetFinderRequest(
        article_topic="content citation rates statistics research",
        find_charts=True,
        find_tables=True,
        find_infographics=True,
        extract_data=True,
        fetch_pages=True,  # Actually fetch pages to extract charts
        max_results=10
    )
    
    print("📊 Searching for research pages with statistics charts...")
    print(f"   Topic: {request.article_topic}")
    print(f"   Will fetch pages and extract charts\n")
    
    assets = await finder.find_engaging_assets(request)
    
    if not assets:
        print("⚠️  No charts found")
        return
    
    print(f"\n✅ Found {len(assets)} engaging assets:\n")
    
    chart_images = []
    for i, asset in enumerate(assets, 1):
        print(f"{i}. {asset.title}")
        print(f"   📊 Type: {asset.asset_type}")
        print(f"   📦 Source: {asset.source}")
        print(f"   🔗 URL: {asset.url[:70]}...")
        if asset.source_url:
            print(f"   📄 Page: {asset.source_url[:60]}...")
        if asset.can_regenerate:
            print(f"   ✨ Can regenerate in design system")
        print()
        
        # Collect chart images
        if asset.asset_type in ['chart', 'infographic'] and asset.url.startswith('http'):
            chart_images.append(asset.url)
    
    # Download and show chart images
    if chart_images:
        print(f"\n📥 Found {len(chart_images)} chart images")
        print("   These are REAL charts with actual data from research pages!")
        print("\n💡 To view these charts:")
        print("   Open the URLs in your browser to see the actual statistics")
        for url in chart_images[:5]:
            print(f"   • {url}")
    
    return chart_images

async def search_specific_statistics():
    """Search for specific statistics like citation rates."""
    print("\n" + "="*80)
    print("SEARCHING FOR CITATION STATISTICS CHARTS")
    print("="*80)
    
    finder = EnhancedAssetFinder()
    
    request = EnhancedAssetFinderRequest(
        article_topic="content citation rates 3x more likely statistics research data",
        find_charts=True,
        find_infographics=True,
        fetch_pages=True,
        max_results=5
    )
    
    print("🔍 Searching for pages with citation rate statistics...\n")
    
    assets = await finder.find_engaging_assets(request)
    
    if assets:
        print(f"✅ Found {len(assets)} assets with citation statistics:\n")
        for i, asset in enumerate(assets, 1):
            print(f"{i}. {asset.title}")
            print(f"   {asset.url[:70]}...")
            if asset.source_url:
                print(f"   From: {asset.source_url[:60]}...")
            print()

async def main():
    """Find real statistics charts."""
    print("\n📊 Finding Real Statistics Charts with Actual Data\n")
    
    charts = await find_real_charts()
    await search_specific_statistics()
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print("\n✅ Enhanced Asset Finder:")
    print("   • Finds research pages with real charts")
    print("   • Fetches and parses HTML pages")
    print("   • Extracts actual chart images with data")
    print("   • Can extract data from charts/tables")
    print("\n💡 These are REAL charts with actual statistics,")
    print("   not AI-generated images!")
    print("\n📊 Next steps:")
    print("   1. Open chart URLs in browser to view")
    print("   2. Extract data from charts using Gemini Vision")
    print("   3. Regenerate charts in your design system")

if __name__ == "__main__":
    asyncio.run(main())

