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
        
        # CRITICAL FIX: Initialize URL link counter to limit each URL to max 2 links per article
        url_link_count = {}
        # Store it in article temporarily so _build_content can access it
        article["_url_link_count"] = url_link_count
        
        # Get citation_map for intro linkification
        citation_map = article.get("_citation_map", {})
        if not citation_map:
            # Try to parse from Sources field as fallback
            sources = article.get("Sources", "")
            citation_map = HTMLRenderer._parse_sources_for_map(sources)
            if citation_map:
                article["_citation_map"] = citation_map
        
        content = HTMLRenderer._build_content(article)
        meta_desc = HTMLRenderer._strip_html(article.get("Meta_Description", ""))  # ✅ CRITICAL FIX: Strip HTML
        meta_title = HTMLRenderer._strip_html(article.get("Meta_Title", headline))  # ✅ CRITICAL FIX: Strip HTML
        
        # Extract and convert image URLs to absolute
        # Handle cases where image URLs might be dicts (from failed graphics generation)
        image_url_raw = article.get("image_url", "")
        image_url = HTMLRenderer._make_absolute_url(image_url_raw if isinstance(image_url_raw, str) else "", company_url)
        image_alt = article.get("image_alt_text", "")
        
        # Mid and bottom images already converted in _build_content
        mid_image_url_raw = article.get("mid_image_url", "")
        mid_image_url = HTMLRenderer._make_absolute_url(mid_image_url_raw if isinstance(mid_image_url_raw, str) else "", company_url)
        mid_image_alt = article.get("mid_image_alt", "")
        bottom_image_url_raw = article.get("bottom_image_url", "")
        bottom_image_url = HTMLRenderer._make_absolute_url(bottom_image_url_raw if isinstance(bottom_image_url_raw, str) else "", company_url)
        bottom_image_alt = article.get("bottom_image_alt", "")
        
        sources = article.get("Sources", "")
        # CRITICAL FIX: Use validated citation_map if available (from stage_10_ai_cleanup)
        # This ensures only valid citations are included (invalid 404 URLs filtered out)
        citation_map = article.get("_citation_map", {})
        if not citation_map:
            # Fallback: Parse from Sources field if citation_map not set
            citation_map = HTMLRenderer._parse_sources(sources)
        if citation_map:
            logger.info(f"✅ Citation map used in render() with {len(citation_map)} entries")
        else:
            logger.warning(f"⚠️  No citation map available (Sources length: {len(sources)})")
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
                # CRITICAL FIX: Pass validated citations to schema generator
                # Get validated CitationList from article dict (set in stage_10_ai_cleanup)
                validated_citations = article.get("_validated_citations_list")
                
                schemas = generate_all_schemas(
                    output=article_output,
                    company_data=company_data,
                    article_url=article_url,
                    base_url=base_url,
                    faq_items=faq_items,
                    validated_citations=validated_citations,
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

        {f'<div class="intro">{HTMLRenderer._linkify_citations(intro, citation_map, url_link_count)}</div>' if intro else ''}

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
        
        # Parse sources to get citation map if not already present (fallback)
        if "_citation_map" not in article:
            sources = article.get("Sources", "")
            citation_map = HTMLRenderer._parse_sources_for_map(sources)
            if citation_map:
                article["_citation_map"] = citation_map
                logger.info(f"✅ Created citation_map from Sources field with {len(citation_map)} entries")
            else:
                logger.warning(f"⚠️  No citation_map available (Sources length: {len(sources)})")
                logger.warning(f"    Citations will remain as #source-N anchors")
        
        # CRITICAL FIX: Get URL link counter from article (initialized in render method)
        url_link_count = article.get("_url_link_count", {})  # Track how many times each URL has been linked
        
        # Extract and convert images to absolute URLs
        # Handle cases where image URLs might be dicts (from failed graphics generation)
        mid_image_url_raw = article.get("mid_image_url", "")
        mid_image_url = HTMLRenderer._make_absolute_url(mid_image_url_raw if isinstance(mid_image_url_raw, str) else "", company_url)
        mid_image_alt = article.get("mid_image_alt", "")
        bottom_image_url_raw = article.get("bottom_image_url", "")
        bottom_image_url = HTMLRenderer._make_absolute_url(bottom_image_url_raw if isinstance(bottom_image_url_raw, str) else "", company_url)
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
                # First clean up useless patterns
                content_clean = HTMLRenderer._cleanup_content(content)
                # Then convert citation markers to clickable links
                # Get citation_map from article if available
                citation_map = article.get("_citation_map", {})
                if citation_map:
                    logger.debug(f"Using citation_map with {len(citation_map)} entries for section {i}")
                else:
                    logger.warning(f"⚠️  No citation_map available for section {i}, links will be anchor-only")
                content_with_links = HTMLRenderer._linkify_citations(content_clean, citation_map, url_link_count)
                parts.append(content_with_links)
            
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
        """
        Render citations section with clickable links to source URLs.
        
        Parses Sources field and renders each citation as a clickable link
        pointing to the actual source page URL.
        """
        if not sources or not sources.strip():
            return ""

        lines = [line.strip() for line in sources.split("\n") if line.strip()]
        if not lines:
            return ""

        items_html = []
        # Pattern: [N]: URL – Description
        pattern = r'\[(\d+)\]:\s*(https?://[^\s]+)\s*[–-]\s*(.+?)(?=\n\[|\n*$)'
        
        for line in lines:
            match = re.match(pattern, line, re.MULTILINE | re.DOTALL)
            if match:
                num_str = match.group(1)
                url = match.group(2).strip()
                description = match.group(3).strip()
                
                # Clean description of any HTML tags before escaping
                clean_description = re.sub(r'<[^>]+>', '', description)  # Remove any HTML tags
                clean_description = re.sub(r'&[^;]+;', '', clean_description)  # Remove HTML entities
                clean_description = clean_description.strip()
                
                # Create clickable link to the actual source URL
                link_html = f'<a href="{HTMLRenderer._escape_attr(url)}" target="_blank" rel="noopener noreferrer">{HTMLRenderer._escape_html(clean_description)}</a>'
                items_html.append(f'<li id="source-{num_str}">{link_html}</li>')
            else:
                # Fallback: if format doesn't match, render as-is (escaped)
                items_html.append(f"<li>{HTMLRenderer._escape_html(line)}</li>")

        return f"""<section class="citations">
            <h2>Sources</h2>
            <ol>
                {''.join(items_html)}
            </ol>
        </section>"""

    @staticmethod
    def _escape_html(text: str) -> str:
        """
        Escape HTML special characters.
        
        CRITICAL FIX: Decode existing HTML entities first to prevent double encoding.
        This ensures that if text already contains &amp;, it becomes & (decoded),
        then gets properly escaped to &amp; (not &amp;amp;).
        """
        if not text:
            return ""
        
        # Decode existing HTML entities first to prevent double encoding
        import html
        try:
            # Decode entities like &amp; → &, &lt; → <, etc.
            text = html.unescape(str(text))
        except Exception:
            # If unescape fails, use text as-is
            text = str(text)
        
        # Now escape normally (this will properly encode plain & to &amp;)
        return (
            text
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
    def _parse_sources(sources: str) -> Dict[int, str]:
        """
        Parse Sources field to extract citation number -> URL mapping.
        
        Format expected: [1]: https://example.com/page – Description text
        Also handles: [1]: https://example.com/page - Description text (hyphen)
        Also handles: [1]: https://example.com/page Description text (no separator)
        
        Args:
            sources: Raw sources string from article
            
        Returns:
            Dict mapping citation number to URL
        """
        if not sources:
            logger.debug("No sources provided to _parse_sources")
            return {}
        
        citation_map = {}
        
        # Try multiple patterns to handle different formats
        patterns = [
            # Pattern 1: [N]: URL – Description (em dash)
            r'\[(\d+)\]:\s*(https?://[^\s]+)\s*[–-]\s*(.+?)(?=\n\[|\n*$)',
            # Pattern 2: [N]: URL - Description (hyphen)
            r'\[(\d+)\]:\s*(https?://[^\s]+)\s*-\s*(.+?)(?=\n\[|\n*$)',
            # Pattern 3: [N]: URL Description (no separator, URL ends at space)
            r'\[(\d+)\]:\s*(https?://[^\s]+)\s+(.+?)(?=\n\[|\n*$)',
            # Pattern 4: [N]: URL (just URL, no description)
            r'\[(\d+)\]:\s*(https?://[^\s]+)(?=\n\[|\n*$)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, sources, re.MULTILINE | re.DOTALL)
            for match in matches:
                try:
                    num_str = match[0]
                    url = match[1].strip()
                    num = int(num_str)
                    if url and url.startswith(('http://', 'https://')):
                        citation_map[num] = url
                        logger.debug(f"Parsed citation [{num}]: {url}")
                except (ValueError, IndexError) as e:
                    logger.debug(f"Failed to parse citation match: {match}, error: {e}")
                    continue
        
        if citation_map:
            logger.info(f"✅ Parsed {len(citation_map)} citations from Sources field")
        else:
            logger.warning(f"⚠️  No citations parsed from Sources field (length: {len(sources)} chars)")
            # Log first 200 chars for debugging
            if sources:
                logger.debug(f"Sources preview: {sources[:200]}")
        
        return citation_map

    @staticmethod
    def _linkify_citations(content: str, citation_map: Optional[Dict[int, str]] = None, url_link_count: Optional[Dict[str, int]] = None) -> str:
        """
        Convert citation markers [1], [2], [3] into clickable links.
        
        Also converts existing anchor links (#source-N) to actual URLs.
        If citation_map is provided, links point to actual source URLs.
        Otherwise, falls back to anchor links (#source-N).
        
        CRITICAL: Limits each URL to maximum 2 hyperlinks per article to avoid over-linking.
        
        Args:
            content: HTML content with citation markers
            citation_map: Optional dict mapping citation number to URL
            url_link_count: Optional dict tracking how many times each URL has been linked (mutated in-place)
        """
        import re
        if not content:
            return ""
        
        # Initialize URL link counter if not provided
        if url_link_count is None:
            url_link_count = {}
        
        # First, convert existing anchor links (#source-N) to real URLs if citation_map is available
        if citation_map:
            logger.debug(f"_linkify_citations: citation_map provided with {len(citation_map)} entries")
            converted_count = 0
            
            def replace_anchor_link(match):
                nonlocal converted_count
                full_match = match.group(0)  # Full <a> tag
                num_str = match.group(1)  # The number from #source-N
                link_text = match.group(2).strip()  # Link text content
                
                try:
                    num = int(num_str)
                    if num in citation_map:
                        url = citation_map[num]
                        
                        # CRITICAL FIX: Limit each URL to maximum 2 links per article
                        current_count = url_link_count.get(url, 0)
                        if current_count >= 2:
                            # Already linked 2 times, remove the link but keep the text
                            logger.debug(f"URL {url} already linked {current_count} times, removing link")
                            return link_text  # Return just the text without link
                        
                        # Increment link count for this URL
                        url_link_count[url] = current_count + 1
                        converted_count += 1
                        logger.debug(f"Converting #source-{num} to {url} (link count: {url_link_count[url]})")
                        
                        # Extract existing attributes from the original tag
                        # Get the opening tag portion
                        tag_match = re.search(r'<a\s+([^>]+)>', full_match)
                        existing_attrs = tag_match.group(1) if tag_match else ""
                        
                        # Preserve class if present, otherwise add citation class
                        if 'class=' in existing_attrs:
                            # Extract class value
                            class_match = re.search(r'class=["\']([^"\']+)["\']', existing_attrs)
                            if class_match:
                                class_value = class_match.group(1)
                                # Build new attributes, keeping class and adding target/rel
                                attrs_parts = [f'class="{class_value}"']
                            else:
                                attrs_parts = ['class="citation"']
                        else:
                            attrs_parts = ['class="citation"']
                        
                        # Always add target and rel for external links
                        attrs_parts.extend(['target="_blank"', 'rel="noopener noreferrer"'])
                        
                        attrs_str = ' '.join(attrs_parts)
                        return f'<a href="{HTMLRenderer._escape_attr(url)}" {attrs_str}>{link_text}</a>'
                    else:
                        logger.debug(f"Citation {num} not found in citation_map (available: {list(citation_map.keys())})")
                except (ValueError, KeyError, AttributeError) as e:
                    logger.debug(f"Error converting anchor link: {e}")
                    pass
                return full_match  # Return original if no conversion possible
            
            # Match <a href="#source-N" ...>text</a> patterns
            # Group 1: number from #source-N, Group 2: other attrs (may include class, etc.), Group 3: link text
            # This pattern handles attributes in any order and with any quoting style
            content = re.sub(
                r'<a\s+[^>]*?href=["\']#source-(\d+)["\'][^>]*?>(.*?)</a>',
                replace_anchor_link,
                content,
                flags=re.IGNORECASE | re.DOTALL
            )
            
            if converted_count > 0:
                logger.info(f"✅ Converted {converted_count} anchor links to real URLs")
            else:
                logger.warning(f"⚠️  No anchor links converted (citation_map had {len(citation_map)} entries)")
        else:
            logger.warning("⚠️  _linkify_citations called without citation_map - links will remain as anchors")
        
        # Then, convert standalone [N] markers to links
        # CRITICAL FIX: Exclude [N] markers that are already inside <a> tags to prevent nested links
        def replace_citation(match):
            num_str = match.group(1)
            start_pos = match.start()
            # Check if this [N] is inside an <a> tag by looking backwards
            text_before = content[:start_pos]
            # Find the last <a> tag before this position
            last_a_open = text_before.rfind('<a')
            last_a_close = text_before.rfind('</a>')
            
            # If there's an <a> tag after the last </a>, we're inside an anchor
            if last_a_open > last_a_close:
                # We're inside an anchor tag, don't convert
                return match.group(0)
            
            try:
                num = int(num_str)
                # Use actual URL if available, otherwise fall back to anchor
                if citation_map and num in citation_map:
                    url = citation_map[num]
                    
                    # CRITICAL FIX: Limit each URL to maximum 2 links per article
                    current_count = url_link_count.get(url, 0)
                    if current_count >= 2:
                        # Already linked 2 times, return plain text without link
                        logger.debug(f"URL {url} already linked {current_count} times, skipping link")
                        return f'[{num}]'  # Return plain text marker
                    
                    # Increment link count for this URL
                    url_link_count[url] = current_count + 1
                    logger.debug(f"Linking citation [{num}] to {url} (link count: {url_link_count[url]})")
                    return f'<a href="{HTMLRenderer._escape_attr(url)}" class="citation" target="_blank" rel="noopener noreferrer">[{num}]</a>'
                else:
                    # CRITICAL FIX: Citation not found in citation_map (was filtered out as invalid)
                    # Return plain text instead of broken anchor link
                    logger.debug(f"Citation [{num}] not in citation_map (filtered out), showing as plain text")
                    return f'[{num}]'  # Plain text, no link
            except ValueError:
                return match.group(0)  # Return original if not a number
        
        # Match [N] where N is one or more digits
        # We'll check inside the replacement function if we're inside an anchor tag
        return re.sub(r'\[(\d+)\]', replace_citation, content)

    @staticmethod
    def _parse_sources_for_map(sources: str) -> Dict[int, str]:
        """
        Parse Sources field to create citation_map (fallback method).
        
        Parses format: [1]: https://example.com – Description
        Returns: {1: "https://example.com", 2: "https://example.org", ...}
        
        Args:
            sources: Sources field string
            
        Returns:
            Dictionary mapping citation number to URL
        """
        import re
        citation_map = {}
        
        if not sources:
            return citation_map
        
        # Parse lines like: [1]: https://example.com – Description
        lines = sources.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Try format: [n]: url – title
            match = re.match(r"\[(\d+)\]:\s*(.+?)\s*[–\-]\s*(.+)", line)
            if match:
                number = int(match.group(1))
                url = match.group(2).strip()
                # CRITICAL FIX: Validate URL before adding
                if url.startswith(("http://", "https://")):
                    # Check for malformed URLs
                    from urllib.parse import urlparse
                    try:
                        parsed = urlparse(url)
                        domain = parsed.netloc.lower()
                        if "." not in domain and domain not in ['localhost']:
                            try:
                                import ipaddress
                                ipaddress.ip_address(domain)
                            except ValueError:
                                logger.warning(f"Skipping invalid URL (missing TLD): {url}")
                                continue
                        citation_map[number] = url
                    except Exception:
                        logger.warning(f"Skipping invalid URL format: {url}")
                        continue
            else:
                # Try simpler format: [n]: url or text with url
                match = re.match(r"\[(\d+)\]:\s*(.+)", line)
                if match:
                    number = int(match.group(1))
                    content = match.group(2).strip()
                    # Extract URL from content
                    url_match = re.search(r"https?://[^\s–\-\)\]\}]+", content)
                    if url_match:
                        url = url_match.group(0).rstrip('.,;:!?)')
                        # CRITICAL FIX: Validate URL before adding
                        if url.startswith(("http://", "https://")):
                            from urllib.parse import urlparse
                            try:
                                parsed = urlparse(url)
                                domain = parsed.netloc.lower()
                                if "." not in domain and domain not in ['localhost']:
                                    try:
                                        import ipaddress
                                        ipaddress.ip_address(domain)
                                    except ValueError:
                                        logger.warning(f"Skipping invalid URL (missing TLD): {url}")
                                        continue
                                citation_map[number] = url
                            except Exception:
                                logger.warning(f"Skipping invalid URL format: {url}")
                                continue
        
        return citation_map

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
        # CRITICAL: Process complete phrases FIRST to avoid leaving orphaned fragments
        
        # Step 3a: Remove complete robotic phrases (entire phrase, not fragments)
        complete_phrase_fixes = [
            # "Here's what matters:" → remove entire phrase including colon
            (r'\bHere\'s what matters\s*:\s*', '', re.IGNORECASE),
            (r'\bHere is what matters\s*:\s*', '', re.IGNORECASE),
            # "Here's how:" → remove entire phrase
            (r'\bHere\'s how\s*:\s*', '', re.IGNORECASE),
            (r'\bHere is how\s*:\s*', '', re.IGNORECASE),
            # "so you can:" → remove entire phrase
            (r'\bso you can\s*:\s*', '', re.IGNORECASE),
            # "if you want:" → remove entire phrase
            (r'\bif you want\s*:\s*', '', re.IGNORECASE),
        ]
        
        for pattern, replacement, flags in complete_phrase_fixes:
            content = re.sub(pattern, replacement, content, flags=flags)
        
        # Step 3b: Remove formulaic transitions (sentence-level, after complete phrases are handled)
        formulaic_fixes = [
            # "Here's how" / "Here's what" phrases (sentence-level)
            # Only apply if NOT followed by "matters:" (already handled above)
            (r'\bHere\'s how\s+(?!matters)', ''),  # "Here's how the market" → "The market"
            (r'\bHere\'s what\s+(?!matters)', ''),  # "Here's what the key is" → "The key is"
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
        
        # STEP 0.1: PRESERVE LIST CONTENT BUT REMOVE ONLY TRULY EMPTY ITEMS
        # After removing citations, only remove list items that are completely empty
        # DO NOT remove items with actual content
        content = re.sub(r'<li>\s*</li>', '', content)  # Only completely empty <li> tags
        content = re.sub(r'<li>\s*[.,;:\-]*\s*</li>', '', content)  # Only punctuation-only items
        # Be more careful with label-only items - only remove if they have no content after the colon
        content = re.sub(r'<li>\s*<strong>[^<]*:</strong>\s*</li>', '', content)  # Label-only items (no content after colon)
        logger.info("🧹 Removed only truly empty list items after citation stripping")
        
        # STEP 0.5: REMOVE EMPTY LABEL PARAGRAPHS (Gemini bug)
        # Matches: <p><strong>GitHub Copilot:</strong></p> (label with NO content after)
        # Matches: <p><strong>Amazon Q Developer:</strong></p>
        content = re.sub(r'<p>\s*<strong>[^<]+:</strong>\s*</p>', '', content)
        logger.info("🧹 Removed empty label paragraphs")
        
        # STEP 0.6: FIX SENTENCE FRAGMENTS AND ORPHANED TEXT - AGGRESSIVE VERSION
        # Gemini splits sentences incorrectly, creating fragments that need to be merged
        
        # Fix fragments at paragraph start - merge short paragraphs with next paragraph
        # Pattern: Short fragments like "In a", "You can", "What is", etc.
        content = re.sub(r'</p>\s*<p>\s*(In a|You can|What is|When you|If you|That\'s why|This is|How to|For example)\s*</p>\s*<p>', r' \1 ', content)  # Remove orphaned short phrases and fix structure
        content = re.sub(r'</p>\s*<p>\s*(In a|You can|What is|When you|If you|That\'s why|This is|How to|For example)\s+', r' \1 ', content)  # Merge short phrases with next text
        
        # Fix truncated sentences at end of paragraphs - more specific patterns
        # Pattern: "That's why trust is e" → remove entirely if incomplete (ends with single letter after space)
        content = re.sub(r'<p>[^<]*\s[a-z]\s*</p>', '', content)  # Remove paragraphs ending with single letter (incomplete)
        content = re.sub(r'\s[a-z]\s*</p>', '</p>', content)  # Remove trailing single letters before closing paragraph
        
        # Fix broken HTML structure after merging
        content = re.sub(r'<p>\s*<p>', '<p>', content)  # Remove double opening paragraph tags
        content = re.sub(r'</p>\s*</p>', '</p>', content)  # Remove double closing paragraph tags
        
        # Fix orphaned punctuation and merge sentences
        content = re.sub(r'</p>\s*<p>\s*([.,;:])\s+([A-Z])', r'\1 \2', content)  # Merge punctuation + capital letter
        content = re.sub(r'</p>\s*<p>\s*([.,;:])', r'\1', content)  # Merge orphaned punctuation
        
        # Fix obvious sentence continuations
        content = re.sub(r'</p>\s*<p>\s*(However|Therefore|Also|Additionally|Furthermore|Moreover|Nevertheless)\b', r'. \1', content)  # Add period before transitions
        content = re.sub(r'</p>\s*<p>\s*(This is why|This means that|This allows|This ensures)\b', r'. \1', content)  # Add period before explanations
        
        # STEP 0.6a: REMOVE UNWANTED KEYWORD BOLDING
        # Remove <strong> tags around keywords that shouldn't be emphasized
        # This prevents keywords from appearing in bold in the final output
        
        # Remove <strong> tags in broken paragraph contexts (orphaned bolded keywords)
        content = re.sub(r'</p>\s*<p>\s*<strong>([^<]+)</strong>\s*</p>', r' \1</p>', content)  # Remove bold, merge text
        content = re.sub(r'</p>\s*<strong>([^<]+)</strong>(?!</p>)', r' \1</p>', content)  # Remove bold, merge text
        content = re.sub(r'</p>\s*<strong>([^<]+)</strong>\s*</p>', r' \1</p>', content)  # Remove bold, merge text
        
        # Also remove standalone <strong> tags around specific keywords that shouldn't be bold
        # Target common keywords that are being inappropriately bolded
        content = re.sub(r'<strong>(zero trust security architecture|SIEM automation|cloud security|DevSecOps)</strong>', r'\1', content, flags=re.IGNORECASE)
        
        logger.info("🔧 Removed unwanted keyword bolding and fixed orphaned bold tags")
        
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
        
        # Pattern 2a: "By so you can building" → "By building"
        # Also fix "By so Building" (capitalized)
        # This happens when multiple phrase injections combine incorrectly
        content = re.sub(r'\bBy so you can (building|implementing|creating|developing|establishing|maintaining)\s+', 
                        lambda m: f'By {m.group(1).capitalize()} ', content, flags=re.IGNORECASE)
        # Also handle "By so Building" (already capitalized)
        content = re.sub(r'\bBy so (Building|Implementing|Creating|Developing|Establishing|Maintaining)\s+', 
                        r'By \1 ', content)
        # Pattern 2b: Fix "By so Building" → "By building" (if lowercase needed)
        content = re.sub(r'\bBy so building\s+', 'By building ', content, flags=re.IGNORECASE)
        
        # Pattern 3: "Here's this reality/scenario/situation" → "This reality/scenario/situation"
        # CRITICAL FIX: Catch "Here's this" in all contexts (not just specific nouns)
        # Matches: "Here's this scenario" → "This scenario"
        # Matches: "Here's this has become" → "This has become"  
        content = re.sub(r"Here's this\s+", r'This ', content, flags=re.IGNORECASE)
        content = re.sub(r"Here's this (reality|scenario|situation)", r'This \1', content, flags=re.IGNORECASE)
        
        # Pattern 4: Double question words "What is How" / "What is Why"
        content = re.sub(r'<h2>What is (How|Why|What|When|Where)\b', r'<h2>\1', content, flags=re.IGNORECASE)
        
        # Pattern 4a: Remove "What is" prefix from section titles that shouldn't be questions
        # Matches: "What is The New Gatekeepers" → "The New Gatekeepers"
        # Only remove if title starts with "The", "Real-World", "Core", etc. (clear statements)
        # Also handle titles with colons: "What is The New Gatekeepers: Gmail" → "The New Gatekeepers: Gmail"
        content = re.sub(
            r'<h2>What is (The|Real-World|Core|Strategic|AI-Driven|Future|Security|Rethinking|Selecting)\s+([^<]+)</h2>',
            r'<h2>\1 \2</h2>',
            content,
            flags=re.IGNORECASE
        )
        
        # Pattern 4b: Fix awkward question titles
        # Matches: "What are the future trends in strategic implementation for the future?" → "Strategic Implementation for the Future"
        content = re.sub(
            r'<h2>What are the future trends in ([^<]+) for the future\?</h2>',
            r'<h2>\1</h2>',
            content,
            flags=re.IGNORECASE
        )
        # Also fix: "What are the future trends in X?" when X already contains "future" or "trends"
        # Also fix: "What are the future trends in outlook: the path forward?" → "Future Outlook: The Path Forward"
        content = re.sub(
            r'<h2>What are the future trends in ([^<]*?(?:future|trend|implementation|strategic|outlook)[^<]*?)\?</h2>',
            lambda m: f'<h2>{m.group(1).strip().title()}</h2>',
            content,
            flags=re.IGNORECASE
        )
        # Pattern 4c: Fix "What is Implementing X?" → "Implementing X"
        # Also fix "What is Selecting X?" → "Selecting X"
        # Also fix "What is Automation at Scale: X?" → "Automation at Scale: X"
        content = re.sub(
            r'<h2>What is (Implementing|Selecting|Building|Creating|Developing|Managing|Optimizing|Automation)([^<]*?)\?</h2>',
            lambda m: f'<h2>{m.group(1)}{m.group(2)}</h2>',
            content,
            flags=re.IGNORECASE
        )
        # Pattern 4f: Fix "How to Governance Frameworks..." → "Governance Frameworks..."
        # Fix broken "How to" conversions
        content = re.sub(
            r'<h2>How to (Governance|Strategic|Compliance|Security)([^<]*?)\?</h2>',
            lambda m: f'<h2>{m.group(1)}{m.group(2)}</h2>',
            content,
            flags=re.IGNORECASE
        )
        # Pattern 4g: Fix "What are the future trends in the future: X?" → "The Future: X"
        # Fix redundant future questions
        content = re.sub(
            r'<h2>What are the future trends in the future:\s*([^<]+)\?</h2>',
            lambda m: f'<h2>The Future: {m.group(1).strip().title()}</h2>',
            content,
            flags=re.IGNORECASE
        )
        
        # Pattern 5: Standalone "matters:" or "so you can:" labels (in own paragraph)
        content = re.sub(r'<p>\s*(matters|so you can|if you want):\s*</p>', '', content, flags=re.IGNORECASE)
        
        # Pattern 6: Orphaned labels in middle of text (CRITICAL FIX for "matters:" issue)
        # Matches: "text. matters: What is..." → "text. What is..."
        # Matches: "text matters: deploying..." → "text deploying..." (with space fix)
        orphaned_label_patterns = [
            # Pattern: sentence end + orphaned label + capital letter (broken sentence)
            (r'([.!?])\s*(matters|so you can|if you want)\s*:\s*([A-Z])', r'\1 \3', re.IGNORECASE),
            # Pattern: orphaned label at start of paragraph
            (r'(<p>)\s*(matters|so you can|if you want)\s*:\s*', r'\1', re.IGNORECASE),
            # Pattern: orphaned label in middle of paragraph (with space before next word)
            (r'\s+(matters|so you can|if you want)\s*:\s+([A-Z])', r' \2', re.IGNORECASE),
            # Pattern: orphaned label followed by "What is" (common broken pattern, same paragraph)
            (r'\s+(matters|so you can|if you want)\s*:\s*What is\s+', r' ', re.IGNORECASE),
            # Pattern: orphaned label followed by "What is" across paragraph boundary
            # "matters:</p><p>What is deploying..." → "</p><p>Deploying..."
            (r'(matters|so you can|if you want)\s*:\s*</p>\s*<p>\s*What is\s+', r'</p><p>', re.IGNORECASE),
        ]
        
        for pattern, replacement, flags in orphaned_label_patterns:
            content = re.sub(pattern, replacement, content, flags=flags)
        
        # Pattern 7: Fix "What is" fragments at start of paragraphs (after orphaned labels removed)
        # "What is deploying these tools effectively requires..." → "Deploying these tools effectively requires..."
        # Only remove if it's clearly a fragment (gerund + verb that makes it ungrammatical as question)
        # Pattern matches: "What is" + gerund + ... + verb (requires/needs/etc) - clearly a fragment
        content = re.sub(
            r'(<p>)\s*What is\s+([a-z]+ing\s+[^<]*?\s+(?:requires?|needs?|means?|involves?|demands?))',
            r'\1\2',
            content,
            flags=re.IGNORECASE
        )
        
        logger.info("🚨 Fixed Gemini hallucination patterns (context loss)")
        
        # STEP 1: Humanize language (remove AI markers)
        content = HTMLRenderer._humanize_content(content)
        
        # Pattern 0: Fix duplicate punctuation (Gemini typos)
        # Matches: ,, or .. or ;; or :: etc.
        # Replace with single punctuation
        content = re.sub(r'([.,;:!?])\1+', r'\1', content)
        
        # Pattern 0a: Fix missing spaces after commas
        # Matches: "flows,capture" → "flows, capture"
        content = re.sub(r'([a-z]),([A-Z])', r'\1, \2', content)
        
        # Pattern 0b: Fix "You can effective" → "Effective"
        content = re.sub(r'\bYou can effective\s+', 'Effective ', content, flags=re.IGNORECASE)
        
        # Pattern 0c: Fix incomplete sentences starting with "A strong"
        content = re.sub(r'<p>\s*A strong\s+([A-Z][^<]+?)\s*</p>', '', content)
        
        # Pattern 0d: Fix "You'll find The top" → "The top" or "Here are the top"
        content = re.sub(r"You'll find The\s+", 'The ', content, flags=re.IGNORECASE)
        
        # Pattern 0e: Fix "real-world implementations validate" → "Real-world implementations validate"
        content = re.sub(r'<p>\s*real-world implementations validate\b', '<p>Real-world implementations validate', content, flags=re.IGNORECASE)
        
        # Pattern 0f: Fix "When you list hygiene" → "List hygiene"
        content = re.sub(r'\bWhen you list hygiene\b', 'List hygiene', content, flags=re.IGNORECASE)
        
        # Pattern 0g: Fix "so you can strategy" → remove broken phrase
        # Also fix "so you can Cloud" → "Cloud"
        content = re.sub(r'\bso you can strategy\b', '', content, flags=re.IGNORECASE)
        content = re.sub(r'\bso you can (Cloud|Security|Identity|Digital|CSPM|CWPP|CNAPP)\s+', r'\1 ', content, flags=re.IGNORECASE)
        
        # Pattern 0h: Fix "This is complete Guide" → "This is a complete Guide"
        content = re.sub(r'\bThis is complete Guide\b', 'This is a complete Guide', content, flags=re.IGNORECASE)
        
        # Pattern 0i: Fix sentence fragments starting with period
        # Matches: "<p>. Also, built-in" → "<p>Also, built-in"
        content = re.sub(r'<p>\s*\.\s+([A-Z])', r'<p>\1', content)
        
        # Pattern 0j: Fix empty paragraphs
        # Matches: <p></p> or <p> </p>
        content = re.sub(r'<p>\s*</p>', '', content)
        
        # Pattern 0k: Fix "You can fragmented" → "Fragmented"
        # Also fix "You can identity" → "Identity"
        content = re.sub(r'\bYou can (fragmented|building|regulatory|successful|effective|modern|traditional|automated|strategic|critical|essential|important|identity|digital|sovereignty|compliance|governance|security)\s+', 
                        lambda m: m.group(1).capitalize() + ' ', content, flags=re.IGNORECASE)
        
        # Pattern 0l: Fix "When you building" → "Building" or "When building"
        # Also fix "When you finally" → "Finally"
        content = re.sub(r'\bWhen you (building|implementing|creating|developing|establishing|maintaining|finally|eventually|ultimately)\s+', 
                        lambda m: m.group(1).capitalize() + ' ', content, flags=re.IGNORECASE)
        # Also fix standalone "When you building" without following word
        content = re.sub(r'\bWhen you building\b', 'Building', content, flags=re.IGNORECASE)
        content = re.sub(r'\bWhen you finally\b', 'Finally', content, flags=re.IGNORECASE)
        
        # Pattern 0m: Fix "That's why however" → "However"
        # Also fix "That's why conversely" → "Conversely"
        content = re.sub(r"That's why (however|conversely|alternatively),?\s+", r'\1, ', content, flags=re.IGNORECASE)
        
        # Pattern 0m2: Fix "You'll find to" → "To"
        content = re.sub(r"\bYou'll find to\s+", 'To ', content, flags=re.IGNORECASE)
        
        # Pattern 0m3: Fix "If you want similarly" → "Similarly"
        content = re.sub(r'\bIf you want (similarly|ultimately|finally|eventually),?\s+', r'\1, ', content, flags=re.IGNORECASE)
        
        # Pattern 0m4: Fix "This is ultimately" → "Ultimately"
        content = re.sub(r'\bThis is (ultimately|finally|eventually),?\s+', r'\1, ', content, flags=re.IGNORECASE)
        
        # Pattern 0m5: Fix "so you can Cloud" → "Cloud"
        content = re.sub(r'\bso you can (Cloud|Security|Identity|Digital)\s+', r'\1 ', content, flags=re.IGNORECASE)
        
        # Pattern 0m6: Fix "That's why handling" → "Handling" or "Navigating"
        # Also fix "That's why navigating" → "Navigating"
        content = re.sub(r'\bThat\'s why (handling|navigating|managing|building|creating)\s+', lambda m: m.group(1).capitalize() + ' ', content, flags=re.IGNORECASE)
        
        # Pattern 0m8: Fix "You can handling" → "Handling" or "Navigating"
        # Also fix "You can navigating" → "Navigating"
        content = re.sub(r'\bYou can (handling|navigating|managing|building|creating)\s+', lambda m: m.group(1).capitalize() + ' ', content, flags=re.IGNORECASE)
        
        # Pattern 0m11: Fix "You'll find selecting" → "Selecting"
        # Also fix other gerunds after "You'll find"
        content = re.sub(r'\bYou\'ll find (selecting|handling|navigating|managing|building|creating)\s+', lambda m: m.group(1).capitalize() + ' ', content, flags=re.IGNORECASE)
        
        # Pattern 0m7: Fix "Here's how beyond" → "Beyond"
        # Also fix other prepositions after "Here's how"
        content = re.sub(r'\bHere\'s how (beyond|within|through|across|during|before|after)\s+', lambda m: m.group(1).capitalize() + ' ', content, flags=re.IGNORECASE)
        
        # Pattern 0n: Fix "If you want regulatory" → "Regulatory" (with capitalization)
        # Also fix "If you want digital" → "Digital"
        content = re.sub(r'\bIf you want (regulatory|strategic|critical|essential|important|modern|traditional|automated|successful|effective|digital|sovereignty|compliance|governance)\s+', 
                        lambda m: m.group(1).capitalize() + ' ', content, flags=re.IGNORECASE)
        
        # Pattern 0n3: Fix "Here's in late" → "In late"
        content = re.sub(r"\bHere's (in|on|at|by|for|with|from|to|of|about)\s+", r'\1 ', content, flags=re.IGNORECASE)
        
        # Pattern 0n2: Fix lowercase sentence starts (e.g., "regulatory pressure" → "Regulatory pressure")
        content = re.sub(r'<p>\s*([a-z])([a-z]+)\s+', lambda m: f'<p>{m.group(1).upper()}{m.group(2)} ', content)
        
        # Pattern 0o: Fix incomplete list items ending with "..."
        # Remove list items that are clearly incomplete (end with "..." or cut off mid-sentence)
        # This is a safety net - ideally list extraction should create complete items
        incomplete_patterns = [
            r'<li>([^<]+)\.\.\.</li>',  # Items ending with "..."
            r'<li>([^<]+)\s+\.\.\.\s*</li>',  # Items with "..." before closing
        ]
        for pattern in incomplete_patterns:
            # Only remove if the item is clearly incomplete (short or ends with incomplete phrase)
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in list(matches):  # Convert to list to avoid modification during iteration
                item_text = match.group(1).strip()
                # Remove if it's clearly incomplete (ends with incomplete word or is very short)
                if len(item_text.split()) < 8 or item_text.endswith(('...', 'toward', 'used', 'that', 'from')):
                    content = content.replace(match.group(0), '', 1)
        
        # Pattern 0p: Fix broken paragraph structure
        # Matches: "</p><p><strong>Cloud Computing Security</strong></p> has evolved"
        # Should be: "</p><p><strong>Cloud Computing Security</strong> has evolved</p>"
        content = re.sub(r'</p>\s*<p><strong>([^<]+)</strong></p>\s+([a-z])', r'</p><p><strong>\1</strong> \2', content, flags=re.IGNORECASE)
        
        # Pattern 0q: Fix "The future of </p><ul>" → complete the sentence
        # Matches incomplete sentences before lists
        content = re.sub(r'<p>The future of\s*</p>\s*<(ul|ol)>', r'<p>The future of cloud computing security lies in strategic integration.</p><\1>', content, flags=re.IGNORECASE)
        
        # Pattern 0r: Remove empty list tags
        # Matches: <ul></ul> or <ol></ol> (lists with no items)
        content = re.sub(r'<(ul|ol)>\s*</\1>', '', content, flags=re.IGNORECASE)
        
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
        
        # Pattern 2a: Remove standalone list introduction labels
        # Matches: <p>Here are key points:</p> or <p>Key benefits include:</p> followed by list
        # CONSERVATIVE FIX: Remove ONLY truly robotic list introductions (preserve meaningful content)
        list_intro_patterns = [
            # Only remove completely generic intros that add zero value
            (r'<p>\s*(?:Key points|Here are the)\s*:?\s*</p>\s*(?=<(?:ul|ol))', ''),
            (r'<p>\s*(?:Important|Key)\s*:?\s*</p>\s*(?=<(?:ul|ol))', ''),  # Single word labels only
        ]
        for pattern, replacement in list_intro_patterns:
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
        
        # Pattern 3: Remove plain text labels with only citations (no HTML)
        # Matches: "Security Compliance: [2][3]" on its own line
        content = re.sub(
            r'^[A-Z][^:\n]{2,50}:\s*(?:\[\d+\]\s*)+$',
            '',
            content,
            flags=re.MULTILINE
        )
        
        # Pattern 3a: Remove ONLY citation-only list items (CONSERVATIVE)
        # Only remove list items that contain NOTHING but a label and citations
        # Preserve items with actual content after the colon
        content = re.sub(
            r'<li>\s*(?:<strong>)?[^<:]{1,15}:(?:</strong>)?\s*(?:\[\d+\]\s*)+\s*</li>',  # Short labels only
            '',
            content,
            flags=re.IGNORECASE
        )
        
        # Pattern 3b: Remove ONLY obvious citation-only labels (CONSERVATIVE)  
        # Only match very specific patterns that are clearly citation-only
        # Be much more conservative to avoid removing legitimate content
        content = re.sub(
            r'\n\s*([A-Z][A-Za-z\s]{3,20}):\s*(?:\[\d+\]\s*){2,}\s*\n',  # Only if 2+ citations and short label
            '\n',
            content
        )
        
        # Pattern 3c: Remove ONLY short citation-only paragraphs (CONSERVATIVE)
        # Only remove paragraphs that contain NOTHING but a short label and citations
        content = re.sub(
            r'<p>\s*([A-Z][^:<]{2,15}):\s*(?:\[\d+\]\s*){2,}\s*</p>',  # Only short labels with 2+ citations
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
        
        # Pattern 6a: Remove list items that duplicate paragraph content verbatim
        # This prevents lists from being exact copies of preceding paragraphs
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', content, re.DOTALL)
        list_items = re.findall(r'<li[^>]*>(.*?)</li>', content, re.DOTALL)
        
        for li in list_items:
            li_text = re.sub(r'<[^>]+>', '', li).strip()
            # Check if list item text appears verbatim in any paragraph
            for para in paragraphs:
                para_text = re.sub(r'<[^>]+>', '', para).strip()
                # Only remove list items that are EXACT duplicates (very conservative)
                if li_text and para_text:
                    # Only remove if it's an exact match or the list item is completely contained in paragraph
                    if li_text.lower().strip() == para_text.lower().strip() or (li_text.lower() in para_text.lower() and len(li_text.split()) < 5):
                        # Remove this list item (only very short exact matches)
                        content = content.replace(f'<li>{li}</li>', '', 1)
                        logger.debug(f"Removed exact duplicate list item: {li_text[:50]}...")
                        break
        
        # Pattern 7: Clean up multiple consecutive newlines
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # STEP 7.5: FIX CAPITALIZATION AFTER LISTS (CRITICAL)
        # After closing list tags (</ul> or </ol>), paragraphs should start with capital letters
        # Pattern: </ul> or </ol> followed by <p> with lowercase first letter
        def capitalize_after_list(match):
            list_close = match.group(1)  # </ul> or </ol>
            p_tag = match.group(2)  # <p> or <p ...>
            first_char = match.group(3)  # First character of paragraph content
            rest = match.group(4)  # Rest of paragraph content
            
            # Only capitalize if first char is lowercase letter
            if first_char.islower():
                return f"{list_close}{p_tag}{first_char.upper()}{rest}"
            return match.group(0)  # Return unchanged if already capitalized
        
        # Match: </ul> or </ol> followed by <p> with optional attributes, then lowercase letter
        content = re.sub(
            r'(</(?:ul|ol)>)\s*(<p[^>]*>)\s*([a-z])([^<]*)',
            capitalize_after_list,
            content,
            flags=re.MULTILINE
        )
        logger.info("🔤 Fixed capitalization after list tags")
        
        # STEP 8: Convert <ul> to <ol> when context suggests numbered lists
        # This fixes cases like "5 best tools" where the list should be numbered
        # Look for patterns like: "X best", "top X", "X ways", "X steps", "X things", etc.
        # in the text before a <ul> list and convert it to <ol>
        numbered_list_patterns = [
            r'\b\d+\s+(?:best|top|leading|top-rated)\s+',  # "5 best tools", "top 3"
            r'\b(?:best|top|leading)\s+\d+\s+',  # "best 5 tools", "top 3"
            r'\b\d+\s+(?:ways?|steps?|things?|items?|points?|strategies?|tips?|methods?|approaches?|solutions?|options?|tools?|platforms?|services?|features?|benefits?|advantages?|factors?|considerations?|criteria?|requirements?|guidelines?|practices?|techniques?|examples?|cases?|scenarios?)\b',  # "5 ways", "3 steps", "10 things"
            r'\b(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\s+',  # "first 5", "second 3"
            r'\b(?:number|#)\s*\d+\s*[:.]',  # "number 5:", "#3:"
        ]
        
        # Match complete <ul>...</ul> blocks and convert if needed
        def convert_list_if_numbered(match):
            full_list = match.group(0)
            # Get context before the list (look back up to 300 characters)
            start_pos = match.start()
            context_start = max(0, start_pos - 300)
            context = content[context_start:start_pos].lower()
            
            # Remove HTML tags from context for pattern matching
            context_text = re.sub(r'<[^>]+>', ' ', context)
            context_text = re.sub(r'\s+', ' ', context_text)
            
            # Check if any numbered list pattern matches
            for pattern in numbered_list_patterns:
                if re.search(pattern, context_text):
                    # Convert entire list from <ul> to <ol>
                    logger.debug(f"Converting <ul> to <ol> based on pattern: {pattern}")
                    return full_list.replace('<ul>', '<ol>').replace('</ul>', '</ol>')
            
            return full_list
        
        # Match complete <ul>...</ul> blocks and convert if needed
        content = re.sub(r'<ul>(.*?)</ul>', convert_list_if_numbered, content, flags=re.DOTALL)
        
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
