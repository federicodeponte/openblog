"""
Output Schema Model

Defines the complete structure of extracted and validated article data.
This model matches the exact JSON schema output from Gemini in Stage 2.

Fields:
- Core: Headline, Subtitle, Teaser, Direct_Answer, Intro
- SEO: Meta Title, Meta Description
- Lead Gen: Lead_Survey_Title, Lead_Survey_Button (optional)
- Content: 9 sections × (title + content pairs)
- Engagement: 3 key takeaways + 4 PAA + 6 FAQ items
- Citations: Sources + Search Queries

Validation:
- Required fields must be non-empty strings
- Optional fields (Lead Survey, unused sections) may be empty
- Content fields must be valid Markdown (converted to HTML at rendering)
"""

from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
import logging
import re

logger = logging.getLogger(__name__)


class ComparisonTable(BaseModel):
    """
    Structured comparison table for products, tools, or features.
    
    Used for content that benefits from side-by-side comparisons.
    Examples: pricing tiers, tool features, before/after scenarios.
    """
    
    title: str = Field(..., description="Table title (e.g., 'AI Code Tools Comparison')")
    headers: List[str] = Field(..., description="Column headers (e.g., ['Tool', 'Price', 'Speed'])")
    rows: List[List[str]] = Field(..., description="Table rows, each row is a list matching header count")
    
    @field_validator('headers')
    @classmethod
    def validate_headers(cls, v):
        """Ensure headers exist and are reasonable."""
        if not v or len(v) < 2:
            raise ValueError("Table must have at least 2 columns")
        if len(v) > 6:
            raise ValueError("Table should not exceed 6 columns for readability")
        return v
    
    @field_validator('rows')
    @classmethod
    def validate_rows(cls, v, info):
        """Ensure rows match header count."""
        if not v:
            raise ValueError("Table must have at least one row")
        headers = info.data.get('headers', [])
        header_count = len(headers)
        
        for idx, row in enumerate(v):
            if len(row) != header_count:
                raise ValueError(f"Row {idx} has {len(row)} cells but table has {header_count} columns")
        
        if len(v) > 10:
            raise ValueError("Table should not exceed 10 rows for readability")
        
        return v


