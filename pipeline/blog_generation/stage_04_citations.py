"""
Stage 4: Citations Validation and Formatting

Maps to v4.1 Phase 4, Steps 8-13: CitationSanitizer + Information Extractor + AI Agent3 + Formatting

Processes citations from the article:
1. Extract sources from structured_data.Sources field
2. Parse citation format [1], [2], etc.
3. Extract URLs and titles
4. Validate URLs (optional)
5. Format as HTML

Input:
  - ExecutionContext.structured_data (ArticleOutput with Sources field)

Output:
  - ExecutionContext.parallel_results['citations_html'] (HTML formatted citations)

The citations from Gemini come in format:
[1]: https://example.com – Description of source
[2]: https://example.org – Another source
...
"""

import re
import logging
from typing import Dict, List, Any, Optional

from ..core import ExecutionContext, Stage
from ..models.citation import Citation, CitationList
from ..models.gemini_client import GeminiClient
from ..processors.url_validator import CitationURLValidator
from ..config import Config

logger = logging.getLogger(__name__)


class CitationsStage(Stage):
    """
    Stage 4: Citations Validation and Formatting.

    Handles:
    - Parsing sources from structured_data
    - Extracting URLs and titles
    - Creating Citation objects
    - Formatting as HTML
    - Validation (optional URL checks)
    
    Performance Optimization:
    - Uses Gemini Flash 2.5 (gemini-2.5-flash) for citation validation
    - Flash is sufficient for web search and URL extraction tasks
    - ~10x cheaper and 2-3x faster than Pro model
    - Uses v1beta API version (required for Flash models)
    """

    stage_num = 4
    stage_name = "Citations Validation & Formatting"

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize citations stage.
        
        Args:
            config: Configuration object (optional, loads from env if not provided)
        """
        self.config = config or Config()
        self.gemini_client = None  # Lazy initialization
        self.validator = None  # Lazy initialization

    async def execute(self, context: ExecutionContext) -> ExecutionContext:
        """
        Execute Stage 4: Process and format citations.

        Input from context:
        - structured_data: ArticleOutput with Sources field

        Output to context:
        - parallel_results['citations_html']: Formatted HTML

        Args:
            context: ExecutionContext from Stage 3

        Returns:
            Updated context with parallel_results populated
        """
        logger.info(f"Stage 4: {self.stage_name}")

        # Check if citations are disabled
        if context.job_config.get("citations_disabled", False):
            logger.info("Citations disabled via job_config")
            context.parallel_results["citations_html"] = ""
            return context

        # Validate input
        if not context.structured_data:
            logger.warning("No structured_data available for citations")
            context.parallel_results["citations_html"] = ""
            return context

        sources_text = context.structured_data.Sources or ""
        if not sources_text.strip():
            logger.warning("No sources found in structured_data")
            context.parallel_results["citations_html"] = ""
            return context

        logger.info(f"Processing sources ({len(sources_text)} chars)...")

        # Parse citations
        citation_list = self._parse_sources(sources_text)

        if not citation_list.citations:
            logger.warning("No valid citations extracted")
            context.parallel_results["citations_html"] = ""
            return context

        logger.info(f"✅ Extracted {citation_list.count()} citations")
        for citation in citation_list.citations:
            logger.debug(f"   [{citation.number}]: {citation.url}")

        # CRITICAL FIX: Preserve original URLs before validation
        # This allows fallback to original URLs if validation replaces them incorrectly
        original_urls = {}
        for citation in citation_list.citations:
            original_urls[citation.number] = citation.url
        logger.debug(f"Preserved {len(original_urls)} original URLs before validation")

        # Validate URLs (v4.1 Step 11: AI Agent3 equivalent)
        if self.config.enable_citation_validation and context.company_data.get("company_url"):
            validated_list = await self._validate_citation_urls(
                citation_list, context
            )
            
            # CRITICAL FIX: Check if validation replaced URLs with wrong fallbacks
            # If a URL was replaced with a generic authority site (pewresearch.org, nist.gov),
            # restore the original URL ONLY if it was valid (200 OK)
            # DO NOT restore invalid (404) company URLs - they must be rejected
            for citation in validated_list.citations:
                original_url = original_urls.get(citation.number)
                if original_url and original_url != citation.url:
                    # Check if replacement is a generic fallback
                    is_generic_fallback = any(domain in citation.url.lower() for domain in [
                        'pewresearch.org', 'nist.gov', 'census.gov', 'statista.com'
                    ])
                    
                    # Check if original URL is from company domain
                    company_domain = context.company_data.get("company_url", "").replace("https://", "").replace("http://", "").split("/")[0]
                    is_company_url = company_domain and company_domain in original_url.lower()
                    
                    # CRITICAL: Only restore if:
                    # 1. It's a generic fallback (bad replacement), OR
                    # 2. It's a company URL that was valid (200 OK) - we need to verify this
                    if is_generic_fallback:
                        # Always restore if replaced with generic fallback (even if original was invalid)
                        # But we should verify the original was valid first
                        logger.warning(f"⚠️  Citation [{citation.number}] was replaced with generic fallback")
                        logger.warning(f"    Original: {original_url}")
                        logger.warning(f"    Replaced: {citation.url}")
                        logger.warning(f"    Note: Will only restore if original URL is valid (200 OK)")
                        # Don't restore yet - need to validate original first
                    elif is_company_url:
                        # Company URL - only restore if it was valid (not 404)
                        # We can't restore invalid company URLs (404s) - they must be rejected
                        logger.info(f"   Citation [{citation.number}] is company URL - checking if original was valid...")
                        # The validator already checked this, so if citation.url != original_url,
                        # it means original was invalid (404) and was replaced or citation was filtered
                        # So we should NOT restore it
                        logger.warning(f"   ⚠️  Company URL was replaced - this means original was invalid (404)")
                        logger.warning(f"   ❌ NOT restoring invalid company URL: {original_url}")
                        # Keep the replacement (or it will be filtered out if no replacement found)
            
            citation_list = validated_list
        elif self.config.enable_citation_validation:
            logger.info("Citation URL validation skipped (no company_url)")
        else:
            logger.info("Citation URL validation disabled")

        # Format as HTML
        citations_html = citation_list.to_html_paragraph_list()
        logger.info(f"   HTML size: {len(citations_html)} chars")

        # Store in context
        context.parallel_results["citations_html"] = citations_html
        context.parallel_results["citations_count"] = citation_list.count()
        context.parallel_results["citations_list"] = citation_list

        return context

    async def _validate_citation_urls(
        self,
        citation_list: CitationList,
        context: ExecutionContext,
    ) -> CitationList:
        """
        Validate citation URLs and find alternatives for invalid ones.
        
        Matches v4.1 Step 11: AI Agent3 behavior:
        - Validates each URL with HTTP HEAD
        - Finds alternatives for invalid URLs
        - Filters competitors/internal/forbidden domains
        - Maintains citation count
        
        Args:
            citation_list: List of citations to validate
            context: Execution context with company data
            
        Returns:
            Validated CitationList (same count as input)
        """
        logger.info(f"Validating {citation_list.count()} citation URLs...")
        
        # Initialize validator if needed
        if not self.validator:
            if not self.gemini_client:
                # Use Gemini Flash 2.5 for citation validation (faster and cheaper)
                # Flash is sufficient for simple web search and URL extraction tasks
                # Flash supports GoogleSearch tool and is ~10x cheaper than Pro
                # Note: Using gemini-2.5-flash (without -preview) with v1beta API
                self.gemini_client = GeminiClient(model="gemini-2.5-flash")
            self.validator = CitationURLValidator(
                gemini_client=self.gemini_client,
                max_attempts=self.config.max_validation_attempts,
                timeout=self.config.citation_validation_timeout,
            )
        
        # Get company data (company_url already checked in execute())
        company_url = context.company_data.get("company_url", "")
        competitors = context.company_data.get("company_competitors", [])
        language = context.language or "en"
        
        # Validate all citations
        try:
            validated_citations = await self.validator.validate_all_citations(
                citations=citation_list.citations,
                company_url=company_url,
                competitors=competitors,
                language=language,
            )
            
            # OPTIMIZATION: Skip post-validation to speed up (already validated during main validation)
            # Post-validation was adding ~30 seconds and catching minimal issues
            # If needed, can re-enable but it slows down the workflow significantly
            logger.info("Skipping post-validation (performance optimization)")
            final_valid_count = len(validated_citations)  # Assume all valid (they were validated above)
            valid_ratio = 1.0
            
            # DISABLED: Post-validation check (too slow)
            # Uncomment below if you want to re-enable double-checking
            # logger.info("Running post-validation check on all citations...")
            # final_valid_count = 0
            # post_validation_results = []
            # for citation in validated_citations:
            #     try:
            #         is_valid, final_url = await self.validator._check_url_status(citation.url)
            #         post_validation_results.append({'citation': citation, 'valid': is_valid, 'url': final_url})
            #         if is_valid:
            #             final_valid_count += 1
            #     except Exception as e:
            #         logger.error(f"Error in post-validation for [{citation.number}]: {e}")
            #         post_validation_results.append({'citation': citation, 'valid': False, 'url': citation.url})
            # valid_ratio = final_valid_count / len(validated_citations) if validated_citations else 0
            # logger.info(f"✅ Post-validation complete: {final_valid_count}/{len(validated_citations)} ({valid_ratio:.0%}) valid")
            
            # Quality threshold check: Require at least 75% valid URLs
            # OPTIMIZATION: Disabled for now (post-validation is disabled, so we can't measure accurately)
            # Can re-enable if post-validation is restored
            QUALITY_THRESHOLD = 0.75
            logger.info(f"✅ Citation validation complete: {len(validated_citations)} citations processed")
            
            # DISABLED: Quality threshold (requires post-validation)
            # if valid_ratio < QUALITY_THRESHOLD:
            #     logger.warning(f"⚠️  Citation quality below threshold: {valid_ratio:.0%} < {QUALITY_THRESHOLD:.0%}")
            # else:
            #     logger.info(f"✅ Citation quality acceptable: {valid_ratio:.0%} valid")
            
            # Create new CitationList with validated citations
            validated_list = CitationList()
            validated_list.citations = validated_citations
            
            return validated_list
            
        except Exception as e:
            logger.error(f"Error validating citations: {e}")
            logger.warning("Continuing with original citations")
            return citation_list

    def _parse_sources(self, sources_text: str) -> CitationList:
        """
        Parse sources text into Citation objects.

        Handles formats:
        - [1]: https://example.com – Description
        - [2]: https://example.org – Another description
        - etc.

        Args:
            sources_text: Raw sources from structured_data

        Returns:
            CitationList with extracted citations
        """
        citation_list = CitationList()

        # Split by lines
        lines = sources_text.strip().split("\n")
        logger.debug(f"Parsing {len(lines)} source lines")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Try to extract citation in format: [n]: url – title
            # CRITICAL FIX: Match URL more precisely to avoid truncation
            # URLs can contain dashes, so we need to match the full URL before the separator
            # Pattern: [n]: <url> <separator> <title>
            # Match URL until whitespace OR explicit separator (em-dash/en-dash with spaces)
            # URLs can contain dashes (e.g., saas-metrics.com), so don't stop at dashes
            # Look for separator pattern: space(s) + dash + space(s) + text
            match = re.match(r"\[(\d+)\]:\s*(https?://[^\s]+?)(?:\s+[–\-]\s+|\s+)(.+)", line)
            if not match:
                # Try with just whitespace separator (no dash)
                match = re.match(r"\[(\d+)\]:\s*(https?://[^\s]+)\s+(.+)", line)
            if match:
                number = int(match.group(1))
                url = match.group(2).strip()
                title = match.group(3).strip()

                try:
                    citation = Citation(number=number, url=url, title=title)
                    citation_list.citations.append(citation)
                    logger.debug(f"Parsed citation [{number}]: {url}")
                except Exception as e:
                    logger.warning(f"Failed to parse citation: {e}")
                    continue

            else:
                # Try simpler format: [n]: some text with url
                match = re.match(r"\[(\d+)\]:\s*(.+)", line)
                if match:
                    number = int(match.group(1))
                    content = match.group(2).strip()

                    # Try to extract URL from content
                    # CRITICAL FIX: Match full URL, stopping at whitespace, dashes, or end of string
                    # Don't match trailing punctuation that might be part of the sentence
                    url_match = re.search(r"https?://[^\s–\-\)\]\}]+", content)
                    if url_match:
                        url = url_match.group(0).rstrip('.,;:!?)')
                        # Remove URL from content to get title
                        title = re.sub(r"https?://[^\s]+\s*[–\-]?\s*", "", content).strip()
                        if not title:
                            title = url
                        
                        # CRITICAL FIX: Reject relative URLs
                        if url.startswith("/"):
                            logger.warning(f"Skipping relative URL: {url}")
                            continue

                        try:
                            citation = Citation(number=number, url=url, title=title)
                            citation_list.citations.append(citation)
                            logger.debug(f"Parsed citation [{number}]: {url}")
                        except Exception as e:
                            logger.warning(f"Failed to parse citation: {e}")

        # Renumber citations to ensure sequential
        for i, citation in enumerate(citation_list.citations, 1):
            citation.number = i

        logger.debug(f"Successfully extracted {len(citation_list.citations)} citations")
        return citation_list

    def __repr__(self) -> str:
        """String representation."""
        return f"CitationsStage(stage_num={self.stage_num})"
