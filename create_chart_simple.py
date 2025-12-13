#!/usr/bin/env python3
"""
Simple Chart Generator using Chart.js

Uses Chart.js (simple, reliable, widely used) + Playwright.
No React complexity - just works!
"""

import asyncio
import subprocess
from pathlib import Path
from playwright.async_api import async_playwright
from PIL import Image
import io

async def create_simple_chart():
    """Create a chart using Chart.js - simple and reliable."""
    print("📊 Creating chart with Chart.js (simple & reliable)...\n")
    
    html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
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
        h2 {
            font-size: 15px;
            font-weight: 600;
            color: #09090b;
            margin-bottom: 24px;
            line-height: 1.5;
        }
        .source {
            font-size: 11px;
            color: #a1a1aa;
            text-align: right;
            margin-top: 16px;
            font-style: italic;
        }
        canvas {
            max-height: 400px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>Your Content Is 3x More Likely to Get Cited If It's Less Than 3 Months Old</h2>
        <canvas id="myChart"></canvas>
        <div class="source">Source: airops Research</div>
    </div>
    
    <script>
        const ctx = document.getElementById('myChart');
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['<3 months', '9-12+ months'],
                datasets: [{
                    label: 'Citation Rate',
                    data: [35, 13],
                    backgroundColor: ['#9ACD32', '#90EE90'],
                    borderRadius: 4,
                    borderSkipped: false,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: '#ffffff',
                        titleColor: '#09090b',
                        bodyColor: '#71717a',
                        borderColor: '#e4e4e7',
                        borderWidth: 1,
                        padding: 12,
                        displayColors: false,
                        callbacks: {
                            label: function(context) {
                                return 'Citation Rate: ' + context.parsed.y + '%';
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 40,
                        ticks: {
                            color: '#71717a',
                            font: {
                                size: 12
                            }
                        },
                        grid: {
                            color: '#e4e4e7',
                            drawBorder: false
                        }
                    },
                    x: {
                        ticks: {
                            color: '#71717a',
                            font: {
                                size: 12
                            }
                        },
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    </script>
</body>
</html>
"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1250, 'height': 650})
        await page.set_content(html)
        
        # Wait for Chart.js to render
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(2000)  # Chart.js needs time to render
        
        # Screenshot
        container = await page.query_selector('.container')
        screenshot_bytes = await container.screenshot(type='png')
        
        await browser.close()
    
    # Convert to WebP
    img = Image.open(io.BytesIO(screenshot_bytes))
    webp_buffer = io.BytesIO()
    img.save(webp_buffer, format='WEBP', quality=95)
    
    # Save
    output_file = Path('output/real_charts/citation_statistics_chartjs.webp')
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'wb') as f:
        f.write(webp_buffer.getvalue())
    
    file_size = output_file.stat().st_size // 1024
    print(f"✅ Created chart: {output_file.name} ({file_size}KB)")
    print(f"   Using Chart.js - simple, reliable, widely used!")
    
    # Open in Preview
    subprocess.run(['open', '-a', 'Preview', str(output_file)])
    print(f"\n✅ Opened in Preview!")
    print(f"   This should actually work! 🎉")

if __name__ == "__main__":
    asyncio.run(create_simple_chart())

