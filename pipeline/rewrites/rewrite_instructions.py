"""
Rewrite Instruction Models

Defines the data structures for targeted article rewrites.
"""

from pydantic import BaseModel, Field, validator
from typing import Literal, Optional, List
from enum import Enum


class RewriteMode(str, Enum):
    """
    Mode determines the type of rewrite operation.
    """
    REFRESH = "refresh"  # Update content with new information
    QUALITY_FIX = "quality_fix"  # Fix quality issues (keywords, length, AI markers)
    COMPREHENSIVE_TRANSFORM = "comprehensive_transform"  # Single-pass all-issues fix (Stage 2b)
    SEO_OPTIMIZE = "seo_optimize"  # Future: SEO-specific optimizations
    TRANSLATE = "translate"  # Future: Translate to another language


class RewriteTarget(str, Enum):
    """
    Target determines which part of the article to rewrite.
    """
    # Metadata
    HEADLINE = "Headline"
    SUBTITLE = "Subtitle"
    TEASER = "Teaser"
    INTRO = "Intro"
    META_TITLE = "Meta_Title"
    META_DESCRIPTION = "Meta_Description"
    
    # Sections (01-09)
    SECTION_01_TITLE = "section_01_title"
    SECTION_01_CONTENT = "section_01_content"
    SECTION_02_TITLE = "section_02_title"
    SECTION_02_CONTENT = "section_02_content"
    SECTION_03_TITLE = "section_03_title"
    SECTION_03_CONTENT = "section_03_content"
    SECTION_04_TITLE = "section_04_title"
    SECTION_04_CONTENT = "section_04_content"
    SECTION_05_TITLE = "section_05_title"
    SECTION_05_CONTENT = "section_05_content"
    SECTION_06_TITLE = "section_06_title"
    SECTION_06_CONTENT = "section_06_content"
    SECTION_07_TITLE = "section_07_title"
    SECTION_07_CONTENT = "section_07_content"
    SECTION_08_TITLE = "section_08_title"
    SECTION_08_CONTENT = "section_08_content"
    SECTION_09_TITLE = "section_09_title"
    SECTION_09_CONTENT = "section_09_content"
    
    # FAQ/PAA
    FAQ_01 = "faq_01"
    FAQ_02 = "faq_02"
    FAQ_03 = "faq_03"
    FAQ_04 = "faq_04"
    FAQ_05 = "faq_05"
    FAQ_06 = "faq_06"
    PAA_01 = "paa_01"
    PAA_02 = "paa_02"
    PAA_03 = "paa_03"
    PAA_04 = "paa_04"
    
    # Special: Rewrite multiple sections at once
    ALL_SECTIONS = "all_sections"  # All section_XX_content fields
    ALL_CONTENT = "all_content"  # All content (intro + sections)


class RewriteInstruction(BaseModel):
    """
    A single targeted rewrite instruction.
    
    Example (Refresh):
        RewriteInstruction(
            target="section_03_content",
            instruction="Update with 2025 Q4 statistics from latest sources",
            mode="refresh",
            preserve_structure=True
        )
    
    Example (Quality Fix):
        RewriteInstruction(
            target="all_sections",
            instruction="Reduce 'AI code generation tools 2025' from 27 to 5-8 mentions",
            mode="quality_fix",
            preserve_structure=True
        )
    """
    
    target: str = Field(
        ...,
        description="Field to rewrite (e.g., 'section_03_content', 'Headline', 'all_sections')"
    )
    
    instruction: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Specific instruction for what to change (10-500 chars)"
    )
    
    mode: RewriteMode = Field(
        default=RewriteMode.QUALITY_FIX,
        description="Type of rewrite operation"
    )
    
    preserve_structure: bool = Field(
        default=True,
        description="If True, maintain HTML structure, paragraph lengths, and citations"
    )
    
    preserve_citations: bool = Field(
        default=True,
        description="If True, keep existing citation numbers unless explicitly adding new sources"
    )
    
    preserve_links: bool = Field(
        default=True,
        description="If True, keep all internal and external links"
    )
    
    max_attempts: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Maximum retry attempts if validation fails (1-5)"
    )
    
    temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Gemini temperature (0.0-1.0). Lower = more consistent edits."
    )
    
    min_similarity: float = Field(
        default=0.70,
        ge=0.0,
        le=1.0,
        description="Minimum similarity between original and updated (0.0-1.0). Prevents full rewrites."
    )
    
    max_similarity: float = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
        description="Maximum similarity (0.0-1.0). Ensures changes were actually made."
    )
    
    context: Optional[dict] = Field(
        default=None,
        description="Additional context for the rewrite (e.g., {'primary_keyword': 'AI tools', 'target_mentions': 6})"
    )
    
    @validator('max_similarity')
    def max_must_be_greater_than_min(cls, v, values):
        """Ensure max_similarity > min_similarity"""
        if 'min_similarity' in values and v <= values['min_similarity']:
            raise ValueError('max_similarity must be greater than min_similarity')
        return v
    
    class Config:
        use_enum_values = True


