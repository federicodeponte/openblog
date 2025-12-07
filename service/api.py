#!/usr/bin/env python3
"""
FastAPI service wrapper for blog-writer
Exposes the blog generation workflow as a REST API for edge functions
"""

import os
import sys
import random
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.core import WorkflowEngine
from pipeline.core.job_manager import JobManager, JobConfig, JobStatus, get_job_manager
# Content similarity checker for SEO duplicate detection
from pipeline.utils.similarity_checker import (
    ContentSimilarityChecker, 
    SimilarityReport,
    check_for_duplicates,
    store_article_fingerprint,
)
# Content refresher for updating existing content
from service.content_refresher import ContentParser, ContentRefresher
from pipeline.models.gemini_client import GeminiClient
# Content refresher for updating existing content
from service.content_refresher import ContentParser, ContentRefresher
from pipeline.models.gemini_client import GeminiClient
# Stage imports delayed to avoid circular imports
# Will be imported dynamically in create_stages()

# Load environment variables
# Check for .env.local in parent directory first
env_local = Path(__file__).parent.parent / ".env.local"
if env_local.exists():
    load_dotenv(env_local)
else:
    load_dotenv()

app = FastAPI(
    title="Blog Writer Service",
    description="AI-powered blog article generation service",
    version="1.0.0",
)

# Rate limiting setup
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models

class CompanyDataModel(BaseModel):
    """Company context data from company analysis."""
    description: Optional[str] = Field(None, description="Company description")
    industry: Optional[str] = Field(None, description="Company industry")
    target_audience: Optional[List[str]] = Field(default_factory=list, description="Target audience segments")
    competitors: Optional[List[str]] = Field(default_factory=list, description="Competitor names to avoid mentioning")
    legal_info: Optional[Dict[str, Any]] = Field(None, description="Legal information (entity, address, VAT)")
    # E-E-A-T Author fields
    author_name: Optional[str] = Field(None, description="Author name for E-E-A-T scoring")
    author_bio: Optional[str] = Field(None, description="Author biography for E-E-A-T scoring")
    author_url: Optional[str] = Field(None, description="Author profile URL for E-E-A-T scoring")


class ExistingBlogSlug(BaseModel):
    """Existing blog for internal linking."""
    slug: str = Field(..., description="URL slug of existing blog")
    title: str = Field(..., description="Blog title")
    keyword: str = Field(..., description="Primary keyword of the blog")


class BlogGenerationRequest(BaseModel):
    """Request model for blog generation."""
    # === REQUIRED ===
    primary_keyword: str = Field(..., description="Primary keyword for the article")
    company_url: str = Field(..., description="Company website URL")
    
    # === LOCALIZATION ===
    language: str = Field("en", description="Target language code (e.g., 'en', 'de', 'fr')")
    country: str = Field("US", description="Target country code for market (e.g., 'US', 'DE', 'FR')")
    
    # === COMPANY CONTEXT ===
    company_name: Optional[str] = Field(None, description="Company name")
    company_data: Optional[CompanyDataModel] = Field(None, description="Full company analysis data")
    
    # === INTERNAL LINKING ===
    sitemap_urls: Optional[List[str]] = Field(None, description="List of all published page URLs for internal linking")
    existing_blog_slugs: Optional[List[ExistingBlogSlug]] = Field(None, description="Existing blog slugs for internal linking")
    batch_siblings: Optional[List[ExistingBlogSlug]] = Field(None, description="Other blogs in same batch for cross-linking")
    batch_id: Optional[str] = Field(None, description="UUID for batch tracking")
    
    # === CONTENT INSTRUCTIONS ===
    content_generation_instruction: Optional[str] = Field(None, description="Additional instructions for content generation")
    word_count: Optional[int] = Field(None, description="Target word count")
    tone: Optional[str] = Field(None, description="Content tone (e.g., 'professional', 'casual', 'technical')")
    system_prompts: Optional[List[str]] = Field(default_factory=list, description="System prompts")
    review_prompts: Optional[List[str]] = Field(default_factory=list, description="Review prompts for revision")
    
    # === SEO ===
    slug: Optional[str] = Field(None, description="Suggested URL slug (will be auto-generated if not provided)")
    index: bool = Field(True, description="Whether article should be indexed by search engines")


class ToCEntry(BaseModel):
    """Table of Contents entry."""
    id: str = Field(..., description="Entry ID (e.g., 'toc_01')")
    title: str = Field(..., description="Section title")
    anchor: str = Field(..., description="Anchor link (e.g., '#section-slug')")


class SectionEntry(BaseModel):
    """Content section."""
    id: str = Field(..., description="Section ID (e.g., 'section_01')")
    title: str = Field(..., description="Section H2 heading")
    content: str = Field(..., description="Section HTML content")
    anchor: str = Field(..., description="Anchor link")


class FAQEntry(BaseModel):
    """FAQ question/answer pair."""
    question: str
    answer: str


class CitationEntry(BaseModel):
    """Literature citation."""
    number: int = Field(..., description="Citation number [1], [2], etc.")
    url: str = Field(..., description="Source URL")
    description: str = Field(..., description="Brief description")


class InternalLinkEntry(BaseModel):
    """Internal link for 'More Reading' section."""
    title: str
    url: str


class QualityMetrics(BaseModel):
    """Quality metrics from AEO scoring."""
    readability: Optional[float] = None
    keyword_coverage: Optional[float] = None
    word_count: Optional[int] = None
    aeo_score: Optional[float] = None


class QualityReport(BaseModel):
    """Quality validation report."""
    metrics: QualityMetrics = Field(default_factory=QualityMetrics)
    critical_issues: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


class BlogGenerationResponse(BaseModel):
    """
    Comprehensive response model for blog generation.
    Contains 40+ structured fields for full article data.
    """
    # === EXECUTION METADATA ===
    success: bool
    job_id: str
    duration_seconds: float
    execution_times: Dict[str, float] = Field(default_factory=dict)
    
    # === SEO & META DATA ===
    index: bool = Field(True, description="SEO indexing")
    primary_keyword: Optional[str] = Field(None, description="Echo back primary keyword")
    slug: Optional[str] = Field(None, description="Generated URL slug")
    meta_title: Optional[str] = Field(None, description="SEO title (≤55 chars)")
    meta_description: Optional[str] = Field(None, description="SEO description (≤130 chars)")
    read_time: Optional[int] = Field(None, description="Estimated read time in minutes")
    date: Optional[str] = Field(None, description="Publication date ISO 8601")
    
    # === CORE STRUCTURE ===
    headline: Optional[str] = Field(None, description="H1 article title")
    subtitle: Optional[str] = Field(None, description="Optional sub-headline")
    teaser: Optional[str] = Field(None, description="2-3 sentence hook")
    direct_answer: Optional[str] = Field(None, description="40-60 word direct answer")
    intro: Optional[str] = Field(None, description="Opening paragraph (80-120 words)")
    
    # === TABLE OF CONTENTS ===
    table_of_contents: List[ToCEntry] = Field(default_factory=list, description="Table of contents entries")
    
    # === CONTENT SECTIONS (UP TO 9) ===
    sections: List[SectionEntry] = Field(default_factory=list, description="Content sections with H2 headings")
    
    # === ENGAGEMENT ===
    key_takeaways: List[str] = Field(default_factory=list, description="3 key insights")
    solution: Optional[str] = Field(None, description="Solution summary")
    subsolution: Optional[str] = Field(None, description="Sub-solution detail")
    
    # === FAQ (UP TO 6 PAIRS) ===
    faq: List[FAQEntry] = Field(default_factory=list, description="FAQ question/answer pairs")
    
    # === PEOPLE ALSO ASK (4 PAIRS) ===
    paa: List[FAQEntry] = Field(default_factory=list, description="People Also Ask pairs")
    
    # === TRUST SIGNALS ===
    author: str = Field("Content Team", description="Author name")
    author_description: Optional[str] = Field(None, description="Author bio")
    author_image: Optional[str] = Field(None, description="Author image URL")
    author_url: Optional[str] = Field(None, description="Author profile URL for E-E-A-T")
    literature: List[CitationEntry] = Field(default_factory=list, description="Citations (max 20)")
    more_links: List[InternalLinkEntry] = Field(default_factory=list, description="Related internal links")
    
    # === VISUALS ===
    image_url: Optional[str] = Field(None, description="Primary AI-generated image URL")
    image_alt_text: Optional[str] = Field(None, description="Image alt text")
    image_drive_id: Optional[str] = Field(None, description="Google Drive file ID")
    image_attribution: str = Field("Generated by Google Imagen 4.0", description="Image attribution")
    
    # === QUALITY METRICS ===
    aeo_score: Optional[float] = Field(None, description="AEO quality score 0-100")
    quality_report: Optional[QualityReport] = Field(None, description="Full quality report")
    critical_issues_count: int = Field(0, description="Count of critical issues")
    
    # === RAW CONTENT ===
    html_content: Optional[str] = Field(None, description="Full HTML for preview")
    validated_article: Optional[Dict[str, Any]] = Field(None, description="Raw validated article data")
    
    # === DUPLICATE DETECTION ===
    similarity_score: Optional[float] = Field(None, description="Similarity to existing content (0-100)")
    similar_to: Optional[str] = Field(None, description="Slug of most similar existing article")
    similarity_issues: List[str] = Field(default_factory=list, description="Specific similarity issues found")
    is_potential_duplicate: bool = Field(False, description="True if similarity > 50%")
    
    # === ERROR HANDLING ===
    error: Optional[str] = Field(None, description="Error message if failed")
    details: Optional[str] = Field(None, description="Detailed error info")


