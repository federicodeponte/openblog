# Quick Reference Card - Python Blog Writing System

**Status**: Pre-Implementation | **Architecture Doc**: `PYTHON_WORKFLOW_ARCHITECTURE.md` (2,106 lines)
**Roadmap**: `IMPLEMENTATION_ROADMAP.md` (detailed stage-by-stage guide)

---

## System Overview

**Goal**: Implement Python version of v4.1 n8n blog writing workflow (12 stages, 38 steps)

**Data Flow**:
```
Job ID
  ↓
[Stage 0] Data Fetch → job_config
  ↓
[Stage 1] Prompt Build → prompt
  ↓
[Stage 2] Gemini Call → raw_article
  ↓
[Stage 3] Extraction → structured_data
  ↓
[Stages 4-9 PARALLEL] ─────────────────┐
  Stage 4: Citations → citations_html   │
  Stage 5: Links → links_html           │
  Stage 6: ToC → toc_dict               │
  Stage 7: Metadata → read_time+date    │
  Stage 8: FAQ/PAA → faq_items+paa_items
  Stage 9: Image → image_url+alt_text   │
  ────────────────────────────────────┘
  ↓
[Stage 10] Merge & Cleanup + Quality Checks → validated_article + quality_report
  ↓
[Stage 11] HTML & Storage → final_html + Supabase upsert
  ↓
ArticleResult ✅
```

---

## 3 Critical Decisions (MUST RESOLVE FIRST)

### Decision 1: Response Format ⚠️
**Question**: `text/plain` (matches v4.1) or `application/json` (current code)?

| Aspect | text/plain | application/json |
|--------|-----------|------------------|
| **v4.1 Match** | ✅ Yes | ❌ No |
| **Tools Work** | ✅ Yes | ❓ Unknown |
| **Parsing** | ❌ Regex needed | ✅ Direct |
| **Complexity** | ❌ Higher | ✅ Lower |

**Action**: Run tests in Part 4k, decide before Stage 2
**Code**: Part 4e (both options)

### Decision 2: Tools Compatibility
**Question**: Do tools (googleSearch, urlContext) work with your chosen format?

**Test Required**: Part 4k provides testing scripts
**Decision**: After Decision 1 testing

### Decision 3: Image Service
**Options**: Replicate | DALL-E | Midjourney | Other

**Decision**: Before Stage 9
**Setup**: Credentials in environment (Part 4e)

---

## Environment Variables Checklist

```bash
# Required
GOOGLE_GEMINI_API_KEY="..."
GOOGLE_PROJECT_ID="..."
SUPABASE_URL="..."
SUPABASE_API_KEY="..."
SUPABASE_SERVICE_ROLE_KEY="..."
GOOGLE_SEARCH_API_KEY="..."  # For AI Agent3

# Choose one (Decision 3)
REPLICATE_API_TOKEN="..."    # OR
OPENAI_API_KEY="..."         # OR
# Other image service

# Optional
GOOGLE_DRIVE_ENABLED="false"
```

---

## 12-Stage Implementation Order

| Stage | Name | Duration | Complexity | Dependency | Blocker |
|-------|------|----------|------------|-----------|---------|
| 0 | Data Fetch | 2-4h | Low | - | None |
| 1 | Prompt Build | 3-6h | Medium | S0 | None |
| 2 | Gemini Call | 4-8h | Medium | S1 | ⚠️ Decision 1 |
| 3 | Extraction | 4-6h | Medium | S2 | None |
| 4 | Citations | 4-6h | High | S3 | None |
| 5 | Links | 4-6h | High | S3 | None |
| 6 | ToC | 1-2h | Low | S3 | None |
| 7 | Metadata | 0.5-1h | Very Low | S3 | None |
| 8 | FAQ/PAA | 2-4h | Medium | S3 | None |
| 9 | Image | 3-5h | Medium | S3 | ⚠️ Decision 3 |
| **4-9** | **All Parallel** | **8-12h total** | - | S3 | None |
| 10 | Cleanup | 6-8h | High | S4-9 | None |
| 11 | Storage | 4-6h | Medium | S10 | None |

---

## AEO Constraints (Non-Negotiable)

✅ **Paragraph max**: 25-30 words (enforced in prompt + Stage 10 checks)
✅ **Internal links**: 1 per H2 section (Stage 5)
✅ **FAQ items**: Minimum 5 (Stage 8)
✅ **PAA items**: Minimum 3 (Stage 8)
✅ **Key takeaways**: 3 items, SEPARATE from content (Stage 3 + Stage 10)
✅ **Tone**: Coaching, not threatening (enforced in prompt)
✅ **Style**: McKinsey/BCG (action-oriented, data-driven - enforced in prompt)
✅ **Citations**: Format [1], [2] matching sources list (Stage 4)
✅ **No competitors**: Mentioned in Stage 10 quality checks

---

## Citation Processing (Special Attention!)

**3 sanitization nodes** (not 1):
1. **CitationSanitizer** (Stage 4, Step 8) - Remove [n] markers from content
2. **CitationSanitizer1** (Stage 4, Step 8b) - Second pass, remove empty brackets
3. **CitationSanitizer2** (Stage 10, Step 32b) ⚠️ OFTEN MISSED - Final cleanup after merge

