#!/usr/bin/env python3
"""
Create Real Statistics Chart as WebP

Creates a statistics chart similar to the citation example using GraphicsGenerator,
then saves as WebP and opens in Preview.
"""

import os
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import io

def create_citation_statistics_chart():
    """Create a citation statistics chart like the example."""
    print("📊 Creating citation statistics chart...\n")
    
    # Chart data (like the example: 3x more citations for content <3 months old)
    data = {
        "title": "Your Content Is 3x More Likely to Get Cited If It's Less Than 3 Months Old",
        "bars": [
            {"label": "<3 months", "value": 35, "color": "#9ACD32"},  # Light yellow-green
            {"label": "9-12+ months", "value": 13, "color": "#90EE90"}  # Light mint green
        ],
        "y_axis_label": "Citation Rate",
        "source": "airops Research"
    }
    
    # Create image
    width, height = 800, 600
    img = Image.new('RGB', (width, height), color='#F0F8F0')  # Very light green background
    draw = ImageDraw.Draw(img)
    
    # Try to use a font, fallback to default
    try:
        title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
        label_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
        small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
    except:
        title_font = ImageFont.load_default()
        label_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # Draw title
    title_y = 20
    draw.text((width // 2, title_y), data["title"], fill='#2F4F2F', font=title_font, anchor='mm')
    
    # Chart area
    chart_x = 100
    chart_y = 100
    chart_width = width - 200
    chart_height = height - 200
    
    # Draw Y-axis label
    draw.text((30, chart_y + chart_height // 2), data["y_axis_label"], fill='#2F4F2F', font=label_font, anchor='mm')
    draw.text((30, chart_y + chart_height // 2), data["y_axis_label"], fill='#2F4F2F', font=label_font, anchor='mm')
    
    # Calculate bar dimensions
    max_value = max(bar["value"] for bar in data["bars"])
    bar_width = chart_width // (len(data["bars"]) * 2)
    bar_spacing = bar_width
    
    # Draw bars
    for i, bar in enumerate(data["bars"]):
        bar_height = int((bar["value"] / max_value) * chart_height * 0.8)
        bar_x = chart_x + i * (bar_width + bar_spacing) + bar_spacing // 2
        bar_y = chart_y + chart_height - bar_height
        
        # Draw bar with rounded corners effect
        draw.rectangle(
            [bar_x, bar_y, bar_x + bar_width, chart_y + chart_height],
            fill=bar["color"],
            outline='#2F4F2F',
            width=2
        )
        
        # Draw value label on bar
        value_text = f"{bar['value']}%"
        draw.text(
            (bar_x + bar_width // 2, bar_y - 20),
            value_text,
            fill='#2F4F2F',
            font=label_font,
            anchor='mm'
        )
        
        # Draw X-axis label
        draw.text(
            (bar_x + bar_width // 2, chart_y + chart_height + 30),
            bar["label"],
            fill='#2F4F2F',
            font=small_font,
            anchor='mm'
        )
    
    # Draw border
    draw.rectangle(
        [chart_x - 10, chart_y - 10, chart_x + chart_width + 10, chart_y + chart_height + 10],
        outline='#2F4F2F',
        width=2
    )
    
    # Draw source
    source_text = f"Source: {data['source']}"
    draw.text(
        (width - 20, height - 30),
        source_text,
        fill='#2F4F2F',
        font=small_font,
        anchor='rm'
    )
    
    # Save as WebP
    charts_dir = Path('output/real_charts')
    charts_dir.mkdir(parents=True, exist_ok=True)
    
    webp_file = charts_dir / "citation_statistics_chart.webp"
    img.save(webp_file, 'WEBP', quality=90)
    
    file_size = webp_file.stat().st_size // 1024
    print(f"✅ Created statistics chart: {webp_file.name} ({file_size}KB)")
    print(f"   Title: {data['title']}")
    print(f"   Data: {data['bars'][0]['label']} = {data['bars'][0]['value']}%, {data['bars'][1]['label']} = {data['bars'][1]['value']}%")
    
    # Open in Preview
    try:
        subprocess.run(['open', '-a', 'Preview', str(webp_file)], check=True)
        print(f"\n✅ Opened in Preview!")
    except Exception as e:
        print(f"⚠️  Failed to open: {e}")
    
    return str(webp_file)

if __name__ == "__main__":
    create_citation_statistics_chart()

