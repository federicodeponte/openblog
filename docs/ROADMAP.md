# Implementation Roadmap - Python Blog Writing System

**Status**: Pre-Implementation (Stage 0 Ready)
**Last Updated**: 2025-11-19
**Architecture Document**: `PYTHON_WORKFLOW_ARCHITECTURE.md` (2,106 lines - final)
**Current Focus**: Pre-implementation decisions and Stage 0 setup

---

## Quick Navigation

- **Pre-Implementation**: Must resolve 3 critical decisions before starting
- **Stage 0-11**: 12 implementation stages (sequential + parallel)
- **Progress Tracking**: Update status as you complete each stage
- **Decision Log**: Track all implementation choices
- **Blockers**: List issues that need resolution

---

## Part 1: Pre-Implementation Checklist ⚠️ MUST COMPLETE FIRST

### Decision 1: Response Format (CRITICAL) 🔴

**What**: Gemini API response format - impacts tools integration and response parsing

**Architecture Reference**: `PYTHON_WORKFLOW_ARCHITECTURE.md` Part 4k

**Options**:

#### Option A: `text/plain` (Matches v4.1 Exactly)
- ✅ Matches v4.1 workflow
- ✅ Tools (googleSearch, urlContext) confirmed to work
- ✅ Proven in production
- ❌ Requires JSON extraction from text (regex parsing)
- ❌ More complex error handling

**Implementation (Part 4e code example available)**:
```python
from google.genai.types import Tool, GoogleSearch, UrlContext

config = GenerateContentConfig(
    response_mime_type="text/plain",
    tools=[
        Tool(url_context=UrlContext()),
        Tool(google_search=GoogleSearch())
    ]
)
```

**Note**: `maxOutputTokens` may be set at model/API level (not in JSON body)

#### Option B: `application/json` (Current Implementation)
- ✅ Structured output (no parsing needed)
- ✅ More reliable
- ❌ Different from v4.1
- ❌ Unknown tools compatibility
- ❌ May need to disable tools

**Implementation**:
```python
config = GenerateContentConfig(
    response_mime_type="application/json",
    response_json_schema=content_schema,
    tools=[...]  # Unknown if compatible
)
```

**Testing Required** (Part 4k):
1. Test if tools work with text/plain response
2. Test if tools work with application/json + schema
3. Document findings

**Decision**:
- [ ] Approach A: text/plain (v4.1 match)
- [ ] Approach B: application/json (current)
- [ ] Decision date: ________
- [ ] Test results: ________

---

### Decision 2: Tools Compatibility Testing

**What**: Verify tools (googleSearch, urlContext) work with chosen response format

**Architecture Reference**: Part 4k Testing Strategy

**Required Tests**:

```python
# Test 1: Tools + text/plain
config_a = GenerateContentConfig(
    response_mime_type="text/plain",
    tools=[Tool(url_context=...), Tool(google_search=...)]
)
response_a = model.generate_content(prompt, config_a)
# Check: Does response contain web search results?

# Test 2: Tools + application/json
config_b = GenerateContentConfig(
    response_mime_type="application/json",
    response_json_schema=schema,
    tools=[...]
)
response_b = model.generate_content(prompt, config_b)
# Check: Does response use tools? Or is schema constraining output?
```

**Status**:
- [ ] Test 1 passed (text/plain + tools)
- [ ] Test 2 passed (application/json + tools)
- [ ] Compatibility verified
- [ ] Test results: ________

---

### Decision 3: Image Generation Service

**What**: Which service to use for image generation in Stage 9

**Options** (Architecture Part 4e):
- [ ] Replicate (Stable Diffusion)
- [ ] DALL-E 3 (via OpenAI)
- [ ] Midjourney (async)
- [ ] Other: ________

**Selection Criteria**:
- Cost per image
- Quality
- Speed
- Availability
- Setup complexity

**Decision**: ________
**Credentials Setup**:
- [ ] API key obtained
- [ ] Environment variable set
- [ ] Tested successfully

---

### Environment Setup Checklist

**Credentials to Configure** (Part 4e reference):

```bash
# Gemini API
export GOOGLE_GEMINI_API_KEY="..."
export GOOGLE_PROJECT_ID="..."

# Supabase
export SUPABASE_URL="..."
export SUPABASE_API_KEY="..."
export SUPABASE_SERVICE_ROLE_KEY="..."

# Google Search (for AI Agent3 in Stage 4)
export GOOGLE_SEARCH_API_KEY="..."  # Serper.dev or similar

# Image Generation (chosen in Decision 3)
export REPLICATE_API_TOKEN="..."  # If Replicate
# OR
export OPENAI_API_KEY="..."  # If DALL-E

# Optional: Google Drive backup
export GOOGLE_DRIVE_ENABLED="false"
export GOOGLE_DRIVE_FOLDER_ID="..."
```

