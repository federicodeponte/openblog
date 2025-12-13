#!/usr/bin/env python3
"""
Create Shadcn-Level Beautiful Chart

Creates a chart with exact shadcn/ui styling using React/recharts + Playwright.
"""

import os
import subprocess
from pathlib import Path

from pipeline.agents.shadcn_chart_generator import ShadcnChartGenerator, ChartData

def create_shadcn_chart():
    """Create shadcn-level beautiful chart."""
    print("📊 Creating shadcn/ui-level beautiful chart...\n")
    
    generator = ShadcnChartGenerator()
    
    if not generator.playwright_available:
        print("❌ Playwright not available")
        print("   Install with: pip install playwright && playwright install chromium")
        return
    
    # Chart data (like the example)
    chart_data = ChartData(
        title="Your Content Is 3x More Likely to Get Cited If It's Less Than 3 Months Old",
        bars=[
            {"label": "<3 months", "value": 35, "color": "#9ACD32"},  # Light yellow-green
            {"label": "9-12+ months", "value": 13, "color": "#90EE90"}  # Light mint green
        ],
        y_axis_label="Citation Rate",
        source="airops Research"
    )
    
    # Create output directory
    charts_dir = Path('output/real_charts')
    charts_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = charts_dir / "citation_statistics_shadcn.webp"
    
    # Generate chart
    print("🎨 Generating chart with React/recharts + shadcn styling...")
    import asyncio
    image_bytes = asyncio.run(generator.create_bar_chart(
        chart_data,
        output_path=str(output_file),
        width=1200,
        height=630,
        theme="light"
    ))
    
    if image_bytes:
        file_size = output_file.stat().st_size // 1024
        print(f"✅ Created shadcn-level chart: {output_file.name} ({file_size}KB)")
        print(f"   Title: {chart_data.title}")
        print(f"   Data: {chart_data.bars[0]['label']} = {chart_data.bars[0]['value']}%, {chart_data.bars[1]['label']} = {chart_data.bars[1]['value']}%")
        
        # Open in Preview
        try:
            subprocess.run(['open', '-a', 'Preview', str(output_file)], check=True)
            print(f"\n✅ Opened in Preview!")
            print(f"   This chart uses React/recharts with shadcn/ui styling!")
            print(f"   Professional, modern, web-native look!")
        except Exception as e:
            print(f"⚠️  Failed to open: {e}")
    else:
        print("❌ Chart generation failed")

if __name__ == "__main__":
    create_shadcn_chart()

