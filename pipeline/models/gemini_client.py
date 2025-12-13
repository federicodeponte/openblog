"""
AI Client with Tools Support - Direct Google GenAI SDK

Uses google-genai SDK directly for:
- Gemini content generation
- Built-in Google Search grounding (free 1,500/day)
  - Automatically fetches URL context from search results
  - Provides real-time web information
- Response parsing (JSON extraction from plain text)
- Retry logic with exponential backoff
- DataForSEO fallback when Google Search quota is exhausted

Configuration:
- Model: gemini-3.0-pro-preview (default, Gemini 3.0 Pro Preview)
- Quality mode: gemini-3.0-pro-preview (same model)
- Response mime type: text/plain (NOT application/json)
- Temperature: 0.2 (consistency)
- Tools: Google Search (includes URL context via search results)
- Fallback: DataForSEO Standard mode ($0.50/1k queries)
"""

import os
import json
import re
import time
import asyncio
import logging
from typing import Optional, Dict, Any, List

from ..models.output_schema import ArticleOutput, ComparisonTable

logger = logging.getLogger(__name__)

# Lazy import for DataForSEO fallback to avoid circular imports
_search_executor = None

def _get_search_executor():
    """Lazy initialization of search executor for DataForSEO fallback."""
    global _search_executor
    if _search_executor is None:
        try:
            from .search_tool_executor import get_search_executor
            _search_executor = get_search_executor()
        except ImportError:
            logger.warning("DataForSEO fallback not available - search_tool_executor not found")
            return None
    return _search_executor

# Default models - using Gemini 3.0 Pro Preview
DEFAULT_MODEL = "gemini-3-pro-preview"  # Gemini 3.0 Pro Preview with search grounding (includes URL context)
QUALITY_MODEL = "gemini-3-pro-preview"  # Same model for quality mode


def build_article_response_schema(genai):
    """
    Build Gemini response_schema from ArticleOutput Pydantic model.
    
    This forces Gemini to output strict JSON matching our schema,
    preventing hallucinations from freeform text generation.
    
    UPDATED: Now dynamically reads field descriptions from ArticleOutput
    to ensure our explicit [N] bans reach Gemini.
    
    Returns:
        genai.types.Schema object for response_schema parameter
    """
    from google.genai import types
    from .output_schema import ArticleOutput
    
    # ComparisonTable sub-schema
    comparison_table_schema = types.Schema(
        type=types.Type.OBJECT,
        properties={
            "title": types.Schema(type=types.Type.STRING, description="Table title"),
            "headers": types.Schema(
                type=types.Type.ARRAY,
                items=types.Schema(type=types.Type.STRING),
                description="Column headers (2-6 columns)"
            ),
            "rows": types.Schema(
                type=types.Type.ARRAY,
                items=types.Schema(
                    type=types.Type.ARRAY,
                    items=types.Schema(type=types.Type.STRING)
                ),
                description="Table rows (1-10 rows)"
            ),
        },
        required=["title", "headers", "rows"]
    )
    
    # Build properties dynamically from ArticleOutput model
    properties = {}
    for field_name, field_info in ArticleOutput.model_fields.items():
        if field_name == "tables":
            # Special handling for tables (ARRAY of OBJECT)
            properties["tables"] = types.Schema(
                type=types.Type.ARRAY,
                items=comparison_table_schema,
                description=field_info.description or "Comparison tables (max 2)"
            )
        else:
            # All other fields are STRING type
            properties[field_name] = types.Schema(
                type=types.Type.STRING,
                description=field_info.description or f"{field_name} field"
            )
    
    # Main ArticleOutput schema
    return types.Schema(
        type=types.Type.OBJECT,
        properties=properties,
        required=[
            "Headline", "Teaser", "Direct_Answer", "Intro", "Meta_Title", "Meta_Description",
            "section_01_title", "section_01_content"  # At least one section required
        ]
    )


