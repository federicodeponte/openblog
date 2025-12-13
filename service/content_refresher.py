"""
Content Refresher - Refresh/correct existing content using prompts
Similar to ChatGPT Canvas - updates specific parts without full rewrite

v2.0: Now uses structured JSON output to prevent hallucinations (same fix as v4.0 blog generation)

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
        enable_web_search: bool = False,
    ) -> Dict[str, Any]:
        """
        Refresh content based on instructions.
        
        Args:
            content: Structured content dict
            instructions: List of prompts/instructions for changes
            target_sections: Optional list of section indices to update (None = all)
            enable_web_search: Enable web search + URL context (like Stage 2) for research-heavy updates
        
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
                updated_section = await self._refresh_section(section, instructions, enable_web_search=enable_web_search)
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
        enable_web_search: bool = False,
    ) -> Dict[str, Any]:
        """
        Refresh a single section based on instructions.
        
        Uses structured JSON output (response_schema) to prevent hallucinations.
        This is the same fix applied to blog generation in v4.0.
        
        Args:
            section: Section dict with heading and content
            instructions: List of instructions for changes
            enable_web_search: Enable web search + URL context (like Stage 2) for research-heavy updates
        """
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
- Keep the same heading (exactly as provided)
- Maintain the same writing style and tone
- Only update parts that need changes based on instructions
- Keep unchanged parts exactly as they are
- Ensure the updated content flows naturally
- Don't add new information unless instructed
- Provide a brief change_summary explaining what you updated

You MUST respond with strict JSON matching this structure:
{{
  "heading": "{heading}",
  "content": "...updated content here (may include HTML)...",
  "change_summary": "...what changed (e.g., 'Updated statistics to 2025')..."
}}

CRITICAL: Output ONLY valid JSON. No other text or explanation."""

        try:
            # Import build_refresh_response_schema
            from pipeline.models.gemini_client import build_refresh_response_schema
            
            # Build response schema for single section
            # We'll use a simplified schema since we're refreshing one section at a time
            import google.genai as genai
            from google.genai import types
            
            refreshed_section_schema = types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "heading": types.Schema(
                        type=types.Type.STRING, 
                        description="Section heading (plain text, NO HTML)"
                    ),
                    "content": types.Schema(
                        type=types.Type.STRING,
                        description="Updated section content (may include HTML like <p>, <ul>, <strong>)"
                    ),
                    "change_summary": types.Schema(
                        type=types.Type.STRING,
                        description="Brief description of changes made"
                    ),
                },
                required=["heading", "content", "change_summary"]
            )
            
            # Generate refreshed content with structured output
            # response_mime_type is automatically set to "application/json" when response_schema is provided
            # Enable web search + URL context if requested (like Stage 2 for research-heavy updates)
            response = await self.gemini_client.generate_content(
                prompt,
                enable_tools=enable_web_search,  # Web search + URL context when needed
                response_schema=refreshed_section_schema
            )
            
            # Parse JSON directly (no regex cleanup needed with structured output!)
            refreshed_data = json.loads(response)
            
            logger.info(f"✅ Refreshed section '{heading}' - Change: {refreshed_data.get('change_summary', 'N/A')}")
            
            return {
                'heading': refreshed_data.get('heading', heading),
                'content': refreshed_data.get('content', content_text),
                'change_summary': refreshed_data.get('change_summary', ''),
            }
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parse error in refresh (structured output failed): {e}")
            # Fallback to original
            return section
        except Exception as e:
            logger.error(f"❌ Error refreshing section: {e}")
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
    
    def generate_diff(self, original_content: Dict[str, Any], refreshed_content: Dict[str, Any]) -> Tuple[str, str]:
        """
        Generate diff between original and refreshed content.
        
        Returns:
            Tuple of (unified_diff_text, html_diff)
        """
        import difflib
        
        # Convert both to readable text for comparison
        original_text = self._content_to_text(original_content)
        refreshed_text = self._content_to_text(refreshed_content)
        
        # Generate unified diff
        original_lines = original_text.splitlines(keepends=True)
        refreshed_lines = refreshed_text.splitlines(keepends=True)
        
        unified_diff = ''.join(difflib.unified_diff(
            original_lines,
            refreshed_lines,
            fromfile='original',
            tofile='refreshed',
            lineterm='',
        ))
        
        # Generate HTML diff
        html_diff = self._generate_html_diff(original_lines, refreshed_lines)
        
        return unified_diff, html_diff
    
    def _content_to_text(self, content: Dict[str, Any]) -> str:
        """Convert structured content to plain text for diffing."""
        text_parts = []
        
        if content.get('headline'):
            text_parts.append(f"# {content['headline']}\n")
        
        if content.get('meta_description'):
            text_parts.append(f"Meta: {content['meta_description']}\n")
        
        for section in content.get('sections', []):
            heading = section.get('heading', '')
            content_text = section.get('content', '')
            
            if heading:
                text_parts.append(f"\n## {heading}\n")
            text_parts.append(f"{content_text}\n")
        
        return '\n'.join(text_parts)
    
    def _generate_html_diff(self, original_lines: List[str], refreshed_lines: List[str]) -> str:
        """Generate HTML diff with highlighting."""
        import difflib
        
        differ = difflib.HtmlDiff(wrapcolumn=80)
        html_diff = differ.make_table(
            original_lines,
            refreshed_lines,
            fromdesc='Original',
            todesc='Refreshed',
            context=True,  # Show context lines
            numlines=3,    # 3 lines of context
        )
        
        # Add custom styling for better readability
        custom_style = """
        <style>
            .diff {
                font-family: monospace;
                border-collapse: collapse;
                width: 100%;
            }
            .diff td {
                padding: 4px;
                vertical-align: top;
            }
            .diff_header {
                background-color: #f0f0f0;
                font-weight: bold;
            }
            .diff_next {
                background-color: #f0f0f0;
            }
            .diff_add {
                background-color: #e6ffed;
                color: #24292e;
            }
            .diff_chg {
                background-color: #fff8c5;
                color: #24292e;
            }
            .diff_sub {
                background-color: #ffeef0;
                color: #24292e;
            }
        </style>
        """
        
        return custom_style + html_diff

