"""
Citation Linker - Convert citation markers [1], [2] to clickable links in HTML content

Post-processes article content to:
1. Replace citation markers [1], [2] with actual anchor tags
2. Links point to specific page URLs (not domains)
3. Maintains citation numbering
"""

import re
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class CitationLinker:
    """Link citations in HTML content."""
    
    @staticmethod
    def link_citations_in_content(
        content: Dict[str, Any],
        citations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Replace citation markers [1], [2] with clickable links in article content.
        
        Args:
            content: Article content dict with sections
            citations: List of citation dicts with 'number', 'url', 'title'
        
        Returns:
            Updated content dict with linked citations
        """
        if not citations:
            logger.debug("No citations to link")
            return content
        
        # Build citation map: number -> url
        citation_map = {}
        for citation in citations:
            if isinstance(citation, dict):
                num = citation.get('number')
                url = citation.get('url', '')
                title = citation.get('title', '')
            else:
                # Handle Citation objects
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
        
        # Link in direct_answer
        if 'direct_answer' in updated_content:
            updated_content['direct_answer'] = CitationLinker._link_citations_in_text(
                updated_content['direct_answer'],
                citation_map
            )
        
        # Link in intro
        if 'intro' in updated_content:
            updated_content['intro'] = CitationLinker._link_citations_in_text(
                updated_content['intro'],
                citation_map
            )
        
        # Link in sections
        sections = updated_content.get('sections', [])
        updated_sections = []
        for section in sections:
            if isinstance(section, dict):
                updated_section = section.copy()
                if 'content' in updated_section:
                    updated_section['content'] = CitationLinker._link_citations_in_text(
                        updated_section['content'],
                        citation_map
                    )
                updated_sections.append(updated_section)
            else:
                updated_sections.append(section)
        
        updated_content['sections'] = updated_sections
        
        # Link in FAQ answers
        faq = updated_content.get('faq', [])
        updated_faq = []
        for faq_item in faq:
            if isinstance(faq_item, dict):
                updated_item = faq_item.copy()
                if 'answer' in updated_item:
                    updated_item['answer'] = CitationLinker._link_citations_in_text(
                        updated_item['answer'],
                        citation_map
                    )
                updated_faq.append(updated_item)
            else:
                updated_faq.append(faq_item)
        updated_content['faq'] = updated_faq
        
        # Link in PAA answers
        paa = updated_content.get('paa', [])
        updated_paa = []
        for paa_item in paa:
            if isinstance(paa_item, dict):
                updated_item = paa_item.copy()
                if 'answer' in updated_item:
                    updated_item['answer'] = CitationLinker._link_citations_in_text(
                        updated_item['answer'],
                        citation_map
                    )
                updated_paa.append(updated_item)
            else:
                updated_paa.append(paa_item)
        updated_content['paa'] = updated_paa
        
        return updated_content
    
    @staticmethod
    def _link_citations_in_text(text: str, citation_map: Dict[int, Dict[str, str]]) -> str:
        """
        Replace citation markers [1], [2] with clickable links.
        
        Pattern: [1], [2], [1][2], etc.
        Replaces with: <a href="url" target="_blank" rel="noopener">[1]</a>
        
        Args:
            text: HTML text with citation markers
            citation_map: Dict mapping citation number to url/title
        
        Returns:
            Text with citation markers converted to links
        """
        if not text:
            return text
        
        # Pattern to match citation markers: [1], [2], [1][2], etc.
        # Match standalone citations or multiple citations together
        def replace_citation(match):
            citation_text = match.group(0)  # e.g., "[1]" or "[1][2]"
            
            # Extract all citation numbers
            numbers = re.findall(r'\[(\d+)\]', citation_text)
            
            if not numbers:
                return citation_text
            
            # Build replacement with links
            linked_citations = []
            for num_str in numbers:
                num = int(num_str)
                if num in citation_map:
                    citation_info = citation_map[num]
                    url = citation_info['url']
                    title = citation_info['title']
                    
                    # Create link with citation number
                    link = f'<a href="{url}" target="_blank" rel="noopener noreferrer" title="{title}">[{num}]</a>'
                    linked_citations.append(link)
                else:
                    # Keep original if citation not found
                    linked_citations.append(f'[{num}]')
            
            return ''.join(linked_citations)
        
        # Replace citation markers with links
        # Pattern: [number] optionally followed by more [number]
        pattern = r'\[\d+\](?:\[\d+\])*'
        result = re.sub(pattern, replace_citation, text)
        
        return result
    
    @staticmethod
    def validate_url_is_specific_page(url: str) -> bool:
        """
        Validate that URL is a specific page, not just a domain homepage.
        
        Args:
            url: URL to validate
        
        Returns:
            True if URL appears to be a specific page
        """
        if not url or not isinstance(url, str):
            return False
        
        # Remove protocol
        url_clean = url.replace('https://', '').replace('http://', '').strip('/')
        
        # Check if it's just a domain (no path)
        if '/' not in url_clean:
            return False
        
        # Check if path is meaningful (not just / or /index.html)
        parts = url_clean.split('/')
        if len(parts) <= 1:
            return False
        
        path = '/'.join(parts[1:])  # Everything after domain
        if not path or path in ['', 'index.html', 'index', 'home', 'homepage']:
            return False
        
        return True

