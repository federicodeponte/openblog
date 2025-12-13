# Asset Finder Agent - Stage-by-Stage Output

## Technology Overview

**How Assets Are Found**: 
- **Gemini AI** with **Google Search Tool** (automatic web search)
- No manual search APIs needed
- Gemini automatically searches and extracts image URLs

**Optional Recreation**:
- **Gemini Imagen 4.0** for recreating images in design system

---

## Stage-by-Stage Output

### STAGE 1: Building Search Query

**Technology**: Simple string concatenation

**Input**:
```python
article_topic = "AI cybersecurity automation"
section_title = "Benefits of AI-Powered Security"
image_types = ["photo", "illustration", "infographic", "diagram"]
industry = "Technology"
```

**Process**:
```
1. Combine: "AI cybersecurity automation"
2. Add section: "Benefits of AI-Powered Security"
3. Add types: "photo illustration infographic diagram free stock images"
4. Add industry: "Technology"
```

**Output**:
```
✅ Search Query: AI cybersecurity automation Benefits of AI-Powered Security photo illustration infographic diagram free stock images Technology
```

---

### STAGE 2: Searching Internet (Gemini + Google Search)

**Technology**: 
- Gemini AI (`gemini-2.0-flash-exp`)
- Google Search Tool (automatic)
- Automatic Function Calling (AFC)

**Process Flow**:
```
📡 Calling Gemini API with Google Search enabled...
   Model: gemini-2.0-flash-exp
   Tools: Google Search (automatic web search)

⏳ Waiting for Gemini response (this may take 10-30 seconds)...
   [Gemini automatically calls Google Search]
   [Searches: "AI cybersecurity automation free stock images"]
   [Finds results from Unsplash, Pexels, Pixabay]
   [Extracts image URLs and metadata]

✅ Received response (1247 characters)
   Response preview: [
     {
       "url": "https://images.unsplash.com/photo-1563013544-824ae1b704d3",
       "title": "Cybersecurity Operations Center",
       ...
```

**What Happens Internally**:
1. Gemini receives prompt asking for images
2. Gemini **automatically** decides to use Google Search tool
3. Google Search searches the web
4. Gemini extracts image URLs from search results
5. Gemini formats results as JSON array
6. Returns structured data

**Output**:
```
STAGE 2.1: Parsing JSON Response
--------------------------------------------------------------------------------
Found 5 assets in response

Parsing asset 1/5:
  URL: https://images.unsplash.com/photo-1563013544-824ae1b704d3...
  Title: Cybersecurity Operations Center
  Source: Unsplash
  ✅ Valid image URL

Parsing asset 2/5:
  URL: https://images.pexels.com/photos/590016...
  Title: AI Security Dashboard
  Source: Pexels
  ✅ Valid image URL

...

✅ Successfully parsed 5 valid assets
```

**Final Assets Found**:
```json
[
  {
    "url": "https://images.unsplash.com/photo-1563013544-824ae1b704d3",
    "title": "Cybersecurity Operations Center",
    "description": "Modern security operations center with multiple monitors",
    "source": "Unsplash",
    "image_type": "photo",
    "license_info": "Free to use",
    "width": 1920,
    "height": 1080
  },
  {
    "url": "https://images.pexels.com/photos/590016",
    "title": "AI Security Dashboard",
    "description": "Digital security dashboard with AI analytics",
    "source": "Pexels",
    "image_type": "illustration",
    "license_info": "Free to use",
    "width": 1920,
    "height": 1080
  }
  // ... more assets
]
```

---

### STAGE 3: Recreating in Design System (Optional)

**Technology**: Gemini Imagen 4.0

**When Enabled**: `recreate_in_design_system=True`

**Process**:

**Step 3.1: Extract Design System**
```
Design System:
  Colors: ['#0066CC', '#00CCFF', '#333333']  (Technology palette)
  Style: modern minimalist
  Industry: Technology
```

**Step 3.2: Build Design Prompt**
```
Recreate this image concept in a professional design system:

Original concept: Modern security operations center with multiple monitors
Image type: photo

Design System Requirements:
- Color palette: #0066CC, #00CCFF, #333333
- Style: modern minimalist
- Industry context: Technology

Technical Requirements:
- Professional, high-quality image
- Suitable for blog article header (1200x630)
- Clean, modern aesthetic
- No text or watermarks
- Consistent with company brand identity
```

**Step 3.3: Generate Image**
```
Recreating asset 1/3: Cybersecurity Operations Center
  Design System:
    Colors: ['#0066CC', '#00CCFF', '#333333']
    Style: modern minimalist
    Industry: Technology
  Prompt length: 487 characters
  ⏳ Generating image with Imagen 4.0...
  ✅ Generated: https://drive.google.com/uc?id=abc123...
```

