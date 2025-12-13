#!/usr/bin/env python3
"""
Beautiful Chart using Observable Plot

Observable Plot is known for beautiful, modern, professional charts.
Used by The New York Times, Bloomberg, etc.
"""

import asyncio
import subprocess
from pathlib import Path
from playwright.async_api import async_playwright
from PIL import Image
import io
import json

async def create_observable_plot_chart():
    """Create a beautiful chart using Observable Plot."""
    print("📊 Creating beautiful chart with Observable Plot...\n")
    
    html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <script type="module">
        import * as Plot from "https://cdn.jsdelivr.net/npm/@observablehq/plot@0.6/+esm";
        
        const data = [
            {label: "<3 months", value: 35},
            {label: "9-12+ months", value: 13}
        ];
        
        const chart = Plot.plot({
            title: "Your Content Is 3x More Likely to Get Cited If It's Less Than 3 Months Old",
            subtitle: "Source: airops Research",
            width: 1152,
            height: 400,
            marginTop: 60,
            marginBottom: 40,
            marginLeft: 60,
            marginRight: 20,
            color: {
                scheme: "custom",
                domain: ["#9ACD32", "#90EE90"]
            },
            x: {
                label: null,
                tickFormat: d => d
            },
            y: {
                label: "Citation Rate (%)",
                grid: true,
                domain: [0, 40]
            },
            marks: [
                Plot.barY(data, {
                    x: "label",
                    y: "value",
                    fill: (d, i) => i === 0 ? "#9ACD32" : "#90EE90",
                    tip: true
                }),
                Plot.text(data, {
                    x: "label",
                    y: "value",
                    text: d => d.value + "%",
                    dy: -10,
                    fill: "#09090b",
                    fontSize: 14,
                    fontWeight: "600"
                })
            ],
            style: {
                fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                fontSize: 13
            }
        });
        
        document.getElementById("chart").appendChild(chart);
    </script>
    <style>
        body {
            margin: 0;
            padding: 24px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: white;
        }
        .container {
            width: 1200px;
            border: 1px solid #e4e4e7;
            border-radius: 8px;
            padding: 24px;
            background: white;
        }
        #chart {
            width: 100%;
            height: 500px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div id="chart"></div>
    </div>
</body>
</html>
"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1250, 'height': 650})
        await page.set_content(html)
        
        # Wait for Observable Plot to render
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(3000)  # Observable Plot needs time
        
        # Screenshot
        container = await page.query_selector('.container')
        screenshot_bytes = await container.screenshot(type='png')
        
        await browser.close()
    
    # Convert to WebP
    img = Image.open(io.BytesIO(screenshot_bytes))
    webp_buffer = io.BytesIO()
    img.save(webp_buffer, format='WEBP', quality=95)
    
    # Save
    output_file = Path('output/real_charts/citation_statistics_observable.webp')
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'wb') as f:
        f.write(webp_buffer.getvalue())
    
    file_size = output_file.stat().st_size // 1024
    print(f"✅ Created chart: {output_file.name} ({file_size}KB)")
    print(f"   Using Observable Plot - beautiful, modern charts!")
    
    # Open in Preview
    subprocess.run(['open', '-a', 'Preview', str(output_file)])
    print(f"\n✅ Opened in Preview!")

if __name__ == "__main__":
    asyncio.run(create_observable_plot_chart())

