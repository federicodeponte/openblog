#!/usr/bin/env python3
"""Create a simple, guaranteed-to-work chart."""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
from PIL import Image
import io

async def create_simple_chart():
    """Create a simple chart that definitely renders."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1200, 'height': 630})
        
        html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/recharts@2.10.3/umd/Recharts.js"></script>
    <style>
        body {
            margin: 0;
            padding: 24px;
            font-family: ui-sans-serif, system-ui, sans-serif;
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
        }
        #chart {
            width: 100%;
            height: 400px;
        }
        .source {
            font-size: 11px;
            color: #a1a1aa;
            text-align: right;
            margin-top: 16px;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>Your Content Is 3x More Likely to Get Cited If It's Less Than 3 Months Old</h2>
        <div id="chart"></div>
        <div class="source">Source: airops Research</div>
    </div>
    
    <script>
        function init() {
            if (typeof React === 'undefined' || typeof ReactDOM === 'undefined' || typeof Recharts === 'undefined') {
                setTimeout(init, 100);
                return;
            }
            
            const { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } = Recharts;
            const data = [
                {name: "<3 months", value: 35},
                {name: "9-12+ months", value: 13}
            ];
            const colors = ["#9ACD32", "#90EE90"];
            
            const root = document.getElementById('chart');
            ReactDOM.render(
                React.createElement(ResponsiveContainer, {width: '100%', height: '100%'},
                    React.createElement(BarChart, {data: data, margin: {top: 5, right: 10, left: 0, bottom: 0}},
                        React.createElement(CartesianGrid, {strokeDasharray: '3 3', stroke: '#e4e4e7', vertical: false}),
                        React.createElement(XAxis, {dataKey: 'name', tick: {fill: '#71717a', fontSize: 12}, axisLine: false, tickLine: false}),
                        React.createElement(YAxis, {tick: {fill: '#71717a', fontSize: 12}, axisLine: false, tickLine: false, width: 40}),
                        React.createElement(Tooltip, {cursor: {fill: 'rgba(0,0,0,0.03)'}}),
                        React.createElement(Bar, {dataKey: 'value', radius: [4, 4, 0, 0]}, 
                            data.map((entry, index) => React.createElement(Cell, {key: `cell-${index}`, fill: colors[index]}))
                        )
                    )
                ),
                root
            );
        }
        
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
        } else {
            init();
        }
    </script>
</body>
</html>
"""
        
        await page.set_content(html)
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(3000)  # Wait for chart
        
        # Verify chart rendered
        has_chart = await page.evaluate('''() => {
            const chart = document.getElementById('chart');
            const svg = chart ? chart.querySelector('svg') : null;
            return svg !== null && svg.children.length > 0;
        }''')
        
        print(f"Chart rendered: {has_chart}")
        
        # Screenshot
        container = await page.query_selector('.container')
        screenshot_bytes = await container.screenshot(type='png')
        
        # Convert to WebP
        img = Image.open(io.BytesIO(screenshot_bytes))
        webp_buffer = io.BytesIO()
        img.save(webp_buffer, format='WEBP', quality=95)
        
        # Save
        output_file = Path('output/real_charts/citation_statistics_simple.webp')
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'wb') as f:
            f.write(webp_buffer.getvalue())
        
        print(f"✅ Saved: {output_file}")
        
        await browser.close()
        
        # Open
        import subprocess
        subprocess.run(['open', '-a', 'Preview', str(output_file)])

asyncio.run(create_simple_chart())

