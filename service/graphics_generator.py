"""
Graphics Generation Service
Generates HTML-based graphics (openfigma style) and converts to PNG.
Perfect for blog graphics: headlines, quotes, metrics, CTAs, infographics.

Uses:
- HTML/CSS templates (dark theme, glassmorphism)
- Playwright for HTML → PNG conversion
- Google Drive for storage
"""

import os
import re
import time
import base64
import asyncio
import logging
from typing import Optional, Dict, Any, Literal
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload

logger = logging.getLogger(__name__)


@dataclass
class GraphicsGenerationRequest:
    """Request for graphics generation."""
    graphic_type: Literal["headline", "quote", "metric", "cta", "infographic"]
    content: Dict[str, Any]  # Type-specific content
    company_data: Optional[Dict[str, Any]] = None
    project_folder_id: Optional[str] = None
    dimensions: tuple = (1080, 1350)  # Default: Instagram story size


@dataclass
class GraphicsGenerationResponse:
    """Response from graphics generation."""
    success: bool
    image_url: str = ""
    alt_text: str = ""
    drive_file_id: str = ""
    generation_time_seconds: float = 0.0
    error: Optional[str] = None


class GraphicsGenerator:
    """
    Generates HTML-based graphics (openfigma style) and converts to PNG.
    
    Supports:
    - Headlines (case study style)
    - Quotes (testimonial style)
    - Metrics (statistics with icons)
    - CTAs (call-to-action cards)
    - Infographics (diagram-style)
    """
    
    # Drive folder structure: Project → Content Output → Graphics (Final)
    CONTENT_OUTPUT_FOLDER = "04 - Content Output"
    GRAPHICS_FOLDER = "Graphics (Final)"
    
    # Domain-wide delegation subject
    DELEGATION_SUBJECT = os.getenv("GOOGLE_DELEGATION_SUBJECT", "")
    
    def __init__(self):
        # Initialize Google Drive service
        self.drive_service = self._init_drive_service()
        
        # Check for Playwright
        try:
            from playwright.async_api import async_playwright
            self._playwright_available = True
            logger.info("Graphics generator initialized (Playwright available)")
        except ImportError:
            self._playwright_available = False
            logger.warning("Playwright not available - graphics generation will be limited")
    
    def _init_drive_service(self):
        """Initialize Google Drive API service with domain-wide delegation."""
        try:
            service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON") or os.getenv("GOOGLE_SERVICE_ACCOUNT")
            if not service_account_json:
                logger.warning("GOOGLE_SERVICE_ACCOUNT_JSON not set - Drive upload disabled")
                return None
            
            # Parse JSON string if needed
            if isinstance(service_account_json, str):
                import json
                service_account_info = json.loads(service_account_json)
            else:
                service_account_info = service_account_json
            
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=['https://www.googleapis.com/auth/drive.file'],
            )
            
            # Use domain-wide delegation if subject provided
            if self.DELEGATION_SUBJECT:
                credentials = credentials.with_subject(self.DELEGATION_SUBJECT)
                logger.info(f"Using domain-wide delegation: {self.DELEGATION_SUBJECT}")
            
            drive_service = build('drive', 'v3', credentials=credentials)
            logger.info("Drive service initialized")
            return drive_service
            
        except Exception as e:
            logger.error(f"Failed to initialize Drive service: {e}")
            return None
    
    async def generate(self, request: GraphicsGenerationRequest) -> GraphicsGenerationResponse:
        """
        Generate graphics from HTML template and convert to PNG.
        
        Steps:
        1. Generate HTML from template
        2. Convert HTML to PNG using Playwright
        3. Upload to Google Drive (or return base64)
        4. Make publicly viewable
        5. Return URL and metadata
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting graphics generation: {request.graphic_type}")
            
            # Step 1: Generate HTML
            html_content = self._generate_html(request)
            logger.info(f"Generated HTML ({len(html_content)} chars)")
            
            # Step 2: Convert HTML to PNG
            if not self._playwright_available:
                raise ValueError("Playwright not available - install with: pip install playwright && playwright install chromium")
            
            image_bytes = await self._html_to_png(html_content, request.dimensions)
            logger.info(f"Converted to PNG ({len(image_bytes)} bytes)")
            
            # Step 3: Upload to Drive (or return base64)
            drive_file_id = None
            image_url = ""
            
            if request.project_folder_id and self.drive_service:
                try:
                    target_folder_id = await self._get_graphics_folder(request.project_folder_id)
                    if not target_folder_id:
                        target_folder_id = request.project_folder_id
                    
                    file_name = f"graphic_{request.graphic_type}_{int(time.time())}.png"
                    drive_file_id = await self._upload_to_drive(image_bytes, file_name, target_folder_id)
                    
                    if drive_file_id:
                        await self._make_public(drive_file_id)
                        image_url = f"https://drive.google.com/uc?export=view&id={drive_file_id}"
                        logger.info(f"Graphics uploaded to Drive: {drive_file_id}")
                except Exception as drive_error:
                    logger.warning(f"Drive upload failed: {drive_error}, returning base64")
                    image_b64 = base64.b64encode(image_bytes).decode('utf-8')
                    image_url = f"data:image/png;base64,{image_b64}"
            else:
                # No Drive configured - return base64
                logger.info("No Drive folder ID or Drive service, returning base64 image")
                image_b64 = base64.b64encode(image_bytes).decode('utf-8')
                image_url = f"data:image/png;base64,{image_b64}"
            
            generation_time = time.time() - start_time
            
            return GraphicsGenerationResponse(
                success=True,
                image_url=image_url,
                alt_text=self._generate_alt_text(request),
                drive_file_id=drive_file_id or "",
                generation_time_seconds=generation_time,
            )
            
        except Exception as e:
            generation_time = time.time() - start_time
            logger.error(f"Graphics generation failed: {e}", exc_info=True)
            return GraphicsGenerationResponse(
                success=False,
                generation_time_seconds=generation_time,
                error=str(e),
            )
    
    def _generate_html(self, request: GraphicsGenerationRequest) -> str:
        """Generate HTML content based on graphic type."""
        if request.graphic_type == "headline":
            return self._generate_headline_html(request)
        elif request.graphic_type == "quote":
            return self._generate_quote_html(request)
        elif request.graphic_type == "metric":
            return self._generate_metric_html(request)
        elif request.graphic_type == "cta":
            return self._generate_cta_html(request)
        elif request.graphic_type == "infographic":
            return self._generate_infographic_html(request)
        else:
            raise ValueError(f"Unknown graphic type: {request.graphic_type}")
    
    def _generate_headline_html(self, request: GraphicsGenerationRequest) -> str:
        """Generate headline graphic HTML (case study style - openfigma quality)."""
        content = request.content
        headline = content.get("headline", "")
        subheadline = content.get("subheadline", "")
        badge_text = content.get("badge", "Case Study")
        company_name = request.company_data.get("name", "") if request.company_data else ""
        show_logos = content.get("show_logos", True)
        
        bold_parts = content.get("bold_parts", [])
        muted_parts = content.get("muted_parts", [])
        
        logos_html = ""
        if show_logos and company_name:
            logos_html = f"""
  <div class="logos-card">
    <div class="logo">
      <svg class="logo-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <path d="M4 6h16M4 12h16M4 18h10"/>
      </svg>
      {company_name.upper()}
    </div>
    <div class="logo-divider"></div>
    <div class="logo">
      <div class="scaile-icon"></div>
      SCAILE
    </div>
  </div>"""
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Headline Graphic</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: 'Inter', -apple-system, sans-serif;
      background: #f8f8f8;
      width: {request.dimensions[0]}px;
      height: {request.dimensions[1]}px;
      display: flex;
      flex-direction: column;
      padding: 60px 80px 80px;
      position: relative;
    }}
    body::before {{
      content: '';
      position: absolute;
      inset: 0;
      background-image: 
        linear-gradient(rgba(0,0,0,0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,0,0,0.025) 1px, transparent 1px);
      background-size: 20px 20px;
      pointer-events: none;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
      background: white;
      border: 1px solid #e8e8e8;
      border-radius: 100px;
      padding: 12px 24px;
      font-size: 16px;
      font-weight: 600;
      color: #1a1a1a;
      box-shadow: 0 1px 4px rgba(0,0,0,0.04);
      width: fit-content;
      margin-bottom: 50px;
    }}
    .badge svg {{ width: 20px; height: 20px; }}
    .headline {{
      text-align: center;
      font-size: 56px;
      font-weight: 800;
      line-height: 1.15;
      letter-spacing: -0.03em;
      margin-bottom: auto;
      padding: 0;
      max-width: 100%;
    }}
    .headline .bold {{ color: #1a1a1a; }}
    .headline .muted {{ color: #b0b0b0; }}
    .subheadline {{
      margin-top: 30px;
      font-size: 24px;
      font-weight: 500;
      color: #6b7280;
      text-align: center;
    }}
    .logos-card {{
      background: #f0f0f0;
      border-radius: 28px;
      padding: 40px 60px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 40px;
      margin-top: 30px;
    }}
    .logo {{
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 28px;
      font-weight: 800;
      color: #1a1a1a;
      letter-spacing: -0.02em;
    }}
    .logo-icon {{ width: 32px; height: 32px; }}
    .logo-divider {{ width: 1px; height: 36px; background: #d0d0d0; }}
    .scaile-icon {{
      width: 30px;
      height: 30px;
      background: linear-gradient(135deg, #6366f1, #8b5cf6);
      border-radius: 8px;
    }}
  </style>
</head>
<body>
  <div class="badge">
    <svg viewBox="0 0 24 24" fill="currentColor">
      <rect x="3" y="3" width="7" height="7" rx="1"/>
      <rect x="14" y="3" width="7" height="7" rx="1"/>
      <rect x="3" y="14" width="7" height="7" rx="1"/>
      <rect x="14" y="14" width="7" height="7" rx="1"/>
    </svg>
    {badge_text}
  </div>

  <h1 class="headline">
    {self._format_headline(headline, bold_parts, muted_parts)}
  </h1>
  {f'<p class="subheadline">{subheadline}</p>' if subheadline else ''}
{logos_html}
</body>
</html>"""
    
    def _format_headline(self, headline: str, bold_parts: list, muted_parts: list) -> str:
        """Format headline with bold/muted styling."""
        if not bold_parts and not muted_parts:
            # No styling specified - return as bold
            return f'<span class="bold">{headline}</span>'
        
        words = headline.split(" ")
        formatted = []
        for word in words:
            word_clean = re.sub(r'[^\w]', '', word.lower())
            if bold_parts and any(word_clean in re.sub(r'[^\w]', '', p.lower()) for p in bold_parts):
                formatted.append(f'<span class="bold">{word}</span>')
            elif muted_parts and any(word_clean in re.sub(r'[^\w]', '', p.lower()) for p in muted_parts):
                formatted.append(f'<span class="muted">{word}</span>')
            else:
                formatted.append(f'<span class="bold">{word}</span>')
        return " ".join(formatted)
    
    def _generate_quote_html(self, request: GraphicsGenerationRequest) -> str:
        """Generate quote graphic HTML (testimonial style - openfigma quality)."""
        content = request.content
        quote = content.get("quote", "")
        quote_emphasis = content.get("quote_emphasis", [])  # Parts to emphasize with <strong>
        author = content.get("author", "")
        role = content.get("role", "")
        author_avatar = content.get("author_avatar", "")
        badge_text = content.get("badge", "Case Study")
        company_name = request.company_data.get("name", "") if request.company_data else ""
        show_logos = content.get("show_logos", True)
        
        # Format quote with emphasis
        formatted_quote = quote
        for emphasis in quote_emphasis:
            formatted_quote = formatted_quote.replace(emphasis, f"<strong>{emphasis}</strong>")
        
        logos_html = ""
        if show_logos and company_name:
            logos_html = f"""
  <div class="logos-card">
    <div class="logo">
      <svg class="logo-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <path d="M4 6h16M4 12h16M4 18h10"/>
      </svg>
      {company_name.upper()}
    </div>
    <div class="logo-divider"></div>
    <div class="logo">
      <div class="scaile-icon"></div>
      SCAILE
    </div>
  </div>"""
        
        avatar_html = ""
        if author_avatar:
            avatar_html = f'<div class="author-avatar"><img src="{author_avatar}" alt="{author}"></div>'
        else:
            # Generate placeholder avatar
            initials = "".join([n[0].upper() for n in author.split()[:2]]) if author else "?"
            avatar_html = f'<div class="author-avatar"><div class="avatar-placeholder">{initials}</div></div>'
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Quote Graphic</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: 'Inter', -apple-system, sans-serif;
      background: #f8f8f8;
      width: {request.dimensions[0]}px;
      height: {request.dimensions[1]}px;
      display: flex;
      flex-direction: column;
      padding: 60px;
      position: relative;
    }}
    body::before {{
      content: '';
      position: absolute;
      inset: 0;
      background-image: 
        linear-gradient(rgba(0,0,0,0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,0,0,0.025) 1px, transparent 1px);
      background-size: 20px 20px;
      pointer-events: none;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
      background: white;
      border: 1px solid #e8e8e8;
      border-radius: 100px;
      padding: 12px 24px;
      font-size: 16px;
      font-weight: 600;
      color: #1a1a1a;
      box-shadow: 0 1px 4px rgba(0,0,0,0.04);
      width: fit-content;
      margin-bottom: 40px;
    }}
    .badge svg {{ width: 20px; height: 20px; }}
    .quote-card {{
      background: white;
      border-radius: 28px;
      padding: 50px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.04);
      flex: 1;
      display: flex;
      flex-direction: column;
      justify-content: center;
    }}
    .quote-text {{
      font-size: 32px;
      line-height: 1.45;
      color: #6b7280;
      margin-bottom: 50px;
    }}
    .quote-text strong {{
      color: #1a1a1a;
      font-weight: 700;
    }}
    .quote-author {{
      display: flex;
      align-items: center;
      gap: 20px;
    }}
    .author-avatar {{
      width: 80px;
      height: 80px;
      border-radius: 50%;
      background: #e5e5e5;
      overflow: hidden;
      flex-shrink: 0;
    }}
    .author-avatar img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
    }}
    .avatar-placeholder {{
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 32px;
      font-weight: 700;
      color: #6b7280;
      background: linear-gradient(135deg, #6366f1, #8b5cf6);
      color: white;
    }}
    .author-info {{
      display: flex;
      flex-direction: column;
    }}
    .author-name {{
      font-size: 26px;
      font-weight: 700;
      color: #1a1a1a;
    }}
    .author-role {{
      font-size: 22px;
      color: #6b7280;
      margin-top: 4px;
    }}
    .logos-card {{
      background: #f0f0f0;
      border-radius: 28px;
      padding: 40px 60px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 40px;
      margin-top: 30px;
    }}
    .logo {{
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 28px;
      font-weight: 800;
      color: #1a1a1a;
      letter-spacing: -0.02em;
    }}
    .logo-icon {{ width: 32px; height: 32px; }}
    .logo-divider {{ width: 1px; height: 36px; background: #d0d0d0; }}
    .scaile-icon {{
      width: 30px;
      height: 30px;
      background: linear-gradient(135deg, #6366f1, #8b5cf6);
      border-radius: 8px;
    }}
  </style>
</head>
<body>
  <div class="badge">
    <svg viewBox="0 0 24 24" fill="currentColor">
      <rect x="3" y="3" width="7" height="7" rx="1"/>
      <rect x="14" y="3" width="7" height="7" rx="1"/>
      <rect x="3" y="14" width="7" height="7" rx="1"/>
      <rect x="14" y="14" width="7" height="7" rx="1"/>
    </svg>
    {badge_text}
  </div>

  <div class="quote-card">
    <p class="quote-text">"{formatted_quote}"</p>
    <div class="quote-author">
      {avatar_html}
      <div class="author-info">
        <div class="author-name">{author}</div>
        {f'<div class="author-role">{role}</div>' if role else ''}
      </div>
    </div>
  </div>
{logos_html}
</body>
</html>"""
    
    def _generate_metric_html(self, request: GraphicsGenerationRequest) -> str:
        """Generate metric graphic HTML (statistics style - openfigma quality)."""
        content = request.content
        headline = content.get("headline", "")  # Optional headline above metric
        value = content.get("value", "")
        label = content.get("label", "")
        quote = content.get("quote", "")  # Optional quote below metric
        quote_emphasis = content.get("quote_emphasis", [])
        change = content.get("change", "")
        change_type = content.get("change_type", "positive")
        badge_text = content.get("badge", "Case Study")
        company_name = request.company_data.get("name", "") if request.company_data else ""
        show_logos = content.get("show_logos", True)
        
        # Format quote with emphasis
        formatted_quote = quote
        if quote_emphasis:
            for emphasis in quote_emphasis:
                formatted_quote = formatted_quote.replace(emphasis, f"<strong>{emphasis}</strong>")
        
        logos_html = ""
        if show_logos and company_name:
            logos_html = f"""
  <div class="logos-card">
    <div class="logo">
      <svg class="logo-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <path d="M4 6h16M4 12h16M4 18h10"/>
      </svg>
      {company_name.upper()}
    </div>
    <div class="logo-divider"></div>
    <div class="logo">
      <div class="scaile-icon"></div>
      SCAILE
    </div>
  </div>"""
        
        headline_html = ""
        if headline:
            bold_parts = content.get("bold_parts", [])
            muted_parts = content.get("muted_parts", [])
            headline_html = f'<h1 class="headline">{self._format_headline(headline, bold_parts, muted_parts)}</h1>'
        
        quote_html = ""
        if quote:
            quote_html = f'<p class="quote-text">"{formatted_quote}"</p>'
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Metric Graphic</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: 'Inter', -apple-system, sans-serif;
      background: #f8f8f8;
      width: {request.dimensions[0]}px;
      height: {request.dimensions[1]}px;
      display: flex;
      flex-direction: column;
      padding: 60px;
      position: relative;
    }}
    body::before {{
      content: '';
      position: absolute;
      inset: 0;
      background-image: 
        linear-gradient(rgba(0,0,0,0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,0,0,0.025) 1px, transparent 1px);
      background-size: 20px 20px;
      pointer-events: none;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
      background: white;
      border: 1px solid #e8e8e8;
      border-radius: 100px;
      padding: 12px 24px;
      font-size: 16px;
      font-weight: 600;
      color: #1a1a1a;
      box-shadow: 0 1px 4px rgba(0,0,0,0.04);
      width: fit-content;
      margin-bottom: 60px;
    }}
    .badge svg {{ width: 20px; height: 20px; }}
    .headline {{
      font-size: 56px;
      font-weight: 800;
      line-height: 1.15;
      letter-spacing: -0.03em;
      margin-bottom: 50px;
    }}
    .headline .muted {{ color: #b0b0b0; }}
    .headline .bold {{ color: #1a1a1a; }}
    .quote-card {{
      background: white;
      border-radius: 28px;
      padding: 50px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.04);
      flex: 1;
      display: flex;
      flex-direction: column;
      justify-content: center;
    }}
    .metric-value {{
      font-size: 120px;
      font-weight: 800;
      background: linear-gradient(135deg, #6366f1, #8b5cf6);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      margin-bottom: 20px;
      text-align: center;
    }}
    .metric-label {{
      font-size: 28px;
      font-weight: 600;
      color: #1a1a1a;
      margin-bottom: 16px;
      text-align: center;
    }}
    .metric-change {{
      font-size: 20px;
      font-weight: 500;
      color: {'#22c55e' if change_type == 'positive' else '#ef4444'};
      text-align: center;
    }}
    .quote-text {{
      font-size: 30px;
      line-height: 1.5;
      color: #6b7280;
      margin-top: 40px;
    }}
    .quote-text strong {{
      color: #1a1a1a;
      font-weight: 700;
    }}
    .logos-card {{
      background: #f0f0f0;
      border-radius: 28px;
      padding: 40px 60px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 40px;
      margin-top: 30px;
    }}
    .logo {{
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 28px;
      font-weight: 800;
      color: #1a1a1a;
      letter-spacing: -0.02em;
    }}
    .logo-icon {{ width: 32px; height: 32px; }}
    .logo-divider {{ width: 1px; height: 36px; background: #d0d0d0; }}
    .scaile-icon {{
      width: 30px;
      height: 30px;
      background: linear-gradient(135deg, #6366f1, #8b5cf6);
      border-radius: 8px;
    }}
  </style>
</head>
<body>
  <div class="badge">
    <svg viewBox="0 0 24 24" fill="currentColor">
      <rect x="3" y="3" width="7" height="7" rx="1"/>
      <rect x="14" y="3" width="7" height="7" rx="1"/>
      <rect x="3" y="14" width="7" height="7" rx="1"/>
      <rect x="14" y="14" width="7" height="7" rx="1"/>
    </svg>
    {badge_text}
  </div>

  {headline_html}

  <div class="quote-card">
    <div class="metric-value">{value}</div>
    <div class="metric-label">{label}</div>
    {f'<div class="metric-change">{change}</div>' if change else ''}
    {quote_html}
  </div>
{logos_html}
</body>
</html>"""
    
    def _generate_cta_html(self, request: GraphicsGenerationRequest) -> str:
        """Generate CTA graphic HTML (openfigma quality)."""
        content = request.content
        headline = content.get("headline", "")
        description = content.get("description", "")
        button_text = content.get("button_text", "Get Started")
        badge_text = content.get("badge", "Get Started")
        company_name = request.company_data.get("name", "") if request.company_data else ""
        show_logos = content.get("show_logos", True)
        
        logos_html = ""
        if show_logos and company_name:
            logos_html = f"""
  <div class="logos-card">
    <div class="logo">
      <svg class="logo-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <path d="M4 6h16M4 12h16M4 18h10"/>
      </svg>
      {company_name.upper()}
    </div>
    <div class="logo-divider"></div>
    <div class="logo">
      <div class="scaile-icon"></div>
      SCAILE
    </div>
  </div>"""
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CTA Graphic</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: 'Inter', -apple-system, sans-serif;
      background: #f8f8f8;
      width: {request.dimensions[0]}px;
      height: {request.dimensions[1]}px;
      display: flex;
      flex-direction: column;
      padding: 60px;
      position: relative;
    }}
    body::before {{
      content: '';
      position: absolute;
      inset: 0;
      background-image: 
        linear-gradient(rgba(0,0,0,0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,0,0,0.025) 1px, transparent 1px);
      background-size: 20px 20px;
      pointer-events: none;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
      background: white;
      border: 1px solid #e8e8e8;
      border-radius: 100px;
      padding: 12px 24px;
      font-size: 16px;
      font-weight: 600;
      color: #1a1a1a;
      box-shadow: 0 1px 4px rgba(0,0,0,0.04);
      width: fit-content;
      margin-bottom: 40px;
    }}
    .badge svg {{ width: 20px; height: 20px; }}
    .cta-card {{
      background: white;
      border-radius: 28px;
      padding: 60px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.04);
      flex: 1;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      text-align: center;
    }}
    .cta-headline {{
      font-size: 56px;
      font-weight: 800;
      color: #1a1a1a;
      margin-bottom: 30px;
      line-height: 1.15;
      letter-spacing: -0.03em;
    }}
    .cta-description {{
      font-size: 28px;
      color: #6b7280;
      margin-bottom: 50px;
      line-height: 1.5;
      max-width: 700px;
    }}
    .cta-button {{
      display: inline-block;
      background: linear-gradient(135deg, #6366f1, #8b5cf6);
      color: white;
      padding: 24px 56px;
      border-radius: 16px;
      font-size: 24px;
      font-weight: 700;
      text-decoration: none;
      border: none;
      cursor: pointer;
      box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
      transition: transform 0.2s;
    }}
    .cta-button:hover {{
      transform: translateY(-2px);
    }}
    .logos-card {{
      background: #f0f0f0;
      border-radius: 28px;
      padding: 40px 60px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 40px;
      margin-top: 30px;
    }}
    .logo {{
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 28px;
      font-weight: 800;
      color: #1a1a1a;
      letter-spacing: -0.02em;
    }}
    .logo-icon {{ width: 32px; height: 32px; }}
    .logo-divider {{ width: 1px; height: 36px; background: #d0d0d0; }}
    .scaile-icon {{
      width: 30px;
      height: 30px;
      background: linear-gradient(135deg, #6366f1, #8b5cf6);
      border-radius: 8px;
    }}
  </style>
</head>
<body>
  <div class="badge">
    <svg viewBox="0 0 24 24" fill="currentColor">
      <rect x="3" y="3" width="7" height="7" rx="1"/>
      <rect x="14" y="3" width="7" height="7" rx="1"/>
      <rect x="3" y="14" width="7" height="7" rx="1"/>
      <rect x="14" y="14" width="7" height="7" rx="1"/>
    </svg>
    {badge_text}
  </div>

  <div class="cta-card">
    <h1 class="cta-headline">{headline}</h1>
    <p class="cta-description">{description}</p>
    <a class="cta-button">{button_text}</a>
  </div>
{logos_html}
</body>
</html>"""
    
    def _generate_infographic_html(self, request: GraphicsGenerationRequest) -> str:
        """Generate infographic HTML (openfigma quality)."""
        content = request.content
        title = content.get("title", "")
        items = content.get("items", [])
        badge_text = content.get("badge", "Process")
        company_name = request.company_data.get("name", "") if request.company_data else ""
        show_logos = content.get("show_logos", True)
        
        logos_html = ""
        if show_logos and company_name:
            logos_html = f"""
  <div class="logos-card">
    <div class="logo">
      <svg class="logo-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <path d="M4 6h16M4 12h16M4 18h10"/>
      </svg>
      {company_name.upper()}
    </div>
    <div class="logo-divider"></div>
    <div class="logo">
      <div class="scaile-icon"></div>
      SCAILE
    </div>
  </div>"""
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Infographic</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: 'Inter', -apple-system, sans-serif;
      background: #f8f8f8;
      width: {request.dimensions[0]}px;
      height: {request.dimensions[1]}px;
      display: flex;
      flex-direction: column;
      padding: 60px;
      position: relative;
    }}
    body::before {{
      content: '';
      position: absolute;
      inset: 0;
      background-image: 
        linear-gradient(rgba(0,0,0,0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,0,0,0.025) 1px, transparent 1px);
      background-size: 20px 20px;
      pointer-events: none;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
      background: white;
      border: 1px solid #e8e8e8;
      border-radius: 100px;
      padding: 12px 24px;
      font-size: 16px;
      font-weight: 600;
      color: #1a1a1a;
      box-shadow: 0 1px 4px rgba(0,0,0,0.04);
      width: fit-content;
      margin-bottom: 40px;
    }}
    .badge svg {{ width: 20px; height: 20px; }}
    .infographic-card {{
      background: white;
      border-radius: 28px;
      padding: 50px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.04);
      flex: 1;
      display: flex;
      flex-direction: column;
    }}
    .infographic-title {{
      font-size: 48px;
      font-weight: 800;
      color: #1a1a1a;
      margin-bottom: 50px;
      text-align: center;
      letter-spacing: -0.02em;
    }}
    .infographic-items {{
      display: flex;
      flex-direction: column;
      gap: 20px;
      flex: 1;
      justify-content: center;
    }}
    .infographic-item {{
      display: flex;
      align-items: center;
      gap: 24px;
      padding: 28px;
      background: #f8f8f8;
      border-radius: 20px;
      border: 1px solid #e8e8e8;
      transition: transform 0.2s;
    }}
    .infographic-item:hover {{
      transform: translateX(4px);
    }}
    .item-number {{
      width: 56px;
      height: 56px;
      border-radius: 50%;
      background: linear-gradient(135deg, #6366f1, #8b5cf6);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 24px;
      font-weight: 700;
      color: white;
      flex-shrink: 0;
      box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
    }}
    .item-text {{
      font-size: 26px;
      font-weight: 600;
      color: #1a1a1a;
      line-height: 1.4;
    }}
    .logos-card {{
      background: #f0f0f0;
      border-radius: 28px;
      padding: 40px 60px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 40px;
      margin-top: 30px;
    }}
    .logo {{
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 28px;
      font-weight: 800;
      color: #1a1a1a;
      letter-spacing: -0.02em;
    }}
    .logo-icon {{ width: 32px; height: 32px; }}
    .logo-divider {{ width: 1px; height: 36px; background: #d0d0d0; }}
    .scaile-icon {{
      width: 30px;
      height: 30px;
      background: linear-gradient(135deg, #6366f1, #8b5cf6);
      border-radius: 8px;
    }}
  </style>
</head>
<body>
  <div class="badge">
    <svg viewBox="0 0 24 24" fill="currentColor">
      <rect x="3" y="3" width="7" height="7" rx="1"/>
      <rect x="14" y="3" width="7" height="7" rx="1"/>
      <rect x="3" y="14" width="7" height="7" rx="1"/>
      <rect x="14" y="14" width="7" height="7" rx="1"/>
    </svg>
    {badge_text}
  </div>

  <div class="infographic-card">
    <h1 class="infographic-title">{title}</h1>
    <div class="infographic-items">
      {''.join([f'<div class="infographic-item"><div class="item-number">{i+1}</div><div class="item-text">{item}</div></div>' for i, item in enumerate(items)])}
    </div>
  </div>
{logos_html}
</body>
</html>"""
    
    async def _html_to_png(self, html_content: str, dimensions: tuple) -> bytes:
        """Convert HTML to PNG using Playwright."""
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": dimensions[0], "height": dimensions[1]})
            
            # Write HTML to temp file
            with NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                f.write(html_content)
                temp_path = f.name
            
            try:
                # Load HTML file
                await page.goto(f"file://{temp_path}")
                await page.wait_for_load_state("networkidle")
                
                # Take screenshot
                screenshot_bytes = await page.screenshot(full_page=False, type="png")
                
                return screenshot_bytes
            finally:
                await browser.close()
                # Clean up temp file
                try:
                    os.unlink(temp_path)
                except:
                    pass
    
    def _generate_alt_text(self, request: GraphicsGenerationRequest) -> str:
        """Generate alt text for the graphic."""
        content = request.content
        if request.graphic_type == "headline":
            return f"Blog graphic: {content.get('headline', 'Headline')}"
        elif request.graphic_type == "quote":
            return f"Quote graphic: {content.get('quote', '')[:100]}"
        elif request.graphic_type == "metric":
            return f"Metric graphic: {content.get('value', '')} {content.get('label', '')}"
        elif request.graphic_type == "cta":
            return f"CTA graphic: {content.get('headline', 'Call to action')}"
        else:
            return f"Infographic: {content.get('title', 'Infographic')}"
    
    async def _get_graphics_folder(self, project_folder_id: str) -> Optional[str]:
        """Navigate to Graphics (Final) folder within project structure."""
        if not self.drive_service:
            return None
        
        try:
            # Find Content Output folder
            content_folder = self._find_folder(project_folder_id, self.CONTENT_OUTPUT_FOLDER)
            if not content_folder:
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
        
        media = MediaInMemoryUpload(
            image_bytes,
            mimetype="image/png",
            resumable=True
        )
        
        file = self.drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id"
        ).execute()
        
        return file.get("id")
    
    async def _make_public(self, file_id: str):
        """Make a Google Drive file publicly accessible."""
        if not self.drive_service:
            raise ValueError("Drive service not initialized - cannot make public")
        
        try:
            permission = {
                "type": "anyone",
                "role": "reader",
            }
            self.drive_service.permissions().create(
                fileId=file_id,
                body=permission,
                fields="id",
            ).execute()
            logger.info(f"File {file_id} made public.")
        except Exception as e:
            logger.error(f"Failed to make file {file_id} public: {e}")
            raise

