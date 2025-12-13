#!/usr/bin/env python3
"""
Create Statistics Chart with Gemini Imagen

Uses Gemini Imagen 4.0 to generate a beautiful statistics chart directly.
"""

import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

from pipeline.models.google_imagen_client import GoogleImagenClient

def create_chart_with_gemini():
    """Create a statistics chart using Gemini Imagen."""
    print("📊 Creating statistics chart with Gemini Imagen 4.0...\n")
    
    # Check API key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ GEMINI_API_KEY not found in .env.local")
        return
    
    # Set environment variable for client
    os.environ['GEMINI_API_KEY'] = api_key
    
    # Initialize client (uses env var)
    client = GoogleImagenClient()
    
    # Create detailed prompt for a statistics chart
    prompt = """Create a professional statistics bar chart showing citation rates.

Chart Title: "Your Content Is 3x More Likely to Get Cited If It's Less Than 3 Months Old"

Data:
- "<3 months": 35% (bar should be taller)
- "9-12+ months": 13% (bar should be shorter)

Style Requirements:
- Modern, clean design similar to shadcn/ui charts
- White background
- Two vertical bars side by side
- First bar: light yellow-green color (#9ACD32)
- Second bar: light mint green color (#90EE90)
- Include axis labels: "Citation Rate" on Y-axis
- Include data labels showing percentages on top of bars
- Clean typography, professional look
- Subtle grid lines
- Rounded bar corners
- Source attribution at bottom: "Source: airops Research"

Make it look like a professional web-based statistics chart, not a hand-drawn sketch."""
    
    print("🎨 Generating chart with Gemini Imagen...")
    print(f"   Prompt length: {len(prompt)} characters\n")
    
    try:
        # Generate image
        image_url = client.generate_image(
            prompt=prompt,
            project_folder_id=None  # Don't upload to Drive, just get URL
        )
        
        if image_url:
            print(f"✅ Chart generated successfully!")
            print(f"   Path: {image_url}")
            
            # Check if it's a local file path
            if image_url.startswith('output/') or image_url.startswith('./'):
                # Already saved locally, just copy to charts directory
                source_file = Path(image_url)
                if source_file.exists():
                    output_dir = Path('output/real_charts')
                    output_dir.mkdir(parents=True, exist_ok=True)
                    output_file = output_dir / "citation_statistics_gemini.webp"
                    
                    # Copy file
                    import shutil
                    shutil.copy2(source_file, output_file)
                    
                    file_size = output_file.stat().st_size // 1024
                    print(f"✅ Saved: {output_file.name} ({file_size}KB)")
                    
                    # Open in Preview
                    try:
                        subprocess.run(['open', '-a', 'Preview', str(output_file)], check=True)
                        print(f"\n✅ Opened in Preview!")
                        print(f"   Chart created with Gemini Imagen 4.0!")
                    except Exception as e:
                        print(f"⚠️  Failed to open: {e}")
                else:
                    print(f"❌ Source file not found: {source_file}")
            else:
                # It's a URL, download it
                import httpx
                response = httpx.get(image_url, timeout=30.0)
                response.raise_for_status()
                
                output_dir = Path('output/real_charts')
                output_dir.mkdir(parents=True, exist_ok=True)
                output_file = output_dir / "citation_statistics_gemini.webp"
                
                with open(output_file, 'wb') as f:
                    f.write(response.content)
                
                file_size = output_file.stat().st_size // 1024
                print(f"✅ Saved: {output_file.name} ({file_size}KB)")
                
                # Open in Preview
                try:
                    subprocess.run(['open', '-a', 'Preview', str(output_file)], check=True)
                    print(f"\n✅ Opened in Preview!")
                    print(f"   Chart created with Gemini Imagen 4.0!")
                except Exception as e:
                    print(f"⚠️  Failed to open: {e}")
        else:
            print("❌ Failed to generate chart")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_chart_with_gemini()

