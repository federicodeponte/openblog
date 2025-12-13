#!/usr/bin/env python3
"""
Beautiful Chart using Plotly

Plotly is known for beautiful, interactive charts.
Used by many major companies.
"""

import asyncio
import subprocess
from pathlib import Path
from playwright.async_api import async_playwright
from PIL import Image
import io
import json

async def create_plotly_chart():
    """Create a beautiful chart using Plotly."""
    print("📊 Creating beautiful chart with Plotly...\n")
    
    data = [
        {"label": "<3 months", "value": 35},
        {"label": "9-12+ months", "value": 13}
    ]
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {{
            margin: 0;
            padding: 24px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: white;
        }}
        .container {{
            width: 1200px;
            border: 1px solid #e4e4e7;
            border-radius: 8px;
            padding: 24px;
            background: white;
        }}
        .title {{
            font-size: 15px;
            font-weight: 600;
            color: #09090b;
            margin-bottom: 24px;
            line-height: 1.5;
        }}
        .source {{
            font-size: 11px;
            color: #a1a1aa;
            text-align: right;
            margin-top: 16px;
            font-style: italic;
        }}
        #chart {{
            width: 100%;
            height: 400px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="title">Your Content Is 3x More Likely to Get Cited If It's Less Than 3 Months Old</div>
        <div id="chart"></div>
        <div class="source">Source: airops Research</div>
    </div>
    
    <script>
        const data = {json.dumps(data)};
        
        const trace = {{
            x: data.map(d => d.label),
            y: data.map(d => d.value),
            type: 'bar',
            marker: {{
                color: ['#9ACD32', '#90EE90'],
                line: {{
                    color: 'white',
                    width: 0
                }}
            }},
            text: data.map(d => d.value + '%'),
            textposition: 'outside',
            textfont: {{
                size: 14,
                color: '#09090b',
                family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
            }}
        }};
        
        const layout = {{
            autosize: true,
            margin: {{
                l: 60,
                r: 20,
                t: 20,
                b: 40
            }},
            xaxis: {{
                showgrid: false,
                showline: false,
                tickfont: {{
                    size: 12,
                    color: '#71717a',
                    family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                }}
            }},
            yaxis: {{
                title: {{
                    text: 'Citation Rate (%)',
                    font: {{
                        size: 12,
                        color: '#71717a',
                        family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                    }}
                }},
                showgrid: true,
                gridcolor: '#e4e4e7',
                gridwidth: 1,
                showline: false,
                tickfont: {{
                    size: 12,
                    color: '#71717a',
                    family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                }},
                range: [0, 40]
            }},
            plot_bgcolor: 'white',
            paper_bgcolor: 'white',
            showlegend: false,
            hovermode: false
        }};
        
        const config = {{
            displayModeBar: false,
            responsive: true
        }};
        
        Plotly.newPlot('chart', [trace], layout, config);
    </script>
</body>
</html>
"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1250, 'height': 650})
        await page.set_content(html)
        
        # Wait for Plotly to render
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(2000)  # Plotly needs time
        
        # Screenshot
        container = await page.query_selector('.container')
        screenshot_bytes = await container.screenshot(type='png')
        
        await browser.close()
    
    # Convert to WebP
    img = Image.open(io.BytesIO(screenshot_bytes))
    webp_buffer = io.BytesIO()
    img.save(webp_buffer, format='WEBP', quality=95)
    
    # Save
    output_file = Path('output/real_charts/citation_statistics_plotly.webp')
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'wb') as f:
        f.write(webp_buffer.getvalue())
    
    file_size = output_file.stat().st_size // 1024
    print(f"✅ Created chart: {output_file.name} ({file_size}KB)")
    print(f"   Using Plotly - beautiful, professional charts!")
    
    # Open in Preview
    subprocess.run(['open', '-a', 'Preview', str(output_file)])
    print(f"\n✅ Opened in Preview!")

if __name__ == "__main__":
    asyncio.run(create_plotly_chart())

