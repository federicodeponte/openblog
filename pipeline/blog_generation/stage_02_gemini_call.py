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
You are a professional content writer creating SurferSEO-quality articles. CRITICAL RULES:

PRODUCTION CONTENT REQUIREMENTS (NON-NEGOTIABLE):
- MINIMUM 3,000 words (industry standard for professional articles)
- Content under 2,500 words will be REJECTED and regenerated  
- Target 3,500-4,000 words for comprehensive coverage
- Each major section must be 500-800 words minimum
- Professional editorial depth matching Bloomberg/Harvard Business Review standards

RESEARCH REQUIREMENTS (MANDATORY):
- MUST use Google Search tool minimum 15 times during content generation
- Minimum 25 authoritative sources with specific data points and metrics
- EVERY section must contain quantified data (percentages, dollar amounts, dates)
- Include minimum 3 detailed case studies with concrete results
- Competitive analysis with specific tool/company comparisons
- Industry-specific insights beyond generic information

SECTION ARCHITECTURE (REQUIRED):
1. Executive Summary (300-400 words) - key insights and data overview
2. Market Analysis (600-800 words) - industry data, trends, market size
3. Detailed Tool Comparison (800-1000 words) - feature analysis with metrics
4. Implementation Strategy (600-800 words) - step-by-step guidance  
5. Cost-Benefit Analysis (500-700 words) - ROI calculations and TCO
6. Future Trends (400-600 words) - predictions with data backing
7. Recommendations (400-500 words) - actionable next steps
8. Comprehensive FAQ (15+ questions, 600+ words total)

CONTENT DEPTH REQUIREMENTS:
- Each section must have 3+ specific examples with quantified results
- Include direct quotes from industry experts or official sources
- Provide actionable implementation details, not just overviews
- Address both benefits AND limitations/challenges honestly
- Include relevant metrics, timelines, and cost considerations

FORMATTING REQUIREMENTS:
- ALL content MUST be pure Markdown format
- FORBIDDEN: HTML tags of any kind
- Use **bold** for emphasis (NOT HTML)
- Use - or * for lists (NOT HTML)
- Separate paragraphs with blank lines (NOT HTML tags)
- NEVER use academic citations like [1], [2], [3]
- Use natural language attribution: "according to X study"
- NEVER use em dashes (—)
- Use commas or parentheses instead

