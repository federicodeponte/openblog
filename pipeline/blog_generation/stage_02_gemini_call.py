"""
Stage 2: Gemini Content Generation with Tools

Maps to v4.1 Phase 2, Step 5: gemini-research

CRITICAL STAGE for deep research:
- Calls Gemini 3 Pro (default, max quality) with tools enabled
- Tools (googleSearch + urlContext) enable 20+ web searches during generation
- Response format: text/plain (allows natural language + embedded JSON)
- Retry logic: exponential backoff (max 3, 5s initial wait)
- Response parsing: extracts JSON from plain text
- Model configurable via GEMINI_MODEL env var (defaults to gemini-3-pro-preview)

Input:
  - ExecutionContext.prompt (from Stage 1)

Output:
  - ExecutionContext.raw_article (raw Gemini response: text/plain with JSON)

The prompt rules force research:
- "every paragraph must contain number, KPI or real example" → forces web search
- "cite all facts" → forces source finding
- "vary examples" → forces multiple searches
Combined with tools = deep research happens naturally.
"""

import logging
import json
from typing import Dict, Any
from pathlib import Path
from datetime import datetime

from ..core.execution_context import ExecutionContext
from ..core.workflow_engine import Stage
from ..core.error_handling import with_api_retry, error_reporter, ErrorClassifier
from ..models.gemini_client import GeminiClient, build_article_response_schema

logger = logging.getLogger(__name__)