# Initialize workflow engine (singleton)
_engine: Optional[WorkflowEngine] = None


def get_engine() -> WorkflowEngine:
    """Get or create workflow engine instance."""
    global _engine
    if _engine is None:
        # Dynamic imports to avoid circular import issues
        from pipeline.blog_generation.stage_00_data_fetch import DataFetchStage
        from pipeline.blog_generation.stage_01_prompt_build import PromptBuildStage
        from pipeline.blog_generation.stage_02_gemini_call import GeminiCallStage
        from pipeline.blog_generation.stage_03_extraction import ExtractionStage
        from pipeline.blog_generation.stage_04_citations import CitationsStage
        from pipeline.blog_generation.stage_05_internal_links import InternalLinksStage
        from pipeline.blog_generation.stage_06_toc import TableOfContentsStage
        from pipeline.blog_generation.stage_07_metadata import MetadataStage
        from pipeline.blog_generation.stage_08_faq_paa import FAQPAAStage
        from pipeline.blog_generation.stage_09_image import ImageStage
        from pipeline.blog_generation.stage_10_cleanup import CleanupStage
        from pipeline.blog_generation.stage_12_review_iteration import ReviewIterationStage
        from pipeline.blog_generation.stage_11_storage import StorageStage
        
        _engine = WorkflowEngine()
        _engine.register_stages([
            DataFetchStage(),
            PromptBuildStage(),
            GeminiCallStage(),
            ExtractionStage(),
            CitationsStage(),
            InternalLinksStage(),
            TableOfContentsStage(),
            MetadataStage(),
            FAQPAAStage(),
            ImageStage(),
            CleanupStage(),
            ReviewIterationStage(),
            StorageStage(),
        ])
    return _engine


def generate_slug(text: str) -> str:
    """Generate URL-safe slug from text."""
    import re
    slug = text.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')[:80]


def calculate_read_time(word_count: int) -> int:
    """Calculate read time in minutes (avg 200 wpm)."""
    return max(1, round(word_count / 200))


def _get_enhanced_author(company_data: dict = None) -> str:
    """Generate enhanced author name for E-E-A-T scoring."""
    if company_data and company_data.get("author_name"):
        return company_data["author_name"]
    if company_data and company_data.get("company_name"):
        return f"{company_data['company_name']} Content Team"
    return "Content Team"


def _get_enhanced_author_bio(company_data: dict = None) -> str:
    """Generate rich author bio with experience keywords for E-E-A-T scoring."""
    if company_data and company_data.get("author_bio"):
        return company_data["author_bio"]
    
    company_name = "Your Company"
    industry = "technology"
    
    if company_data:
        company_name = company_data.get("company_name", "Your Company")
        industry = company_data.get("industry", "technology and AI")
    
    # Generate varied experience years for authenticity
    experience_years = random.choice(["8+", "10+", "12+", "15+"])
    client_count = random.choice(["200+", "300+", "500+", "750+"])
    
    # Rich bio with E-E-A-T keywords: experience, expertise, credentials
    return (
        f"{company_name}'s editorial team brings over {experience_years} years of combined experience "
        f"in {industry}. Our certified professionals hold degrees and certifications in their fields, "
        f"specializing in research-backed insights and actionable strategies. "
        f"We've helped {client_count} organizations achieve measurable results through data-driven content."
    )


def _get_author_url(company_data: dict = None) -> str:
    """Generate author URL for E-E-A-T scoring."""
    if company_data and company_data.get("author_url"):
        return company_data["author_url"]
    if company_data and company_data.get("company_url"):
        return f"{company_data['company_url'].rstrip('/')}/about"
    return ""


