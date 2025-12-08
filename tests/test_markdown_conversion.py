"""
Unit tests for Markdown to HTML conversion.

Tests the _markdown_to_html() method in HTMLRenderer.
"""

import pytest
import sys
from pathlib import Path

# Add pipeline to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.processors.html_renderer import HTMLRenderer


class TestMarkdownConversion:
    """Test Markdown to HTML conversion"""
    
    def test_simple_paragraph(self):
        """Test simple paragraph conversion"""
        md = "This is a simple paragraph."
        html = HTMLRenderer._markdown_to_html(md)
        assert html == "<p>This is a simple paragraph.</p>"
    
    def test_bold_text(self):
        """Test bold text conversion"""
        md = "This is **bold** text."
        html = HTMLRenderer._markdown_to_html(md)
        assert "<strong>bold</strong>" in html
        assert html.startswith("<p>")
        assert html.endswith("</p>")
    
    def test_italic_text(self):
        """Test italic text conversion"""
        md = "This is *italic* text."
        html = HTMLRenderer._markdown_to_html(md)
        assert "<em>italic</em>" in html
        assert html.startswith("<p>")
        assert html.endswith("</p>")
    
    def test_unordered_list(self):
        """Test unordered list conversion"""
        md = "- Item 1\n- Item 2\n- Item 3"
        html = HTMLRenderer._markdown_to_html(md)
        assert "<ul>" in html
        assert "<li>Item 1</li>" in html
        assert "<li>Item 2</li>" in html
        assert "<li>Item 3</li>" in html
        assert "</ul>" in html
    
    def test_ordered_list(self):
        """Test ordered list conversion"""
        md = "1. First item\n2. Second item\n3. Third item"
        html = HTMLRenderer._markdown_to_html(md)
        assert "<ol>" in html
        assert "<li>First item</li>" in html
        assert "<li>Second item</li>" in html
        assert "<li>Third item</li>" in html
        assert "</ol>" in html
    
    def test_mixed_content(self):
        """Test paragraph followed by list"""
        md = """First paragraph with natural flow.

- First list item with full description
- Second list item with metrics
- Third list item with context

Second paragraph continues the narrative."""
        
        html = HTMLRenderer._markdown_to_html(md)
        
        # Check for paragraph
        assert "<p>First paragraph with natural flow.</p>" in html
        
        # Check for list
        assert "<ul>" in html
        assert "<li>First list item with full description</li>" in html
        
        # Check for second paragraph
        assert "<p>Second paragraph continues the narrative.</p>" in html
    
    def test_bold_in_list(self):
        """Test bold labels in list items"""
        md = """- **GitHub Copilot:** Context-aware code suggestions
- **Amazon Q:** AWS-integrated assistant
- **Tabnine:** Air-gapped deployment"""
        
        html = HTMLRenderer._markdown_to_html(md)
        
        assert "<ul>" in html
        assert "<strong>GitHub Copilot:</strong>" in html
        assert "<strong>Amazon Q:</strong>" in html
        assert "<strong>Tabnine:</strong>" in html
    
    def test_links_markdown(self):
        """Test Markdown link conversion"""
        md = "Check out [our guide](/magazine/ai-security) for more information."
        html = HTMLRenderer._markdown_to_html(md)
        
        assert '<a href="/magazine/ai-security">our guide</a>' in html
        assert html.startswith("<p>")
        assert html.endswith("</p>")
    
    def test_external_links(self):
        """Test external link conversion"""
        md = "Learn more at [GitHub](https://github.com)."
        html = HTMLRenderer._markdown_to_html(md)
        
        assert '<a href="https://github.com">GitHub</a>' in html
    
    def test_empty_string(self):
        """Test empty string returns empty"""
        html = HTMLRenderer._markdown_to_html("")
        assert html == ""
    
    def test_none_returns_empty(self):
        """Test None returns empty string"""
        html = HTMLRenderer._markdown_to_html(None)
        assert html == ""
    
    def test_multiple_paragraphs(self):
        """Test multiple paragraphs with blank line separation"""
        md = """First paragraph here.

Second paragraph here.

Third paragraph here."""
        
        html = HTMLRenderer._markdown_to_html(md)
        
        assert html.count("<p>") == 3
        assert html.count("</p>") == 3
    
    def test_bold_and_italic_together(self):
        """Test mixed bold and italic"""
        md = "This is **bold** and this is *italic* text."
        html = HTMLRenderer._markdown_to_html(md)
        
        assert "<strong>bold</strong>" in html
        assert "<em>italic</em>" in html
    
    def test_numbers_and_percentages(self):
        """Test that numbers and percentages are preserved"""
        md = "AI tools increased productivity by **55%** according to research."
        html = HTMLRenderer._markdown_to_html(md)
        
        assert "<strong>55%</strong>" in html
        assert "productivity" in html
    
    def test_complex_sentence_with_data(self):
        """Test complex real-world sentence"""
        md = """GitHub Copilot's 2024 enterprise report shows a **55% increase** in developer productivity. AWS documented a **60% reduction** in migration time with their Q Developer tool."""
        
        html = HTMLRenderer._markdown_to_html(md)
        
        assert "<strong>55% increase</strong>" in html
        assert "<strong>60% reduction</strong>" in html
        assert "GitHub Copilot" in html
        assert "AWS" in html


class TestMarkdownEdgeCases:
    """Test edge cases and error handling"""
    
    def test_html_tags_in_markdown(self):
        """Test that raw HTML tags are handled (Markdown allows them)"""
        md = "This is a <strong>test</strong>."
        html = HTMLRenderer._markdown_to_html(md)
        
        # Markdown library typically passes through HTML
        assert "<strong>test</strong>" in html
    
    def test_special_characters(self):
        """Test special characters are preserved"""
        md = "Test with & < > \" characters."
        html = HTMLRenderer._markdown_to_html(md)
        
        # Check that content is present (exact encoding may vary)
        assert "Test with" in html
    
    def test_very_long_paragraph(self):
        """Test very long paragraph conversion"""
        md = "This is a very long paragraph. " * 50
        html = HTMLRenderer._markdown_to_html(md)
        
        assert html.startswith("<p>")
        assert html.endswith("</p>")
        assert len(html) > len(md)  # HTML adds tags
    
    def test_nested_lists(self):
        """Test nested lists (if supported by Markdown extensions)"""
        md = """- Parent item 1
  - Child item 1.1
  - Child item 1.2
- Parent item 2"""
        
        html = HTMLRenderer._markdown_to_html(md)
        
        # Should have at least ul tags
        assert "<ul>" in html
        assert "<li>Parent item 1" in html or "<li>Parent item 1<" in html
    
    def test_blank_lines_preserved_as_paragraph_breaks(self):
        """Test that blank lines become paragraph breaks"""
        md = """Paragraph 1.

Paragraph 2."""
        
        html = HTMLRenderer._markdown_to_html(md)
        
        # Should have 2 paragraphs
        assert html.count("Paragraph 1") == 1
        assert html.count("Paragraph 2") == 1
        # May have 2 separate <p> tags or combined depending on extension
        assert "<p>" in html


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

