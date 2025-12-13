"""
Google Images Finder - Uses DataForSEO Google Images SERP

Reuses existing DataForSEO infrastructure from DataForSeoProvider.
Much better approach than fetching pages:
1. Direct Google Images search via DataForSEO
2. Gets image results from SERP (not random page images)
3. Filters by relevance, license, size
4. Returns high-quality, relevant images

Cost: $0.50 per 1,000 queries (same as regular search)
"""

import logging
import os
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import httpx

from .asset_finder import FoundAsset
from ..models.dataforseo_provider import LOCATION_CODES

logger = logging.getLogger(__name__)


@dataclass
class GoogleImageResult:
    """Google Images search result."""
    url: str
    title: str
    source: str  # Website domain
    width: Optional[int] = None
    height: Optional[int] = None
    thumbnail_url: Optional[str] = None
    license: Optional[str] = None  # Usage rights if available


class GoogleImagesFinder:
    """
    Find images using DataForSEO Google Images API.
    
    Reuses DataForSEO credentials and infrastructure from DataForSeoProvider.
    Much better than page scraping:
    - Gets images directly from Google Images SERP
    - Filters by relevance automatically
    - Returns high-quality, relevant images
    - No random page images
    """
    
    # DataForSEO Google Images endpoints
    # Note: Using same pattern as regular Google Search, but for Images
    TASK_POST_URL = "https://api.dataforseo.com/v3/serp/google/images/task_post"
    # Try different endpoint formats - might need task_get/advanced or different path
    TASK_GET_URL = "https://api.dataforseo.com/v3/serp/google/images/task_get/advanced/{task_id}"
    
    # Polling configuration (same as DataForSeoProvider)
    MAX_POLL_ATTEMPTS = 10
    INITIAL_POLL_DELAY = 0.5
    MAX_POLL_DELAY = 5.0
    BACKOFF_MULTIPLIER = 1.5
    
    def __init__(self, api_login: Optional[str] = None, api_password: Optional[str] = None):
        """Initialize Google Images finder.
        
        Uses same credentials as DataForSeoProvider (DATAFORSEO_LOGIN, DATAFORSEO_PASSWORD).
        """
        self.api_login = api_login or os.getenv("DATAFORSEO_LOGIN")
        self.api_password = api_password or os.getenv("DATAFORSEO_PASSWORD")
        self._encoded_credentials: Optional[str] = None
        
        if not self.api_login or not self.api_password:
            logger.warning("⚠️  DataForSEO credentials not found - Google Images search disabled")
        else:
            logger.debug("✅ Google Images Finder initialized with DataForSEO credentials")
    
    def is_configured(self) -> bool:
        """Check if DataForSEO is configured (same credentials as regular search)."""
        return bool(self.api_login and self.api_password)
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers (same as DataForSeoProvider)."""
        if not self._encoded_credentials:
            import base64
            credentials = f"{self.api_login}:{self.api_password}"
            self._encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        return {
            "Authorization": f"Basic {self._encoded_credentials}",
            "Content-Type": "application/json",
        }
    
    async def search_images(
        self,
        query: str,
        max_results: int = 20,
        language: str = "en",
        country: str = "us",
        image_type: Optional[str] = None,  # photo, clipart, lineart, face, animated
        size: Optional[str] = None,  # large, medium, icon
        color_type: Optional[str] = None,  # color, grayscale, transparent
        license: Optional[str] = None,  # creativeCommons, commercial
    ) -> List[GoogleImageResult]:
        """
        Search Google Images via DataForSEO.
        
        Args:
            query: Search query (e.g., "cloud security statistics chart")
            max_results: Maximum number of images (default: 20)
            language: Language code (default: "en")
            country: Country code (default: "us")
            image_type: Filter by type (photo, clipart, lineart, face, animated)
            size: Filter by size (large, medium, icon)
            color_type: Filter by color (color, grayscale, transparent)
            license: Filter by license (creativeCommons, commercial)
        
        Returns:
            List of GoogleImageResult objects
        """
        if not self.is_configured():
            logger.warning("DataForSEO not configured - cannot search Google Images")
            return []
        
        logger.info(f"🔍 Searching Google Images: {query}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Step 1: Submit task
                task_id = await self._post_image_task(
                    client, query, max_results, language, country,
                    image_type, size, color_type, license
                )
                
                if not task_id:
                    logger.error("Failed to create Google Images task")
                    return []
                
                # Step 2: Poll for results
                images = await self._poll_image_results(client, task_id)
                
                logger.info(f"✅ Found {len(images)} images from Google Images SERP")
                return images
                
        except Exception as e:
            logger.error(f"Google Images search failed: {e}")
            return []
    
    async def _post_image_task(
        self,
        client: httpx.AsyncClient,
        query: str,
        max_results: int,
        language: str,
        country: str,
        image_type: Optional[str],
        size: Optional[str],
        color_type: Optional[str],
        license: Optional[str],
    ) -> Optional[str]:
        """Submit Google Images search task (reuses LOCATION_CODES from DataForSeoProvider)."""
        location_code = LOCATION_CODES.get(country.lower(), 2840)  # Default to US
        
        # Build search parameters
        search_params = {
            "keyword": query,
            "location_code": location_code,
            "language_code": language,
            "depth": min(max_results, 100),
            "priority": 1,
        }
        
        # Add filters if provided
        if image_type:
            search_params["image_type"] = image_type
        if size:
            search_params["size"] = size
        if color_type:
            search_params["color_type"] = color_type
        if license:
            search_params["license"] = license
        
        payload = [search_params]
        
        try:
            response = await client.post(
                self.TASK_POST_URL,
                json=payload,
                headers=self._get_auth_headers(),
            )
            
            if response.status_code != 200:
                logger.error(f"Task POST failed: HTTP {response.status_code}, Response: {response.text[:200]}")
                return None
            
            data = response.json()
            logger.debug(f"Task POST response: {data}")
            
            if not data.get("tasks") or not data["tasks"]:
                logger.error(f"No tasks in response: {data}")
                return None
            
            task = data["tasks"][0]
            status_code = task.get("status_code")
            if status_code != 20100:
                logger.error(f"Task creation failed: status_code={status_code}, message={task.get('status_message')}")
                logger.debug(f"Full task response: {task}")
                return None
            
            task_id = task.get("id")
            logger.info(f"✅ Google Images task created: {task_id}")
            return task_id
            
        except Exception as e:
            logger.error(f"Task POST error: {e}")
            return None
    
    async def _poll_image_results(
        self,
        client: httpx.AsyncClient,
        task_id: str,
    ) -> List[GoogleImageResult]:
        """Poll for Google Images results."""
        delay = self.INITIAL_POLL_DELAY
        url = self.TASK_GET_URL.format(task_id=task_id)
        
        for attempt in range(self.MAX_POLL_ATTEMPTS):
            await asyncio.sleep(delay)
            
            try:
                response = await client.get(url, headers=self._get_auth_headers())
                
                if response.status_code != 200:
                    logger.debug(f"Poll attempt {attempt + 1}: HTTP {response.status_code}")
                    delay = min(delay * self.BACKOFF_MULTIPLIER, self.MAX_POLL_DELAY)
                    continue
                
                data = response.json()
                if not data.get("tasks") or not data["tasks"]:
                    logger.debug(f"Poll attempt {attempt + 1}: No tasks in response")
                    delay = min(delay * self.BACKOFF_MULTIPLIER, self.MAX_POLL_DELAY)
                    continue
                
                task = data["tasks"][0]
                status_code = task.get("status_code")
                
                # Still processing
                if status_code == 20100:
                    logger.debug(f"Poll attempt {attempt + 1}: Task still processing (20100)")
                    delay = min(delay * self.BACKOFF_MULTIPLIER, self.MAX_POLL_DELAY)
                    continue
                
                # Completed
                if status_code == 20000:
                    result = task.get("result", [])
                    logger.info(f"✅ Task completed! Parsing {len(result) if isinstance(result, list) else 'N/A'} results")
                    parsed = self._parse_image_results(result)
                    return parsed
                
                # Failed or other status
                error_msg = task.get("status_message", f"Unknown status code: {status_code}")
                logger.error(f"Task failed: {error_msg} (status_code: {status_code})")
                logger.debug(f"Full task response: {task}")
                return []
                
            except Exception as e:
                logger.debug(f"Poll error: {e}")
                delay = min(delay * self.BACKOFF_MULTIPLIER, self.MAX_POLL_DELAY)
        
        logger.error("Polling timeout")
        return []
    
    def _parse_image_results(self, results: List[Dict[str, Any]]) -> List[GoogleImageResult]:
        """Parse Google Images API results.
        
        DataForSEO Google Images API structure:
        - results is a list with one task result dict
        - task_result["items"] contains image items
        - Each item has type "images" and contains image data
        """
        images = []
        
        if not results:
            logger.debug("No results to parse")
            return images
        
        # DataForSEO structure: results[0] contains task result
        task_result = results[0] if isinstance(results, list) and results else {}
        items = task_result.get("items", [])
        
        logger.debug(f"Found {len(items)} items in task result")
        
        for idx, item in enumerate(items):
            # DataForSEO Google Images items have type "images"
            item_type = item.get("type")
            if item_type != "images":
                logger.debug(f"Item {idx}: Skipping type '{item_type}' (not 'images')")
                continue
            
            # Extract image URL (can be in different places)
            url = (
                item.get("url") or 
                item.get("image", {}).get("url") if isinstance(item.get("image"), dict) else None or
                item.get("original", {}).get("url") if isinstance(item.get("original"), dict) else None or
                ""
            )
            
            if not url:
                logger.debug(f"Item {idx}: No URL found, skipping. Item keys: {list(item.keys())}")
                continue
            
            # Extract image metadata
            image_data = item.get("image", {}) or item.get("original", {})
            if not isinstance(image_data, dict):
                image_data = {}
            
            images.append(GoogleImageResult(
                url=url,
                title=item.get("title", "") or item.get("alt", "") or item.get("text", "") or "",
                source=item.get("domain", "") or item.get("source", "") or "",
                width=image_data.get("width") or item.get("width"),
                height=image_data.get("height") or item.get("height"),
                thumbnail_url=image_data.get("thumbnail_url") or item.get("thumbnail") or item.get("thumbnail_url"),
                license=item.get("license", {}).get("type") if isinstance(item.get("license"), dict) else item.get("license")
            ))
        
        logger.info(f"Successfully parsed {len(images)} images from {len(items)} items")
        return images
    
    def convert_to_found_assets(
        self,
        image_results: List[GoogleImageResult],
        article_topic: str
    ) -> List[FoundAsset]:
        """Convert GoogleImageResult to FoundAsset format."""
        assets = []
        
        for img in image_results:
            asset = FoundAsset(
                url=img.url,
                title=img.title or f"Image: {article_topic}",
                description=f"Image from {img.source}",
                source=img.source or "Google Images",
                image_type="photo",  # Default, could be enhanced with image_type detection
                license_info=img.license or "Check source for license",
                width=img.width,
                height=img.height
            )
            assets.append(asset)
        
        return assets

