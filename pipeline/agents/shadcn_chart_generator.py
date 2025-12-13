"""
Shadcn-Level Chart Generator

Creates beautiful, modern charts using Playwright + React/recharts with shadcn/ui styling.
Matches the exact look and feel of shadcn/ui charts.
"""

import os
import logging
import json
import asyncio
from typing import Optional, Dict, Any, List
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ChartData:
    """Chart data structure."""
    title: str
    bars: List[Dict[str, Any]]  # [{"label": "...", "value": 35, "color": "#..."}]
    y_axis_label: str = "Value"
    x_axis_label: Optional[str] = None
    source: Optional[str] = None


class ShadcnChartGenerator:
    """
    Generate shadcn/ui-level beautiful charts.
    
    Uses Playwright to render React/recharts with shadcn/ui styling.
    """
    
    def __init__(self):
        """Initialize chart generator."""
        try:
            from playwright.async_api import async_playwright
            self.playwright_available = True
            logger.info("✅ Shadcn chart generator initialized (Playwright available)")
        except ImportError:
            self.playwright_available = False
            logger.warning("⚠️  Playwright not available - install with: pip install playwright && playwright install chromium")
    
    async def create_bar_chart(
        self,
        chart_data: ChartData,
        output_path: Optional[str] = None,
        width: int = 1200,
        height: int = 630,
        theme: str = "light"  # light or dark
    ) -> Optional[bytes]:
        """
        Create a shadcn/ui-level bar chart.
        
        Args:
            chart_data: Chart data structure
            output_path: Optional path to save WebP file
            width: Image width in pixels
            height: Image height in pixels
            theme: Chart theme (light or dark)
            
        Returns:
            Image bytes (WebP format) or None if failed
        """
        if not self.playwright_available:
            logger.error("Playwright not available")
            return None
        
        try:
            from playwright.async_api import async_playwright
            
            # Prepare data
            labels = [bar["label"] for bar in chart_data.bars]
            values = [bar["value"] for bar in chart_data.bars]
            colors = [bar.get("color", "#3b82f6") for bar in chart_data.bars]
            
            # Build HTML with React/recharts + shadcn styling
            html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chart</title>
    <script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/recharts@2.10.3/umd/Recharts.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif;
            background: {'#ffffff' if theme == 'light' else '#0a0a0a'};
            padding: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
        }}
        .chart-container {{
            width: {width}px;
            background: {'#ffffff' if theme == 'light' else '#18181b'};
            border: {'1px solid #e4e4e7' if theme == 'light' else '1px solid #27272a'};
            border-radius: 8px;
            padding: 24px;
        }}
        .chart-title {{
            font-size: 15px;
            font-weight: 600;
            color: {'#09090b' if theme == 'light' else '#fafafa'};
            line-height: 1.5;
            margin-bottom: 24px;
        }}
        #chart-root {{
            width: 100%;
            height: 400px;
        }}
        .chart-source {{
            font-size: 12px;
            color: {'#71717a' if theme == 'light' else '#a1a1aa'};
            text-align: right;
            margin-top: 16px;
            font-style: italic;
        }}
    </style>
