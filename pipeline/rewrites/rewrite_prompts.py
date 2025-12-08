"""
Surgical Edit Prompt Templates

Prompt templates for targeted article rewrites.
"""

from typing import Dict, Any


def get_quality_fix_prompt(
    original_content: str,
    instruction: str,
    target_field: str,
    context: Dict[str, Any] = None
) -> str:
    """
    Build prompt for quality fix mode (Stage 2b).
    
    Goal: Fix specific quality issues while preserving everything else.
    """
    
    context = context or {}
    primary_keyword = context.get("primary_keyword", "")
    
    return f"""You are performing a TARGETED QUALITY FIX on an existing article section.

Your job is to fix a SPECIFIC ISSUE while keeping everything else identical.

*** ORIGINAL CONTENT ***

{original_content}

*** ISSUE TO FIX ***

{instruction}

*** YOUR TASK ***

Apply ONLY the fix described above. Do NOT:
- Rewrite from scratch
- Change facts, data, or statistics
- Remove or modify citations ([N])
- Remove or modify internal links (<a href="/magazine/...">)
- Change the overall structure or flow
- Add new information (unless expanding a short paragraph)

DO:
- Make the MINIMUM changes needed to fix the issue
- Preserve all HTML tags exactly as they are
- Keep the same tone and style
- Maintain paragraph lengths (unless the issue is paragraph length itself)
- Keep citation numbers in the same positions

*** VALIDATION CHECKLIST ***

Before submitting:
1. ✅ Issue is fixed (check the instruction again)
2. ✅ All other content is preserved
3. ✅ HTML structure is intact (<p>, <ul>, <li>, <strong>, <a>)
4. ✅ Citations are preserved (all [N] markers present)
5. ✅ Internal links are preserved (all <a href="/magazine/..."> present)

*** OUTPUT ***

Return ONLY the updated content. No explanations, no markdown, no extra text.
Just the fixed HTML content.
"""


def get_refresh_prompt(
    original_content: str,
    instruction: str,
    target_field: str,
    context: Dict[str, Any] = None
) -> str:
    """
    Build prompt for refresh mode (content update).
    
    Goal: Update content with new information while preserving structure.
    """
    
    context = context or {}
    
    return f"""You are performing a CONTENT REFRESH on an existing article section.

Your job is to update the content with new information while keeping the structure and style.

*** ORIGINAL CONTENT ***

{original_content}

*** UPDATE INSTRUCTION ***

{instruction}

*** YOUR TASK ***

Update the content according to the instruction above. You MAY:
- Replace outdated facts, statistics, or examples with new ones
- Add new citations [N] if referencing new sources (increment from existing numbers)
- Update company names or case studies
- Refresh data to reflect current year (2025)

You MUST NOT:
- Change the overall structure (number of paragraphs, HTML tags)
- Remove internal links (<a href="/magazine/...">)
- Change the tone or writing style
- Rewrite from scratch (preserve as much as possible)

*** GUIDELINES ***

- If original has 3 paragraphs, keep 3 paragraphs
- If original has a list, keep the list structure
- If original mentions 2 companies, mention 2 companies (can be different ones)
- Maintain paragraph lengths (~60-100 words per paragraph)
- Keep the same level of detail and depth

*** VALIDATION CHECKLIST ***

Before submitting:
1. ✅ Content is updated according to instruction
2. ✅ Structure matches original (paragraphs, lists, sections)
3. ✅ HTML tags are intact (<p>, <ul>, <li>, <strong>, <a>)
4. ✅ Internal links are preserved
5. ✅ Tone and style are consistent with original
6. ✅ New citations are numbered correctly (increment from last existing number)

*** OUTPUT ***

Return ONLY the updated content. No explanations, no markdown, no extra text.
Just the refreshed HTML content.
"""


