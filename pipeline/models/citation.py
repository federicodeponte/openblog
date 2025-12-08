"""
Citation Model

Represents a single citation/source in the article.

Structure:
- Number: Citation index [1], [2], etc.
- URL: Source URL
- Title: Short title/description of source
- HTML: Formatted HTML output
"""

from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl, field_validator
import logging

logger = logging.getLogger(__name__)


class Citation(BaseModel):
    """
    Single citation/source reference.

    Attributes:
        number: Citation index (1, 2, 3, ...)
        url: Source URL
        title: Citation title/description (8-15 words as per v4.1)
        accessed_date: Optional: date accessed
    """

    number: int = Field(..., description="Citation number [1], [2], etc.", ge=1, le=999)
    url: str = Field(..., description="Source URL")
    title: str = Field(..., description="Short citation title (8-15 words)")
    accessed_date: Optional[str] = Field(default="", description="Date accessed (YYYY-MM-DD)")

    @field_validator("title")
    @classmethod
    def validate_title_length(cls, v):
        """Validate title is reasonable length."""
        words = len(v.split())
        if words < 3:
            logger.warning(f"Citation title too short ({words} words): {v}")
        elif words > 25:
            logger.warning(f"Citation title too long ({words} words): {v}")
        return v

    @field_validator("url")
    @classmethod
    def validate_url_format(cls, v):
        """Validate URL format."""
        # CRITICAL FIX: Reject relative URLs and malformed URLs
        if not v.startswith(("http://", "https://")):
            if v.startswith("/"):
                # Relative URL - reject it
                logger.error(f"Rejecting relative URL: {v}")
                raise ValueError(f"Relative URLs are not allowed: {v}")
            logger.warning(f"URL missing protocol: {v}")
            # Only prepend https:// if it looks like a domain (has a dot)
            if "." in v and not v.startswith("/"):
                v = f"https://{v}"
            else:
                logger.error(f"Invalid URL format: {v}")
                raise ValueError(f"Invalid URL format: {v}")
        
        # CRITICAL FIX: Validate URL has proper domain structure
        from urllib.parse import urlparse
        try:
            parsed = urlparse(v)
            if not parsed.netloc:
                logger.error(f"URL missing domain: {v}")
                raise ValueError(f"URL missing domain: {v}")
            
            # Check domain has TLD (at least one dot in netloc)
            domain = parsed.netloc.lower()
            if "." not in domain and domain not in ['localhost']:
                # Check if it's an IP address
                try:
                    import ipaddress
                    ipaddress.ip_address(domain)
                except ValueError:
                    logger.error(f"URL missing TLD: {v}")
                    raise ValueError(f"URL missing TLD (invalid domain): {v}")
        except Exception as e:
            logger.error(f"URL validation error for {v}: {e}")
            raise ValueError(f"Invalid URL format: {v}")
        
        return v

    def to_html(self) -> str:
        """
        Convert to HTML format.

        Format: [n]: <a href="url">title</a>
        """
        return f'[{self.number}]: <a href="{self.url}" target="_blank">{self.title}</a>'

    def to_markdown(self) -> str:
        """Convert to Markdown format."""
        return f"[{self.number}]: [{self.title}]({self.url})"

    def __repr__(self) -> str:
        """String representation."""
        return f"Citation({self.number}: {self.url})"


class CitationList(BaseModel):
    """
    Collection of citations.

    Manages multiple citations and provides formatting options.
    """

    citations: List[Citation] = Field(default_factory=list, description="List of citations")
    max_citations: int = Field(default=20, description="Maximum allowed citations (v4.1)")

    @field_validator("citations")
    @classmethod
    def validate_citation_count(cls, v, info):
        """Validate citation count doesn't exceed maximum."""
        if len(v) > 20:
            logger.warning(f"Citation count exceeds 20: {len(v)} citations")
        return v

    def add_citation(self, url: str, title: str, accessed_date: str = "") -> "CitationList":
        """
        Add a citation to the list.

        Returns self for chaining.
        """
        next_number = len(self.citations) + 1
        citation = Citation(
            number=next_number,
            url=url,
            title=title,
            accessed_date=accessed_date,
        )
        self.citations.append(citation)
        return self

    def to_html(self) -> str:
        """
        Convert all citations to HTML.

        Returns:
            HTML block with all citations.
            Format:
            <div class="citations">
              [1]: <a href="url">title</a>
              [2]: <a href="url">title</a>
              ...
            </div>
        """
        if not self.citations:
            return ""

        html_lines = ["<div class=\"citations\">"]
        for citation in self.citations:
            html_lines.append(f"  <p>{citation.to_html()}</p>")
        html_lines.append("</div>")

        return "\n".join(html_lines)

    def to_html_paragraph_list(self) -> str:
        """
        Convert to HTML paragraph list (v4.1 format).

        Returns:
            HTML with each citation as a paragraph.
        """
        if not self.citations:
            return ""

        lines = []
        for citation in self.citations:
            lines.append(f"<p>{citation.to_html()}</p>")

        return "\n".join(lines)

    def count(self) -> int:
        """Get citation count."""
        return len(self.citations)

    def get_urls(self) -> List[str]:
        """Get list of all URLs."""
        return [c.url for c in self.citations]

    def get_citation_by_number(self, number: int) -> Optional[Citation]:
        """Get citation by number."""
        for citation in self.citations:
            if citation.number == number:
                return citation
        return None

    def __repr__(self) -> str:
        """String representation."""
        return f"CitationList({len(self.citations)} citations)"