class RewriteResult(BaseModel):
    """
    Result of a single rewrite operation.
    """
    
    target: str = Field(..., description="Field that was rewritten")
    
    success: bool = Field(..., description="Whether the rewrite succeeded")
    
    original_content: str = Field(..., description="Original content before rewrite")
    
    updated_content: Optional[str] = Field(None, description="Updated content after rewrite")
    
    similarity_score: Optional[float] = Field(
        None,
        description="Similarity between original and updated (0.0-1.0)"
    )
    
    attempts_used: int = Field(..., description="Number of attempts used")
    
    validation_passed: bool = Field(..., description="Whether validation checks passed")
    
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    metadata: Optional[dict] = Field(
        None,
        description="Additional metadata (tokens used, execution time, etc.)"
    )


class RewriteBatchRequest(BaseModel):
    """
    Request model for batch rewrites.
    
    Used by API endpoints and Stage 2b.
    """
    
    article: dict = Field(..., description="Article data (ArticleOutput.dict())")
    
    rewrites: List[RewriteInstruction] = Field(
        ...,
        min_items=1,
        max_items=10,
        description="List of rewrite instructions (1-10 max)"
    )
    
    mode: RewriteMode = Field(
        default=RewriteMode.QUALITY_FIX,
        description="Default mode for all rewrites (can be overridden per instruction)"
    )
    
    stop_on_failure: bool = Field(
        default=False,
        description="If True, stop processing on first failure"
    )


class RewriteBatchResponse(BaseModel):
    """
    Response model for batch rewrites.
    """
    
    success: bool = Field(..., description="Whether all rewrites succeeded")
    
    updated_article: dict = Field(..., description="Updated article data")
    
    results: List[RewriteResult] = Field(..., description="Individual rewrite results")
    
    total_attempts: int = Field(..., description="Total Gemini API calls made")
    
    total_time: float = Field(..., description="Total execution time in seconds")
    
    failures: int = Field(..., description="Number of failed rewrites")


# Pre-defined quality fix instructions (for Stage 2b)
QUALITY_FIX_TEMPLATES = {
    "keyword_overuse": RewriteInstruction(
        target="all_sections",
        instruction="Reduce '{keyword}' from {current} to {target_min}-{target_max} mentions. "
                   "Replace excess with semantic variations: {variations}.",
        mode=RewriteMode.QUALITY_FIX,
        preserve_structure=True,
        min_similarity=0.80,
        max_similarity=0.95
    ),
    
    "first_paragraph_short": RewriteInstruction(
        target="section_01_content",
        instruction="First paragraph is only {current_words} words (target: 60-100). "
                   "Expand with context, examples, or statistics. Keep the same tone and message.",
        mode=RewriteMode.QUALITY_FIX,
        preserve_structure=True,
        min_similarity=0.60,
        max_similarity=0.90
    ),
    
    "remove_em_dashes": RewriteInstruction(
        target="all_content",
        instruction="Remove all em dashes (—). Replace with commas, parentheses, or split into separate sentences.",
        mode=RewriteMode.QUALITY_FIX,
        preserve_structure=True,
        min_similarity=0.85,
        max_similarity=0.99
    ),
    
    "remove_robotic_phrases": RewriteInstruction(
        target="all_content",
        instruction="Remove robotic AI phrases: 'Here's how', 'Here's what', 'Key points:', 'Important considerations:'. "
                   "Rewrite naturally without these markers.",
        mode=RewriteMode.QUALITY_FIX,
        preserve_structure=True,
        min_similarity=0.80,
        max_similarity=0.95
    )
}