**Don't forget CitationSanitizer2 in Stage 10!**

---

## External Services Required

| Service | Stage | Purpose | Setup | Complexity |
|---------|-------|---------|-------|-----------|
| Gemini 3.0 Pro API | 2, 3, 5, 6, 8 | Content generation, extraction, agents | API key + Google Project | Medium |
| Supabase | 0, 11 | Fetch job config, store article | URL + API key + service role | Medium |
| Google Search | 4, 5 | Web search (AI Agent3, link validation) | Serper.dev or Google Search API | Medium |
| Image API | 9 | Generate article images | Replicate/DALL-E/other | Medium |
| Google Drive | 11 | Optional backup | OAuth2 credentials (optional) | Medium |

---

## Critical Gotchas ⚠️

| Issue | Impact | Fix |
|-------|--------|-----|
| Forget CitationSanitizer2 | Leftover [1] markers in final HTML | Add to Stage 10 Step 32b |
| Wrong response format | Tools won't work (or parsing breaks) | Decide & test Decision 1 |
| Key takeaways in content | Fails quality check | Enforce in prompt + extract in Stage 10 |
| Parallel "atomicity" | Timeouts, missed dependencies | Each stage has internal sub-steps |
| image_empty? not checked | Overwrite existing images | Add conditional in Stage 9 |
| Merge missing optional fields | Crash when citations/image disabled | Handle gracefully in Stage 10 |
| Credentials missing | Authentication fails | Fill all env vars before starting |

---

## Quick File Structure

```
src/
├── stages/
│   ├── stage_00_data_fetch.py
│   ├── stage_01_prompt_build.py
│   ├── stage_02_gemini_call.py
│   ├── stage_03_extraction.py
│   ├── stage_04_citations.py
│   ├── stage_05_internal_links.py
│   ├── stage_06_toc.py
│   ├── stage_07_metadata.py
│   ├── stage_08_faq_paa.py
│   ├── stage_09_image.py
│   ├── stage_10_cleanup.py
│   └── stage_11_storage.py
├── prompts/
│   ├── main_article.py          ← Copy from Part 5b
│   ├── citations_generator.py
│   ├── toc_headers.py
│   ├── faq_generator.py
│   └── image_prompt.py
├── processors/
│   ├── extractor.py
│   ├── formatter.py
│   ├── citation_processor.py
│   ├── link_processor.py
│   └── validator.py
├── models/
│   ├── gemini_client.py         ← Code in Part 4e
│   ├── supabase_client.py
│   ├── llm_agent.py             ← For AI Agent3
│   └── image_generator.py
├── core/
│   ├── workflow_engine.py
│   └── pipeline.py
├── schemas/
│   ├── input.py
│   ├── output.py
│   └── internal.py
└── config.py
tests/
├── test_stage_00.py...test_stage_11.py
├── test_integration.py
└── test_prompts.py
```

---

## Implementation Checklist

**Before Starting**:
- [ ] Read Architecture Doc (overview only)
- [ ] Resolve Decision 1 (response format)
- [ ] Resolve Decision 2 (tools compatibility)
- [ ] Resolve Decision 3 (image service)
- [ ] Set up all environment variables
- [ ] Copy baseline prompts from Part 5b

**Stage-by-Stage**:
- [ ] For each stage: Read IMPLEMENTATION_ROADMAP.md section
- [ ] Implement sub-steps
- [ ] Write unit + integration tests
- [ ] Mark complete in roadmap
- [ ] Move to next stage

**After All Stages**:
- [ ] Run full E2E test
- [ ] Verify quality checks pass
- [ ] Test with real Supabase (if not done)
- [ ] Benchmark performance
- [ ] Document any refinements

---

## Quick Command Reference

```bash
# Run single stage test
python -m pytest tests/test_stage_XX.py

# Run all tests
python -m pytest tests/

# Run full workflow
python scripts/run_single.py --job-id 12345 --keyword "test"

# Check environment
echo $GOOGLE_GEMINI_API_KEY $SUPABASE_URL ...
```

---

## Helpful Links

- **Architecture Document**: `PYTHON_WORKFLOW_ARCHITECTURE.md` (2,106 lines - comprehensive)
  - Part 4k: Response format decision
  - Part 4e: Tools configuration code
  - Part 5b: Baseline prompts
  - Part 4c: Retry strategies & conditionals

- **Implementation Roadmap**: `IMPLEMENTATION_ROADMAP.md` (detailed stage-by-stage)
  - Pre-implementation checklist
  - Stage-by-stage guides
  - Decision log
  - Progress tracking

- **v4.1 Original Workflow**: `JSON_4.1_WORKFLOW.md`
  - Source of truth for all node specifications
  - Prompts and configurations

---

**TL;DR**: Resolve 3 decisions → Implement stages 0-11 → Test → Deploy
**Current Status**: Decision-making phase
**Next**: Decide response format (Part 4k)

---

*Last Updated: 2025-11-19*
*For detailed guidance, see IMPLEMENTATION_ROADMAP.md*
