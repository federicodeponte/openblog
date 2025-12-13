"""
Asset Finder Agent

Finds graphics, images, and visual assets from the internet for blog articles.
Optionally uses Gemini Imagen to recreate images in the company's design system.

Features:
- Internet search for relevant images/assets
- Image URL extraction and validation
- Optional recreation using Gemini Imagen in company design system
- Design system extraction from company data
- Standalone, testable module
"""

import os
import logging
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from urllib.parse import urlparse

from ..models.gemini_client import GeminiClient
from ..models.google_imagen_client import GoogleImagenClient

logger = logging.getLogger(__name__)


@dataclass
class AssetFinderRequest:
    """Request for asset finding."""
    article_topic: str  # Main topic/keyword for the article
    article_headline: Optional[str] = None  # Article headline for context
    section_title: Optional[str] = None  # Specific section if finding assets for a section
    company_data: Optional[Dict[str, Any]] = None  # Company info for design system
    max_results: int = 5  # Maximum number of assets to find
    recreate_in_design_system: bool = False  # Whether to recreate using Imagen
    image_types: List[str] = field(default_factory=lambda: ["photo", "illustration", "infographic", "diagram"])  # Types to search for


@dataclass
class FoundAsset:
    """Represents a found asset."""
    url: str
    title: str
    description: str
    source: str  # Website/source name
    image_type: str  # photo, illustration, infographic, etc.
    license_info: Optional[str] = None  # License information if available
    width: Optional[int] = None
    height: Optional[int] = None


@dataclass
class AssetFinderResponse:
    """Response from asset finder."""
    success: bool
    assets: List[FoundAsset] = field(default_factory=list)
    recreated_assets: List[Dict[str, Any]] = field(default_factory=list)  # If recreate_in_design_system=True
    error: Optional[str] = None
    search_query_used: Optional[str] = None