**Setup Status**:
- [ ] Gemini API configured
- [ ] Supabase configured
- [ ] Google Search configured
- [ ] Image service configured
- [ ] All credentials tested

---

### Baseline Resources to Copy

**Part 5b - Baseline Prompts**: Copy these to your codebase

- [ ] `src/prompts/main_article.py` - Copy baseline from Part 5b
- [ ] `src/prompts/citations_generator.py` - Framework provided
- [ ] `src/prompts/toc_headers.py` - Framework provided
- [ ] `src/prompts/faq_generator.py` - Framework provided
- [ ] `src/prompts/image_prompt.py` - Framework provided

---

## Part 2: Stage-by-Stage Implementation Guide

### Stage 0: Data Fetch & Preparation

**Status**: [ ] Not Started | [ ] In Progress | [ ] Complete
**Architecture Lines**: 435-447
**v4.1 Mapping**: Phase 1, Steps 1-3
**Duration Estimate**: 2-4 hours

**Purpose**: Fetch job config and auto-detect company information from `company_url`

**Inputs**:
- `primary_keyword` (required) - Main topic/keyword for the blog article
- `company_url` (required) - Company website URL for auto-detection
- Optional override fields (if user wants to override auto-detection)

**Outputs**:
- ExecutionContext (populated with job_config, auto-detected company_data, blog_page, language)

**Sub-steps**:
- [ ] Sub-step 1: Validate required fields (`primary_keyword`, `company_url`)
- [ ] Sub-step 2: Auto-detect company info from `company_url`:
  - Scrape website to extract company name, location, language
  - Use Gemini to analyze company info (industry, business model, products)
  - Fetch sitemap to build internal links pool
- [ ] Sub-step 3: Apply user overrides (if provided):
  - Use provided `company_name` if available, otherwise use auto-detected
  - Use provided `company_location` if available, otherwise use auto-detected
  - Use provided `company_language` if available, otherwise use auto-detected
  - Use provided `links` if available, otherwise use auto-fetched from sitemap
- [ ] Sub-step 4: Normalize field names and build ExecutionContext
- [ ] Sub-step 5: Handle errors gracefully (invalid URL, scraping failures, etc.)

**Note**: If Supabase is used as entry point, fetch `primary_keyword` and `company_url` from Supabase, then proceed with auto-detection.

**Code Files to Create**:
```
src/stages/stage_00_data_fetch.py          # Main stage class
src/models/supabase_client.py              # Supabase wrapper (if not exists)
tests/test_stage_00.py                     # Unit + integration tests
```

**Implementation Checklist**:
- [ ] Create `stage_00_data_fetch.py` with `DataFetchStage` class
- [ ] Implement `execute(context)` method
- [ ] Add Supabase fetch logic
- [ ] Add field name normalization
- [ ] Add input validation
- [ ] Handle missing fields gracefully
- [ ] Write unit tests
- [ ] Test with real Supabase (if available)
- [ ] Test with mock data (if no Supabase)

**Blockers**:
- [ ] None identified

**Next Stage After Complete**: Stage 1 (Prompt Construction)

---

### Stage 1: Prompt Construction

**Status**: [ ] Not Started | [ ] In Progress | [ ] Complete
**Architecture Lines**: 450-470
**v4.1 Mapping**: Phase 2, Step 4
**Duration Estimate**: 3-6 hours

**Purpose**: Build main article prompt with all AEO constraints

**Inputs**:
- ExecutionContext.job_config
- Baseline prompt from Part 5b

**Outputs**:
- ExecutionContext.prompt (complete instruction set)

**Key Constraints** (from Part 5b baseline):
- Paragraph max: 25-30 words ✅
- Internal links: 1 per H2 section ✅
- FAQ: 5 items minimum ✅
- PAA: 3 items minimum ✅
- McKinsey/BCG style ✅
- Tone: Coaching, not threatening ✅

**Sub-steps**:
- [ ] Load baseline prompt template from `prompts/main_article.py` (Part 5b)
- [ ] Inject variables (keyword, company_data, competitors, language)
- [ ] Apply AEO constraints
- [ ] Build final prompt string

**Code Files to Create**:
```
src/stages/stage_01_prompt_build.py        # Main stage
src/prompts/main_article.py                # Baseline template (from Part 5b)
tests/test_stage_01.py                     # Tests
```

