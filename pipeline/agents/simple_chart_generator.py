"""
Simple Chart Generator using Chart.js

Simple, reliable chart generation using Chart.js (most popular chart library).
No React complexity - just works!
"""

import asyncio
import logging
import json
from typing import Optional, Dict, Any, List
from pathlib import Path
from dataclasses import dataclass
from PIL import Image
import io

logger = logging.getLogger(__name__)


@dataclass
class ChartData:
    """Chart data structure."""
    title: str
    bars: List[Dict[str, Any]]  # [{"label": "...", "value": 35, "color": "#..."}]
    y_axis_label: str = "Value"
    source: Optional[str] = None


class SimpleChartGenerator:
    """
    Generate charts using Chart.js - simple, reliable, widely used.
    
    Uses Chart.js (most popular chart library) + Playwright.
    No React complexity - just works!
    """
    
    def __init__(self):
        """Initialize chart generator."""
        try:
            from playwright.async_api import async_playwright
            self.playwright_available = True
            logger.info("✅ Simple chart generator initialized (Chart.js + Playwright)")
        except ImportError:
            self.playwright_available = False
            logger.warning("⚠️  Playwright not available")
    
    async def create_bar_chart(
        self,
        chart_data: ChartData,
        output_path: Optional[str] = None,
        width: int = 1200,
        height: int = 630
    ) -> Optional[bytes]:
        """
        Create a bar chart using Chart.js.
        
        Args:
            chart_data: Chart data structure
            output_path: Optional path to save WebP file
            width: Image width
            height: Image height
            
        Returns:
            Image bytes (WebP) or None
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
            
            # Build HTML with Chart.js
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        body {{
            margin: 0;
            padding: 24px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: white;
        }}
        .container {{
            width: {width}px;
            border: 1px solid #e4e4e7;
            border-radius: 8px;
            padding: 24px;
            background: white;
        }}
        h2 {{
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
        canvas {{
            max-height: 400px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h2>{chart_data.title}</h2>
        <canvas id="myChart"></canvas>
        {f'<div class="source">Source: {chart_data.source}</div>' if chart_data.source else ''}
    </div>
    
    <script>
        const ctx = document.getElementById('myChart');
        new Chart(ctx, {{
            type: 'bar',
            data: {{
                labels: {labels},
                datasets: [{{
                    label: '{chart_data.y_axis_label}',
                    data: {values},
                    backgroundColor: {colors},
                    borderRadius: 4,
                    borderSkipped: false,
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: true,
                plugins: {{
                    legend: {{
                        display: false
                    }},
                    tooltip: {{
                        backgroundColor: '#ffffff',
                        titleColor: '#09090b',
                        bodyColor: '#71717a',
                        borderColor: '#e4e4e7',
                        borderWidth: 1,
                        padding: 12,
                        displayColors: false,
                        callbacks: {{
                            label: function(context) {{
                                return '{chart_data.y_axis_label}: ' + context.parsed.y + '%';
                            }}
                        }}
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: {max(values) * 1.2 if values else 50},
                        ticks: {{
                            color: '#71717a',
                            font: {{
                                size: 12
                            }}
                        }},
                        grid: {{
                            color: '#e4e4e7',
                            drawBorder: false
                        }}
                    }},
                    x: {{
                        ticks: {{
                            color: '#71717a',
                            font: {{
                                size: 12
                            }}
                        }},
                        grid: {{
                            display: false
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
            
            # Render with Playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(viewport={'width': width + 50, 'height': height + 50})
                await page.set_content(html_content)
                
                # Wait for Chart.js to render
                await page.wait_for_load_state('networkidle')
                await page.wait_for_timeout(2000)  # Chart.js needs time
                
                # Screenshot
                container = await page.query_selector('.container')
                screenshot_bytes = await container.screenshot(type='png')
                
                await browser.close()
            
            # Convert to WebP
            img = Image.open(io.BytesIO(screenshot_bytes))
            webp_buffer = io.BytesIO()
            img.save(webp_buffer, format='WEBP', quality=95)
            image_bytes = webp_buffer.getvalue()
            
            # Save if path provided
            if output_path:
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                with open(output_file, 'wb') as f:
                    f.write(image_bytes)
                logger.info(f"✅ Chart saved: {output_file}")
            
            return image_bytes
            
        except Exception as e:
            logger.error(f"Chart generation failed: {e}", exc_info=True)
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

