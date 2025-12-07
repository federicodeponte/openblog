"""
HTML Renderer - Converts validated article to production HTML.

Simple, clean rendering with:
- Semantic HTML5 structure
- Responsive meta tags
- Open Graph metadata
- Schema.org structured data
- Optimized for SEO and accessibility
"""

import logging
import re
from typing import Dict, Any, Optional, List
from datetime import datetime

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
        intro = article.get("Intro", "")
        
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

        # Generate JSON-LD schemas with error handling
        schemas_html = ""
        if article_output:
            try:
                base_url = company_url.rsplit('/', 1)[0] if company_url else None
                schemas = generate_all_schemas(
                    output=article_output,
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
        
        # Table title (h3)
        if title:
            html_parts.append(f'<h3>{HTMLRenderer._escape_html(title)}</h3>')
        
        # Open table
        html_parts.append('<table class="comparison-table">')
        
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
                # Clean up useless patterns (also removes all [N] citations)
                content_clean = HTMLRenderer._cleanup_content(content)
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
                items_html.append(
                    f'<div class="faq-item"><h3>{HTMLRenderer._escape_html(q)}</h3><p>{a}</p></div>'
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
                items_html.append(
                    f'<div class="paa-item"><h3>{HTMLRenderer._escape_html(q)}</h3><p>{a}</p></div>'
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

        items_html = [f"<li>{HTMLRenderer._escape_html(line)}</li>" for line in lines]

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
        Post-process content to remove useless patterns and standardize internal links.
        
        Removes:
        1. Standalone labels with only citations: <p><strong>Label:</strong> [N]</p>
        2. Plain text labels with only citations: "Label: [N][M]"
        3. Empty <p> tags or tags with only whitespace/punctuation
        4. Duplicate consecutive paragraphs
        
        Fixes:
        5. Double commas, periods, and other duplicate punctuation (Gemini typos)
        6. AI language markers (em dashes, robotic phrases) - via _humanize_content
        
        Standardizes:
        7. Internal links to use /magazine/ prefix
        """
        if not content:
            return ""
        
        # STEP 0: REMOVE ALL ACADEMIC CITATIONS [N] - SAFETY NET
        # This is a HARD BLOCK to enforce inline-only citation style
        # Removes: [1], [2], [1][2], [2][3], etc.
        # Also removes <a href="#source-X">[N]</a> (linked academic citations)
        content = re.sub(r'<a[^>]*href=["\']#source-\d+["\'][^>]*>\s*\[\d+\]\s*</a>', '', content)  # Linked [N]
        content = re.sub(r'\[\d+\]', '', content)  # Standalone [N]
        logger.info("🚫 Stripped all [N] academic citations (enforcing inline-only style)")
        
        # STEP 0.5: REMOVE EMPTY LABEL PARAGRAPHS (Gemini bug)
        # Matches: <p><strong>GitHub Copilot:</strong></p> (label with NO content after)
        # Matches: <p><strong>Amazon Q Developer:</strong></p>
        content = re.sub(r'<p>\s*<strong>[^<]+:</strong>\s*</p>', '', content)
        logger.info("🧹 Removed empty label paragraphs")
        
        # STEP 0.6: FIX SENTENCE FRAGMENTS AT START OF PARAGRAPHS (Gemini bug)
        # Gemini sometimes splits sentences incorrectly, creating fragments like:
        # "<p>Some text</p><p>. However, more text</p>" → "<p>Some text. However, more text</p>"
        # "<p>Some text</p><p>What is as these...</p>" → "<p>Some text What is as these...</p>"
        # Pattern: </p><p> followed by punctuation or fragment word
        content = re.sub(r'</p>\s*<p>(\s*[.,;:])', r'\1', content)  # Join punctuation fragments
        content = re.sub(r'</p>\s*<p>(This is |What is |That\'s why |If you want |When you )', r' \1', content)  # Join phrase fragments
        logger.info("🔧 Fixed sentence fragments at paragraph starts")
        
        # STEP 0.7: FIX GEMINI HALLUCINATION PATTERNS (context loss bugs)
        # Gemini loses context mid-generation and outputs broken phrases:
        # "You can aI code generation" → remove entire broken phrase
        # "When you aI code generation" → remove entire broken phrase
        # "What is aI code generation" → remove entire broken phrase
        # "so you can of increased" → remove broken phrase
        # "Here's this reality faces" → "This reality faces"
        
        # Pattern 1: "You can/When you/What is" + lowercase "aI code" (context loss)
        content = re.sub(r'<p>\s*(You can|When you|What is)\s+aI\s+code[^<]*</p>', '', content, flags=re.IGNORECASE)
        content = re.sub(r'\b(You can|When you|What is)\s+aI\s+code[^.!?]*[.!?]?', '', content, flags=re.IGNORECASE)
        
        # Pattern 2: "so you can of" (broken grammar)
        content = re.sub(r'\bso you can of\b', '', content, flags=re.IGNORECASE)
        
        # Pattern 3: "Here's this reality faces" → "This reality faces"
        content = re.sub(r"Here's this (reality|scenario|situation)", r'This \1', content, flags=re.IGNORECASE)
        
        # Pattern 4: Double question words "What is How" / "What is Why"
        content = re.sub(r'<h2>What is (How|Why|What|When|Where)\b', r'<h2>\1', content, flags=re.IGNORECASE)
        
        # Pattern 5: Standalone "matters:" or "so you can:" labels
        content = re.sub(r'<p>\s*(matters|so you can|if you want):\s*</p>', '', content, flags=re.IGNORECASE)
        
        logger.info("🚨 Fixed Gemini hallucination patterns (context loss)")
        
        # STEP 0.8: FIX KEYWORD LINE BREAKS (Issue D)
        # Gemini sometimes creates paragraph breaks in the middle of keywords:
        # "adoption of\n\nAI code review tools 2025\n\nhas..." → "adoption of AI code review tools 2025 has..."
        # Pattern: Text + newlines + capitalized phrase + newlines + continuation
        content = re.sub(r'(\w+)\s*\n{2,}\s*([A-Z][A-Za-z\s\d]+)\s*\n{2,}\s*([a-z])', r'\1 \2 \3', content)
        logger.info("🔧 Fixed keyword line breaks")
        
        # STEP 0.9: FIX INCOMPLETE SENTENCES (Issue E)
        # Detect and remove sentences that end mid-thought:
        # "Ultimately," → remove entire paragraph
        # "However," → remove if at end of paragraph
        # Pattern: Paragraph ending with conjunction/comma and no continuation
        content = re.sub(
            r'<p>([^<]*?)(Ultimately|However|Moreover|Furthermore|Therefore|Additionally),?\s*</p>(?!\s*<p>)',
            r'<p>\1</p>',
            content,
            flags=re.IGNORECASE
        )
        logger.info("🔧 Fixed incomplete trailing sentences")
        
        # STEP 1: Humanize language (remove AI markers)
        content = HTMLRenderer._humanize_content(content)
        
        # Pattern 0: Fix duplicate punctuation (Gemini typos)
        # Matches: ,, or .. or ;; or :: etc.
        # Replace with single punctuation
        content = re.sub(r'([.,;:!?])\1+', r'\1', content)
        
        # Pattern 1: Remove <p><strong>Label:</strong> LINKED_CITATIONS</p>
        # Matches: <p><strong>Anything:</strong> <a...>[1]</a><a...>[2]</a></p>
        # This catches linkified citations
        content = re.sub(
            r'<p>\s*<strong>[^<]+:</strong>\s*(?:<a[^>]*>\[\d+\]</a>\s*)+\s*</p>',
            '',
            content,
            flags=re.IGNORECASE
        )
        
        # Pattern 2: Remove <p><strong>Label:</strong> RAW_CITATIONS</p>
        # Matches: <p><strong>Anything:</strong> [1][2][3]</p>
        # This catches citations before linkification
        content = re.sub(
            r'<p>\s*<strong>[^<]+:</strong>\s*(?:\[\d+\]\s*)+\s*</p>',
            '',
            content,
            flags=re.IGNORECASE
        )
        
        # Pattern 3: Remove plain text labels with only citations (no HTML)
        # Matches: "Security Compliance: [2][3]" on its own line
        content = re.sub(
            r'^[A-Z][^:\n]{2,50}:\s*(?:\[\d+\]\s*)+$',
            '',
            content,
            flags=re.MULTILINE
        )
        
        # Pattern 3a: Remove standalone labels in list items (AGGRESSIVE)
        # Matches: <li>Label: [N][M]</li> or <li><strong>Label:</strong> [N]</li>
        content = re.sub(
            r'<li>\s*(?:<strong>)?[^<:]+:(?:</strong>)?\s*(?:\[\d+\]\s*)+\s*</li>',
            '',
            content,
            flags=re.IGNORECASE
        )
        
        # Pattern 3b: Remove multi-word standalone labels (AGGRESSIVE)  
        # Matches: "Essential Tooling Checklist: [2][3]" or "IDE-Integrated SAST: [2][3]"
        # Works even with hyphens, spaces, and capital letters
        content = re.sub(
            r'\n\s*([A-Z][A-Za-z\s\-]{3,50}):\s*(?:\[\d+\]\s*)+\s*\n',
            '\n',
            content
        )
        
        # Pattern 3c: Remove labels immediately after paragraph tags
        # Matches: <p>Label: [N]</p> or <p>Multi Word Label: [N][M]</p>
        content = re.sub(
            r'<p>\s*([A-Z][^:<]{2,50}):\s*(?:\[\d+\]\s*)+\s*</p>',
            '',
            content,
            flags=re.IGNORECASE
        )
        
        # Pattern 4: Remove empty or near-empty paragraphs
        # Matches: <p></p> or <p>   </p> or <p>.</p> or <p>,</p> or <p>. Also,,</p>
        content = re.sub(
            r'<p>\s*[.,;:\s]+\s*</p>',
            '',
            content
        )
        
        # Pattern 5: Standardize internal links to /magazine/ format
        # Matches: <a href="/slug"> or <a href="/blog/slug"> but NOT <a href="/magazine/
        # Also NOT <a href="http or <a href="#
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
                new_href = f'/magazine/{href}'
            
            return full_tag.replace(f'href="{href}"', f'href="{new_href}"')
        
        # Apply internal link standardization
        content = re.sub(
            r'<a\s+href="([^"]+)"([^>]*)>',
            fix_internal_link,
            content
        )
        
        # Pattern 6: Remove duplicate consecutive paragraphs (exact duplicates)
        lines = content.split('\n')
        deduped = []
        prev_line = None
        for line in lines:
            if line.strip() != prev_line:
                deduped.append(line)
                prev_line = line.strip()
        content = '\n'.join(deduped)
        
        # Pattern 7: Clean up multiple consecutive newlines
        content = re.sub(r'\n{3,}', '\n\n', content)
        
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
