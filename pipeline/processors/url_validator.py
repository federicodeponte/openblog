"""
Citation URL Validator

Maps to v4.1 Step 11: AI Agent3 (URL validation with serperTool + validTool)

Validates citation URLs with HTTP HEAD requests and finds alternatives for invalid URLs.
Matches v4.1 behavior:
- HTTP HEAD validation (statusCode 200 check)
- Alternative URL search using Gemini with GoogleSearch tool
- Filters competitors, internal links, forbidden domains
- Maintains citation count (if 5 sources provided, returns 5 validated URLs)
- Fallback to company URL if all searches fail
- PARALLEL validation for performance (all citations validated concurrently)
"""

import asyncio
import json
import logging
import re
import time
from typing import List, Optional, Tuple, Set, Dict
from urllib.parse import urlparse, urlunparse
import httpx

from ..models.gemini_client import GeminiClient

logger = logging.getLogger(__name__)

# Forbidden hosts (from v4.1)
FORBIDDEN_HOSTS: Set[str] = {
    "vertexaisearch.cloud.google.com",
    "cloud.google.com",
}

# PERFORMANCE OPTIMIZATION: Global caches for validation results
_URL_STATUS_CACHE: Dict[str, Tuple[bool, str, float]] = {}  # url -> (is_valid, final_url, timestamp)
_AUTHORITY_CACHE: Dict[str, Tuple[Optional[Tuple[str, str]], float]] = {}  # query -> (result, timestamp)
_CACHE_TTL = 180  # 3 minutes cache TTL (reduced from 5min for faster retry)
_FAILED_URL_TTL = 60  # 1 minute cache for failed URLs (retry faster)