def build_refresh_response_schema(genai):
    """
    Build Gemini response_schema from RefreshResponse Pydantic model.
    
    This forces Gemini to output strict JSON when refreshing content,
    preventing hallucinations and ensuring consistent structure.
    
    Returns:
        genai.types.Schema object for response_schema parameter
    """
    from google.genai import types
    
    # RefreshedSection sub-schema
    refreshed_section_schema = types.Schema(
        type=types.Type.OBJECT,
        properties={
            "heading": types.Schema(
                type=types.Type.STRING, 
                description="Section heading (plain text, NO HTML)"
            ),
            "content": types.Schema(
                type=types.Type.STRING,
                description="Updated section content (may include HTML like <p>, <ul>, <strong>)"
            ),
            "change_summary": types.Schema(
                type=types.Type.STRING,
                description="Brief description of changes made (e.g., 'Updated stats to 2025')"
            ),
        },
        required=["heading", "content"]
    )
    
    # Main RefreshResponse schema
    return types.Schema(
        type=types.Type.OBJECT,
        properties={
            "sections": types.Schema(
                type=types.Type.ARRAY,
                items=refreshed_section_schema,
                description="List of refreshed sections (at least 1 required)"
            ),
            "meta_description": types.Schema(
                type=types.Type.STRING,
                description="Updated meta description (120-160 chars, optional)"
            ),
            "changes_made": types.Schema(
                type=types.Type.STRING,
                description="Overall summary of all changes made"
            ),
        },
        required=["sections", "changes_made"]
    )


