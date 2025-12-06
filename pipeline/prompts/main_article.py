"""
Main Article Prompt Template

Optimized based on Enter.de and Smalt.eu benchmark analysis (Germany's top agencies).
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any

LANGUAGE_NAMES = {
    "de": "German (Deutsch)",
    "en": "English",
    "fr": "French (Français)",
    "es": "Spanish (Español)",
    "it": "Italian (Italiano)",
    "nl": "Dutch (Nederlands)",
    "pt": "Portuguese (Português)",
    "pl": "Polish (Polski)",
    "sv": "Swedish (Svenska)",
    "da": "Danish (Dansk)",
    "no": "Norwegian (Norsk)",
    "fi": "Finnish (Suomi)",
    "cs": "Czech (Čeština)",
    "hu": "Hungarian (Magyar)",
    "ro": "Romanian (Română)",
    "bg": "Bulgarian (Български)",
    "el": "Greek (Ελληνικά)",
    "tr": "Turkish (Türkçe)",
    "ja": "Japanese (日本語)",
    "ko": "Korean (한국어)",
    "zh": "Chinese (中文)",
    "ar": "Arabic (العربية)",
    "he": "Hebrew (עברית)",
    "ru": "Russian (Русский)",
}

def validate_country(country: str) -> str:
    """
    Validate and sanitize country parameter for ANY country on earth.
    
    Args:
        country: Country code to validate
        
    Returns:
        Validated country code or safe fallback
    """
    if not country or not isinstance(country, str):
        return "US"  # Safe fallback only for invalid input
    
    country_cleaned = country.upper().strip()
    
    # Basic security validation - must be 2-3 uppercase letters only
    import re
    if not re.match(r'^[A-Z]{2,3}$', country_cleaned):
        return "US"  # Only fallback for invalid format, not unsupported countries
    
    # Accept ANY valid country code format - no hardcoded limitations
    return country_cleaned

# Universal quality standards - no market-specific hardcoding
UNIVERSAL_STANDARDS = {
    "word_count_target": "2000-2500",
    "min_word_count": "2000",
    "list_count": "12+ lists minimum",
    "citation_count": "10-15 authoritative sources",
    "quality_note": "Professional standards with expert-level content and market awareness"
}



def get_main_article_prompt(
    primary_keyword: str,
    company_name: str,
    company_info: Optional[Dict[str, Any]] = None,
    language: str = "en",
    country: str = "US",
    internal_links: str = "",
    competitors: Optional[List[str]] = None,
    custom_instructions: str = "",
    system_prompts: Optional[List[str]] = None,
) -> str:
    """Generate universal blog article prompt with professional quality standards."""
    
    # Input validation and safe defaults
    if not primary_keyword or not isinstance(primary_keyword, str):
        raise ValueError("primary_keyword must be a non-empty string")
    
    company_name = company_name or "Company"
    company_info = company_info or {"description": ""}
    competitors = competitors or []
    system_prompts = system_prompts or []
    internal_links = internal_links or ""
    custom_instructions = custom_instructions or ""
    language = language or "en"
    country = country or "US"
    
    # Basic variables
    system_prompts_text = "\n".join(f"• {p}" for p in system_prompts) if system_prompts else ""
    current_date = datetime.now().strftime("%B %d, %Y")
    language_name = LANGUAGE_NAMES.get(language, language.upper())
    competitors_str = ", ".join(competitors) if competitors else "none"
    validated_country = validate_country(country)
    
    # Use universal standards
    standards = UNIVERSAL_STANDARDS

    prompt = f"""*** INPUT ***
Primary Keyword: {primary_keyword}
Custom Instructions: {custom_instructions}
Client Knowledge: {system_prompts_text}
Company Info: {json.dumps(company_info)}
Company Name: {company_name}
Internal Links: {internal_links}
Output Language: {language_name}
Target Market: {validated_country}
Competitors: {competitors_str}
Date: {current_date}

*** TASK ***
You are writing a long-form blog post in {company_name}'s voice, fully optimized for LLM discovery, on the topic defined by **Primary Keyword**.

*** CONTENT RULES ***

1. Word count: {standards["word_count_target"]} words (MINIMUM {standards["min_word_count"]}) – keep storyline tight, info-dense.

