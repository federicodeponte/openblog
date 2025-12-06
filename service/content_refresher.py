"""
Content Refresher - Refresh/correct existing content using prompts
Similar to ChatGPT Canvas - updates specific parts without full rewrite

Supports flexible input formats:
- HTML
- Markdown
- Plain text
- JSON (structured blog format)
- Google Docs format
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from bs4 import BeautifulSoup
import markdown

logger = logging.getLogger(__name__)


class ContentParser:
    """Parse content from various formats into structured sections."""
    
    @staticmethod
    def parse(content: str, format_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse content from various formats.
        
        Args:
            content: Raw content string
            format_type: Optional format hint ('html', 'markdown', 'json', 'text')
        
        Returns:
            Structured content dict with sections
        """
        # Auto-detect format if not specified
        if not format_type:
            format_type = ContentParser._detect_format(content)
        
        if format_type == 'json':
            return ContentParser._parse_json(content)
        elif format_type == 'html':
            return ContentParser._parse_html(content)
        elif format_type == 'markdown':
            return ContentParser._parse_markdown(content)
        else:
            return ContentParser._parse_text(content)
    
    @staticmethod
    def _detect_format(content: str) -> str:
        """Auto-detect content format."""
        content_stripped = content.strip()
        
        # Check for JSON
        if content_stripped.startswith('{') or content_stripped.startswith('['):
            try:
                json.loads(content_stripped)
                return 'json'
            except:
                pass
        
        # Check for HTML
        if '<html' in content_stripped.lower() or '<div' in content_stripped.lower() or '<p>' in content_stripped.lower():
            return 'html'
        
        # Check for Markdown
        if any(marker in content_stripped for marker in ['# ', '## ', '**', '* ', '- ']):
            return 'markdown'
        
        return 'text'
    
    @staticmethod
    def _parse_json(content: str) -> Dict[str, Any]:
        """Parse JSON format."""
        try:
            data = json.loads(content)
            
            # If it's already structured blog format
            if isinstance(data, dict) and 'sections' in data:
                return data
            
            # Convert to structured format
            return {
                'headline': data.get('headline', data.get('title', '')),
                'sections': data.get('sections', []),
                'faq': data.get('faq', []),
                'meta_description': data.get('meta_description', ''),
            }
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return {'sections': [{'heading': 'Content', 'content': content}]}
    
    @staticmethod
    def _parse_html(content: str) -> Dict[str, Any]:
        """Parse HTML format."""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract headline
            headline = ''
            h1 = soup.find('h1')
            if h1:
                headline = h1.get_text().strip()
            
            # Extract sections (h2/h3 headings with following content)
            sections = []
            current_heading = None
            current_content = []
            
            for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'div', 'ul', 'ol']):
                if element.name in ['h1', 'h2', 'h3', 'h4']:
                    # Save previous section
                    if current_heading:
                        sections.append({
                            'heading': current_heading,
                            'content': ' '.join(current_content)
                        })
                    current_heading = element.get_text().strip()
                    current_content = []
                else:
                    text = element.get_text().strip()
                    if text:
                        current_content.append(text)
            
            # Save last section
            if current_heading:
                sections.append({
                    'heading': current_heading,
                    'content': ' '.join(current_content)
                })
            
            # Extract meta description
            meta = soup.find('meta', attrs={'name': 'description'})
            meta_description = meta.get('content', '') if meta else ''
            
            return {
                'headline': headline,
                'sections': sections,
                'meta_description': meta_description,
            }
        except Exception as e:
            logger.error(f"HTML parse error: {e}")
            return {'sections': [{'heading': 'Content', 'content': content}]}
    
    @staticmethod
    def _parse_markdown(content: str) -> Dict[str, Any]:
        """Parse Markdown format."""
        try:
            # Convert markdown to HTML first
            html = markdown.markdown(content)
            return ContentParser._parse_html(html)
        except Exception as e:
            logger.error(f"Markdown parse error: {e}")
            return {'sections': [{'heading': 'Content', 'content': content}]}
    
    @staticmethod
    def _parse_text(content: str) -> Dict[str, Any]:
        """Parse plain text format."""
        # Split by double newlines (paragraphs)
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        sections = []
        current_heading = None
        current_content = []
        
        for para in paragraphs:
            # Check if paragraph looks like a heading (short, ends with colon, or all caps)
            if len(para) < 100 and (para.endswith(':') or para.isupper()):
                if current_heading:
                    sections.append({
                        'heading': current_heading,
                        'content': ' '.join(current_content)
                    })
                current_heading = para
                current_content = []
            else:
                current_content.append(para)
        
        # Save last section
        if current_heading:
            sections.append({
                'heading': current_heading,
                'content': ' '.join(current_content)
            })
        elif paragraphs:
            # No headings found, treat as single section
            sections.append({
                'heading': 'Content',
                'content': ' '.join(paragraphs)
            })
        
        return {
            'headline': sections[0]['heading'] if sections else '',
            'sections': sections,
            'meta_description': '',
        }


