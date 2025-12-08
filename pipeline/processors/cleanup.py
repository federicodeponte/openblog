"""
Content Cleanup & Sanitization Processors

Maps to v4.1 Phase 9, Steps 29-31:
- Step 29: prepare_variable_names-and-clean
- Step 30: output_sanitizer
- Step 31: normalise-output2

Handles:
- HTML cleaning and normalization
- XSS sanitization (bleach)
- HTML validation (BeautifulSoup)
- Markdown removal
- Broken link fixing
- Invisible character removal
- Section combining
"""

import re
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# Try to import sanitization libraries (optional dependencies)
try:
    import bleach
    BLEACH_AVAILABLE = True
except ImportError:
    logger.warning("bleach not installed - XSS sanitization disabled")
    BLEACH_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    logger.warning("beautifulsoup4 not installed - HTML validation disabled")
    BS4_AVAILABLE = False


class HTMLCleaner:
    """Clean and normalize HTML content."""

    @staticmethod
    def clean_html(html: str) -> str:
        """
        Clean HTML content.

        Args:
            html: HTML string to clean

        Returns:
            Cleaned HTML
        """
        if not html or not isinstance(html, str):
            return ""

        # Remove duplicate h1s (keep first)
        html = HTMLCleaner._remove_duplicate_h1(html)

        # Convert h1 to h2 (articles should not have multiple h1s)
        html = html.replace("<h1>", "<h2>", 1)
        html = html.replace("</h1>", "</h2>", 1)

        # Remove markdown bold
        html = re.sub(r"\*\*(.+?)\*\*", r"\1", html)

        # Fix double closing tags (CRITICAL BUG FIX)
        # Handle cases with/without whitespace: </p></p> or </p> </p>
        html = re.sub(r'</p>\s*</p>', '</p>', html)
        html = re.sub(r'</p>\s*<p>', '</p><p>', html)  # Fix spacing between paragraphs

        # Fix orphaned tags
        html = HTMLCleaner._fix_orphaned_tags(html)

        return html.strip()

    @staticmethod
    def _remove_duplicate_h1(html: str) -> str:
        """Remove duplicate h1 tags, keep only first."""
        h1_count = 0
        result = []

        for line in html.split("\n"):
            if "<h1>" in line.lower():
                h1_count += 1
                if h1_count > 1:
                    # Skip duplicate h1s
                    continue
            result.append(line)

        return "\n".join(result)

    @staticmethod
    def _fix_orphaned_tags(html: str) -> str:
        """Fix orphaned/unclosed HTML tags."""
        # Fix double closing tags (additional check, handle whitespace)
        html = re.sub(r'</p>\s*</p>', '</p>', html)
        
        # CRITICAL FIX: Merge <strong> tags that appear right after </p> back into previous paragraph
        # This fixes the issue where keywords are wrapped in <strong> but placed in new <p> tags
        # Example: "<p>text </p><p><strong>keyword</strong></p>" → "<p>text <strong>keyword</strong></p>"
        # Pattern 1: </p><p><strong>keyword</strong></p> → merge into previous paragraph
        # This pattern finds </p> followed by <p><strong>keyword</strong></p> and merges them
        html = re.sub(r'</p>\s*<p>\s*<strong>([^<]+)</strong>\s*</p>', r' <strong>\1</strong></p>', html)
        # Pattern 2: </p><strong>keyword</strong> (not followed by </p>) → merge into previous paragraph
        html = re.sub(r'</p>\s*<strong>([^<]+)</strong>(?!</p>)', r' <strong>\1</strong></p>', html)
        # Pattern 3: </p><strong>keyword</strong></p> → merge into previous paragraph
        html = re.sub(r'</p>\s*<strong>([^<]+)</strong>\s*</p>', r' <strong>\1</strong></p>', html)
        
        # Fix <strong> tags without proper <p> wrapping (only for truly standalone tags)
        # Pattern: <strong>...</strong> without <p> and NOT immediately after </p>
        # This only wraps tags that are truly orphaned, not ones that should be merged
        html = re.sub(r'(?<!</p>)(?<!<p>)<strong>([^<]+)</strong>(?!</p>)', r'<p><strong>\1</strong></p>', html)
        
        # Fix common unclosed tags
        # NOTE: Skip the <p> tag fix pattern as it can create double closing tags
        # The double closing tag fix above should handle this
        tag_fixes = [
            # Removed: (r"<p([^>]*)>(?!</p>)([^<]+)(?=<[^>]*>)", r"<p\1>\2</p>"),
            # This pattern was causing double closing tags
            (r"<div([^>]*)>(?!</div>)", r"<div\1>"),
            (r"(?<!</li>)\n(?=<li)", r"</li>\n"),
        ]

        for pattern, replacement in tag_fixes:
            html = re.sub(pattern, replacement, html)

        return html

    @staticmethod
    def sanitize(html: str) -> str:
        """
        Sanitize HTML content (Step 30: output_sanitizer).
        
        Now includes:
        - XSS protection (bleach)
        - HTML validation (BeautifulSoup)
        - Entity encoding
        - Markdown cleanup

        Args:
            html: HTML to sanitize

        Returns:
            Sanitized HTML
        """
        if not html or not isinstance(html, str):
            return ""

        # 1. XSS sanitization with bleach (if available)
        if BLEACH_AVAILABLE:
            html = HTMLCleaner._sanitize_xss(html)

        # 2. HTML validation with BeautifulSoup (if available)
        if BS4_AVAILABLE:
            html = HTMLCleaner._validate_html(html)

        # 3. Remove remaining markdown bold
        html = re.sub(r"\*\*(.+?)\*\*", r"\1", html)

        # 4. Clean bracketed content (keep citations [1], remove notes)
        html = HTMLCleaner._clean_brackets(html)

        # 5. Fix broken href
        html = re.sub(r'href="\s*"', "", html)
        html = re.sub(r"href='\\s*'", "", html)

        # 6. Remove invisible characters (zero-width spaces, etc)
        zero_width_chars = [
            "\u200b",  # Zero-width space
            "\u200c",  # Zero-width non-joiner
            "\u200d",  # Zero-width joiner
            "\u200e",  # Left-to-right mark
            "\u200f",  # Right-to-left mark
            "\ufeff",  # Zero-width no-break space
        ]

        for char in zero_width_chars:
            html = html.replace(char, "")

        return html.strip()
    
    @staticmethod
    def _sanitize_xss(html: str) -> str:
        """
        Sanitize HTML to prevent XSS attacks using bleach.
        
        Args:
            html: HTML to sanitize
            
        Returns:
            XSS-safe HTML
        """
        if not BLEACH_AVAILABLE:
            logger.warning("bleach not available - skipping XSS sanitization")
            return html
        
        # Allowed tags for blog content
        allowed_tags = [
            'p', 'br', 'strong', 'em', 'u', 'b', 'i',
            'a', 'ul', 'ol', 'li',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'blockquote', 'code', 'pre',
            'table', 'thead', 'tbody', 'tr', 'th', 'td',
            'cite',  # For citations
        ]
        
        # Allowed attributes
        allowed_attrs = {
            'a': ['href', 'title', 'target', 'rel', 'aria-label', 'itemprop'],
            'cite': [],
        }
        
        # Allowed protocols for href
        allowed_protocols = ['http', 'https', 'mailto']
        
        try:
            clean_html = bleach.clean(
                html,
                tags=allowed_tags,
                attributes=allowed_attrs,
                protocols=allowed_protocols,
                strip=True,  # Strip disallowed tags instead of escaping
            )
            return clean_html
        except Exception as e:
            logger.error(f"bleach sanitization failed: {e}")
            return html
    
    @staticmethod
    def _validate_html(html: str) -> str:
        """
        Validate and fix HTML structure using BeautifulSoup.
        
        Auto-fixes:
        - Unclosed tags
        - Invalid nesting
        - Malformed structure
        
        Args:
            html: HTML to validate
            
        Returns:
            Valid HTML
        """
        if not BS4_AVAILABLE:
            logger.warning("BeautifulSoup not available - skipping HTML validation")
            return html
        
        try:
            # Parse with lxml (strict) or html.parser (fallback)
            try:
                soup = BeautifulSoup(html, 'lxml')
            except:
                soup = BeautifulSoup(html, 'html.parser')
            
            # Get body content only (removes auto-added html/body tags)
            if soup.body:
                return str(soup.body)[6:-7]  # Remove <body> and </body>
            else:
                return str(soup)
        except Exception as e:
            logger.error(f"BeautifulSoup validation failed: {e}")
            return html

    @staticmethod
    def _clean_brackets(html: str) -> str:
        """
        Clean bracketed content.

        Keep valid citations [1], [2], etc.
        Remove notes and invalid brackets.
        """
        # Keep valid citations [n]
        def is_valid_citation(match):
            content = match.group(1)
            # Check if it's a number or comma-separated numbers
            if re.match(r"^\d+(?:,\s*\d+)*$", content):
                return match.group(0)  # Keep valid citations
            return match.group(1)  # Remove brackets for notes

        html = re.sub(r"\[([^\]]+)\]", is_valid_citation, html)

        # Remove empty brackets
        html = re.sub(r"\[\s*\]", "", html)

        return html

    @staticmethod
    def normalize(html: str) -> str:
        """
        Normalize HTML content (Step 31: normalise-output2).

        Args:
            html: HTML to normalize

        Returns:
            Normalized HTML
        """
        if not html or not isinstance(html, str):
            return ""

        # Normalize line breaks (max 2 consecutive)
        html = re.sub(r"\n{3,}", "\n\n", html)

        # Normalize indentation
        html = re.sub(r"^\s+", "", html, flags=re.MULTILINE)

        # Ensure UTF-8 encoding (handle encoding issues)
        try:
            html = html.encode("utf-8", errors="replace").decode("utf-8")
        except Exception:
            pass

        return html.strip()


