# Asset Finding Approach - Evaluation

## Current State

### ✅ What's Working Well

1. **Gemini + Google Search (`images:` prefix)**
   - Finds relevant stock photos
   - Free (included with Gemini)
   - Good relevance
   - Fast enough (~30-60s)

2. **Gemini Imagen Recreation**
   - Works perfectly
   - Applies design system
   - Creates unique images

### ⚠️ Concerns & Issues

1. **Too Similar Images**
   - Problem: Finding 5 images from same search might be too similar
   - Current: No diversity checks
   - Need: Deduplication, diversity scoring, different search angles

2. **Charts Are Really Nice**
   - Problem: Current approach finds photos, not charts
   - We had: Enhanced Asset Finder for charts/tables
   - Need: Bring back chart finding capability

3. **Do We Need Crawling?**
   - Current: Gemini finds images directly
   - Question: Is crawling necessary?
   - Answer: **Probably not** - Gemini is enough for most cases

4. **Serper Dev Instead of DataForSEO**
   - User preference: Use Serper Dev API
   - API key provided: `113e7b9aec3009fa826684d4dd6cac20c01dfbda`
   - Need: Integrate Serper Dev for Google Images

## Recommendations

### 1. Keep Gemini as Primary ✅
- **Why**: Works well, free, good results
- **When**: Default for all image finding
- **Enhancement**: Add diversity checks

### 2. Add Diversity/Deduplication ✅
- **How**: 
  - Use different search angles per image
  - Check for similar URLs/domains
  - Ensure variety in image types
  - Spread across different sources

### 3. Bring Back Chart Finding ✅
- **How**: 
  - Use Enhanced Asset Finder for charts
  - Or add chart-specific search queries
  - Focus on infographics, data visualizations

### 4. Add Serper Dev as Option ✅
- **Why**: User preference, simpler than DataForSEO
- **When**: Alternative to Gemini or fallback
- **Cost**: Check Serper Dev pricing

### 5. Skip Crawling ✅
- **Why**: Gemini finds images directly
- **When**: Not needed for most cases
- **Exception**: Only if we need to extract data from charts

## Proposed Solution

### Hybrid Approach:

1. **Primary: Gemini + Diversity**
   - Find images with diversity checks
   - Different search angles per image
   - Mix of photo types and sources

2. **Charts: Enhanced Search**
   - Specific queries for charts/infographics
   - Use Enhanced Asset Finder when needed
   - Focus on data visualizations

3. **Fallback: Serper Dev**
   - When Gemini quota exhausted
   - When need more control
   - Simpler than DataForSEO

4. **Recreation: Always Available**
   - Gemini Imagen for unique images
   - Prevents similarity issues
   - Applies design system

## Implementation Plan

1. ✅ Add diversity checks to Gemini search
2. ✅ Integrate Serper Dev API
3. ✅ Bring back chart finding
4. ✅ Skip crawling (not needed)
5. ✅ Test with real examples

