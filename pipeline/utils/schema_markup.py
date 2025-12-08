"""JSON-LD schema markup generation for SEO and AEO optimization."""

import json
import re
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..models.output_schema import ArticleOutput


def generate_article_schema(
    output: ArticleOutput,
    company_data: Optional[Dict[str, Any]] = None,
    article_url: Optional[str] = None,
    validated_citations: Optional[List] = None,
) -> Dict:
    """
    Generate comprehensive JSON-LD Article schema markup.
    
    Enhanced for AEO with:
    - Author/datePublished/dateModified
    - Direct answer as acceptedAnswer
    - Publisher Organization
    - ImageObject
    
    Args:
        output: ArticleOutput instance
        company_data: Company metadata
        article_url: Full URL to article
        
    Returns:
        Dict representing JSON-LD Article schema
    """
    # Helper to strip HTML and remove AI markers (em dashes, etc.)
    def _clean_text(text: str) -> str:
        """Strip HTML, humanize text (remove em dashes), and strip citation markers."""
        if not text:
            return ""
        # Strip HTML first
        cleaned = _strip_html(text)
        # Remove em dashes (replace with commas)
        cleaned = cleaned.replace("—", ", ")
        # Remove robotic phrases
        cleaned = cleaned.replace("Here's how ", "")
        cleaned = cleaned.replace("Here's what ", "")
        cleaned = cleaned.replace("Key points: ", "")
        # Strip citation markers [N] - CRITICAL FIX
        import re
        cleaned = re.sub(r'\[\d+\]', '', cleaned)
        # Clean up double spaces
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned.strip()
    
    # Extract text content for description
    intro_text = _clean_text(output.Intro)
    description = intro_text[:160] if intro_text else _clean_text(output.Meta_Description)
    
    # Use direct answer for description if available (AEO optimization)
    if output.Direct_Answer:
        direct_answer_text = _clean_text(output.Direct_Answer)
        if direct_answer_text:
            description = direct_answer_text[:160]
    
    company_name = company_data.get("company_name", "Company") if company_data else "Company"
    company_url = company_data.get("company_url", "") if company_data else ""
    
    schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": _clean_text(output.Headline),  # Clean headline (no HTML, no em dashes)
        "description": description,
        "datePublished": datetime.now().isoformat(),
        "dateModified": datetime.now().isoformat(),
        "author": {
            "@type": "Organization",
            "name": company_name
        },
        "publisher": {
            "@type": "Organization",
            "name": company_name
        }
    }
    
    # Add publisher URL if available
    if company_url:
        schema["publisher"]["url"] = company_url
    
    # Add article URL
    if article_url:
        schema["url"] = article_url
    
    # Add subtitle
    if output.Subtitle:
        schema["alternativeHeadline"] = _clean_text(output.Subtitle)
    
    # Add direct answer as acceptedAnswer for AEO (if available)
    if output.Direct_Answer:
        direct_answer_text = _clean_text(output.Direct_Answer)
        if direct_answer_text:
            schema["acceptedAnswer"] = {
                "@type": "Answer",
                "text": direct_answer_text
            }
    
    # Add article body
    article_body = output.Intro + " " + _get_all_section_content(output)
    schema["articleBody"] = _clean_text(article_body)
    
    # Add ImageObject if image URL provided
    if output.image_url:
        image_obj = {
            "@type": "ImageObject",
            "url": output.image_url
        }
        if output.image_alt_text:
            image_obj["caption"] = output.image_alt_text
        schema["image"] = image_obj
    
    # v3.2: Add citation property for AEO (AI crawlers parse this)
    # CRITICAL FIX: Use validated citations if available (excludes invalid 404 URLs)
    if validated_citations:
        citations = _parse_citations_from_validated_list(validated_citations)
        if citations:
            schema["citation"] = citations
    elif hasattr(output, 'Sources') and output.Sources:
        # Fallback: Parse from Sources field if validated citations not available
        citations = _parse_citations_from_sources(output.Sources)
        if citations:
            schema["citation"] = citations
    
    # Add author schema for E-E-A-T if author info provided
    if company_data:
        author_name = company_data.get('author_name')
        if author_name:
            author_schema = generate_author_schema(
                author_name=author_name,
                author_bio=company_data.get('author_bio'),
                author_url=company_data.get('author_url'),
            )
            schema["author"] = author_schema
    
    return schema