**Implementation Checklist**:
- [ ] Copy baseline prompt from Part 5b to `src/prompts/main_article.py`
- [ ] Create `stage_01_prompt_build.py`
- [ ] Implement `get_main_article_prompt(config)` function
- [ ] Test variable injection
- [ ] Test with different languages
- [ ] Write unit tests
- [ ] Test prompt length/quality

**Blockers**:
- [ ] None (baseline provided in Part 5b)

**Next Stage After Complete**: Stage 2 (Gemini Call)

---

### Stage 2: Gemini Content Generation ⚠️ TOOLS INTEGRATION CRITICAL

**Status**: [ ] Not Started | [ ] In Progress | [ ] Complete
**Architecture Reference**: Part 4k (Response Format Decision) - Stage 2 section
**v4.1 Mapping**: Phase 2, Step 5 (gemini-research)
**Duration Estimate**: 8-12 hours
**BLOCKER**: Tools compatibility test (Decision 1 - test required before implementation)

**Purpose**: Generate content with deep research via tools + prompt rules

**DEEP RESEARCH MECHANISM** (NO separate Stage 1.5 needed):
- Gemini tools (googleSearch, urlContext) conduct real-time web searches during writing
- Prompt rules force research: "every paragraph must contain number, KPI or real example"
- Combined effect: Gemini naturally conducts 20+ searches while generating content
- No separate research phase - integrated directly into content generation

**Inputs**:
- ExecutionContext.prompt (from Stage 1)

**Outputs**:
- ExecutionContext.raw_article (raw Gemini response: plain text with embedded JSON)

**Mandatory Configuration** (matches v4.1 exactly):
```python
from google.genai.types import Tool, GoogleSearch, UrlContext
from google.generativeai import GenerateContentConfig

config = GenerateContentConfig(
    response_mime_type="text/plain",           # ⚠️ NOT application/json
    temperature=0.2,                            # Consistency
    max_output_tokens=65536,                    # Full article
    tools=[
        Tool(url_context=UrlContext()),         # Ground in URLs
        Tool(google_search=GoogleSearch())      # Real-time web search (CRITICAL)
    ]
)
```

**Prompt Baseline** (from your v4.1 example - copy from PYTHON_WORKFLOW_ARCHITECTURE.md Stage 2):
- Injected fields: primary_keyword, company_info, language, competitors, internal_links
- 15 content rules (paragraph length, keyword placement, FAQ/PAA separation, etc.)
- Output schema with 30+ fields (headline, sections 01-09, FAQ, PAA, sources, queries)
- JSON format specification

**Retry Configuration**:
- Max retries: 3
- Wait between retries: 5000 ms (5 seconds)
- Backoff multiplier: 2 (exponential)
- Retry on: Rate limits, timeouts, network errors
- Don't retry on: Malformed JSON, validation errors

**Sub-steps**:
- [ ] Initialize Gemini client with tools ENABLED
- [ ] Load baseline prompt (use your template from PYTHON_WORKFLOW_ARCHITECTURE.md)
- [ ] Inject variables: keyword, company_info, language, competitors, links
- [ ] Call Gemini 3.0 Pro with text/plain + tools config
- [ ] Handle streaming response
- [ ] Extract JSON blocks from plain text response (regex: `\{[\s\S]*?\}`)
- [ ] Parse and concatenate JSON blocks
- [ ] Implement retry logic with exponential backoff

**Code Files to Create**:
```
src/stages/stage_02_gemini_call.py         # Main stage
src/models/gemini_client.py                # Gemini wrapper with tools
tests/test_stage_02.py                     # Comprehensive tests
```

**Implementation Checklist**:
- [ ] **VERIFY**: Tools compatibility test PASSED (run Decision 1 test first)
- [ ] Create `src/models/gemini_client.py` with:
  - [ ] GeminiClient class
  - [ ] Tools configuration (googleSearch + urlContext)
  - [ ] Response parsing (JSON extraction from text/plain)
  - [ ] Retry logic with exponential backoff
- [ ] Create `src/stages/stage_02_gemini_call.py` with:
  - [ ] Prompt injection (use baseline from Architecture Stage 2)
  - [ ] API configuration (text/plain + tools)
  - [ ] Response handling
- [ ] Test with real Gemini API (verify web search results in response)
- [ ] Test JSON extraction from text/plain response
- [ ] Test retry logic (simulate API failures)
- [ ] Verify tools are being used (check for URLs in response)
- [ ] Write comprehensive tests

**Critical Testing Requirements**:
- [ ] Test 1: Verify googleSearch tool produces web results
- [ ] Test 2: Verify urlContext tool grounds citations
- [ ] Test 3: Verify tools work with text/plain (NOT application/json)
- [ ] Test 4: Verify JSON extraction from plain text response
- [ ] Test 5: Verify retry logic on API failures
- [ ] Test 6: Verify response contains 8+ sources (minimum requirement)
- [ ] Test 7: Verify response contains 3+ sections (minimum structure)

