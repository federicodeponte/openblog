"""
Smart Citation Validator

Intelligent citation validation with Gemini + web search:
- URL status validation with replacement
- Gemini-powered source quality analysis  
- Smart alternative source finding via web search
- Metadata quality analysis
- Author sanity checks
"""

import asyncio
import json
import logging
import re
import time
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass
from urllib.parse import urlparse
import httpx
import requests

from ..models.gemini_client import GeminiClient


logger = logging.getLogger(__name__)

# Performance cache for URL validation
_URL_STATUS_CACHE: Dict[str, Tuple[bool, str, float]] = {}
_CACHE_TTL = 300  # 5 minutes

# Forbidden hosts and domains
# NOTE: vertexaisearch.cloud.google.com is ALLOWED - it's Google's grounding redirect
# These URLs redirect (302) to real sources and are the correct way to cite grounding results
FORBIDDEN_HOSTS: Set[str] = {
    "example.com",
    "example.org",
    "placeholder.com"
}


@dataclass
class ValidationResult:
    """Result of citation validation"""
    is_valid: bool
    url: str
    title: str
    issues: List[str]
    validation_type: str  # 'original_url', 'fallback', 'failed'


@dataclass
class CitationValidationIssue:
    """Citation validation issue"""
    citation_id: str
    severity: str  # 'critical', 'warning', 'info'
    issue_type: str
    message: str
    citation_text: str