</head>
<body>
    <div class="chart-container">
        <h2 class="chart-title">{chart_data.title}</h2>
        <div id="chart-root"></div>
        {f'<p class="chart-source">Source: {chart_data.source}</p>' if chart_data.source else ''}
    </div>
    
    <script>
        // Track errors
        window.errors = [];
        window.addEventListener('error', function(e) {{
            window.errors.push(e.message);
            console.error('Error:', e.message);
        }});
        
        function renderChart() {{
            // Wait for all libraries to load
            if (typeof React === 'undefined' || typeof ReactDOM === 'undefined' || typeof Recharts === 'undefined') {{
                setTimeout(renderChart, 200);
                return;
            }}
            
            console.log('All libraries loaded, rendering chart...');
            
            try {{
                const {{ BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell }} = Recharts;
                
                const data = {json.dumps([{"name": label, "value": value} for label, value in zip(labels, values)])};
                const colors = {json.dumps(colors)};
                
                const CustomTooltip = {{ active, payload }} => {{
                    if (active && payload && payload.length) {{
                        return React.createElement('div', {{
                            style: {{
                                backgroundColor: '{'#ffffff' if theme == 'light' else '#18181b'}',
                                border: '1px solid {'#e4e4e7' if theme == 'light' else '#27272a'}',
                                borderRadius: '6px',
                                padding: '8px 12px',
                                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
                                fontSize: '13px'
                            }}
                        }}, [
                            React.createElement('div', {{
                                style: {{
                                    fontWeight: 500,
                                    color: '{'#09090b' if theme == 'light' else '#fafafa'}',
                                    marginBottom: '4px'
                                }}
                            }}, payload[0].payload.name),
                            React.createElement('div', {{
                                style: {{
                                    color: '{'#71717a' if theme == 'light' else '#a1a1aa'}'
                                }}
                            }}, `{chart_data.y_axis_label}: ${{payload[0].value}}%`)
                        ]);
                    }}
                    return null;
                }};
                
                const root = document.getElementById('chart-root');
                if (!root) {{
                    console.error('Chart root not found');
                    return;
                }}
                
                ReactDOM.render(
                    React.createElement(ResponsiveContainer, {{width: '100%', height: '400px'}},
                        React.createElement(BarChart, {{
                            data: data,
                            margin: {{ top: 5, right: 10, left: 0, bottom: 0 }},
                            barCategoryGap: '25%'
                        }},
                            React.createElement(CartesianGrid, {{
                                strokeDasharray: '3 3',
                                stroke: '{'#e4e4e7' if theme == 'light' else '#27272a'}',
                                vertical: false,
                                strokeOpacity: 0.4
                            }}),
                            React.createElement(XAxis, {{
                                dataKey: 'name',
                                tick: {{
                                    fill: '{'#71717a' if theme == 'light' else '#a1a1aa'}',
                                    fontSize: 12,
                                    fontWeight: 400
                                }},
                                axisLine: false,
                                tickLine: false
                            }}),
                            React.createElement(YAxis, {{
                                tick: {{
                                    fill: '{'#71717a' if theme == 'light' else '#a1a1aa'}',
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
                                radius: [4, 4, 0, 0],
                                fill: colors[0],
                                animationDuration: 0
                            }}, data.map((entry, index) => 
                                React.createElement(Cell, {{ 
                                    key: `cell-${{index}}`, 
                                    fill: colors[index % colors.length]
                                }})
                            ))
                        )
                    ),
                    root
                );
            }} catch (error) {{
                console.error('Chart rendering error:', error);
            }}
        }}
        
        // Start rendering when page loads
        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', renderChart);
        }} else {{
            renderChart();
        }}
    </script>
</body>
</html>
"""
            
            # Render with Playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(viewport={'width': width + 80, 'height': height + 80})
                await page.set_content(html_content)
                
                # Wait for scripts to load
                await page.wait_for_load_state('networkidle')
                
                # Wait for chart to render (check multiple times)
                for i in range(10):
                    await page.wait_for_timeout(500)
                    chart_rendered = await page.evaluate('''() => {
                        const root = document.getElementById('chart-root');
                        if (!root) return false;
                        // Check if React rendered something
                        return root.children.length > 0 || root.innerHTML.trim().length > 0;
                    }''')
                    if chart_rendered:
                        logger.info(f"Chart rendered after {i+1} attempts")
                        break
                    if i == 9:
                        logger.warning("Chart may not have rendered properly")
                
                # Final wait for smooth rendering
                await page.wait_for_timeout(500)
                
                # Take screenshot of chart container (PNG, then convert to WebP)
                chart_element = await page.query_selector('.chart-container')
                screenshot_bytes = await chart_element.screenshot(
                    type='png'
                )
                
                # Convert PNG to WebP using PIL
                try:
                    from PIL import Image
                    import io
                    img = Image.open(io.BytesIO(screenshot_bytes))
                    webp_buffer = io.BytesIO()
                    img.save(webp_buffer, format='WEBP', quality=95)
                    screenshot_bytes = webp_buffer.getvalue()
                except Exception as e:
                    logger.warning(f"WebP conversion failed, using PNG: {e}")
                
                await browser.close()
                
                # Save if path provided
                if output_path:
                    output_file = Path(output_path)
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_file, 'wb') as f:
                        f.write(screenshot_bytes)
                    logger.info(f"✅ Shadcn chart saved: {output_file}")
                
                return screenshot_bytes
                
        except Exception as e:
            logger.error(f"Shadcn chart generation failed: {e}", exc_info=True)
            return None
    
    def create_chart_from_data(
        self,
        title: str,
        data: Dict[str, float],
        colors: Optional[Dict[str, str]] = None,
        y_axis_label: str = "Value",
        source: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> Optional[bytes]:
        """
        Convenience method to create chart from simple data dict.
        
        Returns:
            Image bytes (WebP) or None
        """
        bars = []
        default_colors = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"]
        
        for i, (label, value) in enumerate(data.items()):
            color = colors.get(label) if colors else default_colors[i % len(default_colors)]
            bars.append({
                "label": label,
                "value": value,
                "color": color
            })
        
        chart_data = ChartData(
            title=title,
            bars=bars,
            y_axis_label=y_axis_label,
            source=source
        )
        
        # Run async function
        return asyncio.run(self.create_bar_chart(chart_data, output_path=output_path))

