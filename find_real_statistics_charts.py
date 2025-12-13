#!/usr/bin/env python3
"""
Find Real Statistics Charts and Data Visualizations

Finds actual charts with real data from the web, not AI-generated images.
Focuses on statistics, bar charts, line charts, infographics with data.
"""

import asyncio
import os
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

from pipeline.agents.asset_finder import AssetFinderAgent, AssetFinderRequest

async def find_real_statistics_charts():
    """Find real statistics charts with actual data."""
    print("\n" + "="*80)
    print("FINDING REAL STATISTICS CHARTS")
    print("="*80)
    print("\n🎯 Goal: Find REAL charts with actual data (not AI-generated)")
    print("   Like: Bar charts, line charts, statistics, research data\n")
    
    agent = AssetFinderAgent()
    
    # Focus on finding charts with statistics/data
    request = AssetFinderRequest(
        article_topic="content citation rates statistics research data",
        max_results=5,
        image_types=["chart", "infographic", "statistics", "data visualization", "bar chart", "research"]
    )
    
    print("📊 Searching for statistics charts...")
    print(f"   Topic: {request.article_topic}")
    print(f"   Types: {', '.join(request.image_types)}")
    print()
    
    response = await agent.find_assets(request)
    
    if not response.success:
        print(f"❌ Error: {response.error}")
        return
    
    if not response.assets:
        print("⚠️  No charts found")
        return
    
    print(f"\n✅ Found {len(response.assets)} statistics charts:\n")
    
    for i, asset in enumerate(response.assets, 1):
        print(f"{i}. {asset.title}")
        print(f"   📊 Type: {asset.image_type}")
        print(f"   📦 Source: {asset.source}")
        print(f"   🔗 URL: {asset.url[:70]}...")
        print(f"   📐 Size: {asset.width}x{asset.height}" if asset.width and asset.height else "")
        print()
    
    # Try to find more specific statistics
    print("\n" + "="*80)
    print("SEARCHING FOR SPECIFIC STATISTICS")
    print("="*80)
    
    # Search for content marketing statistics
    request2 = AssetFinderRequest(
        article_topic="content marketing statistics 2024 research data visualization",
        max_results=5,
        image_types=["chart", "infographic", "statistics", "bar chart"]
    )
    
    response2 = await agent.find_assets(request2)
    
    if response2.success and response2.assets:
        print(f"\n✅ Found {len(response2.assets)} content marketing statistics:\n")
        for i, asset in enumerate(response2.assets, 1):
            print(f"{i}. {asset.title}")
            print(f"   {asset.url[:70]}...")
            print()

async def find_charts_with_serper():
    """Use Serper Dev to find charts more directly."""
    print("\n" + "="*80)
    print("USING SERPER DEV FOR CHARTS")
    print("="*80)
    
    from pipeline.agents.serper_images_finder import SerperImagesFinder
    
    finder = SerperImagesFinder()
    
    if not finder.is_configured():
        print("\n⚠️  Serper Dev not configured")
        return
    
    # Search for statistics charts
    print("\n🔍 Searching for: 'content citation statistics bar chart'")
    images = await finder.search_images(
        query="content citation statistics bar chart research data",
        max_results=5,
        size="large",
        image_type="photo"  # Charts are often classified as photos
    )
    
    if images:
        print(f"\n✅ Found {len(images)} chart images:\n")
        for i, img in enumerate(images, 1):
            print(f"{i}. {img.title}")
            print(f"   Source: {img.source}")
            print(f"   URL: {img.url[:70]}...")
            print()

async def main():
    """Find real statistics charts."""
    print("\n📊 Finding Real Statistics Charts with Actual Data\n")
    
    await find_real_statistics_charts()
    await find_charts_with_serper()
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print("\n💡 To find REAL statistics charts:")
    print("   1. Search for specific topics + 'statistics' + 'chart'")
    print("   2. Focus on research sites, data visualization sites")
    print("   3. Look for bar charts, line charts, infographics")
    print("   4. Extract data from charts when possible")
    print("\n⚠️  Note: These are REAL charts with actual data,")
    print("   not AI-generated images!")

if __name__ == "__main__":
    asyncio.run(main())