**Output**:
```json
[
  {
    "original_url": "https://images.unsplash.com/photo-1563013544-824ae1b704d3",
    "original_title": "Cybersecurity Operations Center",
    "recreated_url": "https://drive.google.com/uc?id=abc123",
    "design_prompt": "Recreate this image concept...",
    "success": true
  }
]
```

---

## Complete Example Output

### Test Run with API Key

```
================================================================================
ASSET FINDER AGENT - ISOLATED TESTING
================================================================================

================================================================================
TEST 1: Finding Assets from Internet
================================================================================

Technology Used:
  - Gemini AI with Google Search grounding
  - Automatic web search for free stock images
  - JSON parsing of search results

================================================================================
STAGE 1: Building Search Query
================================================================================
✅ Search Query: AI cybersecurity automation Benefits of AI-Powered Security photo illustration infographic diagram free stock images Technology

================================================================================
STAGE 2: Searching Internet (Gemini + Google Search)
================================================================================
Technology: Gemini AI with Google Search grounding
  - Gemini uses Google Search tool automatically
  - Searches free stock photo sites (Unsplash, Pexels, Pixabay)
  - Extracts image URLs and metadata
  - Returns JSON array of assets

📡 Calling Gemini API with Google Search enabled...
   Model: gemini-2.0-flash-exp
   Tools: Google Search (automatic web search)

⏳ Waiting for Gemini response (this may take 10-30 seconds)...
✅ Received response (1247 characters)
   Response preview: [
     {
       "url": "https://images.unsplash.com/photo-1563013544-824ae1b704d3",
       "title": "Cybersecurity Operations Center",
...

STAGE 2.1: Parsing JSON Response
--------------------------------------------------------------------------------
Found 5 assets in response

Parsing asset 1/5:
  URL: https://images.unsplash.com/photo-1563013544-824ae1b704d3...
  Title: Cybersecurity Operations Center
  Source: Unsplash
  ✅ Valid image URL

Parsing asset 2/5:
  URL: https://images.pexels.com/photos/590016...
  Title: AI Security Dashboard
  Source: Pexels
  ✅ Valid image URL

Parsing asset 3/5:
  URL: https://cdn.pixabay.com/photo/2020/05/24/09/15/ethereum-5213525...
  Title: Blockchain Security Concept
  Source: Pixabay
  ✅ Valid image URL

Parsing asset 4/5:
  URL: https://images.unsplash.com/photo-1550751827-4bd374c3f58b...
  Title: Network Security Visualization
  Source: Unsplash
  ✅ Valid image URL

Parsing asset 5/5:
  URL: https://images.pexels.com/photos/1181244...
  Title: Data Protection Shield
  Source: Pexels
  ✅ Valid image URL

✅ Successfully parsed 5 valid assets

================================================================================
STAGE 3: Skipped (recreate_in_design_system=False)
================================================================================

================================================================================
RESULTS
================================================================================
✅ Success: True
🔍 Search Query: AI cybersecurity automation Benefits of AI-Powered Security photo illustration infographic diagram free stock images Technology
📦 Found 5 assets

Asset 1:
  Title: Cybersecurity Operations Center
  URL: https://images.unsplash.com/photo-1563013544-824ae1b704d3
  Source: Unsplash
  Type: photo
  Description: Modern security operations center with multiple monitors showing security dashboards and network visualizations...
  License: Free to use

Asset 2:
  Title: AI Security Dashboard
  URL: https://images.pexels.com/photos/590016
  Source: Pexels
  Type: illustration
  Description: Digital security dashboard with AI analytics and threat detection visualizations...
  License: Free to use

...
```

---

## Key Points

1. **No Manual Search APIs**: Gemini handles everything automatically
2. **Google Search Integration**: Built into Gemini SDK, no extra setup
3. **Intelligent Search**: Gemini understands context and finds relevant images
4. **Free Stock Focus**: Prioritizes Unsplash, Pexels, Pixabay
5. **Structured Output**: Returns JSON with metadata (title, source, license, etc.)
6. **Design System**: Can recreate images in company brand colors/style

---

## Technology Stack Summary

| Stage | Technology | What It Does |
|-------|-----------|--------------|
| **1. Query Building** | String concatenation | Combines topic, section, types into search query |
| **2. Internet Search** | Gemini AI + Google Search Tool | Automatically searches web, extracts image URLs |
| **3. JSON Parsing** | Python JSON parser | Parses Gemini response into structured data |
| **4. Design System** | Logic extraction | Extracts colors/style from company data |
| **5. Image Recreation** | Gemini Imagen 4.0 | Generates new image in design system |

---

## Why This Approach?

✅ **Automatic**: No manual API calls or scraping  
✅ **Intelligent**: Gemini understands context  
✅ **Free**: Uses Google Search (no extra cost)  
✅ **Structured**: Returns JSON with metadata  
✅ **Flexible**: Can recreate in design system  

