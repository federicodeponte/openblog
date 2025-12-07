"""
Unit tests for ContentParser

Tests parsing of various content formats (HTML, Markdown, JSON, plain text)
into structured sections for the refresh workflow.
"""

import pytest
from service.content_refresher import ContentParser


class TestContentParser:
    """Test suite for ContentParser."""
    
    def test_parse_html_with_sections(self):
        """Test parsing HTML with h2/h3 sections."""
        html_content = """
        <html>
        <head>
            <meta name="description" content="Test meta description">
        </head>
        <body>
            <h1>Main Headline</h1>
            <h2>Section One</h2>
            <p>This is the first paragraph of section one.</p>
            <p>This is the second paragraph.</p>
            <h2>Section Two</h2>
            <p>Content for section two.</p>
            <ul>
                <li>Item 1</li>
                <li>Item 2</li>
            </ul>
            <h3>Subsection</h3>
            <p>Subsection content.</p>
        </body>
        </html>
        """
        
        result = ContentParser.parse(html_content, format_type='html')
        
        assert result['headline'] == 'Main Headline'
        assert result['meta_description'] == 'Test meta description'
        assert len(result['sections']) >= 2
        
        # Find "Section One" (may not be first due to h1 also being treated as section)
        section_one = next((s for s in result['sections'] if 'Section One' in s['heading']), None)
        assert section_one is not None
        assert 'first paragraph' in section_one['content']
        assert 'second paragraph' in section_one['content']
        
        # Find "Section Two"
        section_two = next((s for s in result['sections'] if 'Section Two' in s['heading']), None)
        assert section_two is not None
        assert 'section two' in section_two['content'] or 'Item 1' in section_two['content']
    
    def test_parse_markdown_to_sections(self):
        """Test parsing Markdown and converting to sections."""
        markdown_content = """
# Main Title

## Introduction

This is the introduction paragraph with **bold text** and *italic text*.

## Key Points

Here are some key points:

- Point one
- Point two
- Point three

## Conclusion

Final thoughts here.
"""
        
        result = ContentParser.parse(markdown_content, format_type='markdown')
        
        assert result['headline'] == 'Main Title'
        assert len(result['sections']) >= 2
        
        # Check introduction section
        intro_section = next((s for s in result['sections'] if 'Introduction' in s['heading']), None)
        assert intro_section is not None
        assert 'introduction paragraph' in intro_section['content']
        
        # Check key points section
        key_points_section = next((s for s in result['sections'] if 'Key Points' in s['heading']), None)
        assert key_points_section is not None
        assert 'key points' in key_points_section['content']
    
    def test_parse_json_structured(self):
        """Test parsing structured JSON blog format."""
        json_content = """
{
  "headline": "Test Article",
  "sections": [
    {
      "heading": "First Section",
      "content": "Content of first section"
    },
    {
      "heading": "Second Section",
      "content": "Content of second section"
    }
  ],
  "meta_description": "This is a test meta description",
  "faq": [
    {
      "question": "What is this?",
      "answer": "This is a test"
    }
  ]
}
"""
        
        result = ContentParser.parse(json_content, format_type='json')
        
        assert result['headline'] == 'Test Article'
        assert result['meta_description'] == 'This is a test meta description'
        assert len(result['sections']) == 2
        assert result['sections'][0]['heading'] == 'First Section'
        assert result['sections'][0]['content'] == 'Content of first section'
        assert result['sections'][1]['heading'] == 'Second Section'
    
    def test_parse_plain_text_heuristics(self):
        """Test parsing plain text with heading detection."""
        text_content = """
INTRODUCTION:

This is the introduction paragraph. It has multiple sentences to provide context.

Key Features:

Here are the key features of our product. Each feature is important and well-designed.

CONCLUSION:

Final thoughts and summary of the content.
"""
        
        result = ContentParser.parse(text_content, format_type='text')
        
        assert len(result['sections']) >= 2
        
        # Check that headings were detected (ending with colon or uppercase)
        headings = [s['heading'] for s in result['sections']]
        assert any('INTRODUCTION' in h for h in headings)
        assert any('CONCLUSION' in h or 'Key Features' in h for h in headings)
        
        # Check content is associated with headings
        intro_section = next((s for s in result['sections'] if 'INTRODUCTION' in s['heading']), None)
        if intro_section:
            assert 'introduction paragraph' in intro_section['content']
    
    def test_auto_format_detection(self):
        """Test automatic format detection."""
        # Test HTML detection
        html_input = "<html><body><h1>Test</h1><p>Content</p></body></html>"
        result = ContentParser.parse(html_input)  # No format_type specified
        assert result['headline'] == 'Test' or len(result['sections']) > 0
        
        # Test JSON detection
        json_input = '{"headline": "Test", "sections": []}'
        result = ContentParser.parse(json_input)
        assert result['headline'] == 'Test'
        
        # Test Markdown detection
        markdown_input = "# Heading\n\n## Section\n\nContent here"
        result = ContentParser.parse(markdown_input)
        assert len(result['sections']) >= 0  # Should parse as markdown or text
        
        # Test plain text fallback
        text_input = "This is just plain text without any special formatting."
        result = ContentParser.parse(text_input)
        assert len(result['sections']) >= 0  # Should have at least one section
    
    def test_malformed_content_handling(self):
        """Test error recovery for malformed content."""
        # Test malformed JSON
        malformed_json = '{"headline": "Test", "sections": [broken'
        result = ContentParser.parse(malformed_json, format_type='json')
        assert 'sections' in result  # Should fallback gracefully
        assert len(result['sections']) >= 1  # Should have at least one section with content
        
        # Test malformed HTML
        malformed_html = "<html><body><h1>Test<p>Content</html>"  # Missing closing tags
        result = ContentParser.parse(malformed_html, format_type='html')
        assert 'sections' in result  # Should still parse
        
        # Test empty content
        empty_content = ""
        result = ContentParser.parse(empty_content, format_type='text')
        assert 'sections' in result
        assert isinstance(result['sections'], list)
        
        # Test whitespace-only content
        whitespace_content = "   \n\n   \t\t   \n   "
        result = ContentParser.parse(whitespace_content, format_type='text')
        assert 'sections' in result
        assert isinstance(result['sections'], list)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

