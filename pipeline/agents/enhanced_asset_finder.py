"""
Enhanced Asset Finder - Finds Engaging Assets (Charts, Tables, Infographics)

This enhanced version:
1. Searches for pages with engaging assets (charts, tables, infographics)
2. Fetches and parses the actual pages
3. Extracts charts, tables, and other engaging assets
4. Uses AI vision to understand chart data
5. Can regenerate assets in company design system
"""

import logging
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup

from .asset_finder import AssetFinderAgent, AssetFinderRequest, FoundAsset

logger = logging.getLogger(__name__)


@dataclass
class EngagingAsset(FoundAsset):
    """Extended asset with engaging asset specific fields."""
    asset_type: str = "image"  # chart, table, infographic, diagram, image
    data_extracted: Optional[Dict[str, Any]] = None  # Extracted chart/table data
    source_url: str = ""  # URL of page where asset was found
    can_regenerate: bool = False  # Whether we can regenerate this asset


@dataclass
class EnhancedAssetFinderRequest(AssetFinderRequest):
    """Enhanced request with engaging asset options."""
    find_charts: bool = True
    find_tables: bool = True
    find_infographics: bool = True
    extract_data: bool = True  # Extract data from charts/tables
    fetch_pages: bool = True  # Actually fetch pages to extract assets