def get_keyword_reduction_prompt(
    original_content: str,
    keyword: str,
    current_count: int,
    target_min: int,
    target_max: int,
    variations: list
) -> str:
    """
    Specialized prompt for keyword density fixes.
    
    This is the most common quality fix in Stage 2b.
    """
    
    variations_str = ", ".join([f'"{v}"' for v in variations])
    
    return f"""You are a CONTENT EDITOR fixing keyword over-optimization in an article.

The exact keyword phrase "{keyword}" appears TOO MANY TIMES ({current_count} times).
This looks spammy and unnatural. Your job: reduce it to {target_min}-{target_max} mentions.

*** CURRENT STATE ***

Keyword: "{keyword}"
Current mentions: {current_count} (TOO MANY)
Target: {target_min}-{target_max} mentions

*** ORIGINAL CONTENT ***

{original_content}

*** YOUR TASK ***

Reduce "{keyword}" from {current_count} to {target_min}-{target_max} mentions by replacing excess with semantic variations.

---

🎯 **STEP 1: Find All Occurrences**

Search the content for EVERY instance of "{keyword}" (case-insensitive).

---

🎯 **STEP 2: Choose Which to Keep**

Keep {target_min}-{target_max} strategic mentions:
- ✅ First mention (in opening paragraph)
- ✅ 1-2 mentions in middle sections
- ✅ Final mention (in conclusion if present)
- ❌ Remove all other mentions

---

🎯 **STEP 3: Replace Excess with Variations**

Use these semantic alternatives:
{variations_str}

**Example transformation:**

❌ BEFORE (9 mentions - TOO MANY):
<p>AI code generation tools 2025 are transforming development. When evaluating AI code generation tools 2025, security is paramount. The best AI code generation tools 2025 serve distinct use cases. Organizations adopting AI code generation tools 2025 report gains.</p>
<p>However, AI code generation tools 2025 also introduce vulnerabilities. Teams using AI code generation tools 2025 must implement scanning. The future of AI code generation tools 2025 depends on security. AI code generation tools 2025 will define 2025's software landscape [1].</p>

✅ AFTER (6 mentions - BALANCED):
<p>AI code generation tools 2025 are transforming development. When evaluating these tools, security is paramount. The best AI assistants serve distinct use cases. Organizations adopting these platforms report gains.</p>
<p>However, code generators also introduce vulnerabilities. Teams using AI code generation tools 2025 must implement scanning. The future of these solutions depends on security. These tools will define 2025's software landscape [1].</p>

**What changed:**
- Kept 2 mentions in first paragraph ✅
- Replaced 6 mentions with variations ✅
- Total mentions: 6 (within target range) ✅

---

*** CRITICAL RULES ***

✅ Replace keyword with variations NATURALLY (maintain sentence flow)
✅ Preserve ALL other content (facts, citations, links, structure)
✅ Keep HTML tags intact (<p>, <ul>, <strong>, <a>)
✅ Maintain paragraph lengths
✅ Spread remaining keyword mentions evenly

❌ DO NOT remove or modify citations [N]
❌ DO NOT remove or modify internal links <a href="/magazine/...">
❌ DO NOT change facts or data
❌ DO NOT rewrite from scratch
❌ DO NOT change paragraph structure

---

*** VALIDATION CHECKLIST ***

Before you submit, COUNT the keyword mentions:

1. Search for "{keyword}" in your output
2. Count EVERY occurrence (case-insensitive)
3. Verify count is between {target_min} and {target_max}
4. If not, adjust again until it is

**CRITICAL:** Your output MUST have exactly {target_min}-{target_max} mentions of "{keyword}".

Example validation:
- Search: "{keyword}"
- Count: 6 mentions
- Target: {target_min}-{target_max}
- Status: ✅ PASS (within range)

---

*** OUTPUT ***

Return ONLY the edited content with keyword density fixed.
- No explanations
- No markdown
- No extra text
- Just the HTML with {target_min}-{target_max} mentions of "{keyword}"

START OUTPUT NOW:
"""


