# AEO Score Fix Analysis - Deep Inspection

## Current Score: 68.5/100 (Target: 80+)

## Issues Identified

### 1. Direct Answer: 15.0/25 (Losing 10 points)

**Problems:**
- ❌ Missing primary keyword "cybersecurity automation" (-5 points)
- ❌ Missing citation (-5 points)
- ✅ Length: 60 words (acceptable, 5 points)

**Root Cause Analysis:**

**Issue 1.1: Direct Answer optimization condition is TOO RESTRICTIVE**
```python
# Current code (line 716):
if direct_answer and (direct_answer_words < 30 or direct_answer_words > 70 or not has_citation_in_da):
```

**Problem:** 
- Direct Answer is 60 words (within 30-70 range)
- Condition only checks: `< 30 OR > 70 OR missing citation`
- **Missing keyword check is NOT in the condition!**
- Result: Optimization doesn't run even though keyword is missing

**Fix:**
```python
# Should be:
if direct_answer and (
    direct_answer_words < 30 or 
    direct_answer_words > 70 or 
    not has_citation_in_da or
    primary_keyword.lower() not in direct_answer.lower()  # ADD THIS
):
```

**Issue 1.2: Citation detection patterns mismatch**
- Stage 2b uses: `r'according to [A-Z]'`, `r'[A-Z][a-z]+ reports?'`
- AEO scorer uses: `r'according to [A-Z]'`, `r'[A-Z][a-z]+ (reports?|states?|notes?|found)'`
- **AEO scorer is more lenient** - includes "states", "notes", "found"
- Stage 2b might miss citations that AEO scorer would count

**Fix:** Align Stage 2b patterns with AEO scorer patterns

**Issue 1.3: Direct Answer content has HTML tags**
- Direct Answer contains: `"Here's how <p>API security testing..."`
- HTML tags might interfere with keyword/citation detection
- Should strip HTML before checking

**Fix:** Strip HTML tags before keyword/citation detection

---

### 2. Natural Language: 11.0/15 (Losing 4 points)

**Problems:**
- ✅ Conversational phrases: 10 (good, 6 points)
- ❌ Question patterns: 0 (bad, 0 points - should be 4 points for 5+)

**Root Cause Analysis:**

**Issue 2.1: Question patterns not being added by Gemini**
- Stage 2b asks Gemini to add question patterns in the prompt
- But Gemini might not be following through
- Need to verify if Gemini actually added them

**Issue 2.2: Question pattern detection might be too strict**
- Patterns: `['what is', 'how does', 'why does', 'when should', 'where can', 'how can', 'what are']`
- These are exact substring matches (case-insensitive)
- But content might have variations like "What is" at start of sentence vs "what is" in middle

**Issue 2.3: Question patterns need to be in CONTENT, not just titles**
- AEO scorer checks `all_content` (Intro + sections)
- But question patterns might only be in section titles (which are converted to questions)
- Need to ensure question patterns are in the BODY content

**Fix:** 
1. Make prompt more explicit: "Add AT LEAST 5 question patterns like 'What is X?', 'How does Y work?', 'Why should Z?'"
2. Verify Gemini actually added them (post-optimization check)
3. If missing, add them via regex fallback

---

### 3. E-E-A-T: 0.0/15 (Losing 15 points)

**Problem:**
- E-E-A-T scoring requires `input_data` parameter
- Currently passing `None`, so score is always 0

**Root Cause:**
- `input_data` contains author bio, company info, etc.
- Not being passed to AEO scorer in Stage 10

**Fix:** Pass `input_data` from `context.job_config` or `context.company_data`

---

## Fix Priority

### Priority 1: CRITICAL (Fixes 10+ points)
1. **Fix Direct Answer optimization condition** - Add keyword check
2. **Fix Direct Answer citation/keyword detection** - Strip HTML, align patterns
3. **Ensure Direct Answer optimization actually runs** - Current condition is too restrictive

### Priority 2: HIGH (Fixes 4+ points)
4. **Add question patterns verification** - Check if Gemini added them, add fallback
5. **Make question pattern prompt more explicit** - Give examples

### Priority 3: MEDIUM (Fixes 15 points, but requires input_data)
6. **Pass input_data to AEO scorer** - For E-E-A-T scoring

---

## Detailed Fixes

### Fix 1: Direct Answer Optimization Condition

**File:** `pipeline/blog_generation/stage_02b_quality_refinement.py`

