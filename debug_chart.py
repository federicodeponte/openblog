#!/usr/bin/env python3
"""Debug chart rendering issue."""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

async def debug_chart():
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
</head>
<body>
    <div id="chart"></div>
    <script>
        console.log('React:', typeof React);
        console.log('ReactDOM:', typeof ReactDOM);
        console.log('Recharts:', typeof Recharts);
        
        const { BarChart, Bar, XAxis, YAxis, ResponsiveContainer } = Recharts;
        const data = [{name: "A", value: 35}, {name: "B", value: 13}];
        
        ReactDOM.render(
            React.createElement(ResponsiveContainer, {width: '100%', height: 400},
                React.createElement(BarChart, {data: data},
                    React.createElement(XAxis, {dataKey: 'name'}),
                    React.createElement(YAxis),
                    React.createElement(Bar, {dataKey: 'value', fill: '#3b82f6'})
                )
            ),
            document.getElementById('chart')
        );
    </script>
</body>
</html>
"""
        await page.set_content(html)
        await page.wait_for_timeout(5000)
        
        # Check console
        console_msgs = await page.evaluate('() => { return window.console.logs || []; }')
        print("Console messages:", console_msgs)
        
        # Check if chart rendered
        chart_rendered = await page.evaluate('''() => {
            const chart = document.getElementById('chart');
            return chart && chart.children.length > 0;
        }''')
        print(f"Chart rendered: {chart_rendered}")
        
        # Take screenshot
        await page.screenshot(path='debug_chart.png')
        print("Screenshot saved to debug_chart.png")
        
        await browser.close()

asyncio.run(debug_chart())