def get_paragraph_expansion_prompt(
    original_content: str,
    current_words: int,
    target_min: int,
    target_max: int,
    paragraph_index: int = 1
) -> str:
    """
    Specialized prompt for expanding short paragraphs.
    
    Common issue: First paragraph too short.
    """
    
    words_to_add = target_min - current_words
    
    return f"""You are a CONTENT EDITOR expanding a short paragraph in an article.

Paragraph #{paragraph_index} is TOO SHORT ({current_words} words).
Professional articles need substantial opening paragraphs. Target: {target_min}-{target_max} words.

*** CURRENT STATE ***

Paragraph #{paragraph_index}: {current_words} words (TOO SHORT)
Target: {target_min}-{target_max} words
Words to add: ~{words_to_add}

*** ORIGINAL CONTENT ***

{original_content}

*** YOUR TASK ***

Expand paragraph #{paragraph_index} to {target_min}-{target_max} words by adding:
- Context or background information
- Specific examples or statistics
- Supporting data or facts
- Industry trends or insights

---

🎯 **EXPANSION STRATEGY**

**What to add:**
- ✅ Specific numbers (percentages, dollar amounts, timeframes)
- ✅ Industry data or market stats
- ✅ Company examples or case studies
- ✅ Expert opinions or research findings
- ✅ Relevant trends or challenges

**What NOT to add:**
- ❌ Fluff or filler words
- ❌ Repetitive statements
- ❌ Vague generalizations
- ❌ Off-topic tangents

---

**EXAMPLE TRANSFORMATION:**

❌ BEFORE (24 words - TOO SHORT):
<p>AI tools are changing software development. Many teams now use them daily. But security concerns remain.</p>

✅ AFTER (78 words - GOOD):
<p>AI tools are fundamentally changing how software development teams operate in 2025, with 84% of developers now integrating these assistants into their daily workflows [1]. Many teams report 30% faster development cycles and significant reductions in boilerplate code generation [2]. However, security concerns remain a critical barrier to adoption, as 45% of AI-generated code contains vulnerabilities that require manual review [3]. This productivity paradox forces engineering leaders to balance speed with safety.</p>

**What was added:**
- Specific stat: "84% of developers" ✅
- Data point: "30% faster cycles" ✅
- Security stat: "45% vulnerabilities" ✅
- Context: "productivity paradox" ✅
- Citations: [1], [2], [3] ✅
- Total: 78 words (within target) ✅

---

*** CRITICAL RULES ***

✅ Expand with RELEVANT, SUBSTANTIVE content (not filler)
✅ Add specific numbers, percentages, or data points
✅ Maintain the same core message and tone
✅ Keep HTML structure (<p> tags, <strong>, citations)
✅ Add citations [N] for new facts (increment from existing numbers)

❌ DO NOT change other paragraphs
❌ DO NOT remove existing content
❌ DO NOT change the overall meaning
❌ DO NOT add fluff or obvious statements

---

*** VALIDATION CHECKLIST ***

Before you submit:
1. Count words in paragraph #{paragraph_index}
2. Verify: {target_min} ≤ word_count ≤ {target_max}
3. Check: Expansion is substantive (not just adjectives)
4. Check: Added facts have citations [N]
5. Check: Tone matches original

**CRITICAL:** Paragraph #{paragraph_index} MUST be {target_min}-{target_max} words.

---

*** OUTPUT ***

Return ONLY the expanded content.
- No explanations
- No markdown
- No extra text
- Just the HTML with expanded paragraph #{paragraph_index}

START OUTPUT NOW:
"""