**Blockers**:
- [ ] **BLOCKING**: Tools compatibility test must PASS before implementation
  - Run: `python scripts/test_tools_compatibility.py`
  - Expected: Response contains web URLs and grounded information
  - If failed: May need to disable tools (but loses v4.1 parity)

**Success Criteria**:
- Tools (googleSearch, urlContext) confirmed working
- Response contains grounded web information and citations
- JSON extraction handles edge cases (nested JSON, streaming chunks)
- Retry logic handles API failures gracefully
- Output matches expected schema from Architecture Stage 2

**Next Stage After Complete**: Stage 3 (Structured Extraction)

---

### Stage 3: Structured Extraction

**Status**: [ ] Not Started | [ ] In Progress | [ ] Complete
**Architecture Lines**: 494-528
**v4.1 Mapping**: Phase 3, Steps 6-7
**Duration Estimate**: 4-6 hours

**Purpose**: Extract structured data from Gemini response

**Inputs**:
- ExecutionContext.raw_article (from Stage 2)

**Outputs**:
- ExecutionContext.structured_data (Pydantic model with all fields)

**Conditional Logic** (Part 4c):
- `information_incomplete?`: If extraction incomplete, retry (max 2 times)
- Completion check: Validate all critical fields present

**Sub-steps**:
- [ ] Sub-step 1: Concatenate Gemini response text (Step 6)
- [ ] Sub-step 2: Use LLM Information Extractor (Step 7)
- [ ] Extract all required fields (headline, sections, FAQ, PAA, key_takeaways, sources)
- [ ] Validate against OutputSchema
- [ ] Check `information_incomplete?`: All fields populated?
- [ ] Implement retry logic: Max 2 retries, 2 second delay
- [ ] Handle partial data gracefully

**Fields to Extract** (from Part 5b baseline output):
```
headline, subtitle, teaser, direct_answer, intro
meta_title, meta_description, lead_survey_title, lead_survey_button
section_01_title...section_09_title
section_01_content...section_09_content
key_takeaway_01, 02, 03
faq_01_question...faq_06_question (+ answers)
paa_01_question...paa_04_question (+ answers)
sources (URLs with descriptions)
search_queries
```

**Code Files to Create**:
```
src/stages/stage_03_extraction.py          # Main stage
src/processors/extractor.py                # LLM extraction logic
tests/test_stage_03.py                     # Tests
```

**Implementation Checklist**:
- [ ] Create `stage_03_extraction.py`
- [ ] Create `src/processors/extractor.py` (LLM-based)
- [ ] Implement field extraction for all 25+ fields
- [ ] Implement `information_incomplete?` check
- [ ] Implement retry logic (max 2)
- [ ] Implement graceful degradation (allow partial data)
- [ ] Validate against OutputSchema
- [ ] Write tests for each field extraction
- [ ] Test with missing/malformed data

**Blockers**:
- [ ] None (previous stage complete)

**Next Stage After Complete**: Stages 4-9 (Parallel - all start together)

---

### Stages 4-9: Parallel Execution

**Status**: [ ] Not Started | [ ] In Progress | [ ] Complete
**Architecture Lines**: 519-751
**Duration Estimate**: 8-12 hours (total, not per stage)
**Execution**: All 6 stages run concurrently via `asyncio.gather()`

**Critical Note** (Part 4b): Each "parallel stage" has internal sequential dependencies. Total execution time = slowest branch (6 steps)

---

### Stage 4: Citations

**Status**: [ ] Not Started | [ ] In Progress | [ ] Complete
**Architecture Lines**: 536-585
**v4.1 Mapping**: Phase 4, Steps 8-13
**Duration Estimate**: 4-6 hours
**Bottleneck**: AI Agent3 validation loop (up to 20 iterations)

**Purpose**: Validate and format citation sources

**Inputs**:
- ExecutionContext.structured_data.sources

**Outputs**:
- ParallelResult.citations_html

**Conditional Logic** (Part 4c):
- `citations_disabled?`: If true, skip entire stage, return empty citations_html

**6 Sequential Sub-steps** (WITHIN parallel stage):
- [ ] Sub-step 1: CitationSanitizer (Step 8) - Remove citation markers from content
- [ ] Sub-step 1b: CitationSanitizer1 (Step 8b) - Second pass cleanup
  - Remove empty brackets [] left behind from marker removal
  - Clean up spacing/formatting artifacts
