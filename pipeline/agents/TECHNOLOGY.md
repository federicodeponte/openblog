# Asset Finder Agent - Technology Stack

## How Assets Are Found

The Asset Finder Agent uses a **multi-stage AI-powered search process**:

### Stage 1: Query Building
**Technology**: Simple string concatenation
- Combines article topic, section title, image types
- Adds industry context from company data
- Creates optimized search query

**Example**:
```
Input: "AI cybersecurity" + "Benefits section" + "photo illustration" + "Technology"
Output: "AI cybersecurity Benefits section photo illustration infographic diagram free stock images Technology"
```

---

### Stage 2: Internet Search (Gemini + Google Search)

**Technology Stack**:
- **Gemini AI** (`google-genai` SDK)
- **Google Search Tool** (built into Gemini)
- **Automatic Function Calling (AFC)**

**How It Works**:

1. **Gemini AI Model**: Uses `gemini-2.0-flash-exp` or similar
   - Fast, efficient model for search tasks
   - Supports automatic tool calling

2. **Google Search Tool**: Automatically enabled when `enable_tools=True`
   ```
   tools = [
       GoogleSearch()  # Built into Gemini SDK
   ]
   ```

3. **Process Flow**:
   ```
   User Prompt → Gemini AI
                    ↓
              [Gemini decides to search]
                    ↓
              Google Search Tool
                    ↓
              Searches: "AI cybersecurity free stock images"
                    ↓
              Returns: Search results with URLs
                    ↓
              Gemini extracts image URLs
                    ↓
              Returns JSON array of assets
   ```

4. **What Gemini Searches For**:
   - Free stock photo sites (Unsplash, Pexels, Pixabay)
   - Professional, high-quality images
   - Relevant to article topic
   - Different image types (photo, illustration, infographic, diagram)

5. **Response Format**: JSON array
   ```json
   [
     {
       "url": "https://unsplash.com/photos/...",
       "title": "Cybersecurity concept",
       "description": "Modern security operations center",
       "source": "Unsplash",
       "image_type": "photo",
       "license_info": "Free to use",
       "width": 1920,
       "height": 1080
     }
   ]
   ```

**Key Features**:
- ✅ **Automatic**: No manual search API calls needed
- ✅ **Intelligent**: Gemini understands context and finds relevant images
- ✅ **Free**: Uses Google Search (no additional API costs)
- ✅ **Structured**: Returns JSON with metadata

---

### Stage 3: Image Recreation (Optional)

**Technology**: **Gemini Imagen 4.0**

**When Enabled**: `recreate_in_design_system=True`

**How It Works**:

1. **Design System Extraction**:
   - Extracts colors from company industry
   - Determines style from brand_tone
   - Maps to design system parameters

2. **Prompt Building**:
   ```
   Original concept: "Cybersecurity operations center"
   Design System:
   - Colors: [#0066CC, #00CCFF, #333333] (Technology palette)
   - Style: "modern minimalist"
   - Industry: "Technology"
   ```

3. **Imagen Generation**:
   - Model: `imagen-4.0-generate-001`
   - Takes design system prompt
   - Generates new image matching brand identity
   - Output: 1200x630px (blog header size)

4. **Output**: New image URL (Google Drive or local)

**Example**:
```
Original: Generic cybersecurity photo from Unsplash
Recreated: Same concept but with company brand colors and style
```

---

## Technology Comparison

| Feature | Technology | Cost | Speed |
|---------|-----------|------|-------|
| **Search** | Gemini + Google Search | Free (included) | 10-30s |
| **Recreation** | Gemini Imagen 4.0 | Paid (per image) | 5-10s per image |
| **Storage** | Google Drive (optional) | Free | Instant |

---

## Code Flow

```python
# 1. Initialize
agent = AssetFinderAgent()
# Uses: GeminiClient, GoogleImagenClient

# 2. Find Assets
request = AssetFinderRequest(...)
response = await agent.find_assets(request)

# Internally:
#   → _build_search_query()          # Stage 1
#   → _search_for_assets()           # Stage 2
#     → gemini_client.generate_content(enable_tools=True)
#       → Gemini calls Google Search automatically
#       → Returns JSON with assets
#   → _recreate_assets() (optional)   # Stage 3
#     → imagen_client.generate_image()
#       → Imagen 4.0 generates new image
```

---

## Why This Approach?

### ✅ Advantages:
1. **No Manual Search APIs**: Gemini handles search automatically
2. **Context-Aware**: Understands article topic and finds relevant images
3. **Free Stock Focus**: Prioritizes free-to-use images
4. **Design System Integration**: Can recreate in brand colors/style
5. **Structured Output**: Returns JSON with metadata

### ⚠️ Limitations:
1. **API Dependency**: Requires Gemini API key
2. **Rate Limits**: Google Search has rate limits
3. **Quality Varies**: Search results depend on web content
4. **Recreation Cost**: Imagen generation costs per image

---

## Alternative Approaches (Not Used)

| Approach | Why Not Used |
|----------|-------------|
| **Direct Unsplash API** | Requires API key, less flexible |
| **Scraping** | Legal/ethical concerns, fragile |
| **Manual Search** | Not automated, time-consuming |
| **Image Embeddings** | Complex, requires vector DB |

---

## Future Enhancements

1. **Caching**: Cache search results to reduce API calls
2. **Multiple Sources**: Add more stock photo sites
3. **Image Analysis**: Use vision models to verify image quality
4. **License Verification**: Automatically check licenses
5. **Batch Processing**: Process multiple articles at once

