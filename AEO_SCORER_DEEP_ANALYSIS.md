# AEO Scorer Deep Analysis - Issues Found

## Component Breakdown

### 1. Direct Answer (25 points)

**Current Logic:**
- Exists: 10 points
- Length 40-60 words: 5 points (30-40 or 60-80: 2.5 points)
- Contains keyword: 5 points
- Contains citation: 5 points

**Issues:**
1. **Missing keyword/citation still gets 10 points** - If Direct Answer exists but missing both keyword AND citation, it gets 10/25. Should it be penalized more?
2. **Length check uses `direct_answer.split()`** - This counts HTML tags as words! Should strip HTML first.
3. **Citation check looks for academic `[N]`** - But we strip academic citations in HTML renderer! So this will never match.
4. **Fallback to Intro** - If Direct Answer missing, checks Intro for keyword (5 points). But this is inconsistent - why not check Intro for citation too?

### 2. Q&A Format (20 points)

**Current Logic:**
- FAQ 5-6 items: 10 points (3-4: 7 points, 1-2: 3 points)
- PAA 3-4 items: 5 points (2: 3 points, 1: 1 point)
- Question headers: 5 points (2+: 5 points, 1: 2.5 points)

**Issues:**
1. **Question headers check is redundant** - We convert section titles to questions in Stage 10, so this might double-count with Q&A format.
2. **Question headers check looks in section titles** - But we also check question patterns in content separately. This might be double-counting.
3. **FAQ/PAA thresholds might be too strict** - 5-6 FAQ items is a lot. What if article only needs 3-4?

### 3. Citation Clarity (15 points)

**Current Logic:**
- Citation presence (8+): 5 points (5+: 4, 3+: 3, 1+: 2)
- Sources list (5+): 5 points (3+: 4, 1+: 2.5)
- Distribution (50%+ paragraphs): 5 points (30%+: 3, 15%+: 1.5)

**Issues:**
1. **Academic citations are stripped** - We strip `[N]` citations in HTML renderer, so `academic_citations` will always be 0! This means we're only counting natural citations.
2. **Natural citation patterns might be too strict** - Patterns like `r'[A-Z][a-z]+ reports? that'` require "that" after "reports", but Gemini might write "Gartner reports..." without "that".
3. **Distribution check uses `<p>` tags** - But content might not have `<p>` tags if it's raw HTML. Fallback splits by `\n\n` which might not work.
4. **8+ citations threshold is high** - What if article only needs 5-6 citations? Still gets 4 points, but might be penalized unnecessarily.

### 4. Natural Language (15 points)

**Current Logic:**
- Conversational phrases (8+): 6 points (5+: 4, 2+: 2)
- Direct statements vs vague: 5 points
- Question patterns (5+): 4 points (3+: 3, 1+: 1.5)

**Issues:**
1. **Direct statements check is flawed** - Compares vague patterns (`might be`, `could be`) vs direct patterns (`is `, `are `). But `is ` and `are ` are too common - almost every sentence has them! This will almost always score 5 points.
2. **Question patterns double-count** - We check question patterns in content AND question headers separately. This might be double-counting.
3. **Conversational phrases list includes question patterns** - "what is", "how does" are in conversational phrases AND question patterns. Double-counting?
4. **Question patterns use regex** - `r"what is"` will match "what is" anywhere, even in "whatever is" or "somewhat is". Should use word boundaries.

### 5. Structured Data (10 points)

**Current Logic:**
- Lists (3+): 5 points (1+: 2.5)
- Headings (3+ H2 and 2+ H3): 5 points (2+ H2: 2.5)

**Issues:**
1. **Section titles double-counted** - Section titles are counted as H2, but we also count explicit `<h2>` tags. If section titles are rendered as `<h2>`, this double-counts.
2. **H3 requirement might be too strict** - Requires 2+ H3 tags for full points. But many articles don't need H3 tags.
3. **List count is simple** - Just counts `<ul>` and `<ol>` tags. Doesn't check if lists are meaningful or have enough items.

### 6. E-E-A-T (15 points)

**Current Logic:**
- Experience (bio has keywords): 4 points (bio exists: 2)
- Expertise (bio has credentials): 4 points (bio exists: 1)
- Authoritativeness (author_url): 4 points (author_name: 2)
- Trustworthiness (credible sources): 3 points (multiple sources: 1)

**Issues:**
1. **Always 0 if input_data is None** - But we build input_data in Stage 10, so this should work. However, if company_data is missing, this is always 0.
2. **Experience/Expertise both check author_bio** - If bio has "experience" keyword, gets 4 points. If bio has "degree" keyword, gets 4 points. But if bio has both, still only gets 4+4=8 points. This is correct, but might be too lenient.
3. **Trustworthiness checks for `.edu`, `.gov`, `.org`** - But most tech sources are `.com`! This penalizes legitimate sources like Gartner, Forrester, IBM.
4. **Credible domains list is outdated** - Wikipedia is in the list, but Wikipedia isn't always credible for tech content.

## Critical Issues Summary

1. **Academic citations stripped but scorer looks for them** - Mismatch!
2. **Direct Answer length check doesn't strip HTML** - Counts HTML tags as words!
3. **Direct statements check is too lenient** - Almost always scores 5 points
4. **Question patterns might double-count** - Checked in content AND headers
5. **Trustworthiness penalizes `.com` sources** - But most tech sources are `.com`!
6. **Section titles might double-count as H2** - If rendered as `<h2>`, counted twice

## Recommendations

1. **Fix citation detection** - Don't look for academic citations if we strip them, OR don't strip them
2. **Strip HTML before word count** - For Direct Answer length check
3. **Fix direct statements check** - Use better patterns or remove if too lenient
4. **Fix trustworthiness** - Add tech sources like Gartner, Forrester, IBM to credible list
5. **Remove double-counting** - Question patterns OR question headers, not both
6. **Fix section title counting** - Don't double-count if rendered as `<h2>`

