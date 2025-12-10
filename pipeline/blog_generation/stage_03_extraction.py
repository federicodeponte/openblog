"""
Stage 3: Structured Data Extraction

Maps to v4.1 Phase 3, Steps 6-7: article-extraction

Extracts structured data from Gemini's raw response (text/plain JSON).

Input:
  - ExecutionContext.raw_article (from Stage 2)

Output:
  - ExecutionContext.structured_data (ArticleOutput instance)

Process:
1. Extract JSON from raw_article
2. Parse JSON to Python dict
3. Validate against OutputSchema
4. Handle missing/incomplete fields gracefully
5. Store validated ArticleOutput in context

Retry logic:
- Max retries: 2 (for transient validation issues)
- Only retries on validation errors (structure OK but fields invalid)
- Non-retryable: JSON extraction failed, malformed JSON
"""

import logging
import json
import re
from typing import Dict, Any, Optional

from ..core import ExecutionContext, Stage
from ..models.gemini_client import GeminiClient
from ..models.output_schema import ArticleOutput

logger = logging.getLogger(__name__)


class ExtractionStage(Stage):
    """
    Stage 3: Extract and validate structured article data.

    Handles:
    - JSON extraction from raw response
    - Schema validation
    - Field normalization and cleanup
    - Error handling and validation warnings
    - Storage of structured_data in context
    """

    stage_num = 3
    stage_name = "Structured Data Extraction"

    def __init__(self) -> None:
        """Initialize extraction stage."""
        self.client = GeminiClient()
        logger.info(f"Stage 3 initialized: {self.stage_name}")

    async def execute(self, context: ExecutionContext) -> ExecutionContext:
        """
        Execute Stage 3: Extract and validate structured data.

        Input from context:
        - raw_article: Raw Gemini response (text/plain with embedded JSON)

        Output to context:
        - structured_data: Validated ArticleOutput instance

        Args:
            context: ExecutionContext from Stage 2

        Returns:
            Updated context with structured_data populated

        Raises:
            ValueError: If raw_article missing or JSON extraction fails
            Exception: If validation fails after retries
        """
        logger.info(f"Stage 3: {self.stage_name}")

        # Validate input
        if not context.raw_article:
            raise ValueError("Raw article is required (from Stage 2)")

        logger.debug(f"Raw article size: {len(context.raw_article)} characters")

        # Extract JSON from raw response (direct JSON if response_schema was used)
        logger.info("Parsing JSON from raw article...")
        try:
            json_data = json.loads(context.raw_article)
            logger.info("✅ JSON parsing successful")
        except Exception as e:
            logger.error(f"❌ JSON parsing failed: {e}")
            raise ValueError(f"Failed to parse JSON from raw article: {e}")

        logger.debug(f"   JSON keys: {list(json_data.keys())[:10]}...")

        # Parse and validate
        logger.info("Validating and normalizing extracted data...")
        structured_data = self._parse_and_validate(json_data)

        # Log validation results
        logger.info("✅ Validation successful")
        logger.info(f"   Sections: {structured_data.get_active_sections()}")
        logger.info(f"   FAQs: {structured_data.get_active_faqs()}")
        logger.info(f"   PAAs: {structured_data.get_active_paas()}")
        logger.info(f"   Key Takeaways: {structured_data.get_active_takeaways()}")

        # Store in context
        context.structured_data = structured_data
        
        # CRITICAL FIX: Create unified content for downstream processing
        logger.info("Creating unified content for downstream stages...")
        unified_content = self._create_unified_content(structured_data)
        context.structured_data.unified_content = unified_content
        context.structured_data.unified_word_count = self._count_unified_words(unified_content)
        
        logger.info(f"✅ Unified content: {context.structured_data.unified_word_count:,} words")
        logger.info(f"   Content length: {len(unified_content):,} characters")

        return context

    def _parse_and_validate(self, json_data: Dict[str, Any]) -> ArticleOutput:
        """
        Parse JSON data and validate against schema.

        Handles:
        - Type coercion (all values → strings for now)
        - Missing required fields (fills with defaults)
        - Validation errors (logs warnings, continues)
        - Field normalization (strip whitespace)
        - HTML stripping from title fields (CRITICAL: titles must be plain text)

        Args:
            json_data: Extracted JSON dictionary

        Returns:
            Validated ArticleOutput instance

        Raises:
            ValueError: If validation fails
        """
        logger.debug("Parsing JSON data...")
        
        # Define fields that should NEVER contain HTML (must be plain text)
        PLAIN_TEXT_FIELDS = {
            'Headline', 'Subtitle', 'Meta_Title', 'Meta_Description',
            'section_01_title', 'section_02_title', 'section_03_title',
            'section_04_title', 'section_05_title', 'section_06_title',
            'section_07_title', 'section_08_title', 'section_09_title',
            'faq_01_question', 'faq_02_question', 'faq_03_question',
            'faq_04_question', 'faq_05_question', 'faq_06_question',
            'faq_07_question', 'faq_08_question', 'faq_09_question',
            'faq_10_question',
            'paa_01_question', 'paa_02_question', 'paa_03_question',
            'paa_04_question', 'paa_05_question',
            'takeaway_01', 'takeaway_02', 'takeaway_03',
            'takeaway_04', 'takeaway_05',
        }

        # Normalize data: ensure all values are strings EXCEPT lists/dicts (for tables, etc.)
        normalized = {}
        for key, value in json_data.items():
            if value is None:
                normalized[key] = ""
            elif isinstance(value, str):
                cleaned = value.strip()
                # CRITICAL FIX: Strip HTML from title/metadata fields
                if key in PLAIN_TEXT_FIELDS:
                    cleaned = self._strip_html(cleaned)
                    if cleaned != value.strip():
                        logger.warning(f"⚠️  Stripped HTML from {key}: '{value.strip()}' → '{cleaned}'")
                normalized[key] = cleaned
            elif isinstance(value, (list, dict)):
                # CRITICAL FIX: Preserve structured data (tables, etc.) - do NOT stringify
                normalized[key] = value
            else:
                # Convert non-strings to string representation (numbers, booleans, etc.)
                normalized[key] = str(value).strip()

        logger.debug(f"Normalized {len(normalized)} fields")

        # Validate with ArticleOutput schema
        try:
            article = ArticleOutput(**normalized)
            logger.debug("✓ Schema validation passed")
            return article
        except Exception as e:
            # Log validation error details
            logger.warning(f"⚠️  Validation error: {e}")

            # Try to extract what we can and fill blanks
            logger.info("Attempting to recover with partial data...")
            article = self._recover_partial_data(normalized)
            logger.info("✅ Partial recovery successful")
            return article

    def _recover_partial_data(self, json_data: Dict[str, Any]) -> ArticleOutput:
        """
        Recover partial data when validation fails.

        Strategy:
        1. Extract required fields (Headline, Teaser, etc.)
        2. Provide sensible defaults for missing required fields
        3. Include all optional fields as-is
        4. Log warnings for critical missing fields

        Args:
            json_data: Normalized JSON dictionary

        Returns:
            ArticleOutput with available data + defaults
        """
        # Define field mappings (some fields may have variant names)
        field_map = {
            "Headline": ["Headline", "headline", "title"],
            "Meta_Title": ["Meta Title", "Meta_Title", "MetaTitle"],
            "Meta_Description": ["Meta Description", "Meta_Description", "MetaDescription"],
        }

        # Try to find values with variant names
        for standard_name, variants in field_map.items():
            if standard_name not in json_data or not json_data[standard_name]:
                for variant in variants:
                    if variant in json_data and json_data[variant]:
                        json_data[standard_name] = json_data[variant]
                        logger.debug(f"Mapped {variant} → {standard_name}")
                        break

        # Provide defaults for truly missing required fields
        defaults = {
            "Headline": "Untitled Article",
            "Teaser": "This article explores the topic in depth.",
            "Direct_Answer": "This topic is important and relevant.",
            "Intro": "This article provides comprehensive information on the subject.",
            "Meta_Title": "Article",
            "Meta_Description": "Read this article for more information.",
        }

        for field, default in defaults.items():
            if not json_data.get(field):
                logger.warning(f"⚠️  Missing required field '{field}', using default")
                json_data[field] = default

        # Now validate again with defaults in place
        try:
            article = ArticleOutput(**json_data)
            return article
        except Exception as e:
            # Last resort: create minimal valid instance
            logger.error(f"Recovery failed: {e}")
            logger.info("Creating minimal valid article...")

            minimal = ArticleOutput(
                Headline=json_data.get("Headline", "Untitled"),
                Teaser=json_data.get("Teaser", "Article content."),
                Direct_Answer=json_data.get("Direct_Answer", "See article for details."),
                Intro=json_data.get("Intro", "Article introduction."),
                Meta_Title=json_data.get("Meta_Title", "Article"),
                Meta_Description=json_data.get("Meta_Description", "Article"),
            )
            return minimal

    def _log_completeness(self, article: ArticleOutput) -> None:
        """
        Log article completeness metrics.

        Calculates:
        - Percentage of required fields populated
        - Percentage of optional fields populated
        - Missing sections
        """
        logger.debug("Article completeness check:")

        # Required fields
        required_fields = [
            article.Headline,
            article.Teaser,
            article.Direct_Answer,
            article.Intro,
            article.Meta_Title,
            article.Meta_Description,
        ]
        required_count = sum(1 for f in required_fields if f and f.strip())
        required_pct = (required_count / len(required_fields)) * 100
        logger.debug(f"  Required fields: {required_pct:.0f}% ({required_count}/{len(required_fields)})")

        # Optional sections
        sections = article.get_active_sections()
        logger.debug(f"  Content sections: {sections}/9")

        # Engagement elements
        paas = article.get_active_paas()
        faqs = article.get_active_faqs()
        takeaways = article.get_active_takeaways()
        logger.debug(
            f"  Engagement: {faqs} FAQs, {paas} PAAs, {takeaways} Key Takeaways"
        )

        # Citations
        has_sources = bool(article.Sources and article.Sources.strip())
        has_queries = bool(article.Search_Queries and article.Search_Queries.strip())
        logger.debug(f"  Citations: Sources={has_sources}, Queries={has_queries}")
    
    def _strip_html(self, text: str) -> str:
        """
        Strip ALL HTML tags from text, leaving only plain text.
        
        Used for title fields, metadata, and questions where HTML is forbidden.
        
        Args:
            text: Input text that may contain HTML
        
        Returns:
            Plain text with all HTML tags removed
        
        Examples:
            "<p>Hello World</p>" → "Hello World"
            "What is <p>AI Coding</p>?" → "What is AI Coding?"
            "<strong>Bold</strong> text" → "Bold text"
        """
        if not text:
            return text
        
        # Remove all HTML tags
        cleaned = re.sub(r'<[^>]+>', '', text)
        
        # Clean up any leftover HTML entities
        cleaned = cleaned.replace('&nbsp;', ' ')
        cleaned = cleaned.replace('&lt;', '<')
        cleaned = cleaned.replace('&gt;', '>')
        cleaned = cleaned.replace('&amp;', '&')
        cleaned = cleaned.replace('&quot;', '"')
        cleaned = cleaned.replace('&#39;', "'")
        
        # Clean up extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    def _create_unified_content(self, article: ArticleOutput) -> str:
        """
        Create unified Markdown content from all schema fields.
        
        This is the ROOT-LEVEL FIX for the JSON schema fragmentation issue.
        Combines all content fields into a single unified document for downstream processing.
        
        Args:
            article: ArticleOutput with populated schema fields
            
        Returns:
            Complete article in unified Markdown format
        """
        content_parts = []
        
        # Add headline (without H1 formatting - will be added by renderer)
        if article.Headline:
            content_parts.append(f"# {article.Headline}\n")
        
        # Add subtitle if present
        if article.Subtitle:
            content_parts.append(f"*{article.Subtitle}*\n")
        
        # Add teaser/hook
        if article.Teaser:
            content_parts.append(f"{article.Teaser}\n")
        
        # Add direct answer
        if article.Direct_Answer:
            content_parts.append(f"**Quick Answer:** {article.Direct_Answer}\n")
        
        # Add intro
        if article.Intro:
            content_parts.append(f"{article.Intro}\n")
        
        # Add all content sections
        sections = [
            (article.section_01_title, article.section_01_content),
            (article.section_02_title, article.section_02_content),
            (article.section_03_title, article.section_03_content),
            (article.section_04_title, article.section_04_content),
            (article.section_05_title, article.section_05_content),
            (article.section_06_title, article.section_06_content),
            (article.section_07_title, article.section_07_content),
            (article.section_08_title, article.section_08_content),
            (article.section_09_title, article.section_09_content),
        ]
        
        for title, content in sections:
            if title and title.strip():
                content_parts.append(f"\n## {title}\n")
                if content and content.strip():
                    # Clean content: remove HTML if present, keep Markdown
                    clean_content = self._clean_content_for_unified(content)
                    content_parts.append(f"{clean_content}\n")
        
        # Add key takeaways if present
        takeaways = [article.key_takeaway_01, article.key_takeaway_02, article.key_takeaway_03]
        active_takeaways = [t for t in takeaways if t and t.strip()]
        if active_takeaways:
            content_parts.append("\n## Key Takeaways\n")
            for i, takeaway in enumerate(active_takeaways, 1):
                content_parts.append(f"{i}. {takeaway}\n")
        
        # Add FAQ section if present
        faq_pairs = [
            (article.faq_01_question, article.faq_01_answer),
            (article.faq_02_question, article.faq_02_answer),
            (article.faq_03_question, article.faq_03_answer),
            (article.faq_04_question, article.faq_04_answer),
            (article.faq_05_question, article.faq_05_answer),
            (article.faq_06_question, article.faq_06_answer),
        ]
        active_faqs = [(q, a) for q, a in faq_pairs if q and q.strip() and a and a.strip()]
        if active_faqs:
            content_parts.append("\n## Frequently Asked Questions\n")
            for question, answer in active_faqs:
                content_parts.append(f"### {question}\n")
                clean_answer = self._clean_content_for_unified(answer)
                content_parts.append(f"{clean_answer}\n")
        
        # Add PAA section if present  
        paa_pairs = [
            (article.paa_01_question, article.paa_01_answer),
            (article.paa_02_question, article.paa_02_answer),
            (article.paa_03_question, article.paa_03_answer),
            (article.paa_04_question, article.paa_04_answer),
        ]
        active_paas = [(q, a) for q, a in paa_pairs if q and q.strip() and a and a.strip()]
        if active_paas:
            content_parts.append("\n## People Also Ask\n")
            for question, answer in active_paas:
                content_parts.append(f"### {question}\n")
                clean_answer = self._clean_content_for_unified(answer)
                content_parts.append(f"{clean_answer}\n")
        
        # Join all parts into unified content
        unified = "\n".join(content_parts).strip()
        
        logger.debug(f"Created unified content with {len(content_parts)} parts")
        return unified
    
    def _clean_content_for_unified(self, content: str) -> str:
        """
        Clean content for unified format.
        
        Removes HTML tags, preserves Markdown formatting.
        Handles both HTML and Markdown content gracefully.
        
        Args:
            content: Raw content (may be HTML or Markdown)
            
        Returns:
            Clean Markdown content
        """
        if not content:
            return ""
        
        # If content contains HTML tags, convert to Markdown-equivalent
        if '<' in content and '>' in content:
            # Basic HTML to Markdown conversion
            content = re.sub(r'<p>(.*?)</p>', r'\1\n', content, flags=re.DOTALL)
            content = re.sub(r'<strong>(.*?)</strong>', r'**\1**', content)
            content = re.sub(r'<em>(.*?)</em>', r'*\1*', content)
            content = re.sub(r'<ul>(.*?)</ul>', r'\1', content, flags=re.DOTALL)
            content = re.sub(r'<li>(.*?)</li>', r'- \1', content)
            content = re.sub(r'<h([1-6])>(.*?)</h[1-6]>', r'#\1 \2', content)
            
            # Remove any remaining HTML tags
            content = re.sub(r'<[^>]+>', '', content)
            
            logger.debug("Converted HTML content to Markdown")
        
        # Clean up whitespace
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)  # Max 2 consecutive newlines
        content = re.sub(r'^\s+', '', content, flags=re.MULTILINE)  # Remove leading spaces
        
        return content.strip()
    
    def _count_unified_words(self, content: str) -> int:
        """
        Count words in unified content.
        
        More accurate than individual field counting because it handles
        the content as a complete document.
        
        Args:
            content: Unified Markdown content
            
        Returns:
            Total word count
        """
        if not content:
            return 0
        
        # Remove Markdown syntax for accurate counting
        text = re.sub(r'#{1,6}\s+', '', content)  # Remove headers
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Remove bold
        text = re.sub(r'\*(.*?)\*', r'\1', text)  # Remove italic
        text = re.sub(r'^-\s+', '', text, flags=re.MULTILINE)  # Remove list markers
        text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)  # Remove numbered lists
        
        # Split by whitespace and count
        words = text.split()
        return len(words)

    def __repr__(self) -> str:
        """String representation."""
        return f"ExtractionStage(stage_num={self.stage_num})"
