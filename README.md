# OpenBlog

**Open-source AI-powered blog generation system** — 12-stage pipeline for producing high-quality, AEO-optimized articles with production-grade enhancements.

## ✨ Features

### Core Generation
- 🔄 **12-Stage Pipeline** — Modular, testable stages from data fetch to HTML output
- 🎯 **AEO Optimization** — Built-in Answer Engine Optimization scoring (85-90+ scores)
- 🤖 **LLM-Powered Cleanup** — AI-based HTML rendering and content humanization
- 🔍 **Smart Citations** — AEO-optimized citations with Gemini 2.5 Flash validation
- 📝 **Rich Content** — FAQ/PAA extraction, internal links, ToC generation, comparison tables
- 🖼️ **Multiple Images** — Three images per article (hero, mid, bottom) via Gemini Image Creator
- 🎨 **Graphics Generation** — Component-based graphics via OpenFigma

### Content Management
- ✏️ **Rewrite Engine** — Surgical content edits without full regeneration (5x cheaper, 8x faster)
- 🔃 **Content Refresh** — Update existing articles with structured JSON output and diff preview
- 🌐 **Translation API** — Multi-language translation with market adaptation and SEO preservation
- 🔍 **Duplicate Detection** — Content similarity checker to prevent SEO cannibalization

### Production Features
- ⚙️ **Async Job Management** — Fire-and-forget job system with status tracking and progress monitoring
- 🛡️ **3-Layer Quality System** — Defense-in-depth approach (prevention, detection, cleanup)
- 📊 **14+ API Endpoints** — Complete REST API for all operations
- ⚡ **Fast** — 60-90 second generation time

## 📋 Pipeline Stages

```
Stage 0: Data Fetch & Company Detection
Stage 1: Prompt Construction
Stage 2: AI Content Generation (Gemini 3.0 Pro + tools)
Stage 2b: Quality Refinement (optional, LLM-powered fixes)
Stage 3: Structured Data Extraction
Stage 4: Citation Validation (Gemini 2.5 Flash) ─┐
Stage 5: Internal Links                          │ (parallel)
Stage 6: Table of Contents                      │
Stage 7: Metadata                                │
Stage 8: FAQ/PAA Enhancement                     │
Stage 9: Image Generation (3 images)            ─┘
Stage 10: Cleanup & Validation (LLM-powered HTML rendering)
Stage 11: HTML Generation & Storage
```

**Key Improvements:**
- **Stage 2b:** Optional quality refinement with surgical edits
- **Stage 4:** Uses Gemini 2.5 Flash for cost-efficient citation validation (~10x cheaper)
- **Stage 9:** Generates 3 images per article (hero, mid, bottom)
- **Stage 10:** LLM-powered cleanup and HTML rendering for intelligent content processing

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/federicodeponte/openblog.git
cd openblog
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file from the template:

```bash
cp env.example .env
# Edit .env with your API keys
```

**Required:**
```bash
# AI Content Generation (Gemini API - required)
GOOGLE_API_KEY=your_google_api_key
# OR
GEMINI_API_KEY=your_gemini_api_key
# OR
GOOGLE_GEMINI_API_KEY=your_google_gemini_api_key
```

**Optional (but recommended):**
```bash
# Google Drive Integration (for image/graphics storage)
GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'
GOOGLE_DRIVE_FOLDER_ID=your_folder_id
GOOGLE_DELEGATION_SUBJECT=user@domain.com
# See GOOGLE_DRIVE_SETUP.md for detailed setup instructions

# Supabase Storage (for article persistence)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your_supabase_key

# SEO Gap Analysis (for keyword generation)
SERANKING_API_KEY=your_seranking_api_key
```

> **Security Note**: All credentials are stored in environment variables. Never commit `.env` files or hardcode API keys. The `.env` file is automatically ignored by git.

### API Usage

