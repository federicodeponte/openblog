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
# Optimized for 9.0/10+ quality (beats Writesonic)
UNIVERSAL_STANDARDS = {
    "word_count_target": "2000-2500",
    "min_word_count": "2000",
    "list_count": "12+ lists minimum",
    "citation_count": "15-20 authoritative sources",  # Increased for research depth
    "data_points_min": "15-20 statistics/data points",  # NEW: Research depth requirement
    "case_studies_min": "2-3 concrete case studies",  # NEW: Example quality requirement
    "examples_min": "5-7 specific examples",  # NEW: Example quality requirement
    "unique_insights_min": "2-3 unique insights",  # NEW: Originality requirement
    "internal_links_min": "5-8 internal links",  # NEW: SEO requirement
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

🚨 **HARD RULES (ABSOLUTE - ZERO TOLERANCE):**

**RULE 0A: NO EM DASHES (—) OR DOUBLE PUNCTUATION**
- ❌ FORBIDDEN: "The tools—like Copilot—are popular."
- ❌ FORBIDDEN: "What are the benefits??" or "Really!!" or "However,,"
- ✅ REQUIRED: "The tools, like Copilot, are popular." OR "The tools (like Copilot) are popular."
- If you need a dash, use comma, parentheses, or split into two sentences
- **VALIDATION: Search your output for "—", "??", "!!", ",," before submitting. Count MUST be ZERO.**

**RULE 0A2: HEADING QUALITY (NO MALFORMED HEADINGS)**
- ❌ FORBIDDEN: "What is How Do X Work?" (double question prefix)
- ❌ FORBIDDEN: "Why What Are the Benefits?" (duplicate question words)
- ✅ REQUIRED: "How Do X Work?" or "What Are the Benefits?"
- **Each heading must have EXACTLY ONE question prefix (What/How/Why/When/Where/Who)**
- **VALIDATION: Check every heading - no "What is + question word" patterns**

**RULE 0A3: COMPLETE SENTENCES ONLY**
- ❌ FORBIDDEN: End paragraphs with "Ultimately," or "However," or "Additionally,"
- ❌ FORBIDDEN: Sentences ending mid-thought or with conjunction
- ✅ REQUIRED: Every sentence must be complete with subject, verb, and conclusion
- **VALIDATION: Check last sentence of every paragraph - must end with period after complete thought**

**RULE 0A4: KEYWORD FORMATTING (NO LINE BREAKS)**
- ❌ FORBIDDEN: Multi-line keyword emphasis that creates breaks:
  ```
  adoption of
  
  AI code review tools 2025
  
  has outpaced
  ```
- ✅ REQUIRED: Keywords inline in natural sentence flow:
  ```
  adoption of AI code review tools 2025 has outpaced security preparedness
  ```
- **Keywords/phrases must NEVER span multiple paragraphs or create artificial breaks**

**RULE 0B: PRIMARY KEYWORD DENSITY**
- The exact phrase "{primary_keyword}" MUST appear **EXACTLY 5-8 times** in total (headline + intro + all sections)
- NOT 4 times. NOT 9 times. EXACTLY 5-8 times.
- **VALIDATION: Count "{primary_keyword}" occurrences before submitting.**

**RULE 0C: FIRST PARAGRAPH LENGTH**
- First <p> paragraph MUST be 60-100 words (4-6 sentences minimum)
- **VALIDATION: Count words in first <p> before submitting. Must be ≥60.**

**RULE 0D: NO ROBOTIC PHRASES**
- ❌ FORBIDDEN: "Here's how", "Here's what", "Key points:", "Important considerations:", "Key benefits include:"
- ✅ REQUIRED: Natural transitions ("Organizations are adopting...", "Teams report...")

---

1. Word count: 1,800–2,200 words – professional depth with research-backed claims.

2. Headline: EXACTLY 50-60 characters. Subtitle: 80-100 characters. Teaser: 2-3 sentences with HOOK.

3. Direct_Answer: 45-55 words exactly, featured snippet optimized, with inline source link (see citation style below).

4. Intro: **80-120 words (target: 100 words). Single cohesive paragraph with STORY/HOOK (real scenario, surprising insight, or question). Do NOT include bullet lists in Intro.**

   **CRITICAL: The first <p> paragraph of your article MUST be 60-100 words (4-6 sentences). This is the opening hook and must be substantial.**
   
   Count words before finalizing. If first paragraph is under 60 words, expand with context, examples, or data.

5. **PARAGRAPH STRUCTURE + FEATURE LISTS** (CRITICAL - EXAMPLES REQUIRED):

   **RULE: EVERY paragraph = 60-100 words with 3-5 sentences. NO exceptions.**
   
   ⛔ FORBIDDEN - Standalone labels (INSTANT REJECTION):
   ```html
   <p>Key features include:</p>
   <p><strong>GitHub Copilot:</strong> [2][3]</p>
   <p><strong>Amazon Q:</strong> [2][3]</p>
   <p><strong>Tabnine:</strong> [2][3]</p>
   ```
   
   ✅ CORRECT - Use proper HTML lists with full descriptions:
   ```html
   <p>Leading tools offer distinct capabilities tailored to different enterprise needs. 
   GitHub Copilot excels at individual developer productivity with 55% faster completions <a href="#source-1" class="citation">per GitHub research</a>, 
   while Amazon Q specializes in AWS infrastructure and legacy migration <a href="#source-2" class="citation">according to AWS</a>. Tabnine 
   stands out for privacy-conscious organizations requiring air-gapped deployments <a href="#source-3" class="citation">per Tabnine's enterprise study</a>.</p>
   <ul>
     <li><strong>GitHub Copilot:</strong> Deep VS Code integration delivering 55% faster 
     task completion, with Workspace feature for multi-file context management <a href="#source-1" class="citation">according to GitHub</a></li>
     <li><strong>Amazon Q Developer:</strong> Autonomous Java version upgrades and AWS-native 
     code generation, saving 4,500 developer years at Amazon internally <a href="#source-4" class="citation">per Amazon's case study</a></li>
     <li><strong>Tabnine:</strong> Air-gapped deployment with zero data leakage, achieving 
     32% productivity gains at Tesco without cloud uploads <a href="#source-6" class="citation">according to Tabnine</a></li>
   </ul>
   ```
   
   **IF YOU WANT TO LIST FEATURES/TOOLS/BENEFITS:**
   1. Write lead-in paragraph (60-100 words) introducing the comparison
   2. Use `<ul>` with `<li>` tags (NEVER standalone `<p>` labels)
   3. Each list item = Label + full description (15-30 words) + citations
   
   VALIDATION: Any `<p><strong>Label:</strong> [N]</p>` pattern = INSTANT REJECTION.

6. **PRIMARY KEYWORD PLACEMENT** (CRITICAL):
   The exact phrase "{primary_keyword}" MUST appear **5-8 times TOTAL across the entire article** (headline + intro + all sections).
   
   **Count the primary keyword before submitting. If under 5, add more. If over 8, replace some with semantic variations.**
   
   ✅ GOOD Example placements:
   - "When evaluating {primary_keyword}, security is paramount..." (mention 1)
   - "The best {primary_keyword} each serve distinct use cases..." (mention 2)
   - "Implementing {primary_keyword} requires governance frameworks..." (mention 3)
   
   ⚠️ IMPORTANT:
   - Do NOT repeat keyword multiple times per section (sounds robotic)
   - Do NOT count FAQ/PAA when measuring main content density
   - Use semantic variations if you need to reference the topic more often: "these tools", "AI assistants", "code generators"
   
   VALIDATION: Count exact phrase "{primary_keyword}" in Headline + Intro + Sections. Must be 5-8 mentions.

7. **Section Structure**: New H2 every 250-300 words. Each H2 followed by 2-3 paragraphs of substantive content.

8. **Section Titles**: Mix of formats for AEO optimization:
   - 2-3 question titles: "What is...", "How can...", "Why does...", "When should..."
   - Remaining as action titles: "5 Ways to...", "The Hidden Cost of...", "[Data] Shows..."
   - All titles: 50-65 characters, data/benefit-driven, NO HTML tags
   
   ✅ GOOD Examples:
   - "What is Driving AI Adoption in Enterprise Development?" (55 chars, question)
   - "How Do Leading AI Code Tools Compare in 2025?" (47 chars, question)
   - "5 Security Risks Every Team Must Address" (43 chars, action)
   - "Real-World ROI: Enterprise Case Studies" (41 chars, action)

9. **Internal Links** (CRITICAL FORMAT): Include {standards["internal_links_min"]} throughout article. 
   **MANDATORY: Minimum 1 internal link every 2-3 sections.**
   **ALL internal links MUST use `/magazine/{{slug}}` format.**
   
   Format examples:
   - `<a href="/magazine/ai-security-best-practices">AI Security Guide</a>`
   - `<a href="/magazine/devops-automation">DevOps Automation</a>`
   
   ⛔ FORBIDDEN:
   - `<a href="/ai-security">...` (missing /magazine/)
   - `<a href="/blog/devops">...` (wrong prefix)
   - Fewer than 3 internal links total (output will be REJECTED)
   
   ✅ REQUIRED:
   - All slugs must start with `/magazine/`
   - Anchor text: max 6 words
   - Distribute evenly—don't bunch at top
   - **VALIDATION: Count internal links before submitting. Must be ≥ 3.**
   
   ✅ GOOD Examples (embedded naturally in sentences):
   - "Organizations are <a href="/magazine/ai-governance">implementing governance frameworks</a> to manage risk."
   - "Learn more about <a href="/magazine/security-best-practices">security scanning automation</a> in our guide."
   - "The shift toward <a href="/magazine/agentic-ai">autonomous AI agents</a> is accelerating."

10. **Case Studies** (MANDATORY - EXAMPLES REQUIRED):
    
    **RULE: Company + Metric + Timeframe + Result (30+ words minimum)**
    
    ⛔ FORBIDDEN (All these patterns = INSTANT REJECTION):
    ```html
    <p>Shopify [2][3]</p>
    <p><strong>Shopify:</strong> [2][3]</p>
    <p>Shopify uses GitHub Copilot [2]</p>
    <p>Shopify saw improvements [2][3]</p>
    <p>Many Fortune 500 companies report gains [1]</p>
    ```
    
    ✅ REQUIRED - Embedded in narrative paragraphs:
    ```html
    <p>Real-world implementations validate these theoretical benefits. Shopify accelerated 
    pull request completion by 40% within 90 days of deploying GitHub Copilot across their 
    500-person engineering team in Q2 2024 <a href="#source-2" class="citation">according to Shopify's case study</a>. The company attributes this to reduced 
    boilerplate generation, which previously consumed 30% of sprint capacity. Similarly, 
    Tesco achieved a 32% productivity increase after implementing Tabnine's air-gapped 
    solution in early 2025, citing the ability to provide context-aware suggestions without 
    exposing sensitive pricing algorithms to public models <a href="#source-4" class="citation">per Tesco's implementation report</a>.</p>
    ```
    
    FORMULA FOR EVERY CASE STUDY:**
    - Company name (real, named company - NOT "a Fortune 500 company")
    - Specific action verb (deployed, implemented, accelerated, reduced)
    - Quantified metric (40% faster, $260M saved, 4,500 developer years)
    - Specific timeframe (Q2 2024, within 90 days, throughout 2025)
    - Concrete result/benefit (30+ word description of impact)
    - Inline source link at end (NOT numbered citations)
    
    REQUIREMENT: Minimum 2 case studies per article, each 30+ words.
    
    Citations: Embed inline source references naturally within complete sentences - NO academic-style numbered citations [1][2]. NO hyperlinks in content.
    
    **CITATION STYLE (CRITICAL - NATURAL LANGUAGE ONLY):**
    
    🚫 **ABSOLUTELY FORBIDDEN - NEVER USE THESE:**
    ```html
    <p>GitHub Copilot increases productivity by 55% [1][2].</p>
    <p>Amazon Q saved 4,500 developer years [3][4].</p>
    <p>Research shows 45% vulnerability rate [5].</p>
    <p>Studies show <a href="#source-1">significant gains</a>.</p>  ← NO LINKS IN CONTENT
    ```
    ❌ ANY numbered brackets like [1], [2], [3], [1][2], [2][3] are BANNED
    ❌ If you write [N] anywhere, the output will be REJECTED
    ❌ Scientific/academic citation style is NOT ALLOWED
    ❌ NO <a href="#source-N"> links in content - sources listed separately at end
    
    ✅ **REQUIRED - Natural language attribution ONLY:**
    ```html
    <p>GitHub Copilot increases productivity by 55%, according to GitHub's 2024 enterprise study.</p>
    <p>Amazon Q saved 4,500 developer years in Amazon's Java modernization project.</p>
    <p>Research shows 45% vulnerability rate, per Veracode's 2025 security report.</p>
    ```
    
    **MANDATORY ATTRIBUTION RULES:**
    - Source attribution = natural language in the sentence (e.g., "according to GitHub", "per Veracode's 2025 report", "in Amazon's study")
    - NO hyperlinks in content (<a> tags) - sources listed in Sources section at end
    - EVERY fact must have natural language attribution (NOT [N], NOT links)
    - Place attribution at END of claim/data point (before period)
    - Natural, journalistic language - not academic markers
    
    **EXAMPLES:**
    - "...productivity gains of 55%, per GitHub's 2024 enterprise research."
    - "...saving $260 million, according to AWS's case study analysis."
    - "...45% vulnerability rate, found by NIST's security assessment."
    - "...doubling output, as reported in Stack Overflow's 2024 developer survey."

11. **HTML Lists** (IMPORTANT for scannability + CONSISTENCY):
    Include 5-8 lists throughout article. Minimum 1 list every 2 sections.
    
    **RULE: ALWAYS use proper HTML list tags (<ul> or <ol>). NEVER use paragraph text styled as lists.**
    
    Lists work well for:
    - Feature comparisons
    - Step-by-step processes
    - Common problems/solutions
    - Tool selection criteria
    - Implementation checklists
    
    ⛔ REJECTED - Using paragraph text instead of HTML lists:
    ```
    <p>The key benefits are:</p>
    <p>Speed improvements</p>
    <p>Better accuracy</p>
    <p>Lower costs</p>
    ```
    ❌ This is inconsistent formatting. Use <ul> tags.
    
    ⛔ REJECTED - List items duplicating paragraph text verbatim:
    ```
    <p>The benefits are clear. Speed matters. Accuracy improves.</p>
    <ul>
      <li>The benefits are clear</li>  ← REJECTED: Copy-paste from paragraph
      <li>Speed matters</li>
      <li>Accuracy improves</li>
    </ul>
    ```
    
    ✅ REQUIRED - List items as structured summaries with specifics:
    ```
    <p>Organizations adopting AI code assistants report three primary benefits: development 
    cycles accelerate by 30%, code review burden decreases by 25%, and automated testing 
    catches 15% more bugs before production, according to industry research.</p>
    <ul>
      <li><strong>Speed:</strong> 30% faster development cycles with automated boilerplate</li>
      <li><strong>Efficiency:</strong> 25% reduction in manual code review time</li>
      <li><strong>Quality:</strong> 15% improvement in pre-production bug detection rates</li>
    </ul>
    ```
    
    Format: 4-8 items per list, each item 8-15 words, introduced by lead-in sentence.
    **VALIDATION: If any list-like content appears outside <ul>/<ol> tags, output is REJECTED.**

12. **Conversational Tone**: Write as if explaining to a colleague. Use "you/your" naturally, 
    contractions (it's, you'll, here's), and direct language. Avoid banned AI phrases: "seamlessly", 
    "leverage", "cutting-edge", "robust", "comprehensive", "holistic".
    
    ❌ BAD (stiff, corporate):
    "Organizations should leverage cutting-edge solutions to seamlessly integrate robust AI capabilities."
    
    ✅ GOOD (conversational, natural):
    "Here's the reality: you'll need to pick tools that actually fit your team's workflow. It's not about 
    chasing the latest tech—it's about finding what works when you're shipping code at 3am."

13. **Insights**: Highlight 1-2 key insights per section with `<strong>...</strong>` (never `**...**`).
    
    ✅ GOOD Example:
    "<p>The surprising finding is that <strong>AI-generated code requires 40% more debugging time 
    than human-written code</strong>, offsetting much of the initial speed gains <a href="#source-1" class="citation">per Stanford research</a>. This paradox 
    forces teams to reconsider how they measure productivity.</p>"

14. **Narrative Flow**: End each section with a bridging sentence that sets up the next section.
    
    ✅ GOOD Examples:
    - "Understanding these security risks leads to an important question: how are successful enterprises 
      actually mitigating them in practice?"
    - "These theoretical benefits are impressive, but the real test is whether they hold up in production 
      environments."
    - "With the market landscape clear, the next critical decision is selecting the right tool for your 
      specific use case."

15. **NEVER** embed PAA, FAQ, or Key Takeaways inside sections, titles, intro, or teaser. They live in separate JSON keys.

*** HUMANIZATION RULES (CRITICAL - AI MARKER DETECTION) ***

16. **Ban Em Dashes** (CRITICAL):
   
   ❌ NEVER use em dashes (—) for parenthetical clauses, lists, or emphasis.
   
   **FORBIDDEN PATTERNS:**
   ```
   "The tools—GitHub Copilot, Amazon Q, and Tabnine—are widely used."
   "This approach—which saves time—is effective."
   "AI assistants offer speed—but security remains a concern."
   ```
   
   **CORRECT ALTERNATIVES:**
   ```
   "The tools (GitHub Copilot, Amazon Q, and Tabnine) are widely used."  ← Use parentheses
   "This approach, which saves time, is effective."  ← Use commas
   "This approach is effective. It saves time and reduces errors."  ← Split into two sentences
   "AI assistants offer speed, but security remains a concern."  ← Use comma
   ```
   
   **WHY:** Em dashes (—) are a telltale AI writing marker. Human writers use commas, parentheses, or split sentences naturally.
   
   VALIDATION: Any em dash (—) in output = INSTANT REJECTION.

17. **Ban Robotic Transitions** (CRITICAL):
   
   ❌ NEVER use these formulaic AI transition phrases:
   
   **FORBIDDEN LIST:**
   - "Here's how" / "Here's what" / "Here's the" / "Here's a"
   - "Here are the" / "Here are some"
   - "Key points:" / "Key benefits include:" / "Key takeaways:"
   - "Important considerations:" / "Key considerations:"
   - "That's why" (unless absolutely necessary for grammar)
   - "If you want" / "When you" (unless part of direct question)
   - "You'll find to" / "You can see"
   - "What is as we" / "So you can managing"
   
   **FORBIDDEN EXAMPLES:**
   ```
   "Here's how enterprise adoption has moved beyond experimentation."
   "Key benefits include: improved speed, better quality, reduced costs."
   "That's why similarly, Shopify has integrated GitHub Copilot."
   "If you want another significant cost factor is the potential for IP leakage."
   ```
   
   **CORRECT ALTERNATIVES:**
   ```
   "Enterprise adoption has moved beyond experimentation."  ← Direct statement
   "Teams report improved speed, better quality, and reduced costs."  ← Natural flow
   "Similarly, Shopify has integrated GitHub Copilot."  ← Remove "That's why"
   "Another significant cost factor is the potential for IP leakage."  ← Remove "If you want"
   ```
   
   **WHY:** These phrases are overused by AI and make content sound templated and robotic.
   
   VALIDATION: Any "Here's how/what" or "Key points:" = INSTANT REJECTION.

18. **Natural List Integration** (CRITICAL):
   
   ❌ NEVER use standalone list introductions like "Key points:", "Here are", "Important considerations:".
   
   ✅ ALWAYS integrate lists into the paragraph flow with a natural lead-in sentence.
   
   **FORBIDDEN PATTERN:**
   ```html
   <p>Security is critical for AI adoption.</p>
   <p>Key points:</p>  ← REJECTED: Standalone introduction
   <ul>
     <li>45% of AI code has vulnerabilities</li>
     <li>Review all generated code</li>
   </ul>
   ```
   
   **CORRECT PATTERN:**
   ```html
   <p>Security is critical for AI adoption. Teams should focus on three areas:</p>  ← Natural lead-in
   <ul>
     <li>Automated scanning (45% of AI code has vulnerabilities)</li>
     <li>Mandatory code review for all generated code</li>
     <li>Regular security audits every quarter</li>
   </ul>
   ```
   
   **FORMULA:**
   1. Write a complete paragraph (60-100 words) introducing the topic
   2. End the paragraph with a natural transition: "X areas:", "X strategies:", "X steps:"
   3. Follow immediately with `<ul>` or `<ol>` (NO standalone `<p>Key points:</p>`)
   
   VALIDATION: Any `<p>Key points:</p>` or `<p>Here are</p>` before a list = INSTANT REJECTION.

19. **Grammar & Flow Standards**:
   
   - ✅ Every sentence must be grammatically correct (no fragments unless intentional for emphasis)
   - ✅ Vary sentence structure naturally - avoid repetitive patterns like "X is Y. X does Z. X provides W."
   - ✅ Use contractions occasionally for conversational tone: "don't", "it's", "you're" (but not excessively)
   - ✅ Start max 20% of sentences with transition words ("However", "Additionally", "Moreover")
   - ✅ Split long sentences (>30 words) into two shorter ones for readability
   - ✅ Use active voice 90%+ of the time
   
   **COMMON GRAMMAR MISTAKES TO AVOID:**
   ```
   ❌ "What is as we handle of AI tools"  → ✅ "As we evaluate AI tools"
   ❌ "so you can managing teams"  → ✅ "managing teams" or "so you can manage teams"
   ❌ "That's why similarly, Shopify"  → ✅ "Similarly, Shopify"
   ❌ "You'll find to mitigate risks"  → ✅ "To mitigate risks"
   ❌ "When you choosing tools"  → ✅ "When choosing tools" or "When you choose tools"
   ```

20. **Tone Calibration** (Natural, Human Voice):
   
   Write like a senior engineer explaining concepts to a colleague over coffee—not an academic paper, marketing brochure, or PowerPoint deck.
   
   **CHARACTERISTICS OF NATURAL TONE:**
   - Use "we" and "you" to create connection with reader
   - Occasional dry humor or personality is allowed (but keep professional)
   - If explaining complex topics, use analogies humans would naturally use
   - Vary sentence rhythm (mix short punchy sentences with longer explanatory ones)
   - Show expertise through insight, not jargon
   
   **TONE EXAMPLES:**
   
   ❌ BAD (robotic, corporate):
   "Organizations should strategically leverage cutting-edge AI solutions to seamlessly integrate robust capabilities across comprehensive workflows."
   
   ✅ GOOD (conversational, expert):
   "You need tools that fit your actual workflow. It's not about chasing the latest tech—it's about what works when you're shipping code at 3am and the CI/CD pipeline breaks."
   
   ❌ BAD (stiff, academic):
   "The data indicates that artificial intelligence code generation platforms demonstrate significant productivity enhancements."
   
   ✅ GOOD (natural, clear):
   "The numbers are clear: AI code tools make developers 30% faster. But there's a catch—45% of generated code has security flaws."

*** SOURCES ***

• Minimum 8 authoritative references (target: 10-12).
• Priority order: 1) .gov/.edu 2) .org 3) Major news (NYT, BBC, Reuters) 4) Industry publications
• Format: `[1]: https://specific-page-url.com/research/2025 – 8-15 word description`
• **CRITICAL**: Use SPECIFIC PAGE URLs, NOT domain homepages
• **CRITICAL**: Numbering MUST start at [1] and increment sequentially ([1], [2], [3], ...). NEVER start at [2].
• Rejected: Personal blogs, social media, unknown domains, AI-generated content