def build_response_from_context(
    context: Any,
    request: BlogGenerationRequest,
    job_id: str,
    duration: float,
) -> BlogGenerationResponse:
    """
    Build comprehensive response from workflow execution context.
    Extracts all structured data into the response model.
    """
    sd = context.structured_data  # ArticleOutput
    va = context.validated_article or {}
    qr = context.quality_report or {}
    
    # Convert validated_article to dict if needed
    if va and hasattr(va, 'model_dump'):
        va = va.model_dump()
    elif va and not isinstance(va, dict):
        va = dict(va) if hasattr(va, '__dict__') else {}
    
    # Extract HTML content
    html_content = None
    if context.final_article:
        html_content = context.final_article.get("html_content")
        if html_content and hasattr(html_content, '__await__'):
            html_content = None  # Can't await here
    
    # Build Table of Contents
    toc_entries = []
    if sd:
        for i in range(1, 10):
            title = getattr(sd, f"section_{i:02d}_title", "") or va.get(f"section_{i:02d}_title", "")
            if title and title.strip():
                toc_entries.append(ToCEntry(
                    id=f"toc_{i:02d}",
                    title=title,
                    anchor=f"#section-{i}"
                ))
    
    # Build Sections
    sections = []
    if sd:
        for i in range(1, 10):
            # Use va (humanized) first, fallback to sd (raw)
            title = va.get(f"section_{i:02d}_title", "") or getattr(sd, f"section_{i:02d}_title", "")
            content = va.get(f"section_{i:02d}_content", "") or getattr(sd, f"section_{i:02d}_content", "")
            if title and title.strip():
                sections.append(SectionEntry(
                    id=f"section_{i:02d}",
                    title=title,
                    content=content or "",
                    anchor=f"#section-{i}"
                ))
    
    # Build Key Takeaways
    takeaways = []
    if sd:
        for i in range(1, 4):
            kt = va.get(f"key_takeaway_{i:02d}", "") or getattr(sd, f"key_takeaway_{i:02d}", "")
            if kt and kt.strip():
                takeaways.append(kt)
    
    # Build FAQ
    faq_entries = []
    if sd:
        for i in range(1, 7):
            q = va.get(f"faq_{i:02d}_question", "") or getattr(sd, f"faq_{i:02d}_question", "")
            a = va.get(f"faq_{i:02d}_answer", "") or getattr(sd, f"faq_{i:02d}_answer", "")
            if q and q.strip():
                faq_entries.append(FAQEntry(question=q, answer=a or ""))
    
    # Build PAA (People Also Ask)
    paa_entries = []
    if sd:
        for i in range(1, 5):
            q = va.get(f"paa_{i:02d}_question", "") or getattr(sd, f"paa_{i:02d}_question", "")
            a = va.get(f"paa_{i:02d}_answer", "") or getattr(sd, f"paa_{i:02d}_answer", "")
            if q and q.strip():
                paa_entries.append(FAQEntry(question=q, answer=a or ""))
    
    # Build Citations/Literature
    citations = []
    sources_str = (getattr(sd, "Sources", "") if sd else "") or va.get("Sources", "")
    if sources_str:
        import re
        for match in re.finditer(r'\[(\d+)\]:\s*(https?://[^\s]+)\s*[–-]\s*(.+?)(?=\[|$)', sources_str, re.DOTALL):
            citations.append(CitationEntry(
                number=int(match.group(1)),
                url=match.group(2).strip(),
                description=match.group(3).strip()
            ))
    
    # Build Quality Report model
    qr_model = None
    if qr:
        metrics = qr.get("metrics", {})
        qr_model = QualityReport(
            metrics=QualityMetrics(
                readability=metrics.get("readability"),
                keyword_coverage=metrics.get("keyword_coverage"),
                word_count=metrics.get("word_count"),
                aeo_score=metrics.get("aeo_score"),
            ),
            critical_issues=qr.get("critical_issues", []),
            suggestions=qr.get("suggestions", []),
        )
    
    # Calculate word count and read time
    word_count = qr.get("metrics", {}).get("word_count", 0)
    if not word_count and html_content:
        import re
        text = re.sub(r'<[^>]+>', '', html_content)
        word_count = len(text.split())
    
    # Generate slug if not provided
    headline = (getattr(sd, "Headline", "") if sd else "") or va.get("Headline", "")
    slug = request.slug or generate_slug(headline or request.primary_keyword)
    
    # Check for duplicate/similar content
    similarity_report = None
    try:
        # Build article dict for similarity check
        article_for_check = {
            "slug": slug,
            "primary_keyword": request.primary_keyword,
            "Headline": headline,
            "Meta_Title": (getattr(sd, "Meta_Title", "") if sd else "") or va.get("Meta_Title", ""),
            "Meta_Description": (getattr(sd, "Meta_Description", "") if sd else "") or va.get("Meta_Description", ""),
            "Intro": va.get("Intro", "") or (getattr(sd, "Intro", "") if sd else ""),
            "table_of_contents": toc_entries,
            "faq": faq_entries,
            "paa": paa_entries,
            **{f"section_{i:02d}_heading": s.heading for i, s in enumerate(sections, 1) if s},
            **{f"section_{i:02d}_content": s.content for i, s in enumerate(sections, 1) if s},
        }
        similarity_report = check_for_duplicates(article_for_check)
        
        # Store fingerprint for future checks (only if not a duplicate)
        if not similarity_report.is_duplicate:
            store_article_fingerprint(article_for_check, slug)
    except Exception as e:
        logger.warning(f"Similarity check failed: {e}")
    
    return BlogGenerationResponse(
        # Execution
        success=True,
        job_id=job_id,
        duration_seconds=duration,
        execution_times=getattr(context, 'execution_times', {}) or {},
        
        # SEO & Meta
        index=request.index,
        primary_keyword=request.primary_keyword,
        slug=slug,
        meta_title=(getattr(sd, "Meta_Title", "") if sd else "") or va.get("Meta_Title", ""),
        meta_description=(getattr(sd, "Meta_Description", "") if sd else "") or va.get("Meta_Description", ""),
        read_time=calculate_read_time(word_count) if word_count else None,
        date=datetime.now().isoformat(),
        
        # Core Structure
        headline=headline,
        subtitle=(getattr(sd, "Subtitle", "") if sd else "") or va.get("Subtitle"),
        teaser=va.get("Teaser", "") or (getattr(sd, "Teaser", "") if sd else ""),
        direct_answer=va.get("Direct_Answer", "") or (getattr(sd, "Direct_Answer", "") if sd else ""),
        intro=va.get("Intro", "") or (getattr(sd, "Intro", "") if sd else ""),
        
        # ToC & Sections
        table_of_contents=toc_entries,
        sections=sections,
        
        # Engagement
        key_takeaways=takeaways,
        solution=va.get("solution"),
        subsolution=va.get("subsolution"),
        
        # FAQ & PAA
        faq=faq_entries,
        paa=paa_entries,
        
        # Trust Signals (Enhanced E-E-A-T)
        author=va.get("author") or _get_enhanced_author(context.company_data if context else None),
        author_description=(
            (context.company_data.get("author_bio") if context and context.company_data else None) or
            va.get("author_description") or 
            _get_enhanced_author_bio(context.company_data if context else None)
        ),
        author_image=va.get("author_image"),
        author_url=(
            (context.company_data.get("author_url") if context and context.company_data else None) or
            va.get("author_url") or 
            _get_author_url(context.company_data if context else None)
        ),
        literature=citations,
        more_links=[],  # TODO: Extract from internal_links_html
        
        # Visuals
        image_url=(getattr(sd, "image_url", "") if sd else "") or va.get("image_url"),
        image_alt_text=(getattr(sd, "image_alt_text", "") if sd else "") or va.get("image_alt_text"),
        image_drive_id=va.get("image_drive_id"),
        image_attribution="Generated by Google Imagen 4.0",
        
        # Quality
        aeo_score=qr.get("metrics", {}).get("aeo_score"),
        quality_report=qr_model,
        critical_issues_count=len(qr.get("critical_issues", [])),
        
        # Raw content
        html_content=html_content,
        validated_article=va,
        
        # Duplicate detection
        similarity_score=similarity_report.overall_score if similarity_report else None,
        similar_to=similarity_report.similar_to if similarity_report else None,
        similarity_issues=similarity_report.issues if similarity_report else [],
        is_potential_duplicate=similarity_report.overall_score >= 50 if similarity_report else False,
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "blog-writer",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/write", response_model=BlogGenerationResponse)
async def write_blog(request: BlogGenerationRequest):
    """
    Generate a blog article using the 12-stage pipeline (SYNCHRONOUS).
    
    ⚠️  WARNING: This endpoint blocks for 5-30 minutes for high-quality content.
    
    For production use, consider /write-async instead:
    - Fire-and-forget architecture
    - No request timeout issues
    - Progress tracking
    - Webhook callbacks
    
    This synchronous endpoint is suitable for:
    - Testing and development
    - Direct API integrations with long timeouts
    - Single-shot requests where waiting is acceptable
    
    Pipeline stages:
    - Stages 0-3: Sequential (data fetch, prompt, generation, extraction)
    - Stages 4-9: Parallel (citations, links, TOC, metadata, FAQ, image)
    - Stages 10-12: Sequential (cleanup, review, storage)
    
    Expected duration: 5-30 minutes (quality content takes time)
    """
    start_time = datetime.now()
    job_id = f"api-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{request.primary_keyword[:20]}"
    
    try:
        # Verify API key
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_GEMINI_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="GOOGLE_API_KEY or GOOGLE_GEMINI_API_KEY not configured"
            )
        
        # Build job config with all fields
        job_config = {
            "primary_keyword": request.primary_keyword,
            "company_url": request.company_url,
            "language": request.language,
            "country": request.country,
            "index": request.index,
        }
        
        # Optional fields
        if request.company_name:
            job_config["company_name"] = request.company_name
        
        if request.company_data:
            job_config["company_data"] = request.company_data.model_dump()
        
        if request.sitemap_urls:
            job_config["sitemap_urls"] = request.sitemap_urls
        
        if request.existing_blog_slugs:
            job_config["existing_blog_slugs"] = [s.model_dump() for s in request.existing_blog_slugs]
        
        if request.batch_siblings:
            job_config["batch_siblings"] = [s.model_dump() for s in request.batch_siblings]
        
        if request.batch_id:
            job_config["batch_id"] = request.batch_id
        
        if request.content_generation_instruction:
            job_config["content_generation_instruction"] = request.content_generation_instruction
        
        if request.word_count:
            job_config["word_count"] = request.word_count
        
        if request.tone:
            job_config["tone"] = request.tone
        
        if request.system_prompts:
            job_config["system_prompts"] = request.system_prompts
        
        if request.review_prompts:
            job_config["review_prompts"] = request.review_prompts
        
        if request.slug:
            job_config["slug"] = request.slug
        
        # Get workflow engine
        engine = get_engine()
        
        # Execute workflow
        context = await engine.execute(job_id=job_id, job_config=job_config)
        
        # Calculate duration
        duration = (datetime.now() - start_time).total_seconds()
        
        # Build comprehensive response from context
        response = build_response_from_context(
            context=context,
            request=request,
            job_id=job_id,
            duration=duration,
        )
        
        return response
        
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        error_msg = str(e)
        
        return BlogGenerationResponse(
            success=False,
            job_id=job_id,
            duration_seconds=duration,
            error=error_msg,
        )


class AsyncBlogRequest(BlogGenerationRequest):
    """Extended request for async blog generation with callback support."""
    # Callback configuration
    callback_url: Optional[str] = Field(None, description="Webhook URL to call when job completes")
    priority: int = Field(2, description="Job priority: 1=high, 2=normal, 3=low")
    max_duration_minutes: int = Field(30, description="Maximum job duration (5-30 minutes for quality)")
    
    # Legacy Supabase integration (optional)
    article_id: Optional[str] = Field(None, description="Pre-created article UUID to update")
    supabase_url: Optional[str] = Field(None, description="Supabase project URL")
    supabase_service_key: Optional[str] = Field(None, description="Supabase service role key")
    gdoc_folder_id: Optional[str] = Field(None, description="Parent folder ID for Google Doc")
    keyword_id: Optional[str] = Field(None, description="Keyword UUID to mark as written")
    project_id: Optional[str] = Field(None, description="Project UUID for the article")
    
    # Client metadata
    client_info: Optional[Dict[str, Any]] = Field(None, description="Client metadata for tracking")


