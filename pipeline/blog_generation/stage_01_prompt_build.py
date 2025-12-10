"""
Stage 1: Simple Prompt Construction

ABOUTME: Builds prompts using company context instead of complex market templates
ABOUTME: Simple, clean system that focuses on company information only

Builds the main article prompt by:
1. Loading company context (name, industry, description, etc.)
2. Injecting company variables into a simple prompt template
3. Adding optional sections (pain points, competitors, guidelines)
4. Validating prompt structure
5. Storing in context for Stage 2

This approach is SIMPLE and EFFECTIVE:
- Company-focused content generation
- All fields optional except company URL
- Clean prompt structure without market complexity
- Flexible content guidelines and instructions

Combined with tools (googleSearch, urlContext), this creates company-appropriate content.
"""

import logging
from typing import Dict, Any

from ..core import ExecutionContext, Stage
from ..core.company_context import CompanyContext
from ..prompts.simple_article_prompt import build_article_prompt, validate_prompt_inputs

logger = logging.getLogger(__name__)


class PromptBuildStage(Stage):
    """
    Stage 1: Build simple article prompt with company context injection.

    Builds the complete prompt that will be sent to Gemini using company information.
    Simple system without market complexity - company context only.
    """

    stage_num = 1
    stage_name = "Simple Prompt Construction"

    async def execute(self, context: ExecutionContext) -> ExecutionContext:
        """
        Execute Stage 1: Build simple article prompt using company context.

        Inputs from context:
        - job_config.primary_keyword: Main topic (required)
        - job_config.language: Target language (optional, default: en)
        - company_data: Company information (company_url required, rest optional)

        Outputs to context:
        - prompt: Complete prompt string ready for Gemini
        - company_context: Processed company information

        Args:
            context: ExecutionContext from Stage 0

        Returns:
            Updated context with simple prompt populated

        Raises:
            ValueError: If required fields missing
        """
        logger.info(f"Stage 1: {self.stage_name}")

        # Extract primary keyword (required)
        primary_keyword = context.job_config.get("primary_keyword", "")
        if not primary_keyword:
            raise ValueError("primary_keyword is required")

        # Extract language (optional, default to English)
        language = context.job_config.get("language", "en")

        # Convert company_data to CompanyContext
        company_data = context.company_data or {}
        
        # Handle both dict and CompanyContext inputs
        if isinstance(company_data, dict):
            company_context = CompanyContext.from_dict(company_data)
        else:
            company_context = company_data

        # Validate company context (requires company_url)
        company_context.validate()

        # Convert to prompt variables
        prompt_context = company_context.to_prompt_context()

        logger.debug(f"Keyword: '{primary_keyword}'")
        logger.debug(f"Language: {language}")
        logger.debug(f"Company: {prompt_context.get('company_name', 'Unknown')}")
        logger.debug(f"Company URL: {prompt_context.get('company_url', 'Not provided')}")
        logger.debug(f"Industry: {prompt_context.get('industry', 'Not specified')}")

        # Validate inputs before building prompt
        validate_prompt_inputs(primary_keyword, prompt_context)

        # Build the simple prompt
        try:
            prompt = build_article_prompt(
                primary_keyword=primary_keyword,
                company_context=prompt_context,
                language=language
            )
        except Exception as e:
            logger.error(f"Failed to build prompt: {e}")
            raise ValueError(f"Unable to generate prompt: {e}")

        # Validate generated prompt
        if not prompt or len(prompt.strip()) < 500:
            raise ValueError(f"Generated prompt is too short ({len(prompt)} chars, expected > 500)")

        logger.info(f"✅ Simple prompt generated successfully")
        logger.info(f"   Length: {len(prompt)} characters")
        logger.info(f"   Language: {language}")
        logger.info(f"   Keyword: '{primary_keyword}'")
        logger.info(f"   Company: '{prompt_context.get('company_name', 'Unknown')}'")

        # Store in context
        context.prompt = prompt
        context.company_context = company_context
        context.language = language

        return context

    def _validate_prompt(self, prompt: str) -> None:
        """
        Basic prompt validation.
        
        Args:
            prompt: Prompt string to validate
            
        Raises:
            ValueError: If prompt is invalid
        """
        if not prompt or len(prompt.strip()) == 0:
            raise ValueError("Prompt is empty")
        
        if len(prompt) < 500:
            raise ValueError(f"Prompt too short ({len(prompt)} chars, expected > 500)")

        # Check for basic content
        if "Write a comprehensive" not in prompt and "write" not in prompt.lower():
            raise ValueError("Prompt doesn't appear to contain writing instructions")