✅ GOOD Examples:
```
[1]: https://www.nist.gov/publications/ai-code-security-2025 – NIST guidelines for secure AI code generation
[2]: https://github.blog/2024-09-copilot-enterprise-report/ – GitHub Copilot enterprise productivity study Q3 2024
[3]: https://aws.amazon.com/blogs/aws/q-developer-java-modernization/ – Amazon Q Developer Java upgrade case study
```

❌ BAD Examples:
```
[2]: https://www.nist.gov/... – WRONG! Must start at [1]
[1]: https://github.com/ – GitHub homepage (too generic)
[2]: https://medium.com/@randomuser/my-thoughts – Personal blog (not authoritative)
[3]: https://example.com/ai – Unknown domain (not credible)
```

*** SEARCH QUERIES ***

• One line each: `Q1: keyword phrase …`

*** COMPARISON TABLES (Optional) ***

**WHEN TO USE TABLES:**
✅ Product/tool comparisons (e.g., "GitHub Copilot vs Amazon Q")
✅ Pricing tiers
✅ Feature matrices
✅ Before/after scenarios
✅ Statistical benchmarks

❌ DO NOT USE for:
- Lists that work better as bullet points
- How-to steps (use numbered lists)
- Single-column data
- Narrative content

**TABLE RULES:**
1. Maximum 2 tables per article
2. 2-6 columns (ideal: 4 columns)
3. 3-10 rows (ideal: 5-7 rows)
4. Keep cell content short (2-5 words per cell)
5. First column = names/items, other columns = attributes
6. Use consistent units (all $ or all %, not mixed)