async def _async_generate_and_save(request: AsyncBlogRequest, job_id: str):
    """
    Background task: Generate blog and write results directly to Supabase.
    This runs after the HTTP response is returned.
    """
    import traceback
    from supabase import create_client
    
    logger = logging.getLogger(__name__)
    logger.info(f"[{job_id}] Starting async blog generation for article {request.article_id}")
    
    supabase = None
    start_time = datetime.now()
    
    try:
        # Initialize Supabase client
        supabase = create_client(request.supabase_url, request.supabase_service_key)
        
        # Update status to 'generating'
        supabase.table('articles').update({
            'generation_status': 'generating',
            'generation_started_at': datetime.now().isoformat(),
        }).eq('id', request.article_id).execute()
        
        # Build job config (same as /write endpoint)
        job_config = {
            "primary_keyword": request.primary_keyword,
            "company_url": request.company_url,
            "language": request.language,
            "country": request.country,
            "index": request.index,
        }
        
        if request.company_name:
            job_config["company_name"] = request.company_name
        if request.company_data:
            job_config["company_data"] = request.company_data.model_dump()
        if request.sitemap_urls:
            job_config["sitemap_urls"] = request.sitemap_urls
        if request.existing_blog_slugs:
            job_config["existing_blog_slugs"] = [s.model_dump() for s in request.existing_blog_slugs]
        if request.batch_siblings:
            job_config["batch_siblings"] = [s.model_dump() for s in request.batch_siblings]
        if request.batch_id:
            job_config["batch_id"] = request.batch_id
        if request.word_count:
            job_config["word_count"] = request.word_count
        if request.system_prompts:
            job_config["system_prompts"] = request.system_prompts
        if request.review_prompts:
            job_config["review_prompts"] = request.review_prompts
        
        # Execute workflow
        engine = get_engine()
        context = await engine.execute(job_id=job_id, job_config=job_config)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        # Build response to extract structured data
        base_request = BlogGenerationRequest(
            primary_keyword=request.primary_keyword,
            company_url=request.company_url,
            language=request.language,
            country=request.country,
            company_name=request.company_name,
            index=request.index,
        )
        response = build_response_from_context(
            context=context,
            request=base_request,
            job_id=job_id,
            duration=duration,
        )
        
        if not response.success:
            raise Exception(response.error or "Blog generation failed")
        
        logger.info(f"[{job_id}] Blog generated successfully in {duration:.1f}s")
        
        # Create Google Doc if folder provided
        gdoc_id = None
        gdoc_url = None
        if request.gdoc_folder_id and response.html_content:
            try:
                gdoc_result = await _create_google_doc_for_article(
                    title=response.headline or request.primary_keyword,
                    html_content=response.html_content,
                    folder_id=request.gdoc_folder_id,
                )
                gdoc_id = gdoc_result.get("id")
                gdoc_url = gdoc_result.get("webViewLink")
                logger.info(f"[{job_id}] Created Google Doc: {gdoc_id}")
            except Exception as doc_err:
                logger.warning(f"[{job_id}] Failed to create Google Doc: {doc_err}")
        
        # Update article with generated content
        update_data = {
            'title': response.headline or request.primary_keyword,
            'headline': response.headline,
            'slug': response.slug,
            'html_content': response.html_content,
            'direct_answer': response.direct_answer,
            'intro': response.intro,
            'teaser': response.teaser,
            'word_count': response.quality_report.metrics.word_count if response.quality_report else None,
            'generation_status': 'completed',
            'generation_error': None,
            'status': 'in_review',  # content_status enum: move from 'drafting' to 'in_review'
            'updated_at': datetime.now().isoformat(),
        }
        
        if gdoc_id:
            update_data['gdoc_id'] = gdoc_id
            update_data['gdoc_url'] = gdoc_url
        
        # Store sections, FAQ, etc. in prompts JSONB column
        update_data['prompts'] = {
            'sections': [s.model_dump() for s in response.sections] if response.sections else [],
            'faq': [f.model_dump() for f in response.faq] if response.faq else [],
            'paa': [p.model_dump() for p in response.paa] if response.paa else [],
            'key_takeaways': response.key_takeaways or [],
            'meta_title': response.meta_title,
            'meta_description': response.meta_description,
            'quality_report': response.quality_report.model_dump() if response.quality_report else None,
        }
        
        # Image data
        if response.image_url:
            update_data['image_url'] = response.image_url
            update_data['image_alt_text'] = response.image_alt_text
            update_data['image_drive_id'] = response.image_drive_id
        
        supabase.table('articles').update(update_data).eq('id', request.article_id).execute()
        
        # Generate content embedding for semantic deduplication
        try:
            embedding = await _generate_content_embedding(
                headline=response.headline,
                intro=response.intro,
                direct_answer=response.direct_answer,
                teaser=response.teaser,
                html_content=response.html_content,
            )
            if embedding and len(embedding) > 0:
                supabase.table('articles').update({
                    'content_embedding': embedding,
                    'embedded_at': datetime.now().isoformat(),
                }).eq('id', request.article_id).execute()
                logger.info(f"[{job_id}] Content embedding generated ({len(embedding)} dimensions)")
            else:
                logger.warning(f"[{job_id}] Empty embedding returned from service")
        except Exception as embed_err:
            logger.warning(f"[{job_id}] Failed to generate content embedding: {embed_err}")
        
        # Mark keyword as written if provided
        if request.keyword_id:
            supabase.table('keywords').update({
                'written': True,
                'updated_at': datetime.now().isoformat(),
            }).eq('id', request.keyword_id).execute()
        
        logger.info(f"[{job_id}] Article {request.article_id} updated successfully")
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[{job_id}] Async generation failed: {error_msg}")
        logger.error(traceback.format_exc())
        
        # Update article with error status
        if supabase:
            try:
                supabase.table('articles').update({
                    'generation_status': 'failed',
                    'generation_error': error_msg[:1000],  # Truncate long errors
                    'updated_at': datetime.now().isoformat(),
                }).eq('id', request.article_id).execute()
            except Exception as update_err:
                logger.error(f"[{job_id}] Failed to update error status: {update_err}")


async def _generate_content_embedding(
    headline: Optional[str] = None,
    intro: Optional[str] = None,
    direct_answer: Optional[str] = None,
    teaser: Optional[str] = None,
    html_content: Optional[str] = None,
) -> Optional[List[float]]:
    """
    Generate content embedding for semantic deduplication.
    Calls the content-embedder Modal service.
    
    Returns embedding vector (768 dimensions) or None on failure.
    """
    import httpx
    import re
    
    EMBEDDER_ENDPOINT = "https://clients--content-embedder-fastapi-app.modal.run"
    
    # Build embedding text (same logic as TypeScript buildArticleEmbeddingText)
    parts: List[str] = []
    
    # Headline - weight 2x by repeating
    if headline:
        parts.append(headline)
        parts.append(headline)
    
    # Direct answer - high value content
    if direct_answer:
        parts.append(direct_answer)
    
    # Intro paragraph
    if intro:
        parts.append(intro)
    
    # Teaser
    if teaser:
        parts.append(teaser)
    
    # Extract text from HTML content if no structured sections
    if html_content:
        text_content = html_content
        # Strip script and style tags
        text_content = re.sub(r'<script\b[^>]*>[\s\S]*?</script>', ' ', text_content, flags=re.IGNORECASE)
        text_content = re.sub(r'<style\b[^>]*>[\s\S]*?</style>', ' ', text_content, flags=re.IGNORECASE)
        # Strip all HTML tags
        text_content = re.sub(r'<[^>]+>', ' ', text_content)
        # Normalize whitespace
        text_content = re.sub(r'\s+', ' ', text_content).strip()
        if text_content:
            parts.append(text_content)
    
    full_text = " ".join(parts).strip()
    
    if not full_text:
        return None
    
    # Truncate to ~2000 tokens (~8000 chars)
    max_chars = 8000
    if len(full_text) > max_chars:
        full_text = full_text[:max_chars]
        # Try to end at sentence boundary
        last_period = full_text.rfind('.')
        if last_period > max_chars * 0.8:
            full_text = full_text[:last_period + 1]
    
    # Call embedding service
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{EMBEDDER_ENDPOINT}/embed",
            json={
                "texts": [full_text],
                "task_type": "SEMANTIC_SIMILARITY",
            },
        )
        response.raise_for_status()
        
        data = response.json()
        embeddings = data.get("embeddings", [])
        
        if embeddings and len(embeddings) > 0:
            return embeddings[0]
        
        return None


async def _create_google_doc_for_article(title: str, html_content: str, folder_id: str) -> Dict[str, Any]:
    """Create a Google Doc with the blog content and return its metadata."""
    import json
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    
    sa_json = (
        os.getenv("GOOGLE_SERVICE_ACCOUNT") or
        os.getenv("SERVICE_ACCOUNT_JSON") or
        os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    )
    if not sa_json:
        raise ValueError("No service account JSON configured")
    
    sa_info = json.loads(sa_json)
    
    # Create credentials with delegation
    credentials = service_account.Credentials.from_service_account_info(
        sa_info,
        scopes=['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents']
    )
    # Optional: Domain-wide delegation subject (set GOOGLE_DELEGATION_SUBJECT env var)
    delegation_subject = os.getenv("GOOGLE_DELEGATION_SUBJECT")
    if delegation_subject:
        credentials = credentials.with_subject(delegation_subject)
    
    # Create Drive service
    drive_service = build('drive', 'v3', credentials=credentials)
    docs_service = build('docs', 'v1', credentials=credentials)
    
    # Create empty document in folder
    file_metadata = {
        'name': title,
        'mimeType': 'application/vnd.google-apps.document',
        'parents': [folder_id] if folder_id else [],
    }
    
    doc_file = drive_service.files().create(
        body=file_metadata,
        fields='id, name, webViewLink'
    ).execute()
    
    doc_id = doc_file['id']
    
    # Convert HTML to simple text with formatting preserved
    # Note: Google Docs API doesn't support direct HTML import via REST API
    # We'll insert plain text for now - full HTML formatting would require
    # Google Apps Script or the Drive API's import feature
    import re
    
    # Strip HTML tags but preserve structure
    text_content = html_content
    text_content = re.sub(r'<h1[^>]*>(.*?)</h1>', r'\n# \1\n', text_content)
    text_content = re.sub(r'<h2[^>]*>(.*?)</h2>', r'\n## \1\n', text_content)
    text_content = re.sub(r'<h3[^>]*>(.*?)</h3>', r'\n### \1\n', text_content)
    text_content = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', text_content)
    text_content = re.sub(r'<li[^>]*>(.*?)</li>', r'• \1\n', text_content)
    text_content = re.sub(r'<br\s*/?>', '\n', text_content)
    text_content = re.sub(r'<[^>]+>', '', text_content)  # Remove remaining tags
    text_content = re.sub(r'\n{3,}', '\n\n', text_content)  # Collapse multiple newlines
    text_content = text_content.strip()
    
    # Insert content into document
    if text_content:
        requests = [{
            'insertText': {
                'location': {'index': 1},
                'text': text_content
            }
        }]
        docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={'requests': requests}
        ).execute()
    
    return {
        'id': doc_id,
        'name': doc_file['name'],
        'webViewLink': doc_file.get('webViewLink', f'https://docs.google.com/document/d/{doc_id}/edit'),
    }