- [ ] Sub-step 2: Information Extractor1 (Step 9) - Extract URLs from sources
- [ ] Sub-step 3: Split Out1 (Step 10) - Create one item per citation
- [ ] Sub-step 4: AI Agent3 (Step 11) - Validate URLs (agentic loop, max 20 iterations)
  - Tools: serperTool (web search for alternatives), validTool (HTTP validation)
  - Fallback: Return company URL if all validation fails
- [ ] Sub-step 5: format-output1 (Step 12) - Format citations
- [ ] Sub-step 6: literature-formatter (Step 13) - Convert to HTML

**Code Files to Create**:
```
src/stages/stage_04_citations.py           # Main stage
src/processors/citation_processor.py       # Citation handling
src/models/llm_agent.py                    # AI Agent3 (LangChain agent)
tests/test_stage_04.py                     # Tests
```

**Implementation Checklist**:
- [ ] Check `citations_disabled?` flag in job_config
- [ ] Implement CitationSanitizer (remove [n] markers)
- [ ] Implement URL extraction from sources
- [ ] Implement split/array logic
- [ ] Implement AI Agent3 (LangChain agent with serperTool + validTool)
  - [ ] serperTool: Search for alternative URLs
  - [ ] validTool: HTTP HEAD validation
  - [ ] maxIterations: 20
  - [ ] Fallback: Company URL
- [ ] Implement citation formatting
- [ ] Implement HTML conversion
- [ ] Write comprehensive tests
- [ ] Test with invalid URLs
- [ ] Test with missing sources

**Blockers**:
- [ ] None (depends on Stage 3)

---

### Stage 5: Internal Links

**Status**: [ ] Not Started | [ ] In Progress | [ ] Complete
**Architecture Lines**: 588-634
**v4.1 Mapping**: Phase 5, Steps 14-19
**Duration Estimate**: 4-6 hours
**Bottleneck**: URL validation (HTTP HEAD checks)

**Purpose**: Generate and validate internal "More Reading" links

**Inputs**:
- ExecutionContext.structured_data (headline, sections)

**Outputs**:
- ParallelResult.internal_links_html

**6 Sequential Sub-steps** (WITHIN parallel stage):
- [ ] Sub-step 1: create-more-section (Step 14) - Generate 10 internal links
  - Criteria: high authority (DA>40), topic-aligned, no competitors, min 1 Wikipedia link
- [ ] Sub-step 2: create-url-table1 (Step 15) - Parse JSON, extract URLs
- [ ] Sub-step 3: create-url-status-table1 (Step 16) - Validate each URL (HTTP HEAD)
- [ ] Sub-step 4: filter-on-200-status1 (Step 17) - Keep only HTTP 200
- [ ] Sub-step 5: merge-rows1 (Step 18) - Concatenate validated URLs
- [ ] Sub-step 6: create-more-section1 (Step 19) - Format as HTML section

**Code Files to Create**:
```
src/stages/stage_05_internal_links.py      # Main stage
src/processors/link_processor.py           # Link handling
tests/test_stage_05.py                     # Tests
```

**Implementation Checklist**:
- [ ] Implement link generation (LLM + criteria filter)
- [ ] Implement JSON parsing (handle code fences, HTML wrappers)
- [ ] Implement URL validation loop
- [ ] Implement HTTP status code filtering
- [ ] Implement link concatenation
- [ ] Implement HTML formatting
- [ ] Test with various URL formats
- [ ] Test error handling (invalid URLs)
- [ ] Write comprehensive tests

**Blockers**:
- [ ] None (depends on Stage 3)

---

### Stage 6: Table of Contents

**Status**: [ ] Not Started | [ ] In Progress | [ ] Complete
**Architecture Lines**: 638-661
**v4.1 Mapping**: Phase 6a, Steps 20-21
**Duration Estimate**: 1-2 hours
**Speed**: Fast (2 sub-steps)

**Purpose**: Generate short labels for table of contents navigation

**Inputs**:
- ExecutionContext.structured_data.section_01_title...section_09_title

**Outputs**:
- ParallelResult.toc_dict (toc_01...toc_09)

**2 Sequential Sub-steps**:
- [ ] Sub-step 1: add-short-headers (Step 20) - Generate 1-2 word labels
- [ ] Sub-step 2: reformat_short_headers (Step 21) - Further formatting (if needed)

**Code Files to Create**:
```
src/stages/stage_06_toc.py                 # Main stage
src/prompts/toc_headers.py                 # ToC prompt (framework in Part 5b)
tests/test_stage_06.py                     # Tests
```

**Implementation Checklist**:
- [ ] Create or load ToC prompt from Part 5b
- [ ] Implement label generation
- [ ] Implement reformatting logic
- [ ] Test label quality (1-2 words, meaningful)
- [ ] Test with different section titles
- [ ] Write tests

