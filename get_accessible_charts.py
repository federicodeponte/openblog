#!/usr/bin/env python3
"""
Get Accessible Statistics Charts

Finds charts from accessible sources and downloads them properly as WebP.
"""

import asyncio
import os
import subprocess
import httpx
from pathlib import Path
from PIL import Image
import io

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

async def get_accessible_charts():
    """Get charts from pages that are accessible."""
    print("📊 Finding accessible statistics charts from research pages...\n")
    
    finder = EnhancedAssetFinder()
    
    # Search for pages with statistics charts
    request = EnhancedAssetFinderRequest(
        article_topic="content citation rates statistics research",
        find_charts=True,
        find_infographics=True,
        fetch_pages=True,
        max_results=10
    )
    
    assets = await finder.find_engaging_assets(request)
    
    # Filter for chart images with accessible URLs
    chart_images = []
    for asset in assets:
        if asset.asset_type in ['chart', 'infographic']:
            url = asset.url
            # Skip avatars and non-image URLs
            if url.startswith('http') and 'avatar' not in url.lower() and 'gravatar' not in url.lower():
                # Prefer SVG or direct image URLs
                if any(ext in url.lower() for ext in ['.svg', '.png', '.jpg', '.jpeg', '.webp', '.gif']):
                    chart_images.append({
                        'url': url,
                        'title': asset.title,
                        'source': asset.source_url or 'Unknown'
                    })
    
    if not chart_images:
        print("⚠️  No accessible chart images found")
        return
    
    print(f"✅ Found {len(chart_images)} chart images\n")
    
    # Create directory
    charts_dir = Path('output/real_charts')
    charts_dir.mkdir(parents=True, exist_ok=True)
    
    # Download and convert to WebP
    webp_files = []
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        for i, chart in enumerate(chart_images[:5], 1):
            try:
                print(f"📥 {i}/{min(len(chart_images), 5)}: {chart['title'][:50]}...")
                print(f"   URL: {chart['url'][:60]}...")
                
                # Full browser headers to avoid blocking
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'image/webp,image/png,image/svg+xml,image/apng,image/*;q=0.8,*/*;q=0.5',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Referer': chart['source'] if chart.get('source') and chart['source'].startswith('http') else 'https://www.google.com/',
                    'Sec-Fetch-Dest': 'image',
                    'Sec-Fetch-Mode': 'no-cors',
                    'Sec-Fetch-Site': 'cross-site',
                }
                
                response = await client.get(chart['url'], headers=headers)
                
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '').lower()
                    
                    # Check if it's actually an image
                    if 'html' in content_type or response.content[:100].startswith(b'<'):
                        print(f"   ⚠️  Got HTML instead of image (skipping)")
                        continue
                    
                    # Try to open as image
                    try:
                        image_data = io.BytesIO(response.content)
                        pil_image = Image.open(image_data)
                        
                        # Convert to RGB if needed
                        if pil_image.mode in ('RGBA', 'LA', 'P'):
                            rgb_image = Image.new('RGB', pil_image.size, (255, 255, 255))
                            if pil_image.mode == 'P':
                                pil_image = pil_image.convert('RGBA')
                            rgb_image.paste(pil_image, mask=pil_image.split()[-1] if pil_image.mode == 'RGBA' else None)
                            pil_image = rgb_image
                        elif pil_image.mode != 'RGB':
                            pil_image = pil_image.convert('RGB')
                        
                        # Save as WebP
                        webp_filename = charts_dir / f"statistics_chart_{i}.webp"
                        pil_image.save(webp_filename, 'WEBP', quality=90)
                        
                        webp_files.append(str(webp_filename))
                        file_size = webp_filename.stat().st_size // 1024
                        print(f"   ✅ Converted to WebP: {webp_filename.name} ({file_size}KB)")
                    except Exception as e:
                        print(f"   ⚠️  Image conversion failed: {e}")
                else:
                    print(f"   ⚠️  HTTP {response.status_code}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
    
    # Open WebP files in Preview
    if webp_files:
        print(f"\n🖼️  Opening {len(webp_files)} statistics charts in Preview (WebP)...")
        for file_path in webp_files:
            try:
                subprocess.run(['open', '-a', 'Preview', file_path], check=True)
                print(f"   ✅ Opened: {Path(file_path).name}")
            except Exception as e:
                print(f"   ❌ Failed: {e}")
        
        print(f"\n✅ Charts opened in Preview!")
        print(f"   📊 Real statistics charts (WebP format)")
        print(f"   💾 Saved in: {charts_dir}")
    else:
        print("\n⚠️  No charts successfully downloaded")
        print("   Many sites block direct image access")
        print("   Try opening the source URLs in browser instead")

if __name__ == "__main__":
    asyncio.run(get_accessible_charts())

