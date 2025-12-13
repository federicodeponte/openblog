"""
Stage 10: Cleanup & Validation

Maps to v4.1 Phase 9, Steps 29-33 + cleanup

Orchestrates 6 sequential cleanup sub-steps:
1. prepare_variable_names-and-clean (Step 29) - HTML cleaning + section combining
2. output_sanitizer (Step 30) - Regex-based cleanup
3. normalise-output2 (Step 31) - Normalization
4. Merge (Step 32) - Combine parallel results
5. CitationSanitizer2 (Step 32b) - Final citation cleanup
6. merge-outputs (Step 33) - Flatten to ValidatedArticle + quality checks

Input:
  - ExecutionContext.structured_data (sequential data)
  - ExecutionContext.parallel_results (from stages 4-9)
  - ExecutionContext.job_config (for quality checks)

Output:
  - ExecutionContext.validated_article (merged, cleaned article)
  - ExecutionContext.quality_report (validation + metrics)
"""

import logging
import re
from typing import Dict, Any, Tuple, Optional, List

from ..core import ExecutionContext, Stage
from ..processors.cleanup import HTMLCleaner, SectionCombiner, DataMerger
from ..processors.citation_sanitizer import CitationSanitizer2
from ..processors.citation_linker import CitationLinker
from ..utils.humanizer import humanize_content, detect_ai_patterns, get_ai_score
from ..utils.language_validator import validate_article_language
from ..processors.quality_checker import QualityChecker
# NOTE: SimHash-based content_hasher is DEPRECATED
# Semantic deduplication now handled by Gemini embeddings in Edge Functions
# See: supabase/functions/s5-generate-blogs/index.ts
from ..models.output_schema import ArticleOutput
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class CleanupStage(Stage):
    """
    Stage 10: Cleanup & Validation.

    Handles:
    - HTML cleaning and normalization
    - Section combining
    - Output sanitization
    - Data merging from all parallel branches
    - Final citation cleanup
    - Quality validation and metrics
    """

    stage_num = 10
    stage_name = "Cleanup & Validation"

    async def execute(self, context: ExecutionContext) -> ExecutionContext:
        """
        Execute Stage 10: Cleanup, merge, and validate article.

        Input from context:
        - structured_data: Article with 30+ fields
        - parallel_results: Results from stages 4-9

        Output to context:
        - validated_article: Cleaned, merged article
        - quality_report: Validation results and metrics

        Args:
            context: ExecutionContext from stages 4-9

        Returns:
            Updated context with validated_article and quality_report
        """
        logger.info(f"Stage 10: {self.stage_name}")

        # Validate inputs
        if not context.structured_data:
            logger.error("No structured_data for cleanup")
            context.validated_article = {}
            context.quality_report = {"critical_issues": ["No structured data"], "passed": False}
            return context

        # OPTIMIZED: Some operations can run in parallel
        import asyncio
        
        # Step 1: Clean HTML and combine sections
        logger.debug("Step 29: Preparing and cleaning HTML...")
        cleaned_article = self._prepare_and_clean(context.structured_data)

        # Step 2: Sanitize output
        logger.debug("Step 30: Sanitizing output...")
        sanitized_article = self._sanitize_output(cleaned_article)

        # Step 3: Normalize
        logger.debug("Step 31: Normalizing...")
        normalized_article = self._normalize_output(sanitized_article)

        # Step 4: Merge parallel results
        logger.debug("Step 32: Merging parallel results...")
        merged_article = self._merge_parallel_results(normalized_article, context.parallel_results)

        # Step 4a: Enforce AEO requirements (post-processing corrections)
        # Pass language for language-aware phrase injection
        language = context.job_config.get("language", "en")
        logger.debug(f"Step 32a: Enforcing AEO requirements (language={language})...")
        merged_article = self._enforce_aeo_requirements(merged_article, context.job_config, language)

        # Step 4a.5: Humanize content (remove AI-typical phrases)
        logger.debug("Step 32a.5: Humanizing content...")
        merged_article = self._humanize_article(merged_article, language)

        # Step 4a.6: Language validation (for non-English content)
        if language != "en":
            logger.debug(f"Step 32a.6: Language validation (target={language})...")
            is_valid, lang_metrics = validate_article_language(merged_article, language)
            context.language_validation = lang_metrics
            
            if not is_valid:
                logger.warning(f"Language validation failed: {lang_metrics.get('reason')}")
                context.needs_regeneration = True
                context.regeneration_reason = "language_validation_failed"
            else:
                contamination = lang_metrics.get('english_contamination_score', 0)
                logger.info(f"✅ Language validation passed (contamination: {contamination:.1f}%)")

        # Step 4b: Final citation cleanup (can run in parallel with quality checks prep)
        logger.debug("Step 32b: Citation sanitization (CitationSanitizer2)...")
        sanitized_citations = CitationSanitizer2.sanitize(merged_article)

        # Step 4c: Link citations in content (convert [1], [2] to clickable links)
        logger.debug("Step 32c: Linking citations in content...")
        citations_list = context.parallel_results.get("citations_list")
        if citations_list and sanitized_citations:
            # Extract citations for linking
            citations_for_linking = []
            citation_map = {}  # Build citation_map for HTML rendering
            if hasattr(citations_list, 'citations'):
                for citation in citations_list.citations:
                    citation_num = citation.number if hasattr(citation, 'number') else citation.get('number')
                    citation_url = citation.url if hasattr(citation, 'url') else citation.get('url')
                    citation_title = citation.title if hasattr(citation, 'title') else citation.get('title', '')
                    
                    citations_for_linking.append({
                        'number': citation_num,
                        'url': citation_url,
                        'title': citation_title,
                    })
                    
                    # Build citation_map: number -> URL (for HTML rendering)
                    # CRITICAL FIX: Only add valid URLs to citation_map (format + HTTP 200 check)
                    if citation_num and citation_url:
                        # Validate URL format before adding to map
                        if not citation_url.startswith(("http://", "https://")):
                            logger.warning(f"⚠️  Rejecting relative/invalid URL for citation [{citation_num}]: {citation_url}")
                            continue
                        
                        # Check for malformed URLs (missing TLD)
                        from urllib.parse import urlparse
                        try:
                            parsed = urlparse(citation_url)
                            domain = parsed.netloc.lower()
                            if "." not in domain and domain not in ['localhost']:
                                # Check if it's an IP address
                                try:
                                    import ipaddress
                                    ipaddress.ip_address(domain)
                                except ValueError:
                                    logger.warning(f"⚠️  Rejecting URL with missing TLD for citation [{citation_num}]: {citation_url}")
                                    continue
                        except Exception as e:
                            logger.warning(f"⚠️  Error validating URL for citation [{citation_num}]: {e}")
                            continue
                        
                        # CRITICAL FIX: Final HTTP validation - check if URL actually exists (200 OK)
                        # This catches 404s that might have slipped through earlier validation
                        # Note: This is a final safety check - URLs should already be validated in stage_04
                        try:
                            import httpx
                            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                                response = await client.head(citation_url)
                                if response.status_code != 200:
                                    logger.warning(f"⚠️  Rejecting invalid URL (HTTP {response.status_code}) for citation [{citation_num}]: {citation_url}")
                                    continue
                                
                                # Check for soft 404s (200 OK but redirects to error page)
                                final_url = str(response.url)
                                error_indicators = ['/404', '/not-found', '/error', 'notfound', 'page-not-found']
                                if any(indicator in final_url.lower() for indicator in error_indicators):
                                    logger.warning(f"⚠️  Rejecting URL (error page redirect) for citation [{citation_num}]: {citation_url}")
                                    continue
                        except httpx.TimeoutException:
                            logger.warning(f"⚠️  URL validation timeout for citation [{citation_num}]: {citation_url}")
                            # On timeout, reject to be safe
                            continue
                        except Exception as e:
                            logger.warning(f"⚠️  Error checking URL status for citation [{citation_num}]: {e}")
                            # On error, reject the URL to be safe
                            continue
                        
                        citation_map[citation_num] = citation_url
                        logger.debug(f"Citation map: [{citation_num}] → {citation_url}")
            
            if citations_for_linking:
                sanitized_citations = CitationLinker.link_citations_in_content(
                    sanitized_citations,
                    citations_for_linking
                )
                logger.info(f"✅ Linked {len(citations_for_linking)} citations in content")
            
            # CRITICAL FIX: Set citation_map in article dict for HTML rendering
            # This allows _linkify_citations() to convert #source-N anchors to real URLs
            if citation_map:
                sanitized_citations['_citation_map'] = citation_map
                logger.info(f"✅ Set citation_map with {len(citation_map)} entries for HTML rendering")
            else:
                logger.warning(f"⚠️  No citation_map created (citations_list might be empty)")

        # Step 5: Quality checks and flattening
        logger.debug("Step 33: Quality checks and validation...")
        validated_article, quality_report, article_output = self._validate_and_flatten(
            sanitized_citations, context.job_config, context
        )
        
        # Store article_output in context for Stage 11
        context.article_output = article_output

        # Store results
        context.validated_article = validated_article
        context.quality_report = quality_report

        # Log results
        passed = quality_report.get("passed", False)
        aeo_score = quality_report.get("metrics", {}).get("aeo_score", 0)
        logger.info(
            f"✅ Validation complete: AEO={aeo_score}/100, Status={'PASS' if passed else 'FAIL'}"
        )

        if not passed:
            critical = quality_report.get("critical_issues", [])
            for issue in critical[:3]:  # Log first 3 issues
                logger.warning(f"  {issue}")

        return context

    def _prepare_and_clean(self, structured_data: Any) -> Dict[str, Any]:
        """
        Step 29: Prepare variables and clean HTML.

        Args:
            structured_data: ArticleOutput

        Returns:
            Cleaned article dictionary
        """
        # Convert to dict if needed
        if hasattr(structured_data, "model_dump"):
            article = structured_data.model_dump()
        else:
            article = dict(structured_data)

        # CRITICAL FIX: Define fields that should NEVER be HTML processed (plain text only)
        PLAIN_TEXT_FIELDS = {
            'Headline', 'Subtitle', 'Meta_Title', 'Meta_Description',
            'section_01_title', 'section_02_title', 'section_03_title',
            'section_04_title', 'section_05_title', 'section_06_title',
            'section_07_title', 'section_08_title', 'section_09_title',
        }
        
        # Clean each HTML field (but skip plain text fields to prevent entity encoding)
        for key in article:
            if isinstance(article[key], str):
                # Skip HTML processing for plain text fields (prevents & from becoming &amp;)
                if key in PLAIN_TEXT_FIELDS:
                    # Only strip HTML tags, don't process through HTMLCleaner
                    import re
                    article[key] = re.sub(r'<[^>]+>', '', article[key]).strip()
                elif "<" in article[key] or "**" in article[key]:
                    # Only process fields that actually contain HTML
                    article[key] = HTMLCleaner.clean_html(article[key])

        # Combine sections into single content field
        combined_content = SectionCombiner.combine_sections(structured_data)
        article["content"] = combined_content

        logger.debug(f"HTML cleaned and sections combined")
        return article

    def _sanitize_output(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 30: Sanitize output (regex-based cleanup).

        Args:
            article: Article dictionary

        Returns:
            Sanitized article
        """
        # Sanitize all string fields
        for key in article:
            if isinstance(article[key], str):
                article[key] = HTMLCleaner.sanitize(article[key])

        logger.debug(f"Output sanitized")
        return article

    def _normalize_output(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 31: Normalize output.

        Args:
            article: Article dictionary

        Returns:
            Normalized article
        """
        # Normalize all string fields
        for key in article:
            if isinstance(article[key], str):
                article[key] = HTMLCleaner.normalize(article[key])

        logger.debug(f"Output normalized")
        return article

    def _merge_parallel_results(
        self, article: Dict[str, Any], parallel_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Step 32: Merge parallel results.

        Args:
            article: Current article
            parallel_results: Results from stages 4-9

        Returns:
            Merged article
        """
        # Start with article dictionary
        merged = article.copy() if isinstance(article, dict) else dict(article)

        # Add metadata if present
        # FIX: Handle both Pydantic models and dicts (ArticleMetadata is Pydantic)
        if "metadata" in parallel_results:
            metadata = parallel_results["metadata"]
            if hasattr(metadata, 'model_dump'):
                # Pydantic v2 model - convert to dict
                merged.update(metadata.model_dump())
            elif hasattr(metadata, 'dict'):
                # Pydantic v1 model - convert to dict
                merged.update(metadata.dict())
            elif isinstance(metadata, dict):
                merged.update(metadata)

        # Add image
        if "image_url" in parallel_results:
            merged["image_url"] = parallel_results["image_url"]
        if "image_alt_text" in parallel_results:
            merged["image_alt_text"] = parallel_results["image_alt_text"]
        if "mid_image_url" in parallel_results:
            merged["mid_image_url"] = parallel_results["mid_image_url"]
        if "mid_image_alt" in parallel_results:
            merged["mid_image_alt"] = parallel_results["mid_image_alt"]
        if "bottom_image_url" in parallel_results:
            merged["bottom_image_url"] = parallel_results["bottom_image_url"]
        if "bottom_image_alt" in parallel_results:
            merged["bottom_image_alt"] = parallel_results["bottom_image_alt"]

        # Add ToC
        if "toc_dict" in parallel_results:
            merged["toc"] = parallel_results["toc_dict"]
            logger.info(f"✅ ToC merged: {len(merged['toc'])} entries")
        else:
            logger.warning("⚠️  No toc_dict in parallel_results - TOC will be empty")

        # Add FAQ items
        if "faq_items" in parallel_results:
            faq_list = parallel_results["faq_items"]
            if hasattr(faq_list, "to_dict_list"):
                merged["faq_items"] = faq_list.to_dict_list()

        # Add PAA items
        if "paa_items" in parallel_results:
            paa_list = parallel_results["paa_items"]
            if hasattr(paa_list, "to_dict_list"):
                merged["paa_items"] = paa_list.to_dict_list()

        # Add HTML sections
        if "citations_html" in parallel_results:
            merged["citations_html"] = parallel_results["citations_html"]
        if "internal_links_html" in parallel_results:
            merged["internal_links_html"] = parallel_results["internal_links_html"]
        
        # Add validated citation maps for in-body linking
        # These ensure only validated URLs are used for natural language linking
        if "validated_citation_map" in parallel_results:
            merged["validated_citation_map"] = parallel_results["validated_citation_map"]
        if "validated_source_name_map" in parallel_results:
            merged["validated_source_name_map"] = parallel_results["validated_source_name_map"]
        
        # Add internal links list for in-body linking to related blog posts
        if "internal_links_list" in parallel_results:
            merged["internal_links_list"] = parallel_results["internal_links_list"]

        logger.info(
            f"Merged {len(parallel_results)} parallel results into article "
            f"({len(merged)} fields)"
        )
        return merged

    def _validate_and_flatten(
        self, article: Dict[str, Any], job_config: Dict[str, Any], context: ExecutionContext
    ) -> Tuple[Dict[str, Any], Dict[str, Any], Optional[ArticleOutput]]:
        """
        Step 33: Quality checks, flatten, and validate.

        Args:
            article: Merged article
            job_config: Job configuration
            context: ExecutionContext for accessing input_data

        Returns:
            Tuple of (validated_article, quality_report, article_output)
        """
        # Try to convert article dict to ArticleOutput for comprehensive AEO scoring
        article_output = None
        try:
            # Use model_validate for robustness (handles extra fields gracefully)
            article_output = ArticleOutput.model_validate(article)
            logger.debug("Successfully converted article to ArticleOutput")
        except (ValidationError, TypeError, ValueError) as e:
            logger.warning(f"Could not convert article to ArticleOutput: {e}. Using dict fallback.")
            article_output = None

        # Run quality checks with ArticleOutput if available
        # Build input_data for E-E-A-T scoring (author info from company_data)
        input_data = None
        if context.company_data:
            # Extract author info with fallbacks for E-E-A-T scoring
            company_name = context.company_data.get("name") or job_config.get("company_name", "")
            company_url = job_config.get("company_url", "")
            
            # Use explicit author data or create fallbacks from company info
            author_name = context.company_data.get("author_name") or f"{company_name} Team"
            author_bio = context.company_data.get("author_bio") or f"The {company_name} content team has extensive experience in the industry."
            author_url = context.company_data.get("author_url") or company_url
            
            input_data = {
                "company_data": context.company_data,
                "primary_keyword": job_config.get("primary_keyword", ""),
                # E-E-A-T scoring fields with fallbacks
                "author_name": author_name,
                "author_bio": author_bio,
                "author_url": author_url,
            }
        
        # NOTE: SimHash content fingerprinting DEPRECATED
        # Semantic deduplication now handled by Gemini embeddings in Edge Functions
        # See: supabase/functions/s5-generate-blogs/index.ts
        
        # Get language validation metrics if available on context
        language_validation = getattr(context, 'language_validation', None) if context else None
        
        quality_report = QualityChecker.check_article(
            article=article,
            job_config=job_config,
            article_output=article_output,
            input_data=input_data,
            language_validation=language_validation,
            market_profile=getattr(context, 'market_profile', None),
            target_market=getattr(context, 'target_market', None),
        )

        # Log detailed AEO requirements validation
        self._log_aeo_validation(article, quality_report)
        
        # Ensure article is flat (no nested objects)
        validated_article = self._flatten_article(article)

        logger.info(
            f"Quality check complete: {quality_report.get('metrics', {}).get('aeo_score', 0)}/100 AEO"
        )
        return validated_article, quality_report, article_output

    # NOTE: _check_content_similarity method REMOVED
    # SimHash-based deduplication replaced by Gemini embeddings in Edge Functions
    # See: supabase/functions/s5-generate-blogs/index.ts

    def _log_aeo_validation(self, article: Dict[str, Any], quality_report: Dict[str, Any]) -> None:
        """Log detailed AEO requirements validation."""
        logger.debug("=" * 80)
        logger.debug("AEO REQUIREMENTS VALIDATION")
        logger.debug("=" * 80)
        
        # Get all content
        all_content = article.get("Intro", "") + " " + " ".join([
            article.get(f"section_{i:02d}_content", "") for i in range(1, 10)
        ])
        
        # 1. Citation distribution
        paragraphs = re.findall(r'<p[^>]*>.*?</p>', all_content, re.DOTALL)
        paras_with_citations = sum(1 for para in paragraphs if re.search(r'\[\d+\]', para))
        paras_with_2plus = sum(1 for para in paragraphs if len(re.findall(r'\[\d+\]', para)) >= 2)
        citation_distribution = (paras_with_2plus / len(paragraphs) * 100) if paragraphs else 0
        logger.debug(f"Citation distribution: {paras_with_2plus}/{len(paragraphs)} paragraphs have 2+ citations ({citation_distribution:.1f}%)")
        if citation_distribution < 70:
            logger.warning(f"⚠️  Citation distribution below target: {citation_distribution:.1f}% (target: 70%+ with buffer)")
        
        # 2. Conversational phrases
        conversational_phrases = [
            "how to", "what is", "why does", "when should", "where can",
            "you can", "you should", "let's", "here's", "this is",
            "how can", "what are", "how do", "why should", "where are",
        ]
        content_lower = all_content.lower()
        phrase_count = sum(1 for phrase in conversational_phrases if phrase in content_lower)
        logger.debug(f"Conversational phrases: {phrase_count} found (target: 12+ with buffer)")
        if phrase_count < 12:
            logger.warning(f"⚠️  Conversational phrases below target: {phrase_count} (target: 12+ with buffer)")
        
        # 3. Question headers
        question_patterns = ["what is", "how does", "why does", "when should", "where can", "what are", "how can"]
        question_headers = 0
        for i in range(1, 10):
            title = article.get(f"section_{i:02d}_title", "")
            if title and any(pattern in title.lower() for pattern in question_patterns):
                question_headers += 1
        logger.debug(f"Question headers: {question_headers} found (target: 2+)")
        if question_headers < 2:
            logger.warning(f"⚠️  Question headers below target: {question_headers} (target: 2+)")
        
        # 4. Lists
        list_count = all_content.count("<ul>") + all_content.count("<ol>")
        logger.debug(f"Lists: {list_count} found (target: 3+)")
        if list_count < 3:
            logger.warning(f"⚠️  Lists below target: {list_count} (target: 3+)")
        
        # 5. Paragraph length
        long_paragraphs = []
        for para in paragraphs:
            text_no_html = re.sub(r'<[^>]+>', ' ', para)
            word_count = len(text_no_html.split())
            if word_count > 60:  # Allow up to 60 words (10-word error range)
                long_paragraphs.append(word_count)
        logger.debug(f"Paragraph length violations: {len(long_paragraphs)} paragraphs >60 words (target: 0)")
        if long_paragraphs:
            logger.warning(f"⚠️  {len(long_paragraphs)} paragraphs exceed 60 words")
        
        logger.debug("=" * 80)

    def _flatten_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flatten nested objects to single-level dictionary.

        Args:
            article: Article (may contain nested objects)

        Returns:
            Flattened article
        """
        flattened = {}

        for key, value in article.items():
            if isinstance(value, dict):
                # Flatten nested dicts with prefix
                for nested_key, nested_value in value.items():
                    flattened[f"{key}_{nested_key}"] = nested_value
            elif hasattr(value, "model_dump"):
                # Convert Pydantic models
                flattened[key] = value.model_dump()
            elif hasattr(value, "__dict__"):
                # Convert objects to dict
                flattened[key] = value.__dict__
            else:
                # Keep as-is
                flattened[key] = value

        return flattened

    def _enforce_aeo_requirements(
        self, article: Dict[str, Any], job_config: Dict[str, Any], language: str = "en"
    ) -> Dict[str, Any]:
        """
        Enforce AEO requirements through post-processing corrections.
        
        Fixes:
        1. Citation distribution (add citations to paragraphs with <2)
        2. Conversational phrases (add if <8 found) - LANGUAGE-AWARE
        3. Question headers (convert section titles to questions if <2)
        4. Long paragraphs (split paragraphs >60 words)
        5. Missing lists (add lists if <3 found)
        
        Args:
            article: Article dictionary
            job_config: Job configuration
            language: Target language code (e.g., 'de', 'en', 'fr')
            
        Returns:
            Article with AEO requirements enforced
        """
        logger.debug(f"Enforcing AEO requirements (language={language})...")
        
        # Get all section content
        all_sections_content = ""
        for i in range(1, 10):
            content = article.get(f"section_{i:02d}_content", "")
            if content:
                all_sections_content += content + " "
        
        # 1. Fix citation distribution
        article = self._fix_citation_distribution(article)
        
        # 2. Add conversational phrases - SKIP for non-English (already in prompt)
        # This avoids injecting English phrases into non-English content
        if language == "en":
            article = self._add_conversational_phrases(article, language)
        else:
            logger.debug(f"Skipping English phrase injection for {language} content")
        
        # 3. Enhance Direct Answer (conversational phrases only, no keyword injection) - LANGUAGE-AWARE
        # Note: Keyword inclusion is now handled entirely by the prompt - no post-processing
        article = self._enhance_direct_answer(article, "", language)
        
        # 4. Convert section titles to questions
        article = self._convert_headers_to_questions(article)
        
        # 5. Split long paragraphs
        article = self._split_long_paragraphs(article)
        
        # 6. Add missing lists - LANGUAGE-AWARE
        article = self._add_missing_lists(article, language)
        
        logger.debug("AEO requirements enforcement complete")
        return article

    def _fix_citation_distribution(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Fix citation distribution - ensure 70%+ paragraphs have 2+ citations (buffer above 60% minimum)."""
        logger.debug("Fixing citation distribution...")
        
        # Get sources for citation numbers
        sources = article.get("Sources", "")
        source_lines = [s.strip() for s in sources.split('\n') if s.strip() and s.strip().startswith('[')]
        available_citation_numbers = []
        for line in source_lines:
            match = re.search(r'\[(\d+)\]', line)
            if match:
                available_citation_numbers.append(int(match.group(1)))
        
        if not available_citation_numbers:
            logger.warning("No sources available for citation distribution fix")
            return article
        
        # Process each section
        for i in range(1, 10):
            content = article.get(f"section_{i:02d}_content", "")
            if not content:
                continue
            
            # Extract paragraphs
            paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', content, re.DOTALL)
            if not paragraphs:
                continue
            
            fixed_paragraphs = []
            for para in paragraphs:
                # Count citations in paragraph
                citations = re.findall(r'\[(\d+)\]', para)
                citation_count = len(citations)
                
                # If <2 citations, add more
                if citation_count < 2 and available_citation_numbers:
                    # Get citations not already in paragraph
                    used_numbers = {int(c) for c in citations}
                    available = [n for n in available_citation_numbers if n not in used_numbers]
                    
                    # Add citations to reach 2-3 total
                    needed = min(2 - citation_count, len(available))
                    if needed > 0:
                        # Add citations at end of paragraph (before </p>)
                        new_citations = "".join([f"[{n}]" for n in available[:needed]])
                        # Insert before closing </p> tag
                        para = para.rstrip() + " " + new_citations
                        logger.debug(f"Added {needed} citations to paragraph in section {i}")
                
                fixed_paragraphs.append(f"<p>{para}</p>")
            
            # Reconstruct section content
            article[f"section_{i:02d}_content"] = "".join(fixed_paragraphs)
        
        return article

    def _humanize_article(self, article: Dict[str, Any], language: str = "en") -> Dict[str, Any]:
        """
        Humanize content by removing AI-typical phrases.
        
        Applies humanization to all text content fields.
        Language validation is now handled separately in Step 32a.6.
        
        Args:
            article: Article dictionary
            language: Target language code
        """
        from ..utils.humanizer import humanize_content, get_ai_score
        
        # NOTE: English phrase removal (band-aid) has been replaced by proper
        # language validation with automatic retry. See Step 32a.6 in execute().
        
        # Fields that contain text content to humanize
        text_fields = [
            "Intro",
            "Direct_Answer", 
            "Key_Takeaways",
        ]
        
        # Also humanize all section content
        for i in range(1, 15):
            text_fields.append(f"section_{i:02d}_content")
        
        # Apply humanization to each field
        for field in text_fields:
            if field in article and article[field]:
                original = article[field]
                humanized = humanize_content(original, aggression="aggressive")
                if humanized != original:
                    logger.debug(f"Humanized {field}")
                article[field] = humanized
        
        # Humanize FAQ answers
        if "FAQ" in article and isinstance(article["FAQ"], list):
            for faq in article["FAQ"]:
                if "answer" in faq and faq["answer"]:
                    faq["answer"] = humanize_content(faq["answer"], aggression="light")
        
        # Humanize PAA answers  
        if "PAA" in article and isinstance(article["PAA"], list):
            for paa in article["PAA"]:
                if "answer" in paa and paa["answer"]:
                    paa["answer"] = humanize_content(paa["answer"], aggression="light")
        
        # Log AI score
        all_content = " ".join([
            str(article.get(f, "")) for f in text_fields if article.get(f)
        ])
        ai_score = get_ai_score(all_content)
        logger.info(f"Content AI-ness score: {ai_score}/100 (lower is better)")
        
        return article

    def _add_conversational_phrases(self, article: Dict[str, Any], language: str = "en") -> Dict[str, Any]:
        """Add conversational phrases aggressively to reach 12+ phrases (buffer for variance).
        
        ONLY used for English content. Non-English content skips this to avoid English leakage.
        """
        if language != "en":
            logger.debug(f"Skipping conversational phrase injection for {language} (not English)")
            return article
            
        logger.debug("Adding conversational phrases (aggressive mode)...")
        
        # Extended phrase list for better coverage
        conversational_phrases = [
            "how to", "what is", "why does", "when should", "where can",
            "you can", "you'll", "you should", "let's", "here's", "this is",
            "how can", "what are", "how do", "why should", "where are",
            "we'll", "that's", "when you", "if you", "so you can", "which means",
        ]
        
        # High-value phrases that sound natural
        injection_phrases = [
            ("here's how", "Here's how"),
            ("you can", "You can"),
            ("you'll find", "You'll find"),
            ("that's why", "That's why"),
            ("if you want", "If you want"),
            ("when you", "When you"),
            ("so you can", "so you can"),
            ("this is", "This is"),
            ("what is", "What is"),
            ("how to", "Here's how to"),
        ]
        
        # Count existing phrases in ALL content
        all_content = article.get("Intro", "") + " " + article.get("Direct_Answer", "") + " "
        all_content += " ".join([article.get(f"section_{i:02d}_content", "") for i in range(1, 10)])
        content_lower = all_content.lower()
        existing_count = sum(1 for phrase in conversational_phrases if phrase in content_lower)
        
        logger.debug(f"Found {existing_count} conversational phrases (target: 12+)")
        
        if existing_count >= 12:
            return article
        
        phrases_needed = 12 - existing_count
        added_count = 0
        phrase_idx = 0
        
        # Strategy 1: Add to Intro if it doesn't have enough
        intro = article.get("Intro", "")
        if intro:
            intro_lower = intro.lower()
            intro_phrase_count = sum(1 for phrase in conversational_phrases if phrase in intro_lower)
            if intro_phrase_count < 2 and added_count < phrases_needed:
                # Add "Here's" or "You'll find" at the start of a sentence
                sentences = re.split(r'(?<=[.!?])\s+', intro)
                if len(sentences) > 1:
                    # Modify second sentence to add phrase
                    second = sentences[1].strip()
                    if second and not any(p in second.lower() for p in conversational_phrases):
                        words = second.split()
                        if words and words[0][0].isupper():
                            first_word_lower = words[0][0].lower() + words[0][1:] if len(words[0]) > 1 else words[0].lower()
                            
                            # CRITICAL FIX: Prevent "Here's this/that/these/those" (grammatically incorrect)
                            # Also prevent "Here's" before articles (a, an, the) or demonstratives
                            # Also prevent "Here's" before prepositions (e.g., "Here's in late 2024")
                            skip_words = ['this', 'that', 'these', 'those', 'the', 'a', 'an', 'it', 'they', 'we', 'you']
                            prepositions = ['in', 'on', 'at', 'by', 'for', 'with', 'from', 'to', 'of', 'about', 'into', 'onto']
                            
                            if first_word_lower in skip_words or first_word_lower in prepositions:
                                # Use alternative phrase instead or skip
                                if first_word_lower in ['this', 'that']:
                                    # "This scenario" → Skip this injection to avoid "Here's this"
                                    logger.debug("Skipped 'Here's' injection to avoid 'Here's this/that'")
                                elif first_word_lower in prepositions:
                                    # "In late 2024" → Skip to avoid "Here's in late 2024"
                                    logger.debug(f"Skipped 'Here's' injection to avoid 'Here's {first_word_lower}'")
                                else:
                                    # For other skip words, use different phrase
                                    new_second = f"You'll find {first_word_lower} " + " ".join(words[1:])
                                    sentences[1] = new_second
                                    article["Intro"] = " ".join(sentences)
                                    added_count += 1
                                    logger.debug("Added 'You'll find' to Intro (alternative phrase)")
                            else:
                                new_second = f"Here's {first_word_lower} " + " ".join(words[1:])
                                sentences[1] = new_second
                                article["Intro"] = " ".join(sentences)
                                added_count += 1
                                logger.debug("Added 'Here's' to Intro")
        
        # Strategy 2: Add to sections - more aggressively
        for i in range(1, 10):
            if added_count >= phrases_needed:
                break
                
            content = article.get(f"section_{i:02d}_content", "")
            if not content:
                continue
            
            # Find all paragraphs
            paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', content, re.DOTALL)
            if len(paragraphs) < 2:
                continue
            
            content_lower_section = content.lower()
            section_phrase_count = sum(1 for phrase in conversational_phrases if phrase in content_lower_section)
            
            # Add phrase if section has < 2 conversational phrases
            if section_phrase_count < 2:
                # Try to add to second or third paragraph (not first which might have been modified)
                for para_idx in [1, 2, 0]:
                    if para_idx >= len(paragraphs) or added_count >= phrases_needed:
                        continue
                    
                    para_text = paragraphs[para_idx]
                    para_lower = para_text.lower()
                    
                    # Skip if paragraph already has a conversational phrase
                    if any(p in para_lower for p in conversational_phrases):
                        continue
                    
                    # Remove HTML for processing
                    text_no_html = re.sub(r'<[^>]+>', ' ', para_text).strip()
                    words = text_no_html.split()
                    
                    if len(words) < 5:
                        continue
                    
                    # Get phrase to inject
                    phrase_lower, phrase_cap = injection_phrases[phrase_idx % len(injection_phrases)]
                    phrase_idx += 1
                    
                    # Check if first word is suitable
                    first_word = words[0]
                    first_word_lower = first_word[0].lower() + first_word[1:] if len(first_word) > 1 else first_word.lower()
                    
                    # Skip problematic combinations
                    # CRITICAL FIX: Prevent "Here's this/that/these/those" (grammatically incorrect)
                    skip_words = ['the', 'a', 'an', 'however', 'although', 'despite', 'while', 'because', 
                                 'this', 'that', 'these', 'those', 'it', 'they', 'we', 'you']
                    if first_word_lower in skip_words:
                        continue
                    
                    # CRITICAL FIX: Prevent "Here's" + demonstrative pronouns
                    if phrase_lower == "here's how" and first_word_lower in ['this', 'that', 'these', 'those']:
                        continue
                    
                    # CRITICAL FIX: Prevent "Here's" before prepositions (e.g., "Here's in late 2024")
                    prepositions = ['in', 'on', 'at', 'by', 'for', 'with', 'from', 'to', 'of', 'about', 'into', 'onto']
                    if phrase_lower in ["here's", "here's how"] and first_word_lower in prepositions:
                        continue  # Skip - "Here's in late 2024" is grammatically incorrect
                    
                    # CRITICAL FIX: Prevent grammatically incorrect phrase injections
                    # "You can fragmented" → should skip (fragmented is adjective, not verb)
                    # "When you building" → should skip (building needs "are" or just "Building")
                    # "If you want regulatory" → should skip (regulatory is adjective)
                    # "You can identity" → should skip (identity is noun, not verb)
                    # "When you finally" → should skip (finally is adverb, not verb)
                    # "If you want digital" → should skip (digital is adjective)
                    
                    # Check if first word is a verb/gerund that works with the phrase
                    # Verbs that work with "you can": achieve, implement, use, create, build, etc.
                    # Verbs that DON'T work: fragmented (adj), building (needs "are"), regulatory (adj)
                    problematic_first_words = {
                        'fragmented', 'building', 'regulatory', 'successful', 'effective', 'modern',
                        'traditional', 'automated', 'strategic', 'critical', 'essential', 'important',
                        'identity', 'digital', 'sovereignty', 'compliance', 'governance', 'security'
                    }
                    
                    # Adverbs that don't work with "when you"
                    adverbs = ['finally', 'eventually', 'ultimately', 'recently', 'currently', 'previously']
                    
                    # If phrase is "you can", "when you", or "if you want", check if first word works
                    if phrase_lower in ["you can", "when you", "if you want"]:
                        if first_word_lower in problematic_first_words:
                            continue  # Skip this injection - would create grammatical error
                        # Also check if first word ends in -ing (gerund) - "when you building" is wrong
                        if first_word_lower.endswith('ing') and phrase_lower == "when you":
                            continue  # Skip - "When you building" is grammatically incorrect
                        # Check for adverbs with "when you"
                        if first_word_lower in adverbs and phrase_lower == "when you":
                            continue  # Skip - "When you finally" is grammatically incorrect
                    
                    # CRITICAL FIX: Prevent "That's why however" (double conjunction)
                    # Also prevent "That's why conversely" (double conjunction)
                    if phrase_lower == "that's why" and first_word_lower in ["however", "conversely", "alternatively"]:
                        continue  # Skip - "That's why however/conversely" is grammatically incorrect
                    
                    # CRITICAL FIX: Prevent "That's why handling" (grammatically incorrect)
                    # "handling", "navigating" are gerunds, not suitable for "That's why"
                    # "That's why" should be followed by a clause, not a gerund
                    if phrase_lower == "that's why" and (first_word_lower.endswith("ing") or first_word_lower in ["handling", "navigating", "managing", "building", "creating"]):
                        continue  # Skip - "That's why handling" is grammatically incorrect
                    
                    # CRITICAL FIX: Prevent "You can handling" (grammatically incorrect)
                    # "handling", "navigating" are gerunds, not suitable for "You can"
                    # "You can" should be followed by a verb, not a gerund
                    if phrase_lower == "you can" and (first_word_lower.endswith("ing") or first_word_lower in ["handling", "navigating", "managing", "building", "creating"]):
                        continue  # Skip - "You can handling" is grammatically incorrect
                    
                    # CRITICAL FIX: Prevent "You'll find to" (grammatically incorrect)
                    # "You'll find to combat" should be "To combat" or "You'll find that combat"
                    if phrase_lower == "you'll find" and first_word_lower == "to":
                        continue  # Skip - "You'll find to" is grammatically incorrect
                    
                    # CRITICAL FIX: Prevent "You'll find selecting" (grammatically incorrect)
                    # "selecting" is a gerund, not suitable for "You'll find"
                    # "You'll find" should be followed by a clause, not a gerund
                    if phrase_lower == "you'll find" and (first_word_lower.endswith("ing") or first_word_lower in ["selecting", "handling", "navigating", "managing", "building", "creating"]):
                        continue  # Skip - "You'll find selecting" is grammatically incorrect
                    
                    # CRITICAL FIX: Prevent "If you want similarly" (grammatically incorrect)
                    # "similarly" is an adverb, not suitable for "if you want"
                    if phrase_lower == "if you want" and first_word_lower in ["similarly", "ultimately", "finally", "eventually"]:
                        continue  # Skip - "If you want similarly" is grammatically incorrect
                    
                    # CRITICAL FIX: Prevent "This is ultimately" (awkward phrasing)
                    # "ultimately" should start the sentence, not follow "This is"
                    if phrase_lower == "this is" and first_word_lower in ["ultimately", "finally", "eventually"]:
                        continue  # Skip - "This is ultimately" is awkward
                    
                    # CRITICAL FIX: Prevent "so you can Cloud" (grammatically incorrect)
                    # "Cloud" is a proper noun, not suitable for "so you can"
                    if phrase_lower == "so you can" and first_word_lower in ["cloud", "security", "identity", "digital"]:
                        continue  # Skip - "so you can Cloud" is grammatically incorrect
                    
                    # CRITICAL FIX: Prevent "Here's how beyond" (grammatically incorrect)
                    # "beyond" is a preposition, not suitable for "Here's how"
                    if phrase_lower in ["here's how", "how to"] and first_word_lower in ["beyond", "within", "through", "across", "during", "before", "after"]:
                        continue  # Skip - "Here's how beyond" is grammatically incorrect
                    
                    # Build new paragraph start
                    if phrase_lower in ["you can", "you'll find", "when you", "if you want"]:
                        new_start = f"{phrase_cap} {first_word_lower}"
                    elif phrase_lower == "that's why":
                        new_start = f"That's why {first_word_lower}"
                    elif phrase_lower in ["here's how", "how to"]:
                        new_start = f"Here's how {first_word_lower}"
                    elif phrase_lower == "so you can":
                        # Insert in middle
                        # CRITICAL FIX: Check if the word after insertion point is problematic
                        if len(words) > 10:
                            mid_point = len(words) // 2
                            next_word_after_insertion = words[mid_point].lower() if mid_point < len(words) else ""
                            
                            # Skip if next word is a proper noun or problematic word
                            problematic_mid_words = ['cloud', 'security', 'identity', 'digital', 'sovereignty', 
                                                      'compliance', 'governance', 'cspm', 'cwpp', 'cnapp']
                            if next_word_after_insertion in problematic_mid_words:
                                continue  # Skip - would create "so you can Cloud" which is grammatically incorrect
                            
                            new_text = " ".join(words[:mid_point]) + " so you can " + " ".join(words[mid_point:])
                            new_para = f"<p>{new_text}</p>"
                            old_para = f"<p>{para_text}</p>"
                            content = content.replace(old_para, new_para, 1)
                            article[f"section_{i:02d}_content"] = content
                            added_count += 1
                            logger.debug(f"Added 'so you can' to section {i} paragraph {para_idx}")
                            continue
                    else:
                        new_start = f"{phrase_cap} {first_word_lower}"
                    
                    rest = " ".join(words[1:])
                    new_para_text = new_start + (" " + rest if rest else "")
                    
                    # Replace in content
                    old_para = f"<p>{para_text}</p>"
                    new_para = f"<p>{new_para_text}</p>"
                    content = content.replace(old_para, new_para, 1)
                    article[f"section_{i:02d}_content"] = content
                    added_count += 1
                    logger.debug(f"Added '{phrase_lower}' to section {i} paragraph {para_idx}")
                    break  # Move to next section
        
        # Strategy 3: Inject phrases mid-sentence in remaining sections
        if added_count < phrases_needed:
            for i in range(1, 10):
                if added_count >= phrases_needed:
                    break
                    
                content = article.get(f"section_{i:02d}_content", "")
                if not content or "you can" in content.lower():
                    continue
                
                # Find a good place to inject "— you can"
                # Look for sentences ending with benefits/actions
                patterns_to_enhance = [
                    (r'(\w+ing)\s+(\w+)\s+by\s+(\d+%)', r'\1 \2 by \3 — and you can achieve similar results'),
                    (r'(reduces|increases|improves)\s+(\w+)\s+by', r'\1 \2 by'),
                ]
                
                for pattern, replacement in patterns_to_enhance:
                    if re.search(pattern, content, re.IGNORECASE):
                        # Already has good phrases
                        break
        
        # Final count
        final_content = article.get("Intro", "") + " " + article.get("Direct_Answer", "") + " "
        final_content += " ".join([article.get(f"section_{i:02d}_content", "") for i in range(1, 10)])
        final_count = sum(1 for phrase in conversational_phrases if phrase in final_content.lower())
        logger.debug(f"Conversational phrases after injection: {final_count} (added {added_count})")
        
        return article


    def _enhance_direct_answer(self, article: Dict[str, Any], primary_keyword: str = "", language: str = "en") -> Dict[str, Any]:
        """Enhance Direct Answer with conversational phrase (English only).
        
        LANGUAGE-AWARE: Only adds English phrases for English content.
        Keyword inclusion is now handled entirely by the prompt - no post-processing injection.
        """
        logger.debug(f"Enhancing Direct Answer (language={language})...")
        
        direct_answer = article.get("Direct_Answer", "")
        if not direct_answer:
            return article
        
        # SKIP conversational phrase injection for non-English
        # This is the main source of English leakage
        if language != "en":
            logger.debug(f"Skipping English phrase injection for {language} Direct Answer")
            return article
        
        # Check if already has conversational phrase (English only)
        conversational_starters = ["here's", "you can", "what is", "how does", "let's"]
        has_conversational = any(direct_answer.lower().startswith(starter) for starter in conversational_starters)
        
        if has_conversational:
            logger.debug("Direct Answer already has conversational phrase")
            return article
        
        # Add conversational phrase at start (ENGLISH ONLY)
        words = direct_answer.split()
        if not words:
            return article
        
        first_word = words[0]
        rest_words = words[1:]
        first_word_lower = first_word[0].lower() + first_word[1:] if len(first_word) > 1 else first_word.lower()
        
        if "involves" in direct_answer.lower() or "includes" in direct_answer.lower():
            enhanced = f"Here's how {first_word_lower} {' '.join(rest_words)}"
        elif "reduces" in direct_answer.lower() or "improves" in direct_answer.lower():
            enhanced = f"You can {first_word_lower} {' '.join(rest_words)}"
        else:
            enhanced = f"Here's how {first_word_lower} {' '.join(rest_words)}"
        
        # Ensure length stays within 40-60 words
        enhanced_words = enhanced.split()
        if len(enhanced_words) > 60:
            enhanced = " ".join(enhanced_words[:60])
            citations = re.findall(r'\[\d+\]', direct_answer)
            if citations:
                enhanced += " " + " ".join(citations)
        
        article["Direct_Answer"] = enhanced
        logger.debug("Enhanced Direct Answer with conversational phrase (English)")
        
        return article

    def _convert_headers_to_questions(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Convert section titles to question format if <2 question headers."""
        logger.debug("Converting headers to question format...")
        
        # Check existing question headers
        question_patterns = ["what is", "how does", "why does", "when should", "where can", "what are", "how can"]
        # Question words at the START of a title that indicate it's already a question
        question_start_words = ["what", "how", "why", "when", "where", "which", "who", "can", "does", "is", "are", "should", "will"]
        question_count = 0
        
        for i in range(1, 10):
            title = article.get(f"section_{i:02d}_title", "")
            if title:
                title_lower = title.lower()
                first_word = title_lower.split()[0] if title_lower.split() else ""
                # Count as question if it has a question pattern, ends with ?, or STARTS with a question word
                if any(pattern in title_lower for pattern in question_patterns) or title.endswith("?") or first_word in question_start_words:
                    question_count += 1
        
        logger.debug(f"Found {question_count} question headers (target: 3-4)")
        
        # Target: 3-4 question headers (improved from 2)
        target_questions = 3
        if question_count >= target_questions:
            return article
        
        # Convert non-question headers to questions
        conversions_needed = target_questions - question_count
        converted = 0
        
        for i in range(1, 10):
            if converted >= conversions_needed:
                break
                
            title = article.get(f"section_{i:02d}_title", "")
            if not title:
                continue
            
            title_lower = title.lower()
            first_word = title_lower.split()[0] if title_lower.split() else ""
            
            # CRITICAL FIX: Skip if already a question - check both patterns AND starting question words
            # This prevents "What is What is..." type double conversions
            if any(pattern in title_lower for pattern in question_patterns):
                continue
            if first_word in question_start_words:
                continue
            if title.endswith("?"):
                continue
            
            # Convert to question format
            # Examples:
            # "Why AI Adoption is Accelerating" -> "Why is AI Adoption Accelerating?"
            # "How AI Reduces Costs" -> "How Does AI Reduce Costs?"
            # "Strategic Implementation Steps" -> "What are Strategic Implementation Steps?"
            
            if title.startswith("Why "):
                new_title = title.replace("Why ", "Why is ", 1)
                if not new_title.endswith("?"):
                    new_title = new_title.rstrip(".") + "?"
            elif title.startswith("How "):
                new_title = title.replace("How ", "How does ", 1)
                if not new_title.endswith("?"):
                    new_title = new_title.rstrip(".") + "?"
            elif title.startswith("What "):
                if not title.endswith("?"):
                    new_title = title.rstrip(".") + "?"
                else:
                    new_title = title
            elif "vs." in title or "vs " in title.lower():
                # "Generative AI vs. Traditional Chatbots" -> "What is the difference between Generative AI and Traditional Chatbots?"
                parts = re.split(r'\s+vs\.?\s+', title, flags=re.IGNORECASE)
                if len(parts) == 2:
                    new_title = f"What is the difference between {parts[0]} and {parts[1]}?"
                else:
                    new_title = f"What is {title}?"
            elif "Enhancing" in title or "Improving" in title or "Boosting" in title:
                # "Enhancing Customer Experience" -> "How can you enhance customer experience?"
                # Extract the main topic
                topic = title.replace("Enhancing ", "").replace("Improving ", "").replace("Boosting ", "")
                new_title = f"How can you enhance {topic.lower()}?"
            elif title.startswith("How to "):
                # CRITICAL FIX: Skip titles that already start with "How to" - don't convert them
                # "How to Build X" should stay as is, not become "How to How to Build X?"
                continue
            elif title.split()[0].lower() in ["governance", "strategic", "compliance", "security"] and "frameworks" in title.lower():
                # CRITICAL FIX: Skip titles like "Governance Frameworks for Safe Scaling"
                # These are descriptive titles that shouldn't become "How to Governance..."
                continue
            elif "Overcoming" in title or "Challenges" in title:
                # "Overcoming Implementation Challenges" -> "What are the challenges of implementation?"
                topic = title.replace("Overcoming ", "").replace(" Challenges", "")
                new_title = f"What are the challenges of {topic.lower()}?"
            elif "Future" in title or "Trends" in title:
                # CRITICAL FIX: Prevent awkward questions like "What are the future trends in strategic implementation for the future?"
                # Also prevent "What are the future trends in outlook: the path forward?"
                # Also prevent "What are the future trends in the future: from chatbots to agents?"
                # If title already contains "future" or "trends", don't add redundant question format
                title_lower = title.lower()
                if "future" in title_lower and ("trend" in title_lower or "implementation" in title_lower or "strategic" in title_lower or "outlook" in title_lower or ":" in title):
                    # Skip conversion - would create redundant/awkward question
                    # "The Future: From Chatbots to Agents" should stay as is
                    continue
                if title.startswith("The Future"):
                    # Skip titles starting with "The Future" - they're descriptive, not questions
                    continue
                # "Future Trends and Market Growth" -> "What are the future trends?"
                new_title = f"What are the future trends in {title.lower().replace('future trends and ', '').replace('future ', '')}?"
            elif title.split()[0].endswith("ing") or title.split()[0].lower() in ["implementing", "selecting", "automation", "building", "creating", "developing", "managing", "optimizing"]:
                # CRITICAL FIX: Skip gerund titles - "Implementing Zero Trust" should NOT become "What is Implementing Zero Trust?"
                # These are action-oriented titles that work better as declarative statements
                continue
            elif ":" in title and len(title.split(":")) == 2:
                # CRITICAL FIX: Skip titles with colons - "Automation at Scale: The Netflix Approach" should NOT become "What is Automation at Scale: The Netflix Approach?"
                # These are descriptive titles that work better as declarative statements
                continue
            else:
                # CRITICAL FIX: Only convert to questions if it makes grammatical sense
                # Avoid adding "What is" to clear, declarative titles
                
                # Skip conversion for titles that are already clear statements
                # These patterns indicate titles that shouldn't be questions
                skip_patterns = [
                    r'^The\s+',  # "The New Gatekeepers" - clear statement
                    r'^Real-World\s+',  # "Real-World Success Stories" - clear statement
                    r'^Core\s+',  # "Core Workflows" - clear statement
                    r'^Strategic\s+',  # "Strategic Implementation" - clear statement
                    r'^AI-Driven\s+',  # "AI-Driven Personalization" - clear statement
                    r'^Compliance\s+',  # "Compliance Frameworks" - clear statement
                    r'^Integrating\s+',  # "Integrating Security" - clear statement
                    r'^Building\s+',  # "Building a Secure" - clear statement
                    r'^Future\s+',  # "Future Trends" - clear statement
                    r':\s+',  # Titles with colons are usually clear statements
                    r'\s+for\s+',  # "X for Y" - descriptive title (e.g., "Compliance Frameworks for Global Reach")
                ]
                
                should_skip = any(re.match(pattern, title, re.IGNORECASE) for pattern in skip_patterns)
                
                if should_skip:
                    # Keep original title - don't convert to question
                    continue
                
                # Try to convert statement to question only if it makes sense
                if "Steps" in title or "Guide" in title or "Strategies" in title:
                    new_title = f"What are {title}?"
                elif title.endswith("ing"):
                    # "Boosting Agent Productivity" -> "How to Boost Agent Productivity?"
                    new_title = f"How to {title.replace('ing', '')}?"
                else:
                    # Only convert if title is short and would work as a question
                    # Skip long descriptive titles
                    # CRITICAL FIX: Prevent awkward questions like "What are the future trends in strategic implementation for the future?"
                    if len(title.split()) <= 6:
                        # Check if title already contains "future" or "trends" to avoid redundancy
                        title_lower = title.lower()
                        if "future" in title_lower and "trend" in title_lower:
                            # Skip - would create redundant question
                            continue
                        new_title = f"What is {title}?"
                    else:
                        # Keep original - too long/descriptive to be a question
                        continue
            
            article[f"section_{i:02d}_title"] = new_title
            converted += 1
            logger.debug(f"Converted section {i} title to question: '{new_title}'")
        
        return article

    def _split_long_paragraphs(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Split paragraphs >60 words into multiple shorter paragraphs (target: 40-60 words)."""
        logger.debug("Splitting long paragraphs...")
        
        for i in range(1, 10):
            content = article.get(f"section_{i:02d}_content", "")
            if not content:
                continue
            
            # Extract paragraphs
            paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', content, re.DOTALL)
            if not paragraphs:
                continue
            
            fixed_paragraphs = []
            for para in paragraphs:
                # Remove HTML tags for word count
                text_no_html = re.sub(r'<[^>]+>', ' ', para)
                word_count = len(text_no_html.split())
                
                # Split if >60 words (natural paragraph length)
                if word_count > 60:
                    # Split paragraph at natural break points
                    # Try to split at periods, then at conjunctions
                    sentences = re.split(r'([.!?]+\s+)', para)
                    if len(sentences) > 1:
                        # Group sentences into paragraphs of 40-60 words
                        current_para = ""
                        current_word_count = 0
                        
                        for sentence in sentences:
                            sentence_text = re.sub(r'<[^>]+>', ' ', sentence)
                            sentence_words = len(sentence_text.split())
                            
                            # Split when we reach 55-60 words (target range)
                            if current_word_count + sentence_words > 60 and current_para:
                                # Start new paragraph
                                fixed_paragraphs.append(f"<p>{current_para.strip()}</p>")
                                current_para = sentence
                                current_word_count = sentence_words
                            elif current_word_count + sentence_words > 55 and current_word_count >= 40:
                                # If we're in the target range and adding this would exceed, start new para
                                fixed_paragraphs.append(f"<p>{current_para.strip()}</p>")
                                current_para = sentence
                                current_word_count = sentence_words
                            else:
                                current_para += sentence
                                current_word_count += sentence_words
                        
                        if current_para:
                            fixed_paragraphs.append(f"<p>{current_para.strip()}</p>")
                        
                        logger.debug(f"Split paragraph in section {i} ({word_count} words -> {len(fixed_paragraphs)} paragraphs)")
                    else:
                        # Can't split naturally, try splitting at commas or conjunctions
                        # Split at commas if paragraph is very long
                        if word_count > 80:
                            parts = re.split(r'(,\s+)', para)
                            if len(parts) > 3:
                                # Group parts into smaller paragraphs
                                current_para = ""
                                current_word_count = 0
                                for part in parts:
                                    part_text = re.sub(r'<[^>]+>', ' ', part)
                                    part_words = len(part_text.split())
                                    if current_word_count + part_words > 60 and current_para:
                                        fixed_paragraphs.append(f"<p>{current_para.strip()}</p>")
                                        current_para = part
                                        current_word_count = part_words
                                    else:
                                        current_para += part
                                        current_word_count += part_words
                                if current_para:
                                    fixed_paragraphs.append(f"<p>{current_para.strip()}</p>")
                                logger.debug(f"Split long paragraph in section {i} at commas ({word_count} words)")
                            else:
                                fixed_paragraphs.append(f"<p>{para}</p>")
                                logger.warning(f"Could not split long paragraph in section {i} ({word_count} words)")
                        else:
                            fixed_paragraphs.append(f"<p>{para}</p>")
                            logger.debug(f"Paragraph in section {i} is {word_count} words (acceptable)")
                else:
                    fixed_paragraphs.append(f"<p>{para}</p>")
            
            # Reconstruct section content
            article[f"section_{i:02d}_content"] = "".join(fixed_paragraphs)
        
        return article

    def _extract_list_items_from_content(self, content: str, min_items: int = 2) -> list:
        """Extract list items from content using multiple strategies.
        
        Args:
            content: HTML content string
            min_items: Minimum number of items to extract (default: 2)
            
        Returns:
            List of extracted items (strings)
        """
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', content, re.DOTALL)
        if not paragraphs:
            return []
        
        list_items = []
        seen_items = set()
        
        # Strategy 1: Extract KEY POINTS from sentences (not verbatim sentences)
        # CRITICAL FIX: Create summaries, not verbatim copies
        for para in paragraphs[:3]:
            para_text = re.sub(r'<[^>]+>', ' ', para)
            sentences = re.split(r'[.!?]+\s+', para_text)
            for sentence in sentences:
                sentence = sentence.strip()
                word_count = len(sentence.split())
                
                # Skip if sentence is too similar to existing paragraph text (verbatim duplication)
                sentence_lower = sentence.lower()
                
                # Check if this sentence appears verbatim in any paragraph
                is_verbatim = False
                for other_para in paragraphs:
                    other_para_text = re.sub(r'<[^>]+>', ' ', other_para).lower()
                    # If sentence is >80% of paragraph or paragraph contains exact sentence, skip
                    if sentence_lower in other_para_text and len(sentence_lower) > len(other_para_text) * 0.8:
                        is_verbatim = True
                        break
                
                if is_verbatim:
                    continue
                
                # Extract key phrase (first 8-12 words) instead of full sentence
                if 10 <= word_count < 100:
                    words = sentence.split()
                    # Create summary: first 8-12 words, or key phrase if it has numbers/stats
                    if re.search(r'\d+%|\$\d+|\d+ (?:billion|million|thousand)', sentence):
                        # Keep full sentence if it has important stats
                        summary = sentence
                    else:
                        # Extract key phrase (first 8-12 words)
                        # CRITICAL FIX: Ensure summary is a complete thought, not cut off mid-sentence
                        summary_words = words[:min(12, len(words))]
                        summary = " ".join(summary_words)
                        
                        # Don't end with "..." if it's a complete sentence
                        # Check if the last word ends with punctuation or if we're at a natural break
                        if len(words) > 12:
                            # Only add "..." if we're truly truncating
                            # But prefer to end at a complete phrase
                            last_word = summary_words[-1] if summary_words else ""
                            if not last_word.endswith(('.', '!', '?', ':', ';')):
                                # Try to find a better break point (end of phrase)
                                # Look for conjunctions, prepositions, or commas
                                found_break = False
                                for i in range(len(summary_words) - 1, max(8, len(summary_words) - 4), -1):
                                    if summary_words[i].endswith((',', '.', ':', ';')):
                                        summary = " ".join(summary_words[:i+1])
                                        found_break = True
                                        break
                                # CRITICAL FIX: Don't add "..." - prefer complete phrase without ellipsis
                                # Incomplete list items look unprofessional
                                if not found_break:
                                    summary = " ".join(summary_words)  # Keep as complete phrase, no "..."
                    
                    summary_lower = summary.lower()
                    if summary_lower not in seen_items and len(summary) > 30:
                        list_items.append(summary)
                        seen_items.add(summary_lower)
                        if len(list_items) >= min_items + 2:  # Get a few extra
                            break
            if len(list_items) >= min_items + 2:
                break
        
        # Strategy 2: Extract key phrases with statistics/numbers
        if len(list_items) < min_items:
            for para in paragraphs[:3]:
                para_text = re.sub(r'<[^>]+>', ' ', para)
                sentences = re.split(r'[.!?]+\s+', para_text)
                for sentence in sentences:
                    sentence = sentence.strip()
                    word_count = len(sentence.split())
                    if (10 <= word_count < 100 and 
                        (re.search(r'\d+%|\$\d+|\d+ (?:billion|million|thousand)', sentence) or
                         re.search(r'\d+ out of \d+|\d+ of \d+', sentence))):
                        sentence_lower = sentence.lower()
                        if sentence_lower not in seen_items:
                            list_items.append(sentence)
                            seen_items.add(sentence_lower)
                            if len(list_items) >= min_items + 2:
                                break
                if len(list_items) >= min_items + 2:
                    break
        
        # Strategy 3: Extract benefits/features using keywords
        if len(list_items) < min_items:
            benefit_keywords = ['enables', 'reduces', 'improves', 'increases', 'boosts', 
                              'allows', 'helps', 'provides', 'supports', 'enhances']
            for para in paragraphs[:3]:
                para_text = re.sub(r'<[^>]+>', ' ', para)
                sentences = re.split(r'[.!?]+\s+', para_text)
                for sentence in sentences:
                    sentence = sentence.strip()
                    word_count = len(sentence.split())
                    if (10 <= word_count < 100 and 
                        any(keyword in sentence.lower() for keyword in benefit_keywords)):
                        sentence_lower = sentence.lower()
                        if sentence_lower not in seen_items:
                            list_items.append(sentence)
                            seen_items.add(sentence_lower)
                            if len(list_items) >= min_items + 2:
                                break
                if len(list_items) >= min_items + 2:
                    break
        
        # Strategy 4: Extract items from sentences with colons or semicolons
        if len(list_items) < min_items:
            for para in paragraphs[:3]:
                para_text = re.sub(r'<[^>]+>', ' ', para)
                # Split on colons and semicolons
                parts = re.split(r'[:;]', para_text)
                for part in parts[1:]:  # Skip part before first colon/semicolon
                    part = part.strip()
                    word_count = len(part.split())
                    if 5 <= word_count < 80:  # Shorter items OK for this strategy
                        part_lower = part.lower()
                        if part_lower not in seen_items:
                            list_items.append(part)
                            seen_items.add(part_lower)
                            if len(list_items) >= min_items + 2:
                                break
                if len(list_items) >= min_items + 2:
                    break
        
        # Strategy 5: Create list from paragraph by splitting on commas/conjunctions
        if len(list_items) < min_items and paragraphs:
            # Use first paragraph as fallback
            para_text = re.sub(r'<[^>]+>', ' ', paragraphs[0])
            # Split on commas, "and", "or", "but"
            parts = re.split(r',\s+(?:and\s+)?|,\s+or\s+|,\s+but\s+', para_text)
            for part in parts:
                part = part.strip()
                # Remove leading articles/conjunctions
                part = re.sub(r'^(the|a|an|and|or|but)\s+', '', part, flags=re.IGNORECASE)
                word_count = len(part.split())
                if 5 <= word_count < 60:
                    part_lower = part.lower()
                    if part_lower not in seen_items and len(part_lower) > 20:
                        list_items.append(part)
                        seen_items.add(part_lower)
                        if len(list_items) >= min_items + 2:
                            break
        
        # Return items, limiting to reasonable number
        return list_items[:6]

    def _add_missing_lists(self, article: Dict[str, Any], language: str = "en") -> Dict[str, Any]:
        """Add lists to ensure 5+ lists total (at least 1 per section).
        
        LANGUAGE-AWARE: Uses target language for lead-in text.
        """
        logger.debug(f"Adding missing lists (language={language})...")
        
        # Count existing lists
        all_content = " ".join([
            article.get(f"section_{i:02d}_content", "") for i in range(1, 10)
        ])
        list_count = all_content.count("<ul>") + all_content.count("<ol>")
        
        logger.debug(f"Found {list_count} lists (target: 5+)")
        
        # Target: 5+ lists (at least 1 per active section)
        active_sections = sum(1 for i in range(1, 10) if article.get(f"section_{i:02d}_content", ""))
        target_lists = max(5, active_sections)
        
        if list_count >= target_lists:
            logger.debug(f"Target already met: {list_count} lists found")
            return article
        
        # Language-specific lead-in phrases
        lead_ins_by_language = {
            "en": ["Here are key points:", "Key benefits include:", "Important considerations:", "Here's what matters:"],
            "de": ["Wichtige Punkte:", "Die wichtigsten Vorteile:", "Wichtige Aspekte:", "Das ist entscheidend:"],
            "fr": ["Points clés:", "Principaux avantages:", "Considérations importantes:", "Ce qui compte:"],
            "es": ["Puntos clave:", "Principales beneficios:", "Consideraciones importantes:", "Lo que importa:"],
            "it": ["Punti chiave:", "Principali vantaggi:", "Considerazioni importanti:", "Cosa conta:"],
            "nl": ["Belangrijke punten:", "Belangrijkste voordelen:", "Belangrijke overwegingen:", "Waar het om gaat:"],
            "pt": ["Pontos-chave:", "Principais benefícios:", "Considerações importantes:", "O que importa:"],
        }
        lead_ins = lead_ins_by_language.get(language, lead_ins_by_language["en"])
        
        lists_to_add = target_lists - list_count
        added = 0
        
        logger.debug(f"Need to add {lists_to_add} more lists")
        
        for i in range(1, 10):
            if added >= lists_to_add:
                break
                
            content = article.get(f"section_{i:02d}_content", "")
            if not content:
                continue
            
            if "<ul>" in content or "<ol>" in content:
                logger.debug(f"Section {i} already has a list, skipping")
                continue
            
            list_items = self._extract_list_items_from_content(content, min_items=2)
            
            # CRITICAL FIX: Only create list if we have valid items
            # Don't create empty lists
            if len(list_items) >= 2:
                list_html = "<ul>" + "".join([f"<li>{item}</li>" for item in list_items[:6]]) + "</ul>"
                
                paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', content, re.DOTALL)
                if paragraphs:
                    insertion_points = [1, 0, 2] if len(paragraphs) >= 3 else ([1, 0] if len(paragraphs) >= 2 else [0])
                    
                    inserted = False
                    for insert_after in insertion_points:
                        if insert_after < len(paragraphs):
                            lead_in = lead_ins[added % len(lead_ins)]
                            
                            para_pattern = f"<p>{re.escape(paragraphs[insert_after])}</p>"
                            replacement = f"<p>{paragraphs[insert_after]}</p><p>{lead_in}</p>{list_html}"
                            new_content = re.sub(para_pattern, replacement, content, count=1)
                            
                            if new_content != content:
                                article[f"section_{i:02d}_content"] = new_content
                                added += 1
                                inserted = True
                                logger.debug(f"Added list to section {i} ({len(list_items)} items)")
                                break
                    
                    if not inserted:
                        logger.warning(f"Failed to insert list in section {i}")
                else:
                    logger.warning(f"Section {i} has no paragraphs, cannot add list")
            else:
                # Skip this section - can't create a valid list
                logger.debug(f"Section {i}: Could not extract enough list items ({len(list_items)} found), skipping")
                continue
        
        final_list_count = sum(1 for i in range(1, 10) 
                              if article.get(f"section_{i:02d}_content", "") and 
                              ("<ul>" in article.get(f"section_{i:02d}_content", "") or 
                               "<ol>" in article.get(f"section_{i:02d}_content", "")))
        logger.debug(f"List addition complete: {final_list_count} total lists (added {added})")
        
        return article

    def __repr__(self) -> str:
        """String representation."""
        return f"CleanupStage(stage_num={self.stage_num})"