**Blockers**:
- [ ] None (depends on Stage 3)

---

### Stage 7: Metadata

**Status**: [ ] Not Started | [ ] In Progress | [ ] Complete
**Architecture Lines**: 664-688
**v4.1 Mapping**: Phase 6b, Steps 22-23
**Duration Estimate**: 0.5-1 hour
**Speed**: Very fast (2 simple calculations)

**Purpose**: Generate reading time and publication date

**Inputs**:
- ExecutionContext.structured_data (all content fields)

**Outputs**:
- ParallelResult.metadata (read_time, publication_date)

**2 Sub-steps**:
- [ ] Sub-step 1: add-readtime (Step 22) - Calculate reading time
  - Count total words across all sections
  - Divide by 200 words/minute
  - Min 1 minute, Max 30 minutes
- [ ] Sub-step 2: add_date (Step 23) - Generate random publication date
  - Random date within last 90 days
  - Format: DD.MM.YYYY

**Code Files to Create**:
```
src/stages/stage_07_metadata.py            # Main stage (simple calculations)
tests/test_stage_07.py                     # Tests
```

**Implementation Checklist**:
- [ ] Implement word count function
- [ ] Implement reading time calculation
- [ ] Implement date generation (random within 90 days)
- [ ] Write tests for both calculations

**Blockers**:
- [ ] None (depends on Stage 3)

---

### Stage 8: FAQ/PAA Enhancement

**Status**: [ ] Not Started | [ ] In Progress | [ ] Complete
**Architecture Lines**: 692-703
**v4.1 Mapping**: Phase 7, Step 24
**Duration Estimate**: 2-4 hours
**Speed**: Medium (1 complex step)

**Purpose**: Validate and enhance FAQ/PAA items

**Inputs**:
- ExecutionContext.structured_data.faq_*, paa_*

**Outputs**:
- ParallelResult.faq_items (5 items)
- ParallelResult.paa_items (3 items)

**Operations**:
- [ ] Validate extracted FAQ/PAA items
- [ ] Generate additional items if needed (target: 5 FAQ, 3 PAA)
- [ ] Remove duplicates
- [ ] Format for AEO optimization

**Code Files to Create**:
```
src/stages/stage_08_faq_paa.py             # Main stage
src/prompts/faq_generator.py               # FAQ/PAA prompt (framework in Part 5b)
tests/test_stage_08.py                     # Tests
```

**Implementation Checklist**:
- [ ] Load FAQ/PAA prompt from Part 5b
- [ ] Implement validation logic
- [ ] Implement generation for missing items
- [ ] Implement deduplication
- [ ] Test with 0-6 existing FAQs
- [ ] Test with 0-4 existing PAAs
- [ ] Write comprehensive tests

**Blockers**:
- [ ] None (depends on Stage 3)

---

### Stage 9: Image Generation

**Status**: [ ] Not Started | [ ] In Progress | [ ] Complete
**Architecture Lines**: 706-751
**v4.1 Mapping**: Phase 8, Steps 25-28
**Duration Estimate**: 3-5 hours
**Blocker**: Image service decision (Decision 3 above)

**Purpose**: Generate article header image

**Inputs**:
- ExecutionContext.structured_data.headline
- company_data

**Outputs**:
- ParallelResult.image_url
- ParallelResult.image_alt_text

**Conditional Logic** (Part 4c):
- `image_empty?`: If image already exists, skip generation

**3 Sub-steps** (WHEN NOT SKIPPED):
- [ ] Sub-step 1: get-insights (Step 25) - Generate image prompt
- [ ] Sub-step 2: execute_image_generation (Step 27) - Call image API
- [ ] Sub-step 3: store_image_in_blog (Step 28) - Save image URL

**Code Files to Create**:
```
src/stages/stage_09_image.py               # Main stage
src/models/image_generator.py              # Image API wrapper
src/prompts/image_prompt.py                # Image prompt (framework in Part 5b)
tests/test_stage_09.py                     # Tests
```

**Implementation Checklist**:
- [ ] **RESOLVE**: Decision 3 (image service choice)
- [ ] Implement `image_empty?` conditional check
- [ ] Load image prompt from Part 5b
- [ ] Implement image prompt generation
- [ ] Implement image API call (based on chosen service)
- [ ] Implement retry logic (max 2 retries, 60s timeout)
- [ ] Implement image URL storage
- [ ] Implement alt text generation
- [ ] Test with mocked image API
- [ ] Test with real image API (if available)
- [ ] Write comprehensive tests

**Blockers**:
- [ ] **BLOCKING**: Image service decision required (Decision 3)

---

### Stage 10: Cleanup & Validation

