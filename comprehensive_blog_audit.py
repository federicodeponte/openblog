#!/usr/bin/env python3
"""
Comprehensive Blog Audit - Check All Missing Elements
Audits generated blogs for:
1. Citations/References section 
2. Source validation and accessibility
3. Internal linkage within batch
4. Author data and metadata completeness
5. Schema compliance and SEO elements
"""
import sys
import os
import json
import re
import requests
from urllib.parse import urlparse
from datetime import datetime
import asyncio

def audit_blog_html(html_file):
    """Comprehensive audit of a generated blog HTML file"""
    
    print(f"🔍 AUDITING: {html_file}")
    print("=" * 60)
    
    if not os.path.exists(html_file):
        print(f"❌ File not found: {html_file}")
        return None
    
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    audit_results = {
        'file': html_file,
        'timestamp': datetime.now().isoformat(),
        'citations': {},
        'metadata': {},
        'internal_links': {},
        'content_quality': {},
        'schema_compliance': {}
    }
    
    # 1. CITATIONS/REFERENCES AUDIT
    print("\n📚 CITATIONS & REFERENCES AUDIT")
    print("-" * 40)
    
    # Check for inline citations
    inline_citations = re.findall(r'<a[^>]+href\s*=\s*["\']([^"\']*)["\'][^>]*>', content)
    citation_count = len(inline_citations)
    
    # Check for References section
    has_references_section = bool(re.search(r'<h[2-6][^>]*>.*?(?:References|Sources|Bibliography).*?</h[2-6]>', content, re.IGNORECASE))
    
    # Check for numbered citation format
    numbered_citations = re.findall(r'\[(\d+)\]', content)
    
    # Analyze citation URLs
    external_urls = [url for url in inline_citations if url.startswith('http')]
    internal_urls = [url for url in inline_citations if not url.startswith('http') and not url.startswith('#')]
    placeholder_urls = [url for url in inline_citations if url.startswith('#source-')]
    
    print(f"📊 Citation Statistics:")
    print(f"  • Total inline citations: {citation_count}")
    print(f"  • External URLs: {len(external_urls)}")
    print(f"  • Internal URLs: {len(internal_urls)}")
    print(f"  • Placeholder citations: {len(placeholder_urls)}")
    print(f"  • Numbered citations [1]: {len(numbered_citations)}")
    print(f"  • Has References section: {'✅' if has_references_section else '❌'}")
    
    audit_results['citations'] = {
        'total_count': citation_count,
        'external_urls': external_urls,
        'internal_urls': internal_urls,
        'placeholder_count': len(placeholder_urls),
        'numbered_citations': numbered_citations,
        'has_references_section': has_references_section
    }
    
    # 2. SOURCE VALIDATION
    print(f"\n🔗 SOURCE VALIDATION")
    print("-" * 40)
    
    validated_sources = []
    broken_sources = []
    
    if external_urls:
        print(f"Checking {len(external_urls)} external sources...")
        for i, url in enumerate(external_urls[:10]):  # Limit to first 10 for speed
            try:
                response = requests.head(url, timeout=5, allow_redirects=True)
                status = response.status_code
                domain = urlparse(url).netloc
                
                if 200 <= status < 400:
                    validated_sources.append({'url': url, 'status': status, 'domain': domain})
                    print(f"  ✅ [{i+1}] {domain} - HTTP {status}")
                else:
                    broken_sources.append({'url': url, 'status': status, 'domain': domain})
                    print(f"  ❌ [{i+1}] {domain} - HTTP {status}")
                    
            except Exception as e:
                broken_sources.append({'url': url, 'error': str(e), 'domain': urlparse(url).netloc})
                print(f"  💥 [{i+1}] {urlparse(url).netloc} - ERROR: {str(e)[:50]}")
    else:
        print("⚠️  No external URLs found to validate")
    
    audit_results['citations']['validated_sources'] = validated_sources
    audit_results['citations']['broken_sources'] = broken_sources
    
    # 3. INTERNAL LINKAGE AUDIT
    print(f"\n🔗 INTERNAL LINKAGE AUDIT") 
    print("-" * 40)
    
    # Find internal links
    internal_link_patterns = [
        r'/[^/\s"\']*',  # Absolute paths
        r'\.\.?/[^/\s"\']*',  # Relative paths
        r'#[a-zA-Z][\w-]*'  # Anchor links
    ]
    
    all_internal_links = []
    for pattern in internal_link_patterns:
        matches = re.findall(r'href\s*=\s*["\'](' + pattern + r')["\']', content)
        all_internal_links.extend(matches)
    
    # Categorize internal links
    topic_links = [link for link in all_internal_links if '/magazine/' in link or '/blog/' in link]
    anchor_links = [link for link in all_internal_links if link.startswith('#')]
    relative_links = [link for link in all_internal_links if link.startswith('/') and not link.startswith('/magazine/') and not link.startswith('/blog/')]
    
    print(f"📊 Internal Link Statistics:")
    print(f"  • Total internal links: {len(all_internal_links)}")
    print(f"  • Topic-based links: {len(topic_links)}")
    print(f"  • Anchor links: {len(anchor_links)}")
    print(f"  • Other relative links: {len(relative_links)}")
    
    if topic_links:
        print(f"  📄 Topic Links Found:")
        for link in topic_links[:5]:  # Show first 5
            print(f"    → {link}")
    
    audit_results['internal_links'] = {
        'total_count': len(all_internal_links),
        'topic_links': topic_links,
        'anchor_links': anchor_links,
        'relative_links': relative_links
    }
    
    # 4. AUTHOR & METADATA AUDIT
    print(f"\n👤 AUTHOR & METADATA AUDIT")
    print("-" * 40)
    
    # Check for author information
    author_patterns = [
        r'<meta[^>]+name\s*=\s*["\']author["\'][^>]+content\s*=\s*["\']([^"\']+)["\']',
        r'<span[^>]*class[^>]*author[^>]*>([^<]+)</span>',
        r'By\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
        r'Written by\s+([A-Z][a-z]+\s+[A-Z][a-z]+)'
    ]
    
    authors_found = []
    for pattern in author_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        authors_found.extend(matches)
    
    # Check for publication metadata
    pub_date_patterns = [
        r'<meta[^>]+name\s*=\s*["\'](?:date|published)["\'][^>]+content\s*=\s*["\']([^"\']+)["\']',
        r'<time[^>]*datetime\s*=\s*["\']([^"\']+)["\']',
        r'Published:?\s*([A-Za-z]+ \d+, \d{4})'
    ]
    
    pub_dates_found = []
    for pattern in pub_date_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        pub_dates_found.extend(matches)
    
    # Check for meta tags
    meta_tags = re.findall(r'<meta[^>]+name\s*=\s*["\']([^"\']+)["\'][^>]+content\s*=\s*["\']([^"\']+)["\']', content)
    meta_dict = dict(meta_tags)
    
    print(f"📊 Metadata Statistics:")
    print(f"  • Authors found: {len(authors_found)} - {authors_found[:3] if authors_found else 'None'}")
    print(f"  • Publication dates: {len(pub_dates_found)} - {pub_dates_found[:2] if pub_dates_found else 'None'}")
    print(f"  • Meta tags found: {len(meta_tags)}")
    
    if meta_dict:
        print(f"  📋 Key Meta Tags:")
        for key in ['description', 'keywords', 'og:title', 'twitter:card'][:4]:
            if key in meta_dict:
                print(f"    → {key}: {meta_dict[key][:50]}{'...' if len(meta_dict[key]) > 50 else ''}")
    
    audit_results['metadata'] = {
        'authors': authors_found,
        'publication_dates': pub_dates_found,
        'meta_tags': meta_dict,
        'has_author': len(authors_found) > 0,
        'has_pub_date': len(pub_dates_found) > 0
    }
    
    # 5. CONTENT QUALITY AUDIT
    print(f"\n📝 CONTENT QUALITY AUDIT")
    print("-" * 40)
    
    # Word count
    text_content = re.sub(r'<[^>]+>', '', content)
    word_count = len(text_content.split())
    
    # Section structure
    headings = re.findall(r'<h([1-6])[^>]*>([^<]+)</h[1-6]>', content)
    h1_count = len([h for h in headings if h[0] == '1'])
    h2_count = len([h for h in headings if h[0] == '2'])
    h3_count = len([h for h in headings if h[0] == '3'])
    
    # FAQ and PAA sections
    faq_sections = re.findall(r'<h[2-6][^>]*>.*?(?:FAQ|Frequently Asked).*?</h[2-6]>', content, re.IGNORECASE)
    paa_sections = re.findall(r'<h[2-6][^>]*>.*?(?:People Also Ask|PAA).*?</h[2-6]>', content, re.IGNORECASE)
    
    # Count FAQ and PAA items
    faq_items = len(re.findall(r'<h[3-6][^>]*>.*?\?.*?</h[3-6]>', content))
    
    print(f"📊 Content Quality Statistics:")
    print(f"  • Word count: {word_count:,} words")
    print(f"  • H1 headings: {h1_count}")
    print(f"  • H2 headings: {h2_count}")  
    print(f"  • H3 headings: {h3_count}")
    print(f"  • FAQ sections: {len(faq_sections)}")
    print(f"  • PAA sections: {len(paa_sections)}")
    print(f"  • FAQ items: {faq_items}")
    
    audit_results['content_quality'] = {
        'word_count': word_count,
        'headings': {'h1': h1_count, 'h2': h2_count, 'h3': h3_count},
        'faq_sections': len(faq_sections),
        'paa_sections': len(paa_sections),
        'faq_items': faq_items
    }
    
    # 6. SCHEMA COMPLIANCE AUDIT
    print(f"\n🏗️ SCHEMA COMPLIANCE AUDIT")
    print("-" * 40)
    
    # Check for schema.org markup
    schema_scripts = re.findall(r'<script[^>]+type\s*=\s*["\']application/ld\+json["\'][^>]*>([^<]+)</script>', content, re.DOTALL)
    
    # Check for Open Graph tags
    og_tags = {k: v for k, v in meta_dict.items() if k.startswith('og:')}
    
    # Check for Twitter Card tags
    twitter_tags = {k: v for k, v in meta_dict.items() if k.startswith('twitter:')}
    
    # Check for article schema fields
    has_article_schema = any('Article' in script for script in schema_scripts)
    
    print(f"📊 Schema Compliance:")
    print(f"  • JSON-LD scripts: {len(schema_scripts)}")
    print(f"  • Article schema: {'✅' if has_article_schema else '❌'}")
    print(f"  • Open Graph tags: {len(og_tags)}")
    print(f"  • Twitter Card tags: {len(twitter_tags)}")
    
    audit_results['schema_compliance'] = {
        'json_ld_scripts': len(schema_scripts),
        'has_article_schema': has_article_schema,
        'og_tags': og_tags,
        'twitter_tags': twitter_tags
    }
    
    # OVERALL ASSESSMENT
    print(f"\n🎯 OVERALL ASSESSMENT")
    print("-" * 40)
    
    # Calculate completion score
    scores = {
        'citations': 1 if has_references_section and len(external_urls) > 5 else 0.5 if len(external_urls) > 0 else 0,
        'metadata': 1 if authors_found and pub_dates_found else 0.5 if authors_found or pub_dates_found else 0,
        'internal_links': 1 if len(topic_links) > 3 else 0.5 if len(topic_links) > 0 else 0,
        'content_quality': 1 if word_count > 1000 and h2_count > 3 else 0.5 if word_count > 500 else 0,
        'schema_compliance': 1 if has_article_schema and len(og_tags) > 3 else 0.5 if len(og_tags) > 0 else 0
    }
    
    overall_score = sum(scores.values()) / len(scores) * 100
    
    print(f"📊 Completion Scores:")
    for category, score in scores.items():
        status = "✅ Complete" if score >= 1 else "⚠️ Partial" if score >= 0.5 else "❌ Missing"
        print(f"  • {category.replace('_', ' ').title()}: {score*100:.0f}% - {status}")
    
    print(f"\n🏆 OVERALL SCORE: {overall_score:.1f}%")
    
    if overall_score >= 80:
        print("🎉 EXCELLENT - Production ready with comprehensive features")
    elif overall_score >= 60:
        print("✅ GOOD - Solid foundation with some enhancements needed") 
    elif overall_score >= 40:
        print("⚠️ FAIR - Basic functionality but missing key elements")
    else:
        print("❌ POOR - Major elements missing, requires significant work")
    
    audit_results['overall_score'] = overall_score
    audit_results['scores'] = scores
    
    return audit_results

