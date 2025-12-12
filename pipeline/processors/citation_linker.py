"""
Citation Linker - Natural Language and Legacy Citation Linking

Provides two types of citation linking:

1. NATURAL LANGUAGE LINKING (new):
   Converts "according to IBM" → <a href="ibm-url">according to IBM</a>
   Used by HTMLRenderer for inline citation linking.

2. LEGACY [N] LINKING (backward compatible):
   Converts [1], [2] markers → <a href="url">Source Name</a>
   Used by Stage 10 for article content processing.

Design Principles:
- Single Responsibility: Citation linking only
- Open/Closed: Pattern list is configurable
- DRY: Shared utility methods
- Backward Compatible: Maintains Stage 10 API
"""

import re
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CitationPattern:
    """Defines a pattern for finding natural language citations."""
    pattern: str  # Regex pattern
    source_group: int  # Which group contains the source name
    link_format: str  # How to format the link


class CitationLinker:
    """
    Link citations in content - supports both natural language and [N] markers.
    
    This class provides:
    - Instance methods for natural language citation linking
    - Static methods for legacy [N] citation linking (Stage 10 compatibility)
    """
    
    # Common patterns for source attribution in professional content
    CITATION_PATTERNS = [
        CitationPattern(
            pattern=r'(?i)\baccording to\s+([A-Z][A-Za-z\s&]+?)(?=[,\.\s]|\'s|\s+research|\s+report|\s+study|\s+data)',
            source_group=1,
            link_format='according to <a href="{url}" target="_blank" rel="noopener noreferrer" class="citation">{source}</a>'
        ),
        CitationPattern(
            pattern=r'(?i)\b([A-Z][A-Za-z\s&]+?)\s+(reports?|states?|notes?|predicts?|estimates?|indicates?|found|shows?|reveals?|highlights?)\s+that\b',
            source_group=1,
            link_format='<a href="{url}" target="_blank" rel="noopener noreferrer" class="citation">{source}</a> {verb} that'
        ),
        CitationPattern(
            pattern=r'(?i)\b(research|report|study|survey|analysis)\s+(?:by|from)\s+([A-Z][A-Za-z\s&]+?)(?=[,\.\s])',
            source_group=2,
            link_format='{prefix} by <a href="{url}" target="_blank" rel="noopener noreferrer" class="citation">{source}</a>'
        ),
        CitationPattern(
            pattern=r'(?i)\b([A-Z][A-Za-z\s&]+?)\'s\s+(research|report|study|survey|analysis|data|findings)\b',
            source_group=1,
            link_format='<a href="{url}" target="_blank" rel="noopener noreferrer" class="citation">{source}</a>\'s {suffix}'
        ),
        CitationPattern(
            pattern=r'(?i)\b(data|statistics|figures|numbers)\s+from\s+([A-Z][A-Za-z\s&]+?)(?=[,\.\s])',
            source_group=2,
            link_format='{prefix} from <a href="{url}" target="_blank" rel="noopener noreferrer" class="citation">{source}</a>'
        ),
    ]
    
    # Known source name mappings
    SOURCE_ALIASES = {
        'ibm': ['ibm', 'ibm security', 'ibm research'],
        'gartner': ['gartner', 'gartner research', 'gartner inc'],
        'mckinsey': ['mckinsey', 'mckinsey & company', 'mckinsey and company'],
        'forrester': ['forrester', 'forrester research'],
        'palo alto': ['palo alto', 'palo alto networks'],
        'crowdstrike': ['crowdstrike'],
        'splunk': ['splunk'],
        'darktrace': ['darktrace'],
        'sans': ['sans', 'sans institute'],
        'isc2': ['isc2', 'isc²', '(isc)²'],
        'owasp': ['owasp'],
        'nist': ['nist'],
        'cisa': ['cisa'],
    }
    
    def __init__(self, citation_map: Optional[Dict[str, str]] = None, max_links_per_source: int = 2):
        """
        Initialize for natural language citation linking.
        
        Args:
            citation_map: Dict mapping source names to URLs
            max_links_per_source: Maximum times to link each source
        """
        self.citation_map = citation_map or {}
        self.max_links_per_source = max_links_per_source
        self.link_counts: Dict[str, int] = {}
        self.source_lookup = self._build_source_lookup()
    
    def _build_source_lookup(self) -> Dict[str, str]:
        """Build normalized source name → URL lookup."""
        lookup = {}
        
        for key, url in self.citation_map.items():
            if not url or not url.startswith('http'):
                continue
            
            # Add lowercase key
            lookup[str(key).lower()] = url
            
            # Extract domain from URL
            domain = self._extract_source_from_url(url)
            if domain:
                lookup[domain.lower()] = url
        
        return lookup
    
    def _extract_source_from_url(self, url: str) -> Optional[str]:
        """Extract source name from URL domain."""
        try:
            domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
            if domain_match:
                domain = domain_match.group(1)
                parts = domain.split('.')
                if len(parts) >= 2:
                    return parts[-2]
        except Exception:
            pass
        return None
    
    def _find_matching_url(self, source_name: str) -> Optional[str]:
        """Find URL for a source name, handling aliases."""
        normalized = source_name.lower().strip()
        
        # Direct lookup
        if normalized in self.source_lookup:
            return self.source_lookup[normalized]
        
        # Check aliases
        for base_name, aliases in self.SOURCE_ALIASES.items():
            if normalized in aliases or base_name in normalized:
                for key, url in self.source_lookup.items():
                    if base_name in key:
                        return url
        
        # Fuzzy match
        for key, url in self.source_lookup.items():
            if key in normalized or normalized in key:
                return url
        
        return None
    
    def link_citations(self, content: str) -> str:
        """
        Convert natural language citations to hyperlinks.
        
        Args:
            content: HTML content with natural language citations
            
        Returns:
            Content with linked citations
        """
        if not content or not self.source_lookup:
            return content
        
        linked_count = 0
        
        for pattern_def in self.CITATION_PATTERNS:
            matches = list(re.finditer(pattern_def.pattern, content))
            
            for match in reversed(matches):
                source_name = match.group(pattern_def.source_group).strip()
                url = self._find_matching_url(source_name)
                
                if not url:
                    continue
                
                current_count = self.link_counts.get(url, 0)
                if current_count >= self.max_links_per_source:
                    continue
                
                # Build replacement
                full_match = match.group(0)
                linked_source = f'<a href="{url}" target="_blank" rel="noopener noreferrer" class="citation">{source_name}</a>'
                replacement = full_match.replace(source_name, linked_source, 1)
                
                content = content[:match.start()] + replacement + content[match.end():]
                self.link_counts[url] = current_count + 1
                linked_count += 1
        
        if linked_count > 0:
            logger.info(f"✅ Linked {linked_count} natural language citations")
        
        return content
    
    # =========================================================================
    # LEGACY STATIC METHODS - Stage 10 Backward Compatibility
    # =========================================================================
    
    @staticmethod
    def link_citations_in_content(
        content: Dict[str, Any],
        citations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Replace citation markers [1], [2] with clickable links in article content.
        
        LEGACY METHOD - Maintains backward compatibility with Stage 10.
        
        Args:
            content: Article content dict with sections
            citations: List of citation dicts with 'number', 'url', 'title'
        
        Returns:
            Updated content dict with linked citations
        """
        if not citations:
            logger.debug("No citations to link")
            return content
        
        # Build citation map: number -> {url, title}
        citation_map = {}
        for citation in citations:
            if isinstance(citation, dict):
                num = citation.get('number')
                url = citation.get('url', '')
                title = citation.get('title', '')
            else:
                num = getattr(citation, 'number', None)
                url = getattr(citation, 'url', '')
                title = getattr(citation, 'title', '')
            
            if num and url:
                citation_map[num] = {
                    'url': url,
                    'title': title or f"Source {num}",
                }
        
        if not citation_map:
            logger.debug("No valid citations found in citation map")
            return content
        
        logger.info(f"Linking {len(citation_map)} citations in content")
        
        # Process each section
        updated_content = content.copy()
        
        # Link in section content
        for i in range(1, 10):
            key = f'section_{i:02d}_content'
            if key in updated_content and updated_content[key]:
                updated_content[key] = CitationLinker._link_markers_in_text(
                    updated_content[key],
                    citation_map
                )
        
        # Link in Intro
        if 'Intro' in updated_content:
            updated_content['Intro'] = CitationLinker._link_markers_in_text(
                updated_content['Intro'],
                citation_map
            )
        
        # Link in Direct_Answer  
        if 'Direct_Answer' in updated_content:
            updated_content['Direct_Answer'] = CitationLinker._link_markers_in_text(
                updated_content['Direct_Answer'],
                citation_map
            )
        
        return updated_content
    
    @staticmethod
    def _link_markers_in_text(text: str, citation_map: Dict[int, Dict]) -> str:
        """
        Replace [N] markers with links in text.
        
        Args:
            text: Text containing [1], [2], etc. markers
            citation_map: Dict mapping number to {'url': ..., 'title': ...}
            
        Returns:
            Text with [N] replaced by <a href="...">source name</a>
        """
        if not text:
            return text
        
        def replace_marker(match):
            num = int(match.group(1))
            if num in citation_map:
                cite = citation_map[num]
                url = cite['url']
                title = cite['title']
                source_name = title.split()[0] if title else f"Source {num}"
                return f'<a href="{url}" target="_blank" rel="noopener noreferrer" class="citation">{source_name}</a>'
            return match.group(0)
        
        return re.sub(r'\[(\d+)\]', replace_marker, text)


# Module-level convenience function
def link_natural_citations(content: str, citation_map: Dict[str, str], 
                          max_links_per_source: int = 2) -> str:
    """
    Link natural language citations to their source URLs.
    
    This is the main entry point for natural language citation linking.
    
    Args:
        content: HTML content with citations
        citation_map: Dict mapping source identifiers to URLs
        max_links_per_source: Maximum times to link each URL
        
    Returns:
        Content with linked citations
    """
    linker = CitationLinker(citation_map, max_links_per_source)
    return linker.link_citations(content)