def generate_faqpage_schema(
    output: ArticleOutput,
    faq_items: Optional[List[Dict[str, str]]] = None,
) -> Optional[Dict]:
    """
    Generate JSON-LD FAQPage schema.
    
    Args:
        output: ArticleOutput instance
        faq_items: List of FAQ items with 'question' and 'answer' keys
        
    Returns:
        Dict representing FAQPage schema or None if no FAQs
    """
    # Extract FAQs from output if not provided
    if not faq_items:
        faq_items = []
        for i in range(1, 7):
            q_field = getattr(output, f"faq_{i:02d}_question", "")
            a_field = getattr(output, f"faq_{i:02d}_answer", "")
            if q_field and a_field:
                faq_items.append({
                    "question": q_field,
                    "answer": a_field
                })
    
    if not faq_items:
        return None
    
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": item["question"],
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": _strip_html(item["answer"])
                }
            }
            for item in faq_items
        ]
    }


def generate_breadcrumb_schema(
    output: ArticleOutput,
    base_url: Optional[str] = None,
    article_url: Optional[str] = None,
) -> Optional[Dict]:
    """
    Generate JSON-LD BreadcrumbList schema.
    
    Args:
        output: ArticleOutput instance
        base_url: Base URL for breadcrumbs
        article_url: Full URL to article
        
    Returns:
        Dict representing BreadcrumbList schema or None
    """
    if not base_url:
        return None
    
    items = [
        {
            "@type": "ListItem",
            "position": 1,
            "name": "Home",
            "item": base_url
        },
        {
            "@type": "ListItem",
            "position": 2,
            "name": "Blog",
            "item": f"{base_url}/blog"
        }
    ]
    
    if article_url:
        items.append({
            "@type": "ListItem",
            "position": 3,
            "name": output.Headline,
            "item": article_url
        })
    
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": items
    }


def generate_organization_schema(
    company_name: str,
    company_url: Optional[str] = None,
    logo_url: Optional[str] = None,
) -> Dict:
    """
    Generate JSON-LD Organization schema.
    
    Args:
        company_name: Company name
        company_url: Company website URL
        logo_url: Company logo URL
        
    Returns:
        Dict representing Organization schema
    """
    schema = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": company_name
    }
    
    if company_url:
        schema["url"] = company_url
    
    if logo_url:
        schema["logo"] = {
            "@type": "ImageObject",
            "url": logo_url
        }
    
    return schema


def generate_howto_schema(
    steps: List[Dict[str, str]],
    name: str,
    description: Optional[str] = None,
) -> Dict:
    """
    Generate JSON-LD HowTo schema for guides/tutorials.
    
    Args:
        steps: List of step dicts with "name" and "text" keys
        name: HowTo name/title
        description: Optional description
        
    Returns:
        Dict representing HowTo schema
    """
    schema = {
        "@context": "https://schema.org",
        "@type": "HowTo",
        "name": name,
    }
    
    if description:
        schema["description"] = description
    
    if steps:
        schema["step"] = [
            {
                "@type": "HowToStep",
                "name": step.get("name", ""),
                "text": step.get("text", ""),
                "position": idx + 1,
            }
            for idx, step in enumerate(steps)
        ]
    
    return schema


def generate_author_schema(
    author_name: str,
    author_bio: Optional[str] = None,
    author_url: Optional[str] = None,
) -> Dict:
    """
    Generate JSON-LD Person/Author schema (E-E-A-T).
    
    Args:
        author_name: Author's name
        author_bio: Optional author biography
        author_url: Optional author URL/profile
        
    Returns:
        Dict representing Person schema
    """
    schema = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": author_name,
    }
    
    if author_bio:
        schema["description"] = author_bio
    
    if author_url:
        schema["url"] = author_url
    
    return schema


