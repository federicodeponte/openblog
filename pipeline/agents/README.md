# Asset Finder Agent

An agent that finds visual assets (images, graphics, illustrations) from the internet for blog articles. Optionally recreates images using Gemini Imagen in your company's design system.

## Features

- 🔍 **Internet Search**: Uses Gemini with Google Search to find relevant images/assets
- 🎨 **Design System Recreation**: Optionally recreates images using Gemini Imagen in your company's brand colors and style
- 🎯 **Context-Aware**: Finds assets based on article topic, headline, or specific sections
- ✅ **Standalone**: Can be tested and used independently of the full pipeline

## Quick Start

### Basic Usage: Find Assets Only

```python
from pipeline.agents.asset_finder import AssetFinderAgent, AssetFinderRequest

agent = AssetFinderAgent()

request = AssetFinderRequest(
    article_topic="AI cybersecurity automation",
    article_headline="Complete Guide to AI Cybersecurity Automation",
    max_results=5,
    recreate_in_design_system=False  # Just find, don't recreate
)

response = await agent.find_assets(request)

for asset in response.assets:
    print(f"{asset.title}: {asset.url}")
```

### Advanced Usage: Find + Recreate in Design System

```python
company_data = {
    "company_name": "TechSecure Inc",
    "industry": "Technology",
    "brand_tone": "modern professional",
    "project_folder_id": "your-google-drive-folder-id"  # Optional
}

request = AssetFinderRequest(
    article_topic="cloud security",
    article_headline="Cloud Security Best Practices",
    company_data=company_data,
    max_results=3,
    recreate_in_design_system=True  # Enable recreation
)

response = await agent.find_assets(request)

# Original assets
for asset in response.assets:
    print(f"Original: {asset.url}")

# Recreated assets
for recreated in response.recreated_assets:
    print(f"Recreated: {recreated['recreated_url']}")
```

## Testing

Run the isolated test script:

```bash
python test_asset_finder_agent.py
```

This will test:
1. Finding assets from the internet
2. Design system extraction from company data
3. Section-specific asset search
4. Finding + recreating assets (requires API key)

## Configuration

### Environment Variables

- `GOOGLE_API_KEY` or `GEMINI_API_KEY`: Required for Gemini search and Imagen recreation
- `GOOGLE_SERVICE_ACCOUNT`: Optional, for Google Drive uploads

### Design System

The agent automatically extracts design system information from company data:

- **Colors**: Based on industry (e.g., Technology → Blue tones)
- **Style**: Based on brand_tone (e.g., "modern professional" → Modern minimalist)
- **Industry Context**: Used to inform image style

## Integration with Pipeline

To integrate with the blog generation pipeline, you can:

1. **Use in Stage 9 (Image Generation)**: Add as an alternative to direct image generation
2. **Use as Pre-Stage**: Find assets before article generation to inform content
3. **Use as Post-Stage**: Find additional assets after article generation

Example integration:

```python
# In your stage or service
from pipeline.agents.asset_finder import AssetFinderAgent, AssetFinderRequest

# Find assets for a section
agent = AssetFinderAgent()
request = AssetFinderRequest(
    article_topic=context.structured_data.Headline,
    section_title=section_title,
    company_data=context.company_data,
    max_results=3,
    recreate_in_design_system=True
)

response = await agent.find_assets(request)
# Use response.assets or response.recreated_assets
```

## API Reference

### AssetFinderRequest

- `article_topic` (str, required): Main topic/keyword
- `article_headline` (str, optional): Article headline for context
- `section_title` (str, optional): Specific section title
- `company_data` (dict, optional): Company info for design system
- `max_results` (int, default=5): Maximum assets to find
- `recreate_in_design_system` (bool, default=False): Enable recreation
- `image_types` (list, default=["photo", "illustration", "infographic", "diagram"]): Types to search

### AssetFinderResponse

- `success` (bool): Whether operation succeeded
- `assets` (List[FoundAsset]): Found assets
- `recreated_assets` (List[dict]): Recreated assets (if enabled)
- `error` (str, optional): Error message if failed
- `search_query_used` (str, optional): The search query that was used

### FoundAsset

- `url` (str): Image URL
- `title` (str): Asset title
- `description` (str): Description
- `source` (str): Source website (Unsplash, Pexels, etc.)
- `image_type` (str): Type (photo, illustration, etc.)
- `license_info` (str, optional): License information
- `width` (int, optional): Image width
- `height` (int, optional): Image height

## Notes

- **Rate Limits**: Be mindful of Gemini API rate limits when recreating images
- **Image Quality**: Recreation uses Gemini Imagen, which may take 5-10 seconds per image
- **Design System**: Currently extracts basic design system from company data. For advanced customization, extend `_extract_design_system()` method
- **Free Stock Images**: The agent prioritizes free stock photo sites (Unsplash, Pexels, Pixabay)