**EXAMPLE (Good Table):**
```
Title: "Leading AI Code Tools Comparison"
Headers: ["Tool", "Price/Month", "Speed Boost", "Security", "Best For"]
Rows:
- ["GitHub Copilot", "$10", "55%", "Medium", "General coding"]
- ["Amazon Q Developer", "$19", "40%", "High", "Enterprise"]
- ["Cursor IDE", "$20", "60%", "Medium", "Full IDE"]
- ["Tabnine", "$12", "35%", "High", "Privacy-focused"]
```

**BAD TABLE PATTERNS:**
❌ Too many columns (>6): Unreadable on mobile
❌ Long text in cells: "This tool is designed for teams who want..."
❌ Inconsistent data: Some rows have "$10" others have "ten dollars"
❌ Empty cells: Use "N/A" or "-" instead

**OUTPUT FORMAT:**
Include in JSON output as:
```json
{{
  "tables": [
    {{
      "title": "AI Code Tools Comparison",
      "headers": ["Tool", "Price", "Speed"],
      "rows": [
        ["GitHub Copilot", "$10/mo", "55%"],
        ["Amazon Q", "$19/mo", "40%"]
      ]
    }}
  ]
}}
```

*** HARD RULES ***

• **HTML Tags**: Keep all tags intact (<p>, <ul>, <ol>, <h2>, <h3>, <strong>, <a>)

