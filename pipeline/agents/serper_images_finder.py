"""
Serper Dev Google Images Finder

Uses Serper Dev API for Google Images search.
Simpler than DataForSEO, faster, more reliable.

API: https://serper.dev/api/google-images
Cost: Check Serper Dev pricing
"""

import logging
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import httpx

from .asset_finder import FoundAsset

logger = logging.getLogger(__name__)


@dataclass
class SerperImageResult:
    """Serper Dev Google Images search result."""
    url: str
    title: str
    source: str  # Website domain
    width: Optional[int] = None
    height: Optional[int] = None
    thumbnail_url: Optional[str] = None


class SerperImagesFinder:
    """
    Find images using Serper Dev Google Images API.
    
    Advantages over DataForSEO:
    - Simpler API (single request, no polling)
    - Faster (no task polling)
    - More reliable
    - Better documentation
    """
    
    API_URL = "https://google.serper.dev/images"
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Serper Dev images finder.
        
        Args:
            api_key: Serper Dev API key (defaults to env var SERPER_API_KEY)
        """
        self.api_key = api_key or os.getenv("SERPER_API_KEY")
        
        if not self.api_key:
            logger.warning("⚠️  Serper Dev API key not found - Google Images search disabled")
        else:
            logger.info("✅ Serper Dev Google Images finder initialized")
    
    def is_configured(self) -> bool:
        """Check if Serper Dev is configured."""
        return bool(self.api_key)
    
    def _get_headers(self) -> Dict[str, str]:
        """Get API request headers."""
        return {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }
    
    async def search_images(
        self,
        query: str,
        max_results: int = 20,
        image_type: Optional[str] = None,  # photo, clipart, lineart, face, animated
        size: Optional[str] = None,  # large, medium, icon
        color_type: Optional[str] = None,  # color, grayscale, transparent
        license: Optional[str] = None,  # creativeCommons, commercial
    ) -> List[SerperImageResult]:
        """
        Search Google Images via Serper Dev.
        
        Args:
            query: Search query (e.g., "cloud security statistics chart")
            max_results: Maximum number of images (default: 20)
            image_type: Filter by type (photo, clipart, lineart, face, animated)
            size: Filter by size (large, medium, icon)
            color_type: Filter by color (color, grayscale, transparent)
            license: Filter by license (creativeCommons, commercial)
        
        Returns:
            List of SerperImageResult objects
        """
        if not self.is_configured():
            logger.warning("Serper Dev not configured - cannot search Google Images")
            return []
        
        logger.info(f"🔍 Searching Google Images via Serper Dev: {query}")
        
        # Build request payload
        payload = {
            "q": query,
            "num": min(max_results, 100),  # Serper Dev max is 100
        }
        
        # Add filters if provided
        if image_type:
            payload["imageType"] = image_type
        if size:
            payload["imageSize"] = size
        if color_type:
            payload["imageColorType"] = color_type
        if license:
            payload["imageLicense"] = license
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.API_URL,
                    json=payload,
                    headers=self._get_headers(),
                )
                
                if response.status_code != 200:
                    logger.error(f"Serper Dev API error: HTTP {response.status_code}")
                    logger.debug(f"Response: {response.text[:200]}")
                    return []
                
                data = response.json()
                images = self._parse_results(data)
                
                logger.info(f"✅ Found {len(images)} images from Serper Dev")
                return images
                
        except Exception as e:
            logger.error(f"Serper Dev search failed: {e}")
            return []
    
    def _parse_results(self, data: Dict[str, Any]) -> List[SerperImageResult]:
        """Parse Serper Dev API response."""
        images = []
        
        # Serper Dev structure: data["images"] contains image results
        image_items = data.get("images", [])
        
        for item in image_items:
            url = item.get("link") or item.get("imageUrl") or ""
            if not url:
                continue
            
            images.append(SerperImageResult(
                url=url,
                title=item.get("title", "") or item.get("alt", "") or "",
                source=item.get("source", "") or item.get("displayLink", "") or "",
                width=item.get("imageWidth"),
                height=item.get("imageHeight"),
                thumbnail_url=item.get("thumbnailLink") or item.get("thumbnailUrl")
            ))
        
        return images
    
    def convert_to_found_assets(
        self,
        image_results: List[SerperImageResult],
        article_topic: str
    ) -> List[FoundAsset]:
        """Convert SerperImageResult to FoundAsset format."""
        assets = []
        
        for img in image_results:
            asset = FoundAsset(
                url=img.url,
                title=img.title or f"Image: {article_topic}",
                description=f"Image from {img.source}",
                source=img.source or "Google Images",
                image_type="photo",  # Default, could be enhanced
                license_info="Check source for license",
                width=img.width,
                height=img.height
            )
            assets.append(asset)
        
        return assets

