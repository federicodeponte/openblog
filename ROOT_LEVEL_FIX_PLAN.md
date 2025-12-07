# Root-Level Fix Plan: Content Quality Issues

## 🚨 CRITICAL FINDINGS FROM SHOWCASE AUDIT

**Source**: Audit of `showcase-20251207-173434-0/index.html` (generated 2025-12-07)

### **P0 - BLOCKING ISSUES** (Must Fix Before Next Generation)

| # | Issue | Example | Impact | Priority |
|---|-------|---------|--------|----------|
| **A** | **Malformed Headings** | "What is How Do X??" | CRITICAL UX | 🔴 P0 |
| **B** | **Sentence Fragments** | "text\n\n. next sentence" | CRITICAL Readability | 🔴 P0 |
| **C** | **Broken Citation Links** | `href="#source-3"` (404) | CRITICAL Functionality | 🔴 P0 |
| **D** | **Keyword Line Breaks** | "AI\n\ncode review\n\ntools" | HIGH Readability | 🟠 P0 |
| **E** | **Cutoff Sentences** | "Ultimately," (ends) | HIGH Quality | 🟠 P0 |

### **P1 - HIGH PRIORITY** (Next Sprint)

| # | Issue | Example | Impact | Priority |
|---|-------|---------|--------|----------|
| **F** | **Missing Internal Links** | No related articles | MEDIUM SEO | 🟡 P1 |
| **G** | **Citation Numbering** | Starts at [2] not [1] | MEDIUM Cosmetic | 🟡 P1 |
| **H** | **Inconsistent Lists** | Sometimes bullets, sometimes paragraphs | MEDIUM Readability | 🟡 P1 |
| **1** | **Academic Citations** | `[1], [2]` still appear | MEDIUM Cosmetic | 🟡 P1 |
| **2** | **Em Dashes** | `—` occasional | LOW Cosmetic | 🟢 P1 |

### Visual Examples

**Issue A: Malformed Heading**
```html
❌ <h2>What is How Do Leading AI Review Tools Compare??</h2>
✅ <h2>How Do Leading AI Review Tools Compare?</h2>
```

**Issue B: Sentence Fragment**
```
❌ "This project highlighted... with minimal human intervention

. Similarly, Duolingo applyd GitHub Copilot..."

✅ "This project highlighted... with minimal human intervention. Similarly, Duolingo applied GitHub Copilot..."
```

**Issue C: Broken Citation Link**
```html
❌ <a href="#source-3">according to Stack Overflow data</a>
   (Link goes nowhere - anchor doesn't exist)

✅ <a href="https://stackoverflow.co/labs/developer-survey-2024/" target="_blank">according to Stack Overflow data</a>
```

**Issue D: Keyword Line Break**
```html
❌ "adoption of

AI code review tools 2025

has outpaced security"

✅ "adoption of <strong>AI code review tools 2025</strong> has outpaced security"
```

---

## Problem Statement (Updated)

Despite v4.0 structured JSON eliminating hallucinations, **8 new critical formatting/quality issues** were discovered during showcase audit, plus the original 2 minor issues. These break basic readability and professionalism.

**Current approach**: Limited regex cleanup (reactive, incomplete)  
**Target approach**: Multi-layered prevention + validation + cleanup (proactive, comprehensive)

---

## Root Cause Analysis (Updated from Showcase Audit)

### NEW CRITICAL ISSUES FROM SHOWCASE-20251207-173434-0

Based on audit of `showcase-20251207-173434-0/index.html`, the following **critical** issues were identified:

#### Issue A: Malformed Section Headings (CRITICAL)
**Example**: `<h2>What is How Do Leading AI Review Tools Compare??</h2>`

**Problem**: Question prefix "What is" incorrectly prepended to another question, creating nonsensical heading.

**Root Cause**: 
- Gemini's structured JSON output is including "What is" prefix in section titles
- Likely caused by prompt asking for "questions" but schema allowing double-question format
- HTML renderer not stripping these prefixes

**Impact**: HIGH - Destroys user experience, looks completely unprofessional

#### Issue B: Sentence Fragments with Orphaned Punctuation (CRITICAL)
**Example**: 
```
"This project highlighted the tool's ability... with minimal human intervention

. Similarly, Duolingo applyd GitHub Copilot..."
```

**Problem**: Period orphaned on new line after sentence, followed by broken continuation.

**Root Cause**:
- Regex cleanup for academic citations removing `[N]` mid-sentence
- Leaves behind punctuation + line break + lowercase continuation
- Pattern: `sentence [N]. Next sentence` → `sentence \n. next sentence`

**Impact**: HIGH - Broken readability, looks like corrupted data

#### Issue C: Broken Citation Links (CRITICAL)
**Example**: `<a href="#source-3">according to Stack Overflow data</a>`

