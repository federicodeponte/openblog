"""
AI Client with Tools Support - Direct Google GenAI SDK

Uses google-genai SDK directly for:
- Gemini content generation
- Built-in Google Search grounding (free 1,500/day)
  - Automatically fetches URL context from search results
  - Provides real-time web information
- Response parsing (JSON extraction from plain text)
- Retry logic with exponential backoff

Configuration:
- Model: gemini-3.0-pro-preview (default, Gemini 3.0 Pro Preview)
- Quality mode: gemini-3.0-pro-preview (same model)
- Response mime type: text/plain (NOT application/json)
- Temperature: 0.2 (consistency)
- Tools: Google Search (includes URL context via search results)
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
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY, GEMINI_API_KEY, or GOOGLE_GEMINI_API_KEY environment variable required")
        
        # Initialize client with v1alpha API version for Gemini 3.0 Pro Preview
        try:
            from google import genai
            from google.genai import types
            # Use v1alpha API version for preview models
            self.client = genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(api_version='v1alpha')
            )
            self._genai = genai
            logger.info(f"AI client initialized (model: {self.MODEL}, backend: google-genai SDK, API: v1alpha)")
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
                
                # Log grounding metadata if available
                if hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                        gm = candidate.grounding_metadata
                        if hasattr(gm, 'search_entry_point') and gm.search_entry_point:
                            logger.info("🔍 Google Search grounding used")
                        if hasattr(gm, 'grounding_chunks') and gm.grounding_chunks:
                            logger.info(f"📎 {len(gm.grounding_chunks)} grounding sources")

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

        # All retries failed
        raise Exception(
            f"AI API call failed after {self.MAX_RETRIES} retries: {last_error}"
        )

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

    def __repr__(self) -> str:
        """String representation."""
        return f"GeminiClient(model={self.MODEL}, backend=google-genai)"