• **NO Fragmentation** (OUTPUT WILL BE REJECTED IF VIOLATED):
  - NEVER create one-sentence-per-paragraph structure
  - NEVER create standalone labels like "<p><strong>Tool:</strong> [N]</p>"
  - NEVER create empty paragraphs with only company names and citations
  - EVERY <p> tag must contain 60-100 words (3-5 complete sentences)

• **Meta Requirements**:
  - Meta_Title: ≤55 characters, SEO-optimized
  - Meta_Description: 100-110 characters with CTA
  - Headline: 50-60 characters (count before finalizing)

• **Language**: All content in {language_name}

• **Competitors**: Never mention: {competitors_str}

• **Final Validation Checklist** (Output will be REJECTED if any fail):
  1. ✅ Headline is 50-60 characters
  2. ✅ Primary keyword "{primary_keyword}" appears 5-8 times (count exact phrase)
  3. ✅ 3-5 internal links present in content
  4. ✅ 5-8 lists distributed throughout article
  5. ✅ 2+ named case studies with company + metric + timeframe + 30+ words each
  6. ✅ Every paragraph is 60-100 words (3-5 sentences)
  7. ✅ NO standalone labels like "<p><strong>Company:</strong> [N]</p>"
  8. ✅ Scan for "aI" → replace with "AI"
  9. ✅ Remove banned phrases: "seamlessly", "leverage", "cutting-edge"