class GeminiClient:
    """
    AI client for content generation with Google Search grounding.
    Uses google-genai SDK directly.

    Implements:
    - Content generation with Google Search grounding
      (automatically fetches URL context from search results)
    - Response parsing (JSON extraction from text/plain)
    - Retry logic with exponential backoff
    - Error handling and logging
    """

    # Configuration constants
    RESPONSE_MIME_TYPE = "text/plain"  # Critical: NOT application/json
    TEMPERATURE = 0.2  # Consistency
    MAX_OUTPUT_TOKENS = 65536  # Full article

    # Retry configuration
    MAX_RETRIES = 3
    INITIAL_RETRY_WAIT = 5.0  # seconds
    RETRY_BACKOFF_MULTIPLIER = 2.0

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None) -> None:
        """
        Initialize AI client.

        Args:
            model: Model name (defaults to GEMINI_MODEL env var or gemini-2.0-flash-exp)
            api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
        """
        # Set model
        self.MODEL = model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
        
        # Get API key
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable required")
        
        # Determine API version based on model
        # Flash models (2.5-flash, 2.5-flash-lite) require v1beta
        # Preview models (3.0-pro-preview) use v1alpha
        is_flash_model = 'flash' in self.MODEL.lower()
        api_version = 'v1beta' if is_flash_model else 'v1alpha'
        
        # Normalize Flash model name (remove -preview suffix if present)
        if is_flash_model and self.MODEL.endswith('-preview'):
            # Use standard Flash model name for v1beta
            normalized_model = self.MODEL.replace('-preview', '')
            logger.info(f"Normalizing Flash model: {self.MODEL} → {normalized_model}")
            self.MODEL = normalized_model
        
        # Store grounding URLs from last API call
        self._last_grounding_urls: List[Dict[str, str]] = []
        
        # Initialize client with appropriate API version
        try:
            from google import genai
            from google.genai import types
            self.client = genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(api_version=api_version)
            )
            self._genai = genai
            logger.info(f"AI client initialized (model: {self.MODEL}, backend: google-genai SDK, API: {api_version})")
        except ImportError:
            raise ImportError("google-genai package required. Install with: pip install google-genai")

    async def generate_content(
        self,
        prompt: str,
        enable_tools: bool = True,
        response_schema: Any = None,
        system_instruction: str = None,
    ) -> str:
        """
        Generate content using Gemini API with Google Search grounding.

        Args:
            prompt: Complete prompt string
            enable_tools: Whether to enable Google Search grounding (includes URL context)
            response_schema: Optional schema for structured JSON output
            system_instruction: Optional system instruction (high priority guidance for Gemini)

        Returns:
            Raw response text (plain text with embedded JSON, or direct JSON if schema provided)

        Raises:
            Exception: If all retries fail
        """
        logger.info(f"Generating content with {self.MODEL}")
        logger.debug(f"Prompt length: {len(prompt)} characters")
        logger.debug(f"Grounding tools: {enable_tools}")
        logger.debug(f"Response schema: {'Yes' if response_schema else 'No'}")
        logger.debug(f"System instruction: {'Yes' if system_instruction else 'No'}")

        # Call API with retry logic
        response_text = await self._call_api_with_retry(
            prompt, 
            enable_tools, 
            response_schema=response_schema,
            system_instruction=system_instruction
        )

        return response_text

    async def _call_api_with_retry(self, prompt: str, enable_grounding: bool, response_schema: Any = None, system_instruction: str = None) -> str:
        """
        Call Gemini API with exponential backoff retry.

        Args:
            prompt: Complete prompt
            enable_grounding: Whether to enable Google Search grounding (includes URL context)
            response_schema: Optional schema for structured JSON output
            system_instruction: Optional system instruction (high priority)

        Returns:
            Response text

        Raises:
            Exception: If all retries fail
        """
        last_error = None
        wait_time = self.INITIAL_RETRY_WAIT

        for attempt in range(self.MAX_RETRIES):
            try:
                logger.debug(f"API call attempt {attempt + 1}/{self.MAX_RETRIES}")

                # Build grounding tools if enabled
                tools = None
                if enable_grounding:
                    # Google Search grounding automatically includes URL context from search results
                    tools = [
                        self._genai.types.Tool(google_search=self._genai.types.GoogleSearch()),
                    ]
                    logger.debug("Google Search grounding enabled (includes URL context)")

                # Make synchronous call (google-genai doesn't have native async)
                # Run in executor to not block event loop
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.client.models.generate_content(
                        model=self.MODEL,
                        contents=prompt,
                        config=self._genai.types.GenerateContentConfig(
                            temperature=self.TEMPERATURE,
                            max_output_tokens=self.MAX_OUTPUT_TOKENS,
                            tools=tools,
                            response_schema=response_schema,
                            response_mime_type="application/json" if response_schema else None,
                            system_instruction=system_instruction,  # HIGH PRIORITY GUIDANCE
                        )
                    )
                )

                # Extract text from response
                if not response:
                    raise Exception("Empty response from Gemini API")

                # For JSON schema responses, extract from candidates
                response_text = None
                if response_schema and hasattr(response, "candidates") and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, "content") and candidate.content:
                        parts = getattr(candidate.content, "parts", [])
                        if parts and hasattr(parts[0], "text"):
                            response_text = parts[0].text

                # Fallback to response.text
                if not response_text and hasattr(response, "text") and response.text:
                    response_text = response.text

                if not response_text:
                    raise Exception("Empty response payload from Gemini API")

                logger.info(f"✅ API call succeeded ({len(response_text)} chars)")
                
                # Extract and store grounding sources (actual URLs from Google Search)
                grounding_urls = []
                if hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                        gm = candidate.grounding_metadata
                        if hasattr(gm, 'search_entry_point') and gm.search_entry_point:
                            logger.info("🔍 Google Search grounding used")
                        if hasattr(gm, 'grounding_chunks') and gm.grounding_chunks:
                            logger.info(f"📎 {len(gm.grounding_chunks)} grounding sources")
                            # CRITICAL: Extract URLs from grounding chunks
                            # The 'uri' is a proxy URL (vertexaisearch.cloud.google.com)
                            # The 'title' contains the real domain (e.g., "sportingnews.com")
                            # We resolve the proxy to get the real URL
                            for chunk in gm.grounding_chunks:
                                if hasattr(chunk, 'web') and chunk.web:
                                    proxy_url = getattr(chunk.web, 'uri', None)
                                    title = getattr(chunk.web, 'title', None)
                                    if proxy_url:
                                        # Resolve proxy URL to real URL
                                        real_url = self._resolve_proxy_url(proxy_url)
                                        grounding_urls.append({
                                            'url': real_url,
                                            'proxy_url': proxy_url,
                                            'title': title or real_url,
                                            'domain': title  # Title is the domain
                                        })
                                        logger.debug(f"   📎 {title}: {real_url}")
                            if grounding_urls:
                                logger.info(f"✅ Extracted {len(grounding_urls)} grounding URLs (resolved from proxy)")
                
                # Store grounding URLs for later use (will be injected into Sources field)
                self._last_grounding_urls = grounding_urls

                return response_text

            except Exception as e:
                last_error = e
                error_type = type(e).__name__
                error_str = str(e).lower()

                # Check if error is retryable
                retryable = self._is_retryable_error(e)

                if not retryable:
                    logger.error(f"Non-retryable error: {error_type}: {e}")
                    raise

                if attempt < self.MAX_RETRIES - 1:
                    logger.warning(
                        f"Retryable error (attempt {attempt + 1}): {error_type}: {e}"
                    )
                    logger.info(f"Waiting {wait_time:.1f}s before retry...")
                    await asyncio.sleep(wait_time)
                    wait_time *= self.RETRY_BACKOFF_MULTIPLIER
                else:
                    logger.error(f"All {self.MAX_RETRIES} retries failed: {error_type}")

        # All retries failed - check if we should try DataForSEO fallback
        if enable_grounding and self._should_use_search_fallback(last_error):
            logger.warning("🚨 Google Search quota exhausted, attempting DataForSEO fallback...")
            fallback_result = await self._try_dataforseo_fallback(prompt, last_error)
            if fallback_result:
                return fallback_result
            logger.error("❌ DataForSEO fallback also failed")

        # All retries failed
        raise Exception(
            f"AI API call failed after {self.MAX_RETRIES} retries: {last_error}"
        )

    def _should_use_search_fallback(self, error: Exception) -> bool:
        """
        Check if error indicates Google Search quota exhaustion.
        
        Args:
            error: The exception from the failed API call
            
        Returns:
            True if DataForSEO fallback should be attempted
        """
        if not error:
            return False
            
        error_str = str(error).lower()
        
        # Patterns indicating Google Search quota exhaustion
        quota_patterns = [
            "resource_exhausted",
            "quota",
            "rate limit",
            "429",
            "too many requests",
            "usage limit",
            "daily limit",
            "search grounding",
            "google search",
        ]
        
        for pattern in quota_patterns:
            if pattern in error_str:
                logger.debug(f"Detected quota pattern: {pattern}")
                return True
                
        return False
    
    def get_last_grounding_urls(self) -> List[Dict[str, str]]:
        """
        Get the grounding URLs from the last API call.
        
        Returns:
            List of dicts with 'url' and 'title' keys from Google Search grounding.
            These are the ACTUAL source URLs found by Gemini's deep research.
        """
        return self._last_grounding_urls.copy()

    async def _try_dataforseo_fallback(
        self, 
        prompt: str, 
        original_error: Exception
    ) -> Optional[str]:
        """
        Attempt DataForSEO fallback when Google Search fails.
        
        This is a best-effort fallback - it extracts the main topic from the
        prompt and performs a DataForSEO search, then retries content generation
        with the search results injected into the prompt.
        
        Args:
            prompt: The original prompt
            original_error: The error from Google Search
            
        Returns:
            Response text if fallback succeeds, None otherwise
        """
        executor = _get_search_executor()
        if not executor or not executor.is_fallback_available():
            logger.warning("DataForSEO fallback not available")
            return None
            
        try:
            # Extract main query from prompt (look for keyword or topic)
            query = self._extract_search_query_from_prompt(prompt)
            if not query:
                logger.warning("Could not extract search query from prompt")
                return None
                
            logger.info(f"🔍 DataForSEO fallback search: '{query}'")
            
            # Execute fallback search
            search_results = await executor.execute_search_with_fallback(
                query=query,
                primary_error=original_error,
                max_results=5,
            )
            
            if not search_results or "failed" in search_results.lower():
                logger.warning(f"DataForSEO search failed: {search_results}")
                return None
                
            # Inject search results into prompt and retry WITHOUT grounding
            enhanced_prompt = self._inject_search_results(prompt, search_results)
            
            logger.info("🔄 Retrying content generation with DataForSEO results...")
            
            # Retry without Google Search grounding (we have DataForSEO results now)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model=self.MODEL,
                    contents=enhanced_prompt,
                    config=self._genai.types.GenerateContentConfig(
                        temperature=self.TEMPERATURE,
                        max_output_tokens=self.MAX_OUTPUT_TOKENS,
                        tools=None,  # No grounding - we injected search results
                    )
                )
            )
            
            if response and hasattr(response, "text") and response.text:
                logger.info(f"✅ DataForSEO fallback succeeded ({len(response.text)} chars)")
                return response.text
                
            return None
            
        except Exception as e:
            logger.error(f"DataForSEO fallback error: {e}")
            return None

    def _extract_search_query_from_prompt(self, prompt: str) -> Optional[str]:
        """
        Extract the main search query from a content generation prompt.
        
        Looks for keyword/topic patterns in the prompt.
        
        Args:
            prompt: The full generation prompt
            
        Returns:
            Extracted query string or None
        """
        import re
        
        # Common patterns for keyword/topic in prompts
        patterns = [
            r'primary\s*keyword[:\s]*["\']?([^"\'\n,]+)["\']?',
            r'target\s*keyword[:\s]*["\']?([^"\'\n,]+)["\']?',
            r'keyword[:\s]*["\']?([^"\'\n,]+)["\']?',
            r'topic[:\s]*["\']?([^"\'\n,]+)["\']?',
            r'write\s+(?:about|on)[:\s]*["\']?([^"\'\n,]+)["\']?',
            r'article\s+(?:about|on)[:\s]*["\']?([^"\'\n,]+)["\']?',
        ]
        
        prompt_lower = prompt.lower()
        
        for pattern in patterns:
            match = re.search(pattern, prompt_lower, re.IGNORECASE)
            if match:
                query = match.group(1).strip()
                if len(query) >= 3 and len(query) <= 100:
                    return query
                    
        # Fallback: use first significant line that looks like a topic
        lines = prompt.split('\n')
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            if len(line) >= 5 and len(line) <= 100 and not line.startswith('#'):
                # Skip common prompt instructions
                skip_words = ['write', 'create', 'generate', 'the', 'you', 'please', 'make']
                first_word = line.split()[0].lower() if line.split() else ''
                if first_word not in skip_words:
                    return line
                    
        return None

    def _inject_search_results(self, prompt: str, search_results: str) -> str:
        """
        Inject DataForSEO search results into the prompt.
        
        Args:
            prompt: Original prompt
            search_results: Formatted search results from DataForSEO
            
        Returns:
            Enhanced prompt with search results
        """
        injection = f"""
## Web Research Results (from DataForSEO)

The following search results provide current information for your article:

{search_results}

Use these sources to inform your content. Cite specific sources where appropriate.

---

"""
        return injection + prompt

    def _is_retryable_error(self, error: Exception) -> bool:
        """
        Check if error is retryable.

        Retryable:
        - Rate limit errors (429)
        - Timeout errors
        - Network errors
        - Service unavailable (503)

        Not retryable:
        - Authentication errors (401, 403)
        - Bad requests (400)
        - Validation errors
        - Malformed input

        Args:
            error: Exception to check

        Returns:
            True if error is retryable
        """
        error_str = str(error).lower()

        # Retryable patterns
        retryable_patterns = [
            "rate limit",
            "429",
            "timeout",
            "connection",
            "service unavailable",
            "503",
            "temporarily unavailable",
            "deadline exceeded",
            "resource exhausted",
            "quota",
        ]

        # Non-retryable patterns
        non_retryable_patterns = [
            "authentication",
            "401",
            "403",
            "forbidden",
            "unauthorized",
            "bad request",
            "400",
            "invalid",
            "malformed",
            "api key",
        ]

        # Check patterns
        for pattern in non_retryable_patterns:
            if pattern in error_str:
                return False

        for pattern in retryable_patterns:
            if pattern in error_str:
                return True

        # Default: retry unknown errors
        return True

    def extract_json_from_response(self, response_text: str) -> Dict[str, Any]:
        """
        Extract JSON from text/plain response.

        Response may contain:
        - JSON wrapped in ```json ... ```
        - Plain JSON object
        - Text before/after JSON
        - Multiple JSON blocks (concatenate)

        Args:
            response_text: Raw response text from AI

        Returns:
            Parsed JSON as dictionary

        Raises:
            ValueError: If no valid JSON found
            json.JSONDecodeError: If JSON is malformed
        """
        logger.debug(f"Extracting JSON from {len(response_text)} chars")

        # Try code block first
        code_block_match = re.search(r"```json\s*([\s\S]*?)\s*```", response_text)
        if code_block_match:
            json_str = code_block_match.group(1)
            logger.debug("Found JSON in code block")
            return json.loads(json_str)

        # Try plain JSON object
        json_match = re.search(r"\{[\s\S]*\}", response_text)
        if json_match:
            json_str = json_match.group(0)
            logger.debug("Found JSON object")
            return json.loads(json_str)

        # No JSON found
        raise ValueError("No JSON found in response")

    @staticmethod
    def build_article_response_schema(genai_types) -> Any:
        """
        Build a Google GenAI Schema from ArticleOutput for response_schema.
        
        Maps ArticleOutput fields to proper schema types:
        - Most fields: STRING (text/HTML)
        - tables: ARRAY of OBJECT (structured data)
        
        Args:
            genai_types: google.genai.types module
            
        Returns:
            Schema object for GenerateContentConfig
        """
        props = {}
        required = []
        
        # Special handling for tables field (ARRAY of OBJECT)
        table_schema = genai_types.Schema(
            type=genai_types.Type.OBJECT,
            properties={
                "title": genai_types.Schema(type=genai_types.Type.STRING),
                "headers": genai_types.Schema(
                    type=genai_types.Type.ARRAY,
                    items=genai_types.Schema(type=genai_types.Type.STRING)
                ),
                "rows": genai_types.Schema(
                    type=genai_types.Type.ARRAY,
                    items=genai_types.Schema(
                        type=genai_types.Type.ARRAY,
                        items=genai_types.Schema(type=genai_types.Type.STRING)
                    )
                ),
            },
            required=["title", "headers", "rows"]
        )
        
        # Map all fields from ArticleOutput
        for name, field in ArticleOutput.model_fields.items():
            if name == "tables":
                # CRITICAL FIX: tables is ARRAY, not STRING
                props[name] = genai_types.Schema(
                    type=genai_types.Type.ARRAY,
                    items=table_schema
                )
            else:
                # All other fields are strings (text/HTML)
                props[name] = genai_types.Schema(type=genai_types.Type.STRING)
            
            # Mark as required if field is required
            if field.is_required():
                required.append(name)
        
        return genai_types.Schema(
            type=genai_types.Type.OBJECT,
            properties=props,
            required=required if required else None,
        )

    def _resolve_proxy_url(self, proxy_url: str) -> str:
        """
        Resolve a Gemini grounding proxy URL to the real destination URL.
        
        Gemini's grounding returns URLs like:
        https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQ...
        
        These redirect (302) to the actual source URL. We follow the redirect
        to get the real URL for cleaner citations.
        
        Args:
            proxy_url: The vertexaisearch proxy URL
            
        Returns:
            The real destination URL, or the proxy URL if resolution fails
        """
        if not proxy_url or 'vertexaisearch.cloud.google.com' not in proxy_url:
            return proxy_url
        
        try:
            import requests
            # Use HEAD request with allow_redirects=False to get redirect location
            response = requests.head(proxy_url, allow_redirects=False, timeout=5)
            if response.status_code in (301, 302, 303, 307, 308):
                real_url = response.headers.get('Location', proxy_url)
                logger.debug(f"   Resolved proxy → {real_url}")
                return real_url
            else:
                # Not a redirect, return as-is
                return proxy_url
        except Exception as e:
            logger.debug(f"   Failed to resolve proxy URL: {e}")
            return proxy_url

    def __repr__(self) -> str:
        """String representation."""
        return f"GeminiClient(model={self.MODEL}, backend=google-genai)"
