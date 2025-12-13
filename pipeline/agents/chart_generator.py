"""
Beautiful Statistics Chart Generator

Creates professional-looking statistics charts using:
1. Seaborn (beautiful Python charts) - Primary ✅
2. Playwright + React/recharts (for web-style charts) - Alternative
"""

import os
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from dataclasses import dataclass
import io
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class ChartData:
    """Chart data structure."""
    title: str
    bars: List[Dict[str, Any]]  # [{"label": "...", "value": 35, "color": "#..."}]
    y_axis_label: str = "Value"
    x_axis_label: Optional[str] = None
    source: Optional[str] = None


class ChartGenerator:
    """
    Generate beautiful statistics charts.
    
    Uses Seaborn for professional-looking charts (like recharts/shadcn quality).
    Can also use Playwright + React/recharts for web-style charts.
    """
    
    def __init__(self):
        """Initialize chart generator."""
        # Seaborn
        try:
            import seaborn as sns
            import matplotlib.pyplot as plt
            import matplotlib
            matplotlib.use('Agg')  # Non-interactive backend
            self.seaborn_available = True
            self.sns = sns
            self.plt = plt
            logger.info("✅ Chart generator initialized (Seaborn available)")
        except ImportError:
            self.seaborn_available = False
            logger.warning("⚠️  Seaborn not available")
        
        # Playwright for React/recharts
        try:
            from playwright.async_api import async_playwright
            self.playwright_available = True
            logger.info("✅ Playwright available (can use React/recharts)")
        except ImportError:
            self.playwright_available = False
            logger.debug("Playwright not available")
    
    def create_bar_chart(
        self,
        chart_data: ChartData,
        output_path: Optional[str] = None,
        style: str = "whitegrid",
        palette: Optional[List[str]] = None,
        width: int = 1200,
        height: int = 630,
        dpi: int = 100
    ) -> Optional[bytes]:
        """
        Create a beautiful bar chart using Seaborn.
        
        Args:
            chart_data: Chart data structure
            output_path: Optional path to save WebP file
            style: Seaborn style (whitegrid, darkgrid, white, dark, ticks)
            palette: Custom color palette (uses chart_data colors if not provided)
            width: Image width in pixels
            height: Image height in pixels
            dpi: DPI for rendering
            
        Returns:
            Image bytes (WebP format) or None if failed
        """
        if not self.seaborn_available:
            logger.error("Seaborn not available")
            return None
        
        try:
            # Set style
            self.sns.set_style(style)
            self.sns.set_context("notebook", font_scale=1.2)
            
            # Prepare data
            labels = [bar["label"] for bar in chart_data.bars]
            values = [bar["value"] for bar in chart_data.bars]
            colors = [bar.get("color", "#4A90E2") for bar in chart_data.bars] if not palette else palette
            
            # Create figure with high DPI for crisp rendering
            fig, ax = self.plt.subplots(figsize=(width/dpi, height/dpi), dpi=dpi)
            
            # Create bar chart with beautiful styling
            bars = ax.bar(
                labels,
                values,
                color=colors,
                edgecolor='white',
                linewidth=2,
                alpha=0.9,
                width=0.6
            )
            
            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2.,
                    height + max(values) * 0.01,
                    f'{int(height)}%',
                    ha='center',
                    va='bottom',
                    fontsize=14,
                    fontweight='bold',
                    color='#2C3E50'
                )
            
            # Customize axes
            ax.set_ylabel(chart_data.y_axis_label, fontsize=16, fontweight='bold', color='#2C3E50')
            if chart_data.x_axis_label:
                ax.set_xlabel(chart_data.x_axis_label, fontsize=16, fontweight='bold', color='#2C3E50')
            
            # Set title
            ax.set_title(
                chart_data.title,
                fontsize=20,
                fontweight='bold',
                color='#2C3E50',
                pad=20
            )
            
            # Add source if provided
            if chart_data.source:
                fig.text(
                    0.99, 0.01,
                    f"Source: {chart_data.source}",
                    ha='right',
                    fontsize=10,
                    style='italic',
                    color='#7F8C8D'
                )
            
            # Remove top and right spines for cleaner look
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#BDC3C7')
            ax.spines['bottom'].set_color('#BDC3C7')
            
            # Set y-axis to start at 0
            ax.set_ylim(0, max(values) * 1.15)
            
            # Grid styling
            ax.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)
            ax.set_axisbelow(True)
            
            # Rotate x-axis labels if needed
            self.plt.xticks(rotation=0, ha='center')
            
            # Tight layout
            self.plt.tight_layout()
            
            # Save to bytes (WebP format)
            img_buffer = io.BytesIO()
            fig.savefig(
                img_buffer,
                format='webp',
                dpi=dpi,
                bbox_inches='tight',
                facecolor='white',
                edgecolor='none'
            )
            img_buffer.seek(0)
            image_bytes = img_buffer.read()
            
            # Also save to file if path provided
            if output_path:
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                with open(output_file, 'wb') as f:
                    f.write(image_bytes)
                logger.info(f"✅ Chart saved: {output_file}")
            
            self.plt.close(fig)
            
            return image_bytes
            
        except Exception as e:
            logger.error(f"Chart generation failed: {e}", exc_info=True)
            if 'fig' in locals():
                self.plt.close(fig)
            return None
    
    async def create_chart_with_recharts(
        self,
        chart_data: ChartData,
        output_path: Optional[str] = None,
        width: int = 1200,
        height: int = 630
    ) -> Optional[bytes]:
        """
        Create chart using Playwright + React/recharts (web-style charts).
        
        Requires: Playwright installed and React/recharts CDN available.
        
        Args:
            chart_data: Chart data structure
            output_path: Optional path to save WebP file
            width: Image width
            height: Image height
            
        Returns:
            Image bytes (WebP) or None
        """
        if not self.playwright_available:
            logger.warning("Playwright not available for recharts rendering")
            return None
        
        try:
            from playwright.async_api import async_playwright
            
            # Build React/recharts HTML
            labels = [bar["label"] for bar in chart_data.bars]
            values = [bar["value"] for bar in chart_data.bars]
            colors = [bar.get("color", "#4A90E2") for bar in chart_data.bars]
            
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/recharts@2.10.3/umd/Recharts.js"></script>
    <style>
        body {{
            margin: 0;
            padding: 40px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: white;
        }}
        #chart {{
            width: {width}px;
            height: {height}px;
        }}
    </style>