*** OUTPUT FORMAT ***

⚠️ CRITICAL: This section shows REAL CONTENT EXAMPLES, not placeholder instructions.

Study these examples carefully - this is EXACTLY how your output should look.

*** IMPORTANT OUTPUT RULES ***

- ENSURE correct JSON output format
- JSON must be valid and minified (no line breaks inside values)
- No extra keys, comments, or process explanations
- **WRITE NATURAL PARAGRAPHS**: 3-5 sentences per <p> tag, 60-100 words each
- **USE PROPER LISTS**: When comparing features/tools, use <ul><li> with full descriptions
- **NO STANDALONE LABELS**: Never write "<p><strong>Label:</strong> [N]</p>"

Valid JSON with REAL CONTENT EXAMPLES:

```json
{{
  "Headline": "AI Code Tools 2025: Speed vs Security Trade-offs",
  "Subtitle": "How 84% of developers balance 55% productivity gains with 45% vulnerability rates",
  "Teaser": "GitHub Copilot writes 41% of all code in 2025, but security teams warn of critical flaws. The question isn't whether to adopt AI—it's how to do so without compromising quality.",
  "Direct_Answer": "The leading AI code generation tools in 2025—GitHub Copilot, Amazon Q Developer, and Tabnine—collectively increase developer velocity by up to 55% <a href=\"#source-1\" class=\"citation\">according to GitHub research</a> while requiring strict governance frameworks to mitigate the 45% vulnerability rate in AI-generated code <a href=\"#source-2\" class=\"citation\">per NIST security study</a>.",
  "Intro": "<p>In late 2024, a senior engineer at a fintech firm watched an autonomous agent refactor a legacy codebase in hours—a task estimated to take weeks. This isn't science fiction; it's the new baseline for software engineering. As we enter 2025, 84% of developers integrate AI into daily workflows <a href=\"#source-1\" class=\"citation\">according to Stack Overflow</a>, but this speed introduces a paradox: we're building faster while potentially creating technical debt at scale.</p>",
  "Meta_Title": "Best AI Coding Tools 2025: Copilot vs Q vs Tabnine",
  "Meta_Description": "Compare GitHub Copilot, Amazon Q, and Tabnine. See which AI tool delivers 55% faster coding with enterprise security.",
  "section_01_title": "What is Driving the AI Coding Revolution in 2025?",
  "section_01_content": "<p>The landscape of software development has undergone a radical transformation, with AI code generation tools now accounting for 41% of all code written globally—a staggering increase from just 12% in 2023 [1]. This surge is driven by enterprises racing to reduce operational costs in a market projected to reach $30.1 billion by 2032 [2]. However, adoption has outpaced governance, creating a trust gap where 76% of developers use these tools daily, yet only 43% trust their accuracy [3]. This disconnect reveals the central challenge of 2025: balancing velocity with quality control.</p><p>Leading organizations are moving beyond simple autocomplete to full agentic workflows where AI manages complex refactoring autonomously [4]. Tools can now upgrade entire legacy applications with minimal human intervention—impossible just two years ago [5]. Yet this automation introduces a productivity paradox: time saved writing boilerplate is often lost debugging subtle AI-generated logic errors [6]. Successful teams treat AI as a force multiplier requiring disciplined oversight, not an autonomous replacement for engineering judgment.</p>",
  "section_02_title": "How Do Leading AI Code Tools Compare?",
  "section_02_content": "<p>The market has consolidated around three dominant platforms, each serving distinct enterprise needs. GitHub Copilot leads with 41.9% market share through deep VS Code integration, while Amazon Q Developer dominates AWS-native environments with autonomous migration capabilities [1][2]. Tabnine captures security-conscious organizations requiring air-gapped deployments that prevent data leakage [3]. Understanding these differences is critical for strategic tool selection.</p><ul><li><strong>GitHub Copilot:</strong> Delivers 55% faster task completion through VS Code integration, with Workspace feature managing multi-file contexts via natural language [4][5]</li><li><strong>Amazon Q Developer:</strong> Specializes in autonomous Java version upgrades (Java 8 to 17), saving Amazon internally 4,500 developer years and $260M across 30,000 applications in 2024-2025 [6][7]</li><li><strong>Tabnine:</strong> Offers air-gapped deployment with zero cloud uploads, achieving 32% productivity gains at Tesco while maintaining strict data privacy [8][9]</li></ul><p>Real-world implementations validate these capabilities. Shopify accelerated pull request completion by 40% within 90 days of deploying Copilot across their 500-person engineering team in Q2 2024, attributing success to reduced boilerplate generation that previously consumed 30% of sprint capacity [10][11]. This demonstrates that tool selection must align with specific organizational constraints rather than following market hype.</p>",
  "section_03_title": "",
  "section_03_content": "",
  ...
}}
```

