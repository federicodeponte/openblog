#!/usr/bin/env python3
"""
Download Statistics Charts and Convert to WebP

Finds real statistics charts, downloads them, converts to WebP, and opens in Preview.
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

from pipeline.agents.serper_images_finder import SerperImagesFinder

async def download_and_convert_charts():
    """Find statistics charts, download, convert to WebP, and show."""
    print("📊 Finding real statistics charts...\n")
    
    finder = SerperImagesFinder()
    
    if not finder.is_configured():
        print("⚠️  Serper Dev not configured")
        return
    
    # Search for accessible statistics charts
    queries = [
        "content citation statistics bar chart",
        "blog post statistics research data visualization",
        "content marketing statistics infographic"
    ]
    
    all_images = []
    
    for query in queries:
        print(f"🔍 Searching: {query}")
        images = await finder.search_images(
            query=query,
            max_results=5,
            size="large"
        )
        
        if images:
            print(f"   ✅ Found {len(images)} charts")
            all_images.extend(images)
        print()
    
    if not all_images:
        print("⚠️  No charts found")
        return
    
    # Remove duplicates
    seen_urls = set()
    unique_images = []
    for img in all_images:
        if img.url not in seen_urls:
            seen_urls.add(img.url)
            unique_images.append(img)
    
    print(f"✅ Found {len(unique_images)} unique charts\n")
    
    # Create directory
    charts_dir = Path('output/real_charts')
    charts_dir.mkdir(parents=True, exist_ok=True)
    
    # Download, convert to WebP, and show
    webp_files = []
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        for i, img in enumerate(unique_images[:5], 1):
            try:
                print(f"📥 {i}/{min(len(unique_images), 5)}: {img.title[:50]}...")
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                }
                
                response = await client.get(img.url, headers=headers)
                
                if response.status_code == 200:
                    # Try to open as image
                    try:
                        image_data = io.BytesIO(response.content)
                        pil_image = Image.open(image_data)
                        
                        # Convert to RGB if needed (for PNG with transparency)
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
                        print(f"   ✅ Converted to WebP: {webp_filename.name} ({webp_filename.stat().st_size // 1024}KB)")
                    except Exception as e:
                        print(f"   ⚠️  Image conversion failed: {e}")
                        # Try saving original
                        ext = 'png' if 'png' in response.headers.get('content-type', '') else 'jpg'
                        filename = charts_dir / f"statistics_chart_{i}.{ext}"
                        with open(filename, 'wb') as f:
                            f.write(response.content)
                        print(f"   ✅ Saved original: {filename.name}")
                else:
                    print(f"   ⚠️  Failed: HTTP {response.status_code}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
    
    # Open WebP files in Preview
    if webp_files:
        print(f"\n🖼️  Opening {len(webp_files)} statistics charts in Preview (WebP format)...")
        for file_path in webp_files:
            try:
                subprocess.run(['open', '-a', 'Preview', file_path], check=True)
                print(f"   ✅ Opened: {Path(file_path).name}")
            except Exception as e:
                print(f"   ❌ Failed: {e}")
        
        print(f"\n✅ Statistics charts opened in Preview!")
        print(f"   📊 Real charts with actual data (WebP format)")
        print(f"   💾 Saved in: {charts_dir}")
    else:
        print("\n⚠️  No charts converted")

if __name__ == "__main__":
    asyncio.run(download_and_convert_charts())