class SmartCitationValidator:
    """
    Smart citation validator with Gemini + web search replacement.
    
    Provides:
    - URL status validation
    - Gemini-powered alternative source finding
    - Smart citation replacement when URLs are broken
    - Metadata quality analysis
    - Author sanity checks
    """

    def __init__(
        self,
        gemini_client: Optional[GeminiClient] = None,
        timeout: float = 10.0,
        max_search_attempts: int = 3
    ):
        """
        Initialize smart citation validator.
        
        Args:
            gemini_client: Gemini client for web search and analysis
            timeout: HTTP request timeout in seconds
            max_search_attempts: Maximum attempts to find alternative sources
        """
        self.gemini_client = gemini_client
        self.timeout = timeout
        self.max_search_attempts = max_search_attempts
        
        # Async HTTP client for URL validation
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=3.0, read=timeout),
            follow_redirects=True,
            max_redirects=3
        )

    async def validate_citations_simple(
        self,
        citations: List[Dict[str, Any]],
        company_url: str = "",
        competitors: List[str] = None,
    ) -> List[ValidationResult]:
        """
        Simple validation of multiple citations in parallel.
        
        Args:
            citations: List of citation dictionaries
            company_url: Company URL for fallback
                competitors: List of competitor domains to avoid
            
        Returns:
            List of ValidationResult objects
        """
        if not citations:
            return []

        competitors = competitors or []
        
        logger.info(f"🔍 Starting simple validation of {len(citations)} citations")
        
        # Validate all citations in parallel for performance
        validation_tasks = [
            self.validate_single_citation(
                citation, company_url, competitors
            )
            for citation in citations
        ]
        
        results = await asyncio.gather(*validation_tasks, return_exceptions=True)
        
        # Handle any exceptions
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Citation {i} validation failed: {result}")
                # Create failed validation result
                citation = citations[i]
                valid_results.append(ValidationResult(
                    is_valid=False,
                    url=citation.get('url', ''),
                    title=citation.get('title', ''),
                    issues=[f"Validation failed: {str(result)}"],
                    validation_type='failed'
                ))
            else:
                valid_results.append(result)
        
        # Log validation summary
        valid_count = sum(1 for r in valid_results if r.is_valid)
        logger.info(f"✅ Citation validation complete: {valid_count}/{len(citations)} valid")
        
        return valid_results

    async def validate_single_citation(
        self,
        citation: Dict[str, Any],
        company_url: str,
        competitors: List[str]
    ) -> ValidationResult:
        """
        Validate a single citation simply.
        
        Process:
        1. Validate URL status
        2. Check metadata quality
        3. Check author sanity
        4. Return validation result
        """
        url = citation.get('url', '').strip()
        title = citation.get('title', '').strip()
        authors = citation.get('authors', [])
        doi = citation.get('doi', '').strip()
        
        issues = []
        
        # Step 1: Basic URL validation
        url_is_valid = False
        if url:
            status_code, error_msg = self.validate_url_status_simple(url)
            if status_code and 200 <= status_code < 400:
                url_is_valid = True
            else:
                if error_msg:
                    issues.append(f"URL validation failed: {error_msg}")
                if status_code:
                    issues.append(f"HTTP {status_code}")
        
        # Step 2: If URL is broken and we have Gemini, try to find alternative
        if not url_is_valid and self.gemini_client and title:
            logger.info(f"🔍 Searching for alternative source for: {title[:50]}...")
            alternative_url = await self._find_alternative_source(title, citation)
            if alternative_url:
                logger.info(f"✅ Found alternative: {alternative_url}")
                # Validate the alternative
                alt_status, alt_error = self.validate_url_status_simple(alternative_url)
                if alt_status and 200 <= alt_status < 400:
                    return ValidationResult(
                        is_valid=True,
                        url=alternative_url,
                        title=title,
                        issues=issues + [f"Original URL replaced: {url}"],
                        validation_type='alternative_found'
                    )
                else:
                    issues.append(f"Alternative URL also failed: {alt_error}")
            else:
                issues.append("No alternative source found")
        
        # Step 3: If original URL works, use it only
        
        # Step 2: Metadata quality checks
        metadata_issues = self.check_metadata_quality(citation)
        issues.extend(metadata_issues)
        
        # Step 3: Author sanity checks
        if authors:
            author_issues = self.check_author_sanity(authors)
            issues.extend(author_issues)
        
        if url_is_valid and not self._is_forbidden_or_competitor(url, competitors):
            return ValidationResult(
                is_valid=True,
                url=url,
                title=title,
                issues=issues,
                validation_type='original_url'
            )
        
        # Step 4: Final fallback - mark as invalid but preserve data
        return ValidationResult(
            is_valid=False,
            url=url or company_url,
            title=title or "Source unavailable",
            issues=issues + ["No valid URL found"],
            validation_type='fallback'
        )

    def validate_url_status_simple(self, url: str) -> Tuple[Optional[int], str]:
        """
        Simple URL validation (from OpenDraft - might be better than ours).
        
        Args:
            url: URL to validate
            
        Returns:
            Tuple of (status_code, error_message)
        """
        if not url:
            return None, "No URL provided"
        
        try:
            import requests
            response = requests.head(
                url,
                timeout=self.timeout,
                allow_redirects=True,
                headers={'User-Agent': 'OpenBlog Citation Validator'}
            )
            
            # Some servers block HEAD, try GET
            if response.status_code == 405:
                response = requests.get(url, timeout=self.timeout, allow_redirects=True)
            
            return response.status_code, ""
            
        except requests.exceptions.Timeout:
            return None, "Timeout"
        except requests.exceptions.ConnectionError:
            return None, "Connection failed"
        except requests.exceptions.RequestException as e:
            return None, f"Request error: {str(e)[:50]}"

    async def validate_url_simple_async(self, url: str) -> Tuple[bool, str, List[str]]:
        """
        Simple async URL validation with caching.
        
        Returns:
            Tuple of (is_valid, final_url, issues_list)
        """
        if not url:
            return False, "", ["No URL provided"]
        
        # Check cache
        cache_key = url
        if cache_key in _URL_STATUS_CACHE:
            is_valid, final_url, timestamp = _URL_STATUS_CACHE[cache_key]
            if time.time() - timestamp < _CACHE_TTL:
                return is_valid, final_url, []
        
        issues = []
        
        try:
            async with self.http_client as client:
                response = await client.head(url)
                
                # Some servers block HEAD requests, try GET
                if response.status_code == 405:
                    response = await client.get(url)
                
                is_valid = 200 <= response.status_code < 400
                final_url = str(response.url)
                
                if not is_valid:
                    issues.append(f"HTTP {response.status_code}")
                
                # Cache result
                _URL_STATUS_CACHE[cache_key] = (is_valid, final_url, time.time())
                
                return is_valid, final_url, issues
                
        except httpx.TimeoutException:
            issues.append("Request timeout")
            _URL_STATUS_CACHE[cache_key] = (False, url, time.time())
            return False, url, issues
            
        except Exception as e:
            issues.append(f"Request failed: {str(e)[:50]}")
            _URL_STATUS_CACHE[cache_key] = (False, url, time.time())
            return False, url, issues

    def check_metadata_quality(self, citation: Dict[str, Any]) -> List[str]:
        """
        Check citation metadata quality (from OpenDraft).
        
        Returns:
            List of quality issues found
        """
        issues = []
        title = citation.get('title', '')
        authors = citation.get('authors', [])
        url = citation.get('url', '')
        year = citation.get('year', 0)
        
        # Check 1: Title is domain name
        domain_pattern = r'^[a-zA-Z0-9.-]+\.(com|org|gov|edu|net|io|ai|co\.uk)(:443)?$'
        if re.match(domain_pattern, title, re.IGNORECASE):
            issues.append(f"Domain name as title: '{title}'")
        
        # Check 2: Author is same as title
        if authors and title and len(authors) > 0:
            if authors[0].strip().lower() == title.strip().lower():
                issues.append(f"Author duplicates title: '{authors[0]}'")
        
        # Check 3: URL contains error keywords
        error_keywords = ['error', '403', '404', '500', '503', 'not-found', 'forbidden']
        if url and any(keyword in url.lower() for keyword in error_keywords):
            issues.append(f"URL contains error keyword: '{url}'")
        
        # Check 4: Year validation
        if year and (year < 1990 or year > 2026):
            issues.append(f"Year out of range: {year}")
        
        # Check 5: Placeholder titles
        placeholder_titles = [
            'untitled', 'no title', 'unknown', '[title]', 'n/a', 'article', 'document'
        ]
        if title.lower().strip() in placeholder_titles:
            issues.append(f"Placeholder title: '{title}'")
        
        return issues

    def check_author_sanity(self, authors: List[str]) -> List[str]:
        """
        Check for suspicious author patterns (from OpenDraft).
        
        Returns:
            List of author-related issues
        """
        issues = []
        
        # Check for excessive authors
        MAX_REASONABLE_AUTHORS = 30
        if len(authors) > MAX_REASONABLE_AUTHORS:
            issues.append(f"Excessive authors ({len(authors)}) - likely malformed data")
            return issues
        
        for author in authors:
            # Repetitive initials pattern
            if re.match(r'^([A-Z]\.\s*){6,}$', author):
                issues.append(f"Repetitive initials pattern: '{author}'")
            
            # Domain name as author
            domain_pattern = r'^[a-zA-Z0-9.-]+\.(com|org|gov|edu|net|io|ai|co\.uk)$'
            if re.match(domain_pattern, author, re.IGNORECASE):
                issues.append(f"Domain name as author: '{author}'")
        
        return issues


    def _is_forbidden_or_competitor(self, url: str, competitors: List[str]) -> bool:
        """
        Check if URL is forbidden or from a competitor.
        
        Args:
            url: URL to check
            competitors: List of competitor domains
            
        Returns:
            True if URL should be avoided
        """
        if not url:
            return True
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Check forbidden hosts
            if domain in FORBIDDEN_HOSTS:
                return True
            
            # Check competitors
            for competitor in competitors:
                if competitor.lower() in domain:
                    return True
            
            return False
            
        except Exception:
            return True

    async def _find_alternative_source(self, title: str, citation: Dict[str, Any]) -> Optional[str]:
        """
        Use Gemini + web search to find alternative source when URL is broken.
        
        Args:
            title: Citation title to search for
            citation: Full citation dict for context
            
        Returns:
            Alternative URL if found, None otherwise
        """
        if not self.gemini_client:
            logger.warning("No Gemini client available for alternative source search")
            return None
        
        logger.info(f"🧠 Calling Gemini to find alternative for: {title[:100]}...")
            
        try:
            # Create search query from title
            search_query = self._create_search_query(title, citation)
            
            # Use Gemini with Google Search to find alternative sources
            prompt = f"""You are helping fix a broken citation. The original source is no longer available.

TASK: Find a high-quality alternative source for this content.

Citation Title: {title}
Authors: {citation.get('authors', [])}
Year: {citation.get('year', 'Unknown')}
Original URL: {citation.get('url', 'None')} (broken)

REQUIREMENTS:
1. Search for authoritative sources (.edu, .gov, .org, major publications)
2. Avoid blogs, personal websites, or low-quality sources
3. Prefer recent sources (2020+) unless historical context needed
4. Return ONLY the URL of the best alternative source
5. If no good alternative exists, return "NO_ALTERNATIVE_FOUND"

Search for: {search_query}"""

            # Use Gemini with web search enabled
            response = await self.gemini_client.generate_content(
                prompt,
                enable_tools=True  # Enable Google Search grounding
            )
            
            if response:
                potential_url = response.strip()
                
                # Validate that we got a URL
                if potential_url.startswith(('http://', 'https://')) and 'NO_ALTERNATIVE_FOUND' not in potential_url.upper():
                    return potential_url
                    
            return None
            
        except Exception as e:
            logger.warning(f"Alternative source search failed: {e}")
            return None

    def _create_search_query(self, title: str, citation: Dict[str, Any]) -> str:
        """
        Create optimized search query for finding alternative sources.
        
        Args:
            title: Citation title
            citation: Citation metadata
            
        Returns:
            Optimized search query string
        """
        # Start with title
        query_parts = [title]
        
        # Add authors if available
        authors = citation.get('authors', [])
        if authors and len(authors) > 0:
            # Use first author for search
            query_parts.append(authors[0])
        
        # Add year if available and recent
        year = citation.get('year')
        if year and year >= 2015:  # Only add year if somewhat recent
            query_parts.append(str(year))
        
        # Create final query
        search_query = ' '.join(query_parts)
        
        # Limit length and clean up
        if len(search_query) > 200:
            search_query = search_query[:200]
        
        return search_query.strip()

    async def close(self):
        """Close HTTP client."""
        if hasattr(self, 'http_client'):
            await self.http_client.aclose()


# Utility functions for backwards compatibility
def validate_citation_url_legacy(url: str, timeout: int = 10) -> Tuple[Optional[int], str]:
    """
    Legacy URL validation function for backwards compatibility.
    
    Returns:
        Tuple of (status_code, error_message)
    """
    if not url:
        return None, "No URL provided"
    
    try:
        response = requests.head(
            url,
            timeout=timeout,
            allow_redirects=True,
            headers={'User-Agent': 'OpenBlog Citation Validator'}
        )
        
        # Try GET if HEAD fails
        if response.status_code == 405:
            response = requests.get(url, timeout=timeout, allow_redirects=True)
        
        return response.status_code, ""
        
    except requests.exceptions.Timeout:
        return None, "Timeout"
    except requests.exceptions.ConnectionError:
        return None, "Connection failed"
    except requests.exceptions.RequestException as e:
        return None, f"Request error: {str(e)[:50]}"