class GeminiCallStage(Stage):
    """
    Stage 2: Generate content using Gemini API with tools + JSON schema.

    Handles:
    - Initializing Gemini client
    - Building response_schema from ArticleOutput (forces structured output)
    - Calling API with tools enabled + schema
    - Parsing response (now direct JSON from Gemini)
    - Error handling and retry logic
    - Storing raw article in context
    """

    stage_num = 2
    stage_name = "Gemini Content Generation (Structured JSON)"

    def __init__(self) -> None:
        """Initialize stage with Gemini client."""
        self.client = GeminiClient()
        logger.info(f"Stage 2 initialized: {self.client}")

    async def execute(self, context: ExecutionContext) -> ExecutionContext:
        """
        Execute Stage 2: Generate content with Gemini (structured JSON output).

        Input from context:
        - prompt: Complete prompt (from Stage 1)

        Output to context:
        - raw_article: Raw Gemini response (DIRECT JSON matching ArticleOutput schema)

        Args:
            context: ExecutionContext from Stage 1

        Returns:
            Updated context with raw_article populated

        Raises:
            ValueError: If prompt missing
            Exception: If Gemini API call fails
        """
        logger.info(f"Stage 2: {self.stage_name}")

        # Validate input
        if not context.prompt:
            raise ValueError("Prompt is required (from Stage 1)")

        logger.debug(f"Prompt length: {len(context.prompt)} characters")

        # Build response schema from ArticleOutput (forces structured output)
        response_schema = build_article_response_schema(self.client._genai)
        logger.info("📐 Built JSON schema from ArticleOutput (prevents hallucinations)")

        # Call Gemini API with tools + JSON schema (with error handling and retries)
        logger.info(f"Calling Gemini API ({self.client.MODEL}) with tools + schema + system instruction...")
        logger.info("(Deep research via googleSearch + urlContext, output forced to JSON)")

        # System instruction (high priority rules)
        system_instruction = """
You are a professional content writer. CRITICAL RULES:
- ALL content MUST be pure Markdown format
- FORBIDDEN: HTML tags of any kind
- Use **bold** for emphasis (NOT HTML)
- Use - or * for lists (NOT HTML)
- Separate paragraphs with blank lines (NOT HTML tags)
- MANDATORY: Use natural attribution combined with academic citations for key facts
- Target 8-12 total citations: mix of "according to [Source]" and numbered "[1], [2]" for statistics
- Include citations in 70%+ of paragraphs (minimum 2 per paragraph with citations)
- NEVER use em dashes (—)
- Use commas or parentheses instead
- Write in conversational, engaging tone with direct reader address
"""

        raw_response = await self._generate_content_with_retry(
            context, 
            response_schema=response_schema,
            system_instruction=system_instruction
        )

        logger.info(f"✅ Gemini API call succeeded")
        logger.info(f"   Response size: {len(raw_response)} characters")

        # Validate response
        self._validate_response(raw_response)

        # Store raw response (now direct JSON string from structured output)
        context.raw_article = raw_response

        # Save raw output for debugging/analysis
        try:
            output_dir = Path("output/raw_gemini_outputs")
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            raw_output_file = output_dir / f"raw_output_{timestamp}.json"
            with open(raw_output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "timestamp": timestamp,
                    "response_size": len(raw_response),
                    "raw_json": raw_response,
                    "parsed_preview": json.loads(raw_response) if raw_response.strip().startswith('{') else None
                }, f, indent=2, ensure_ascii=False)
            logger.info(f"💾 Raw Gemini output saved to: {raw_output_file}")
        except Exception as e:
            logger.warning(f"⚠️  Could not save raw output: {e}")

        # Log response preview
        preview = raw_response[:200].replace("\n", " ")
        logger.info(f"   Response preview: {preview}...")

        # Parse JSON to verify structure (response_schema ensures valid JSON)
        try:
            json_data = json.loads(raw_response)
            logger.info(f"✅ JSON parsing successful")
            logger.info(f"   Top-level keys: {', '.join(list(json_data.keys())[:5])}...")
        except Exception as e:
            logger.warning(f"⚠️  Could not parse JSON from response: {e}")
            logger.warning("   This may cause issues in Stage 3 (Extraction)")

        return context

    def _validate_response(self, response: str) -> None:
        """
        Validate Gemini response.

        Checks:
        - Not empty
        - Contains JSON
        - Reasonable length

        Args:
            response: Raw response from Gemini

        Raises:
            ValueError: If response is invalid
        """
        if not response or len(response.strip()) == 0:
            raise ValueError("Empty response from Gemini API")

        logger.debug("Response validation:")
        logger.debug(f"  ✓ Not empty")

        # Check for JSON
        if "{" in response and "}" in response:
            logger.debug(f"  ✓ Contains JSON (has {{ and }})")
        else:
            logger.warning(f"  ⚠️  May not contain JSON (no {{ or }})")

        # Check length (should be substantial article)
        if len(response) < 1000:
            logger.warning(f"  ⚠️  Response very short ({len(response)} chars)")

        logger.debug(f"Response validation complete")
    
    def _validate_required_fields(self, json_data: dict) -> None:
        """
        Validate that critical required fields are present in JSON response.
        
        Args:
            json_data: Parsed JSON response from Gemini
            
        Raises:
            ValueError: If required fields are missing
        """
        required_fields = [
            "Headline", "Subtitle", "Teaser", "Direct_Answer", "Intro",
            "Meta_Title", "Meta_Description"
        ]
        
        missing_fields = []
        for field in required_fields:
            if field not in json_data or not json_data[field] or not json_data[field].strip():
                missing_fields.append(field)
        
        if missing_fields:
            logger.error(f"❌ Missing required fields: {', '.join(missing_fields)}")
            raise ValueError(f"Response missing required fields: {', '.join(missing_fields)}")
        
        # Validate Meta_Title length
        meta_title = json_data.get("Meta_Title", "")
        if len(meta_title) > 60:
            logger.warning(f"⚠️ Meta_Title too long ({len(meta_title)} chars): {meta_title[:60]}...")
        
        # Validate Meta_Description length
        meta_description = json_data.get("Meta_Description", "")
        if len(meta_description) < 100 or len(meta_description) > 160:
            logger.warning(f"⚠️ Meta_Description wrong length ({len(meta_description)} chars - should be 100-160)")
        
        logger.info(f"✅ All required fields present")
        logger.info(f"   Meta_Title: {len(meta_title)} chars")
        logger.info(f"   Meta_Description: {len(meta_description)} chars")
    
    @with_api_retry("stage_02")
    async def _generate_content_with_retry(self, context: ExecutionContext, response_schema: Any = None, system_instruction: str = None) -> str:
        """
        Generate content with comprehensive error handling and retries.
        
        Args:
            context: Execution context with prompt
            response_schema: Optional JSON schema for structured output
            system_instruction: Optional system instruction (high priority)
            
        Returns:
            Raw Gemini response
            
        Raises:
            Exception: If generation fails after all retries
        """
        try:
            raw_response = await self.client.generate_content(
                prompt=context.prompt,
                enable_tools=True,  # CRITICAL: tools must be enabled!
                response_schema=response_schema,  # JSON schema for structured output
                system_instruction=system_instruction,  # High priority guidance
            )
            
            if not raw_response or len(raw_response.strip()) < 500:
                raise ValueError(f"Response too short ({len(raw_response)} chars) - likely incomplete")
            
            return raw_response
            
        except Exception as e:
            # Log detailed error context for debugging
            logger.error(f"Content generation failed: {e}")
            logger.error(f"Prompt length: {len(context.prompt)} chars")
            logger.error(f"Model: {self.client.MODEL}")
            
            # Let the error handling decorator manage retries and reporting
            raise e