def get_ai_marker_removal_prompt(
    original_content: str,
    markers_found: list
) -> str:
    """
    Specialized prompt for removing AI language markers.
    
    Targets: em dashes, robotic phrases, formulaic transitions.
    """
    
    markers_list = "\n".join([f"- {marker}" for marker in markers_found])
    
    # Count em dashes for validation
    em_dash_count = original_content.count("—")
    
    return f"""You are a CONTENT EDITOR removing AI language markers from an article.

AI-generated content contains telltale markers that make it sound robotic and unnatural.
Your job: Remove ONLY these markers while keeping everything else identical.

*** AI MARKERS TO REMOVE ***

{markers_list}

*** ORIGINAL CONTENT ***

{original_content}

*** TRANSFORMATION RULES ***

🎯 **RULE 1: Remove ALL Em Dashes (—)**

{em_dash_count} em dashes detected. You MUST remove all of them.

❌ BEFORE (with em dashes):
<p>AI tools—like GitHub Copilot and Amazon Q—are transforming development workflows. Organizations—especially Fortune 500 companies—report 55% faster development cycles [1].</p>

✅ AFTER (humanized):
<p>AI tools, like GitHub Copilot and Amazon Q, are transforming development workflows. Organizations, especially Fortune 500 companies, report 55% faster development cycles [1].</p>

**How to fix:**
- Mid-sentence em dash → comma
- Parenthetical em dash → parentheses or commas
- Long em dash clause → split into 2 sentences

---

🎯 **RULE 2: Remove Robotic Introductions**

❌ BEFORE (robotic):
<p>Here's how enterprises are mitigating risks:</p>
<ul>
  <li>Automated scanning</li>
  <li>Code review</li>
</ul>

✅ AFTER (natural):
<p>Enterprises are mitigating risks through several approaches:</p>
<ul>
  <li>Automated scanning</li>
  <li>Code review</li>
</ul>

**Phrases to remove:**
- "Here's how" → just state the action
- "Here's what" → just state the content
- "Key points:" → integrate naturally
- "Important considerations:" → rephrase naturally

---

🎯 **RULE 3: Fix Formulaic Transitions**

❌ BEFORE:
<p>That's why similarly, organizations must balance speed with security.</p>

✅ AFTER:
<p>Similarly, organizations must balance speed with security.</p>

---

*** CRITICAL: PRESERVE EVERYTHING ELSE ***

✅ Keep ALL citations: [1], [2], [3] → unchanged
✅ Keep ALL internal links: <a href="/magazine/..."> → unchanged
✅ Keep ALL HTML tags: <p>, <ul>, <strong> → unchanged
✅ Keep ALL facts and data → unchanged
✅ Keep paragraph structure → unchanged

❌ DO NOT rewrite from scratch
❌ DO NOT change the meaning
❌ DO NOT add new content
❌ DO NOT remove existing facts

---

*** VALIDATION CHECKLIST ***

Before you submit, verify:
1. ✅ ZERO em dashes (—) present (count them!)
2. ✅ No "Here's how/what" phrases
3. ✅ No "Key points:" labels
4. ✅ All citations [N] still present
5. ✅ All <a href> links still present
6. ✅ Same number of paragraphs
7. ✅ Content flows naturally

**CRITICAL:** If the original had {em_dash_count} em dashes, your output MUST have 0.

---

*** OUTPUT ***

Return ONLY the cleaned HTML content.
- No explanations
- No markdown code blocks
- No extra text
- Just the HTML with AI markers removed

START OUTPUT NOW:
"""