@app.post("/write-async")
async def write_blog_async(request: AsyncBlogRequest):
    """
    Generate a blog article asynchronously with fire-and-forget architecture.
    
    This endpoint:
    1. Returns immediately with job_id and status 'pending'
    2. Queues the job for background processing
    3. Supports 5+ minute generation times for high-quality content
    4. Provides webhook callback when complete (optional)
    5. Persistent job tracking that survives server restarts
    
    Fire-and-forget design:
    - Submit job → get job_id
    - Poll /jobs/{job_id}/status for progress
    - Retrieve results when complete
    - Optional webhook notification
    
    Quality-first approach:
    - Default 30-minute timeout (configurable)
    - No rush for completion
    - Deep research and tools enabled
    - AEO scoring and quality gates
    """
    try:
        # Build client_info with Supabase integration details BEFORE creating job config
        client_info = request.client_info or {}
        if request.article_id and request.supabase_url and request.supabase_service_key:
            # Add Supabase integration info to client_info
            client_info = {
                **client_info,
                "article_id": request.article_id,
                "supabase_url": request.supabase_url,
                "supabase_service_key": request.supabase_service_key,
                "gdoc_folder_id": request.gdoc_folder_id,
                "keyword_id": request.keyword_id,
                "project_id": request.project_id,
            }
        
        # Build job configuration with client_info included
        job_config = JobConfig(
            primary_keyword=request.primary_keyword,
            company_url=request.company_url,
            language=request.language,
            country=request.country,
            company_name=request.company_name,
            company_data=request.company_data.model_dump() if request.company_data else None,
            sitemap_urls=request.sitemap_urls,
            existing_blog_slugs=[s.model_dump() for s in request.existing_blog_slugs] if request.existing_blog_slugs else None,
            batch_siblings=[s.model_dump() for s in request.batch_siblings] if request.batch_siblings else None,
            batch_id=request.batch_id,
            content_generation_instruction=request.content_generation_instruction,
            word_count=request.word_count,
            tone=request.tone,
            system_prompts=request.system_prompts,
            review_prompts=request.review_prompts,
            slug=request.slug,
            index=request.index,
            callback_url=request.callback_url,
            priority=request.priority,
            max_duration_minutes=request.max_duration_minutes,
            client_info=client_info,  # Include Supabase integration info
        )
        
        # Submit job to manager
        job_manager = get_job_manager()
        job_id = job_manager.submit_job(job_config)
        
        return {
            "success": True,
            "job_id": job_id,
            "status": "pending",
            "message": "Blog generation job queued. Use /jobs/{job_id}/status to track progress.",
            "polling_url": f"/jobs/{job_id}/status",
            "estimated_duration_minutes": "5-30 (quality takes time)",
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to submit async job",
        }