class AssetFinderAgent:
    """
    Agent that finds visual assets from the internet for blog articles.
    
    Can optionally recreate images using Gemini Imagen in the company's design system.
    """
    
    def __init__(self, gemini_api_key: Optional[str] = None):
        """
        Initialize asset finder agent.
        
        Args:
            gemini_api_key: Optional Gemini API key (uses env var if not provided)
        """
        self.gemini_client = GeminiClient(api_key=gemini_api_key)
        self.imagen_client = None
        
        # Initialize Imagen client if API key available
        try:
            self.imagen_client = GoogleImagenClient()
            if not self.imagen_client.mock_mode:
                logger.info("✅ Imagen client initialized for image recreation")
            else:
                logger.info("⚠️  Imagen client in mock mode")
        except Exception as e:
            logger.warning(f"Imagen client initialization failed: {e}")
            self.imagen_client = None
        
        # Initialize Serper Dev Google Images finder (fallback/enhancement)
        self.serper_finder = None
        try:
            from .serper_images_finder import SerperImagesFinder
            self.serper_finder = SerperImagesFinder()
            if self.serper_finder.is_configured():
                logger.info("✅ Serper Dev Google Images finder initialized (fallback available)")
        except Exception as e:
            logger.debug(f"Serper Dev finder not available: {e}")
            self.serper_finder = None
        
        # Initialize DataForSEO Google Images finder (fallback/enhancement)
        self.dataforseo_finder = None
        try:
            from .google_images_finder import GoogleImagesFinder
            self.dataforseo_finder = GoogleImagesFinder()
            if self.dataforseo_finder.is_configured():
                logger.info("✅ DataForSEO Google Images finder initialized (fallback available)")
        except Exception as e:
            logger.debug(f"DataForSEO finder not available: {e}")
            self.dataforseo_finder = None
    
    async def find_assets(self, request: AssetFinderRequest) -> AssetFinderResponse:
        """
        Find assets from the internet for a blog article.
        
        Technology Stack:
        - Gemini AI (google-genai SDK) with Google Search grounding
        - Google Search Tool: Automatically searches web and extracts URLs
        - Optional: Gemini Imagen for image recreation
        
        Process:
        1. Build search query from article context
        2. Use Gemini with Google Search to find image URLs
        3. Parse JSON response with asset metadata
        4. Optionally recreate using Imagen in design system
        
        Args:
            request: Asset finder request
            
        Returns:
            AssetFinderResponse with found assets
        """
        try:
            print("\n" + "="*80)
            print("STAGE 1: Building Search Query")
            print("="*80)
            logger.info(f"🔍 Finding assets for: {request.article_topic}")
            
            # Step 1: Build search query
            search_query = self._build_search_query(request)
            print(f"✅ Search Query: {search_query}")
            logger.info(f"Search query: {search_query}")
            
            print("\n" + "="*80)
            print("STAGE 2: Searching Internet (Gemini + Google Search)")
            print("="*80)
            print("Technology: Gemini AI with Google Search grounding")
            print("  - Gemini uses Google Search tool automatically")
            print("  - Searches free stock photo sites (Unsplash, Pexels, Pixabay)")
            print("  - Extracts image URLs and metadata")
            print("  - Returns JSON array of assets\n")
            
            # Step 2: Use Gemini with Google Search to find assets
            assets = await self._search_for_assets(search_query, request)
            
            # Fallback to Serper Dev or DataForSEO if Gemini returns no results
            if not assets:
                # Try Serper Dev first (simpler, faster)
                if self.serper_finder and self.serper_finder.is_configured():
                    print("\n⚠️  Gemini returned no results, trying Serper Dev Google Images API...")
                    try:
                        clean_query = search_query.replace("images:", "").strip()
                        images = await self.serper_finder.search_images(
                            query=clean_query,
                            max_results=request.max_results,
                            size="large",
                            license="creativeCommons"
                        )
                        if images:
                            print(f"✅ Found {len(images)} images via Serper Dev fallback")
                            assets = self.serper_finder.convert_to_found_assets(images, request.article_topic)
                    except Exception as e:
                        logger.warning(f"Serper Dev fallback failed: {e}")
                
                # Try DataForSEO as last resort
                if not assets and self.dataforseo_finder and self.dataforseo_finder.is_configured():
                    print("\n⚠️  Trying DataForSEO Google Images API...")
                    try:
                        clean_query = search_query.replace("images:", "").strip()
                        images = await self.dataforseo_finder.search_images(
                            query=clean_query,
                            max_results=request.max_results,
                            size="large",
                            license="creativeCommons"
                        )
                        if images:
                            print(f"✅ Found {len(images)} images via DataForSEO fallback")
                            assets = self.dataforseo_finder.convert_to_found_assets(images, request.article_topic)
                    except Exception as e:
                        logger.warning(f"DataForSEO fallback failed: {e}")
            
            # Apply diversity checks to prevent too similar images
            if assets:
                assets = self._ensure_diversity(assets, request)
            
            if not assets:
                logger.warning("No assets found")
                return AssetFinderResponse(
                    success=False,
                    error="No assets found",
                    search_query_used=search_query
                )
            
            print(f"✅ Found {len(assets)} assets")
            logger.info(f"✅ Found {len(assets)} assets")
            
            # Step 3: Optionally recreate in design system
            recreated_assets = []
            if request.recreate_in_design_system and self.imagen_client:
                print("\n" + "="*80)
                print("STAGE 3: Recreating in Design System (Gemini Imagen)")
                print("="*80)
                print("Technology: Gemini Imagen 4.0")
                print("  - Takes original asset concept")
                print("  - Applies company design system (colors, style)")
                print("  - Generates new image matching brand identity\n")
                logger.info("🎨 Recreating assets in company design system...")
                recreated_assets = await self._recreate_assets(assets, request)
                print(f"✅ Recreated {len(recreated_assets)} assets")
            else:
                print("\n" + "="*80)
                print("STAGE 3: Skipped (recreate_in_design_system=False)")
                print("="*80)
            
            return AssetFinderResponse(
                success=True,
                assets=assets,
                recreated_assets=recreated_assets,
                search_query_used=search_query
            )
            
        except Exception as e:
            logger.error(f"Asset finding failed: {e}", exc_info=True)
            print(f"\n❌ Error: {e}")
            return AssetFinderResponse(
                success=False,
                error=str(e)
            )
    
    def _build_search_query(self, request: AssetFinderRequest) -> str:
        """
        Build search query for finding assets.
        
        Uses "images:" prefix to search Google Images directly (better than page scraping).
        
        Args:
            request: Asset finder request
            
        Returns:
            Search query string optimized for Google Images search
        """
        # Use "images:" prefix for Google Images search (more relevant than page scraping)
        query_parts = ["images:"]
        
        # Add main topic
        query_parts.append(request.article_topic)
        
        if request.section_title:
            query_parts.append(request.section_title)
        
        # Add image type hints
        image_types_str = " ".join(request.image_types)
        query_parts.append(image_types_str)
        
        # Add free stock image sites (Google Images will prioritize these)
        query_parts.append("unsplash pexels pixabay free")
        
        # Add context about use case
        if request.company_data:
            industry = request.company_data.get("industry", "")
            if industry:
                query_parts.append(industry)
        
        return " ".join(query_parts)
    
    async def _search_for_assets(
        self, 
        search_query: str, 
        request: AssetFinderRequest
    ) -> List[FoundAsset]:
        """
        Use Gemini with Google Search to find image assets.
        
        Technology: Gemini AI with Google Search grounding
        - Gemini automatically uses Google Search tool when enable_tools=True
        - Searches web and extracts URLs from search results
        - Returns structured JSON with asset metadata
        
        Falls back to DataForSEO Google Images API if Gemini fails or returns no results.
        
        Args:
            search_query: Search query
            request: Original request for context
            
        Returns:
            List of found assets
        """
        # Primary: Use Gemini + Google Search
        print(f"📡 Calling Gemini API with Google Search enabled...")
        print(f"   Model: {self.gemini_client.MODEL}")
        print(f"   Tools: Google Search (automatic web search)")
        print()
        
        # Create prompt for Gemini to find assets using Google Images search
        prompt = f"""You are helping find visual assets (images, graphics, illustrations) for a blog article.

Article Topic: {request.article_topic}
{"Headline: " + request.article_headline if request.article_headline else ""}
{"Section: " + request.section_title if request.section_title else ""}

TASK: Use Google Images Search to find {request.max_results} high-quality, relevant visual assets.

IMPORTANT: Search Google Images directly (not regular web pages). Focus on images that are:
- Relevant to the article topic: {request.article_topic}
- High quality and professional
- From free stock photo sites (Unsplash, Pexels, Pixabay preferred)
- Appropriate types: {', '.join(request.image_types)}
- Large size (suitable for blog headers, at least 800px wide)

AVOID:
- Logos and brand images
- Small icons or decorative elements
- Low-quality or irrelevant images
- Images from random websites (prefer stock photo sites)

For each asset found, return JSON in this format:
{{
    "url": "https://example.com/image.jpg",
    "title": "Descriptive title",
    "description": "What the image shows",
    "source": "Unsplash/Pexels/etc",
    "image_type": "photo|illustration|infographic|diagram",
    "license_info": "Free to use / CC0 / etc",
    "width": 1920,
    "height": 1080
}}

Return ONLY a JSON array of assets, no other text:
[
    {{"url": "...", "title": "...", ...}},
    ...
]"""

        try:
            # Use Gemini with Google Search enabled
            # Note: We'll parse JSON from text response (no schema needed for simple array)
            print("⏳ Waiting for Gemini response (this may take 10-30 seconds)...")
            response = await self.gemini_client.generate_content(
                prompt,
                enable_tools=True  # Enable Google Search - this triggers automatic web search
            )
            
            print(f"✅ Received response ({len(response)} characters)")
            print(f"   Response preview: {response[:200]}...")
            print()
            
            if not response:
                logger.warning("No response from Gemini")
                return []
            
            # Parse JSON response (may be embedded in text)
            import json
            import re
            
            # Try to extract JSON array from response
            # Look for JSON array pattern
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                # Try parsing entire response
                json_str = response.strip()
            
            # Remove markdown code blocks if present
            json_str = re.sub(r'```json\s*', '', json_str)
            json_str = re.sub(r'```\s*', '', json_str)
            json_str = json_str.strip()
            
            try:
                assets_data = json.loads(json_str)
            except json.JSONDecodeError:
                # Try to find JSON array more aggressively
                json_match = re.search(r'\[[\s\S]*\]', response)
                if json_match:
                    try:
                        assets_data = json.loads(json_match.group(0))
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse JSON from response")
                        logger.debug(f"Response: {response[:500]}")
                        return []
                else:
                    logger.error(f"No JSON array found in response")
                    logger.debug(f"Response: {response[:500]}")
                    return []
            
            if not isinstance(assets_data, list):
                logger.warning("Response is not a list")
                return []
            
            print("STAGE 2.1: Parsing JSON Response")
            print("-" * 80)
            print(f"Found {len(assets_data)} assets in response")
            print()
            
            # Convert to FoundAsset objects
            assets = []
            for i, asset_data in enumerate(assets_data[:request.max_results], 1):
                try:
                    print(f"Parsing asset {i}/{min(len(assets_data), request.max_results)}:")
                    print(f"  URL: {asset_data.get('url', 'N/A')[:80]}...")
                    print(f"  Title: {asset_data.get('title', 'N/A')}")
                    print(f"  Source: {asset_data.get('source', 'N/A')}")
                    
                    asset = FoundAsset(
                        url=asset_data.get("url", ""),
                        title=asset_data.get("title", ""),
                        description=asset_data.get("description", ""),
                        source=asset_data.get("source", "Unknown"),
                        image_type=asset_data.get("image_type", "photo"),
                        license_info=asset_data.get("license_info"),
                        width=asset_data.get("width"),
                        height=asset_data.get("height")
                    )
                    
                    # Validate URL
                    if self._is_valid_image_url(asset.url):
                        print(f"  ✅ Valid image URL")
                        assets.append(asset)
                    else:
                        print(f"  ⚠️  Invalid image URL (skipping)")
                        logger.warning(f"Invalid image URL: {asset.url}")
                    print()
                        
                except Exception as e:
                    print(f"  ❌ Failed to parse: {e}")
                    logger.warning(f"Failed to parse asset: {e}")
                    continue
            
            print(f"✅ Successfully parsed {len(assets)} valid assets")
            return assets
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response was: {response[:500]}")
            return []
        except Exception as e:
            logger.error(f"Asset search failed: {e}", exc_info=True)
            return []
    
    def _is_valid_image_url(self, url: str) -> bool:
        """
        Check if URL looks like a valid image URL.
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL appears valid
        """
        if not url or not url.startswith(("http://", "https://")):
            return False
        
        # Check for common image extensions
        image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"]
        url_lower = url.lower()
        
        # Check if URL has image extension or is from known image hosting sites
        has_extension = any(ext in url_lower for ext in image_extensions)
        is_image_host = any(domain in url_lower for domain in [
            "unsplash.com", "pexels.com", "pixabay.com", "imgur.com",
            "flickr.com", "gettyimages.com", "shutterstock.com"
        ])
        
        return has_extension or is_image_host
    
    async def _recreate_assets(
        self,
        assets: List[FoundAsset],
        request: AssetFinderRequest
    ) -> List[Dict[str, Any]]:
        """
        Recreate assets using Gemini Imagen in company design system.
        
        Args:
            assets: List of found assets to recreate
            request: Original request with company data
            
        Returns:
            List of recreated asset metadata
        """
        if not self.imagen_client or self.imagen_client.mock_mode:
            logger.warning("Imagen client not available for recreation")
            return []
        
        recreated = []
        
        print(f"Processing {min(len(assets), 3)} assets for recreation...")
        print()
        
        for i, asset in enumerate(assets[:3], 1):  # Limit to 3 recreations to avoid rate limits
            try:
                print(f"Recreating asset {i}/{min(len(assets), 3)}: {asset.title}")
                logger.info(f"🎨 Recreating: {asset.title}")
                
                # Extract design system
                design_system = self._extract_design_system(request.company_data or {})
                print(f"  Design System:")
                print(f"    Colors: {design_system.get('colors', [])}")
                print(f"    Style: {design_system.get('style', 'N/A')}")
                print(f"    Industry: {design_system.get('industry', 'N/A')}")
                
                # Build design system prompt
                design_prompt = self._build_design_system_prompt(asset, request)
                print(f"  Prompt length: {len(design_prompt)} characters")
                print(f"  ⏳ Generating image with Imagen 4.0...")
                
                # Generate image
                project_folder_id = None
                if request.company_data:
                    project_folder_id = request.company_data.get("project_folder_id")
                
                recreated_url = self.imagen_client.generate_image(
                    design_prompt,
                    project_folder_id=project_folder_id
                )
                
                if recreated_url:
                    print(f"  ✅ Generated: {recreated_url}")
                    recreated.append({
                        "original_url": asset.url,
                        "original_title": asset.title,
                        "recreated_url": recreated_url,
                        "design_prompt": design_prompt,
                        "success": True
                    })
                    logger.info(f"✅ Recreated: {recreated_url}")
                else:
                    print(f"  ❌ Generation failed")
                    logger.warning(f"Failed to recreate: {asset.title}")
                print()
                    
            except Exception as e:
                print(f"  ❌ Error: {e}")
                logger.error(f"Error recreating asset: {e}")
                continue
        
        return recreated
    
    def _build_design_system_prompt(
        self,
        asset: FoundAsset,
        request: AssetFinderRequest
    ) -> str:
        """
        Build prompt for recreating image in company design system.
        
        Args:
            asset: Original asset to recreate
            request: Request with company data
            
        Returns:
            Design system prompt for Imagen
        """
        # Extract design system from company data
        design_system = self._extract_design_system(request.company_data or {})
        
        prompt_parts = [
            f"Recreate this image concept in a professional design system:",
            f"",
            f"Original concept: {asset.description or asset.title}",
            f"Image type: {asset.image_type}",
            f"",
            f"Design System Requirements:",
        ]
        
        # Add design system elements
        if design_system.get("colors"):
            prompt_parts.append(f"- Color palette: {', '.join(design_system['colors'])}")
        
        if design_system.get("style"):
            prompt_parts.append(f"- Style: {design_system['style']}")
        
        if design_system.get("industry"):
            prompt_parts.append(f"- Industry context: {design_system['industry']}")
        
        # Add technical requirements
        prompt_parts.extend([
            f"",
            f"Technical Requirements:",
            f"- Professional, high-quality image",
            f"- Suitable for blog article header (1200x630)",
            f"- Clean, modern aesthetic",
            f"- No text or watermarks",
            f"- Consistent with company brand identity"
        ])
        
        return "\n".join(prompt_parts)
    
    def _extract_design_system(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract design system information from company data.
        
        Args:
            company_data: Company information
            
        Returns:
            Design system dict with colors, style, etc.
        """
        design_system = {
            "colors": [],
            "style": "professional",
            "industry": company_data.get("industry", "")
        }
        
        # Try to extract brand colors from company data
        # This is a placeholder - in a real system, you'd have brand colors stored
        industry = company_data.get("industry", "").lower()
        
        # Map industries to typical color palettes
        industry_colors = {
            "technology": ["#0066CC", "#00CCFF", "#333333"],
            "finance": ["#1A472A", "#2D5016", "#FFD700"],
            "healthcare": ["#0066CC", "#00CC99", "#FFFFFF"],
            "retail": ["#FF6B6B", "#4ECDC4", "#FFE66D"],
            "education": ["#4A90E2", "#50C878", "#FFA500"],
        }
        
        for key, colors in industry_colors.items():
            if key in industry:
                design_system["colors"] = colors
                break
        
        # Default colors if none found
        if not design_system["colors"]:
            design_system["colors"] = ["#6366F1", "#8B5CF6", "#EC4899"]  # Modern gradient
        
        # Extract style preferences
        brand_tone = company_data.get("brand_tone", "").lower()
        if "modern" in brand_tone or "contemporary" in brand_tone:
            design_system["style"] = "modern minimalist"
        elif "classic" in brand_tone or "traditional" in brand_tone:
            design_system["style"] = "classic professional"
        elif "creative" in brand_tone or "bold" in brand_tone:
            design_system["style"] = "creative vibrant"
        
        return design_system
    
    def _ensure_diversity(self, assets: List[FoundAsset], request: AssetFinderRequest) -> List[FoundAsset]:
        """
        Ensure diversity in found assets to prevent too similar images.
        
        Strategies:
        1. Remove duplicate domains (max 2 per domain)
        2. Ensure variety in image types
        3. Spread across different sources
        4. Remove very similar URLs
        
        Args:
            assets: List of found assets
            request: Original request
            
        Returns:
            Filtered list with diversity ensured
        """
        if len(assets) <= 1:
            return assets
        
        from collections import Counter
        
        # Track domains and sources
        domain_count = Counter()
        source_count = Counter()
        seen_urls = set()
        diverse_assets = []
        
        for asset in assets:
            # Skip duplicates
            if asset.url in seen_urls:
                continue
            seen_urls.add(asset.url)
            
            # Parse domain
            try:
                domain = urlparse(asset.url).netloc
                # Limit to 2 images per domain
                if domain_count[domain] >= 2:
                    continue
                domain_count[domain] += 1
            except:
                pass
            
            # Limit to 2 images per source
            if source_count[asset.source] >= 2:
                continue
            source_count[asset.source] += 1
            
            diverse_assets.append(asset)
            
            # Stop if we have enough diverse assets
            if len(diverse_assets) >= request.max_results:
                break
        
        if len(diverse_assets) < len(assets):
            logger.info(f"Applied diversity filter: {len(assets)} → {len(diverse_assets)} assets")
        
        return diverse_assets

