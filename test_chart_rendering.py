#!/usr/bin/env python3
"""Test chart rendering to debug empty page issue."""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

async def test_chart():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Show browser
        page = await browser.new_page()
        
        html = """
<!DOCTYPE html>
<html>
<head>
    <script crossorigin src="https://unpkg.com/react@18/umd/react.development.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/recharts@2.10.3/umd/Recharts.js"></script>
    <style>
        body { padding: 20px; font-family: system-ui; }
        #chart { width: 100%; height: 400px; border: 1px solid #ccc; }
    </style>
</head>
<body>
    <h1>Chart Test</h1>
    <div id="chart"></div>
    <script>
        function renderChart() {
            if (typeof React === 'undefined' || typeof ReactDOM === 'undefined' || typeof Recharts === 'undefined') {
                console.log('Waiting for libraries...');
                setTimeout(renderChart, 100);
                return;
            }
            
            console.log('Libraries loaded, rendering...');
            const { BarChart, Bar, XAxis, YAxis, ResponsiveContainer } = Recharts;
            const data = [{name: "<3 months", value: 35}, {name: "9-12+ months", value: 13}];
            
            const root = document.getElementById('chart');
            ReactDOM.render(
                React.createElement(ResponsiveContainer, {width: '100%', height: 400},
                    React.createElement(BarChart, {data: data},
                        React.createElement(XAxis, {dataKey: 'name'}),
                        React.createElement(YAxis),
                        React.createElement(Bar, {dataKey: 'value', fill: '#3b82f6'})
                    )
                ),
                root
            );
            console.log('Chart rendered!');
        }
        
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', renderChart);
        } else {
            renderChart();
        }
    </script>
</body>
</html>
"""
        await page.set_content(html)
        
        # Wait and check console
        await page.wait_for_timeout(5000)
        
        # Get console logs
        console_logs = []
        page.on("console", lambda msg: console_logs.append(msg.text))
        
        # Check if chart rendered
        chart_exists = await page.evaluate('''() => {
            const chart = document.getElementById('chart');
            return chart && chart.children.length > 0;
        }''')
        
        print(f"Chart rendered: {chart_exists}")
        print(f"Console logs: {console_logs}")
        
        # Screenshot
        await page.screenshot(path='test_chart_debug.png', full_page=True)
        print("Screenshot saved to test_chart_debug.png")
        
        input("Press Enter to close browser...")
        await browser.close()

asyncio.run(test_chart())

