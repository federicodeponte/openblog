#!/usr/bin/env python3
"""
Generate and Show Example Images in Preview

Finds assets and recreates them with Gemini Imagen, then opens in Preview as WebP.
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

from pipeline.agents.asset_finder import AssetFinderAgent, AssetFinderRequest

async def generate_and_show_images():
    """Generate example images and open in Preview."""
    print("🎨 Generating example images with Gemini Imagen...\n")
    
    agent = AssetFinderAgent()
    
    if agent.imagen_client and agent.imagen_client.mock_mode:
        print("⚠️  Imagen is in mock mode - generating mock images")
        print("   Set GOOGLE_API_KEY or GEMINI_API_KEY for real generation\n")
    
    company_data = {
        "company_name": "TechSecure Inc",
        "industry": "Technology",
        "brand_tone": "modern professional",
        "primary_color": "#0066CC",
        "secondary_color": "#00CCFF",
    }
    
    request = AssetFinderRequest(
        article_topic="cloud security dashboard",
        company_data=company_data,
        max_results=3,
        recreate_in_design_system=True  # Enable recreation!
    )
    
    response = await agent.find_assets(request)
    
    if not response.success:
        print(f"❌ Error: {response.error}")
        return
    
    if not response.recreated_assets:
        print("⚠️  No images were recreated")
        return
    
    print(f"\n✅ Generated {len(response.recreated_assets)} images\n")
    
    # Find WebP files
    webp_files = []
    for recreated in response.recreated_assets:
        recreated_url = recreated.get('recreated_url', '')
        if recreated_url and recreated_url.endswith('.webp'):
            # Convert relative path to absolute
            if not recreated_url.startswith('/'):
                recreated_url = os.path.abspath(recreated_url)
            webp_files.append(recreated_url)
    
    if not webp_files:
        # Look for WebP files in output/images
        output_dir = Path('output/images')
        if output_dir.exists():
            webp_files = list(output_dir.glob('*.webp'))
            webp_files = [str(f) for f in webp_files[:5]]  # Limit to 5
    
    if webp_files:
        print(f"📸 Found {len(webp_files)} WebP images:")
        for img in webp_files:
            print(f"   • {img}")
        
        print("\n🖼️  Opening in Preview...")
        
        # Open all images in Preview
        for img_path in webp_files:
            if os.path.exists(img_path):
                try:
                    subprocess.run(['open', '-a', 'Preview', img_path], check=True)
                    print(f"   ✅ Opened: {os.path.basename(img_path)}")
                except Exception as e:
                    print(f"   ❌ Failed to open {img_path}: {e}")
        
        print("\n✅ Images opened in Preview!")
    else:
        print("⚠️  No WebP images found")
        print("   Check output/images/ directory")

if __name__ == "__main__":
    asyncio.run(generate_and_show_images())

