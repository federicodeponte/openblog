# Finding Real Statistics Charts - Approach

## User Requirement

**Goal**: Find REAL statistics charts with actual data (like bar charts showing citation rates), NOT AI-generated generic images.

## Current Problem

- Current approach finds generic stock photos
- AI-generated images are too generic
- Need actual charts with real statistics/data

## Solution: Enhanced Asset Finder + Serper Dev

### Approach 1: Enhanced Asset Finder (Page Scraping)

**Process**:
1. Search for research pages with statistics
2. Fetch and parse HTML pages
3. Extract chart images from pages
4. Identify charts by alt text/content

**Pros**:
- Finds charts from actual research pages
- Can extract data from charts
- Gets context from surrounding content

**Cons**:
- Some sites block scraping (403 errors)
- Slower (requires page fetching)
- Some URLs may be outdated (404)

### Approach 2: Serper Dev Google Images (Direct Search)

**Process**:
1. Search Google Images for "statistics chart" + topic
2. Get direct image URLs from SERP
3. Download chart images
4. Show in Preview

**Pros**:
- Faster (direct image URLs)
- Finds charts from multiple sources
- No page parsing needed

**Cons**:
- Some sites block direct image access (403)
- Less context about the chart
- Can't extract data easily

## Recommended Hybrid Approach

### Step 1: Use Serper Dev for Initial Search
- Search Google Images for statistics charts
- Get direct image URLs
- Filter for accessible images

### Step 2: Use Enhanced Asset Finder for Deep Dive
- When need to extract data from charts
- When need context from research pages
- When Serper Dev results are blocked

### Step 3: Extract Data from Charts
- Use Gemini Vision to analyze chart images
- Extract data points, labels, values
- Structure data for regeneration

### Step 4: Regenerate in Design System
- Use GraphicsGenerator to recreate charts
- Apply company design system
- Use extracted data points

## Implementation

```python
# 1. Search for statistics charts
charts = await serper_finder.search_images(
    query="content citation rates statistics bar chart",
    size="large"
)

# 2. Download accessible charts
for chart in charts:
    if is_accessible(chart.url):
        download_chart(chart.url)

# 3. Extract data (optional)
for chart_image in downloaded_charts:
    data = await extract_chart_data_with_vision(chart_image)
    
# 4. Regenerate in design system (optional)
if data:
    new_chart = graphics_generator.create_chart(data, design_system)
```

## Key Differences

| Feature | Generic Images | Real Statistics Charts |
|---------|---------------|----------------------|
| **Source** | Stock photos | Research pages, reports |
| **Data** | None | Actual statistics/data |
| **Type** | Generic visuals | Bar charts, line charts |
| **Use Case** | Decorative | Data-driven content |
| **Regeneration** | Full AI generation | Extract data + regenerate |

## Next Steps

1. ✅ Use Serper Dev to find statistics charts
2. ✅ Download and show in Preview
3. ⏳ Add Gemini Vision to extract chart data
4. ⏳ Regenerate charts in design system
5. ⏳ Integrate into asset finder workflow

