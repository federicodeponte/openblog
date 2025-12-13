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
    # NOTE: Patterns are applied in order - more specific patterns should come first
    CITATION_PATTERNS = [
        # Pattern 1: "according to IBM" / "according to Gartner research"
        CitationPattern(
            pattern=r'(?i)\baccording to\s+(?:the\s+)?([A-Z][A-Za-z\s&]+?)(?=[,\.\s]|\'s|\s+research|\s+report|\s+study|\s+data)',
            source_group=1,
            link_format='according to <a href="{url}" target="_blank" rel="noopener noreferrer" class="citation">{source}</a>'
        ),
        # Pattern 2: "IBM reports that" / "Gartner predicts that" / "McKinsey found that"
        CitationPattern(
            pattern=r'(?i)\b([A-Z][A-Za-z\s&]+?)\s+(reports?|states?|notes?|predicts?|estimates?|indicates?|found|shows?|reveals?|highlights?|concludes?|demonstrates?|suggests?|warns?|recommends?)\s+that\b',
            source_group=1,
            link_format='<a href="{url}" target="_blank" rel="noopener noreferrer" class="citation">{source}</a> {verb} that'
        ),
        # Pattern 3: "the 2024 IBM report" / "the 2025 Gartner study"
        CitationPattern(
            pattern=r'(?i)\bthe\s+\d{4}\s+([A-Z][A-Za-z\s&]+?)\s+(report|study|survey|analysis|research)\b',
            source_group=1,
            link_format='the {year} <a href="{url}" target="_blank" rel="noopener noreferrer" class="citation">{source}</a> {suffix}'
        ),
        # Pattern 4: "research by IBM" / "report from Gartner"
        CitationPattern(
            pattern=r'(?i)\b(research|report|study|survey|analysis)\s+(?:by|from)\s+([A-Z][A-Za-z\s&]+?)(?=[,\.\s])',
            source_group=2,
            link_format='{prefix} by <a href="{url}" target="_blank" rel="noopener noreferrer" class="citation">{source}</a>'
        ),
        # Pattern 5: "IBM's research" / "Gartner's latest report"
        CitationPattern(
            pattern=r'(?i)\b([A-Z][A-Za-z\s&]+?)\'s\s+(?:latest\s+)?(research|report|study|survey|analysis|data|findings)\b',
            source_group=1,
            link_format='<a href="{url}" target="_blank" rel="noopener noreferrer" class="citation">{source}</a>\'s {suffix}'
        ),
        # Pattern 6: "data from IBM" / "statistics from Gartner"
        CitationPattern(
            pattern=r'(?i)\b(data|statistics|figures|numbers|insights)\s+from\s+([A-Z][A-Za-z\s&]+?)(?=[,\.\s])',
            source_group=2,
            link_format='{prefix} from <a href="{url}" target="_blank" rel="noopener noreferrer" class="citation">{source}</a>'
        ),
        # Pattern 7: "as IBM notes" / "as Gartner highlights"
        CitationPattern(
            pattern=r'(?i)\bas\s+([A-Z][A-Za-z\s&]+?)\s+(notes?|highlights?|points out|emphasizes?|stresses?)\b',
            source_group=1,
            link_format='as <a href="{url}" target="_blank" rel="noopener noreferrer" class="citation">{source}</a> {verb}'
        ),
        # Pattern 8: "per IBM" / "per Gartner's analysis"
        CitationPattern(
            pattern=r'(?i)\bper\s+([A-Z][A-Za-z\s&]+?)(?=[,\.\s]|\'s)',
            source_group=1,
            link_format='per <a href="{url}" target="_blank" rel="noopener noreferrer" class="citation">{source}</a>'
        ),
        # Pattern 9: "X%, according to IBM" / "X percent, per Gartner"
        CitationPattern(
            pattern=r'(?i)(\d+%|\d+\s+percent)[,\s]+(?:according to|per)\s+([A-Z][A-Za-z\s&]+?)(?=[,\.\s])',
            source_group=2,
            link_format='{percent}, according to <a href="{url}" target="_blank" rel="noopener noreferrer" class="citation">{source}</a>'
        ),
        # Pattern 10: "IBM analysis shows" / "Gartner data suggests"
        CitationPattern(
            pattern=r'(?i)\b([A-Z][A-Za-z\s&]+?)\s+(analysis|data|research|study)\s+(shows?|suggests?|indicates?|reveals?)\b',
            source_group=1,
            link_format='<a href="{url}" target="_blank" rel="noopener noreferrer" class="citation">{source}</a> {middle} {verb}'
        ),
    ]
    
    # Known source name mappings - used for fuzzy matching source names to URLs
    SOURCE_ALIASES = {
        'ibm': ['ibm', 'ibm security', 'ibm research', 'ibm cost of a data breach'],
        'gartner': ['gartner', 'gartner research', 'gartner inc', 'gartner group'],
        'mckinsey': ['mckinsey', 'mckinsey & company', 'mckinsey and company', 'mckinsey global institute'],
        'forrester': ['forrester', 'forrester research', 'forrester wave'],
        'palo alto': ['palo alto', 'palo alto networks'],
        'crowdstrike': ['crowdstrike', 'crowd strike'],
        'splunk': ['splunk'],
        'darktrace': ['darktrace'],
        'sans': ['sans', 'sans institute'],
        'isc2': ['isc2', 'isc²', '(isc)²'],
        'owasp': ['owasp'],
        'nist': ['nist', 'national institute'],
        'cisa': ['cisa', 'cybersecurity and infrastructure'],
        'github': ['github', 'github copilot'],
        'google': ['google', 'google cloud', 'google dora'],
        'microsoft': ['microsoft', 'microsoft security'],
        'amazon': ['amazon', 'aws', 'amazon web services'],
        'cisco': ['cisco', 'cisco talos'],
        'deloitte': ['deloitte'],
        'accenture': ['accenture'],
        'pwc': ['pwc', 'pricewaterhousecoopers'],
        'kpmg': ['kpmg'],
        'ey': ['ey', 'ernst & young', 'ernst and young'],
        'gitclear': ['gitclear'],
        'dora': ['dora', 'google dora', 'dora report'],
    }
    
    # Multi-word source names that should be matched as complete units
    # These are checked BEFORE regular pattern matching to prevent partial matches like "Palo" instead of "Palo Alto Networks"
    MULTI_WORD_SOURCES = [
        'Palo Alto Networks',
        'McKinsey & Company',
        'McKinsey and Company',
        'McKinsey Global Institute',
        'IBM Security',
        'IBM Research',
        'Google Cloud',
        'Google DORA',
        'Amazon Web Services',
        'Microsoft Security',
        'Cisco Talos',
        'Gartner Research',
        'Forrester Research',
        'Forrester Wave',
        'SANS Institute',
        'Ernst & Young',
        'National Institute of Standards and Technology',
        'World Economic Forum',
        'Cloud Security Alliance',
        'Ponemon Institute',
        'Check Point Research',
    ]
    
    def __init__(self, citation_map: Optional[Dict[str, str]] = None, max_links_per_source: int = 3):
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
    
    def _link_multi_word_sources(self, content: str) -> tuple[str, int]:
        """
        Link multi-word source names before regular pattern matching.
        
        This prevents partial matches like "Palo" instead of "Palo Alto Networks".
        
        Args:
            content: HTML content
            
        Returns:
            Tuple of (updated content, number of links made)
        """
        linked_count = 0
        
        for source_name in self.MULTI_WORD_SOURCES:
            url = self._find_matching_url(source_name)
            if not url:
                continue
            
            current_count = self.link_counts.get(url, 0)
            if current_count >= self.max_links_per_source:
                continue
            
            # Only match if not already linked (check for <a> tag)
            # Match: source_name NOT preceded by ">" (end of tag) or followed by "</a"
            pattern = rf'(?<!>)(?<!")\b({re.escape(source_name)})\b(?!</a)(?!.*?</a)'
            
            def replace_source(match):
                nonlocal linked_count
                if self.link_counts.get(url, 0) >= self.max_links_per_source:
                    return match.group(0)
                linked = f'<a href="{url}" target="_blank" rel="noopener noreferrer" class="citation">{match.group(1)}</a>'
                self.link_counts[url] = self.link_counts.get(url, 0) + 1
                linked_count += 1
                return linked
            
            content = re.sub(pattern, replace_source, content, count=self.max_links_per_source - current_count, flags=re.IGNORECASE)
        
        if linked_count > 0:
            logger.info(f"✅ Linked {linked_count} multi-word source citations")
        
        return content, linked_count
    
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
        
        # STEP 1: Link multi-word sources FIRST to prevent partial matches
        # e.g., "Palo Alto Networks" should be linked as a whole, not just "Palo"
        content, multi_word_links = self._link_multi_word_sources(content)
        linked_count += multi_word_links
        
        # STEP 2: Apply regular citation patterns
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


