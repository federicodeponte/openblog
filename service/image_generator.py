"""
Image Generation Service
Generates blog images using Google GenAI SDK (gemini-3-pro-image-preview).
Uploads to Google Drive and makes publicly viewable.

v3: Uses Google GenAI SDK directly (consistent with blog generation)
Updated: 2025-12-06 - Fixed syntax error, removed OpenRouter dependency
"""

import os
import re
import json
import time
import base64
import asyncio
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload

logger = logging.getLogger(__name__)


@dataclass
class CompanyImageData:
    """Company context for image generation."""
    name: str
    industry: str
    language: str
    custom_prompt_instructions: Optional[str] = None


@dataclass
class ImageGenerationRequest:
    """Request for image generation."""
    headline: str
    keyword: str
    company_data: CompanyImageData
    project_folder_id: Optional[str] = None


@dataclass
class ImageGenerationResponse:
    """Response from image generation."""
    success: bool
    image_url: str = ""
    alt_text: str = ""
    drive_file_id: str = ""
    generation_time_seconds: float = 0.0
    error: Optional[str] = None
    prompt_used: Optional[str] = None


class ImageGenerator:
    """
    Handles blog image generation using:
    - Google GenAI SDK (gemini-3-pro-image-preview) - Latest Nano Banana Pro model with professional-grade features
    - Google Drive for storage
    """

    # Google GenAI SDK config
    IMAGE_MODEL = "gemini-3-pro-image-preview"  # Latest Gemini 3 Pro Image (Nano Banana Pro) model
    
    # Drive folder structure: Project → Content Output → Graphics (Final)
    CONTENT_OUTPUT_FOLDER = "04 - Content Output"
    GRAPHICS_FOLDER = "Graphics (Final)"

    # Domain-wide delegation subject (user to impersonate for Drive quota)
    # Set via GOOGLE_DELEGATION_SUBJECT environment variable
    DELEGATION_SUBJECT = os.getenv("GOOGLE_DELEGATION_SUBJECT", "")

    def __init__(self):
        # Get Gemini API key (same as blog generation)
        self.api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY, GEMINI_API_KEY, or GOOGLE_GEMINI_API_KEY environment variable required")
        
        # Initialize Google GenAI client
        try:
            from google import genai
            from google.genai import types
            self.client = genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(api_version='v1alpha')  # Use v1alpha for preview models
            )
            self._genai = genai
            self._types = types
            logger.info(f"Image generator initialized (model: {self.IMAGE_MODEL}, backend: google-genai SDK)")
        except ImportError:
            raise ImportError("google-genai package required. Install with: pip install google-genai")
        
        # Initialize Google Drive service
        self.drive_service = self._init_drive_service()
    
    def _init_drive_service(self):
        """Initialize Google Drive API service with domain-wide delegation."""
        # Try multiple env var names for flexibility (different secrets use different names)
        sa_json = (
            os.getenv("GOOGLE_SERVICE_ACCOUNT") or  # Modal google-service-account secret
            os.getenv("SERVICE_ACCOUNT_JSON") or     # gmail-proxy style
            os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON") or
            os.getenv("GOOGLE_CREDENTIALS")
        )
        if not sa_json:
            logger.warning("No service account JSON found in environment")
            return None
        
        try:
            sa_info = json.loads(sa_json)
            logger.info(f"Initializing Drive service as: {sa_info.get('client_email', 'unknown')}")
            
            # Create base credentials
            credentials = service_account.Credentials.from_service_account_info(
                sa_info,
                scopes=["https://www.googleapis.com/auth/drive"]
            )
            
            # Apply domain-wide delegation if configured
            # This allows the SA to use the user's Drive quota
            if self.DELEGATION_SUBJECT:
                credentials = credentials.with_subject(self.DELEGATION_SUBJECT)
                logger.info(f"Using domain-wide delegation as: {self.DELEGATION_SUBJECT}")
            else:
                logger.info("Using service account credentials (no delegation)")
            
            return build("drive", "v3", credentials=credentials)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse service account JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize Drive service: {e}")
            return None

    async def generate(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        """
        Generate image for a blog article.
        
        Steps:
        1. Build image prompt from article context
        2. Generate image with Gemini 3 Pro Image via OpenRouter
        3. Upload to Google Drive
        4. Make publicly viewable
        5. Return URL and metadata
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting image generation for: {request.headline[:50]}...")
            
            # Step 1: Build image prompt
            prompt = self._build_image_prompt(request)
            alt_text = self._generate_alt_text(request)
            
            logger.info(f"Generated prompt ({len(prompt)} chars)")
            
            # Step 2: Generate image with Google GenAI SDK
            image_bytes = await self._generate_image(prompt)
            
            logger.info(f"Generated image ({len(image_bytes)} bytes)")
            
            # Step 3: Upload to Drive (or return base64 if Drive unavailable)
            drive_file_id = None
            image_url = ""
            
            if request.project_folder_id and self.drive_service:
                try:
                    target_folder_id = await self._get_graphics_folder(request.project_folder_id)
                    if not target_folder_id:
                        target_folder_id = request.project_folder_id
                        logger.warning(f"Could not find Graphics folder, uploading to project folder: {target_folder_id}")
                    
                    file_name = f"{self._slugify(request.keyword)}_{int(time.time())}.png"
                    drive_file_id = await self._upload_to_drive(image_bytes, file_name, target_folder_id)
                    
                    # Make publicly viewable
                    if drive_file_id:
                        await self._make_public(drive_file_id)
                        image_url = f"https://drive.google.com/uc?export=view&id={drive_file_id}"
                        logger.info(f"Image uploaded to Drive: {drive_file_id}")
                except Exception as drive_error:
                    logger.warning(f"Drive upload failed: {drive_error}, returning base64 image data")
                    # Fallback: return base64 image data
                    image_b64 = base64.b64encode(image_bytes).decode('utf-8')
                    image_url = f"data:image/png;base64,{image_b64}"
            else:
                # No Drive configured - return base64
                logger.info("No Drive folder ID or Drive service, returning base64 image")
                image_b64 = base64.b64encode(image_bytes).decode('utf-8')
                image_url = f"data:image/png;base64,{image_b64}"
            generation_time = time.time() - start_time
            
            logger.info(f"Image uploaded to Drive: {drive_file_id} ({generation_time:.1f}s)")
            
            return ImageGenerationResponse(
                success=True,
                image_url=image_url,
                alt_text=alt_text,
                drive_file_id=drive_file_id,
                generation_time_seconds=generation_time,
                prompt_used=prompt,
            )
            
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return ImageGenerationResponse(
                success=False,
                generation_time_seconds=time.time() - start_time,
                error=str(e),
            )

    def _build_image_prompt(self, request: ImageGenerationRequest) -> str:
        """
        Build a concise image prompt optimized for natural, editorial-style results.
        
        Key principles:
        - Specific but not over-specified (Gemini works better with cleaner prompts)
        - Real photography terminology triggers realistic output
        - Describe what you WANT, not what to avoid (negative prompts unreliable)
        - Consistent aspect ratio for blog layouts
        """
        
        # Build the core visual description based on the topic
        topic_desc = self._get_topic_visual(request.keyword, request.company_data.industry)
        
        # Get style based on industry
        style = self._get_industry_style(request.company_data.industry)
        
        prompt_parts = [
            # Core request - clear and specific
            f"Editorial photograph for a business magazine article about {request.keyword}.",
            f"",
            f"Scene: {topic_desc}",
            f"",
            # Photography style - concise technical specs
            f"Photography style:",
            f"- Shot on Canon 5D Mark IV with 35mm lens at f/2.8, ISO 400",
            f"- {style['color_tone']}",
            f"- Natural window light, soft shadows, not harsh or uniform",
            f"- Rule of thirds composition, subject not centered",
            f"- Shallow depth of field with natural background blur",
            f"- Subtle film grain, authentic textures",
            f"",
            # Key realism triggers
            f"Important: Candid documentary moment, not posed. Real office environment with natural wear and personal items visible. No text or logos in image.",
            f"",
            # Aspect ratio - critical for blog consistency
            f"Aspect ratio: 16:9 wide landscape format",
            f"",
            f"Style reference: Editorial photography from The New York Times or Bloomberg Businessweek",
        ]
        
        # Add custom instructions if provided
        if request.company_data.custom_prompt_instructions:
            prompt_parts.extend([
                f"",
                f"Additional requirements: {request.company_data.custom_prompt_instructions}",
            ])
        
        return "\n".join(prompt_parts)
    
    def _get_industry_style(self, industry: str) -> dict:
        """Get color/style preferences based on industry."""
        industry_lower = industry.lower() if industry else ""
        
        styles = {
            "technology": {"color_tone": "Cool neutral tones, modern clean aesthetic"},
            "finance": {"color_tone": "Warm amber tones, sophisticated classic feel"},
            "healthcare": {"color_tone": "Soft warm tones, calming and professional"},
            "manufacturing": {"color_tone": "Industrial neutral tones, high contrast"},
            "retail": {"color_tone": "Bright natural tones, inviting atmosphere"},
            "creative": {"color_tone": "Vibrant but natural colors, artistic energy"},
            "legal": {"color_tone": "Muted professional tones, traditional gravitas"},
            "education": {"color_tone": "Warm inviting tones, approachable feel"},
        }
        
        # Match industry to style
        for key, style in styles.items():
            if key in industry_lower:
                return style
        
        # Default professional style
        return {"color_tone": "Kodak Portra 400 color science - muted warm tones, natural skin"}
    
    def _get_topic_visual(self, keyword: str, industry: str) -> str:
        """
        Generate a specific, grounded visual description based on topic.
        Focuses on real-world scenarios rather than abstract concepts.
        """
        keyword_lower = keyword.lower()
        industry_lower = industry.lower() if industry else ""
        
        # Map common topics to specific, photographable scenes
        # AI & Technology
        if any(term in keyword_lower for term in ['ai', 'artificial intelligence', 'machine learning', 'automation']):
            return "A small team of developers in a modern office, gathered around a laptop. Coffee cups and notebooks scattered naturally. One person gesturing while explaining to colleagues. Lived-in workspace with personal items."
        
        # Customer Experience
        elif any(term in keyword_lower for term in ['customer service', 'support', 'helpdesk', 'customer experience', 'cx']):
            return "Customer service representative at their desk, headset on, genuinely engaged in conversation. Personal items visible - family photo, plant, coffee mug. Natural daylight from nearby window."
        
        # Sustainability & Environment
        elif any(term in keyword_lower for term in ['sustainability', 'green', 'eco', 'environment', 'carbon', 'renewable']):
            return "Workers in a warehouse handling boxes with recycling symbols, electric forklift in background. Industrial space with natural light from skylights. Real workers in practical clothing."
        
        # Marketing & Sales
        elif any(term in keyword_lower for term in ['marketing', 'advertising', 'brand', 'sales', 'growth', 'leads']):
            return "Creative team brainstorming in a conference room, whiteboard with sketches visible. Laptops open, some people standing, relaxed but focused. Afternoon light through blinds."
        
        # Finance & Investment
        elif any(term in keyword_lower for term in ['finance', 'investment', 'banking', 'accounting', 'budget', 'roi']):
            return "Financial analyst at desk with multiple monitors showing charts. Reading glasses, pen in hand, concentrated expression. Traditional office with wood accents and city view."
        
        # Healthcare & Medical
        elif any(term in keyword_lower for term in ['healthcare', 'medical', 'health', 'patient', 'clinical', 'hospital']):
            return "Healthcare professional consulting with a patient in a modern clinic. Warm, reassuring atmosphere. Medical equipment visible but approachable. Natural light, calm colors."
        
        # Software & Tech
        elif any(term in keyword_lower for term in ['software', 'saas', 'digital', 'tech', 'app', 'platform', 'cloud']):
            return "Software engineers pair programming at standing desk, one pointing at screen. Modern tech office with exposed brick, plants. Casual dress, authentic working moment."
        
        # Startup & Business
        elif any(term in keyword_lower for term in ['startup', 'entrepreneur', 'business', 'strategy', 'management']):
            return "Small team meeting in a coworking space, founder presenting to 3-4 people. Laptops, notebooks, whiteboards with post-its. Energy of a real working session."
        
        # E-commerce & Retail
        elif any(term in keyword_lower for term in ['ecommerce', 'retail', 'shopping', 'store', 'fulfillment', 'inventory']):
            return "Warehouse worker scanning packages with handheld device, shelves of products in background. Real fulfillment center with natural movement and activity."
        
        # Education & Training
        elif any(term in keyword_lower for term in ['education', 'learning', 'training', 'onboarding', 'course', 'workshop']):
            return "Adult professional learning session, instructor at whiteboard with small group engaged. Corporate training room with natural light, real learning moment."
        
        # HR & People
        elif any(term in keyword_lower for term in ['hr', 'hiring', 'recruitment', 'employee', 'talent', 'workforce', 'team']):
            return "HR professional in a one-on-one meeting with a candidate or employee. Comfortable office setting, warm atmosphere. Coffee cups on table, genuine conversation."
        
        # Legal & Compliance
        elif any(term in keyword_lower for term in ['legal', 'compliance', 'regulation', 'contract', 'law', 'policy']):
            return "Professional reviewing documents in a traditional office with bookshelves. Pen in hand, serious but not stern expression. Warm wood tones, afternoon light."
        
        # Cybersecurity
        elif any(term in keyword_lower for term in ['security', 'cyber', 'data protection', 'privacy', 'breach']):
            return "IT security professional at workstation with multiple monitors showing dashboards. Focused concentration, modern security operations center. Blue ambient lighting."
        
        # Manufacturing & Operations
        elif any(term in keyword_lower for term in ['manufacturing', 'production', 'factory', 'operations', 'supply chain', 'logistics']):
            return "Factory floor with workers operating machinery or reviewing quality. Industrial setting with natural light from high windows. Safety equipment visible, real work in progress."
        
        # Construction & Real Estate
        elif any(term in keyword_lower for term in ['construction', 'building', 'real estate', 'property', 'architecture']):
            return "Construction site or office with blueprints spread on table. Project managers reviewing plans, hard hats visible. Mix of indoor/outdoor industrial environment."
        
        # Food & Hospitality
        elif any(term in keyword_lower for term in ['food', 'restaurant', 'hospitality', 'hotel', 'catering', 'culinary']):
            return "Commercial kitchen or restaurant setting with staff at work. Professional but warm atmosphere. Natural steam, activity, authentic service moment."
        
        # Data & Analytics
        elif any(term in keyword_lower for term in ['data', 'analytics', 'insights', 'metrics', 'reporting', 'dashboard']):
            return "Analyst at desk reviewing data visualizations on screen, notebook with handwritten notes nearby. Modern office, focused but not sterile. Coffee cup, personal items."
        
        # Communication & Collaboration
        elif any(term in keyword_lower for term in ['communication', 'collaboration', 'meeting', 'remote', 'hybrid', 'video']):
            return "Team in hybrid meeting - some in conference room, others on video screen. Laptops, notebooks, engaged discussion. Modern office with natural light."
        
        else:
            # Smart generic fallback - use industry context
            if industry_lower:
                return f"Professional in {industry} industry setting, engaged in work related to {keyword}. Authentic office or workspace environment with natural lighting. Real working moment with personal items visible, not posed."
            else:
                return f"Professional team in modern office environment discussing {keyword}. Natural meeting room setting with laptops and notebooks. Candid working moment with natural light."

    def _generate_alt_text(self, request: ImageGenerationRequest) -> str:
        """Generate alt text for the image."""
        # Create concise alt text based on headline
        alt_text = f"Blog image: {request.headline}"
        
        # Truncate to 125 chars max for accessibility
        if len(alt_text) > 125:
            alt_text = alt_text[:122] + "..."
        
        return alt_text

    async def _generate_image(self, prompt: str, max_retries: int = 3) -> bytes:
        """
        Generate image using Google GenAI SDK (gemini-3-pro-image-preview).
        Includes retry logic with exponential backoff.
        """
        last_error = None
        wait_time = 5.0
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"Image generation attempt {attempt + 1}/{max_retries}")
                
                # Generate image using Google GenAI SDK
                # Run synchronous call in executor to avoid blocking event loop
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.client.models.generate_content(
                        model=self.IMAGE_MODEL,
                        contents=prompt,
                        config=self._types.GenerateContentConfig(
                            response_modalities=[self._types.Modality.TEXT, self._types.Modality.IMAGE]
                        )
                    )
                )
                
                # Extract image from response
                image_bytes = self._extract_image_from_genai_response(response)
                if image_bytes:
                    logger.info(f"✅ Successfully generated image ({len(image_bytes)} bytes)")
                    return image_bytes
                
                # No image in response - might be a content policy issue, retry
                logger.warning(f"No image in response, retrying ({attempt + 1}/{max_retries})")
                await self._async_sleep(wait_time)
                wait_time *= 2
                
            except Exception as e:
                last_error = str(e)
                error_str = str(e).lower()
                
                # Check if error is retryable
                retryable = (
                    "rate limit" in error_str or
                    "429" in error_str or
                    "quota" in error_str or
                    "timeout" in error_str or
                    "503" in error_str or
                    "temporarily unavailable" in error_str
                )
                
                if not retryable:
                    logger.error(f"Non-retryable error: {e}")
                    raise
                
                if attempt < max_retries - 1:
                    logger.warning(f"Retryable error (attempt {attempt + 1}): {e}, retrying in {wait_time}s...")
                    await self._async_sleep(wait_time)
                    wait_time *= 2
                else:
                    raise
        
        raise ValueError(f"Failed after {max_retries} attempts. Last error: {last_error}")
    
    async def _async_sleep(self, seconds: float):
        """Async sleep helper."""
        await asyncio.sleep(seconds)
    
    def _extract_image_from_genai_response(self, response) -> Optional[bytes]:
        """Extract image bytes from Google GenAI SDK response."""
        try:
            logger.debug(f"Extracting image from response type: {type(response)}")
            
            if not response:
                logger.warning("Empty response")
                return None
            
            # Log response structure for debugging
            if hasattr(response, '__dict__'):
                logger.debug(f"Response attributes: {list(response.__dict__.keys())}")
            
            if not hasattr(response, 'candidates'):
                logger.warning("No candidates attribute in response")
                # Try alternative response structure
                if hasattr(response, 'text'):
                    logger.warning("Response has 'text' attribute - might be text-only response")
                return None
            
            candidates = response.candidates
            if not candidates or len(candidates) == 0:
                logger.warning("Empty candidates in GenAI response")
                return None
            
            candidate = candidates[0]
            if not hasattr(candidate, 'content') or not candidate.content:
                logger.warning("No content in candidate")
                return None
            
            content = candidate.content
            if not hasattr(content, 'parts') or not content.parts:
                logger.warning("No parts in content")
                return None
            
            logger.debug(f"Found {len(content.parts)} parts in content")
            
            # Look for image data in parts
            for i, part in enumerate(content.parts):
                logger.debug(f"Part {i}: type={type(part)}, attributes={dir(part) if hasattr(part, '__dict__') else 'N/A'}")
                
                # Check for inline_data
                if hasattr(part, 'inline_data') and part.inline_data:
                    inline_data = part.inline_data
                    logger.debug(f"Found inline_data: {type(inline_data)}, attributes={dir(inline_data) if hasattr(inline_data, '__dict__') else 'N/A'}")
                    
                    # Check if data is bytes or base64 string
                    if hasattr(inline_data, 'data'):
                        image_data = inline_data.data
                        logger.debug(f"Image data type: {type(image_data)}, length: {len(image_data) if image_data else 0}")
                        
                        if image_data:
                            # Check if it's already bytes or needs decoding
                            if isinstance(image_data, bytes):
                                # Already bytes - check if it's valid image format
                                if len(image_data) > 100:
                                    # Check for PNG signature
                                    if image_data[:8] == b'\x89PNG\r\n\x1a\n':
                                        logger.info(f"Found valid PNG image data ({len(image_data)} bytes)")
                                        return image_data
                                    # Check for JPEG signature
                                    elif image_data[:3] == b'\xff\xd8\xff':
                                        logger.info(f"Found valid JPEG image data ({len(image_data)} bytes)")
                                        return image_data
                                    else:
                                        logger.warning(f"Image data doesn't match PNG or JPEG format (first bytes: {image_data[:20]})")
                                else:
                                    logger.warning(f"Image data too small ({len(image_data)} bytes)")
                            elif isinstance(image_data, str):
                                # Try base64 decode
                                try:
                                    decoded = base64.b64decode(image_data)
                                    if len(decoded) > 100:
                                        # Check for PNG signature
                                        if decoded[:8] == b'\x89PNG\r\n\x1a\n':
                                            logger.info(f"Found base64-encoded PNG image ({len(decoded)} bytes)")
                                            return decoded
                                        # Check for JPEG signature
                                        elif decoded[:3] == b'\xff\xd8\xff':
                                            logger.info(f"Found base64-encoded JPEG image ({len(decoded)} bytes)")
                                            return decoded
                                        else:
                                            logger.warning(f"Decoded data doesn't match PNG or JPEG format")
                                    else:
                                        logger.warning(f"Decoded data too small ({len(decoded)} bytes)")
                                except Exception as e:
                                    logger.warning(f"Failed to decode base64: {e}")
                    
                    # Check mime_type
                    if hasattr(inline_data, 'mime_type'):
                        logger.debug(f"MIME type: {inline_data.mime_type}")
                
                # Also check for mime_type directly on part
                if hasattr(part, 'mime_type') and part.mime_type and part.mime_type.startswith('image/'):
                    logger.debug(f"Part has image mime_type: {part.mime_type}")
                    if hasattr(part, 'inline_data') and part.inline_data:
                        if hasattr(part.inline_data, 'data'):
                            image_data = part.inline_data.data
                            if image_data:
                                if isinstance(image_data, bytes):
                                    return image_data
                                elif isinstance(image_data, str):
                                    try:
                                        return base64.b64decode(image_data)
                                    except:
                                        pass
            
            logger.warning("No valid image data found in response parts")
            logger.debug(f"Response structure: candidates={len(candidates)}, parts={len(content.parts) if content.parts else 0}")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting image from GenAI response: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None
    

    async def _get_graphics_folder(self, project_folder_id: str) -> Optional[str]:
        """Navigate to Graphics (Final) folder within project structure."""
        if not self.drive_service:
            return None
        
        try:
            # Find Content Output folder
            content_folder = self._find_folder(project_folder_id, self.CONTENT_OUTPUT_FOLDER)
            if not content_folder:
                # Create if doesn't exist
                content_folder = self._create_folder(self.CONTENT_OUTPUT_FOLDER, project_folder_id)
            
            # Find or create Graphics folder
            graphics_folder = self._find_folder(content_folder, self.GRAPHICS_FOLDER)
            if not graphics_folder:
                graphics_folder = self._create_folder(self.GRAPHICS_FOLDER, content_folder)
            
            return graphics_folder
            
        except Exception as e:
            logger.error(f"Failed to get graphics folder: {e}")
            return None

    def _find_folder(self, parent_id: str, name: str) -> Optional[str]:
        """Find a folder by name within a parent folder."""
        if not self.drive_service:
            return None
            
        query = f"name='{name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = self.drive_service.files().list(
            q=query,
            spaces="drive",
            fields="files(id, name)",
        ).execute()
        
        files = results.get("files", [])
        return files[0]["id"] if files else None

    def _create_folder(self, name: str, parent_id: str) -> str:
        """Create a folder in Drive."""
        if not self.drive_service:
            raise ValueError("Drive service not initialized")
            
        file_metadata = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        }
        
        folder = self.drive_service.files().create(
            body=file_metadata,
            fields="id"
        ).execute()
        
        return folder.get("id")

    async def _upload_to_drive(
        self, 
        image_bytes: bytes, 
        file_name: str, 
        folder_id: Optional[str] = None
    ) -> str:
        """Upload image to Google Drive."""
        if not self.drive_service:
            raise ValueError("Drive service not initialized - cannot upload")
        
        file_metadata = {"name": file_name}
        if folder_id:
            file_metadata["parents"] = [folder_id]
        
        media = MediaInMemoryUpload(image_bytes, mimetype="image/png")
        
        file = self.drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id"
        ).execute()
        
        return file.get("id", "")

    async def _make_public(self, file_id: str) -> None:
        """Make a Drive file publicly viewable."""
        if not self.drive_service:
            return
        
        try:
            self.drive_service.permissions().create(
                fileId=file_id,
                body={"type": "anyone", "role": "reader"},
            ).execute()
        except Exception as e:
            logger.warning(f"Failed to make file public: {e}")

    def _slugify(self, text: str) -> str:
        """Convert text to URL-safe slug."""
        slug = text.lower()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'[\s_]+', '-', slug)
        slug = re.sub(r'-+', '-', slug)
        return slug.strip('-')[:50]


# Singleton instance
_generator: Optional[ImageGenerator] = None


def get_generator() -> ImageGenerator:
    """Get or create image generator instance."""
    global _generator
    if _generator is None:
        _generator = ImageGenerator()
    return _generator