class EnhancedAssetFinder(AssetFinderAgent):
    """
    Enhanced asset finder that finds engaging assets like charts, tables, infographics.
    
    Process:
    1. Search for pages with engaging assets (research papers, reports, articles)
    2. Fetch actual pages (if fetch_pages=True)
    3. Extract charts, tables, images from HTML
    4. Use AI vision to understand chart data
    5. Extract structured data from charts/tables
    6. Optionally regenerate in design system
    """
    
    def __init__(self, gemini_api_key: Optional[str] = None):
        super().__init__(gemini_api_key)
        # Use browser-like headers to avoid blocking
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
        }
        self.http_client = httpx.AsyncClient(timeout=30.0, headers=headers, follow_redirects=True)
    
    async def find_engaging_assets(
        self, 
        request: EnhancedAssetFinderRequest
    ) -> List[EngagingAsset]:
        """
        Find engaging assets (charts, tables, infographics) for article.
        
        Args:
            request: Enhanced asset finder request
            
        Returns:
            List of engaging assets with extracted data
        """
        logger.info(f"🔍 Finding engaging assets for: {request.article_topic}")
        
        # Step 1: Search for pages with engaging assets
        search_query = self._build_engaging_search_query(request)
        logger.info(f"Search query: {search_query}")
        
        # Step 2: Use Gemini to find relevant pages
        pages = await self._search_for_pages(search_query, request)
        
        if not pages:
            logger.warning("No pages found")
            return []
        
        # Step 3: Fetch pages and extract assets
        engaging_assets = []
        
        for page_url in pages[:5]:  # Limit to 5 pages
            try:
                if request.fetch_pages:
                    assets = await self._extract_assets_from_page(page_url, request)
                    engaging_assets.extend(assets)
                else:
                    # Just return page URLs as potential sources
                    asset = EngagingAsset(
                        url=page_url,
                        title=f"Page with {request.article_topic} assets",
                        description=f"Potential source for engaging assets",
                        source="Web",
                        image_type="page",
                        source_url=page_url
                    )
                    engaging_assets.append(asset)
                    
            except Exception as e:
                logger.error(f"Error extracting from {page_url}: {e}")
                continue
        
        return engaging_assets
    
    def _build_engaging_search_query(self, request: EnhancedAssetFinderRequest) -> str:
        """Build search query optimized for finding engaging assets."""
        query_parts = [request.article_topic]
        
        # Add engaging asset types
        asset_types = []
        if request.find_charts:
            asset_types.append("charts graphs statistics")
        if request.find_tables:
            asset_types.append("tables comparisons data")
        if request.find_infographics:
            asset_types.append("infographics visualizations")
        
        if asset_types:
            query_parts.append(" ".join(asset_types))
        
        # Add source types
        query_parts.append("research report study article")
        
        return " ".join(query_parts)
    
    async def _search_for_pages(
        self,
        search_query: str,
        request: EnhancedAssetFinderRequest
    ) -> List[str]:
        """
        Use Gemini to find pages with engaging assets.
        
        Returns list of URLs to pages that likely contain charts/tables/infographics.
        """
        prompt = f"""Find {request.max_results} web pages that contain engaging visual assets for this article topic.

Article Topic: {request.article_topic}
{"Headline: " + request.article_headline if request.article_headline else ""}

TASK: Use Google Search to find pages that contain:
{"- Charts and graphs" if request.find_charts else ""}
{"- Comparison tables" if request.find_tables else ""}
{"- Infographics" if request.find_infographics else ""}

PRIORITIZE:
- Research papers (.edu, .org domains)
- Industry reports (McKinsey, Gartner, etc.)
- Data visualization sites (Tableau Public, Observable, etc.)
- Statistics sites (Statista, Pew Research, etc.)

Return ONLY a JSON array of URLs:
[
    "https://example.com/research-paper",
    "https://example.com/industry-report",
    ...
]"""

        try:
            response = await self.gemini_client.generate_content(
                prompt,
                enable_tools=True
            )
            
            # Parse JSON response
            import json
            import re
            
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                urls = json.loads(json_match.group(0))
                return [url for url in urls if isinstance(url, str) and url.startswith('http')]
            
            return []
            
        except Exception as e:
            logger.error(f"Page search failed: {e}")
            return []
    
    async def _extract_assets_from_page(
        self,
        page_url: str,
        request: EnhancedAssetFinderRequest
    ) -> List[EngagingAsset]:
        """
        Fetch page and extract engaging assets (charts, tables, images).
        
        Process:
        1. Fetch HTML content
        2. Parse HTML with BeautifulSoup
        3. Find charts (images that look like charts)
        4. Find tables (<table> elements)
        5. Find infographics (large images with text)
        6. Use AI vision to analyze charts
        7. Extract data from tables
        """
        assets = []
        
        try:
            # Fetch page
            logger.info(f"Fetching page: {page_url}")
            response = await self.http_client.get(page_url)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract tables
            if request.find_tables:
                tables = soup.find_all('table')
                for i, table in enumerate(tables[:3], 1):  # Limit to 3 tables
                    table_data = self._extract_table_data(table)
                    if table_data:
                        asset = EngagingAsset(
                            url=page_url + f"#table-{i}",
                            title=f"Data Table: {request.article_topic}",
                            description=f"Comparison table with {len(table_data.get('rows', []))} rows",
                            source="Web Page",
                            image_type="table",
                            asset_type="table",
                            source_url=page_url,
                            data_extracted=table_data,
                            can_regenerate=True
                        )
                        assets.append(asset)
            
            # Extract images (potential charts/infographics)
            images = soup.find_all('img')
            for img in images[:10]:  # Limit to 10 images
                img_url = img.get('src') or img.get('data-src', '')
                if not img_url:
                    continue
                
                # Make absolute URL
                if img_url.startswith('/'):
                    img_url = urljoin(page_url, img_url)
                elif not img_url.startswith('http'):
                    continue
                
                # Check if it might be a chart/infographic
                alt_text = img.get('alt', '').lower()
                is_chart = any(word in alt_text for word in ['chart', 'graph', 'statistic', 'data', 'visualization'])
                is_infographic = any(word in alt_text for word in ['infographic', 'diagram', 'flowchart'])
                
                asset_type = "chart" if is_chart else ("infographic" if is_infographic else "image")
                
                if (request.find_charts and is_chart) or (request.find_infographics and is_infographic) or not (is_chart or is_infographic):
                    asset = EngagingAsset(
                        url=img_url,
                        title=img.get('alt', 'Image') or f"{asset_type.title()} from {page_url}",
                        description=f"{asset_type.title()} found on page",
                        source="Web Page",
                        image_type=asset_type,
                        asset_type=asset_type,
                        source_url=page_url,
                        can_regenerate=is_chart or is_infographic
                    )
                    assets.append(asset)
            
            logger.info(f"Extracted {len(assets)} assets from {page_url}")
            
        except Exception as e:
            logger.error(f"Error extracting from {page_url}: {e}")
        
        return assets
    
    def _extract_table_data(self, table) -> Optional[Dict[str, Any]]:
        """Extract structured data from HTML table."""
        try:
            rows = []
            headers = []
            
            # Extract headers
            thead = table.find('thead')
            if thead:
                header_row = thead.find('tr')
                if header_row:
                    headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
            
            # Extract rows
            tbody = table.find('tbody') or table
            for tr in tbody.find_all('tr')[:20]:  # Limit to 20 rows
                cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                if cells:
                    rows.append(cells)
            
            if not rows:
                return None
            
            # If no headers, use first row as headers
            if not headers and rows:
                headers = rows[0]
                rows = rows[1:]
            
            return {
                "headers": headers,
                "rows": rows,
                "row_count": len(rows),
                "column_count": len(headers) if headers else (len(rows[0]) if rows else 0)
            }
            
        except Exception as e:
            logger.error(f"Error extracting table data: {e}")
            return None
    
    async def analyze_chart_with_vision(self, chart_url: str) -> Optional[Dict[str, Any]]:
        """
        Use Gemini Vision to analyze chart and extract data.
        
        This would use Gemini's vision capabilities to:
        - Identify chart type (bar, line, pie, etc.)
        - Extract data points
        - Understand labels and values
        """
        # TODO: Implement Gemini Vision analysis
        # This would require:
        # 1. Download chart image
        # 2. Send to Gemini Vision API
        # 3. Extract structured data
        logger.info(f"Chart analysis not yet implemented for {chart_url}")
        return None
    
    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()