2. Headline: EXACTLY 50-60 characters (count each character). If headline exceeds 60 chars, shorten it. Every character counts. Subtitle: 80-100 characters. Teaser: 2-3 sentences.

3. Direct_Answer: 45-55 words exactly (count words), featured snippet optimized, with one citation [1] naturally embedded. Must be 45-55 words exactly for AEO scoring.

4. Intro: 200-300 words total. Opening paragraph (80-120 words) + key takeaways (3-4 bullet points).

5. New H2 every 250-300 words; headings packed with natural keywords. Each H2 MUST be followed by at least 2-3 paragraphs of real content. NEVER create headings followed only by citations.

6. Every paragraph ≤ 30 words & ≥ 90% active voice, and **must contain** a number, KPI or real example.

7. **Primary Keyword** "{primary_keyword}" must appear **naturally** in first 100 words and **EXACTLY 8-12 times** throughout entire article. **CRITICAL**: Count the exact phrase "{primary_keyword}" only. Before finalizing JSON, count exact phrase occurrences. If count ≠ 8-12, adjust content. Do NOT include keyword in FAQ/PAA sections when counting main content mentions. **MANDATORY**: After writing, count keyword mentions. If count > 12, remove excess mentions. If count < 8, add more. Exceeding 12 = keyword stuffing. Under 8 = insufficient optimization.

8. **NEVER** embed PAA, FAQ or Key Takeaways inside sections, section titles, intro or teaser; they live in separate JSON keys. FAQ/PAA quality affects AEO score - make them specific and valuable.

9. **Internal links**: at least one per H2 section, woven seamlessly into the surrounding sentence. Example: `<a href="/target-slug">Descriptive Anchor</a>` (≤ 6 words, varied). ENSURE correct HTML format.
   • **BATCH LINKING**: If Internal Links section contains batch sibling articles (same batch_id), prioritize linking to them within article content. Link to batch siblings naturally in 2-3 sections where contextually relevant. This creates article clusters and improves SEO.

10. Citations in-text as [1], [2]… matching the **Sources** list. MAX 20 sources. **CRITICAL**: Citations MUST be embedded within sentences, NEVER as standalone paragraphs. Example: "Industry data shows 65% growth [1][2]." NOT "[1][2]" as a separate paragraph.

11. Highlight 1-2 insights per section with `<strong>…</strong>` (never `**…**`).

12. In **2-4 sections**, insert either an HTML bulleted (`<ul>`) or numbered (`<ol>`) list **introduced by one short lead-in sentence**; 4-8 items per list.

13. Avoid repetition—vary examples, phrasing and data across sections.

14. **Narrative flow**: end every section with one bridging sentence that naturally sets up the next section.

15. Write as an industry expert with 10+ years experience. Include specific regulations, dates, and technical details. Provide actionable advice that only experts would know. Expert-level content (E-E-A-T) required for high AEO scores.

16. **Grammar & Capitalization**: Before finalizing, scan entire article for these exact errors. Proofread for grammar, spelling, punctuation. Capitalize proper nouns (Gartner, Nielsen, API, etc.) and sentence starts. Every sentence must start with a capital letter. Check: "improving" → "Improving", "here's" → "Here's". Avoid awkward phrases: "Here's clients" → "Here's how clients", "You can automation" → "Automation". **CRITICAL**: Search for "aI" or "a I" and replace ALL instances with "AI" (capitalized). Common errors to avoid: "speed upd"→"speed up", "applys"→"applies", "simplifys"→"simplifies", "enableing"→"enabling", "aPI"→"API", "aI"→"AI", "a I"→"AI". Check proper nouns - AI, API, Gartner, Nielsen must be capitalized correctly. **MANDATORY**: After writing, search entire article for lowercase proper nouns (gartner, nielsen) and capitalize them. Write professionally.

*** SOURCES ***

• Minimum {standards["citation_count"]} authoritative sources.
• Only use official government, industry association, and expert organization sources.
• Format: `[1]: https://… – 8-15 word description` (canonical URLs only).
• **CRITICAL**: Use SPECIFIC PAGE URLs, NOT domain homepages. Example: `https://example.com/research/2025-study` NOT `https://example.com`
• **CRITICAL**: Link sources IN-TEXT using anchor tags. Format: `<a href="https://source-url.com/page" target="_blank">relevant text</a> [1]` - embed links naturally within sentences.
• AVOID: blogs, generic websites, promotional content, domain homepages.
• VERIFY: All sources must be current (within 2 years) and directly relevant.