**Status**: [ ] Not Started | [ ] In Progress | [ ] Complete
**Architecture Lines**: 756-841
**v4.1 Mapping**: Phase 9, Steps 29-33
**Duration Estimate**: 6-8 hours
**Critical**: Merge point and quality checks

**Purpose**: Merge parallel results, cleanup data, run quality checks

**Inputs**:
- ExecutionContext.structured_data
- All ParallelResults (from Stages 4-9)

**Outputs**:
- ExecutionContext.validated_article
- ExecutionContext.quality_report

**6 Sequential Sub-steps**:
- [ ] Sub-step 1: prepare_variable_names-and-clean (Step 29)
  - Map field names
  - Clean HTML (remove duplicates, h1→h2)
  - Combine sections 01-09 into content string
- [ ] Sub-step 2: output_sanitizer (Step 30)
  - Regex cleanup (markdown bold, brackets, href)
  - Recursive cleaning of nested objects
- [ ] Sub-step 3: normalise-output2 (Step 31)
  - Normalize formatting
  - Ensure UTF-8 encoding
  - Validate field types
- [ ] Sub-step 4: Merge (Step 32) - CRITICAL
  - Combine all parallel results
  - Merge citations, links, ToC, metadata, FAQ, PAA, image
- [ ] Sub-step 4b: CitationSanitizer2 (Step 32b) ⚠️ v4.1 MAPPED NODE
  - Final citation cleanup pass
  - Remove remaining citation artifacts
- [ ] Sub-step 5: merge-outputs (Step 33)
  - Flatten to single ValidatedArticle
  - Extract/validate key_takeaways
  - Handle optional fields
- [ ] Quality Checks (after flattening):
  - Critical checks: Required fields, duplicates, competitors, HTML validity
  - Suggestion checks: Paragraph length, keyword coverage, reading time
  - Generate metrics: AEO score, readability, keyword coverage

**Code Files to Create**:
```
src/stages/stage_10_cleanup.py             # Main stage
src/processors/formatter.py                # HTML formatting + cleanup
src/processors/validator.py                # Quality checks
tests/test_stage_10.py                     # Tests
```

**Implementation Checklist**:
- [ ] Implement field name mapping
- [ ] Implement HTML cleaning
- [ ] Implement section concatenation
- [ ] Implement output sanitizer (regex-based)
- [ ] Implement normalization
- [ ] Implement merge logic (combine 7 parallel inputs)
- [ ] **CRITICAL**: Implement CitationSanitizer2 (final cleanup)
- [ ] Implement merge-outputs (flattening)
- [ ] Implement key_takeaways extraction/validation
- [ ] Implement critical quality checks
- [ ] Implement suggestion checks (warnings only)
- [ ] Implement metrics calculation
- [ ] Write comprehensive tests
- [ ] Test with various edge cases

**Blockers**:
- [ ] None (all previous stages complete)

**Next Stage After Complete**: Stage 11 (HTML Generation & Storage)

---

### Stage 11: HTML Generation & Storage

**Status**: [ ] Not Started | [ ] In Progress | [ ] Complete
**Architecture Lines**: 844-863
**v4.1 Mapping**: Phase 10, Steps 34-38
**Duration Estimate**: 4-6 hours
**Final Stage**: No dependencies after this

**Purpose**: Generate final HTML document and store in Supabase

**Inputs**:
- ExecutionContext.validated_article
- ExecutionContext.quality_report

**Outputs**:
- ArticleResult (complete final output)
- Supabase storage confirmation

**5 Sub-steps**:
- [ ] Step 34: HTML1 - Generate HTML document
  - Template with meta tags, styling
  - Include all sections, FAQs, citations, metadata
  - Responsive design
- [ ] Step 35: Edit Fields - Final adjustments
- [ ] Step 36: store_article - Supabase upsert
  - Match on job_id
  - Auto-map all fields
  - Exclude: id, row_index, primary_keyword
- [ ] Step 37: Google Drive - Optional backup
  - Upload if enabled in config
- [ ] Step 38: format_download_link - Create download URL

**Code Files to Create**:
```
src/stages/stage_11_storage.py             # Main stage
src/templates/article_template.html        # HTML template
tests/test_stage_11.py                     # Tests
```

**Implementation Checklist**:
- [ ] Create HTML template with proper structure
- [ ] Implement template variable injection
- [ ] Implement Supabase upsert logic
- [ ] Implement field mapping
- [ ] Implement optional Google Drive upload
- [ ] Implement download link generation
- [ ] Write comprehensive tests
- [ ] Test with real Supabase
- [ ] Test HTML output quality

**Blockers**:
- [ ] None (all previous stages complete)

---

