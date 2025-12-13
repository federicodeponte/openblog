#!/usr/bin/env python3
"""Update preview HTML with real data from enhanced asset finder."""

import asyncio
import json
from pathlib import Path
import os

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

async def get_real_assets():
    finder = EnhancedAssetFinder()
    request = EnhancedAssetFinderRequest(
        article_topic='cloud security statistics',
        find_charts=True,
        find_tables=True,
        find_infographics=True,
        fetch_pages=True,
        max_results=3
    )
    assets = await finder.find_engaging_assets(request)
    await finder.close()
    
    # Convert to JSON-serializable format
    result = []
    for asset in assets[:15]:  # Limit to 15
        asset_dict = {
            'url': asset.url,
            'title': asset.title[:100],  # Truncate long titles
            'description': asset.description[:200] if asset.description else '',
            'source': asset.source,
            'asset_type': asset.asset_type,
            'image_type': asset.image_type,
            'can_regenerate': asset.can_regenerate,
            'source_url': asset.source_url
        }
        
        # Add data_extracted if available
        if asset.data_extracted:
            asset_dict['data_extracted'] = asset.data_extracted
        
        result.append(asset_dict)
    
    return result

if __name__ == "__main__":
    assets = asyncio.run(get_real_assets())
    
    # Generate JavaScript array
    js_array = json.dumps(assets, indent=8)
    
    # Read current HTML
    html_file = Path('preview_enhanced_assets.html')
    if html_file.exists():
        content = html_file.read_text()
        
        # Replace assets array
        import re
        pattern = r'const assets = \[.*?\];'
        replacement = f'const assets = {js_array};'
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        html_file.write_text(content)
        print(f"✅ Updated {html_file} with {len(assets)} real assets")
    else:
        print(f"❌ {html_file} not found")