class SectionCombiner:
    """Combine article sections into single content."""

    @staticmethod
    def combine_sections(structured_data: Any) -> str:
        """
        Combine section_01_content through section_09_content into single HTML content.

        Args:
            structured_data: ArticleOutput with section fields

        Returns:
            Combined HTML content with h2 headers and content
        """
        content_parts = []

        # Add headline as h1
        if hasattr(structured_data, "Headline") and structured_data.Headline:
            content_parts.append(f"<h1>{structured_data.Headline}</h1>")

        # Add intro
        if hasattr(structured_data, "Intro") and structured_data.Intro:
            content_parts.append(f"<p>{structured_data.Intro}</p>")

        # Add sections 1-9
        for i in range(1, 10):
            title_attr = f"section_{i:02d}_title"
            content_attr = f"section_{i:02d}_content"

            title = getattr(structured_data, title_attr, None)
            content = getattr(structured_data, content_attr, None)

            if title and title.strip():
                content_parts.append(f"<h2>{title}</h2>")

            if content and content.strip():
                content_parts.append(content)

        return "\n".join(content_parts)

    @staticmethod
    def extract_sections(content: str) -> Dict[str, str]:
        """
        Extract sections from combined HTML content.

        Args:
            content: Combined HTML content

        Returns:
            Dictionary mapping section numbers to content
        """
        sections = {}

        # Parse h2 headers and following content
        h2_pattern = r"<h2>([^<]+)</h2>(.*?)(?=<h2>|$)"
        matches = re.findall(h2_pattern, content, re.DOTALL)

        for idx, (title, content_text) in enumerate(matches, 1):
            section_num = f"{idx:02d}"
            sections[f"section_{section_num}_title"] = title.strip()
            sections[f"section_{section_num}_content"] = content_text.strip()

        return sections


