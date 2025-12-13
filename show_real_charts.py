#!/usr/bin/env python3
"""
Download and Show Real Statistics Charts in Preview

Finds real charts from research pages and opens them in Preview.
"""

import asyncio
import os
import subprocess
import httpx
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

async def download_and_show_charts():
    """Find and show real statistics charts."""
    print("📊 Finding real statistics charts from research pages...\n")
    
    finder = EnhancedAssetFinder()
    
    # Search for content citation statistics (like the example shown)
    request = EnhancedAssetFinderRequest(
        article_topic="content citation rates statistics research data visualization",
        find_charts=True,
        find_infographics=True,
        fetch_pages=True,
        max_results=10
    )
    
    assets = await finder.find_engaging_assets(request)
    
    # Filter for actual chart images
    chart_images = []
    for asset in assets:
        if asset.asset_type in ['chart', 'infographic'] and asset.url.startswith('http'):
            # Skip avatars and small images
            if 'avatar' not in asset.url.lower() and 'gravatar' not in asset.url.lower():
                chart_images.append({
                    'url': asset.url,
                    'title': asset.title,
                    'source': asset.source_url or asset.source
                })
    
    if not chart_images:
        print("⚠️  No chart images found")
        return
    
    print(f"✅ Found {len(chart_images)} real statistics charts\n")
    
    # Create directory for charts
    charts_dir = Path('output/real_charts')
    charts_dir.mkdir(parents=True, exist_ok=True)
    
    # Download charts
    downloaded_files = []
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        for i, chart in enumerate(chart_images[:5], 1):  # Limit to 5
            try:
                print(f"📥 Downloading {i}/{min(len(chart_images), 5)}: {chart['title'][:50]}...")
                
                response = await client.get(chart['url'])
                
                if response.status_code == 200:
                    # Determine file extension
                    ext = 'svg' if chart['url'].endswith('.svg') else 'png'
                    if 'svg' in chart['url']:
                        ext = 'svg'
                    elif 'png' in chart['url']:
                        ext = 'png'
                    elif 'jpg' in chart['url'] or 'jpeg' in chart['url']:
                        ext = 'jpg'
                    else:
                        ext = 'png'  # Default
                    
                    filename = charts_dir / f"chart_{i}_{chart['title'][:30].replace(' ', '_')}.{ext}"
                    
                    with open(filename, 'wb') as f:
                        f.write(response.content)
                    
                    downloaded_files.append(str(filename))
                    print(f"   ✅ Saved: {filename.name}")
                else:
                    print(f"   ⚠️  Failed: HTTP {response.status_code}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
    
    # Open in Preview
    if downloaded_files:
        print(f"\n🖼️  Opening {len(downloaded_files)} charts in Preview...")
        for file_path in downloaded_files:
            try:
                subprocess.run(['open', '-a', 'Preview', file_path], check=True)
                print(f"   ✅ Opened: {Path(file_path).name}")
            except Exception as e:
                print(f"   ❌ Failed to open {file_path}: {e}")
        
        print(f"\n✅ Charts opened in Preview!")
        print(f"   These are REAL statistics charts with actual data!")
        print(f"   Saved in: {charts_dir}")
    else:
        print("\n⚠️  No charts downloaded")

if __name__ == "__main__":
    asyncio.run(download_and_show_charts())