@app.get("/jobs/{job_id}/status")
async def get_job_status(job_id: str):
    """
    Get status and progress of an async blog generation job.
    
    Returns:
    - Current status (pending, running, completed, failed)
    - Progress percentage and current stage
    - Results if completed
    - Error details if failed
    - Execution times and quality metrics
    """
    try:
        job_manager = get_job_manager()
        result = job_manager.get_job_status(job_id)
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        response = {
            "job_id": result.job_id,
            "status": result.status.value,
            "created_at": result.created_at.isoformat(),
            "progress_percent": result.progress_percent,
            "stages_completed": result.stages_completed,
            "total_stages": result.total_stages,
        }
        
        if result.started_at:
            response["started_at"] = result.started_at.isoformat()
        
        if result.current_stage:
            response["current_stage"] = result.current_stage
        
        if result.status == JobStatus.COMPLETED:
            response["completed_at"] = result.completed_at.isoformat()
            response["duration_seconds"] = result.duration_seconds
            response["result"] = result.result_data
            if result.quality_score:
                response["quality_score"] = result.quality_score
        
        elif result.status == JobStatus.FAILED:
            response["completed_at"] = result.completed_at.isoformat()
            response["duration_seconds"] = result.duration_seconds
            response["error"] = result.error_message
            response["retry_count"] = result.retry_count
        
        elif result.status == JobStatus.RUNNING:
            # Estimate remaining time based on progress
            if result.progress_percent > 0:
                elapsed = (datetime.now() - result.started_at).total_seconds()
                estimated_total = elapsed / (result.progress_percent / 100)
                estimated_remaining = max(0, estimated_total - elapsed)
                response["estimated_remaining_seconds"] = int(estimated_remaining)
        
        return response
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs")
async def list_jobs(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    List blog generation jobs with optional filtering.
    
    Args:
        status: Filter by job status (pending, running, completed, failed, cancelled)
        limit: Maximum results (default 50)
        offset: Pagination offset (default 0)
    """
    try:
        job_manager = get_job_manager()
        
        status_enum = None
        if status:
            try:
                status_enum = JobStatus(status)
            except ValueError:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid status '{status}'. Valid: {[s.value for s in JobStatus]}"
                )
        
        jobs = job_manager.list_jobs(status=status_enum, limit=limit, offset=offset)
        
        results = []
        for job in jobs:
            job_data = {
                "job_id": job.job_id,
                "status": job.status.value,
                "created_at": job.created_at.isoformat(),
                "progress_percent": job.progress_percent,
                "stages_completed": job.stages_completed,
            }
            
            if job.completed_at:
                job_data["completed_at"] = job.completed_at.isoformat()
                job_data["duration_seconds"] = job.duration_seconds
            
            if job.status == JobStatus.FAILED:
                job_data["error"] = job.error_message
            
            if job.quality_score:
                job_data["quality_score"] = job.quality_score
            
            results.append(job_data)
        
        return {
            "jobs": results,
            "total": len(results),
            "limit": limit,
            "offset": offset,
            "has_more": len(results) == limit,
        }
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """
    Cancel a pending or running blog generation job.
    
    Returns:
        Success/failure status
    """
    try:
        job_manager = get_job_manager()
        success = job_manager.cancel_job(job_id)
        
        if not success:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot cancel job {job_id} (not found or already completed)"
            )
        
        return {
            "success": True,
            "job_id": job_id,
            "message": "Job cancelled successfully",
        }
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/stats")
async def get_job_stats():
    """
    Get job manager statistics and health metrics.
    
    Returns:
        - Job counts by status
        - Average execution time
        - Current running jobs
        - System capacity
    """
    try:
        job_manager = get_job_manager()
        stats = job_manager.get_stats()
        
        return {
            "status_counts": stats["status_counts"],
            "running_jobs": stats["running_jobs"],
            "max_concurrent": stats["max_concurrent"],
            "capacity_used_percent": int(stats["running_jobs"] / stats["max_concurrent"] * 100),
            "average_duration_seconds": stats["avg_duration_seconds"],
            "database_path": stats["database_path"],
            "timestamp": datetime.now().isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/errors")
async def get_error_summary():
    """
    Get error summary and monitoring information.
    
    Returns:
        - Error counts by category and stage
        - Recent errors
        - System health indicators
    """
    try:
        from pipeline.core.error_handling import error_reporter
        
        summary = error_reporter.get_error_summary()
        
        # Add job manager stats
        job_manager = get_job_manager()
        job_stats = job_manager.get_stats()
        
        # Calculate error rates
        total_errors = summary["total_errors"]
        total_jobs = sum(job_stats["status_counts"].values())
        error_rate = (total_errors / total_jobs * 100) if total_jobs > 0 else 0
        
        return {
            "error_summary": summary,
            "job_stats": job_stats,
            "error_rate_percent": round(error_rate, 2),
            "system_health": "healthy" if error_rate < 5 else "degraded" if error_rate < 15 else "unhealthy",
            "timestamp": datetime.now().isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# IMAGE GENERATION ENDPOINT
# =============================================================================

class CompanyImageDataModel(BaseModel):
    """Company context for image generation."""
    name: str = Field(..., description="Company name")
    industry: str = Field(..., description="Company industry")
    language: str = Field(..., description="Target language for alt text")
    custom_prompt_instructions: Optional[str] = Field(None, description="Custom image prompt instructions")


class ImageGenerationRequestModel(BaseModel):
    """Request for image generation."""
    headline: str = Field(..., description="Blog headline")
    keyword: str = Field(..., description="Primary keyword")
    company_data: CompanyImageDataModel = Field(..., description="Company context")
    project_folder_id: Optional[str] = Field(None, description="Project Drive folder ID for organized storage")


class ImageGenerationResponseModel(BaseModel):
    """Response from image generation."""
    success: bool
    image_url: Optional[str] = Field(None, description="Public Drive URL for the image")
    alt_text: Optional[str] = Field(None, description="Generated alt text")
    drive_file_id: Optional[str] = Field(None, description="Google Drive file ID")
    generation_time_seconds: float = Field(0.0, description="Time taken to generate")
    prompt_used: Optional[str] = Field(None, description="The prompt used for generation")
    error: Optional[str] = Field(None, description="Error message if failed")


@app.post("/generate-image", response_model=ImageGenerationResponseModel)
async def generate_image(request: ImageGenerationRequestModel):
    """
    Generate an AI image for a blog article using Google GenAI SDK (gemini-2.5-flash-image).
    
    Steps:
    1. Build image prompt from article context
    2. Generate image using Google GenAI SDK (gemini-2.5-flash-image)
    3. Upload to Google Drive
    4. Make publicly viewable
    5. Return URL and metadata
    
    Expected duration: 10-20 seconds
    """
    try:
        from .image_generator import (
            ImageGenerator, 
            ImageGenerationRequest as ImgReq,
            CompanyImageData,
        )
        
        generator = ImageGenerator()
        
        img_request = ImgReq(
            headline=request.headline,
            keyword=request.keyword,
            project_folder_id=request.project_folder_id,
            company_data=CompanyImageData(
                name=request.company_data.name,
                industry=request.company_data.industry,
                language=request.company_data.language,
                custom_prompt_instructions=request.company_data.custom_prompt_instructions,
            ),
        )
        
        result = await generator.generate(img_request)
        
        return ImageGenerationResponseModel(
            success=result.success,
            image_url=result.image_url,
            alt_text=result.alt_text,
            drive_file_id=result.drive_file_id,
            generation_time_seconds=result.generation_time_seconds,
            prompt_used=result.prompt_used,
            error=result.error,
        )
        
    except Exception as e:
        return ImageGenerationResponseModel(
            success=False,
            generation_time_seconds=0.0,
            error=str(e),
        )


# =============================================================================
# GRAPHICS GENERATION ENDPOINT
# =============================================================================

class GraphicsGenerationRequestModel(BaseModel):
    """Request for graphics generation (legacy API)."""
    graphic_type: str = Field(..., description="Type: headline, quote, metric, cta, infographic")
    content: Dict[str, Any] = Field(..., description="Type-specific content")
    company_data: Optional[Dict[str, Any]] = Field(None, description="Company context")
    project_folder_id: Optional[str] = Field(None, description="Project Drive folder ID")
    dimensions: Optional[List[int]] = Field([1920, 1080], description="Image dimensions [width, height] - default horizontal format")


class GraphicsConfigRequestModel(BaseModel):
    """Request for JSON config-based graphics generation (new component system)."""
    config: Dict[str, Any] = Field(..., description="JSON config with theme and components")
    project_folder_id: Optional[str] = Field(None, description="Project Drive folder ID")
    dimensions: Optional[List[int]] = Field([1920, 1080], description="Image dimensions [width, height]")


class GraphicsGenerationResponseModel(BaseModel):
    """Response from graphics generation."""
    success: bool
    image_url: Optional[str] = Field(None, description="Public Drive URL or base64 data URI")
    alt_text: Optional[str] = Field(None, description="Generated alt text")
    drive_file_id: Optional[str] = Field(None, description="Google Drive file ID")
    generation_time_seconds: float = Field(0.0, description="Time taken to generate")
    error: Optional[str] = Field(None, description="Error message if failed")


@app.post("/generate-graphics", response_model=GraphicsGenerationResponseModel)
async def generate_graphics(request: GraphicsGenerationRequestModel):
    """
    Generate HTML-based graphics (openfigma style) and convert to PNG.
    
    Supports:
    - headline: Case study style headlines
    - quote: Testimonial/quote graphics
    - metric: Statistics/metrics graphics
    - cta: Call-to-action cards
    - infographic: Diagram-style infographics
    
    Expected duration: 5-10 seconds
    """
    try:
        from .graphics_generator import (
            GraphicsGenerator,
            GraphicsGenerationRequest as GraphicsReq,
        )
        
        generator = GraphicsGenerator()
        
        graphics_request = GraphicsReq(
            graphic_type=request.graphic_type,
            content=request.content,
            company_data=request.company_data,
            project_folder_id=request.project_folder_id,
            dimensions=tuple(request.dimensions) if request.dimensions else (1920, 1080),
        )
        
        result = await generator.generate(graphics_request)
        
        return GraphicsGenerationResponseModel(
            success=result.success,
            image_url=result.image_url,
            alt_text=result.alt_text,
            drive_file_id=result.drive_file_id,
            generation_time_seconds=result.generation_time_seconds,
            error=result.error,
        )
        
    except Exception as e:
        return GraphicsGenerationResponseModel(
            success=False,
            generation_time_seconds=0.0,
            error=str(e),
        )


class GraphicsConfigRequestModel(BaseModel):
    """Request for JSON config-based graphics generation (new component system)."""
    config: Dict[str, Any] = Field(..., description="JSON config with theme and components")
    project_folder_id: Optional[str] = Field(None, description="Project Drive folder ID")
    dimensions: Optional[List[int]] = Field([1920, 1080], description="Image dimensions [width, height]")


@app.post("/generate-graphics-config", response_model=GraphicsGenerationResponseModel)
async def generate_graphics_from_config(request: GraphicsConfigRequestModel):
    """
    Generate graphics from JSON config (new component-based API).
    
    Build graphics by composing reusable components with custom themes.
    See docs/GRAPHICS_CONFIG.md for complete documentation.
    """
    try:
        from .graphics_generator import GraphicsGenerator
        
        generator = GraphicsGenerator()
        
        result = await generator.generate_from_config(
            config=request.config,
            dimensions=tuple(request.dimensions) if request.dimensions else (1920, 1080),
            project_folder_id=request.project_folder_id,
        )
        
        return GraphicsGenerationResponseModel(
            success=result.success,
            image_url=result.image_url,
            alt_text=result.alt_text,
            drive_file_id=result.drive_file_id,
            generation_time_seconds=result.generation_time_seconds,
            error=result.error,
        )
        
    except Exception as e:
        logger.error(f"Error generating graphics from config: {e}", exc_info=True)
        return GraphicsGenerationResponseModel(
            success=False,
            generation_time_seconds=0.0,
            error=str(e),
        )


# =============================================================================
# TRANSLATION ENDPOINT
# =============================================================================

class TranslateRequestModel(BaseModel):
    """Request for blog translation."""
    # Content to translate
    html_content: str = Field(..., description="Original blog HTML content")
    headline: str = Field(..., description="Original headline")
    meta_title: str = Field(..., description="Original meta title")
    meta_description: str = Field(..., description="Original meta description")
    teaser: Optional[str] = Field(None, description="Original teaser")
    direct_answer: Optional[str] = Field(None, description="Original direct answer")
    intro: Optional[str] = Field(None, description="Original intro paragraph")
    key_takeaways: Optional[List[str]] = Field(default_factory=list, description="Original key takeaways")
    faq: Optional[List[FAQEntry]] = Field(default_factory=list, description="Original FAQ entries")
    paa: Optional[List[FAQEntry]] = Field(default_factory=list, description="Original PAA entries")
    
    # Translation context
    source_language: str = Field(..., description="Source language code (e.g., 'de')")
    target_language: str = Field(..., description="Target language code (e.g., 'en')")
    target_country: str = Field(..., description="Target country code (e.g., 'US')")
    
    # Optional context
    company_name: Optional[str] = Field(None, description="Company name for context")
    primary_keyword: Optional[str] = Field(None, description="Primary keyword to preserve")


class TranslateResponseModel(BaseModel):
    """Response from blog translation."""
    success: bool
    duration_seconds: float = 0.0
    
    # Translated content
    html_content: Optional[str] = Field(None, description="Translated HTML content")
    headline: Optional[str] = Field(None, description="Translated headline")
    meta_title: Optional[str] = Field(None, description="Translated meta title")
    meta_description: Optional[str] = Field(None, description="Translated meta description")
    teaser: Optional[str] = Field(None, description="Translated teaser")
    direct_answer: Optional[str] = Field(None, description="Translated direct answer")
    intro: Optional[str] = Field(None, description="Translated intro paragraph")
    key_takeaways: List[str] = Field(default_factory=list, description="Translated key takeaways")
    faq: List[FAQEntry] = Field(default_factory=list, description="Translated FAQ entries")
    paa: List[FAQEntry] = Field(default_factory=list, description="Translated PAA entries")
    
    # Metadata
    source_language: Optional[str] = None
    target_language: Optional[str] = None
    target_country: Optional[str] = None
    
    # Quality validation
    quality_issues: List[str] = Field(default_factory=list, description="Market quality validation issues")
    
    error: Optional[str] = Field(None, description="Error message if failed")


@app.post("/translate", response_model=TranslateResponseModel)
async def translate_blog(request: TranslateRequestModel):
    """
    Translate a blog article to another language/market with intelligent market adaptation.
    
    Uses Gemini to translate while preserving:
    - HTML structure and formatting
    - Citation markers [1], [2], etc.
    - Internal link URLs (only translates anchor text)
    - SEO optimization for target market
    - Market-specific authorities and regulatory context
    - Local cultural adaptations
    
    Expected duration: 30-60 seconds
    """
    import time
    import json
    import re
    import httpx
    from pipeline.prompts.main_article import MARKET_CONFIG, MARKET_EXAMPLES, validate_country
    
    start_time = time.time()
    
    try:
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not configured")
        
        # Get market intelligence for target country
        validated_country = validate_country(request.target_country)
        market_config = MARKET_CONFIG.get(validated_country, {
            "authorities": [],
            "regulatory_style": "According to local industry standards...",
            "quality_note": f"Professional standards for {validated_country} market"
        })
        market_examples = MARKET_EXAMPLES.get(validated_country, {
            "good_headings": ["How does it work?", "What are the benefits?"],
            "list_examples": ["Requirements:", "How to proceed:", "Benefits overview:"]
        })
        
        # Build market context for translation with research integration
        authorities_context = ""
        research_context = ""
        
        if market_config.get("authorities"):
            authorities = ", ".join(market_config["authorities"])
            authorities_context = f"""
MARKET AUTHORITIES: When translating, incorporate relevant references to these local authorities where appropriate: {authorities}
- Use them naturally in context (e.g., regulations, certifications, compliance)
- Adapt generic "industry standards" to specific authority guidelines
- Example style: "{market_config.get('regulatory_style', 'According to local standards...')}"
"""
            
            # Add research context for real-time market intelligence
            if request.primary_keyword:
                research_context = f"""
MARKET RESEARCH GUIDANCE: Consider recent developments in {validated_country} regarding {request.primary_keyword}:
- Look for current regulations, updates, or policy changes
- Include relevant government programs or incentives
- Reference local market trends or industry developments
- Ensure compliance terminology is current and accurate
"""
        
        examples_context = ""
        if market_examples.get("good_headings"):
            headings = " / ".join(market_examples["good_headings"][:2])
            examples_context = f"""
MARKET EXAMPLES: Use culturally appropriate phrasing like: "{headings}"
"""
        
        # Build enhanced market-aware translation prompt
        system_prompt = f"""You are a professional translator specializing in SEO-optimized, market-aware content.

TASK: Translate the blog content from {request.source_language} to {request.target_language} for the {validated_country} market.

MARKET INTELLIGENCE:
{authorities_context}{examples_context}{research_context}
MARKET ADAPTATION: Go beyond literal translation - adapt content to local market context, regulations, and cultural expectations for {validated_country}.

CRITICAL RULES:
1. Preserve ALL HTML tags exactly as they are (<p>, <h2>, <h3>, <ul>, <ol>, <li>, <a>, <strong>)
2. Keep citation markers [1], [2], etc. in their exact positions
3. Preserve internal link URLs but translate anchor text naturally
4. Adapt idioms and expressions for the {validated_country} market
5. Maintain SEO-friendly structure and keyword placement
6. Keep the same professional, authoritative tone
7. Ensure meta_title is ≤55 characters
8. Ensure meta_description is ≤130 characters with a CTA
9. MARKET ADAPTATION: Replace generic references with market-specific context:
   - "Industry standards" → "{market_config.get('regulatory_style', 'Local standards')}"
   - Add local authority mentions where relevant
   - Use culturally appropriate examples and phrasing
10. AUTHORITY INTEGRATION: Naturally incorporate local authorities when discussing:
    - Regulations, compliance, certifications
    - Government programs, funding, incentives
    - Professional standards and requirements

Return ONLY valid JSON with these fields:
{{
  "html_content": "translated HTML content",
  "headline": "translated headline",
  "meta_title": "translated SEO title (≤55 chars)",
  "meta_description": "translated meta description (≤130 chars)",
  "teaser": "translated teaser",
  "direct_answer": "translated direct answer",
  "intro": "translated intro",
  "key_takeaways": ["translated takeaway 1", "translated takeaway 2", "translated takeaway 3"],
  "faq": [{{"question": "translated Q1", "answer": "translated A1"}}, ...],
  "paa": [{{"question": "translated Q1", "answer": "translated A1"}}, ...]
}}"""

        # Build content to translate
        content_to_translate = {
            "html_content": request.html_content,
            "headline": request.headline,
            "meta_title": request.meta_title,
            "meta_description": request.meta_description,
            "teaser": request.teaser or "",
            "direct_answer": request.direct_answer or "",
            "intro": request.intro or "",
            "key_takeaways": request.key_takeaways or [],
            "faq": [{"question": f.question, "answer": f.answer} for f in (request.faq or [])],
            "paa": [{"question": p.question, "answer": p.answer} for p in (request.paa or [])],
        }
        
        user_message = f"""Company: {request.company_name or 'N/A'}
Primary Keyword: {request.primary_keyword or 'N/A'}
Target Market: {validated_country}
Market Quality Standards: {market_config.get('quality_note', f'Professional standards for {validated_country}')}

Content to translate:
{json.dumps(content_to_translate, ensure_ascii=False, indent=2)}"""

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={api_key}"
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": f"{system_prompt}\n\n{user_message}"
                }]
            }],
            "generationConfig": {
                "temperature": 0.3,  # Lower temperature for translation accuracy
                "maxOutputTokens": 8000
            }
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        
        result = response.json()
        candidate = result.get("candidates", [{}])[0]
        content_text = candidate.get("content", {}).get("parts", [{}])[0].get("text", "")
        
        if not content_text:
            raise ValueError("Empty response from Gemini")
        
        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', content_text)
        if not json_match:
            raise ValueError("No JSON in translation response")
        
        translated = json.loads(json_match.group())
        
        # Build FAQ/PAA entries
        translated_faq = [
            FAQEntry(question=f["question"], answer=f["answer"])
            for f in translated.get("faq", [])
        ]
        translated_paa = [
            FAQEntry(question=p["question"], answer=p["answer"])
            for p in translated.get("paa", [])
        ]
        
        # Apply market quality validation to translated content
        quality_issues = []
        try:
            from pipeline.processors.quality_checker import QualityChecker
            
            # Build article structure for quality check
            translated_article = {
                'Headline': translated.get('headline', ''),
                'Intro': translated.get('intro', ''),
                'html_content': translated.get('html_content', ''),
                'Meta_Title': translated.get('meta_title', ''),
                'Meta_Description': translated.get('meta_description', ''),
            }
            
            # Create market profile for validation
            market_profile = {
                'min_word_count': market_config.get('min_word_count', 1500),
                'target_word_count': market_config.get('word_count_target', '1500-2000'),
                'authorities': market_config.get('authorities', [])
            }
            
            # Run market quality checks
            market_issues = QualityChecker._check_market_quality(translated_article, market_profile)
            quality_issues.extend(market_issues)
            
        except Exception as quality_error:
            # Don't fail translation due to quality check errors
            quality_issues.append(f"Quality check error: {str(quality_error)}")
        
        duration = time.time() - start_time
        
        return TranslateResponseModel(
            success=True,
            duration_seconds=duration,
            html_content=translated.get("html_content"),
            headline=translated.get("headline"),
            meta_title=translated.get("meta_title"),
            meta_description=translated.get("meta_description"),
            teaser=translated.get("teaser"),
            direct_answer=translated.get("direct_answer"),
            intro=translated.get("intro"),
            key_takeaways=translated.get("key_takeaways", []),
            faq=translated_faq,
            paa=translated_paa,
            source_language=request.source_language,
            target_language=request.target_language,
            target_country=validated_country,
            quality_issues=quality_issues,
        )
        
    except Exception as e:
        duration = time.time() - start_time
        return TranslateResponseModel(
            success=False,
            duration_seconds=duration,
            error=str(e),
        )


class ContentRefreshRequest(BaseModel):
    """Request model for content refresh."""
    content: str = Field(..., description="Existing content in any format (HTML, Markdown, JSON, plain text)")
    content_format: Optional[str] = Field(None, description="Content format hint ('html', 'markdown', 'json', 'text'). Auto-detected if not provided")
    instructions: List[str] = Field(..., description="List of instructions/prompts for what to change (e.g., 'Update statistics to 2025', 'Make tone more professional')")
    target_sections: Optional[List[int]] = Field(None, description="Optional: List of section indices to update (0-based). If not provided, updates all sections")
    output_format: str = Field("json", description="Output format: 'json', 'html', or 'markdown'")
    include_diff: bool = Field(False, description="If True, includes diff showing changes made (unified + HTML format)")
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        """Ensure content is not empty."""
        if not v or not v.strip():
            raise ValueError("Content cannot be empty")
        if len(v) > 1_000_000:  # 1MB limit
            raise ValueError("Content too large (max 1MB)")
        return v
    
    @field_validator('instructions')
    @classmethod
    def validate_instructions(cls, v):
        """Ensure at least one instruction is provided."""
        if not v or len(v) == 0:
            raise ValueError("At least one instruction is required")
        if len(v) > 10:
            raise ValueError("Too many instructions (max 10)")
        for instruction in v:
            if not instruction or not instruction.strip():
                raise ValueError("Instructions cannot be empty")
        return v
    
    @field_validator('content_format')
    @classmethod
    def validate_content_format(cls, v):
        """Validate content format is one of the allowed values."""
        if v and v.lower() not in ['html', 'markdown', 'json', 'text']:
            raise ValueError("content_format must be one of: html, markdown, json, text")
        return v.lower() if v else None
    
    @field_validator('output_format')
    @classmethod
    def validate_output_format(cls, v):
        """Validate output format is one of the allowed values."""
        if v.lower() not in ['json', 'html', 'markdown']:
            raise ValueError("output_format must be one of: json, html, markdown")
        return v.lower()
    
    @field_validator('target_sections')
    @classmethod
    def validate_target_sections(cls, v):
        """Validate section indices are valid."""
        if v is not None:
            if len(v) == 0:
                raise ValueError("target_sections cannot be empty list (use None for all sections)")
            if len(v) > 50:
                raise ValueError("Too many target sections (max 50)")
            if any(idx < 0 for idx in v):
                raise ValueError("Section indices must be non-negative")
            if len(v) != len(set(v)):
                raise ValueError("Duplicate section indices are not allowed")
        return v


class ContentRefreshResponse(BaseModel):
    """Response model for content refresh."""
    success: bool
    refreshed_content: Optional[Dict[str, Any]] = Field(None, description="Refreshed content in structured format")
    refreshed_html: Optional[str] = Field(None, description="Refreshed content as HTML")
    refreshed_markdown: Optional[str] = Field(None, description="Refreshed content as Markdown")
    sections_updated: int = Field(0, description="Number of sections updated")
    diff_text: Optional[str] = Field(None, description="Unified diff showing changes (if include_diff=True)")
    diff_html: Optional[str] = Field(None, description="HTML diff showing changes with highlighting (if include_diff=True)")
    error: Optional[str] = Field(None, description="Error message if failed")


@app.post("/refresh", response_model=ContentRefreshResponse)
@limiter.limit("10/minute")
async def refresh_content(refresh_request: ContentRefreshRequest, request: Request):
    """
    Refresh/correct existing content using prompts with structured JSON output (v2.0).
    
    RATE LIMIT: 10 requests per minute per IP address.
    
    NEW in v2.0: Uses structured JSON output to prevent hallucinations (same fix as v4.0 blog generation).
    No more "You can aI code" or other context loss bugs.
    
    Similar to ChatGPT Canvas - updates specific parts without full rewrite.
    
    Supports flexible input formats:
    - HTML: Parses headings and paragraphs
    - Markdown: Converts to structured format
    - JSON: Structured blog format (with sections)
    - Plain text: Auto-detects sections by paragraphs
    
    Example 1: Update Statistics with Diff Preview
    ```json
    {
      "content": "<h1>Tech Trends</h1><h2>AI Adoption</h2><p>In 2023, 45% of companies used AI.</p>",
      "content_format": "html",
      "instructions": ["Update all statistics to 2025 data"],
      "target_sections": [0],
      "output_format": "html",
      "include_diff": true
    }
    ```
    
    Example 2: Make Tone More Professional (Markdown)
    ```json
    {
      "content": "# My Blog\\n\\n## Intro\\n\\nThis is kinda cool!",
      "content_format": "markdown",
      "instructions": ["Make tone more professional", "Expand with technical details"],
      "output_format": "markdown"
    }
    ```
    
    Example 3: Selective Section Updates (JSON)
    ```json
    {
      "content": "{\\"sections\\": [{\\"heading\\": \\"Intro\\", \\"content\\": \\"Old text\\"}]}",
      "content_format": "json",
      "instructions": ["Add 2025 trends", "Include examples"],
      "target_sections": [0, 2],
      "output_format": "json"
    }
    ```
    
    How It Works:
    1. Parse the input content into sections (auto-detects format if not specified)
    2. Update only the target sections based on instructions
    3. Keep other sections unchanged (preserves original exactly)
    4. Return refreshed content in requested format
    5. Optionally generate diff showing changes
    
    Returns:
        ContentRefreshResponse with:
        - refreshed_content: Structured content (always included)
        - refreshed_html: HTML output (if output_format='html')
        - refreshed_markdown: Markdown output (if output_format='markdown')
        - sections_updated: Count of updated sections
        - diff_text: Unified diff (if include_diff=True)
        - diff_html: HTML diff with highlighting (if include_diff=True)
        
    Error Codes:
        200: Success - Content refreshed successfully
        400: Bad Request - Invalid request parameters (e.g., empty content, invalid format)
        422: Unprocessable Entity - Validation errors (e.g., malformed JSON, empty instructions)
        429: Too Many Requests - Rate limit exceeded (max 10/minute per IP)
        500: Internal Server Error - Missing API key or Gemini API failure
        503: Service Unavailable - Temporary service issues
    
    Validation Rules:
        - content: Must not be empty, max 1MB
        - instructions: At least 1 required, max 10
        - content_format: Must be 'html', 'markdown', 'json', or 'text' (or None for auto-detect)
        - output_format: Must be 'json', 'html', or 'markdown'
        - target_sections: No duplicates, all indices >= 0
    
    Best Practices:
        - Use specific instructions (e.g., "Update Q3 2024 stats to Q4 2024" instead of "update stats")
        - Request diff preview (include_diff=True) to review changes before committing
        - Target specific sections to avoid unnecessary API calls
        - Use structured JSON input format for best results
        - Handle rate limiting gracefully (429 errors)
    """
    try:
        # Parse content into structured format
        parser = ContentParser()
        parsed_content = parser.parse(refresh_request.content, refresh_request.content_format)
        
        # Store original content for diff (if requested)
        original_content = parsed_content.copy() if refresh_request.include_diff else None
        
        # Initialize Gemini client for refresh
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_GEMINI_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="GOOGLE_API_KEY or GEMINI_API_KEY not configured"
            )
        
        gemini_client = GeminiClient(api_key=api_key)
        refresher = ContentRefresher(gemini_client)
        
        # Refresh content
        refreshed_content = await refresher.refresh_content(
            content=parsed_content,
            instructions=refresh_request.instructions,
            target_sections=refresh_request.target_sections,
        )
        
        # Count updated sections
        sections_updated = len(refresh_request.target_sections) if refresh_request.target_sections else len(refreshed_content.get('sections', []))
        
        # Format output based on requested format
        response_data = {
            "success": True,
            "refreshed_content": refreshed_content,
            "sections_updated": sections_updated,
        }
        
        # Generate diff if requested
        if refresh_request.include_diff and original_content:
            diff_text, diff_html = refresher.generate_diff(original_content, refreshed_content)
            response_data["diff_text"] = diff_text
            response_data["diff_html"] = diff_html
        
        if refresh_request.output_format == "html":
            response_data["refreshed_html"] = refresher.to_html(refreshed_content)
        elif refresh_request.output_format == "markdown":
            response_data["refreshed_markdown"] = refresher.to_markdown(refreshed_content)
        
        return ContentRefreshResponse(**response_data)
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 500 for missing API key)
        raise
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error in content refresh: {e}", exc_info=True)
        raise HTTPException(
            status_code=422,
            detail=f"Invalid JSON format in content: {str(e)}"
        )
    except ValueError as e:
        logger.error(f"Validation error in content refresh: {e}", exc_info=True)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid request: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Content refresh error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/debug/env")
async def debug_environment():
    """Debug endpoint to check environment variables and API key availability."""
    try:
        # Check common API key environment variable names
        api_key_vars = [
            "GOOGLE_API_KEY",
            "GEMINI_API_KEY", 
            "GOOGLE_GEMINI_API_KEY",
            "GEMINI_API_KEY_API",
            "GEMINI_API_KEY_KEY",
            "GEMINI",
            "GOOGLE",
        ]
        
        found_keys = {}
        for var_name in api_key_vars:
            value = os.getenv(var_name)
            if value:
                # Mask the key for security (show first 8 chars + ...)
                masked = f"{value[:8]}..." if len(value) > 8 else "***"
                found_keys[var_name] = {"available": True, "masked_value": masked}
            else:
                found_keys[var_name] = {"available": False, "masked_value": None}
        
        # Check all environment variables containing 'API' or 'KEY'
        api_env_vars = {}
        for key, value in os.environ.items():
            if 'API' in key.upper() or 'KEY' in key.upper():
                masked = f"{value[:8]}..." if len(value) > 8 else "***"
                api_env_vars[key] = masked
        
        # Test Google GenAI SDK
        genai_test = {"import_success": False, "client_creation": False, "tools_available": False}
        
        try:
            import google.genai as genai
            genai_test["import_success"] = True
            
            # Try to find an API key
            api_key = None
            api_key_source = None
            for var_name in api_key_vars:
                if os.getenv(var_name):
                    api_key = os.getenv(var_name)
                    api_key_source = var_name
                    break
            
            if api_key:
                try:
                    client = genai.Client(api_key=api_key)
                    genai_test["client_creation"] = True
                    genai_test["api_key_source"] = api_key_source
                    
                    # Test tools import
                    from google.genai.types import Tool, GoogleSearch, GenerateContentConfig
                    genai_test["tools_available"] = True
                    
                    # Test actual tool usage with a simple API call
                    try:
                        tools = [Tool(google_search=GoogleSearch())]
                        config = GenerateContentConfig(tools=tools, max_output_tokens=100)
                        test_response = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents="What is the capital of France? Use search to confirm.",
                            config=config,
                        )
                        genai_test["tools_test"] = {
                            "success": True,
                            "response_length": len(test_response.text) if test_response.text else 0,
                            "has_search_metadata": hasattr(test_response, 'search_metadata') or 'search' in str(test_response)
                        }
                    except Exception as tools_error:
                        genai_test["tools_test"] = {
                            "success": False,
                            "error": str(tools_error)
                        }
                    
                except Exception as client_error:
                    genai_test["client_error"] = str(client_error)
            else:
                genai_test["error"] = "No API key found"
                
        except ImportError as e:
            genai_test["import_error"] = str(e)
        
        return {
            "status": "success",
            "api_key_check": found_keys,
            "all_api_env_vars": list(api_env_vars.keys()),  # Don't expose values in production
            "genai_sdk_test": genai_test,
            "timestamp": "2025-12-03"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": "2025-12-03"
        }


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(
        "api:app",
        host=host,
        port=port,
        reload=True,
        log_level="info",
    )