def link_internal_articles(content: str, internal_links: List[Dict[str, str]], 
                          max_links: int = 3) -> str:
    """
    Link keywords in content to related internal blog posts.
    
    Finds topic keywords from internal link titles and links them
    to the corresponding blog posts, similar to how external citations work.
    
    Args:
        content: HTML content to process
        internal_links: List of {'url': str, 'title': str} dicts
        max_links: Maximum internal links to add to body
        
    Returns:
        Content with internal links added
    """
    if not content or not internal_links:
        return content
    
    linked_count = 0
    link_counts: Dict[str, int] = {}
    
    for link_data in internal_links:
        if linked_count >= max_links:
            break
            
        url = link_data.get('url', '')
        title = link_data.get('title', '')
        
        if not url or not title:
            continue
        
        # Skip if already linked this URL
        if link_counts.get(url, 0) >= 1:
            continue
        
        # Extract key phrases from title (2-3 word phrases)
        # e.g., "Automated Lead Generation for Tech Startups" -> ["lead generation", "tech startups"]
        title_clean = re.sub(r'^(Automated|Building|Setting Up|Implementing|Using|Developing)\s+', '', title, flags=re.IGNORECASE)
        title_clean = re.sub(r'\s+(For|With|In|To|From)\s+.+$', '', title_clean, flags=re.IGNORECASE)
        
        # Try to find this phrase in the content (case insensitive)
        if len(title_clean) < 5:
            continue
            
        # Look for the phrase NOT already inside an <a> tag
        pattern = rf'(?<![">])({re.escape(title_clean)})(?![^<]*</a>)'
        match = re.search(pattern, content, re.IGNORECASE)
        
        if match:
            matched_text = match.group(1)
            replacement = f'<a href="{url}" class="internal-link">{matched_text}</a>'
            content = content[:match.start(1)] + replacement + content[match.end(1):]
            link_counts[url] = link_counts.get(url, 0) + 1
            linked_count += 1
            logger.debug(f"Added internal link: {matched_text} -> {url}")
    
    if linked_count > 0:
        logger.info(f"✅ Added {linked_count} internal links to body")
    
    return content