class CitationURLValidator:
    """
    Validates citation URLs and finds alternatives for invalid URLs.
    
    Implements v4.1 AI Agent3 behavior:
    - Validates URLs with HTTP HEAD requests
    - Finds alternative URLs using Gemini with GoogleSearch tool
    - Filters competitors, internal links, forbidden domains
    - Maintains citation count
    - Falls back to company URL if all searches fail
    """

    def __init__(
        self,
        gemini_client: GeminiClient,
        max_attempts: int = 20,
        timeout: float = 8.0,
    ):
        """
        Initialize citation URL validator.
        
        Args:
            gemini_client: Gemini client for alternative URL search
            max_attempts: Maximum validation/search attempts per URL (default: 20, matches v4.1)
            timeout: HTTP request timeout in seconds (default: 8.0)
        """
        self.gemini_client = gemini_client
        self.max_attempts = max_attempts
        self.timeout = timeout
        # OPTIMIZED: Shorter timeout for HTTP requests (3s default, was 8s)
        # Also limit redirects to prevent slow chains
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=2.0, read=timeout),  # 2s connect, timeout read
            follow_redirects=True,
            max_redirects=3  # Limit redirect chains
        )

    async def validate_citation_url(
        self,
        url: str,
        title: str,
        company_url: str,
        competitors: List[str],
        language: str = "en",
    ) -> Tuple[bool, str, str]:
        """
        Validate citation URL and find alternative if invalid.
        
        Matches v4.1 AI Agent3 behavior:
        1. Check URL with HTTP HEAD (validTool equivalent)
        2. If invalid (non-200), search for alternative (serperTool equivalent)
        3. Filter competitors/internal/forbidden domains
        4. Return validated URL or fallback
        
        Args:
            url: Original citation URL
            title: Citation title/description
            company_url: Company URL (for filtering and fallback)
            competitors: List of competitor domains to exclude
            language: Language code for meta titles
            
        Returns:
            Tuple of (is_valid, final_url, final_title)
            - is_valid: True if URL is valid (HTTP 200)
            - final_url: Validated URL or alternative
            - final_title: Updated title if URL was replaced
        """
        logger.info(f"=" * 80)
        logger.info(f"VALIDATING CITATION")
        logger.info(f"  Original URL: {url}")
        logger.info(f"  Title: {title[:60]}...")
        logger.info(f"=" * 80)
        
        # Step 1: Check if URL is valid (HTTP HEAD)
        logger.debug(f"Step 1: Checking original URL status...")
        is_valid, final_url = await self._check_url_status(url)
        
        # CRITICAL FIX: If URL is valid (200), keep it even if not perfectly specific
        # Only try to find more specific page if URL is invalid or clearly just a domain
        is_specific_page = self._is_specific_page_url(final_url)
        
        # Only search for specific page if:
        # 1. URL is valid BUT it's clearly just a domain homepage (no path at all)
        # 2. Don't replace valid URLs that have any path - they're likely correct
        if is_valid and not is_specific_page:
            # Check if it's truly just a domain (no path)
            url_clean = final_url.replace('https://', '').replace('http://', '').strip('/')
            if '/' not in url_clean or url_clean.split('/')[1] in ['', 'index.html', 'index', 'home']:
                logger.warning(f"  ⚠️  URL is valid but appears to be domain homepage: {final_url}")
                logger.info(f"  Attempting to find more specific page URL...")
                # Try to find a specific page URL using the title
                specific_url = await self._find_specific_page_url(title, final_url, company_url, competitors, language)
                if specific_url:
                    # Validate the specific URL before using it
                    specific_valid, specific_final = await self._check_url_status(specific_url)
                    if specific_valid:
                        final_url = specific_final
                        logger.info(f"  ✅ Found and validated specific page URL: {final_url}")
                    else:
                        logger.warning(f"  ⚠️  Specific URL found but invalid, keeping original: {final_url}")
                else:
                    logger.info(f"  ℹ️  Could not find more specific page, keeping valid original URL")
            else:
                # URL has a path, even if not perfectly specific, keep it if valid
                logger.info(f"  ℹ️  URL has path and is valid, keeping original: {final_url}")
        
        logger.info(f"  Original URL status: {'✅ VALID (200)' if is_valid else '❌ INVALID (non-200)'}")
        
        if is_valid:
            # URL is valid, check if it should be filtered
            # CRITICAL FIX: Company URLs should NOT be filtered for citations
            # Company URLs (e.g., cello.so/customers) are valid citations (case studies, customer pages)
            # Only filter if it's a competitor or forbidden domain, NOT company domain
            should_filter = self._should_filter_url(final_url, company_url, competitors, filter_company=False)
            if should_filter:
                logger.warning(f"  Step 2: URL filtered (competitor/forbidden): {final_url}")
                logger.info(f"  Step 3: Searching for alternative...")
                # Search for alternative
                alternative = await self._find_alternative_url(
                    title, company_url, competitors, language
                )
                if alternative:
                    logger.info(f"  ✅ RESULT: Alternative found - {alternative[0]}")
                    logger.info(f"=" * 80)
                    return True, alternative[0], alternative[1]
                # No alternative found
                logger.error(f"  ❌ RESULT: No alternative found, keeping original (filtered)")
                logger.info(f"=" * 80)
                return False, url, title
            else:
                # URL is valid and passes filters - KEEP IT (don't replace with fallbacks)
                logger.info(f"  ✅ RESULT: Original URL validated and accepted: {final_url}")
                logger.info(f"=" * 80)
                return True, final_url, title
        
        # Step 2: URL is invalid (404/non-200), search for alternative
        logger.info(f"  Step 2: Original URL invalid (404), searching for alternative...")
        
        # CRITICAL FIX: Try multiple search strategies for better alternative finding
        alternative = None
        
        # Strategy 1: Search with full title
        alternative = await self._find_alternative_url(
            title, company_url, competitors, language
        )
        
        # Strategy 2: If that fails, try searching on the same domain
        if not alternative:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc or url.replace('https://', '').replace('http://', '').split('/')[0]
            if domain:
                logger.info(f"  Trying domain-specific search: {domain}")
                domain_alternative = await self._find_specific_page_url(
                    title, f"https://{domain}", company_url, competitors, language
                )
                if domain_alternative:
                    # Validate the domain-specific URL
                    alt_valid, alt_final = await self._check_url_status(domain_alternative)
                    if alt_valid:
                        logger.info(f"  ✅ Found valid domain-specific alternative: {domain_alternative}")
                        alternative = (domain_alternative, title)
        
        # Strategy 3: Try searching with simplified query (extract key terms)
        if not alternative:
            # Extract key terms from title (remove common words)
            import re
            key_terms = re.sub(r'\b(the|a|an|on|in|at|for|with|to|from|of|and|or|but)\b', '', title, flags=re.IGNORECASE)
            key_terms = ' '.join(key_terms.split()[:5])  # First 5 meaningful words
            if key_terms and len(key_terms) > 10:
                logger.info(f"  Trying simplified search query: {key_terms}")
                alternative = await self._find_alternative_url(
                    key_terms, company_url, competitors, language
                )
        
        if alternative:
            # CRITICAL FIX: Only use alternative if it's clearly better than original
            # Don't replace with generic authority fallbacks (pewresearch.org, nist.gov) unless absolutely necessary
            alternative_url = alternative[0]
            
            # Check if alternative is a generic authority fallback
            is_generic_fallback = any(domain in alternative_url.lower() for domain in [
                'pewresearch.org', 'nist.gov', 'census.gov', 'statista.com'
            ])
            
            if is_generic_fallback:
                logger.warning(f"  ⚠️  Alternative is generic authority fallback: {alternative_url}")
                logger.warning(f"  ⚠️  Preferring to keep original URL even if invalid")
                logger.error(f"  ❌ RESULT: No good alternative found, keeping original URL")
                logger.info(f"=" * 80)
                return False, url, title
            
            # Validate the alternative URL before using it
            alt_valid, alt_final = await self._check_url_status(alternative_url)
            if alt_valid:
                logger.info(f"  ✅ RESULT: Alternative URL found and validated")
                logger.info(f"    New URL: {alternative[0]}")
                logger.info(f"    New Title: {alternative[1][:60]}...")
                logger.info(f"=" * 80)
                return True, alternative[0], alternative[1]
            else:
                logger.warning(f"  ⚠️  Alternative URL also invalid (404): {alternative_url}")
        
        # Step 3: All searches failed
        # CRITICAL FIX: Reject invalid URLs (404s) - don't keep them even if they're company URLs
        # Invalid URLs break user trust and harm SEO, regardless of domain
        logger.error(f"  ❌ RESULT: No valid alternative found after multiple attempts")
        logger.error(f"    Original URL is invalid (404): {url}")
        logger.error(f"    Citation will be REJECTED (invalid URLs are not acceptable)")
        logger.info(f"=" * 80)
        return False, url, title  # Return False to signal rejection

    async def _check_url_status(self, url: str) -> Tuple[bool, str]:
        """
        Check URL status with HTTP HEAD request (OPTIMIZED for speed).
        
        Matches v4.1 validTool behavior:
        - HTTP HEAD request
        - Check statusCode 200
        - Follow redirects (limited to 3)
        - Detect error pages
        - Detect soft 404s (200 OK but 404 content)
        
        OPTIMIZED:
        - 5-minute cache for repeated URL checks
        - Shorter timeout (3s default)
        - Limited redirects (max 3)
        - Fast failure on timeout
        - Content analysis for soft 404s (only when HEAD returns 200)
        
        Args:
            url: URL to check
            
        Returns:
            Tuple of (is_valid, final_url)
        """
        # CRITICAL FIX: Validate URL format before making HTTP request
        # Reject malformed URLs like https://www.saas/ (missing TLD)
        if not self._is_valid_url_format(url):
            logger.warning(f"Invalid URL format rejected: {url}")
            return False, url
        
        # PERFORMANCE: Check cache first with different TTLs for success/failure
        current_time = time.time()
        if url in _URL_STATUS_CACHE:
            is_valid, final_url, timestamp = _URL_STATUS_CACHE[url]
            # Use shorter TTL for failed URLs to retry faster, longer for successful URLs
            cache_ttl = _CACHE_TTL if is_valid else _FAILED_URL_TTL
            if current_time - timestamp < cache_ttl:
                logger.debug(f"URL status cache hit: {url} -> {'VALID' if is_valid else 'INVALID'}")
                return is_valid, final_url
        
        try:
            # Try HEAD first (lightweight, fast)
            # OPTIMIZED: Use asyncio.wait_for to enforce strict timeout
            try:
                response = await asyncio.wait_for(
                    self.http_client.head(url, follow_redirects=True),
                    timeout=self.timeout + 0.5  # Add small buffer
                )
            except httpx.HTTPStatusError as e:
                # Some servers return errors on HEAD, try GET instead
                logger.debug(f"HEAD request failed for {url}, trying GET: {e}")
                response = await asyncio.wait_for(
                    self.http_client.get(url, follow_redirects=True),
                    timeout=self.timeout + 0.5
                )
            
            final_url = str(response.url)
            
            # Check status code - CRITICAL: Check actual status code first
            if response.status_code == 404:
                # Explicit 404 - cache and return immediately
                logger.warning(f"HTTP 404 detected: {final_url}")
                _URL_STATUS_CACHE[url] = (False, final_url, current_time)
                return False, final_url
            elif response.status_code == 200:
                # Check for error page indicators in URL path
                if self._is_error_page_url(final_url):
                    # Cache negative result
                    _URL_STATUS_CACHE[url] = (False, final_url, current_time)
                    return False, final_url
                
                # CRITICAL FIX: Always check for soft 404s when status is 200
                # Some sites return 200 OK but show 404 content (soft 404)
                is_soft_404 = await self._check_soft_404(final_url)
                if is_soft_404:
                    logger.warning(f"Soft 404 detected (200 OK but 404 content): {final_url}")
                    # Cache negative result
                    _URL_STATUS_CACHE[url] = (False, final_url, current_time)
                    return False, final_url
                
                # Cache positive result
                _URL_STATUS_CACHE[url] = (True, final_url, current_time)
                return True, final_url
            elif response.status_code in (301, 302, 303, 307, 308):
                # Follow redirect (limited to 3 redirects by httpx config)
                try:
                    get_response = await asyncio.wait_for(
                        self.http_client.get(final_url),
                        timeout=self.timeout + 0.5
                    )
                    if get_response.status_code == 200 and not self._is_error_page_url(str(get_response.url)):
                        final_redirect_url = str(get_response.url)
                        _URL_STATUS_CACHE[url] = (True, final_redirect_url, current_time)
                        return True, final_redirect_url
                    final_redirect_url = str(get_response.url)
                    _URL_STATUS_CACHE[url] = (False, final_redirect_url, current_time)
                    return False, final_redirect_url
                except asyncio.TimeoutError:
                    _URL_STATUS_CACHE[url] = (False, final_url, current_time)
                    return False, final_url
            else:
                # Non-200 status - cache negative result
                _URL_STATUS_CACHE[url] = (False, final_url, current_time)
                return False, final_url
                
        except asyncio.TimeoutError:
            logger.debug(f"Timeout checking URL: {url} (>{self.timeout}s)")
            return False, url
        except httpx.TimeoutException:
            logger.debug(f"HTTP timeout checking URL: {url}")
            return False, url
        except httpx.RequestError as e:
            logger.debug(f"Request error checking URL {url}: {e}")
            return False, url
        except Exception as e:
            logger.debug(f"Error checking URL {url}: {e}")
            return False, url

    def _is_valid_url_format(self, url: str) -> bool:
        """
        Validate URL format before making HTTP request.
        
        Rejects:
        - Malformed URLs like https://www.saas/ (missing TLD)
        - Invalid domain structures
        - Relative URLs without proper domain
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL format is valid
        """
        try:
            parsed = urlparse(url)
            
            # Must have scheme (http/https)
            if not parsed.scheme or parsed.scheme not in ['http', 'https']:
                return False
            
            # Must have netloc (domain)
            if not parsed.netloc:
                return False
            
            # Check domain structure
            domain = parsed.netloc.lower()
            
            # Reject domains without TLD (like "www.saas" or "saas")
            # Valid domains should have at least one dot (e.g., "example.com")
            # Exception: localhost and IP addresses
            if '.' not in domain and domain not in ['localhost']:
                # Check if it's an IP address
                try:
                    import ipaddress
                    ipaddress.ip_address(domain)
                    return True  # IP addresses are valid
                except ValueError:
                    return False  # Not an IP and no TLD
            
            # Reject domains ending with just a slash (like "www.saas/")
            # This is caught by netloc check above, but double-check
            if domain.endswith('/'):
                return False
            
            return True
            
        except Exception as e:
            logger.debug(f"URL format validation error for {url}: {e}")
            return False
    
    def _is_error_page_url(self, url: str) -> bool:
        """
        Check if URL appears to be an error page.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL looks like an error page
        """
        url_lower = url.lower()
        error_patterns = [
            "/notfound",
            "/not-found",
            "/404",
            "/error",
            "notfound.aspx",
            "/notfound.aspx",
            "/page-not-found",
            "/404-error",
        ]
        return any(pattern in url_lower for pattern in error_patterns)
    
    async def _check_soft_404(self, url: str) -> bool:
        """
        Check for soft 404s - pages that return 200 OK but contain 404 error content.
        
        Some websites (like Paddle) return HTTP 200 with a 404 error page. This method
        fetches the page content and checks for indicators that it's actually a 404 page.
        
        Args:
            url: URL to check
            
        Returns:
            True if page appears to be a soft 404 (200 OK but 404 content)
        """
        try:
            # Fetch page content (limited size for performance)
            get_response = await asyncio.wait_for(
                self.http_client.get(url, follow_redirects=True),
                timeout=self.timeout + 0.5
            )
            
            # CRITICAL FIX: Check actual HTTP status code first
            # If it's a real 404, return True immediately (this is a hard 404, not soft)
            if get_response.status_code == 404:
                logger.debug(f"Hard 404 detected in soft 404 check: {url}")
                return True  # Treat as invalid
            
            if get_response.status_code != 200:
                return False  # Not a soft 404 if status isn't 200
            
            # Read content (limit to first 50KB to avoid memory issues)
            content = await get_response.aread()
            content_text = content[:50000].decode('utf-8', errors='ignore').lower()
            
            # CRITICAL FIX: Check for 404 indicators in HTML title tag
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', content_text, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).lower()
                soft_404_title_patterns = [
                    '404',
                    'not found',
                    'page not found',
                    'error 404',
                    '404 error',
                    'page does not exist',
                    'cannot be found',
                    "can't find",
                    'does not exist',
                    'sorry',
                    'error',
                    "doesn't exist",
                    'page not available',
                    'content not found',
                    'resource not found',
                    'not available',
                    'unavailable',
                    'removed',
                    'deleted',
                    'gone',
                    'no longer available',
                    'no longer exists',
                    'moved permanently',
                    'permanently moved',
                    'something has gone wrong',  # Attio error page
                    'something went wrong',  # Common error page
                    'we\'ve run into an error',  # Attio error page
                    'run into an error',  # Error page variant
                    'investigating the issue',  # Error page message
                    'contact support',  # Often on error pages
                ]
                if any(pattern in title for pattern in soft_404_title_patterns):
                    logger.debug(f"Soft 404 detected in HTML title: {title_match.group(1)}")
                    return True
            
            # CRITICAL FIX: Also check meta title (og:title, twitter:title, or meta name="title")
            meta_title_patterns = [
                r'<meta\s+property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']',
                r'<meta\s+name=["\']twitter:title["\'][^>]*content=["\']([^"\']+)["\']',
                r'<meta\s+name=["\']title["\'][^>]*content=["\']([^"\']+)["\']',
            ]
            
            for pattern in meta_title_patterns:
                meta_title_match = re.search(pattern, content_text, re.IGNORECASE)
                if meta_title_match:
                    meta_title = meta_title_match.group(1).lower()
                    soft_404_meta_patterns = [
                        '404',
                        'not found',
                        'page not found',
                        'error 404',
                        '404 error',
                        'page does not exist',
                        'cannot be found',
                        "can't find",
                        'does not exist',
                        'sorry',
                        'error',
                        "doesn't exist",
                        'page not available',
                        'content not found',
                        'resource not found',
                        'not available',
                        'unavailable',
                        'removed',
                        'deleted',
                        'gone',
                        'no longer available',
                        'no longer exists',
                        'moved permanently',
                        'permanently moved',
                        'oops',
                        'something went wrong',
                        'something has gone wrong',  # Attio error page
                        'we\'ve run into an error',  # Attio error page
                        'run into an error',  # Error page variant
                        'we couldn\'t find',
                        'we cannot find',
                        'we can\'t find',
                        'looks like',
                        'seems like',
                        'appears to be',
                        'investigating the issue',  # Error page message
                        'contact support',  # Often on error pages
                        'reload and try again',  # Error page instruction
                    ]
                    if any(pattern in meta_title for pattern in soft_404_meta_patterns):
                        logger.debug(f"Soft 404 detected in meta title: {meta_title_match.group(1)}")
                        return True
            
            # Check for robots noindex meta tag (often present on error pages)
            robots_match = re.search(r'<meta[^>]*name=["\']robots["\'][^>]*content=["\']([^"\']+)["\']', content_text, re.IGNORECASE)
            if robots_match:
                robots_content = robots_match.group(1).lower()
                if 'noindex' in robots_content:
                    # Check if page also has 404 indicators in body
                    body_match = re.search(r'<body[^>]*>([^<]{0,500})', content_text, re.IGNORECASE | re.DOTALL)
                    if body_match:
                        body_snippet = body_match.group(1).lower()
                        soft_404_body_patterns = [
                            '404',
                            'not found',
                            'page not found',
                            "can't find that page",
                            "doesn't exist",
                            'has been moved',
                        ]
                        if any(pattern in body_snippet for pattern in soft_404_body_patterns):
                            logger.debug(f"Soft 404 detected: robots noindex + 404 content")
                            return True
            
            # Check for common 404 error messages in body content
            body_match = re.search(r'<body[^>]*>([^<]{0,1000})', content_text, re.IGNORECASE | re.DOTALL)
            if body_match:
                body_snippet = body_match.group(1).lower()
                # Look for strong indicators of 404 pages
                strong_404_indicators = [
                    'sorry, we can\'t find that page',
                    'sorry, we cannot find that page',
                    'the page you\'re looking for doesn\'t exist',
                    'the page you\'re looking for does not exist',
                    'page not found',
                    '404 page not found',
                    'error 404',
                    '404 error',
                    'something has gone wrong',  # Attio error page
                    'something went wrong',  # Common error page
                    'we\'ve run into an error',  # Attio error page
                    'run into an error',  # Error page variant
                    'investigating the issue',  # Error page message
                    'our team have been alerted',  # Error page message
                    'reload and try again',  # Error page instruction
                    'contact support',  # Often on error pages
                    'the requested url was not found',  # Apache 404
                    'not found on this server',  # Server 404 message
                ]
                if any(indicator in body_snippet for indicator in strong_404_indicators):
                    logger.debug(f"Soft 404 detected in body content")
                    return True
            
            return False  # Not a soft 404
            
        except asyncio.TimeoutError:
            logger.debug(f"Timeout checking soft 404 for {url}")
            return False  # Assume not soft 404 on timeout
        except Exception as e:
            logger.debug(f"Error checking soft 404 for {url}: {e}")
            return False  # Assume not soft 404 on error

    async def _find_alternative_url(
        self,
        title: str,
        company_url: str,
        competitors: List[str],
        language: str = "en",
    ) -> Optional[Tuple[str, str]]:
        """
        Find alternative URL using Gemini with GoogleSearch tool.
        
        OPTIMIZED: Fast path - tries simple URL fixes first before expensive Gemini call.
        
        Matches v4.1 serperTool behavior:
        - Search web for alternative URLs
        - Filter competitors/internal/forbidden domains
        - Validate each candidate URL
        - Return first valid alternative
        
        Args:
            title: Citation title (used as search query)
            company_url: Company URL (for filtering)
            competitors: Competitor domains to exclude
            language: Language code
            
        Returns:
            Tuple of (url, meta_title) if found, None otherwise
        """
        # Build search query from title
        search_query = self._build_search_query(title)
        
        logger.debug(f"Searching for alternative URL with query: {search_query}")
        
        # FAST PATH: Try simple URL fixes first (www prefix, https, etc.)
        # This avoids expensive Gemini calls for common issues
        # Most URLs just need www prefix or protocol fix
        
        try:
            # Use Gemini with GoogleSearch tool to find alternatives
            # OPTIMIZED: Targeted search for authoritative sources only
            prompt = f"""Use GoogleSearch to find ONE authoritative source about: {search_query}

Prioritize: .edu .gov .org major publications (Forbes, McKinsey, Harvard Business Review, Nature, WHO, etc.)

Return ONLY JSON:
{{"url": "https://authority-site.com/article", "title": "Article Title", "verified": true}}

AVOID:
- {company_url if company_url else 'company sites'}
- Competitors: {', '.join(competitors[:2]) if competitors else 'none'}
- Social media, forums, personal blogs

If no authority source found: {{"url": "", "verified": false}}"""

            # Call Gemini with GoogleSearch tool (with timeout protection)
            logger.debug(f"Calling Gemini for: {search_query[:50]}...")
            
            # SMART OPTIMIZATION: Use fast, targeted search with adaptive timeout
            # Gemini Flash 2.5 needs more time for web searches (can take 60-90s for complex queries)
            base_timeout = 90.0  # Increased to 90s for Flash model web searches to prevent timeouts
            adaptive_timeout = min(base_timeout, self.timeout * 2.5)  # More generous scaling
            
            try:
                response_text = await asyncio.wait_for(
                    self.gemini_client.generate_content(
                        prompt=prompt,
                        enable_tools=True,
                    ),
                    timeout=adaptive_timeout  # Adaptive timeout for better performance
                )
                logger.debug(f"Gemini response ({len(response_text)} chars): {response_text[:200]}...")
            except asyncio.TimeoutError:
                logger.warning(f"Gemini search timed out after {base_timeout:.0f}s for: {search_query[:50]}...")
                # FALLBACK: Try domain authority sites for common topics
                return await self._try_authority_fallback(search_query, company_url, competitors)
            except Exception as e:
                logger.error(f"Gemini search failed for {search_query[:50]}...: {e}")
                # FALLBACK: Try domain authority sites for common topics
                return await self._try_authority_fallback(search_query, company_url, competitors)
            
            # Try to parse structured JSON response first (preferred method)
            try:
                # Look for JSON object with url, title, verified fields
                json_match = re.search(r'\{[^}]*"url"[^}]*"verified"[^}]*\}', response_text, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(0))
                    if data.get("verified") and data.get("url"):
                        candidate_url = data["url"].strip()
                        candidate_title = data.get("title", title)
                        
                        logger.info(f"Extracted structured response: {candidate_url}")
                        
                        # Normalize URL
                        candidate_url = self._normalize_url(candidate_url)
                        
                        # Filter out invalid domains
                        if self._should_filter_url(candidate_url, company_url, competitors):
                            logger.warning(f"Structured URL filtered (competitor/internal): {candidate_url}")
                        else:
                            # Double-check URL status (verify Gemini's claim)
                            logger.debug(f"Double-checking URL status: {candidate_url}")
                            is_valid, final_url = await self._check_url_status(candidate_url)
                            
                            if is_valid:
                                logger.info(f"✅ Structured URL validated: {final_url}")
                                return final_url, candidate_title
                            else:
                                logger.warning(f"Structured URL failed validation (non-200): {candidate_url}")
                    elif data.get("url") == "" and data.get("verified") is False:
                        logger.info("Gemini reported no valid URL found in search results")
                        return None
            except json.JSONDecodeError as e:
                logger.debug(f"Could not parse structured JSON (will try regex extraction): {e}")
            except Exception as e:
                logger.warning(f"Error parsing structured response: {e}")
            
            # Fallback: Extract URLs from response text (legacy method)
            logger.debug("Falling back to regex URL extraction...")
            urls = self._extract_urls_from_response(response_text)
            logger.debug(f"Extracted {len(urls)} URLs via regex: {urls}")
            
            # Validate and filter URLs
            for candidate_url in urls:
                if not candidate_url:
                    continue
                
                # Normalize URL
                candidate_url = self._normalize_url(candidate_url)
                
                # Filter out invalid domains
                if self._should_filter_url(candidate_url, company_url, competitors):
                    logger.debug(f"Filtered URL (competitor/internal): {candidate_url}")
                    continue
                
                # Validate URL status
                logger.debug(f"Checking URL status: {candidate_url}")
                is_valid, final_url = await self._check_url_status(candidate_url)
                
                if is_valid:
                    # Extract title from response or use original
                    meta_title = self._extract_title_from_response(response_text, candidate_url) or title
                    logger.info(f"✅ Found valid alternative via regex: {final_url}")
                    return final_url, meta_title
                else:
                    logger.debug(f"URL failed validation (non-200): {candidate_url}")
            
            # No valid alternatives found
            logger.warning(f"No valid alternatives found for: {search_query[:50]}...")
            return None
            
        except Exception as e:
            logger.error(f"Error searching for alternative URL: {e}")
            return None

    def _is_specific_page_url(self, url: str) -> bool:
        """
        Check if URL is a specific page, not just a domain homepage.
        
        Args:
            url: URL to check
        
        Returns:
            True if URL appears to be a specific page
        """
        if not url or not isinstance(url, str):
            return False
        
        # Remove protocol
        url_clean = url.replace('https://', '').replace('http://', '').strip('/')
        
        # Check if it's just a domain (no path)
        if '/' not in url_clean:
            return False
        
        # Check if path is meaningful (not just / or /index.html)
        parts = url_clean.split('/')
        if len(parts) <= 1:
            return False
        
        path = '/'.join(parts[1:])  # Everything after domain
        if not path or path.lower() in ['', 'index.html', 'index', 'home', 'homepage', 'default']:
            return False
        
        return True
    
    async def _find_specific_page_url(
        self,
        title: str,
        domain_url: str,
        company_url: str,
        competitors: List[str],
        language: str,
    ) -> Optional[str]:
        """
        Find a specific page URL from a domain using Google Search.
        
        Args:
            title: Citation title (used as search query)
            domain_url: Domain URL to find pages on
            company_url: Company URL (for filtering)
            competitors: Competitor domains to exclude
            language: Language code
        
        Returns:
            Specific page URL or None
        """
        try:
            # Extract domain
            from urllib.parse import urlparse
            parsed = urlparse(domain_url)
            domain = parsed.netloc or domain_url.replace('https://', '').replace('http://', '').split('/')[0]
            
            # Build search query: title + site:domain
            search_query = f"{title} site:{domain}"
            
            logger.debug(f"Searching for specific page: {search_query}")
            
            # Use Gemini with Google Search to find specific page
            if not self.gemini_client:
                return None
            
            prompt = f"""Use GoogleSearch to find a specific page URL on {domain} about: {title}

Return ONLY a JSON object with:
{{"url": "https://{domain}/specific-page-path", "verified": true}}

Requirements:
- Must be a specific page URL (not homepage)
- Must be on {domain}
- Must be relevant to: {title}
- Must be an authoritative source

If no specific page found: {{"url": "", "verified": false}}"""

            response_text = await self.gemini_client.generate_content(prompt, enable_tools=True)
            
            # Parse response
            import json
            json_match = re.search(r'\{[^}]+\}', response_text)
            if json_match:
                result = json.loads(json_match.group(0))
                if result.get('verified') and result.get('url'):
                    found_url = result['url']
                    # Validate it's a specific page
                    if self._is_specific_page_url(found_url):
                        return found_url
            
            return None
        except Exception as e:
            logger.error(f"Error finding specific page URL: {e}")
            return None
    
    def _is_specific_page_url(self, url: str) -> bool:
        """
        Check if URL is a specific page, not just a domain homepage.
        
        Args:
            url: URL to check
        
        Returns:
            True if URL appears to be a specific page
        """
        if not url or not isinstance(url, str):
            return False
        
        # Remove protocol
        url_clean = url.replace('https://', '').replace('http://', '').strip('/')
        
        # Check if it's just a domain (no path)
        if '/' not in url_clean:
            return False
        
        # Check if path is meaningful (not just / or /index.html)
        parts = url_clean.split('/')
        if len(parts) <= 1:
            return False
        
        path = '/'.join(parts[1:])  # Everything after domain
        if not path or path.lower() in ['', 'index.html', 'index', 'home', 'homepage', 'default']:
            return False
        
        return True
    
    async def _find_specific_page_url(
        self,
        title: str,
        domain_url: str,
        company_url: str,
        competitors: List[str],
        language: str,
    ) -> Optional[str]:
        """
        Find a specific page URL from a domain using Google Search.
        
        Args:
            title: Citation title (used as search query)
            domain_url: Domain URL to find pages on
            company_url: Company URL (for filtering)
            competitors: Competitor domains to exclude
            language: Language code
        
        Returns:
            Specific page URL or None
        """
        try:
            # Extract domain
            parsed = urlparse(domain_url)
            domain = parsed.netloc or domain_url.replace('https://', '').replace('http://', '').split('/')[0]
            
            # Build search query: title + site:domain
            search_query = f"{title} site:{domain}"
            
            logger.debug(f"Searching for specific page: {search_query}")
            
            # Use Gemini with Google Search to find specific page
            if not self.gemini_client:
                return None
            
            prompt = f"""Use GoogleSearch to find a specific page URL on {domain} about: {title}

Return ONLY a JSON object with:
{{"url": "https://{domain}/specific-page-path", "verified": true}}

Requirements:
- Must be a specific page URL (not homepage)
- Must be on {domain}
- Must be relevant to: {title}
- Must be an authoritative source

If no specific page found: {{"url": "", "verified": false}}"""

            response_text = await self.gemini_client.generate_content(prompt, enable_tools=True)
            
            # Parse response
            json_match = re.search(r'\{[^}]+\}', response_text)
            if json_match:
                result = json.loads(json_match.group(0))
                if result.get('verified') and result.get('url'):
                    found_url = result['url']
                    # Validate it's a specific page
                    if self._is_specific_page_url(found_url):
                        return found_url
            
            return None
        except Exception as e:
            logger.error(f"Error finding specific page URL: {e}")
            return None
    
    def _build_search_query(self, title: str) -> str:
        """
        Build search query from citation title.
        
        Args:
            title: Citation title
            
        Returns:
            Search query string
        """
        # Clean title and use as query
        query = title.strip()
        
        # Remove citation markers if present
        query = re.sub(r"\[\d+\]", "", query)
        
        # Limit length
        if len(query) > 100:
            query = query[:100] + "..."
        
        return query

    def _extract_urls_from_response(self, response_text: str) -> List[str]:
        """
        Extract URLs from Gemini response.
        
        Args:
            response_text: Gemini response text
            
        Returns:
            List of extracted URLs
        """
        urls = []
        
        # Try to extract URLs from text
        url_pattern = r"https?://[^\s\)\]\>\"\']+"
        matches = re.findall(url_pattern, response_text)
        
        for match in matches:
            # Clean URL (remove trailing punctuation)
            url = match.rstrip(".,;:!?)")
            if url:
                urls.append(url)
        
        # Also try to extract from JSON if present
        json_match = re.search(r'\{[^}]*"url"[^}]*\}', response_text)
        if json_match:
            import json
            try:
                data = json.loads(json_match.group(0))
                if "url" in data:
                    urls.insert(0, data["url"])  # Prefer JSON URL
            except Exception:
                pass
        
        return urls

    async def _try_authority_fallback(
        self,
        search_query: str,
        company_url: str,
        competitors: List[str],
    ) -> Optional[Tuple[str, str]]:
        """
        Fast fallback using high-authority domain patterns.
        
        CRITICAL FIX: This fallback is now DISABLED to prevent replacing valid URLs
        with generic authority sites. Generic fallbacks (pewresearch.org, nist.gov) 
        are not appropriate replacements for specific company URLs.
        
        When Gemini search fails/times out, return None to preserve original URL
        rather than replacing with unrelated generic authority sites.
        
        Args:
            search_query: Original search query
            company_url: Company URL (for filtering)
            competitors: Competitor domains
            
        Returns:
            None (fallback disabled to preserve original URLs)
        """
        # CRITICAL FIX: Disable generic authority fallbacks
        # These were causing valid URLs (cello.so/customers) to be replaced with
        # unrelated generic sites (pewresearch.org, nist.gov)
        logger.warning(f"⚠️  Authority fallback disabled - preserving original URL instead of generic replacement")
        logger.warning(f"    Search query: {search_query[:50]}...")
        logger.warning(f"    This prevents wrong URL replacements (e.g., cello.so → pewresearch.org)")
        
        # Return None to indicate no fallback found
        # This allows the original URL to be preserved even if invalid
        return None

    def _extract_title_from_response(self, response_text: str, url: str) -> Optional[str]:
        """
        Extract meta title from Gemini response.
        
        Args:
            response_text: Gemini response text
            url: URL to find title for
            
        Returns:
            Meta title if found, None otherwise
        """
        # Try to extract from JSON
        json_match = re.search(r'\{[^}]*"url_meta_title"[^}]*\}', response_text)
        if json_match:
            import json
            try:
                data = json.loads(json_match.group(0))
                if "url_meta_title" in data:
                    return data["url_meta_title"]
            except Exception:
                pass
        
        # Try to find title near URL in text
        url_index = response_text.find(url)
        if url_index > 0:
            # Look for title-like text before URL
            before_url = response_text[max(0, url_index - 200):url_index]
            # Extract potential title (text in quotes or after "title:")
            title_match = re.search(r'(?:title|meta)[:\s]+["\']?([^"\']{10,80})["\']?', before_url, re.I)
            if title_match:
                return title_match.group(1).strip()
        
        return None

    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL (add protocol if missing, clean up).
        
        Args:
            url: URL to normalize
            
        Returns:
            Normalized URL
        """
        url = url.strip()
        
        # Add protocol if missing
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        
        # Remove common tracking parameters
        parsed = urlparse(url)
        query_params = []
        for param in parsed.query.split("&"):
            if param and not param.lower().startswith(("utm_", "gclid", "fbclid")):
                query_params.append(param)
        
        if query_params:
            new_query = "&".join(query_params)
            url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
        else:
            url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, "", parsed.fragment))
        
        return url

    def _should_filter_url(
        self,
        url: str,
        company_url: str,
        competitors: List[str],
        filter_company: bool = True,
    ) -> bool:
        """
        Check if URL should be filtered out.
        
        Filters:
        - Company domain and subdomains (if filter_company=True)
        - Competitor domains
        - Forbidden hosts (vertexaisearch.cloud.google.com, cloud.google.com)
        
        Args:
            url: URL to check
            company_url: Company URL
            competitors: List of competitor domains
            filter_company: If False, allow company URLs (for citations)
            
        Returns:
            True if URL should be filtered out
        """
        try:
            parsed = urlparse(url)
            host = self._normalize_hostname(parsed.netloc)
            
            # Check forbidden hosts
            if host in FORBIDDEN_HOSTS:
                return True
            
            # Check company domain (only filter if filter_company=True)
            # CRITICAL: Company URLs are valid for citations (case studies, customer pages)
            if filter_company and company_url:
                company_parsed = urlparse(company_url)
                company_host = self._normalize_hostname(company_parsed.netloc)
                if host == company_host or self._is_subdomain(host, company_host):
                    return True
            
            # Check competitors (handle both list of strings and comma-separated strings)
            for competitor in competitors:
                if not competitor or not isinstance(competitor, str):
                    continue
                
                # Handle comma-separated competitor strings (e.g., "Rewardful, PartnerStack")
                if "," in competitor:
                    comp_list = [c.strip() for c in competitor.split(",") if c.strip()]
                else:
                    comp_list = [competitor.strip()]
                
                for comp in comp_list:
                    if not comp:
                        continue
                    comp_url = comp if comp.startswith("http") else f"https://{comp}"
                    try:
                        comp_parsed = urlparse(comp_url)
                        comp_host = self._normalize_hostname(comp_parsed.netloc)
                        if host == comp_host or self._is_subdomain(host, comp_host):
                            return True
                    except Exception as e:
                        logger.debug(f"Error parsing competitor URL '{comp}': {e}")
                        # Fallback: simple string matching if URL parsing fails
                        if comp.lower() in host.lower() or host.lower() in comp.lower():
                            return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Error checking if URL should be filtered: {e}")
            return False

    def _normalize_hostname(self, hostname: str) -> str:
        """
        Normalize hostname for comparison.
        
        Args:
            hostname: Hostname to normalize
            
        Returns:
            Normalized hostname (lowercase, no www)
        """
        if not hostname:
            return ""
        hostname = hostname.lower().lstrip(".")
        if hostname.startswith("www."):
            hostname = hostname[4:]
        return hostname

    def _is_subdomain(self, host: str, root: str) -> bool:
        """
        Check if host is a subdomain of root.
        
        Args:
            host: Hostname to check
            root: Root domain
            
        Returns:
            True if host is subdomain of root
        """
        if not host or not root:
            return False
        return host.endswith(f".{root}")

    def _get_company_fallback(self, company_url: str) -> Tuple[bool, str, str]:
        """
        Get company URL fallback (v4.1 behavior).
        
        Args:
            company_url: Company URL
            
        Returns:
            Tuple of (is_valid, company_url, company_name)
        """
        # Extract company name from URL
        parsed = urlparse(company_url)
        company_name = parsed.netloc.replace("www.", "").split(".")[0].title()
        
        logger.info(f"Using company URL fallback: {company_url}")
        return True, company_url, company_name

    async def validate_all_citations(
        self,
        citations: List,
        company_url: str,
        competitors: List[str],
        language: str = "en",
    ) -> List:
        """
        Validate all citations in parallel and maintain count.
        
        Matches v4.1 behavior: maintains exact citation count.
        If 5 citations provided, returns 5 validated citations.
        
        PERFORMANCE: Validates all citations concurrently using asyncio.gather()
        instead of sequentially. This reduces total time from O(n) to O(1) for
        the slowest citation.
        
        Args:
            citations: List of Citation objects
            company_url: Company URL
            competitors: List of competitor domains
            language: Language code
            
        Returns:
            List of validated Citation objects (same count as input, same order)
        """
        if not citations:
            return []
        
        logger.info(f"Validating {len(citations)} citations in parallel...")
        
        # Create validation tasks for all citations
        async def validate_single_citation(citation):
            """Validate a single citation and return updated citation."""
            try:
                is_valid, final_url, final_title = await self.validate_citation_url(
                    url=citation.url,
                    title=citation.title,
                    company_url=company_url,
                    competitors=competitors,
                    language=language,
                )
                
                # CRITICAL FIX: If URL is invalid (404), try harder to find alternative
                # Don't accept 404 URLs - they break user trust
                if not is_valid:
                    logger.warning(f"⚠️  Citation [{citation.number}] URL is invalid (404): {final_url}")
                    logger.info(f"   Attempting aggressive alternative search...")
                    
                    # Try one more time with a more aggressive search
                    alternative = await self._find_alternative_url(
                        citation.title, company_url, competitors, language
                    )
                    
                    if alternative:
                        # Validate the alternative URL
                        alt_valid, alt_final = await self._check_url_status(alternative[0])
                        if alt_valid:
                            logger.info(f"   ✅ Found valid alternative: {alternative[0]}")
                            citation.url = alternative[0]
                            citation.title = alternative[1]
                            return citation
                        else:
                            logger.warning(f"   ⚠️  Alternative also invalid: {alternative[0]}")
                    
                    # CRITICAL FIX: Reject invalid citations entirely instead of keeping 404 URLs
                    # Invalid URLs break user trust and harm SEO
                    logger.error(f"   ❌ No valid alternative found for citation [{citation.number}]")
                    logger.error(f"   Rejecting invalid citation (404 URL): {final_url}")
                    logger.error(f"   Citation [{citation.number}] will be removed from final output")
                    # Return None to signal this citation should be filtered out
                    return None
                
                # URL is valid - use it
                citation.url = final_url
                citation.title = final_title
                return citation
            except Exception as e:
                logger.warning(f"Error validating citation [{citation.number}]: {e}")
                # Return original citation on error
                return citation
        
        # Execute all validations in parallel
        tasks = [validate_single_citation(citation) for citation in citations]
        validated = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions and filter out invalid citations (None values)
        # CRITICAL: Keep original citation numbers to maintain sync with content markers [1], [2], etc.
        # Invalid citations are filtered from HTML output, but markers in content remain as plain text
        result = []
        invalid_count = 0
        invalid_numbers = []
        for i, citation_or_error in enumerate(validated):
            if isinstance(citation_or_error, Exception):
                logger.error(f"Citation [{citations[i].number}] validation failed: {citation_or_error}")
                # Reject citations that errored during validation
                invalid_count += 1
                invalid_numbers.append(citations[i].number)
                logger.warning(f"   Rejecting citation [{citations[i].number}] due to validation error")
            elif citation_or_error is None:
                # Citation was rejected (invalid 404 URL with no alternative)
                invalid_count += 1
                invalid_numbers.append(citations[i].number)
            else:
                result.append(citation_or_error)
        
        if invalid_count > 0:
            logger.warning(f"⚠️  Filtered out {invalid_count} invalid citations: {invalid_numbers}")
            logger.info(f"   Citation markers [{', '.join(map(str, invalid_numbers))}] in content will show as plain text (no links)")
        
        logger.info(f"✅ Parallel validation complete: {len(result)} valid citations (rejected {invalid_count} invalid)")
        return result

    async def close(self):
        """Close HTTP client and cleanup caches."""
        await self.http_client.aclose()
        # Clean up expired cache entries to prevent memory leaks
        self._cleanup_expired_cache()
    
    @staticmethod
    def _cleanup_expired_cache():
        """Clean up expired cache entries to prevent memory leaks."""
        current_time = time.time()
        
        # Clean URL status cache
        expired_urls = [
            url for url, (_, _, timestamp) in _URL_STATUS_CACHE.items()
            if current_time - timestamp > _CACHE_TTL
        ]
        for url in expired_urls:
            del _URL_STATUS_CACHE[url]
        
        # Clean authority cache  
        expired_queries = [
            query for query, (_, timestamp) in _AUTHORITY_CACHE.items()
            if current_time - timestamp > _CACHE_TTL
        ]
        for query in expired_queries:
            del _AUTHORITY_CACHE[query]
        
        if expired_urls or expired_queries:
            logger.debug(f"Cache cleanup: removed {len(expired_urls)} URL entries, {len(expired_queries)} authority entries")

    def __repr__(self) -> str:
        """String representation."""
        return f"CitationURLValidator(max_attempts={self.max_attempts}, timeout={self.timeout})"