**Problem**: Link points to `#source-3` anchor (doesn't exist), not actual source URL.

**Root Cause**:
- Citations stage (Stage 4) generates placeholder anchors `#source-N`
- But HTML renderer isn't replacing with actual URLs from sources list
- Sources appear at bottom but aren't linked to inline citations

**Impact**: HIGH - Broken links, no actual citation verification possible

#### Issue D: Missing Internal Links (CRITICAL)
**Observation**: No internal links visible in HTML despite Stage 5 running.

**Root Cause**:
- Internal links stage may be generating suggestions but not inserting them
- Or links being stripped by cleanup regex
- Need to verify Stage 5 output in article.json

**Impact**: MEDIUM - Missed SEO opportunity, poor user engagement

#### Issue E: Incomplete Sentences / Cutoffs (HIGH)
**Example**: `"Ultimately,\n\n" -> cutoff here`

**Problem**: Sentence starts but never completes, followed by blank space.

**Root Cause**:
- Gemini truncating content mid-sentence
- Quality checker not detecting incomplete sentences
- Could be token limit issue or bad regex cleanup

**Impact**: HIGH - Looks unfinished, unprofessional

#### Issue F: Inconsistent List Formatting (MEDIUM)
**Example**: Some sections use `<ul><li>` (bullets), others use paragraph text with "Key benefits include:" prefix but no actual list.

**Problem**: Schema allows freeform content, Gemini inconsistently formats lists.

**Root Cause**:
- Prompt doesn't enforce consistent list HTML
- Gemini sometimes uses paragraphs instead of `<ul>`
- Quality checker doesn't validate list formatting

**Impact**: MEDIUM - Inconsistent reading experience

#### Issue G: Keyword Line Breaks (HIGH)
**Example**: 
```
"adoption of

AI code review tools 2025

has outpaced secur"
```

**Problem**: Target keyword split across 3 lines with blank lines between.

**Root Cause**:
- Keyword emphasis logic inserting `<strong>` tags incorrectly
- Or paragraph cleanup regex breaking keyword phrases
- Creates unreadable fragmentation

**Impact**: HIGH - Kills readability, breaks SEO keyword targeting

#### Issue H: Citation Number Mismatch (MEDIUM)
**Example**: Sources list shows `[2], [3], [4]` but should start at `[1]`.

**Problem**: Citation numbering is off-by-one or skipping numbers.

**Root Cause**:
- Citation extraction not sorting properly
- Or regex cleanup removing first citation
- Index mismatch between inline refs and sources list

**Impact**: MEDIUM - Confusing for readers, looks sloppy

---

### Issue 1: Academic Citations `[1], [2]` (EXISTING)

**Current State:**
- Gemini generates numbered citations despite instructions
- Regex in `html_renderer.py` attempts cleanup but misses edge cases
- Pattern: `[1], [2]` or `[2][3]` or mid-sentence `text [1] more text`

**Root Causes:**
1. **Prompt ambiguity** (Stage 1): Instructions say "inline contextual" but don't explicitly forbid `[N]`
2. **Schema permissiveness** (Stage 2): Pydantic `ArticleOutput` doesn't validate citation format
3. **Quality gate gap** (Stage 2b): Doesn't check for citation style violations
4. **Regex limitations** (Cleanup): Only catches common patterns, misses edge cases

### Issue 2: Em Dashes `—`, `&mdash;`, `&#8212;`

**Current State:**
- Gemini occasionally uses em dashes for emphasis or parenthetical clauses
- Regex replacement exists but may miss HTML entity variants

**Root Causes:**
1. **Prompt silence**: No explicit instruction against em dashes
2. **Quality gate gap**: Stage 2b doesn't check for em dashes
3. **Regex incompleteness**: May not catch all 3 variants (Unicode, HTML entity, numeric entity)

---

## Multi-Layered Defense Strategy

### Layer 1: Prevention at Source (Prompt Engineering) - **P0**
**Goal**: Gemini never generates these patterns  
**Effectiveness**: 90%+ reduction  
**Maintenance**: Low (one-time prompt update)

### Layer 2: Validation (Schema + Quality Gate) - **P0**
**Goal**: Detect violations before HTML rendering  
**Effectiveness**: 8-9% additional coverage  
**Maintenance**: Medium (schema + quality checker updates)

### Layer 3: Cleanup (Regex Hardening) - **P1**
**Goal**: Catch the remaining 1-2% edge cases  
**Effectiveness**: Final safety net  
**Maintenance**: Low (comprehensive regex patterns)

---

## UPDATED Implementation Plan (Including New Critical Issues)

## Phase 0: HOTFIX Critical Issues (P0 - URGENT) 🚨

Must fix before any new blog generation. These break basic readability.

### 0.1 Fix Malformed Section Headings

**File**: `services/blog-writer/pipeline/blog_generation/stage_03_extraction.py`

**Problem**: Headings like "What is How Do X?"

**Root Cause**: Schema field names include "What is" prefix, Gemini adds another question.

**Fix**:
```python
# In Stage 3: After extracting section titles
def _clean_section_heading(heading: str) -> str:
    """Remove duplicate question prefixes."""
    # Remove "What is" prefix if heading already starts with question word
    heading = heading.strip()
    if heading.startswith("What is "):
        rest = heading[8:]  # Remove "What is "
        if rest.lower().startswith(("how ", "why ", "what ", "when ", "where ", "who ")):
            heading = rest
    
    # Remove double question marks
    heading = re.sub(r'\?{2,}', '?', heading)
    
    return heading

# Apply to all section_XX_title fields during extraction
```

**Better Fix** (Schema level):
```python
# In article_schema.py
class ArticleOutput(BaseModel):
    section_01_title: str = Field(..., description="Section 1 H2 heading (no 'What is' prefix)")
    
    @field_validator('section_01_title', 'section_02_title', ...)
    @classmethod
    def clean_heading(cls, v: str) -> str:
        """Clean malformed headings."""
        v = v.strip()
        # Remove "What is" if followed by another question word
        if v.startswith("What is "):
            rest = v[8:]
            if rest.lower().startswith(("how ", "why ", "what ")):
                v = rest
        # Remove double punctuation
        v = re.sub(r'\?{2,}', '?', v)
        v = re.sub(r'\.{2,}', '.', v)
        return v
```

**Prompt Fix**:
```python
# In main_prompt.py - Section heading instructions
SECTION_HEADING_RULES = """
H2 HEADING RULES:
- Write clean, direct headings: "How AI Tools Compare" or "Why Security Matters"
- NEVER prefix with "What is": ❌ "What is How to Choose Tools?"
- NEVER use double punctuation: ❌ "Best Tools??"
- Use question format OR statement format, not both mixed
- Keep headings concise (max 80 characters)

Good examples:
✅ "How Do Leading AI Review Tools Compare?"
✅ "Why Security Remains the Critical Bottleneck"
✅ "5 Steps to Implement Safe AI Code Reviews"

Bad examples:
❌ "What is How Do Leading AI Review Tools Compare??"
❌ "What is Why Security Matters"
❌ "How to Choose Tools??????"
"""
```

### 0.2 Fix Sentence Fragments (Period + Line Break Issues)

**File**: `services/blog-writer/pipeline/processors/html_renderer.py`

**Problem**: `"text\n\n. Next sentence"` pattern from broken citation removal.

**Current State**: Academic citation regex removes `[N]` but leaves orphaned punctuation.

**Fix** (Enhanced regex):
```python
def fix_sentence_fragments(html: str) -> str:
    """Fix broken sentences from citation removal."""
    
    # Pattern 1: Orphaned period after line break
    # "text\n\n. Next" → "text. Next"
    html = re.sub(r'(\w)\s*\n+\s*\.\s+([a-z])', r'\1. \2', html)
    
    # Pattern 2: Missing space after period
    # "text.Next" → "text. Next"
    html = re.sub(r'\.([A-Z])', r'. \1', html)
    
    # Pattern 3: Multiple line breaks before punctuation
    # "text\n\n," → "text,"
    html = re.sub(r'\s*\n+\s*([.,;:!?])\s+', r'\1 ', html)
    
    # Pattern 4: Lowercase after period (broken sentence continuation)
    # ". similarly" → ". Similarly"
    html = re.sub(r'\.\s+([a-z])', lambda m: '. ' + m.group(1).upper(), html)
    
    return html

# Add to cleanup pipeline in html_renderer.py
```

### 0.3 Fix Citation Link Anchors

**File**: `services/blog-writer/pipeline/blog_generation/stage_04_citations.py`

**Problem**: Links point to `#source-3` (broken) instead of actual URLs.

**Current State**: Citation stage generates placeholder anchors but doesn't replace them.

**Fix**:
```python
# In Stage 4: After validating citations
def replace_citation_anchors(html: str, citations: List[Dict]) -> str:
    """Replace #source-N anchors with actual citation URLs."""
    
    for i, citation in enumerate(citations, start=1):
        # Find inline references to #source-N
        anchor_pattern = f'#source-{i}'
        
        # Replace with actual URL
        if citation.get('url'):
            html = html.replace(
                f'href="{anchor_pattern}"',
                f'href="{citation["url"]}" target="_blank" rel="noopener noreferrer"'
            )
    
    return html

# Add to Stage 4 output
context.parallel_results['citations'] = {
    'citations_html': citations_html,
    'citation_replacements': citation_map,  # NEW: map of anchors to URLs
}

# Then in html_renderer.py, apply replacements
html = replace_citation_anchors(html, citation_map)
```

**Better Approach** (Don't use anchors):
```python
# In Stage 4: Generate inline citations with actual URLs immediately
def format_inline_citation(text: str, source_url: str, source_name: str) -> str:
    """Format inline citation with real URL."""
    return f'<a href="{source_url}" target="_blank" rel="noopener noreferrer">{text}</a>'

# Don't use placeholders at all
```

### 0.4 Fix Keyword Line Breaks

**File**: `services/blog-writer/pipeline/processors/html_renderer.py`

**Problem**: Keywords split across multiple lines with blank lines.

**Root Cause**: Keyword emphasis inserting `<p><strong>keyword</strong></p>` instead of inline `<strong>`.

**Fix**:
```python
def fix_keyword_formatting(html: str, keyword: str) -> str:
    """Fix keyword line breaks and formatting."""
    
    # Pattern 1: Keyword wrapped in standalone paragraph
    # "<p>AI code review tools 2025</p>" mid-sentence → "<strong>AI code review tools 2025</strong>"
    keyword_escaped = re.escape(keyword)
    html = re.sub(
        rf'<p>\s*({keyword_escaped})\s*</p>',
        r'<strong>\1</strong>',
        html,
        flags=re.IGNORECASE
    )
    
    # Pattern 2: Multiple paragraphs with keyword fragments
    # Remove excessive paragraph breaks around keywords
    html = re.sub(r'</p>\s*<p>\s*<strong>', ' <strong>', html)
    html = re.sub(r'</strong>\s*</p>\s*<p>', '</strong> ', html)
    
    # Pattern 3: Blank lines before/after keyword
    html = re.sub(r'\n{3,}', '\n\n', html)
    
    return html
```

### 0.5 Fix Cutoff Sentences

**File**: `services/blog-writer/pipeline/blog_generation/stage_02b_quality_refinement.py`

**Problem**: Sentences like "Ultimately," followed by nothing.

**Root Cause**: Content truncation or bad extraction.

**Detection**:
```python
def _check_incomplete_sentences(self, article_data: Dict[str, Any]) -> List[QualityIssue]:
    """Detect sentence fragments and cutoffs."""
    issues = []
    
    # Patterns indicating incomplete sentences
    incomplete_patterns = [
        r'\w+,\s*$',  # Ends with comma: "Ultimately,"
        r'\b(and|or|but|however|moreover|furthermore|therefore)\s*$',  # Ends with conjunction
        r':\s*$',      # Ends with colon (no list follows)
    ]
    
    for key, value in article_data.items():
        if isinstance(value, str):
            for pattern in incomplete_patterns:
                if re.search(pattern, value.strip()):
                    issues.append(QualityIssue(
                        type="incomplete_sentence",
                        severity="high",
                        field=key,
                        issue=f"Content ends with incomplete sentence: '{value[-50:]}'",
                        fix_instruction="Complete the sentence or remove the fragment"
                    ))
    
    return issues
```

### 0.6 Fix Citation Numbering

**File**: `services/blog-writer/pipeline/blog_generation/stage_04_citations.py`

**Problem**: Citations start at [2] instead of [1], or skip numbers.

**Fix**:
```python
def renumber_citations(citations: List[Dict]) -> List[Dict]:
    """Ensure citations are numbered sequentially from 1."""
    for i, citation in enumerate(citations, start=1):
        citation['number'] = i
    return citations

# Before rendering sources list
citations = renumber_citations(validated_citations)
```

### 0.7 Fix Missing Internal Links

**File**: `services/blog-writer/pipeline/blog_generation/stage_05_internal_links.py`

**Problem**: Internal links generated but not inserted into HTML.

**Investigation Needed**:
1. Check if Stage 5 is producing link suggestions in `article.json`
2. Verify if HTML renderer is consuming internal_links data
3. Check if links are being stripped by cleanup regex

**Fix** (if links not being inserted):
```python
# In html_renderer.py
def insert_internal_links(html: str, internal_links: List[Dict]) -> str:
    """Insert internal links into content."""
    
    if not internal_links:
        return html
    
    # Create "More Reading" section
    links_html = '<div class="internal-links"><h3>Related Articles</h3><ul>'
    for link in internal_links[:5]:  # Max 5 links
        links_html += f'<li><a href="{link["url"]}">{link["title"]}</a></li>'
    links_html += '</ul></div>'
    
    # Insert before FAQ section or at end of main content
    if '<h2>People Also Ask</h2>' in html:
        html = html.replace('<h2>People Also Ask</h2>', f'{links_html}<h2>People Also Ask</h2>')
    else:
        # Insert before footer
        html = html.replace('</article>', f'{links_html}</article>')
    
    return html
```

**Better Fix** (inline contextual links):
```python
# In Stage 5: Find relevant keywords in content and link them
def insert_contextual_internal_links(html: str, link_suggestions: List[Dict]) -> str:
    """Insert internal links inline where contextually relevant."""
    
    for suggestion in link_suggestions:
        anchor_text = suggestion['anchor_text']  # e.g., "microservices architecture"
        target_url = suggestion['url']
        
        # Find first occurrence of anchor text (case-insensitive)
        pattern = re.compile(re.escape(anchor_text), re.IGNORECASE)
        
        # Replace only first occurrence to avoid over-linking
        html = pattern.sub(
            f'<a href="{target_url}" class="internal-link">{anchor_text}</a>',
            html,
            count=1
        )
    
    return html
```

### 0.8 Fix Inconsistent List Formatting

**File**: `services/blog-writer/pipeline/prompts/main_prompt.py`

**Problem**: Sometimes bullets (`<ul>`), sometimes paragraphs with "Key points:" label.

**Prompt Fix**:
```python
LIST_FORMATTING_RULES = """
LIST FORMATTING RULES:
- ALWAYS use proper HTML lists for multiple related points
- Use <ul><li> for unordered lists (most common)
- Use <ol><li> for numbered steps or sequences
- NEVER write "Key points:" followed by plain paragraphs
- NEVER write "Here are X:" without actual list markup

Good examples:
✅ <ul><li>Point one about AI tools</li><li>Point two about security</li></ul>
✅ <ol><li>First step: Define scope</li><li>Second step: Train team</li></ol>

Bad examples:
❌ Key points: The first point is... The second point is...
❌ Here are the benefits: Benefit one. Benefit two.
❌ Important considerations: (followed by paragraphs)
"""
```

**Quality Check** (Stage 2b or Stage 10):
```python
def _check_list_formatting(self, article_data: Dict[str, Any]) -> List[QualityIssue]:
    """Detect improper list formatting."""
    issues = []
    
    # Patterns indicating lists that should use <ul>/<ol>
    list_indicators = [
        r'(?:Key points|Here are|Benefits include|Important considerations|Main features):',
        r'(?:First|Second|Third|1\.|2\.|3\.)',
        r'- \w+',  # Markdown-style list
    ]
    
    for key, value in article_data.items():
        if isinstance(value, str):
            # Check if content has list indicators but no <ul> or <ol>
            has_indicator = any(re.search(pattern, value) for pattern in list_indicators)
            has_list_markup = '<ul>' in value or '<ol>' in value
            
            if has_indicator and not has_list_markup:
                issues.append(QualityIssue(
                    type="list_formatting",
                    severity="medium",
                    field=key,
                    issue="Content has list indicators but no proper <ul>/<ol> markup",
                    fix_instruction="Convert paragraph list to proper HTML list with <ul><li> tags"
                ))
    
    return issues
```

---

## PRIORITY SUMMARY

### Must Fix Immediately (P0 - Blocking)
1. **Malformed headings** ("What is How Do X??") - CRITICAL UX break
2. **Sentence fragments** (orphaned periods, broken continuations) - CRITICAL readability
3. **Broken citation links** (`#source-3` doesn't work) - CRITICAL functionality
4. **Keyword line breaks** (split across 3 lines) - HIGH readability issue
5. **Cutoff sentences** ("Ultimately,") - HIGH quality issue

### Fix in Next Sprint (P1 - High Priority)
6. **Missing internal links** - MEDIUM SEO/UX issue
7. **Citation numbering** (starts at [2]) - MEDIUM cosmetic issue  
8. **Inconsistent list formatting** - MEDIUM readability issue

### Already Planned (P1 - Existing Issues)
9. **Academic citations `[N]`** - MEDIUM (non-blocking cosmetic)
10. **Em dashes** - LOW (rare occurrence)

---

## Phase 1: Prompt Engineering (P0) 🎯

### 1.1 Update Main Content Prompt

**File**: `services/blog-writer/pipeline/prompts/main_prompt.py`

**Changes Required:**

```python
# Add explicit citation style enforcement section
CITATION_STYLE_RULES = """
CRITICAL CITATION RULES (ZERO TOLERANCE):
- NEVER use academic numbered citations like [1], [2], [3]
- NEVER use bracket notation for sources: [source], [ref], [citation]
- ALWAYS use inline contextual anchor text: "according to GitHub's 2024 report"
- Link anchor text must be descriptive: "as demonstrated in Amazon's case study"
- Citation numbers are FORBIDDEN in all content fields

Examples of FORBIDDEN patterns:
❌ "Studies show [1] that AI improves productivity [2][3]"
❌ "According to research [1], developers prefer..."
❌ "[Source] indicates that..."

Examples of CORRECT patterns:
✅ "Studies from MIT's 2024 AI Research Lab show that AI improves productivity"
✅ "According to GitHub's Developer Survey, developers prefer..."
✅ "Amazon's 2024 case study indicates that..."
"""

# Add to main prompt template (after tone/style section)
```

**Action Items:**
- [ ] Locate current citation instructions in prompt
- [ ] Replace/enhance with explicit FORBIDDEN patterns
- [ ] Add visual examples (❌ vs ✅)
- [ ] Position prominently in prompt (not buried in middle)

### 1.2 Add Em Dash Prevention

**File**: Same as above

**Changes Required:**

```python
# Add punctuation rules section
PUNCTUATION_RULES = """
PUNCTUATION STANDARDS:
- NEVER use em dashes (—) or their HTML entities (&mdash;, &#8212;)
- Use regular hyphens (-) for ranges: "2024-2025", "cost-effective"
- Use commas, parentheses, or separate sentences for parenthetical clauses
- Use colons (:) for introducing lists or explanations

Examples of FORBIDDEN patterns:
❌ "The tool — despite its cost — improves productivity"
❌ "Organizations are adopting AI&mdash;with mixed results"
❌ "The market is growing&#8212;projected to reach $30B"

Examples of CORRECT patterns:
✅ "The tool, despite its cost, improves productivity"
✅ "Organizations are adopting AI (with mixed results)"
✅ "The market is growing: projected to reach $30B"
"""
```

**Action Items:**
- [ ] Add punctuation rules section to prompt
- [ ] Include all 3 em dash variants in forbidden list
- [ ] Provide alternative punctuation guidance

---

## Phase 2: Schema-Level Validation (P0) 🛡️

### 2.1 Add Content Validators to Pydantic Schema

**File**: `services/blog-writer/pipeline/models/article_schema.py`

**Changes Required:**

```python
from pydantic import BaseModel, Field, field_validator, ValidationError
import re

class ArticleOutput(BaseModel):
    """Article schema with citation and punctuation validation."""
    
    Headline: str = Field(..., description="Article headline")
    # ... other fields ...
    
    @field_validator('Headline', 'Subtitle', 'Teaser', 'Intro', 'Direct_Answer')
    @classmethod
    def validate_no_academic_citations(cls, v: str) -> str:
        """Reject content with academic citation patterns [N]."""
        if re.search(r'\[\d+\]', v):
            raise ValueError(
                f"Academic citations [N] are forbidden. Found in: {v[:100]}... "
                "Use inline contextual links instead."
            )
        return v
    
    @field_validator('Headline', 'Subtitle', 'Teaser', 'Intro', 'Direct_Answer')
    @classmethod
    def validate_no_em_dashes(cls, v: str) -> str:
        """Reject content with em dashes."""
        if re.search(r'—|&mdash;|&#8212;', v):
            raise ValueError(
                f"Em dashes are forbidden. Found in: {v[:100]}... "
                "Use commas, parentheses, or colons instead."
            )
        return v
    
    @field_validator('section_01_content', 'section_02_content', ..., mode='before')
    @classmethod
    def validate_section_content(cls, v: str) -> str:
        """Validate section content for citations and em dashes."""
        if re.search(r'\[\d+\]', v):
            raise ValueError("Academic citations [N] found in section content")
        if re.search(r'—|&mdash;|&#8212;', v):
            raise ValueError("Em dashes found in section content")
        return v
```

**Action Items:**
- [ ] Add `field_validator` decorators for all text fields
- [ ] Create comprehensive regex patterns for both issues
- [ ] Test validation with known bad examples
- [ ] Ensure validation runs BEFORE extraction stage

**Trade-off**: This will cause Gemini calls to fail if violations exist, triggering retry. This is GOOD - forces Gemini to comply.

### 2.2 Update Quality Checker

**File**: `services/blog-writer/pipeline/core/quality_checker.py`

**Changes Required:**

```python
def check_citation_style(article_data: Dict[str, Any]) -> List[str]:
    """Check for academic citation violations."""
    issues = []
    citation_pattern = re.compile(r'\[\d+\]')
    
    # Check all text fields
    for key, value in article_data.items():
        if isinstance(value, str) and citation_pattern.search(value):
            issues.append(f"Academic citation [N] found in {key}: {value[:50]}...")
    
    return issues

def check_em_dashes(article_data: Dict[str, Any]) -> List[str]:
    """Check for em dash violations."""
    issues = []
    em_dash_pattern = re.compile(r'—|&mdash;|&#8212;')
    
    for key, value in article_data.items():
        if isinstance(value, str) and em_dash_pattern.search(value):
            issues.append(f"Em dash found in {key}: {value[:50]}...")
    
    return issues

# Add to overall quality check
def validate_article(article_data: Dict[str, Any]) -> Dict[str, Any]:
    """Run all quality checks."""
    issues = {
        'citation_style_violations': check_citation_style(article_data),
        'em_dash_violations': check_em_dashes(article_data),
        # ... other checks
    }
    return issues
```

**Action Items:**
- [ ] Add citation style checker
- [ ] Add em dash checker
- [ ] Integrate into Stage 10 quality validation
- [ ] Return violations in quality report

---

## Phase 3: Quality Refinement Enhancement (P0) 🔧

### 3.1 Add Citation Style to Stage 2b Checks

**File**: `services/blog-writer/pipeline/blog_generation/stage_02b_quality_refinement.py`

**Changes Required:**

```python
def _check_citation_style(self, article_data: Dict[str, Any]) -> List[QualityIssue]:
    """Detect academic citation patterns."""
    issues = []
    citation_pattern = re.compile(r'\[\d+\]')
    
    for key, value in article_data.items():
        if isinstance(value, str):
            matches = citation_pattern.findall(value)
            if matches:
                issues.append(QualityIssue(
                    type="citation_style",
                    severity="high",
                    field=key,
                    issue=f"Academic citations {matches} found - must use inline contextual links",
                    fix_instruction="Replace [N] with descriptive anchor text like 'according to X study'"
                ))
    
    return issues

def _check_em_dashes(self, article_data: Dict[str, Any]) -> List[QualityIssue]:
    """Detect em dash usage."""
    issues = []
    em_dash_pattern = re.compile(r'—|&mdash;|&#8212;')
    
    for key, value in article_data.items():
        if isinstance(value, str) and em_dash_pattern.search(value):
            issues.append(QualityIssue(
                type="punctuation",
                severity="medium",
                field=key,
                issue="Em dash found - use comma, parentheses, or colon instead",
                fix_instruction="Replace em dash with comma or split into separate sentences"
            ))
    
    return issues

# Add to detect_issues() method
def detect_issues(self, article_data: Dict[str, Any]) -> List[QualityIssue]:
    """Run all quality checks."""
    all_issues = []
    all_issues.extend(self._check_keyword_density(article_data))
    all_issues.extend(self._check_paragraph_length(article_data))
    all_issues.extend(self._check_ai_markers(article_data))
    all_issues.extend(self._check_citation_style(article_data))  # NEW
    all_issues.extend(self._check_em_dashes(article_data))        # NEW
    return all_issues
```

**Action Items:**
- [ ] Add citation style detector to Stage 2b
- [ ] Add em dash detector to Stage 2b
- [ ] Create fix instructions for RewriteEngine
- [ ] Test with known violations
- [ ] Verify rewrite quality

**Expected Behavior**: If violations detected, Stage 2b will trigger RewriteEngine to fix them using Gemini's rewrite mode.

---

## Phase 4: Regex Hardening (P1) 🧹

### 4.1 Comprehensive Citation Regex

**File**: `services/blog-writer/pipeline/processors/html_renderer.py`

**Current Regex** (likely incomplete):
```python
# Probably something like:
content = re.sub(r'\[\d+\]', '', content)
```

**Enhanced Regex** (catches all edge cases):
```python
def strip_academic_citations(html: str) -> str:
    """
    Remove all academic citation patterns comprehensively.
    Handles: [1], [2], [1,2], [1-3], [1][2], mid-sentence [N], etc.
    """
    # Pattern 1: Basic numbered citations [N]
    html = re.sub(r'\[\d+\]', '', html)
    
    # Pattern 2: Range citations [1-3]
    html = re.sub(r'\[\d+\s*-\s*\d+\]', '', html)
    
    # Pattern 3: Comma-separated citations [1,2] or [1, 2]
    html = re.sub(r'\[\d+(?:\s*,\s*\d+)+\]', '', html)
    
    # Pattern 4: Multiple adjacent citations [1][2][3]
    html = re.sub(r'(?:\[\d+\])+', '', html)
    
    # Pattern 5: Citations with spaces [ 1 ]
    html = re.sub(r'\[\s*\d+\s*\]', '', html)
    
    # Pattern 6: Superscript citations <sup>[1]</sup>
    html = re.sub(r'<sup>\s*\[\d+\]\s*</sup>', '', html)
    
    # Cleanup: Remove double spaces left behind
    html = re.sub(r'\s{2,}', ' ', html)
    
    # Cleanup: Fix punctuation after citation removal
    html = re.sub(r'\s+([.,;:!?])', r'\1', html)
    
    return html
```

### 4.2 Comprehensive Em Dash Regex

**Enhanced Regex**:
```python
def replace_em_dashes(html: str) -> str:
    """
    Replace all em dash variants with appropriate punctuation.
    Handles: —, &mdash;, &#8212;, &#x2014;
    """
    # Pattern 1: Unicode em dash
    html = re.sub(r'\s*—\s*', ', ', html)
    
    # Pattern 2: HTML entity &mdash;
    html = re.sub(r'\s*&mdash;\s*', ', ', html)
    
    # Pattern 3: Numeric entity &#8212;
    html = re.sub(r'\s*&#8212;\s*', ', ', html)
    
    # Pattern 4: Hex entity &#x2014;
    html = re.sub(r'\s*&#x2014;\s*', ', ', html)
    
    # Cleanup: Fix spacing around commas
    html = re.sub(r'\s*,\s*', ', ', html)
    
    return html
```

**Action Items:**
- [ ] Replace existing regex with comprehensive patterns
- [ ] Test against known edge cases
- [ ] Add logging when replacements occur
- [ ] Track replacement counts in metrics

---

## Phase 5: Testing Strategy 🧪

### 5.1 Unit Tests for Validators

**File**: `services/blog-writer/tests/test_validators.py` (NEW)

```python
import pytest
from pipeline.models.article_schema import ArticleOutput
from pydantic import ValidationError

class TestCitationValidation:
    def test_reject_basic_citation(self):
        """Should reject [1] pattern."""
        with pytest.raises(ValidationError, match="Academic citations"):
            ArticleOutput(
                Headline="AI Tools [1] Are Great",
                # ... other required fields
            )
    
    def test_reject_multiple_citations(self):
        """Should reject [1][2] pattern."""
        with pytest.raises(ValidationError):
            ArticleOutput(
                Intro="Studies show [1][2] that AI helps",
                # ...
            )
    
    def test_accept_inline_citations(self):
        """Should accept inline contextual links."""
        article = ArticleOutput(
            Headline="AI Tools Are Great",
            Intro="According to GitHub's study, AI helps",
            # ...
        )
        assert article.Intro == "According to GitHub's study, AI helps"

class TestEmDashValidation:
    def test_reject_unicode_em_dash(self):
        """Should reject — character."""
        with pytest.raises(ValidationError, match="Em dashes"):
            ArticleOutput(
                Headline="AI Tools — The Future",
                # ...
            )
    
    def test_reject_html_entity(self):
        """Should reject &mdash; entity."""
        with pytest.raises(ValidationError):
            ArticleOutput(
                Intro="AI is growing&mdash;fast",
                # ...
            )
```

### 5.2 Integration Tests for Stage 2b

**File**: `services/blog-writer/tests/test_stage_02b.py`

```python
@pytest.mark.asyncio
async def test_citation_style_detection():
    """Stage 2b should detect citation violations."""
    article_data = {
        "Headline": "Test Article",
        "Intro": "Research shows [1] that AI helps [2].",
    }
    
    stage = QualityRefinementStage()
    issues = stage.detect_issues(article_data)
    
    citation_issues = [i for i in issues if i.type == "citation_style"]
    assert len(citation_issues) > 0
    assert "[1]" in str(citation_issues)
```

### 5.3 End-to-End Regression Tests

**File**: `services/blog-writer/tests/test_generation_e2e.py`

```python
@pytest.mark.asyncio
async def test_no_academic_citations_in_output():
    """Generated blogs must not contain [N] citations."""
    result = await generate_blog(keyword="test keyword")
    
    html = result.html_content
    assert not re.search(r'\[\d+\]', html), "Academic citations found in output"

@pytest.mark.asyncio
async def test_no_em_dashes_in_output():
    """Generated blogs must not contain em dashes."""
    result = await generate_blog(keyword="test keyword")
    
    html = result.html_content
    assert not re.search(r'—|&mdash;|&#8212;', html), "Em dashes found in output"
```

**Action Items:**
- [ ] Create 20+ test cases covering edge cases
- [ ] Run tests against existing showcase blogs
- [ ] Add to CI/CD pipeline
- [ ] Set test coverage target: 95%+

---

## Phase 6: Monitoring & Metrics 📊

### 6.1 Add Quality Metrics Tracking

**File**: `services/blog-writer/pipeline/core/execution_context.py`

```python
class QualityMetrics(BaseModel):
    """Track quality issues detected and fixed."""
    citation_violations_detected: int = 0
    citation_violations_fixed: int = 0
    em_dash_violations_detected: int = 0
    em_dash_violations_fixed: int = 0
    # ... other metrics
```

### 6.2 Add Logging

**File**: `services/blog-writer/pipeline/processors/html_renderer.py`

```python
# Log when cleanup is triggered (should be rare after P0 fixes)
if citation_matches := re.findall(r'\[\d+\]', html):
    logger.warning(
        f"⚠️  Regex cleanup caught {len(citation_matches)} academic citations "
        f"that passed validation. Investigate prompt/schema!"
    )
```

---

## Success Criteria 🎯 (UPDATED)

### P0 Goals (Must Achieve Before Next Blog Generation)
- [ ] **0% malformed headings** ("What is X?" format clean)
- [ ] **0% sentence fragments** (no orphaned punctuation)
- [ ] **100% working citation links** (real URLs, not #source-N)
- [ ] **0% keyword line breaks** (keywords stay inline)
- [ ] **0% cutoff sentences** (all sentences complete)
- [ ] **0% academic citations** `[N]` in generated content
- [ ] **0% em dashes** in generated content

### P1 Goals (Next Sprint)
- [ ] **Internal links present** in all blogs (5+ per article)
- [ ] **Citations numbered correctly** (starting from [1])
- [ ] **Consistent list formatting** (always `<ul>/<ol>`)
- [ ] **95%+ test coverage** for all validators

### Measurement Plan
1. **Immediate**: Fix showcase-20251207-173434-0 HTML manually to verify fixes work
2. **Baseline**: Re-run showcase script (5 blogs) with Phase 0 fixes
3. **Validation**: All 5 must pass P0 criteria (0 critical issues)
4. **Regression**: Add to nightly CI test suite

---

## Implementation Timeline (UPDATED)

### Week 1: HOTFIX Critical Issues (P0 - URGENT)
- **Day 1**: Fix malformed headings + sentence fragments (0.1, 0.2)
- **Day 2**: Fix citation links + keyword formatting (0.3, 0.4)
- **Day 3**: Fix cutoffs + citation numbering (0.5, 0.6)
- **Day 4**: Fix internal links + list formatting (0.7, 0.8)
- **Day 5**: Test all fixes, run 5-blog showcase validation

### Week 2: Prevention & Validation (P0)
- **Day 1-2**: Update prompts with all new rules (Phase 1)
- **Day 3-4**: Add schema validators (Phase 2.1)
- **Day 5**: Add quality checker updates (Phase 2.2)

### Week 3: Enhancement & Monitoring (P1)
- **Day 1-2**: Enhance Stage 2b (Phase 3)
- **Day 3-4**: Write comprehensive tests (Phase 5)
- **Day 5**: Add metrics tracking (Phase 6)

---

## Risk Assessment & Mitigation

### Risk 1: Schema Validation Breaks Generation
**Impact**: High (blocks all generation if too strict)  
**Mitigation**: 
- Add try-catch in validation
- Log violations but don't block initially (warning mode)
- Gradually enable blocking after testing

### Risk 2: Prompt Changes Degrade Quality
**Impact**: Medium (might affect AEO scores)  
**Mitigation**:
- A/B test new prompts against baseline
- Monitor AEO scores before/after
- Rollback if scores drop >5 points

### Risk 3: Performance Impact
**Impact**: Low (validators add ~10ms per blog)  
**Mitigation**:
- Profile validation code
- Optimize regex patterns
- Cache compiled patterns

---

## Rollout Strategy

### Phase 1: Canary (10% traffic)
- Enable P0 fixes for 10% of blogs
- Monitor for regressions
- Collect metrics on violation rates

### Phase 2: Gradual (50% traffic)
- If canary succeeds, expand to 50%
- Continue monitoring
- Fix any edge cases discovered

### Phase 3: Full (100% traffic)
- Deploy to all blogs
- Enable blocking mode for validators
- Archive old regex-only approach

---

## Alternative Approaches (Rejected)

### Alternative 1: Post-Processing Only (Regex)
**Why Rejected**: Reactive, doesn't fix root cause, brittle

### Alternative 2: Custom Gemini Fine-Tune
**Why Rejected**: Expensive, slow iteration, not guaranteed to work

### Alternative 3: Second-Pass Gemini Call for Cleanup
**Why Rejected**: Doubles cost, adds latency, masks root issue

---

## Conclusion

This plan takes a **defense-in-depth** approach:
1. **Prevent** at source (prompts) - 90% effective
2. **Validate** before render (schema + quality gate) - 9% effective
3. **Cleanup** as last resort (regex) - 1% effective

**Expected Outcome**: 100% elimination of both issues with sustainable, maintainable solution.

**Key Principle**: Fix the root cause (Gemini's output) rather than patching symptoms (HTML cleanup).

