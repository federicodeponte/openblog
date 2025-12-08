"""
Stage 11: HTML Generation & Storage

Maps to v4.1 Phase 9, Step 34: publish-to-wordpress + storage

Final stage: Convert validated article to HTML and persist.

Handles:
1. HTML rendering from validated article
2. Metadata extraction and indexing
3. Storage (Supabase or file system)
4. Final validation and reporting

Input:
  - ExecutionContext.validated_article (from Stage 10)
  - ExecutionContext.quality_report (from Stage 10)
  - ExecutionContext.job_id
  - ExecutionContext.company_data

Output:
  - ExecutionContext.final_article (validated_article confirmed for delivery)
  - ExecutionContext.storage_result (storage operation result)
"""

import logging
import re
from typing import Dict, Any, Optional, List

from ..core import ExecutionContext, Stage
from ..processors.html_renderer import HTMLRenderer
from ..processors.storage import StorageProcessor

logger = logging.getLogger(__name__)


class StorageStage(Stage):
    """
    Stage 11: HTML Generation & Storage.

    Handles:
    - HTML rendering
    - Metadata extraction
    - Article storage
    - Final validation
    """

    stage_num = 11
    stage_name = "HTML Generation & Storage"

    async def execute(self, context: ExecutionContext) -> ExecutionContext:
        """
        Execute Stage 11: Generate HTML and store article.

        Input from context:
        - validated_article: Cleaned, merged article from Stage 10
        - quality_report: Validation report from Stage 10
        - job_id: Unique job identifier
        - company_data: Company information

        Output to context:
        - final_article: Confirmed article ready for delivery
        - storage_result: Storage operation result

        Args:
            context: ExecutionContext from Stage 10

        Returns:
            Updated context with final_article and storage_result

        Raises:
            ValueError: If validated_article missing
        """
        logger.info(f"Stage 11: {self.stage_name}")

        # Step 1: Validate input
        if not context.validated_article:
            logger.error("No validated_article available")
            context.final_article = {}
            context.storage_result = {
                "success": False,
                "error": "No validated article from Stage 10",
            }
            return context

        # Step 2: Confirm quality passed
        passed_quality = context.quality_report.get("passed", False)
        if not passed_quality:
            critical_issues = context.quality_report.get("critical_issues", [])
            logger.warning(f"Quality checks failed: {critical_issues[:2]}")
            context.final_article = {}
            context.storage_result = {
                "success": False,
                "error": "Quality checks failed",
                "critical_issues": critical_issues,
            }
            return context

        # Step 3: Extract FAQ/PAA items and generate article URL
        logger.debug("Extracting FAQ/PAA items and generating article URL...")
        
        # Extract FAQ/PAA items from parallel_results with error handling
        faq_items_dict = []
        paa_items_dict = []
        
        try:
            # Extract FAQ items
            faq_list = context.parallel_results.get('faq_items') if context.parallel_results else None
            if faq_list:
                if hasattr(faq_list, 'to_dict_list'):
                    faq_items_dict = faq_list.to_dict_list()
                elif isinstance(faq_list, list):
                    faq_items_dict = faq_list
        except Exception as e:
            logger.warning(f"Failed to extract FAQ items: {e}. Continuing without FAQs.")
            faq_items_dict = []
        
        try:
            # Extract PAA items
            paa_list = context.parallel_results.get('paa_items') if context.parallel_results else None
            if paa_list:
                if hasattr(paa_list, 'to_dict_list'):
                    paa_items_dict = paa_list.to_dict_list()
                elif isinstance(paa_list, list):
                    paa_items_dict = paa_list
        except Exception as e:
            logger.warning(f"Failed to extract PAA items: {e}. Continuing without PAAs.")
            paa_items_dict = []
        
        # Generate article URL with error handling
        article_url = None
        try:
            headline = context.validated_article.get("Headline", "")
            company_url = context.company_data.get("company_url") if context.company_data else None
            article_url = self._generate_article_url(headline, company_url)
            if article_url:
                logger.debug(f"Generated article URL: {article_url}")
        except Exception as e:
            logger.warning(f"Failed to generate article URL: {e}. Continuing without URL.")
            article_url = None
        
        # OPTIMIZED: Parallelize HTML rendering and metadata extraction
        import asyncio
        
        logger.debug("Rendering HTML and extracting metadata in parallel...")
        
        # Prepare article dict for HTMLRenderer
        if paa_items_dict and not context.validated_article.get("paa_items"):
            context.validated_article["paa_items"] = paa_items_dict
        
        # Run HTML rendering and metadata extraction in parallel
        def render_html():
            try:
                html = HTMLRenderer.render(
                    article=context.validated_article,
                    company_data=context.company_data,
                    article_output=context.article_output,
                    article_url=article_url,
                    faq_items=faq_items_dict,
                )
                logger.info(f"   HTML rendered ({len(html)} bytes)")
                return html
            except Exception as e:
                logger.error(f"HTML rendering failed: {e}")
                # Fallback: render without AEO features
                try:
                    html = HTMLRenderer.render(
                        article=context.validated_article,
                        company_data=context.company_data,
                        article_output=None,
                        article_url=None,
                        faq_items=[],
                    )
                    logger.warning("HTML rendered with fallback (no AEO features)")
                    return html
                except Exception as e2:
                    logger.error(f"Fallback HTML rendering also failed: {e2}")
                    return f"<html><body><h1>Error rendering article</h1><p>{str(e2)}</p></body></html>"
        
        def extract_metadata():
            metadata = StorageProcessor.extract_metadata(context.validated_article)
            return metadata
        
        # Execute both in parallel
        html_content, metadata = await asyncio.gather(
            asyncio.to_thread(render_html),
            asyncio.to_thread(extract_metadata)
        )
        
        context.validated_article["metadata_extracted"] = metadata

        # Step 6: Store article
        logger.debug("Storing article...")
        success, storage_result = StorageProcessor.store(
            context.validated_article,
            context.job_id,
            html_content,
            storage_type="supabase",
        )

        # Step 7: Set final article and storage result
        context.final_article = context.validated_article
        context.final_article["html_content"] = html_content
        context.storage_result = {
            "success": success,
            **storage_result,
        }

        # Log completion
        if success:
            logger.info(f"✅ Article stored successfully")
            logger.info(f"   Job ID: {context.job_id}")
            logger.info(
                f"   Storage: {storage_result.get('storage_type', 'unknown')}"
            )
            headline = context.validated_article.get("Headline", "Unknown")
            logger.info(f"   Headline: {headline}")
            logger.info(
                f"   Quality: AEO={context.quality_report.get('metrics', {}).get('aeo_score', 0)}/100"
            )
        else:
            logger.error(f"❌ Storage failed: {storage_result.get('error', 'Unknown')}")

        return context

    @staticmethod
    def _generate_article_url(headline: str, company_url: Optional[str]) -> Optional[str]:
        """
        Generate article URL from headline and company URL.
        
        Args:
            headline: Article headline
            company_url: Company base URL
            
        Returns:
            Full article URL or None if company_url is missing
        """
        if not company_url or not headline:
            return None
        
        # ROOT-LEVEL FIX: Strip ALL HTML tags from headline before creating slug
        from html import unescape
        clean_headline = re.sub(r'<[^>]+>', '', headline)  # Remove HTML tags
        clean_headline = unescape(clean_headline)  # Unescape HTML entities
        
        # Create slug from clean headline
        slug = clean_headline.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)  # Remove special chars
        slug = re.sub(r'[-\s]+', '-', slug)   # Replace spaces with hyphens
        slug = slug.strip('-')
        
        # Ensure company_url doesn't end with /
        base_url = company_url.rstrip('/')
        return f"{base_url}/blog/{slug}"

    def __repr__(self) -> str:
        """String representation."""
        return f"StorageStage(stage_num={self.stage_num})"