def generate_all_schemas(
    output: ArticleOutput,
    company_data: Optional[Dict[str, Any]] = None,
    article_url: Optional[str] = None,
    base_url: Optional[str] = None,
    faq_items: Optional[List[Dict[str, str]]] = None,
    validated_citations: Optional[List] = None,
) -> List[Dict]:
    """
    Generate all relevant schemas for an article.
    
    Args:
        validated_citations: Optional CitationList with validated citations (invalid URLs filtered out)
    
    Returns:
        List of schema dicts
    """
    schemas = []
    
    # Article schema (always)
    article_schema = generate_article_schema(output, company_data, article_url, validated_citations)
    schemas.append(article_schema)
    
    # FAQPage schema (if FAQs exist)
    faq_schema = generate_faqpage_schema(output, faq_items)
    if faq_schema:
        schemas.append(faq_schema)
    
    # Organization schema (if company data)
    if company_data:
        company_name = company_data.get("company_name")
        company_url = company_data.get("company_url")
        if company_name:
            org_schema = generate_organization_schema(
                company_name=company_name,
                company_url=company_url,
                logo_url=company_data.get("logo_url")
            )
            schemas.append(org_schema)
    
    # BreadcrumbList schema (if base URL provided)
    if base_url:
        breadcrumb_schema = generate_breadcrumb_schema(output, base_url, article_url)
        if breadcrumb_schema:
            schemas.append(breadcrumb_schema)
    
    return schemas


def render_schemas_as_json_ld(schemas: List[Dict]) -> str:
    """
    Render schemas as JSON-LD script tags.
    
    Args:
        schemas: List of schema dicts
        
    Returns:
        HTML string with JSON-LD script tags
    """
    script_tags = []
    for schema in schemas:
        json_str = json.dumps(schema, indent=2, ensure_ascii=False)
        script_tags.append(f'<script type="application/ld+json">\n{json_str}\n</script>')
    
    return "\n".join(script_tags)


def _strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


def _get_all_section_content(output: ArticleOutput) -> str:
    """Get all section content as a single string."""
    sections = [
        output.section_01_content, output.section_02_content, output.section_03_content,
        output.section_04_content, output.section_05_content, output.section_06_content,
        output.section_07_content, output.section_08_content, output.section_09_content,
    ]
    return " ".join(s for s in sections if s)


def _parse_citations_from_validated_list(validated_citations) -> List[Dict]:
    """
    Parse validated CitationList to extract citations for JSON-LD schema.
    
    CRITICAL FIX: Uses validated citations (invalid 404 URLs already filtered out).
    
    Args:
        validated_citations: CitationList object with validated citations
        
    Returns:
        List of citation dicts for schema.org citation property
    """
    if not validated_citations:
        return []
    
    citations = []
    
    # Check if it's a CitationList object
    if hasattr(validated_citations, 'citations'):
        citation_list = validated_citations.citations
    elif isinstance(validated_citations, list):
        citation_list = validated_citations
    else:
        return []
    
    for citation in citation_list:
        if hasattr(citation, 'url') and hasattr(citation, 'title'):
            citation_dict = {
                "@type": "CreativeWork",
                "url": citation.url.strip(),
                "name": citation.title.strip()
            }
            citations.append(citation_dict)
    
    return citations


def _parse_citations_from_sources(sources: str) -> List[Dict]:
    """
    Parse Sources field to extract citations for JSON-LD schema (v3.2).
    
    Format expected:
    [1]: https://example.com/page – Description text
    [2]: https://example.com/page2 – Another description
    
    Args:
        sources: Raw sources string from article
        
    Returns:
        List of citation dicts for schema.org citation property
    """
    if not sources:
        return []
    
    citations = []
    
    # Pattern: [N]: URL – Description
    pattern = r'\[(\d+)\]:\s*(https?://[^\s]+)\s*[–-]\s*(.+?)(?=\n\[|\n*$)'
    matches = re.findall(pattern, sources, re.MULTILINE | re.DOTALL)
    
    for num, url, title in matches:
        citation = {
            "@type": "CreativeWork",
            "url": url.strip(),
            "name": title.strip()
        }
        citations.append(citation)
    
    return citations

