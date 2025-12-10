"""
Simple Article Prompt - Company Context Based
Replaces complex market-aware prompts with simple company context injection.
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def build_article_prompt(
    primary_keyword: str,
    company_context: Dict[str, Any],
    language: str = "en",
    **kwargs
) -> str:
    """
    Build a simple article prompt using company context.
    
    Args:
        primary_keyword: Main topic/keyword for the article
        company_context: Company information from CompanyContext.to_prompt_context()
        language: Target language (default: en)
        **kwargs: Additional parameters
    
    Returns:
        Complete prompt string ready for Gemini
    """
    
    company_name = company_context.get("company_name", "the company")
    company_url = company_context.get("company_url", "")
    industry = company_context.get("industry", "")
    description = company_context.get("description", "")
    brand_tone = company_context.get("brand_tone", "professional")
    
    # Optional context sections
    products_services = company_context.get("products_services", "")
    target_audience = company_context.get("target_audience", "")
    competitors = company_context.get("competitors", "")
    pain_points = company_context.get("pain_points", "")
    value_propositions = company_context.get("value_propositions", "")
    use_cases = company_context.get("use_cases", "")
    content_themes = company_context.get("content_themes", "")
    
    # Content guidelines
    system_instructions = company_context.get("system_instructions", "")
    client_knowledge_base = company_context.get("client_knowledge_base", "")
    content_instructions = company_context.get("content_instructions", "")
    
    # Build the company context section
    company_section = f"""
COMPANY CONTEXT:
Company: {company_name}
Website: {company_url}"""
    
    if industry:
        company_section += f"\nIndustry: {industry}"
    
    if description:
        company_section += f"\nDescription: {description}"
        
    if products_services:
        company_section += f"\nProducts/Services: {products_services}"
    
    if target_audience:
        company_section += f"\nTarget Audience: {target_audience}"
    
    if brand_tone:
        company_section += f"\nBrand Tone: {brand_tone}"
    
    # Add optional sections if provided
    optional_sections = ""
    
    if pain_points:
        optional_sections += f"""

CUSTOMER PAIN POINTS:
{pain_points}"""
    
    if value_propositions:
        optional_sections += f"""

VALUE PROPOSITIONS:
{value_propositions}"""
    
    if use_cases:
        optional_sections += f"""

USE CASES:
{use_cases}"""
    
    if content_themes:
        optional_sections += f"""

CONTENT THEMES: {content_themes}"""
    
    if competitors:
        optional_sections += f"""

COMPETITORS TO DIFFERENTIATE FROM: {competitors}"""
    
    # Content guidelines section
    guidelines_section = ""
    
    if system_instructions:
        guidelines_section += f"""

SYSTEM INSTRUCTIONS:
{system_instructions}"""
    
    if client_knowledge_base:
        guidelines_section += f"""

COMPANY KNOWLEDGE BASE:
{client_knowledge_base}"""
    
    if content_instructions:
        guidelines_section += f"""

CONTENT WRITING INSTRUCTIONS:
{content_instructions}"""
    
    # Build the complete prompt
    prompt = f"""Write a comprehensive, high-quality blog article about "{primary_keyword}".

{company_section}{optional_sections}{guidelines_section}

ARTICLE REQUIREMENTS:
- Target language: {language}
- Write in {brand_tone} tone
- Focus on providing genuine value to readers
- Include specific examples and actionable insights
- Structure with clear headings and subheadings
- Aim for 1,500-2,500 words
- Include introduction, main sections, and conclusion
- Make it engaging and informative

IMPORTANT GUIDELINES:
- Write from an authoritative, knowledgeable perspective
- Include relevant statistics and data when possible
- Reference industry best practices
- Provide actionable takeaways for readers
- Ensure content is original and valuable
- Optimize for search engines while prioritizing reader value

Please write the complete article now."""

    logger.debug(f"Generated prompt length: {len(prompt)} characters")
    logger.debug(f"Company context included: {bool(company_name and company_url)}")
    logger.debug(f"Optional sections: {len(optional_sections)} chars")
    logger.debug(f"Guidelines sections: {len(guidelines_section)} chars")
    
    return prompt


def validate_prompt_inputs(primary_keyword: str, company_context: Dict[str, Any]) -> bool:
    """
    Validate that required inputs are provided for prompt generation.
    
    Args:
        primary_keyword: Main topic/keyword
        company_context: Company information dictionary
    
    Returns:
        True if valid, raises ValueError if invalid
    """
    if not primary_keyword or not primary_keyword.strip():
        raise ValueError("primary_keyword is required and cannot be empty")
    
    if not company_context.get("company_url"):
        raise ValueError("company_url is required in company_context")
    
    return True


def get_prompt_length_estimate(
    primary_keyword: str,
    company_context: Dict[str, Any],
    language: str = "en"
) -> int:
    """
    Estimate the prompt length without building the full prompt.
    Useful for checking if prompt will be too long for API limits.
    """
    base_prompt_length = 800  # Approximate base template length
    
    # Add length of dynamic content
    keyword_length = len(primary_keyword) if primary_keyword else 0
    company_name_length = len(company_context.get("company_name", "")) 
    description_length = len(company_context.get("description", ""))
    
    # Add length of optional sections
    optional_length = sum([
        len(company_context.get("products_services", "")),
        len(company_context.get("target_audience", "")),
        len(company_context.get("competitors", "")),
        len(company_context.get("pain_points", "")),
        len(company_context.get("value_propositions", "")),
        len(company_context.get("use_cases", "")),
        len(company_context.get("content_themes", "")),
        len(company_context.get("system_instructions", "")),
        len(company_context.get("client_knowledge_base", "")),
        len(company_context.get("content_instructions", ""))
    ])
    
    estimated_length = base_prompt_length + keyword_length + company_name_length + description_length + optional_length
    
    logger.debug(f"Estimated prompt length: {estimated_length} characters")
    return estimated_length