```bash
# Start the server
uvicorn service.api:app --reload

# Generate a blog (synchronous)
curl -X POST http://localhost:8000/write \
  -H "Content-Type: application/json" \
  -d '{
    "primary_keyword": "AI in customer service",
    "company_url": "https://example.com"
  }'

# Generate a blog (asynchronous - fire-and-forget)
curl -X POST http://localhost:8000/write-async \
  -H "Content-Type: application/json" \
  -d '{
    "primary_keyword": "AI in customer service",
    "company_url": "https://example.com"
  }'

# Check job status
curl http://localhost:8000/jobs/{job_id}/status

# Refresh existing content
curl -X POST http://localhost:8000/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "content": "<h1>Article</h1><p>Content...</p>",
    "instructions": ["Update statistics to 2025"],
    "output_format": "html"
  }'

# Translate blog to another language
curl -X POST http://localhost:8000/translate \
  -H "Content-Type: application/json" \
  -d '{
    "html_content": "<h1>Article</h1>...",
    "headline": "Article Title",
    "source_language": "en",
    "target_language": "de",
    "target_country": "DE"
  }'

# Generate graphics
curl -X POST http://localhost:8000/generate-graphics-config \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "theme": {"accent": "#3b82f6"},
      "components": [{"type": "headline", "content": {"text": "Title"}}]
    }
  }'
```

**Available Endpoints:**
- `POST /write` - Synchronous blog generation
- `POST /write-async` - Asynchronous blog generation
- `GET /jobs/{job_id}/status` - Get job status
- `GET /jobs` - List jobs
- `POST /jobs/{job_id}/cancel` - Cancel job
- `POST /refresh` - Refresh existing content
- `POST /translate` - Translate blog article
- `POST /generate-image` - Generate AI image
- `POST /generate-graphics-config` - Generate graphics from config
- `GET /health` - Health check

### Python Usage

```python
from pipeline.core.workflow_engine import WorkflowEngine
from pipeline.core.execution_context import ExecutionContext

engine = WorkflowEngine()
context = ExecutionContext(
    job_id="test-123",
    job_config={
        "primary_keyword": "AI adoption in customer service",
        "company_url": "https://example.com",
    },
)

result = await engine.execute(context)
print(result.final_article["Headline"])
```

## 🏗️ Project Structure

```
openblog/
├── pipeline/
│   ├── blog_generation/    # 12 stages (stage_00 to stage_11)
│   ├── core/               # Workflow engine, execution context, job manager
│   ├── models/             # Data models, AI clients, schemas
│   ├── processors/         # HTML renderer, citations, sitemap, quality checker
│   ├── prompts/            # Prompt templates (main article, graphics)
│   ├── rewrites/           # Rewrite engine (surgical edits)
│   └── utils/              # AEO scorer, similarity checker, helpers
├── service/
│   ├── api.py              # FastAPI endpoints (14+ endpoints)
│   ├── image_generator.py  # Image generation (Gemini Image Creator)
│   ├── graphics_generator.py  # Graphics generation (OpenFigma)
│   └── content_refresher.py   # Content refresh workflow
├── tests/                  # Comprehensive test suite (18+ test files)
├── docs/                   # Documentation
├── modal_deploy.py         # Modal deployment
└── requirements.txt
```

## 📊 Output Quality

- **AEO Score**: 85-90+ / 100 (improved from 70-75)
- **Generation Time**: 60-90 seconds
- **Citation Quality**: 9.5/10 (AEO-optimized with semantic HTML, JSON-LD)
- **Citation Validation**: Gemini 2.5 Flash (~10x cheaper than Pro)
- **HTML Output**: Clean, semantic markup with LLM-powered rendering
- **Images**: 3 per article (hero, mid, bottom)
- **Quality System**: 3-layer defense (prevention, detection, cleanup)

## 🔧 Deployment

### Modal (Recommended)

```bash
pip install modal
modal deploy modal_deploy.py
```

### Docker

```bash
docker build -t openblog .
docker run -p 8000:8000 openblog
```

## 📖 Documentation

### Core Documentation
- [Architecture Overview](ARCHITECTURE_OVERVIEW.md) - High-level system architecture
- [Detailed Architecture](docs/ARCHITECTURE.md) - Complete technical documentation
- [Input Requirements](docs/INPUT_REQUIREMENTS.md) - API input specifications
- [Async Architecture](docs/ASYNC_ARCHITECTURE.md) - Async job management
- [Setup Guide](SETUP.md) - Detailed installation and configuration

