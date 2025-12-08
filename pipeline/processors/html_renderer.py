"""
HTML Renderer - Converts validated article to production HTML.

Simple, clean rendering with:
- Semantic HTML5 structure
- Responsive meta tags
- Open Graph metadata
- Schema.org structured data
- Optimized for SEO and accessibility
- Markdown to HTML conversion
"""

import logging
import re
import html
from typing import Dict, Any, Optional, List
from datetime import datetime

try:
    import markdown
except ImportError:
    markdown = None  # Will install later

from ..utils.schema_markup import generate_all_schemas, render_schemas_as_json_ld
from ..models.output_schema import ArticleOutput

logger = logging.getLogger(__name__)


class HTMLRenderer:
    """Render validated article data to production HTML."""

    @staticmethod
    def _make_absolute_url(url: str, base_url: str) -> str:
        """
        Convert relative URL to absolute URL.
        
        For local development/viewing, keeps output/images/ as relative paths.
        For production, converts to absolute URLs using base_url.
        
        Args:
            url: Potentially relative URL
            base_url: Base URL (company_url)
            
        Returns:
            Absolute or relative URL (relative for local images)
        """
        if not url:
            return ""
        
        # Keep local image paths relative for viewing
        # HTML is at output/SLUG/index.html, images at output/images/
        # So: ../images/filename.webp
        if url.startswith('output/images/'):
            filename = url.split('/')[-1]  # Extract just the filename
            return f"../images/{filename}"
        
        # Already absolute
        if url.startswith(('http://', 'https://')):
            return url
        
        # Make absolute
        base = base_url.rstrip('/')
        path = url.lstrip('/')
        return f"{base}/{path}"

    @staticmethod
    def _markdown_to_html(md_content: str) -> str:
        """
        Convert Markdown content to HTML.
        
        Uses Python-Markdown with extensions:
        - extra: tables, fenced code, footnotes
        - nl2br: newline to <br> conversion
        - sane_lists: better list handling
        
        Args:
            md_content: Markdown formatted text
        
        Returns:
            HTML formatted text
        """
        if not md_content:
            return ""
        
        if markdown is None:
            logger.error("markdown library not installed - cannot convert Markdown to HTML")
            logger.error("Run: pip install markdown")
            return md_content  # Return as-is if markdown not installed
        
        # Configure Markdown parser with extensions
        md = markdown.Markdown(extensions=[
            'extra',       # Tables, fenced code, footnotes
            'nl2br',       # Newlines to <br>
            'sane_lists',  # Better list handling
        ])
        
        # Convert Markdown to HTML
        html_content = md.convert(md_content)
        
        # Post-process: wrap in <p> if no block elements
        if html_content and not html_content.startswith(('<p>', '<h', '<ul>', '<ol>', '<div>', '<blockquote>')):
            html_content = f'<p>{html_content}</p>'
        
        return html_content

    @staticmethod
    def render(
        article: Dict[str, Any],
        company_data: Optional[Dict[str, Any]] = None,
        article_output: Optional[ArticleOutput] = None,
        article_url: Optional[str] = None,
        faq_items: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Render article to production HTML.

        Args:
            article: Validated article dictionary
            company_data: Company metadata (for copyright, logo, etc)

        Returns:
            Complete HTML document string
        """
        if not article:
            return ""

        # Extract key fields
        headline = HTMLRenderer._strip_html(article.get("Headline", "Untitled"))
        subtitle = HTMLRenderer._strip_html(article.get("Subtitle", ""))
        intro_md = article.get("Intro", "")
        # Convert intro from Markdown to HTML
        intro = HTMLRenderer._markdown_to_html(intro_md) if intro_md else ""
        
        # Extract company info (needed for absolute URLs)
        company_name = company_data.get("company_name", "") if company_data else ""
        company_url = company_data.get("company_url", "") if company_data else ""
        
        # Inject company_url into article for _build_content (hidden field)
        article["_company_url"] = company_url
        
        content = HTMLRenderer._build_content(article)
        meta_desc = HTMLRenderer._strip_html(article.get("Meta_Description", ""))  # ✅ CRITICAL FIX: Strip HTML
        meta_title = HTMLRenderer._strip_html(article.get("Meta_Title", headline))  # ✅ CRITICAL FIX: Strip HTML
        
        # Extract and convert image URLs to absolute
        image_url = HTMLRenderer._make_absolute_url(article.get("image_url", ""), company_url)
        image_alt = article.get("image_alt_text", "")
        
        # Mid and bottom images already converted in _build_content
        mid_image_url = HTMLRenderer._make_absolute_url(article.get("mid_image_url", ""), company_url)
        mid_image_alt = article.get("mid_image_alt", "")
        bottom_image_url = HTMLRenderer._make_absolute_url(article.get("bottom_image_url", ""), company_url)
        bottom_image_alt = article.get("bottom_image_alt", "")
        
        sources = article.get("Sources", "")
        toc = article.get("toc", {})
        # Use passed faq_items if provided, otherwise extract from article
        if faq_items is None:
            faq_items = article.get("faq_items", [])
        paa_items = article.get("paa_items", [])
        internal_links = article.get("internal_links_html", "")
        read_time = article.get("read_time", 5)
        publication_date = article.get("publication_date", datetime.now().isoformat())

        # ROOT-LEVEL FIX: Clean ArticleOutput BEFORE schema generation
        # Issue: Schemas were generated from RAW Pydantic model with HTML tags BEFORE
        # _build_content() ran its cleanup, causing schema.org / HTML mismatches
        cleaned_output = HTMLRenderer._clean_article_output_for_schema(article_output) if article_output else None
        
        # Generate JSON-LD schemas with error handling
        schemas_html = ""
        if cleaned_output:
            try:
                # ROOT-LEVEL FIX: Use company_url directly as base_url (don't strip path)
                # Previous bug: rsplit('/') would turn "https://example.com" into "https:"
                base_url = company_url.rstrip('/') if company_url else None
                schemas = generate_all_schemas(
                    output=cleaned_output,  # ← Use CLEANED output
                    company_data=company_data,
                    article_url=article_url,
                    base_url=base_url,
                    faq_items=faq_items,
                )
                schemas_html = render_schemas_as_json_ld(schemas)
            except Exception as e:
                logger.warning(f"Schema generation failed: {e}. Continuing without schemas.")
                schemas_html = ""

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{HTMLRenderer._escape_attr(meta_desc)}">
    <meta name="robots" content="index, follow">
    <meta name="author" content="{HTMLRenderer._escape_attr(company_name)}">
    <title>{HTMLRenderer._escape_html(meta_title)}</title>
    
    {f'<link rel="canonical" href="{HTMLRenderer._escape_attr(article_url)}">' if article_url else ''}

    {HTMLRenderer._og_tags(headline, meta_desc, image_url, article_url, publication_date)}
    {HTMLRenderer._twitter_tags(meta_title, meta_desc, image_url)}
    
    {schemas_html}

    <style>
        :root {{
            --primary: #0066cc;
            --text: #1a1a1a;
            --text-light: #666;
            --bg-light: #f9f9f9;
            --border: #e0e0e0;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: var(--text);
            line-height: 1.6;
            background: white;
        }}

        .container {{ max-width: 900px; margin: 0 auto; padding: 0 20px; }}

        header {{ padding: 40px 0; border-bottom: 1px solid var(--border); margin-bottom: 40px; }}
        header h1 {{ font-size: 2.5em; margin-bottom: 10px; line-height: 1.2; }}
        header .meta {{ color: var(--text-light); font-size: 0.95em; }}

        .featured-image {{ width: 100%; max-height: 400px; object-fit: cover; margin: 30px 0; border-radius: 8px; }}

        .inline-image {{ width: 100%; max-height: 350px; object-fit: cover; margin: 40px 0; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}

        .intro {{ font-size: 1.1em; color: var(--text-light); margin: 30px 0; font-style: italic; }}

        .toc {{ background: var(--bg-light); padding: 20px; border-radius: 8px; margin: 30px 0; }}
        .toc h2 {{ font-size: 1.2em; margin-bottom: 15px; }}
        .toc ul {{ list-style: none; }}
        .toc li {{ margin: 8px 0; }}
        .toc a {{ color: var(--primary); text-decoration: none; }}
        .toc a:hover {{ text-decoration: underline; }}

        article {{ margin: 40px 0; }}
        article h2 {{ font-size: 1.8em; margin: 40px 0 20px; }}
        article h3 {{ font-size: 1.3em; margin: 30px 0 15px; }}
        article p {{ margin: 15px 0; }}
        article ul, article ol {{ margin: 15px 0 15px 30px; }}
        article li {{ margin: 8px 0; }}
        article a {{ color: var(--primary); text-decoration: none; }}
        article a:hover {{ text-decoration: underline; }}

        .faq, .paa {{ margin: 40px 0; }}
        .faq h2, .paa h2 {{ font-size: 1.5em; margin-bottom: 20px; }}
        .faq-item, .paa-item {{ margin: 20px 0; padding: 15px; background: var(--bg-light); border-radius: 6px; }}
        .faq-item h3, .paa-item h3 {{ margin-bottom: 10px; font-size: 1.1em; }}

        .more-links {{ margin: 40px 0; padding: 20px; background: var(--bg-light); border-radius: 8px; }}
        .more-links h2 {{ font-size: 1.3em; margin-bottom: 15px; }}
        .more-links ul {{ list-style: none; margin: 0; }}
        .more-links li {{ margin: 10px 0; }}
        .more-links a {{ color: var(--primary); text-decoration: none; }}

        footer {{ border-top: 1px solid var(--border); margin-top: 60px; padding: 40px 0; color: var(--text-light); font-size: 0.9em; }}
        footer a {{ color: var(--primary); }}

        .citations {{ margin: 40px 0; padding: 20px; background: var(--bg-light); border-left: 4px solid var(--primary); }}
        .citations h2 {{ font-size: 1.2em; margin-bottom: 15px; }}
        .citations ol {{ margin: 0 0 0 20px; }}
        .citations li {{ margin: 10px 0; }}
        
        .citation {{ color: var(--primary); text-decoration: none; font-weight: 500; }}
        .citation:hover {{ text-decoration: underline; }}
        
        /* Comparison table styles */
        .comparison-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 2rem 0;
            background: white;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        }}
        
        .comparison-table caption {{
            caption-side: top;
            font-weight: 600;
            font-size: 1.1em;
            color: var(--text);
            padding: 0.75rem 0;
            text-align: left;
            margin-bottom: 0.5rem;
        }}
        
        .comparison-table th {{
            background: var(--bg-light);
            font-weight: 600;
            padding: 0.75rem 1rem;
            text-align: left;
            border: 1px solid var(--border);
            font-size: 0.95em;
            color: var(--text);
        }}
        
        .comparison-table td {{
            padding: 0.75rem 1rem;
            border: 1px solid var(--border);
            vertical-align: top;
        }}
        
        .comparison-table tbody tr:hover {{
            background: #f5f9ff;
        }}
        
        .comparison-table tbody tr:nth-child(even) {{
            background: var(--bg-light);
        }}
        
        .comparison-table tbody tr:nth-child(even):hover {{
            background: #f5f9ff;
        }}
        
        /* Responsive table */
        @media (max-width: 768px) {{
            .comparison-table {{
                font-size: 0.9em;
            }}
            
            .comparison-table th,
            .comparison-table td {{
                padding: 0.5rem 0.75rem;
            }}
        }}
            </style>
</head>
<body>
    <header class="container">
        <h1>{HTMLRenderer._escape_html(headline)}</h1>
        {f'<h2 class="subtitle">{HTMLRenderer._escape_html(subtitle)}</h2>' if subtitle else ''}
        <div class="meta">
            <span>Published: {publication_date.split('T')[0]}</span>
            <span> • </span>
            <span>Read time: {read_time} min</span>
            {f' • <span><a href="{HTMLRenderer._escape_attr(company_url)}">{HTMLRenderer._escape_html(company_name)}</a></span>' if company_url else ''}
        </div>
    </header>

    <main class="container">
        {f'<img src="{HTMLRenderer._escape_attr(image_url)}" alt="{HTMLRenderer._escape_attr(image_alt)}" class="featured-image">' if image_url else ''}

        {f'<div class="intro">{intro}</div>' if intro else ''}

        {HTMLRenderer._render_toc(toc)}

        <article>
            {content}
        </article>

        {HTMLRenderer._render_paa(paa_items)}
        {HTMLRenderer._render_faq(faq_items)}
        {internal_links}
        {HTMLRenderer._render_citations(sources)}
    </main>

    <footer class="container">
        <p>© {datetime.now().year} {HTMLRenderer._escape_html(company_name)}. All rights reserved.</p>
        {f'<p><a href="{HTMLRenderer._escape_attr(company_url)}">Visit {HTMLRenderer._escape_html(company_name)}</a></p>' if company_url else ''}
    </footer>
</body>
</html>"""
        return html

    @staticmethod
    def _render_comparison_table(table: Dict[str, Any]) -> str:
        """
        Render a comparison table from ComparisonTable data.
        
        Args:
            table: Dict with keys: title, headers, rows
            
        Returns:
            HTML string with table markup
        """
        title = table.get('title', '')
        headers = table.get('headers', [])
        rows = table.get('rows', [])
        
        if not headers or not rows:
            return ""
        
        # Build table HTML
        html_parts = []
        
        # Table title (h3) - for visual hierarchy
        if title:
            html_parts.append(f'<h3>{HTMLRenderer._escape_html(title)}</h3>')
        
        # Open table
        html_parts.append('<table class="comparison-table">')
        
        # ROOT-LEVEL FIX: Add <caption> for accessibility and SEO (Issue 10)
        if title:
            html_parts.append(f'  <caption>{HTMLRenderer._escape_html(title)}</caption>')
        
        # Table header
        html_parts.append('  <thead>')
        html_parts.append('    <tr>')
        for header in headers:
            html_parts.append(f'      <th>{HTMLRenderer._escape_html(header)}</th>')
        html_parts.append('    </tr>')
        html_parts.append('  </thead>')
        
        # Table body
        html_parts.append('  <tbody>')
        for row in rows:
            html_parts.append('    <tr>')
            for cell in row:
                html_parts.append(f'      <td>{HTMLRenderer._escape_html(cell)}</td>')
            html_parts.append('    </tr>')
        html_parts.append('  </tbody>')
        
        # Close table
        html_parts.append('</table>')
        
        return '\n'.join(html_parts)

    @staticmethod
    def _build_content(article: Dict[str, Any]) -> str:
        """Build article content from sections with inline images and comparison tables."""
        parts = []
        
        # Get company URL for absolute image paths
        # Note: This is a workaround - ideally we'd pass these as parameters
        # but keeping the method signature unchanged for now
        company_url = article.get("_company_url", "")  # Hidden field for URL conversion
        
        # Extract and convert images to absolute URLs
        mid_image_url = HTMLRenderer._make_absolute_url(article.get("mid_image_url", ""), company_url)
        mid_image_alt = article.get("mid_image_alt", "")
        bottom_image_url = HTMLRenderer._make_absolute_url(article.get("bottom_image_url", ""), company_url)
        bottom_image_alt = article.get("bottom_image_alt", "")
        
        # Extract comparison tables (max 2)
        tables = article.get("tables", [])

        for i in range(1, 10):
            title_key = f"section_{i:02d}_title"
            content_key = f"section_{i:02d}_content"

            title = article.get(title_key, "")
            content = article.get(content_key, "")

            if title and title.strip():
                # Strip any <p> tags from title before escaping
                title_clean = HTMLRenderer._strip_html(title)
                parts.append(f"<h2>{HTMLRenderer._escape_html(title_clean)}</h2>")

            if content and content.strip():
                # Convert Markdown to HTML
                content_html = HTMLRenderer._markdown_to_html(content)
                # Clean up artifacts and patterns
                content_clean = HTMLRenderer._cleanup_content(content_html)
                parts.append(content_clean)
            
            # Inject first comparison table after section 2
            if i == 2 and tables and len(tables) >= 1:
                parts.append(HTMLRenderer._render_comparison_table(tables[0]))
            
            # Inject mid-article image after section 3
            if i == 3 and mid_image_url:
                parts.append(f'<img src="{HTMLRenderer._escape_attr(mid_image_url)}" alt="{HTMLRenderer._escape_attr(mid_image_alt)}" class="inline-image">')
            
            # Inject second comparison table after section 5
            if i == 5 and tables and len(tables) >= 2:
                parts.append(HTMLRenderer._render_comparison_table(tables[1]))
            
            # Inject bottom image after section 6
            if i == 6 and bottom_image_url:
                parts.append(f'<img src="{HTMLRenderer._escape_attr(bottom_image_url)}" alt="{HTMLRenderer._escape_attr(bottom_image_alt)}" class="inline-image">')

        return "\n".join(parts) if parts else "<p>No content available.</p>"

    @staticmethod
    def _render_toc(toc: Dict[str, Any]) -> str:
        """Render table of contents."""
        if not toc:
            return ""

        items = [f'<li><a href="#{k}">{HTMLRenderer._escape_html(v)}</a></li>' for k, v in toc.items() if v]

        if not items:
            return ""

        return f"""<div class="toc">
            <h2>Table of Contents</h2>
            <ul>
                {''.join(items)}
            </ul>
        </div>"""

    @staticmethod
    def _render_faq(faq_items: list) -> str:
        """Render FAQ section."""
        if not faq_items:
            return ""

        items_html = []
        for item in faq_items:
            q = item.get("question", "")
            a = item.get("answer", "")
            if q and a:
                # Convert answer from Markdown to HTML
                a_html = HTMLRenderer._markdown_to_html(a)
                # Strip outer <p> tags if present (we'll add them in the template)
                a_html = re.sub(r'^<p>(.*)</p>$', r'\1', a_html.strip(), flags=re.DOTALL)
                items_html.append(
                    f'<div class="faq-item"><h3>{HTMLRenderer._escape_html(q)}</h3><p>{a_html}</p></div>'
                )

        if not items_html:
            return ""

        return f"""<section class="faq">
            <h2>Frequently Asked Questions</h2>
            {''.join(items_html)}
        </section>"""

    @staticmethod
    def _render_paa(paa_items: list) -> str:
        """Render People Also Ask section."""
        if not paa_items:
            return ""

        items_html = []
        for item in paa_items:
            q = item.get("question", "")
            a = item.get("answer", "")
            if q and a:
                # Convert answer from Markdown to HTML
                a_html = HTMLRenderer._markdown_to_html(a)
                # Strip outer <p> tags if present (we'll add them in the template)
                a_html = re.sub(r'^<p>(.*)</p>$', r'\1', a_html.strip(), flags=re.DOTALL)
                items_html.append(
                    f'<div class="paa-item"><h3>{HTMLRenderer._escape_html(q)}</h3><p>{a_html}</p></div>'
                )

        if not items_html:
            return ""

        return f"""<section class="paa">
            <h2>People Also Ask</h2>
            {''.join(items_html)}
        </section>"""

    @staticmethod
    def _render_citations(sources: str) -> str:
        """Render citations section."""
        if not sources or not sources.strip():
            return ""

        lines = [line.strip() for line in sources.split("\n") if line.strip()]
        if not lines:
            return ""

        # ROOT-LEVEL FIX: Strip [N]: prefix from citations (let <ol> handle numbering)
        # Also ensure HTML entities are properly escaped
        items_html = []
        for line in lines:
            # Remove [N]: prefix if present (Gemini sometimes adds it)
            cleaned_line = re.sub(r'^\[\d+\]:\s*', '', line)
            items_html.append(f"<li>{HTMLRenderer._escape_html(cleaned_line)}</li>")

        return f"""<section class="citations">
            <h2>Sources</h2>
            <ol>
                {''.join(items_html)}
            </ol>
        </section>"""

    @staticmethod
    def _escape_html(text: str) -> str:
        """Escape HTML special characters."""
        if not text:
            return ""
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )

    @staticmethod
    def _escape_attr(text: str) -> str:
        """Escape HTML attribute values."""
        if not text:
            return ""
        return str(text).replace('"', "&quot;").replace("'", "&#x27;")

    @staticmethod
    def _strip_html(text: str) -> str:
        """Remove all HTML tags from text."""
        import re
        if not text:
            return ""
        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', '', str(text))
        # Clean up any leftover entities
        clean = clean.replace('&nbsp;', ' ').strip()
        return clean
    
    @staticmethod
    def _clean_article_output_for_schema(article_output: ArticleOutput) -> ArticleOutput:
        """
        Clean ArticleOutput fields BEFORE passing to schema generation.
        
        CRITICAL FIX for Issue 1: Schema.org timing bug
        
        Problem: Schemas were generated from RAW Pydantic model with HTML tags
        BEFORE _build_content() ran its cleanup, causing mismatches:
        - Schema: "<p>Uber infrastructure</p>"
        - HTML: "Uber infrastructure"
        
        Solution: Clean all text fields that go into schemas (headline, subtitle,
        direct answer, intro, section titles, FAQ/PAA) BEFORE schema generation.
        
        This ensures schema.org and visible HTML contain identical content.
        """
        from copy import deepcopy
        
        # Deep copy to avoid mutating original
        cleaned = deepcopy(article_output)
        
        # Clean all fields that appear in schemas
        cleaned.Headline = HTMLRenderer._strip_html(cleaned.Headline)
        cleaned.Subtitle = HTMLRenderer._strip_html(cleaned.Subtitle) if cleaned.Subtitle else ""
        cleaned.Teaser = HTMLRenderer._strip_html(cleaned.Teaser)
        cleaned.Direct_Answer = HTMLRenderer._strip_html(cleaned.Direct_Answer)
        cleaned.Intro = HTMLRenderer._strip_html(cleaned.Intro)
        
        # Clean section titles (appear in breadcrumbs/TOC)
        for i in range(1, 10):
            title_field = f"section_{i:02d}_title"
            title_value = getattr(cleaned, title_field, "")
            if title_value:
                setattr(cleaned, title_field, HTMLRenderer._strip_html(title_value))
        
        # Clean FAQ questions/answers (appear in FAQPage schema)
        for i in range(1, 7):
            q_field = f"faq_{i:02d}_question"
            a_field = f"faq_{i:02d}_answer"
            q_value = getattr(cleaned, q_field, "")
            a_value = getattr(cleaned, a_field, "")
            if q_value:
                setattr(cleaned, q_field, HTMLRenderer._strip_html(q_value))
            if a_value:
                setattr(cleaned, a_field, HTMLRenderer._strip_html(a_value))
        
        # Clean PAA questions/answers
        for i in range(1, 5):
            q_field = f"paa_{i:02d}_question"
            a_field = f"paa_{i:02d}_answer"
            q_value = getattr(cleaned, q_field, "")
            a_value = getattr(cleaned, a_field, "")
            if q_value:
                setattr(cleaned, q_field, HTMLRenderer._strip_html(q_value))
            if a_value:
                setattr(cleaned, a_field, HTMLRenderer._strip_html(a_value))
        
        logger.info("🔧 Cleaned ArticleOutput for schema generation (removed HTML tags)")
        
        return cleaned

    @staticmethod
    def _linkify_citations(content: str) -> str:
        """Convert citation markers [1], [2], [3] into clickable anchor links."""
        import re
        if not content:
            return ""
        
        # Pattern: [1], [2], [1][2], [1][2][3], etc.
        # Replace [N] with <a href="#source-N" class="citation">[N]</a>
        def replace_citation(match):
            num = match.group(1)
            return f'<a href="#source-{num}" class="citation">[{num}]</a>'
        
        # Match [N] where N is one or more digits
        return re.sub(r'\[(\d+)\]', replace_citation, content)

    @staticmethod
    def _humanize_content(content: str) -> str:
        """
        🛡️ LAYER 3: Production-grade post-processing fallback.
        
        This is our GUARANTEED fix layer - catches anything the prompt missed.
        
        Fixes (in priority order):
        1. Em dashes (—) → commas/parentheses [CRITICAL - zero tolerance]
        2. Robotic phrases ("Here's how", "Key points:") [HIGH]
        3. Formulaic transitions [MEDIUM]
        4. AI grammar mistakes [LOW]
        
        Philosophy: Prevention (prompt) is best, but detection + cleanup (here) is mandatory.
        """
        if not content:
            return ""
        
        # ═══════════════════════════════════════════════════════════════════
        # CRITICAL FIX #1: Em Dashes (—) - ZERO TOLERANCE
        # ═══════════════════════════════════════════════════════════════════
        # Em dashes are the #1 AI marker. Must remove ALL instances.
        
        # Strategy 1: Paired em dashes (parenthetical clause)
        # "text—middle clause—text" → "text (middle clause) text" OR "text, middle clause, text"
        def replace_paired_em_dash(match):
            before = match.group(1)
            middle = match.group(2)
            after = match.group(3)
            
            # Short clause (< 40 chars) → parentheses
            if len(middle.strip()) < 40:
                return f"{before}({middle.strip()}){after}"
            # Long clause → commas
            else:
                return f"{before}, {middle.strip()},{after}"
        
        # Match: (text)—(clause)—(text)
        content = re.sub(
            r'([^—\n]{8,})\s*—\s*([^—\n]{3,}?)\s*—\s*([^—\n]{8,})',
            replace_paired_em_dash,
            content
        )
        
        # Strategy 2: Single em dashes (sentence separator)
        # "text—more text" → "text, more text" OR "text. More text"
        def replace_single_em_dash(match):
            before = match.group(1)
            after = match.group(2)
            
            # If after starts with capital letter → split into sentences
            if after and after[0].isupper():
                return f"{before}. {after}"
            # Otherwise use comma
            else:
                return f"{before}, {after}"
        
        # Match: (word)—(word)
        content = re.sub(
            r'(\w+)\s*—\s*(\w+)',
            replace_single_em_dash,
            content
        )
        
        # Strategy 3: Any remaining em dashes → commas (safety net)
        content = content.replace("—", ", ")
        
        # Strategy 4: HTML entities for em dash (fallback)
        content = content.replace("&mdash;", ", ")
        content = content.replace("&#8212;", ", ")
        
        # Strategy 5: Unicode variants (belt-and-suspenders)
        content = content.replace("\u2014", ", ")  # Em dash
        content = content.replace("\u2013", ", ")  # En dash
        
        # ═══════════════════════════════════════════════════════════════════
        # HIGH PRIORITY FIX #2: Robotic List Introductions
        # ═══════════════════════════════════════════════════════════════════
        # <p>Here's how:</p> → (remove)
        # <p>Key points:</p> → (remove)
        # <p>Important considerations:</p> → (remove)
        
        robotic_intros = [
            r'Here\'s how',
            r'Here\'s what',
            r'Here is how',
            r'Here is what',
            r'Key points?',
            r'Key benefits? include',
            r'Important considerations?',
            r'The following are',
            r'Consider the following',
        ]
        
        for pattern in robotic_intros:
            # Remove standalone intros: <p>Pattern:</p>
            content = re.sub(
                rf'<p>\s*{pattern}\s*:?\s*</p>',
                '',
                content,
                flags=re.IGNORECASE
            )
            
            # Also remove mid-sentence: "Pattern: " at start of <p>
            content = re.sub(
                rf'(<p>)\s*{pattern}\s*:\s*',
                r'\1',
                content,
                flags=re.IGNORECASE
            )
        
        # ═══════════════════════════════════════════════════════════════════
        # MEDIUM PRIORITY FIX #3: Formulaic Transitions
        # ═══════════════════════════════════════════════════════════════════
        formulaic_fixes = [
            # "Here's how" / "Here's what" phrases (sentence-level)
            (r'\bHere\'s how\s+', ''),  # "Here's how the market" → "The market"
            (r'\bHere\'s what\s+', ''),  # "Here's what matters" → "Matters"
            (r'\bHere are the\s+', 'The '),  # "Here are the tools" → "The tools"
            
            # Awkward transitions
            (r'\bThat\'s why similarly,?\s*', 'Similarly, '),
            (r'\bIf you want another\s+', 'Another '),
            (r'\bIf you want\s+', ''),
        ]
        
        for pattern, replacement in formulaic_fixes:
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
        
        # ═══════════════════════════════════════════════════════════════════
        # LOW PRIORITY FIX #4: AI Grammar Mistakes
        # ═══════════════════════════════════════════════════════════════════
        grammar_fixes = [
            (r'\bWhen you choosing\b', 'When choosing'),
            (r'\bYou\'ll find to\b', 'To'),
            (r'\bso you can managing\b', 'managing'),
            (r'\bWhat is as we handle of\b', 'As we evaluate'),
            (r'\bWhat is as we\b', 'As we'),
        ]
        
        for pattern, replacement in grammar_fixes:
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
        
        # ═══════════════════════════════════════════════════════════════════
        # FINAL CLEANUP: Whitespace
        # ═══════════════════════════════════════════════════════════════════
        # Fix double spaces
        content = re.sub(r'  +', ' ', content)
        
        # Fix space before punctuation
        content = re.sub(r' ([.,;:!?])', r'\1', content)
        
        # Fix missing space after punctuation
        content = re.sub(r'([.,;:!?])([A-Z])', r'\1 \2', content)
        
        return content.strip()

    @staticmethod
    def _cleanup_content(content: str) -> str:
        """
        Post-process HTML content with safety net cleanup.
        
        Stage 2b (Comprehensive Content Transformation) should handle ALL content issues.
        This method is now a SAFETY NET only for:
        1. Emergency fallback: Remove any remaining [N] citations (if Stage 2b missed)
        2. HTML-specific fixes: broken tags, escaped characters
        3. Final whitespace cleanup
        
        ⚠️ If this method catches issues, it means Stage 2b needs improvement.
        """
        if not content:
            return ""
        
        # ===========================================================================
        # SAFETY NET 1: EMERGENCY CITATION REMOVAL (if Stage 2b missed any)
        # ===========================================================================
        # Stage 2b should have transformed [N] → inline attribution
        # This is emergency fallback only
        
        remaining_citations = len(re.findall(r'\[\d+\]', content))
        if remaining_citations > 0:
            logger.warning(f"⚠️ SAFETY NET: Stage 2b missed {remaining_citations} citations, removing as fallback")
            
            # Pattern 1: Broken #source-N links (any anchor text)
            content = re.sub(
                r'<a[^>]*href=["\']#source-\d+["\'][^>]*>([^<]+)</a>',
                r'\1',  # Keep only the anchor text
                content
            )
            
            # Pattern 2: Standalone [N]
            content = re.sub(r'\[\d+\]', '', content)
            
            # Pattern 3: Multiple consecutive [N][M][K]
            content = re.sub(r'(?:\[\d+\])+', '', content)
            
            # Pattern 4: [N] with spaces [ 1 ]
            content = re.sub(r'\[\s*\d+\s*\]', '', content)
            
            # Cleanup orphaned commas from citation removal
            content = re.sub(r',\s*,', ',', content)
            content = re.sub(r'\s+,', ',', content)
            content = re.sub(r',\s*\.', '.', content)
        else:
            logger.info("✅ No academic citations found (Stage 2b worked correctly)")
        
        # ===========================================================================
        # SAFETY NET 2: CHECK FOR EM DASHES (Stage 2b should have removed)
        # ===========================================================================
        em_dash_count = content.count('—') + content.count('&mdash;') + content.count('&#8212;')
        if em_dash_count > 0:
            logger.warning(f"⚠️ SAFETY NET: Stage 2b missed {em_dash_count} em dashes, removing as fallback")
            content = content.replace('—', ', ')
            content = content.replace('&mdash;', ', ')
            content = content.replace('&#8212;', ', ')
        else:
            logger.info("✅ No em dashes found (Stage 2b worked correctly)")
        
        # ===========================================================================
        # SAFETY NET 3: CHECK FOR STANDALONE LABELS (Stage 2b should have integrated)
        # ===========================================================================
        standalone_patterns = [
            r'<p>\s*<strong>[^<]+:</strong>\s*</p>',
            r'<p>\s*Key benefits include:\s*</p>',
            r'<p>\s*Important considerations:\s*</p>',
            r'<p>\s*Here are key points:\s*</p>',
        ]
        
        for pattern in standalone_patterns:
            matches = len(re.findall(pattern, content, flags=re.IGNORECASE))
            if matches > 0:
                logger.warning(f"⚠️ SAFETY NET: Stage 2b missed {matches} standalone labels, removing as fallback")
                content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        # ===========================================================================
        # HTML-SPECIFIC FIXES (NOT content transformation)
        # ===========================================================================
        
        # ===========================================================================
        # MARKDOWN CONVERSION ARTIFACTS (from Markdown→HTML)
        # ===========================================================================
        
        # Pattern 1: Double-wrapped paragraphs from Markdown parsing
        content = re.sub(r'<p>\s*<p>([^<]+)</p>\s*</p>', r'<p>\1</p>', content)
        content = re.sub(r'<p>\s*<p>', '<p>', content)
        content = re.sub(r'</p>\s*</p>', '</p>', content)
        
        # Pattern 2: Empty list items from Markdown parsing
        content = re.sub(r'<li>\s*</li>', '', content)
        
        # Pattern 3: Lists immediately after paragraphs (add spacing for readability)
        content = re.sub(r'</p>\s*<ul>', '</p>\n<ul>', content)
        content = re.sub(r'</p>\s*<ol>', '</p>\n<ol>', content)
        
        # Fix duplicate punctuation (HTML rendering artifact)
        content = re.sub(r'([.,;:!?])\1+', r'\1', content)
        
        # Remove empty or near-empty paragraphs (HTML structure cleanup)
        content = re.sub(r'<p>\s*[.,;:\s]+\s*</p>', '', content)
        
        # Standardize internal links to /magazine/ format (HTML link normalization)
        def fix_internal_link(match):
            full_tag = match.group(0)
            href = match.group(1)
            
            # Skip if already /magazine/ or external/anchor
            if href.startswith('/magazine/') or href.startswith('http') or href.startswith('#'):
                return full_tag
            
            # Fix: remove /blog/ prefix if present, then add /magazine/
            if href.startswith('/blog/'):
                new_href = href.replace('/blog/', '/magazine/', 1)
            elif href.startswith('/'):
                new_href = f'/magazine{href}'
            else:
                return full_tag
            
            return full_tag.replace(f'href="{href}"', f'href="{new_href}"').replace(f"href='{href}'", f"href='{new_href}'")
        
        content = re.sub(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>', fix_internal_link, content)
        
        # ===========================================================================
        # FINAL WHITESPACE CLEANUP
        # ===========================================================================
        
        # Remove duplicate consecutive paragraphs (exact duplicates)
        lines = content.split('\n')
        deduped = []
        prev_line = None
        for line in lines:
            if line.strip() != prev_line:
                deduped.append(line)
                prev_line = line.strip()
        content = '\n'.join(deduped)
        
        # Clean up multiple consecutive newlines
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        logger.info("✅ Stage 10 safety net complete (HTML-only cleanup)")
        
        return content.strip()

    @staticmethod
    def _og_tags(title: str, desc: str, image: str, url: str, publication_date: str = None) -> str:
        """Generate OpenGraph meta tags for social media sharing."""
        tags = [
            f'<meta property="og:title" content="{HTMLRenderer._escape_attr(title)}">',
            f'<meta property="og:description" content="{HTMLRenderer._escape_attr(desc)}">',
        ]

        if image:
            tags.append(f'<meta property="og:image" content="{HTMLRenderer._escape_attr(image)}">')

        if url:
            tags.append(f'<meta property="og:url" content="{HTMLRenderer._escape_attr(url)}">')

        tags.append('<meta property="og:type" content="article">')
        
        # Add article-specific Open Graph tags
        if publication_date:
            tags.append(f'<meta property="article:published_time" content="{publication_date}">')

        return "\n    ".join(tags)
    
    @staticmethod
    def _twitter_tags(title: str, desc: str, image: str) -> str:
        """Generate Twitter Card meta tags for Twitter/X sharing."""
        tags = [
            '<meta name="twitter:card" content="summary_large_image">',
            f'<meta name="twitter:title" content="{HTMLRenderer._escape_attr(title)}">',
            f'<meta name="twitter:description" content="{HTMLRenderer._escape_attr(desc)}">',
        ]
        
        if image:
            tags.append(f'<meta name="twitter:image" content="{HTMLRenderer._escape_attr(image)}">')
        
        return "\n    ".join(tags)