</head>
<body>
    <div id="chart"></div>
    <script>
        const {{ BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer }} = Recharts;
        
        const data = {json.dumps([{"name": label, "value": value} for label, value in zip(labels, values)])};
        const colors = {json.dumps(colors)};
        
        ReactDOM.render(
            React.createElement('div', null,
                React.createElement('h2', {{style: {{fontSize: '24px', fontWeight: 'bold', marginBottom: '20px', color: '#2C3E50'}}}}, '{chart_data.title}'),
                React.createElement(ResponsiveContainer, {{width: '100%', height: '80%'}},
                    React.createElement(BarChart, {{data: data, margin: {{top: 20, right: 30, left: 20, bottom: 5}}}},
                        React.createElement(CartesianGrid, {{strokeDasharray: '3 3', stroke: '#E0E0E0'}}),
                        React.createElement(XAxis, {{dataKey: 'name', tick: {{fill: '#666'}}}}),
                        React.createElement(YAxis, {{tick: {{fill: '#666'}}, label: {{value: '{chart_data.y_axis_label}', angle: -90, position: 'insideLeft'}}}}),
                        React.createElement(Tooltip, {{contentStyle: {{backgroundColor: '#fff', border: '1px solid #ccc'}}}}),
                        React.createElement(Bar, {{dataKey: 'value', fill: colors[0], radius: [8, 8, 0, 0]}})
                    )
                ),
                {'React.createElement("p", {style: {fontSize: "12px", color: "#999", textAlign: "right", marginTop: "10px"}}, `Source: ${chart_data.source}`)' if chart_data.source else ''}
            ),
            document.getElementById('chart')
        );
    </script>
</body>
</html>
"""
            
            # Render with Playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()
                await page.set_content(html_content)
                await page.wait_for_timeout(1000)  # Wait for chart to render
                
                # Take screenshot
                screenshot_bytes = await page.screenshot(
                    type='webp',
                    full_page=False,
                    clip={'x': 0, 'y': 0, 'width': width, 'height': height}
                )
                
                await browser.close()
                
                # Save if path provided
                if output_path:
                    output_file = Path(output_path)
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_file, 'wb') as f:
                        f.write(screenshot_bytes)
                    logger.info(f"✅ Recharts chart saved: {output_file}")
                
                return screenshot_bytes
                
        except Exception as e:
            logger.error(f"Recharts chart generation failed: {e}", exc_info=True)
            return None
    
    def create_chart_from_data(
        self,
        title: str,
        data: Dict[str, float],  # {"<3 months": 35, "9-12+ months": 13}
        colors: Optional[Dict[str, str]] = None,
        y_axis_label: str = "Value",
        source: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> Optional[bytes]:
        """
        Convenience method to create chart from simple data dict.
        
        Args:
            title: Chart title
            data: Dict of label -> value
            colors: Optional dict of label -> color
            y_axis_label: Y-axis label
            source: Optional source attribution
            output_path: Optional path to save
            
        Returns:
            Image bytes (WebP) or None
        """
        bars = []
        default_colors = ["#4A90E2", "#50C878", "#FF6B6B", "#FFD93D", "#9B59B6"]
        
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
        
        return self.create_bar_chart(chart_data, output_path=output_path)