class ContentRefresher:
    """Refresh/correct content using prompts - updates specific parts."""
    
    def __init__(self, gemini_client):
        self.gemini_client = gemini_client
    
    async def refresh_content(
        self,
        content: Dict[str, Any],
        instructions: List[str],
        target_sections: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Refresh content based on instructions.
        
        Args:
            content: Structured content dict
            instructions: List of prompts/instructions for changes
            target_sections: Optional list of section indices to update (None = all)
        
        Returns:
            Updated content dict
        """
        sections = content.get('sections', [])
        
        # If no target sections specified, update all
        if target_sections is None:
            target_sections = list(range(len(sections)))
        
        # Refresh each target section
        updated_sections = []
        for i, section in enumerate(sections):
            if i in target_sections:
                # Refresh this section
                updated_section = await self._refresh_section(section, instructions)
                updated_sections.append(updated_section)
            else:
                # Keep original
                updated_sections.append(section)
        
        # Update content dict
        refreshed_content = content.copy()
        refreshed_content['sections'] = updated_sections
        
        # Optionally refresh meta description if instructions mention it
        if any('meta' in inst.lower() or 'description' in inst.lower() for inst in instructions):
            refreshed_content['meta_description'] = await self._refresh_meta(
                content.get('meta_description', ''),
                instructions
            )
        
        return refreshed_content
    
    async def _refresh_section(
        self,
        section: Dict[str, Any],
        instructions: List[str],
    ) -> Dict[str, Any]:
        """Refresh a single section based on instructions."""
        heading = section.get('heading', '')
        content_text = section.get('content', '')
        
        # Build prompt for section refresh
        instructions_text = '\n'.join(f"- {inst}" for inst in instructions)
        
        prompt = f"""You are refreshing existing content. Update the following section based on the instructions, but keep the same structure and style. Only change what needs to be changed - don't rewrite everything.

Section Heading: {heading}

Current Content:
{content_text}

Instructions:
{instructions_text}

Requirements:
- Keep the same heading
- Maintain the same writing style and tone
- Only update parts that need changes based on instructions
- Keep unchanged parts exactly as they are
- Ensure the updated content flows naturally
- Don't add new information unless instructed

Return ONLY the updated content text (no heading, no markdown, just the paragraph text):"""

        try:
            # Generate refreshed content
            refreshed_text = await self.gemini_client.generate_content(
                prompt,
                enable_tools=False,  # No search needed for refresh
            )
            
            # Clean up response (remove any markdown formatting)
            refreshed_text = refreshed_text.strip()
            refreshed_text = re.sub(r'^```[a-z]*\n', '', refreshed_text)
            refreshed_text = re.sub(r'\n```$', '', refreshed_text)
            refreshed_text = refreshed_text.strip()
            
            return {
                'heading': heading,
                'content': refreshed_text,
            }
        except Exception as e:
            logger.error(f"Error refreshing section: {e}")
            # Return original on error
            return section
    
    async def _refresh_meta(
        self,
        meta_description: str,
        instructions: List[str],
    ) -> str:
        """Refresh meta description."""
        instructions_text = '\n'.join(f"- {inst}" for inst in instructions)
        
        prompt = f"""Update this meta description based on the instructions. Keep it concise (120-160 characters).

Current Meta Description:
{meta_description}

Instructions:
{instructions_text}

Return ONLY the updated meta description (no quotes, no explanation):"""

        try:
            refreshed_meta = await self.gemini_client.generate_content(
                prompt,
                enable_tools=False,
            )
            return refreshed_meta.strip().strip('"').strip("'")
        except Exception as e:
            logger.error(f"Error refreshing meta: {e}")
            return meta_description
    
    def to_html(self, content: Dict[str, Any]) -> str:
        """Convert refreshed content back to HTML."""
        html_parts = []
        
        if content.get('headline'):
            html_parts.append(f"<h1>{content['headline']}</h1>")
        
        for section in content.get('sections', []):
            heading = section.get('heading', '')
            content_text = section.get('content', '')
            
            if heading:
                html_parts.append(f"<h2>{heading}</h2>")
            
            # Convert content to paragraphs
            paragraphs = [p.strip() for p in content_text.split('\n\n') if p.strip()]
            for para in paragraphs:
                html_parts.append(f"<p>{para}</p>")
        
        return '\n'.join(html_parts)
    
    def to_markdown(self, content: Dict[str, Any]) -> str:
        """Convert refreshed content to Markdown."""
        md_parts = []
        
        if content.get('headline'):
            md_parts.append(f"# {content['headline']}\n")
        
        for section in content.get('sections', []):
            heading = section.get('heading', '')
            content_text = section.get('content', '')
            
            if heading:
                md_parts.append(f"## {heading}\n")
            
            md_parts.append(f"{content_text}\n")
        
        return '\n'.join(md_parts)
    
    def to_json(self, content: Dict[str, Any]) -> str:
        """Convert refreshed content to JSON."""
        return json.dumps(content, indent=2, ensure_ascii=False)

