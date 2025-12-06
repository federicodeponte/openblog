"""
Stage 5: Internal Links Generation

Maps to v4.1 Phase 5, Steps 14-19: create-more-section → URL generation and formatting

Generates "More Reading" / "Related Links" suggestions based on article content.

Input:
  - ExecutionContext.structured_data (ArticleOutput with headline, sections)
  - ExecutionContext.job_config (company_data for context)

Output:
  - ExecutionContext.parallel_results['internal_links_html'] (formatted HTML)

Process:
1. Extract article topics (headline + section titles)
2. Generate internal link suggestions (topic-based)
3. Filter and deduplicate
4. Format as HTML
"""

import logging
import asyncio
from typing import List, Dict, Any
import httpx

from ..core import ExecutionContext, Stage
from ..models.internal_link import InternalLink, InternalLinkList

logger = logging.getLogger(__name__)


class InternalLinksStage(Stage):
    """
    Stage 5: Internal Links Generation.

    Handles:
    - Topic extraction from article
    - Link suggestion generation
    - Deduplication and filtering
    - HTML formatting
    """

    stage_num = 5
    stage_name = "Internal Links Generation"

    async def execute(self, context: ExecutionContext) -> ExecutionContext:
        """
        Execute Stage 5: Generate internal links.

        Input from context:
        - structured_data: ArticleOutput with headline and sections
        - job_config: Optional company context

        Output to context:
        - parallel_results['internal_links_html']: Formatted HTML

        Args:
            context: ExecutionContext from Stage 3

        Returns:
            Updated context with parallel_results populated
        """
        logger.info(f"Stage 5: {self.stage_name}")

        # Validate input
        if not context.structured_data:
            logger.warning("No structured_data available for internal links")
            context.parallel_results["internal_links_html"] = ""
            return context

        # Extract topics from article
        topics = self._extract_topics(context.structured_data)
        logger.info(f"Extracted {len(topics)} topics from article")

        # Generate link suggestions based on topics
        link_list = self._generate_suggestions(topics, context)
        logger.info(f"Generated {link_list.count()} initial link suggestions")

        # Validate URLs with HTTP HEAD checks
        logger.info(f"Validating {link_list.count()} internal link URLs...")
        validated_link_list = await self._validate_internal_link_urls(link_list, context)
        
        # Filter and optimize
        link_list = (
            validated_link_list.filter_valid()
            .sort_by_relevance()
            .deduplicate_domains()
            .limit(10)  # Keep top 10 links
        )

        logger.info(f"✅ Final link count: {link_list.count()}")
        for link in link_list.links:
            logger.debug(f"   {link.url} (relevance={link.relevance})")

        # Format as HTML
        internal_links_html = link_list.to_html()
        logger.info(f"   HTML size: {len(internal_links_html)} chars")

        # Store in context
        context.parallel_results["internal_links_html"] = internal_links_html
        context.parallel_results["internal_links_count"] = link_list.count()
        context.parallel_results["internal_links_list"] = link_list

        return context

    def _extract_topics(self, article) -> List[str]:
        """
        Extract topics from article.

        Uses headline and section titles to identify main topics.

        Args:
            article: ArticleOutput instance

        Returns:
            List of topic strings
        """
        topics = []

        # Add headline as primary topic
        if article.Headline:
            topics.append(article.Headline)

        # Add section titles
        section_titles = [
            article.section_01_title,
            article.section_02_title,
            article.section_03_title,
            article.section_04_title,
            article.section_05_title,
            article.section_06_title,
            article.section_07_title,
            article.section_08_title,
            article.section_09_title,
        ]

        for title in section_titles:
            if title and title.strip():
                topics.append(title.strip())

        logger.debug(f"Extracted topics: {topics}")
        return topics

    def _generate_suggestions(
        self, topics: List[str], context: ExecutionContext
    ) -> InternalLinkList:
        """
        Generate internal link suggestions.

        In v4.1, this would call an LLM or use a knowledge base to find
        related articles. Here we provide a simplified stub that can be
        extended with real link generation.

        Args:
            topics: List of article topics
            context: ExecutionContext for company data

        Returns:
            InternalLinkList with suggested links
        """
        link_list = InternalLinkList()

        # Get company data for context (to avoid competitor links)
        company_data = context.company_data or {}
        competitors = company_data.get("company_competitors", [])
        company_name = company_data.get("company_name", "")

        logger.debug(f"Generating suggestions for topics: {topics}")
        logger.debug(f"Avoiding competitors: {competitors}")

        # Check if sitemap_urls were provided in job_config
        sitemap_urls = context.job_config.get("sitemap_urls", []) if context.job_config else []
        
        # Get batch siblings for cross-linking within same batch
        batch_siblings = context.job_config.get("batch_siblings", []) if context.job_config else []
        
        # PRIORITIZE batch siblings - add them FIRST to the link pool
        batch_sibling_urls = []
        if batch_siblings:
            logger.info(f"Prioritizing {len(batch_siblings)} batch siblings for cross-linking")
            for sibling in batch_siblings:
                sibling_url = sibling.get("slug", "")
                sibling_title = sibling.get("title", "")
                sibling_keyword = sibling.get("keyword", "")
                if sibling_url:
                    batch_sibling_urls.append({
                        'url': sibling_url,
                        'title': sibling_title or sibling_url.split("/")[-1].replace("-", " ").title(),
                        'keyword': sibling_keyword,
                        'is_batch_sibling': True,
                    })
        
        # Merge batch sibling URLs into sitemap_urls pool (prioritized first)
        if batch_sibling_urls:
            for batch_item in batch_sibling_urls:
                if batch_item['url'] not in sitemap_urls:
                    sitemap_urls.insert(0, batch_item['url'])  # Insert at beginning for priority
        
        if sitemap_urls:
            # USE PROVIDED SITEMAP URLs (batch siblings prioritized)
            logger.info(f"Using {len(sitemap_urls)} provided sitemap URLs ({len(batch_sibling_urls)} batch siblings)")
            for i, url in enumerate(sitemap_urls[:10]):
                # Check if this is a batch sibling
                is_batch = any(item['url'] == url for item in batch_sibling_urls)
                batch_item = next((item for item in batch_sibling_urls if item['url'] == url), None)
                
                # Generate a title from the URL or use batch sibling title
                if batch_item:
                    title = batch_item['title']
                else:
                    title = url.split("/")[-1].replace("-", " ").title()
                    if not title:
                        title = "Related Content"
                
                # Higher relevance for batch siblings
                relevance = max(10 - i, 5) if not is_batch else max(10 - i + 2, 7)
                
                link_list.add_link(
                    url=url,
                    title=title if not is_batch else f"{title} (Related Article)",
                    relevance=relevance,
                    domain=url.split("/")[1] if "/" in url else "/blog/",
                )
            logger.info(f"Added {link_list.count()} links from sitemap_urls ({len(batch_sibling_urls)} batch siblings prioritized)")
            return link_list
        
        # FALLBACK: Generate placeholder links from topics
        logger.warning("No sitemap_urls provided, generating placeholders from topics")
        for i, topic in enumerate(topics[:5]):
            url_slug = topic.lower().replace(" ", "-").replace("?", "")
            url = f"/blog/{url_slug}"

            # Filter competitors
            skip = False
            for competitor in competitors:
                if competitor.lower() in topic.lower():
                    skip = True
                    break

            if skip:
                logger.debug(f"Skipping topic (competitor mentioned): {topic}")
                continue

            # Add link with relevance based on position
            relevance = max(10 - i, 5)  # Decreasing relevance for later topics
            link_list.add_link(
                url=url,
                title=f"Learn more about {topic}",
                relevance=relevance,
                domain="/blog/",
            )

        # Ensure minimum diversity (at least 3 different sources)
        # In real implementation, would fetch from internal knowledge base
        additional_links = [
            (
                "/blog/basics",
                "Getting Started Guide",
                7,
            ),
            (
                "/blog/best-practices",
                "Best Practices",
                6,
            ),
            (
                "/blog/case-studies",
                "Case Studies",
                5,
            ),
        ]

        for url, title, relevance in additional_links:
            link_list.add_link(url=url, title=title, relevance=relevance, domain="/blog/")

        logger.info(f"Generated {link_list.count()} initial suggestions")
        return link_list

    async def _validate_internal_link_urls(
        self, link_list: InternalLinkList, context: ExecutionContext
    ) -> InternalLinkList:
        """
        Validate internal link URLs with HTTP HEAD requests.
        
        Matches v4.1 behavior for internal link validation:
        - HTTP HEAD requests to check URL status
        - Remove URLs that return non-200 status codes
        - Parallel validation for performance
        
        Args:
            link_list: List of internal links to validate
            context: Execution context (for company URL base)
            
        Returns:
            InternalLinkList with only validated URLs
        """
        if not link_list.links:
            return link_list
        
        # Get company base URL for building full URLs
        company_url = context.company_data.get("company_url", "") if context.company_data else ""
        
        if not company_url:
            logger.warning("No company URL available for internal link validation")
            return link_list
        
        # Parse base URL
        from urllib.parse import urljoin, urlparse
        base_url = company_url.rstrip('/')
        
        # Validate links in parallel
        async def validate_single_link(link: InternalLink) -> InternalLink:
            """Validate a single internal link."""
            try:
                # Build full URL if relative
                if link.url.startswith('/'):
                    full_url = urljoin(base_url, link.url)
                else:
                    full_url = link.url
                
                # HTTP HEAD request with timeout
                async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                    response = await client.head(full_url)
                    
                    if response.status_code == 200:
                        logger.debug(f"✅ Internal link valid: {link.url}")
                        return link
                    else:
                        logger.warning(f"❌ Internal link invalid (HTTP {response.status_code}): {link.url}")
                        return None
                        
            except httpx.TimeoutException:
                logger.warning(f"❌ Internal link timeout: {link.url}")
                return None
            except httpx.RequestError as e:
                logger.warning(f"❌ Internal link error: {link.url} - {e}")
                return None
            except Exception as e:
                logger.warning(f"❌ Internal link validation failed: {link.url} - {e}")
                return None
        
        # Execute validations in parallel
        logger.info(f"Validating {len(link_list.links)} internal links against {base_url}")
        validation_tasks = [validate_single_link(link) for link in link_list.links]
        
        try:
            validated_results = await asyncio.gather(*validation_tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Internal link validation failed: {e}")
            return link_list  # Return original list on error
        
        # Filter out failed validations
        validated_links = []
        for result in validated_results:
            if isinstance(result, InternalLink):  # Successful validation
                validated_links.append(result)
            elif isinstance(result, Exception):
                logger.warning(f"Internal link validation exception: {result}")
        
        # Create new link list with validated links
        validated_link_list = InternalLinkList()
        for link in validated_links:
            validated_link_list.add_link(
                url=link.url,
                title=link.title,
                relevance=link.relevance,
                domain=link.domain
            )
        
        removed_count = len(link_list.links) - len(validated_links)
        if removed_count > 0:
            logger.warning(f"🔗 Internal link validation: {len(validated_links)} valid, {removed_count} removed (404/timeout)")
        else:
            logger.info(f"🔗 Internal link validation: All {len(validated_links)} links valid")
        
        return validated_link_list

    def __repr__(self) -> str:
        """String representation."""
        return f"InternalLinksStage(stage_num={self.stage_num})"
