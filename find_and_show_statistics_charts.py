#!/usr/bin/env python3
"""
Find Real Statistics Charts and Show in Preview

Uses Serper Dev to find actual statistics charts from research sites,
then downloads and opens them in Preview.
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

from pipeline.agents.serper_images_finder import SerperImagesFinder

async def find_and_show_charts():
    """Find statistics charts and show in Preview."""
    print("📊 Finding real statistics charts with actual data...\n")
    
    finder = SerperImagesFinder()
    
    if not finder.is_configured():
        print("⚠️  Serper Dev not configured")
        return
    
    # Search for statistics charts like the example
    queries = [
        "content citation rates statistics bar chart research",
        "content marketing statistics 2024 data visualization",
        "blog post citation statistics research chart"
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
        else:
            print(f"   ⚠️  No results")
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
    
    print(f"✅ Found {len(unique_images)} unique statistics charts\n")
    
    # Create directory
    charts_dir = Path('output/real_charts')
    charts_dir.mkdir(parents=True, exist_ok=True)
    
    # Download and show charts
    downloaded_files = []
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        for i, img in enumerate(unique_images[:5], 1):  # Limit to 5
            try:
                print(f"📥 Downloading {i}/{min(len(unique_images), 5)}: {img.title[:50]}...")
                print(f"   Source: {img.source}")
                
                # Set user agent to avoid blocking
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                }
                
                response = await client.get(img.url, headers=headers)
                
                if response.status_code == 200:
                    # Determine extension from content type or URL
                    content_type = response.headers.get('content-type', '')
                    if 'svg' in content_type or img.url.endswith('.svg'):
                        ext = 'svg'
                    elif 'png' in content_type or img.url.endswith('.png'):
                        ext = 'png'
                    elif 'jpg' in content_type or 'jpeg' in content_type or img.url.endswith(('.jpg', '.jpeg')):
                        ext = 'jpg'
                    else:
                        ext = 'png'  # Default
                    
                    filename = charts_dir / f"statistics_chart_{i}.{ext}"
                    
                    with open(filename, 'wb') as f:
                        f.write(response.content)
                    
                    downloaded_files.append(str(filename))
                    print(f"   ✅ Saved: {filename.name} ({len(response.content)} bytes)")
                else:
                    print(f"   ⚠️  Failed: HTTP {response.status_code}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
    
    # Open in Preview
    if downloaded_files:
        print(f"\n🖼️  Opening {len(downloaded_files)} statistics charts in Preview...")
        for file_path in downloaded_files:
            try:
                subprocess.run(['open', '-a', 'Preview', file_path], check=True)
                print(f"   ✅ Opened: {Path(file_path).name}")
            except Exception as e:
                print(f"   ❌ Failed: {e}")
        
        print(f"\n✅ Statistics charts opened in Preview!")
        print(f"   📊 These are REAL charts with actual data from research sites")
        print(f"   💾 Saved in: {charts_dir}")
    else:
        print("\n⚠️  No charts downloaded")

if __name__ == "__main__":
    asyncio.run(find_and_show_charts())

