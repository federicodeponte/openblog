#!/usr/bin/env python3
"""
Beautiful Chart using Datawrapper API

Datawrapper is used by The New York Times, Bloomberg, etc.
Known for beautiful, professional charts.
"""

import httpx
import subprocess
from pathlib import Path
from PIL import Image
import io

def create_datawrapper_chart():
    """Create a chart using Datawrapper API (if available) or QuickChart fallback."""
    print("📊 Creating beautiful chart...\n")
    
    # Try QuickChart.io (free, simple API)
    # Datawrapper requires account, so using QuickChart as it's also beautiful
    
    chart_config = {
        "type": "bar",
        "data": {
            "labels": ["<3 months", "9-12+ months"],
            "datasets": [{
                "label": "Citation Rate",
                "data": [35, 13],
                "backgroundColor": ["#9ACD32", "#90EE90"],
                "borderRadius": 6,
                "borderSkipped": False
            }]
        },
        "options": {
            "plugins": {
                "legend": {"display": False},
                "title": {
                    "display": True,
                    "text": "Your Content Is 3x More Likely to Get Cited If It's Less Than 3 Months Old",
                    "font": {"size": 16, "weight": "600"},
                    "color": "#09090b",
                    "padding": {"bottom": 20}
                },
                "datalabels": {
                    "anchor": "end",
                    "align": "top",
                    "formatter": (value) => value + "%",
                    "font": {"size": 12, "weight": "600"},
                    "color": "#09090b"
                }
            },
            "scales": {
                "y": {
                    "beginAtZero": True,
                    "max": 40,
                    "ticks": {
                        "color": "#71717a",
                        "font": {"size": 12}
                    },
                    "grid": {
                        "color": "#e4e4e7",
                        "drawBorder": False
                    }
                },
                "x": {
                    "ticks": {
                        "color": "#71717a",
                        "font": {"size": 12}
                    },
                    "grid": {"display": False}
                }
            },
            "layout": {
                "padding": {"top": 20, "bottom": 20}
            }
        }
    }
    
    import json
    import urllib.parse
    
    # QuickChart.io API
    chart_json = json.dumps(chart_config)
    encoded = urllib.parse.quote(chart_json)
    url = f"https://quickchart.io/chart?c={encoded}&width=1200&height=500&format=png"
    
    print("📥 Downloading chart from QuickChart.io...")
    
    try:
        response = httpx.get(url, timeout=30.0)
        response.raise_for_status()
        
        # Convert to WebP
        img = Image.open(io.BytesIO(response.content))
        webp_buffer = io.BytesIO()
        img.save(webp_buffer, format='WEBP', quality=95)
        
        # Save
        output_file = Path('output/real_charts/citation_statistics_quickchart.webp')
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'wb') as f:
            f.write(webp_buffer.getvalue())
        
        file_size = output_file.stat().st_size // 1024
        print(f"✅ Created chart: {output_file.name} ({file_size}KB)")
        print(f"   Using QuickChart.io - beautiful, professional charts!")
        
        # Open in Preview
        subprocess.run(['open', '-a', 'Preview', str(output_file)])
        print(f"\n✅ Opened in Preview!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    create_datawrapper_chart()

