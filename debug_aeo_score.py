#!/usr/bin/env python3
"""
Debug AEO Score - Analyze why score is low (75/100).

This script loads the latest article and calculates detailed AEO scores
to identify which components are failing.
"""

import sys
import json
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from pipeline.utils.aeo_scorer import AEOScorer
from pipeline.models.output_schema import ArticleOutput

def main():
    # Find latest article JSON
    output_dir = Path("output/html_first_test")
    json_files = list(output_dir.glob("**/*.json"))
    if not json_files:
        print("❌ No JSON files found in output/html_first_test")
        return
    
    # Get most recent JSON file
    latest_json = max(json_files, key=lambda p: p.stat().st_mtime)
    print(f"📄 Loading: {latest_json}")
    
    with open(latest_json, 'r') as f:
        article_data = json.load(f)
    
    # Convert to ArticleOutput
    try:
        article_output = ArticleOutput(**article_data)
    except Exception as e:
        print(f"❌ Failed to parse ArticleOutput: {e}")
        return
    
    # Get primary keyword from article data or default
    primary_keyword = article_data.get("primary_keyword", "cybersecurity automation")
    
    # Calculate detailed AEO scores
    scorer = AEOScorer()
    
    print("\n" + "="*80)
    print("AEO SCORE BREAKDOWN")
    print("="*80)
    
    # 1. Direct Answer (25 points)
    da_score = scorer._score_direct_answer(article_output, primary_keyword)
    da_words = len(article_output.Direct_Answer.split()) if article_output.Direct_Answer else 0
    da_has_keyword = primary_keyword.lower() in (article_output.Direct_Answer or "").lower()
    da_has_citation = bool(
        re.search(r'\[\d+\]', article_output.Direct_Answer or "") or
        re.search(r'according to [A-Z]', article_output.Direct_Answer or "", re.IGNORECASE) or
        re.search(r'[A-Z][a-z]+ (reports?|states?|notes?|found)', article_output.Direct_Answer or "")
    )
    print(f"\n1. Direct Answer: {da_score}/25")
    print(f"   - Exists: ✅ (10 points)")
    print(f"   - Length: {da_words} words ({'✅ 40-60' if 40 <= da_words <= 60 else '⚠️ 60-80' if 60 < da_words <= 80 else '❌ <30 or >80'} = {5.0 if 40 <= da_words <= 60 else 2.5 if 60 < da_words <= 80 else 0} points)")
    print(f"   - Keyword: {'✅' if da_has_keyword else '❌'} ({'5.0' if da_has_keyword else '0'} points)")
    print(f"   - Citation: {'✅' if da_has_citation else '❌'} ({'5.0' if da_has_citation else '0'} points)")
    
    # 2. Q&A Format (20 points)
    qa_score = scorer._score_qa_format(article_output)
    faq_count = article_output.get_active_faqs()
    paa_count = article_output.get_active_paas()
    print(f"\n2. Q&A Format: {qa_score}/20")
    print(f"   - FAQ: {faq_count} items ({'✅ 5+' if faq_count >= 5 else '⚠️ 3-4' if faq_count >= 3 else '❌ <3'} = {10.0 if faq_count >= 5 else 7.0 if faq_count >= 3 else 3.0 if faq_count > 0 else 0} points)")
    print(f"   - PAA: {paa_count} items ({'✅ 3+' if paa_count >= 3 else '⚠️ 2' if paa_count >= 2 else '❌ <2'} = {5.0 if paa_count >= 3 else 3.0 if paa_count >= 2 else 1.0 if paa_count > 0 else 0} points)")
    
    # 3. Citation Clarity (15 points)
    citation_score = scorer._score_citation_clarity(article_output)
    print(f"\n3. Citation Clarity: {citation_score}/15")
    
    # 4. Natural Language (15 points)
    nl_score = scorer._score_natural_language(article_output, primary_keyword)
    all_content = article_output.Intro + " " + scorer._get_all_section_content(article_output)
    content_lower = all_content.lower()
    
    conversational_phrases = [
        "how to", "what is", "why does", "when should", "where can",
        "you can", "you'll", "you should", "let's", "here's", "this is",
        "how can", "what are", "how do", "why should", "where are",
        "we'll", "that's", "when you", "if you", "so you can", "which means",
    ]
    phrase_count = sum(1 for phrase in conversational_phrases if phrase in content_lower)
    
    question_patterns = [
        r"what is", r"how do", r"why does", r"when should", r"where can",
        r"how can", r"what are",
    ]
    import re
    question_count = sum(1 for pattern in question_patterns if re.search(pattern, content_lower))
    
    print(f"\n4. Natural Language: {nl_score}/15")
    print(f"   - Conversational phrases: {phrase_count} ({'✅ 8+' if phrase_count >= 8 else '⚠️ 5-7' if phrase_count >= 5 else '❌ <5'} = {6.0 if phrase_count >= 8 else 4.0 if phrase_count >= 5 else 2.0 if phrase_count >= 2 else 0} points)")
    print(f"   - Question patterns: {question_count} ({'✅ 5+' if question_count >= 5 else '⚠️ 3-4' if question_count >= 3 else '❌ <3'} = {4.0 if question_count >= 5 else 3.0 if question_count >= 3 else 1.5 if question_count >= 1 else 0} points)")
    
    # 5. Structured Data (10 points)
    struct_score = scorer._score_structured_data(article_output)
    print(f"\n5. Structured Data: {struct_score}/10")
    
    # 6. E-E-A-T (15 points)
    eat_score = scorer._score_eat(article_output, None)
    print(f"\n6. E-E-A-T: {eat_score}/15")
    
    # Total
    total_score = scorer.score_article(article_output, primary_keyword, None)
    print(f"\n{'='*80}")
    print(f"TOTAL AEO SCORE: {total_score}/100")
    print(f"{'='*80}")
    
    # Identify issues
    print("\n🔍 ISSUES IDENTIFIED:")
    issues = []
    if da_words > 60:
        issues.append(f"❌ Direct Answer too long ({da_words} words, target: 40-60)")
    if phrase_count < 8:
        issues.append(f"❌ Too few conversational phrases ({phrase_count}, target: 8+)")
    if question_count < 5:
        issues.append(f"❌ Too few question patterns ({question_count}, target: 5+)")
    if faq_count < 5:
        issues.append(f"❌ Too few FAQs ({faq_count}, target: 5+)")
    if paa_count < 3:
        issues.append(f"❌ Too few PAAs ({paa_count}, target: 3+)")
    
    if issues:
        for issue in issues:
            print(f"   {issue}")
    else:
        print("   ✅ No major issues found!")

if __name__ == "__main__":
    import re
    main()