def get_comprehensive_content_transformation_prompt(
    original_content: str,
    citations: list,
    primary_keyword: str = "",
    company_name: str = ""
) -> str:
    """
    Build prompt for comprehensive content transformation (Stage 2b).
    
    Single-pass Gemini transformation that fixes ALL content quality issues at once:
    - Academic citations [N] → inline natural language (using citation metadata)
    - Standalone labels → natural list integration
    - Em dashes → contextual commas/removal
    - Robotic transitions → natural flow
    - Malformed headings → clean headings
    - Weird word passages → natural sentences
    - Incomplete sentences → complete thoughts
    - Double punctuation → single
    
    This is the MOST IMPORTANT prompt in the entire pipeline - it transforms
    Gemini's raw output into production-ready, human-quality content.
    
    Args:
        original_content: The article content (all sections concatenated)
        citations: List of citation dicts with {number, url, title}
        primary_keyword: Primary keyword for natural distribution
        company_name: Company name for context
    
    Returns:
        Comprehensive transformation prompt for Gemini 3.0 Pro Preview
    """
    
    # Build citation reference section
    citation_reference = ""
    if citations:
        citation_reference = "**Available Citations for Inline Transformation:**\n\n"
        for cit in citations[:10]:  # Limit to first 10 to avoid token bloat
            num = cit.get('number', '?')
            title = cit.get('title', 'Source')[:100]
            url = cit.get('url', '')
            citation_reference += f"[{num}]: {title}\n    URL: {url}\n\n"
    else:
        citation_reference = "**Note:** No citation metadata available. Remove [N] markers if found.\n\n"
    
    return f"""You are an expert content editor transforming AI-generated content into professional, human-quality MARKDOWN text.

Your task is to perform a COMPREHENSIVE CONTENT TRANSFORMATION on this article.
This is a SINGLE-PASS transformation that fixes ALL quality issues at once.

⚠️ CRITICAL: Input is MARKDOWN format. Output must also be PURE MARKDOWN (NO HTML tags).

*** ORIGINAL CONTENT (MARKDOWN) ***

{original_content}

*** YOUR MISSION ***

Transform this MARKDOWN content to be production-ready by fixing ALL of the following issues:

═══════════════════════════════════════════════════════════════════
🎯 TRANSFORMATION #1: Academic Citations [N] → Inline Natural Language
═══════════════════════════════════════════════════════════════════

{citation_reference}

**Your Task:**
Convert ALL academic citation markers [N] to natural inline attribution using the citation metadata above.

❌ BEFORE (academic style):
GitHub Copilot increases developer productivity by 55% [1]. Amazon Q Developer reduced migration time by 60% [2].

✅ AFTER (natural inline):
GitHub Copilot's 2024 enterprise report shows a **55% increase** in developer productivity. AWS documented a **60% reduction** in migration time with their Q Developer tool.

**Guidelines:**
- Use natural language: "according to", "as noted in", "research from", "[Company]'s [Year] report"
- Vary your phrasing - don't repeat the same attribution style
- Integrate attribution smoothly into the sentence flow
- Keep the factual accuracy - preserve the statistics and claims
- Remove ALL bracket markers [1] [2] [3] completely
- If citation metadata unavailable, keep the claim but remove the [N]
- Use **bold** to emphasize key numbers and stats

═══════════════════════════════════════════════════════════════════
🎯 TRANSFORMATION #2: Standalone Labels → Natural List Integration
═══════════════════════════════════════════════════════════════════

❌ BEFORE (broken standalone labels):
**GitHub Copilot:**

**Amazon Q Developer:**

- Feature 1

✅ AFTER (natural integration):
Leading AI code generation tools include:

- **GitHub Copilot:** Context-aware code suggestions with 55% faster completions
- **Amazon Q Developer:** AWS-integrated development assistant for cloud migrations

This approach allows teams to select tools based on their specific needs.

**Your Task:**
- Find ALL standalone `**Label:**` patterns on their own lines
- Convert to proper list items with descriptions or integrate into narrative
- Ensure labels have accompanying content (15-30 words each)
- Add a follow-up sentence after lists to maintain flow

═══════════════════════════════════════════════════════════════════
🎯 TRANSFORMATION #3: Em Dashes (—) → Contextual Commas/Removal
═══════════════════════════════════════════════════════════════════

❌ BEFORE (AI marker - em dashes):
AI tools—like GitHub Copilot—are transforming development. Organizations—especially enterprises—report significant gains.

✅ AFTER (natural punctuation):
AI tools, like GitHub Copilot, are transforming development. Organizations, especially enterprises, report significant gains.

**Your Task:**
- Replace ALL em dashes (—, &mdash;, &#8212;) with commas or split into sentences
- Choose based on context: mid-sentence → comma, long clause → new sentence
- Count: Your output MUST have ZERO em dashes

═══════════════════════════════════════════════════════════════════
🎯 TRANSFORMATION #4: Robotic Transitions → Natural Flow
═══════════════════════════════════════════════════════════════════

❌ BEFORE (robotic AI phrases):
Here's how enterprises adopt AI tools:

Here's what you need to know:

Key points include:

Important considerations:

That's why similarly, organizations...

When you similarly, the tools...

✅ AFTER (natural transitions):
Enterprises adopt AI tools through several approaches:

Understanding these factors is essential:

Organizations should consider:

Similarly, organizations...

Similarly, the tools...

**Phrases to Fix:**
- "Here's how/what" → just state the action
- "Key points:" → remove or rephrase naturally
- "That's why similarly," → "Similarly,"
- "When you similarly," → "Similarly,"
- "so you can with" → "with"
- "What is as we" → "As we"

═══════════════════════════════════════════════════════════════════
🎯 TRANSFORMATION #5: Malformed Headings → Clean Headings
═══════════════════════════════════════════════════════════════════

❌ BEFORE (duplicate question prefixes):
What is How AI Tools Work?

What is Why Security Matters??

✅ AFTER (clean headings):
How AI Tools Work

Why Security Matters

**Your Task:**
- Remove duplicate "What is" prefixes
- Remove double punctuation in headings (??, !!)
- Ensure headings are grammatically correct
- Note: Headings should NOT have Markdown ## syntax in content (section titles are already H2)

═══════════════════════════════════════════════════════════════════
🎯 TRANSFORMATION #6: Weird Word Passages → Natural Sentences
═══════════════════════════════════════════════════════════════════

❌ BEFORE (context loss/hallucination patterns):
What is as we look at the market...

so you can of the implementation...

When you aI code generation...

Here's however, the challenge...

✅ AFTER (natural sentences):
As we look at the market...

for the implementation...

AI code generation...

However, the challenge...

**Your Task:**
- Fix broken grammar from AI context loss
- Remove nonsensical word combinations
- Ensure every sentence is grammatically correct
- Fix lowercase "aI" → "AI" (proper capitalization)

═══════════════════════════════════════════════════════════════════
🎯 TRANSFORMATION #7: Incomplete Sentences → Complete Thoughts
═══════════════════════════════════════════════════════════════════

❌ BEFORE (trailing fragments):
The market is changing rapidly. Ultimately,

Organizations must adapt. However,

✅ AFTER (complete sentences):
The market is changing rapidly.

Organizations must adapt to these changes.

**Your Task:**
- Complete any sentences ending with conjunctions (Ultimately, However, Similarly, Therefore)
- Ensure every paragraph ends with a complete thought
- Remove orphaned fragments

═══════════════════════════════════════════════════════════════════
🎯 TRANSFORMATION #8: Double Punctuation → Single
═══════════════════════════════════════════════════════════════════

❌ BEFORE:
The tools are evolving.. Also,, organizations must adapt.

What are the benefits??

✅ AFTER:
The tools are evolving. Also, organizations must adapt.

What are the benefits?

**Your Task:**
- Fix all double commas (,,) → single comma
- Fix all double periods (..) → single period
- Fix double question marks (??) → single
- Fix double exclamations (!!) → single

═══════════════════════════════════════════════════════════════════
🎯 CRITICAL: PRESERVE STRUCTURE & FACTS (MARKDOWN FORMAT)
═══════════════════════════════════════════════════════════════════

✅ **KEEP UNCHANGED:**
- ALL Markdown formatting (**bold**, - lists, [links](url))
- ALL facts, statistics, and data points
- ALL internal links ([text](/magazine/slug))
- Overall paragraph structure and flow (blank line separators)
- Technical accuracy of all claims

❌ **DO NOT:**
- Rewrite content from scratch
- Change the meaning or intent
- Add new information not in the original
- Remove facts or data points
- Add HTML tags (<p>, <ul>, <li>, <strong>, <em>)
- Remove internal links
- Change Markdown to HTML

═══════════════════════════════════════════════════════════════════
🎯 VALIDATION CHECKLIST (VERIFY BEFORE SUBMITTING)
═══════════════════════════════════════════════════════════════════

Before you return the transformed content, verify:

1. ✅ ZERO academic citations [N] remain (all converted to inline)
2. ✅ ZERO em dashes (—) remain (all converted to commas/sentences)
3. ✅ ZERO standalone labels remain (all integrated into lists/narrative)
4. ✅ ZERO "Here's how/what" phrases remain
5. ✅ ZERO malformed headings (no "What is How")
6. ✅ ZERO weird passages (no "What is as we", "so you can with")
7. ✅ ZERO incomplete sentences (no trailing "Ultimately,")
8. ✅ ZERO double punctuation (,, .. ?? !!)
9. ✅ ZERO HTML tags (should be pure Markdown: **bold**, - lists, [links](url))
10. ✅ ALL internal links preserved ([text](/magazine/slug))
11. ✅ ALL facts and data preserved
12. ✅ Content flows naturally and reads like human-written text
13. ✅ Paragraphs separated by blank lines

═══════════════════════════════════════════════════════════════════
🎯 OUTPUT INSTRUCTIONS
═══════════════════════════════════════════════════════════════════

Return ONLY the transformed MARKDOWN content.
- No explanations or comments
- No markdown code blocks (no ```)
- No "Here's the transformed content" preface
- Just the clean, transformed MARKDOWN
- Start with plain text immediately (NOT with HTML tags)
- Use **bold** for emphasis, - for lists, blank lines for paragraphs

**Quality Standard:** The output should be indistinguishable from professionally written content.
No reader should be able to tell it was AI-generated.

START TRANSFORMED MARKDOWN CONTENT NOW:
"""


# Map modes to prompt functions
PROMPT_BUILDERS = {
    "quality_fix": get_quality_fix_prompt,
    "refresh": get_refresh_prompt,
}

# Specialized builders for common fixes
SPECIALIZED_BUILDERS = {
    "keyword_reduction": get_keyword_reduction_prompt,
    "paragraph_expansion": get_paragraph_expansion_prompt,
    "ai_marker_removal": get_ai_marker_removal_prompt,
    "comprehensive_transform": get_comprehensive_content_transformation_prompt,
}