## Part 3: Decision Log

**Track all implementation decisions here for future reference**

| Decision | Status | Choice | Date | Notes |
|----------|--------|--------|------|-------|
| Response Format | [ ] Pending | [ ] text/plain / [ ] application/json | _____ | See Part 1, Decision 1 |
| Tools Compatibility | [ ] Pending | [ ] Compatible / [ ] Incompatible | _____ | See Part 1, Decision 2 |
| Image Service | [ ] Pending | [ ] Replicate / [ ] DALL-E / [ ] Other | _____ | See Part 1, Decision 3 |
| LangChain Version | [ ] TBD | | | |
| Prompt Refinements | [ ] In Progress | | | |
| Performance Target | [ ] TBD | [Minutes/sec] | | |

---

## Part 4: Progress Tracking

**Update this as you complete each stage**

### Overall Progress
- Stages Complete: 0/12 (0%)
- Critical Blockers: 3 (Decisions 1-3)
- Current Focus: Pre-implementation setup

### Stage Completion Status

| Stage | Name | Status | Hours | Notes |
|-------|------|--------|-------|-------|
| 0 | Data Fetch | [ ] | _____ | |
| 1 | Prompt Build | [ ] | _____ | |
| 2 | Gemini Call | [ ] BLOCKED | _____ | **Waiting**: Decision 1 |
| 3 | Extraction | [ ] | _____ | |
| 4 | Citations | [ ] | _____ | |
| 5 | Internal Links | [ ] | _____ | |
| 6 | ToC | [ ] | _____ | |
| 7 | Metadata | [ ] | _____ | |
| 8 | FAQ/PAA | [ ] | _____ | |
| 9 | Image | [ ] BLOCKED | _____ | **Waiting**: Decision 3 |
| 10 | Cleanup | [ ] | _____ | Includes CitationSanitizer2 |
| 11 | Storage | [ ] | _____ | |

### Test Coverage

| Stage | Unit Tests | Integration Tests | Status |
|-------|------------|-------------------|--------|
| 0 | [ ] | [ ] | |
| 1 | [ ] | [ ] | |
| 2 | [ ] | [ ] | **Blocked** |
| 3 | [ ] | [ ] | |
| 4 | [ ] | [ ] | |
| 5 | [ ] | [ ] | |
| 6 | [ ] | [ ] | |
| 7 | [ ] | [ ] | |
| 8 | [ ] | [ ] | |
| 9 | [ ] | [ ] | **Blocked** |
| 10 | [ ] | [ ] | |
| 11 | [ ] | [ ] | |

---

## Part 5: Common Pitfalls & Gotchas

### Citation Processing (Stage 4)
- ❌ Don't forget CitationSanitizer2 in Stage 10!
- ❌ AI Agent3 is complex - implement fallback to company URL
- ✅ Test with invalid/404 URLs
- ✅ Log each citation validation step

### Parallel Execution (Stages 4-9)
- ❌ Don't assume stages are "atomic" - each has internal dependencies
- ❌ Don't forget image_empty? conditional in Stage 9
- ✅ Test with asyncio.gather() timing
- ✅ Log stage completion times

### Key Takeaways (Stage 3 + Stage 10)
- ❌ Key takeaways MUST be separate from content (enforced in prompt + cleanup)
- ❌ Don't embed them in section content
- ✅ Extract if found embedded (KeyTakeawaysInSection? check)
- ✅ Validate exactly 3 key takeaways present

### Response Parsing (Stage 2)
- ❌ Don't assume JSON response - depends on format decision!
- ❌ If text/plain: implement robust JSON extraction
- ✅ Test with edge cases (nested JSON, text around JSON)
- ✅ Implement proper error handling

### Merge Point (Stage 10)
- ❌ Don't forget CitationSanitizer2 after merge!
- ❌ Don't forget to handle optional fields (image, citations if disabled)
- ✅ Test merge with all combinations (citations on/off, image on/off)
- ✅ Validate data integrity after merge

---

## Part 6: Architecture Reference Quick Links

**For detailed information, refer to**:
- `PYTHON_WORKFLOW_ARCHITECTURE.md` (2,106 lines - comprehensive)
  - Part 4k: Response Format Decision
  - Part 4e: Tools Configuration Examples
  - Part 5b: Baseline Prompt Templates
  - Part 4c: Conditional Logic & Retry Strategies

- `QUICK_REFERENCE_CARD.md` (1 page - ultra-concise)
  - 12-stage overview
  - Data flow diagram
  - Critical constraints
  - Pitfalls checklist

---

**Last Updated**: 2025-11-19
**Next Review**: After Stage 0 completion
**Questions?**: Refer to architecture doc or quick reference card