### Feature Documentation
- [Modifications & Improvements](MODIFICATIONS_AND_IMPROVEMENTS.md) - **Complete list of enhancements from base repo**
- [Google Drive Setup](GOOGLE_DRIVE_SETUP.md) - Google Drive integration guide
- [OpenFigma Implementation](docs/OPENFIGMA_IMPLEMENTATION.md) - Graphics generation
- [Image Generation](docs/IMAGE_GENERATION.md) - Image generation strategy
- [Graphics Config](docs/GRAPHICS_CONFIG.md) - Graphics configuration guide
- [Quality Upgrade](docs/QUALITY_UPGRADE.md) - Quality system improvements

### Implementation Reports
- [Rewrite Engine](REWRITE_ENGINE_PHASE1_COMPLETE.md) - Surgical edit system
- [Refresh Workflow](REFRESH_IMPLEMENTATION_COMPLETE.md) - Content refresh system
- [Citation v3.2](CITATION_V3.2_SUMMARY.md) - Citation enhancements
- [Production Quality System](PRODUCTION_QUALITY_SYSTEM.md) - 3-layer quality system

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Test specific stage
pytest tests/stages/test_stage_00.py -v

# Test content refresh
pytest tests/test_content_refresher.py -v
pytest tests/test_refresh_api.py -v

# Test rewrite engine
python test_rewrite_engine.py

# Test with environment variables
# Make sure your .env file is configured before running tests
```

**Test Coverage:**
- 18+ comprehensive test suites
- Content parser tests (6 cases)
- Content refresher tests (6 cases)
- Refresh API tests (6 cases)
- Rewrite engine tests (4 cases)
- Stage-by-stage pipeline tests

## 🔒 Security

This project follows security best practices:

- ✅ All API keys and credentials use environment variables
- ✅ `.env` files are automatically ignored by git
- ✅ No hardcoded secrets in source code
- ✅ Credential JSON files excluded from version control

**Important**: Before pushing to GitHub, ensure:
- Your `.env` file is not committed
- No API keys are hardcoded in source files
- All sensitive files are listed in `.gitignore`

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

## 🆕 What's New (Enhanced Version)

This enhanced version includes significant improvements over the base repository:

### Major Features Added
- ✏️ **Rewrite Engine** - Surgical content edits (5x cheaper, 8x faster than full regeneration)
- 🔃 **Content Refresh API** - Update existing articles with structured JSON output
- 🌐 **Translation API** - Multi-language translation with market adaptation
- ⚙️ **Async Job Management** - Production-grade job tracking and monitoring
- 🎨 **Graphics Generation** - Component-based graphics via OpenFigma
- 🖼️ **Multiple Images** - 3 images per article (hero, mid, bottom)
- 🔍 **Duplicate Detection** - Content similarity checker for SEO

### Quality Improvements
- 🛡️ **3-Layer Quality System** - Defense-in-depth approach
- 🤖 **LLM-Powered HTML Rendering** - AI-based cleanup and humanization
- 📊 **AEO Score Improvement** - 70-75 → 85-90+ (15-20 point increase)
- 🔗 **Enhanced Citations** - v3.2 with semantic HTML, JSON-LD, accessibility
- 📋 **Comparison Tables** - Structured data for better AEO

### Performance Optimizations
- ⚡ **Gemini 2.5 Flash** - Citation validation (~10x cheaper, 2-3x faster)
- 🔄 **Parallel Execution** - Stages 4-9 run concurrently
- 📈 **Cost Efficiency** - Optimized model usage throughout pipeline

See [MODIFICATIONS_AND_IMPROVEMENTS.md](MODIFICATIONS_AND_IMPROVEMENTS.md) for complete details.

## 🤝 Contributing

Contributions welcome! Please read the contributing guidelines before submitting PRs.

---

Built with ❤️ by [SCAILE](https://scaile.tech)  
**Enhanced Version** - Production-ready with extensive improvements