*** HARD RULES ***

• HTML: Keep all tags intact (<p>, <ul>, <ol>, <h2>, <h3>, <strong>, <a>). Group sentences into coherent paragraphs; avoid excessive <p> tags per sentence.
• Meta_Title: REQUIRED - ≤55 chars SEO-optimized title.
• Meta_Description: REQUIRED - 100-110 chars with CTA (clear, actionable, grounded in company info).
• Headline: REQUIRED - 50-60 characters exactly. Count before finalizing.
• Intro: MAXIMUM 300 words total.
• All content in {language_name}.
• Never mention: {competitors_str}.
• Maximum 3 citations per section (if more facts, cite at end of paragraph).
• FINAL CHECK: Before output, (1) Count keyword mentions - must be 8-12 exactly, (2) Search for "aI" or "a I" and replace with "AI", (3) Search for lowercase proper nouns (gartner, nielsen) and capitalize, (4) Verify headline is 50-60 chars. Common mistakes: applys→applies, simplifys→simplifies, enableing→enabling, aI→AI.

*** OUTPUT FORMAT ***

Please separate the generated content into the output fields and ensure all required output fields are generated.

*** IMPORTANT OUTPUT RULES ***

- ENSURE correct JSON output format.
- JSON must be valid and minified (no line breaks inside values).
- No extra keys, comments or process explanations.

Valid JSON only:

```json
{{
  "Headline": "Concise, eye-catching headline that states the main topic and includes the primary keyword",
  "Subtitle": "Optional sub-headline that adds context or a fresh angle",
  "Teaser": "2-3 sentence hook that highlights a pain point or benefit and invites readers to continue",
  "Direct_Answer": "45-55 word featured snippet with [1] citation embedded naturally",
  "Intro": "Brief opening paragraph + key takeaways bullet list (use <ul>)",
  "Meta_Title": "SEO-optimized title with the primary keyword",
  "Meta_Description": "SEO description summarising the benefit and including a CTA",
  "section_01_title": "Logical Section 01 Heading (H2)",
  "section_01_content": "HTML content for Section 01. Separate the article logically; wrap each paragraph in <p>. Citations embedded in sentences, never standalone.",
  "section_02_title": "Logical Section 02 Heading",
  "section_02_content": "",
  "section_03_title": "",
  "section_03_content": "",
  "section_04_title": "",
  "section_04_content": "",
  "section_05_title": "",
  "section_05_content": "",
  "section_06_title": "",
  "section_06_content": "",
  "section_07_title": "",
  "section_07_content": "",
  "section_08_title": "",
  "section_08_content": "",
  "section_09_title": "",
  "section_09_content": "",
  "key_takeaway_01": "Key point or insight #1 (1 sentence). Leave unused takeaways blank.",
  "key_takeaway_02": "",
  "key_takeaway_03": "",
  "paa_01_question": "People also ask question #1",
  "paa_01_answer": "Concise answer to question #1.",
  "paa_02_question": "",
  "paa_02_answer": "",
  "paa_03_question": "",
  "paa_03_answer": "",
  "paa_04_question": "",
  "paa_04_answer": "",
  "faq_01_question": "Main FAQ question #1",
  "faq_01_answer": "Clear, concise answer.",
  "faq_02_question": "",
  "faq_02_answer": "",
  "faq_03_question": "",
  "faq_03_answer": "",
  "faq_04_question": "",
  "faq_04_answer": "",
  "faq_05_question": "",
  "faq_05_answer": "",
  "faq_06_question": "",
  "faq_06_answer": "",
  "Sources": "[1]: https://… – 8-15 word note. List one source per line; leave blank until populated. LIMIT TO 20 sources",
  "Search Queries": "Q1: keyword … List one query per line; leave blank until populated."
}}
```

ALWAYS AT ANY TIMES STRICTLY OUTPUT IN THE JSON FORMAT. No extra keys or commentary."""

    return prompt