def audit_multiple_blogs():
    """Audit all available blog files"""
    
    print("🔍 COMPREHENSIVE BLOG AUDIT SYSTEM")
    print("=" * 60)
    print("Checking all generated blogs for completeness...")
    
    # Find all HTML files
    html_files = []
    for file in os.listdir('.'):
        if file.endswith('.html') and ('blog' in file.lower() or 'isaac' in file.lower()):
            html_files.append(file)
    
    if not html_files:
        print("❌ No blog HTML files found in current directory")
        return
    
    print(f"📄 Found {len(html_files)} blog files to audit:")
    for i, file in enumerate(html_files, 1):
        print(f"  {i}. {file}")
    
    # Audit each blog
    all_results = []
    for file in html_files:
        print(f"\n" + "="*80)
        result = audit_blog_html(file)
        if result:
            all_results.append(result)
        print(f"\n" + "="*80)
    
    # Generate summary report
    if all_results:
        print(f"\n📊 BATCH AUDIT SUMMARY")
        print("=" * 60)
        
        avg_score = sum(r['overall_score'] for r in all_results) / len(all_results)
        
        print(f"📄 Blogs audited: {len(all_results)}")
        print(f"🏆 Average score: {avg_score:.1f}%")
        
        # Category breakdown
        categories = ['citations', 'metadata', 'internal_links', 'content_quality', 'schema_compliance']
        print(f"\n📊 Category Performance:")
        for category in categories:
            avg_cat_score = sum(r['scores'][category] for r in all_results) / len(all_results) * 100
            print(f"  • {category.replace('_', ' ').title()}: {avg_cat_score:.1f}%")
        
        # Save detailed results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = f"blog_audit_results_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(all_results, f, indent=2, default=str)
        
        print(f"\n💾 Detailed results saved to: {results_file}")
        
        return all_results
    
    return None

if __name__ == "__main__":
    audit_multiple_blogs()