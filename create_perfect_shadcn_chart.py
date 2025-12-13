#!/usr/bin/env python3
"""
Create Perfect Shadcn-Level Chart

Uses exact shadcn/ui chart styling with React/recharts.
Matches the look and feel of shadcn/ui charts exactly.
"""

import os
import subprocess
import json
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def create_perfect_shadcn_chart():
    """Create a perfect shadcn/ui-level chart."""
    print("📊 Creating perfect shadcn/ui-level chart...\n")
    
    # Chart data
    title = "Your Content Is 3x More Likely to Get Cited If It's Less Than 3 Months Old"
    data = [
        {"name": "<3 months", "value": 35},
        {"name": "9-12+ months", "value": 13}
    ]
    colors = ["#9ACD32", "#90EE90"]
    y_axis_label = "Citation Rate"
    source = "airops Research"
    
    # Perfect shadcn/ui HTML with exact styling
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script crossorigin src="https://unpkg.com/react@18/umd/react.development.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
    <script src="https://unpkg.com/recharts@2.10.3/umd/Recharts.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif;
            background: #ffffff;
            padding: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
        }}
        .chart-wrapper {{
            width: 1200px;
            background: #ffffff;
            border: 1px solid #e4e4e7;
            border-radius: 8px;
            padding: 24px;
        }}
        .chart-header {{
            margin-bottom: 24px;
        }}
        .chart-title {{
            font-size: 15px;
            font-weight: 600;
            color: #09090b;
            line-height: 1.5;
            margin-bottom: 4px;
        }}
        .chart-description {{
            font-size: 13px;
            color: #71717a;
            margin-top: 4px;
        }}
        .chart-content {{
            height: 400px;
            width: 100%;
        }}
        .chart-footer {{
            margin-top: 16px;
            text-align: right;
        }}
        .chart-source {{
            font-size: 11px;
            color: #a1a1aa;
            font-style: italic;
        }}
    </style>
</head>
<body>
    <div class="chart-wrapper">
        <div class="chart-header">
            <h3 class="chart-title">{title}</h3>
        </div>
        <div id="chart" class="chart-content"></div>
        <div class="chart-footer">
            <span class="chart-source">Source: {source}</span>
        </div>
    </div>
    
    <script>
        const {{ BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell }} = Recharts;
        
        const chartData = {json.dumps(data)};
        const chartColors = {json.dumps(colors)};
        
        const CustomTooltip = {{ active, payload }} => {{
            if (active && payload && payload.length) {{
                return React.createElement('div', {{
                    className: 'tooltip',
                    style: {{
                        backgroundColor: '#ffffff',
                        border: '1px solid #e4e4e7',
                        borderRadius: '6px',
                        padding: '8px 12px',
                        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
                        fontSize: '13px'
                    }}
                }}, [
                    React.createElement('div', {{
                        style: {{ fontWeight: 500, color: '#09090b', marginBottom: '4px' }}
                    }}, payload[0].payload.name),
                    React.createElement('div', {{
                        style: {{ color: '#71717a' }}
                    }}, `{y_axis_label}: ${{payload[0].value}}%`)
                ]);
            }}
            return null;
        }};
        
        ReactDOM.render(
            React.createElement(ResponsiveContainer, {{ width: '100%', height: '100%' }},
                React.createElement(BarChart, {{
                    data: chartData,
                    margin: {{ top: 0, right: 0, left: -20, bottom: 0 }}
                }},
                    React.createElement(CartesianGrid, {{
                        strokeDasharray: '3 3',
                        stroke: '#e4e4e7',
                        vertical: false,
                        strokeOpacity: 0.4
                    }}),
                    React.createElement(XAxis, {{
                        dataKey: 'name',
                        tick: {{
                            fill: '#71717a',
                            fontSize: 12,
                            fontWeight: 400
                        }},
                        axisLine: false,
                        tickLine: false
                    }}),
                    React.createElement(YAxis, {{
                        tick: {{
                            fill: '#71717a',
                            fontSize: 12,
                            fontWeight: 400
                        }},
                        axisLine: false,
                        tickLine: false,
                        width: 40
                    }}),
                    React.createElement(Tooltip, {{
                        content: CustomTooltip,
                        cursor: {{ fill: 'rgba(0, 0, 0, 0.03)' }}
                    }}),
                    React.createElement(Bar, {{
                        dataKey: 'value',
                        radius: [4, 4, 0, 0]
                    }}, chartData.map((entry, index) =>
                        React.createElement(Cell, {{
                            key: `cell-${{index}}`,
                            fill: chartColors[index % chartColors.length]
                        }})
                    ))
                )
            ),
            document.getElementById('chart')
        );
    </script>
</body>
</html>
"""
    
    # Render with Playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1250, 'height': 650})
        await page.set_content(html_content)
        
        # Wait for rendering
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(2000)
        
        # Take screenshot
        chart_element = await page.query_selector('.chart-wrapper')
        screenshot_bytes = await chart_element.screenshot(type='png')
        
        await browser.close()
    
    # Convert to WebP
    from PIL import Image
    import io
    img = Image.open(io.BytesIO(screenshot_bytes))
    webp_buffer = io.BytesIO()
    img.save(webp_buffer, format='WEBP', quality=95)
    webp_bytes = webp_buffer.getvalue()
    
    # Save
    charts_dir = Path('output/real_charts')
    charts_dir.mkdir(parents=True, exist_ok=True)
    output_file = charts_dir / "citation_statistics_perfect_shadcn.webp"
    with open(output_file, 'wb') as f:
        f.write(webp_bytes)
    
    file_size = output_file.stat().st_size // 1024
    print(f"✅ Created perfect shadcn chart: {output_file.name} ({file_size}KB)")
    
    # Open in Preview
    subprocess.run(['open', '-a', 'Preview', str(output_file)], check=True)
    print(f"✅ Opened in Preview!")
    print(f"   Perfect shadcn/ui styling - clean, modern, professional!")

if __name__ == "__main__":
    asyncio.run(create_perfect_shadcn_chart())