**Current (line 716):**
```python
if direct_answer and (direct_answer_words < 30 or direct_answer_words > 70 or not has_citation_in_da):
```

**Fixed:**
```python
# Check if Direct Answer needs optimization
primary_keyword = context.job_config.get("primary_keyword", "") if context.job_config else ""
direct_answer_text = re.sub(r'<[^>]+>', '', direct_answer) if direct_answer else ""  # Strip HTML
has_keyword_in_da = primary_keyword.lower() in direct_answer_text.lower() if primary_keyword and direct_answer_text else False

if direct_answer and (
    direct_answer_words < 30 or 
    direct_answer_words > 70 or 
    not has_citation_in_da or
    not has_keyword_in_da  # ADD: Check for keyword
):
```

### Fix 2: Align Citation Detection Patterns

**File:** `pipeline/blog_generation/stage_02b_quality_refinement.py`

**Current (line 601-604):**
```python
natural_citation_patterns = [
    r'according to [A-Z]', r'[A-Z][a-z]+ reports?', r'[A-Z][a-z]+ states?',
    r'[A-Z][a-z]+ notes?', r'[A-Z][a-z]+ predicts?', r'research by [A-Z]',
]
```

**Fixed (align with AEO scorer):**
```python
natural_citation_patterns = [
    r'according to [A-Z]',
    r'[A-Z][a-z]+ (reports?|states?|notes?|found)',  # Match AEO scorer pattern
    r'[A-Z][a-z]+ predicts?',
    r'research (by|from) [A-Z]',  # Match AEO scorer pattern
]
```

### Fix 3: Strip HTML Before Detection

**File:** `pipeline/blog_generation/stage_02b_quality_refinement.py`

**Add before line 618:**
```python
# Strip HTML for accurate detection
import re
direct_answer_text = re.sub(r'<[^>]+>', '', direct_answer) if direct_answer else ""
has_citation_in_da = any(re.search(pattern, direct_answer_text, re.IGNORECASE) for pattern in natural_citation_patterns) if direct_answer_text else False
has_keyword_in_da = primary_keyword.lower() in direct_answer_text.lower() if primary_keyword and direct_answer_text else False
```

### Fix 4: Verify Question Patterns After Optimization

**File:** `pipeline/blog_generation/stage_02b_quality_refinement.py`

**Add after section optimization (around line 713):**
```python
# Verify question patterns were added
all_content_after = article_dict.get('Intro', '') + ' ' + article_dict.get('Direct_Answer', '')
for i in range(1, 10):
    all_content_after += ' ' + article_dict.get(f'section_{i:02d}_content', '')
question_count_after = sum(1 for pattern in question_patterns if pattern in all_content_after.lower())

if question_count_after < 5:
    logger.warning(f"⚠️ Only {question_count_after} question patterns found after optimization (target: 5+)")
    # Could add fallback regex injection here if needed
```

### Fix 5: More Explicit Question Pattern Prompt

**File:** `pipeline/blog_generation/stage_02b_quality_refinement.py`

**Current (line 653-655):**
```python
3. Add question patterns naturally (target: 5+ total)
   - Use: "what is", "how does", "why does", "when should", "where can"
   - Add 2-3 more question patterns if below 5 total
```

**Fixed:**
```python
3. Add question patterns naturally (target: 5+ total) - CRITICAL FOR AEO SCORE
   - Use these EXACT patterns: "What is", "How does", "Why does", "When should", "Where can", "How can", "What are"
   - Add AT LEAST 5 question patterns total across all sections
   - Examples: "What is API security testing?", "How does automation help?", "Why should you implement this?"
   - Add 3-5 more question patterns if currently below 5 total
```

### Fix 6: Pass input_data to AEO Scorer

**File:** `pipeline/processors/quality_checker.py`

**Current (line 130-134):**
```python
comprehensive_score = scorer.score_article(
    output=article_output,
    primary_keyword=primary_keyword,
    input_data=input_data,
)
```

**Check if input_data is being passed correctly from Stage 10**

---

## Expected Score After Fixes

**Current:** 68.5/100
**After Fix 1-3 (Direct Answer):** +10 points = 78.5/100
**After Fix 4-5 (Question Patterns):** +4 points = 82.5/100
**After Fix 6 (E-E-A-T):** +15 points = 97.5/100 (if input_data available)

**Target:** 80+ (achievable with Fixes 1-5)

---

## Testing Plan

1. Run test with fixes
2. Verify Direct Answer has keyword and citation
3. Verify question patterns >= 5
4. Check AEO score >= 80