class ArticleOutput(BaseModel):
    """
    Complete article output schema (30+ fields).

    Maps to the exact JSON output from Gemini API response.
    """

    # Core content
    Headline: str = Field(..., description="Main article headline with primary keyword. NO [N] citations allowed.")
    Subtitle: Optional[str] = Field(
        default="",
        description="Optional sub-headline for context or angle. NO [N] citations.",
    )
    Teaser: str = Field(
        ...,
        description="2-3 sentence hook in MARKDOWN format highlighting pain point or benefit. Use **bold** for emphasis. NO [N] citations or em dashes allowed.",
    )
    Direct_Answer: str = Field(
        ...,
        description="40-60 word direct answer in MARKDOWN format to primary question. Use **bold** for key points. Use natural language attribution (NOT [N] citations).",
    )
    Intro: str = Field(
        ...,
        description="Opening paragraph (80-120 words) in MARKDOWN format framing the problem. Use **bold** for emphasis. NO [N] citations - use 'according to X' instead.",
    )

    # SEO metadata
    Meta_Title: str = Field(
        ...,
        description="≤55 character SEO title with primary keyword",
    )
    Meta_Description: str = Field(
        ...,
        description="≤130 character SEO description with CTA",
    )

    # Lead generation (optional)
    Lead_Survey_Title: Optional[str] = Field(default="", description="Optional survey title")
    Lead_Survey_Button: Optional[str] = Field(
        default="",
        description="Optional survey CTA button text",
    )

    # Content sections (9 sections × 2 fields)
    # Section 1 is now OPTIONAL to match Gemini's actual output format
    section_01_title: Optional[str] = Field(default="", description="Section 1 heading. NO [N] citations.")
    section_01_content: Optional[str] = Field(default="", description="Section 1 MARKDOWN content. Use **bold**, - lists. FORBIDDEN: [N] citations, em dashes, HTML tags. Use natural attribution.")
    section_02_title: Optional[str] = Field(default="", description="Section 2 heading. NO [N] citations.")
    section_02_content: Optional[str] = Field(default="", description="Section 2 MARKDOWN content. Use **bold**, - lists. FORBIDDEN: [N] citations, em dashes, HTML tags.")
    section_03_title: Optional[str] = Field(default="", description="Section 3 heading. NO [N] citations.")
    section_03_content: Optional[str] = Field(default="", description="Section 3 MARKDOWN content. Use **bold**, - lists. FORBIDDEN: [N] citations, em dashes, HTML tags.")
    section_04_title: Optional[str] = Field(default="", description="Section 4 heading. NO [N] citations.")
    section_04_content: Optional[str] = Field(default="", description="Section 4 MARKDOWN content. Use **bold**, - lists. FORBIDDEN: [N] citations, em dashes, HTML tags.")
    section_05_title: Optional[str] = Field(default="", description="Section 5 heading. NO [N] citations.")
    section_05_content: Optional[str] = Field(default="", description="Section 5 MARKDOWN content. Use **bold**, - lists. FORBIDDEN: [N] citations, em dashes, HTML tags.")
    section_06_title: Optional[str] = Field(default="", description="Section 6 heading. NO [N] citations.")
    section_06_content: Optional[str] = Field(default="", description="Section 6 MARKDOWN content. Use **bold**, - lists. FORBIDDEN: [N] citations, em dashes, HTML tags.")
    section_07_title: Optional[str] = Field(default="", description="Section 7 heading. NO [N] citations.")
    section_07_content: Optional[str] = Field(default="", description="Section 7 MARKDOWN content. Use **bold**, - lists. FORBIDDEN: [N] citations, em dashes, HTML tags.")
    section_08_title: Optional[str] = Field(default="", description="Section 8 heading. NO [N] citations.")
    section_08_content: Optional[str] = Field(default="", description="Section 8 MARKDOWN content. Use **bold**, - lists. FORBIDDEN: [N] citations, em dashes, HTML tags.")
    section_09_title: Optional[str] = Field(default="", description="Section 9 heading. NO [N] citations.")
    section_09_content: Optional[str] = Field(default="", description="Section 9 MARKDOWN content. Use **bold**, - lists. FORBIDDEN: [N] citations, em dashes, HTML tags.")

    # Key takeaways (3 items, at least 1 required)
    key_takeaway_01: Optional[str] = Field(default="", description="Key insight #1")
    key_takeaway_02: Optional[str] = Field(default="", description="Key insight #2")
    key_takeaway_03: Optional[str] = Field(default="", description="Key insight #3")

    # People Also Ask (PAA) - 4 items
    paa_01_question: Optional[str] = Field(default="", description="PAA question #1. NO [N] citations.")
    paa_01_answer: Optional[str] = Field(default="", description="PAA answer #1 in MARKDOWN format. Use **bold** for emphasis. NO [N] citations.")
    paa_02_question: Optional[str] = Field(default="", description="PAA question #2. NO [N] citations.")
    paa_02_answer: Optional[str] = Field(default="", description="PAA answer #2 in MARKDOWN format. Use **bold** for emphasis. NO [N] citations.")
    paa_03_question: Optional[str] = Field(default="", description="PAA question #3. NO [N] citations.")
    paa_03_answer: Optional[str] = Field(default="", description="PAA answer #3 in MARKDOWN format. Use **bold** for emphasis. NO [N] citations.")
    paa_04_question: Optional[str] = Field(default="", description="PAA question #4. NO [N] citations.")
    paa_04_answer: Optional[str] = Field(default="", description="PAA answer #4 in MARKDOWN format. Use **bold** for emphasis. NO [N] citations.")

    # FAQ - 6 items (5 minimum required)
    faq_01_question: Optional[str] = Field(default="", description="FAQ question #1. NO [N] citations.")
    faq_01_answer: Optional[str] = Field(default="", description="FAQ answer #1 in MARKDOWN format. Use **bold** for emphasis. NO [N] citations.")
    faq_02_question: Optional[str] = Field(default="", description="FAQ question #2. NO [N] citations.")
    faq_02_answer: Optional[str] = Field(default="", description="FAQ answer #2 in MARKDOWN format. Use **bold** for emphasis. NO [N] citations.")
    faq_03_question: Optional[str] = Field(default="", description="FAQ question #3. NO [N] citations.")
    faq_03_answer: Optional[str] = Field(default="", description="FAQ answer #3 in MARKDOWN format. Use **bold** for emphasis. NO [N] citations.")
    faq_04_question: Optional[str] = Field(default="", description="FAQ question #4. NO [N] citations.")
    faq_04_answer: Optional[str] = Field(default="", description="FAQ answer #4 in MARKDOWN format. Use **bold** for emphasis. NO [N] citations.")
    faq_05_question: Optional[str] = Field(default="", description="FAQ question #5. NO [N] citations.")
    faq_05_answer: Optional[str] = Field(default="", description="FAQ answer #5 in MARKDOWN format. Use **bold** for emphasis. NO [N] citations.")
    faq_06_question: Optional[str] = Field(default="", description="FAQ question #6. NO [N] citations.")
    faq_06_answer: Optional[str] = Field(default="", description="FAQ answer #6 in MARKDOWN format. Use **bold** for emphasis. NO [N] citations.")

    # Image (optional, generated in Stage 9)
    image_url: Optional[str] = Field(
        default="",
        description="URL to generated article image (1200x630)",
    )
    image_alt_text: Optional[str] = Field(
        default="",
        description="Alt text for article image (max 125 chars)",
    )

    # Sources and research
    Sources: Optional[str] = Field(
        default="",
        description="Citations as [1]: URL – description. Limited to 20 sources.",
    )
    Search_Queries: Optional[str] = Field(
        default="",
        description="Research queries documented (Q1: keyword...). One per line.",
    )
    
    # Comparison tables (optional, used when content benefits from structured comparison)
    tables: Optional[List[ComparisonTable]] = Field(
        default=[],
        description="Comparison tables (max 2 per article). Use for product comparisons, pricing tiers, feature matrices.",
    )
    
    # PRODUCTION FIX: Unified content for downstream processing
    unified_content: Optional[str] = Field(
        default="",
        description="Complete article in unified Markdown format. Created in Stage 3 from all schema fields.",
    )
    unified_word_count: Optional[int] = Field(
        default=0,
        description="Accurate word count of unified content. Used for production quality validation.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "Headline": "Complete Guide to Python Blog Writing in 2024",
                "Subtitle": "Master the art of writing engaging technical content",
                "Teaser": "Writing about Python can be challenging. This guide shows exactly how to craft engaging, SEO-optimized blog posts that rank.",
                "Direct_Answer": "Blog writing about Python requires balancing technical depth with accessibility, consistent research, and SEO optimization for discovery.",
                "Intro": "Python is one of the most discussed programming languages online...",
                "Meta_Title": "Python Blog Writing Guide 2024 | SCAILE",
                "Meta_Description": "Learn professional Python blog writing techniques for maximum reach and engagement.",
                "section_01_title": "Why Python Blog Writing Matters",
                "section_01_content": "<p>Python content serves multiple audiences...</p>",
                "Sources": "[1]: https://example.com – Research on Python trends",
            }
        }
    )

    @field_validator("Headline", "Teaser", "Direct_Answer", "Intro", "Meta_Title", "Meta_Description")
    @classmethod
    def required_fields_not_empty(cls, v):
        """Validate required fields are non-empty."""
        if not v or not v.strip():
            raise ValueError("This field is required and cannot be empty")
        return v.strip()

    @field_validator("Meta_Title")
    @classmethod
    def meta_title_length(cls, v):
        """Validate and auto-truncate Meta Title to SEO limits."""
        if len(v) > 60:
            logger.warning(f"Meta Title exceeds 60 chars: {len(v)} chars, truncating...")
            # Truncate to 60 chars (57 chars + "...")
            return v[:57] + "..." if len(v) > 60 else v
        return v

    @field_validator("Meta_Description")
    @classmethod
    def meta_description_length(cls, v):
        """Validate and auto-truncate Meta Description to SEO limits."""
        if len(v) > 160:
            logger.warning(f"Meta Description exceeds 160 chars: {len(v)} chars, truncating...")
            # Truncate to 160 chars with ellipsis
            truncated = v[:157] + "..."
            return truncated[:160]
        return v
    
    # ========== ROOT-LEVEL FIX VALIDATORS (from ROOT_LEVEL_FIX_PLAN.md) ==========
    
    @field_validator(
        'section_01_title', 'section_02_title', 'section_03_title',
        'section_04_title', 'section_05_title', 'section_06_title',
        'section_07_title', 'section_08_title', 'section_09_title',
        'paa_01_question', 'paa_02_question', 'paa_03_question', 'paa_04_question',
        'faq_01_question', 'faq_02_question', 'faq_03_question',
        'faq_04_question', 'faq_05_question', 'faq_06_question',
        mode='before'
    )
    @classmethod
    def clean_heading(cls, v: str) -> str:
        """
        Fix Issue A: Malformed headings like "What is How Do X??"
        
        Cleans:
        - Duplicate question prefixes (What is + How/Why/What)
        - Double punctuation (??, !!, ..)
        - HTML tags in plain text fields
        """
        if not v or not isinstance(v, str):
            return v
        
        v = v.strip()
        
        # Strip HTML tags from headings (should be plain text)
        v = re.sub(r'<[^>]+>', '', v)
        
        # Fix: Remove "What is" prefix if followed by another question word
        if v.startswith("What is "):
            rest = v[8:]  # Remove "What is "
            if rest.lower().startswith(("how ", "why ", "what ", "when ", "where ", "who ")):
                v = rest
                logger.info(f"🔧 Fixed malformed heading: removed duplicate 'What is' prefix")
        
        # Fix: Remove double punctuation
        original = v
        v = re.sub(r'\?{2,}', '?', v)  # ?? → ?
        v = re.sub(r'!{2,}', '!', v)  # !! → !
        v = re.sub(r'\.{2,}', '.', v)  # .. → .
        if v != original:
            logger.info(f"🔧 Fixed double punctuation in heading")
        
        return v.strip()
    
    @field_validator('Headline', 'Teaser', 'Direct_Answer', 'Intro', mode='before')
    @classmethod
    def warn_html_in_markdown_fields(cls, v: str) -> str:
        """
        Warn if HTML tags found in Markdown fields.
        Content should be pure Markdown, not HTML.
        """
        if not v or not isinstance(v, str):
            return v
        
        # Check if field contains HTML tags (should be Markdown)
        if '<p>' in v or '<ul>' in v or '<li>' in v or '<strong>' in v or '<em>' in v:
            logger.warning(f"⚠️ HTML tags found in Markdown field (should use **bold**, - lists): {v[:100]}...")
            logger.warning("   Content should be pure Markdown, not HTML. HTML will be stripped.")
            # Strip HTML tags as fallback
            cleaned = re.sub(r'<[^>]+>', '', v)
            return cleaned.strip()
        
        return v.strip()
    
    @field_validator(
        'section_01_content', 'section_02_content', 'section_03_content',
        'section_04_content', 'section_05_content', 'section_06_content',
        'section_07_content', 'section_08_content', 'section_09_content',
        'paa_01_answer', 'paa_02_answer', 'paa_03_answer', 'paa_04_answer',
        'faq_01_answer', 'faq_02_answer', 'faq_03_answer',
        'faq_04_answer', 'faq_05_answer', 'faq_06_answer',
        mode='before'
    )
    @classmethod
    def validate_markdown_syntax(cls, v: str) -> str:
        """
        Validate Markdown syntax in content fields.
        
        Checks for:
        - HTML tags (should be pure Markdown)
        - Proper list syntax (- or * for unordered lists)
        - Bold syntax (**text** not <strong>)
        
        This is a warning validator - doesn't block, just warns.
        """
        if not v or not isinstance(v, str):
            return v
        
        # Check for HTML tags (most common issue)
        html_tags = re.findall(r'<(p|ul|ol|li|div|span|strong|em|h[1-6])[\s>]', v, re.IGNORECASE)
        if html_tags:
            unique_tags = set(tag.lower() for tag in html_tags)
            logger.warning(
                f"⚠️ HTML tags found in Markdown content field: {', '.join(f'<{tag}>' for tag in unique_tags)}"
            )
            logger.warning(f"   Content should use Markdown syntax: **bold**, - lists, ## headings")
            logger.warning(f"   Preview: {v[:150]}...")
        
        return v
    
    @field_validator(
        'Headline', 'Subtitle', 'Teaser', 'Direct_Answer', 'Intro',
        'section_01_content', 'section_02_content', 'section_03_content',
        'section_04_content', 'section_05_content', 'section_06_content',
        'section_07_content', 'section_08_content', 'section_09_content',
        'paa_01_answer', 'paa_02_answer', 'paa_03_answer', 'paa_04_answer',
        'faq_01_answer', 'faq_02_answer', 'faq_03_answer',
        'faq_04_answer', 'faq_05_answer', 'faq_06_answer',
        mode='before'
    )
    @classmethod
    def validate_no_academic_citations(cls, v: str) -> str:
        """
        Fix Issue 1: WARN about academic citations [N] (Layer 4 will clean)
        
        Changed from BLOCKING to WARNING to prevent regeneration exhaustion.
        Layer 4 regex cleanup guarantees removal in final HTML.
        """
        if not v or not isinstance(v, str):
            return v
        
        # Check for academic citation patterns
        if re.search(r'\[\d+\]', v):
            count = len(re.findall(r'\[\d+\]', v))
            logger.warning(
                f"⚠️  Academic citations [N] detected ({count} instances) - "
                f"Layer 4 regex will clean. Preview: {v[:100]}..."
            )
            # DON'T RAISE - let Layer 4 handle cleanup
        
        return v
    
    @field_validator(
        'Headline', 'Subtitle', 'Teaser', 'Direct_Answer', 'Intro',
        'section_01_content', 'section_02_content', 'section_03_content',
        'section_04_content', 'section_05_content', 'section_06_content',
        'section_07_content', 'section_08_content', 'section_09_content',
        mode='before'
    )
    @classmethod
    def validate_no_em_dashes(cls, v: str) -> str:
        """
        Fix Issue 2: AUTO-REPLACE em dashes (defense-in-depth)
        
        Replaces: —, &mdash;, &#8212;, &#x2014; → regular dash ( - )
        System instruction already prevents Gemini from generating these,
        but this validator provides fallback normalization.
        """
        if not v or not isinstance(v, str):
            return v
        
        # Auto-replace em dash patterns with regular dashes
        original = v
        v = re.sub(r'—|&mdash;|&#8212;|&#x2014;', ' - ', v)
        
        if v != original:
            logger.warning(f"⚠️  Em dashes found and auto-replaced in: {original[:80]}...")
        
        return v
    
    @field_validator(
        'section_01_content', 'section_02_content', 'section_03_content',
        'section_04_content', 'section_05_content', 'section_06_content',
        'section_07_content', 'section_08_content', 'section_09_content',
        mode='before'
    )
    @classmethod
    def detect_incomplete_sentences(cls, v: str) -> str:
        """
        Fix Issue E: Detect cutoff sentences
        
        Warns about patterns indicating incomplete sentences:
        - Ends with comma: "Ultimately,"
        - Ends with conjunction: "and", "but", "however"
        - Ends with colon without list following
        """
        if not v or not isinstance(v, str):
            return v
        
        # Strip HTML to check plain text
        text = re.sub(r'<[^>]+>', '', v).strip()
        
        # Check for incomplete sentence patterns
        incomplete_patterns = [
            (r'\w+,\s*$', "ends with comma"),
            (r'\b(and|or|but|however|moreover|furthermore|therefore)\s*$', "ends with conjunction"),
            (r':\s*$', "ends with colon without list"),
        ]
        
        for pattern, desc in incomplete_patterns:
            if re.search(pattern, text):
                logger.warning(f"⚠️  Possible incomplete sentence ({desc}): ...{text[-50:]}")
                # Don't block, just warn (might be intentional)
        
        return v
    
    @field_validator(
        'section_01_content', 'section_02_content', 'section_03_content',
        'section_04_content', 'section_05_content', 'section_06_content',
        'section_07_content', 'section_08_content', 'section_09_content',
        mode='before'
    )
    @classmethod
    def detect_standalone_labels(cls, v: str) -> str:
        """
        Fix Issue 9: Detect standalone label paragraphs
        
        Warns about patterns like:
        <p><strong>GitHub Copilot:</strong></p>
        <p><strong>Amazon Q:</strong> [2][3]</p>
        
        These should be <ul><li> lists instead.
        """
        if not v or not isinstance(v, str):
            return v
        
        # Pattern: <p><strong>Label:</strong> (optional citation/text)</p>
        standalone_label_pattern = r'<p>\s*<strong>[^<]+:</strong>\s*(?:\[\d+\]\s*)*</p>'
        
        matches = re.findall(standalone_label_pattern, v)
        if matches:
            logger.warning(
                f"⚠️  Standalone labels detected ({len(matches)} instances) - "
                f"should be <ul><li> lists instead. Example: {matches[0][:100]}"
            )
            # Don't block - Layer 4 cleanup will remove
        
        return v
    
    @field_validator(
        'section_01_content', 'section_02_content', 'section_03_content',
        'section_04_content', 'section_05_content', 'section_06_content',
        'section_07_content', 'section_08_content', 'section_09_content',
        mode='before'
    )
    @classmethod
    def detect_duplicate_punctuation(cls, v: str) -> str:
        """
        Fix Issue 6: Detect double punctuation (Gemini typo)
        
        Warns about patterns like: ",," or ".." or "??"
        """
        if not v or not isinstance(v, str):
            return v
        
        # Check for duplicate punctuation
        duplicate_punct_pattern = r'([.,;:!?])\1+'
        
        matches = re.findall(duplicate_punct_pattern, v)
        if matches:
            logger.warning(
                f"⚠️  Duplicate punctuation detected ({len(matches)} instances) - "
                f"Layer 4 cleanup will fix. Example: {matches[0]}"
            )
            # Don't block - Layer 4 cleanup will remove
        
        return v

    def get_active_sections(self) -> int:
        """Count non-empty section titles."""
        sections = [
            self.section_01_title,
            self.section_02_title,
            self.section_03_title,
            self.section_04_title,
            self.section_05_title,
            self.section_06_title,
            self.section_07_title,
            self.section_08_title,
            self.section_09_title,
        ]
        return sum(1 for s in sections if s and s.strip())

    def get_active_faqs(self) -> int:
        """Count non-empty FAQ questions."""
        faqs = [
            self.faq_01_question,
            self.faq_02_question,
            self.faq_03_question,
            self.faq_04_question,
            self.faq_05_question,
            self.faq_06_question,
        ]
        return sum(1 for f in faqs if f and f.strip())

    def get_active_paas(self) -> int:
        """Count non-empty PAA questions."""
        paas = [
            self.paa_01_question,
            self.paa_02_question,
            self.paa_03_question,
            self.paa_04_question,
        ]
        return sum(1 for p in paas if p and p.strip())

    def get_active_takeaways(self) -> int:
        """Count non-empty key takeaways."""
        takeaways = [
            self.key_takeaway_01,
            self.key_takeaway_02,
            self.key_takeaway_03,
        ]
        return sum(1 for t in takeaways if t and t.strip())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump()

    def __repr__(self) -> str:
        """String representation."""
        sections = self.get_active_sections()
        faqs = self.get_active_faqs()
        return (
            f"ArticleOutput(headline_len={len(self.Headline)}, "
            f"sections={sections}, faqs={faqs})"
        )