class DataMerger:
    """Merge structured data with parallel results."""

    @staticmethod
    def merge_all_results(
        structured_data: Any,
        parallel_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Merge all article components into single validated article.

        Args:
            structured_data: ArticleOutput
            parallel_results: Results from stages 4-9

        Returns:
            Merged article dictionary
        """
        # Start with structured data
        merged = structured_data.model_dump() if hasattr(structured_data, "model_dump") else {}

        # Add metadata
        if "metadata" in parallel_results:
            metadata = parallel_results["metadata"]
            if isinstance(metadata, dict):
                merged.update(metadata)

        # Add image
        if "image_url" in parallel_results:
            merged["image_url"] = parallel_results["image_url"]
        if "image_alt_text" in parallel_results:
            merged["image_alt_text"] = parallel_results["image_alt_text"]

        # Add ToC
        if "toc_dict" in parallel_results:
            merged["toc"] = parallel_results["toc_dict"]

        # Add FAQ items
        if "faq_items" in parallel_results:
            faq_list = parallel_results["faq_items"]
            if hasattr(faq_list, "to_dict_list"):
                merged["faq_items"] = faq_list.to_dict_list()

        # Add PAA items
        if "paa_items" in parallel_results:
            paa_list = parallel_results["paa_items"]
            if hasattr(paa_list, "to_dict_list"):
                merged["paa_items"] = paa_list.to_dict_list()

        # Add HTML sections
        if "citations_html" in parallel_results:
            merged["citations_html"] = parallel_results["citations_html"]
        if "internal_links_html" in parallel_results:
            merged["internal_links_html"] = parallel_results["internal_links_html"]

        return merged