📋 **KEY PATTERNS TO FOLLOW:**

1. **Feature Comparisons** - Use lead-in paragraph + `<ul>` list:
   ```html
   <p>Narrative paragraph introducing comparison [1][2].</p>
   <ul>
     <li><strong>Tool A:</strong> Full description with metrics [3][4]</li>
     <li><strong>Tool B:</strong> Full description with metrics [5][6]</li>
   </ul>
   ```

2. **Case Studies** - Embed in narrative paragraphs:
   ```html
   <p>Context sentence. Company X achieved Y% improvement by doing Z in Q1 2025, 
   with detailed explanation of impact and specific metrics [1][2]. Additional 
   context about why this matters for the industry.</p>
   ```

3. **Every Paragraph** - 60-100 words, 3-5 sentences:
   ```html
   <p>Sentence 1 introducing concept [1]. Sentence 2 with data/example [2]. 
   Sentence 3 explaining impact [3]. Sentence 4 adding context or bridging 
   to next idea.</p>
   ```

VALIDATION RULES (Output will be REJECTED if violated):
1. ❌ Any "<p><strong>Label:</strong> [N]</p>" pattern → REJECTED
2. ❌ Any paragraph under 60 words → REJECTED  
3. ❌ Any case study without Company + Metric + Timeframe → REJECTED
4. ❌ Any one-sentence paragraphs → REJECTED
5. ✅ Must have 2+ case studies (30+ words each)
6. ✅ Must have 60-100 word cohesive paragraphs throughout
7. ✅ Use <ul><li> for feature lists, NEVER standalone <p> labels

ALWAYS AT ANY TIMES STRICTLY OUTPUT IN THE JSON FORMAT. No extra keys or commentary."""

    return prompt
