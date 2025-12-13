#!/usr/bin/env python3
"""
Debug DataForSEO Google Images API - See what's happening
"""

import asyncio
import os
import logging
from pathlib import Path

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Load env
env_file = Path('.env.local')
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip('"').strip("'")

from pipeline.agents.google_images_finder import GoogleImagesFinder

async def test():
    finder = GoogleImagesFinder()
    
    if not finder.is_configured():
        print("❌ Not configured")
        return
    
    print("✅ Configured")
    print(f"   Login: {finder.api_login}")
    print(f"   Password: {'*' * len(finder.api_password) if finder.api_password else None}")
    print()
    
    print("Testing with simple query...")
    images = await finder.search_images(
        query="cloud security",
        max_results=5
    )
    
    print(f"\n✅ Found {len(images)} images")
    for img in images:
        print(f"  - {img.title}: {img.url[:60]}...")

if __name__ == "__main__":
    asyncio.run(test())