QUALITY STANDARDS:
- Professional editorial quality suitable for publication
- Industry-specific terminology and insights
- Balance of technical depth with accessibility
- Clear value proposition and actionable insights
- Competitive differentiation and positioning analysis
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
            
            # Validate response meets research and quality requirements
            self._validate_research_quality(raw_response)
            
            return raw_response
            
        except Exception as e:
            # Log detailed error context for debugging
            logger.error(f"Content generation failed: {e}")
            logger.error(f"Prompt length: {len(context.prompt)} chars")
            logger.error(f"Model: {self.client.MODEL}")
            
            # Let the error handling decorator manage retries and reporting
            raise e

    def _validate_research_quality(self, raw_response: str) -> None:
        """
        Validate that the response meets research and quality requirements.
        
        Checks:
        - Minimum word count (1,500+ words)
        - Presence of research sources (10+ "according to", "per", etc.)
        - Proper section structure (H2 headings)
        - FAQ content presence
        
        Args:
            raw_response: Raw JSON response from Gemini
            
        Raises:
            ValueError: If response doesn't meet quality standards
        """
        if not raw_response or len(raw_response.strip()) < 500:
            raise ValueError(f"Response too short ({len(raw_response)} chars) - likely incomplete")
        
        try:
            # Parse JSON to check content
            import json
            data = json.loads(raw_response)
            
            # Check if we have content to validate - aggregate from all fields
            content_parts = []
            
            # Add main content fields
            content_parts.append(data.get('content', '') or data.get('body', '') or '')
            content_parts.append(data.get('intro', '') or '')
            content_parts.append(data.get('direct_answer', '') or '')
            
            # Add section content fields
            for i in range(1, 10):
                section_content_key = f'section_{i:02d}_content'
                if section_content_key in data and data[section_content_key]:
                    content_parts.append(data[section_content_key])
            
            # Add FAQ content
            content_parts.append(data.get('faq', '') or '')
            
            # Aggregate all content
            content = ' '.join(filter(None, content_parts))
            
            # Production-level word count validation  
            word_count = len(content.split())
            if word_count < 2000:
                raise ValueError(f"Content severely insufficient: {word_count} words (production minimum: 3,000). Content appears to be a stub or incomplete generation requiring complete regeneration.")
            elif word_count < 2500:
                raise ValueError(f"Content below minimum threshold: {word_count} words (production minimum: 3,000). Need {3000 - word_count} more words. Ensure each major section is 500-800 words.")
            elif word_count < 3000:
                raise ValueError(f"Content below production standard: {word_count} words (minimum: 3,000). Need {3000 - word_count} more words for SurferSEO-level quality. Expand sections with more research and examples.")
            elif word_count < 3500:
                logger.warning(f"⚠️  Content meets minimum but below optimal: {word_count} words (optimal: 3,500-4,000). Consider expanding for competitive advantage.")
            else:
                logger.info(f"✅ Content meets production standards: {word_count} words")
            
            # Production-level research source validation
            research_indicators = [
                'according to', 'per ', 'study shows', 'research indicates', 
                'survey found', 'report states', 'data reveals', 'analysis shows',
                'survey by', 'report from', 'study by', 'research from',
                'data from', 'findings from', 'statistics from', 'found that',
                'revealed that', 'demonstrated that', 'showed that', 'reported that'
            ]
            source_count = sum(content.lower().count(indicator) for indicator in research_indicators)
            
            # Also count quantified data points (percentages, dollar amounts, specific numbers)
            import re
            percentage_count = len(re.findall(r'\d+%', content))
            dollar_count = len(re.findall(r'\$\d+', content))
            metric_count = len(re.findall(r'\d+[.,]\d+|\d{1,3},\d{3}', content))
            data_points = percentage_count + dollar_count + metric_count
            
            if source_count < 15:
                raise ValueError(f"Insufficient research depth: {source_count} sources found (production minimum: 25). Content lacks professional research backing. Ensure minimum 15 Google Search tool calls with detailed analysis.")
            elif source_count < 20:
                raise ValueError(f"Below research target: {source_count} sources found (production minimum: 25). Need {25 - source_count} more researched claims with specific data and metrics.")
            elif source_count < 25:
                logger.warning(f"⚠️  Research below optimal: {source_count} sources (target: 25+). Content meets minimum but could be stronger.")
            
            if data_points < 10:
                raise ValueError(f"Insufficient quantified data: {data_points} data points found (minimum: 15). Add more percentages, dollar amounts, and specific metrics with source attribution.")
            elif data_points < 15:
                logger.warning(f"⚠️  Data points below target: {data_points} found (optimal: 20+). More quantified analysis would strengthen credibility.")
            
            logger.info(f"📊 Research metrics: {source_count} sources, {data_points} data points ({percentage_count}% + ${dollar_count} + {metric_count} metrics)")
            
            # Production-level section structure validation 
            h2_count = content.count('## ')
            h3_count = content.count('### ')
            
            # Also check if sections are in schema format (section_XX_title fields)
            schema_sections = 0
            section_word_counts = []
            for i in range(1, 10):
                section_title_key = f'section_{i:02d}_title'
                section_content_key = f'section_{i:02d}_content'
                if section_title_key in data and data[section_title_key] and len(data[section_title_key].strip()) > 0:
                    schema_sections += 1
                    # Check individual section word count
                    section_content = data.get(section_content_key, '')
                    section_words = len(section_content.split()) if section_content else 0
                    section_word_counts.append(section_words)
            
            total_sections = max(h2_count, schema_sections)
            if total_sections < 6:
                raise ValueError(f"Insufficient main sections: {total_sections} sections found (production minimum: 8 required). Content lacks comprehensive structure. Need sections: Executive Summary, Market Analysis, Tool Comparison, Implementation, Cost-Benefit, Future Trends, Recommendations, FAQ.")
            elif total_sections < 8:
                raise ValueError(f"Below production target: {total_sections} sections found (minimum: 8 required). Need {8 - total_sections} more sections for professional depth.")
            
            # Validate individual section depth
            if section_word_counts:
                short_sections = [i+1 for i, count in enumerate(section_word_counts) if count > 0 and count < 300]
                if short_sections:
                    raise ValueError(f"Sections too shallow: Section(s) {short_sections} under 300 words (minimum: 500-800 per section). Professional articles require substantial depth in each section.")
                
                avg_section_length = sum(count for count in section_word_counts if count > 0) / len([c for c in section_word_counts if c > 0])
                if avg_section_length < 400:
                    raise ValueError(f"Average section length too short: {avg_section_length:.0f} words (minimum: 500-800). Expand sections with more research, examples, and analysis.")
            
            logger.info(f"📋 Section analysis: {total_sections} sections, average {avg_section_length:.0f} words per section" if section_word_counts else f"📋 Section count: {total_sections}")
            
            # Production-level FAQ validation
            faq_present = 'FAQ' in content or 'Frequently Asked' in content or 'Q:' in content
            faq_questions = content.count('**Q:') + content.count('**Question:') + content.count('Q:') + content.count('?')
            
            if not faq_present:
                raise ValueError("Missing FAQ section - REQUIRED for production quality. Professional articles must include comprehensive FAQ section addressing common user questions and concerns.")
            
            if faq_questions < 15:
                raise ValueError(f"Insufficient FAQ questions: {faq_questions} found (production minimum: 15). FAQ section must be comprehensive, addressing implementation, costs, comparisons, and troubleshooting.")
            elif faq_questions < 20:
                logger.warning(f"⚠️  FAQ questions below optimal: {faq_questions} found (target: 20+). More comprehensive FAQ would improve user experience.")
            
            # Check FAQ content depth
            faq_content = ''
            for key, value in data.items():
                if 'faq' in key.lower() and value:
                    faq_content += value + ' '
            
            faq_word_count = len(faq_content.split()) if faq_content else 0
            if faq_word_count < 400:
                raise ValueError(f"FAQ content too shallow: {faq_word_count} words (minimum: 600). FAQ answers must be detailed and actionable, not just brief responses.")
            
            # Production-level content quality scoring
            # Scoring criteria aligned with SurferSEO standards
            word_score = min(30, (word_count / 3500) * 30)  # 30 points for optimal word count
            research_score = min(25, (source_count / 25) * 25)  # 25 points for research depth  
            data_score = min(15, (data_points / 20) * 15)  # 15 points for quantified data
            structure_score = min(20, (total_sections / 8) * 20)  # 20 points for section structure
            faq_score = min(10, (faq_questions / 15) * 10)  # 10 points for FAQ completeness
            
            quality_score = word_score + research_score + data_score + structure_score + faq_score
            
            # Quality assessment
            if quality_score < 70:
                logger.warning(f"⚠️  Quality below production standard: {quality_score:.1f}/100")
            elif quality_score < 85:
                logger.info(f"✅ Quality meets minimum production standard: {quality_score:.1f}/100")
            else:
                logger.info(f"🏆 Exceptional quality content: {quality_score:.1f}/100")
            
            logger.info(f"📊 Production Quality Metrics:")
            logger.info(f"   - Word count: {word_count} words ({word_count - 3000:+d} vs 3,000 minimum) [{word_score:.1f}/30]")
            logger.info(f"   - Research sources: {source_count} indicators [{research_score:.1f}/25]")
            logger.info(f"   - Data points: {data_points} quantified metrics [{data_score:.1f}/15]")
            logger.info(f"   - Section structure: {total_sections} sections [{structure_score:.1f}/20]")
            logger.info(f"   - FAQ completeness: {faq_questions} questions, {faq_word_count} words [{faq_score:.1f}/10]")
            logger.info(f"   - OVERALL SCORE: {quality_score:.1f}/100 {'✅ PRODUCTION READY' if quality_score >= 85 else '⚠️  NEEDS IMPROVEMENT' if quality_score >= 70 else '❌ BELOW STANDARD'}")
            
        except json.JSONDecodeError:
            # If not valid JSON, just check basic text requirements
            word_count = len(raw_response.split())
            if word_count < 1500:
                raise ValueError(f"Content too short: {word_count} words (minimum 1,500 required)")
            
            logger.warning("Could not parse JSON for detailed validation, but basic word count passed")
