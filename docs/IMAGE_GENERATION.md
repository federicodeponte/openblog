# Image Generation Strategy

## Current Setup (Dec 2025)

OpenBlog has **two image generation pipelines**:

### 1. **Gemini Image Creator** (DEFAULT) ✅
- **File:** `service/image_generator.py`
- **API:** `POST /generate-image`
- **Technology:** Google GenAI SDK (`gemini-2.5-flash-image`)
- **Output:** AI-generated images
- **Use case:** Blog hero images, topic visualizations
- **Status:** **Production default**

### 2. **OpenFigma Graphics** (Optional)
- **File:** `service/graphics_generator.py`
- **API:** 
  - `POST /generate-graphics` (legacy templates)
  - `POST /generate-graphics-config` (JSON config)
- **Technology:** HTML/CSS → Playwright → PNG
- **Library:** `openfigma` (external package)
- **Output:** Component-based graphics (charts, stats, processes)
- **Use case:** Data visualizations, infographics, stats dashboards
- **Status:** Available but not default

## Why Gemini is Default

1. **AI-powered** - Creates unique, contextual images
2. **Fast** - Direct API call, no HTML rendering
3. **Creative** - Better for blog hero images
4. **Simpler** - Single API call

## When to Use OpenFigma

- Data visualizations (charts, graphs)
- Stats dashboards
- Process flows
- Before/After comparisons
- Infographics
- Case study graphics

## Configuration

Default image generator is set in blog generation pipeline.
To use OpenFigma graphics, explicitly call `/generate-graphics-config` endpoint.

## Future

Both pipelines coexist. Gemini for creative content, OpenFigma for structured data viz.

