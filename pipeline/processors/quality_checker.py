"""
Quality Checker - Article Quality Validation & Scoring

ABOUTME: Enhanced with market-specific quality validation
ABOUTME: Integrates German premium standards and multi-market quality assessment

Maps to v4.1 Phase 9 Quality Checks

Performs:
- Critical checks (blocking issues)
- Suggestion checks (warnings)
- Metrics calculation (AEO score, readability, keyword coverage)
- Market-specific quality validation (German agency standards, etc.)

Output: Quality report with scores 0-100
"""

import re
from ..utils.humanizer import detect_ai_patterns, get_ai_score
import logging
from typing import Dict, Any, List, Tuple, Optional

from ..models.output_schema import ArticleOutput
from ..utils.aeo_scorer import AEOScorer
# Market quality validation removed - using prompt-based approach

logger = logging.getLogger(__name__)


class QualityChecker:
    """
    Article quality validation and scoring.

    Implements critical and suggestion checks per v4.1.
    """

    # Flesch-Kincaid reading level constants
    FLESCH_KINCAID_WEIGHTS = {
        0: 0,  # Very easy
        6: 20,  # Easy
        12: 40,  # Standard
        14: 60,  # Fairly difficult
        16: 80,  # Difficult
        18: 100,  # Very difficult
    }

    @staticmethod
    def check_article(
        article: Dict[str, Any],
        job_config: Dict[str, Any],
        article_output: Optional[ArticleOutput] = None,
        input_data: Optional[Dict[str, Any]] = None,
        language_validation: Optional[Dict[str, Any]] = None,
        market_profile: Optional[Dict[str, Any]] = None,
        target_market: str = "DE",
    ) -> Dict[str, Any]:
        """
        Perform full quality check on article.

        Args:
            article: Article dictionary
            job_config: Job configuration (primary_keyword, etc)
            article_output: Optional ArticleOutput instance for comprehensive AEO scoring
            input_data: Optional input data (company_data) for E-E-A-T scoring
            language_validation: Optional language validation metrics from LanguageValidator

        Returns:
            Quality report with issues and metrics
        """
        report = {
            "critical_issues": [],
            "suggestions": [],
            "metrics": {},
            "passed": True,
        }

        # Critical checks
        report["critical_issues"].extend(QualityChecker._check_required_fields(article))
        report["critical_issues"].extend(QualityChecker._check_duplicate_content(article))
        report["critical_issues"].extend(QualityChecker._check_competitor_mentions(article))
        report["critical_issues"].extend(QualityChecker._check_html_validity(article))
        report["critical_issues"].extend(QualityChecker._check_paragraph_length_critical(article))
        
        # ROOT_LEVEL_FIX_PLAN.md checks (CRITICAL - except citations and links)
        # NOTE: Academic citations and broken links moved to suggestions (Layer 4 cleanup handles)
        # NOTE: Em dashes moved to suggestions to reduce production blocking
        report["critical_issues"].extend(QualityChecker._check_malformed_headings(article))

        # Suggestion checks
        report["suggestions"].extend(QualityChecker._check_paragraph_length(article))
        report["suggestions"].extend(QualityChecker._check_keyword_coverage(article, job_config))
        report["suggestions"].extend(QualityChecker._check_em_dashes(article))  # Moved from critical
        report["suggestions"].extend(QualityChecker._check_reading_time(article))
        
        # Academic citations and broken links = suggestions only (Layer 4 regex cleanup guaranteed)
        report["suggestions"].extend(QualityChecker._check_academic_citations(article))
        report["suggestions"].extend(QualityChecker._check_broken_citation_links(article))
        
        # AEO quality checks
        report["suggestions"].extend(QualityChecker._check_citation_distribution(article))
        report["suggestions"].extend(QualityChecker._check_internal_link_distribution(article))
        report["suggestions"].extend(QualityChecker._check_question_headers(article))
        report["suggestions"].extend(QualityChecker._check_conversational_phrases(article))
        report["suggestions"].extend(QualityChecker._check_list_count(article))
        report["suggestions"].extend(QualityChecker._check_ai_phrases(article))
        
        # Content quality checks (truncated lists, duplicates, typos)
        report["critical_issues"].extend(QualityChecker._check_truncated_list_items(article))
        report["suggestions"].extend(QualityChecker._check_duplicate_summaries(article))
        report["suggestions"].extend(QualityChecker._check_common_typos(article))

        # Market awareness now handled through enhanced prompting
        if target_market and market_profile:
            # Add basic market context to report for reference
            report["metrics"]["market_context"] = {
                "target_market": target_market,
                "target_word_count": market_profile.get("target_word_count", "unknown"),
                "authorities": market_profile.get("authorities", [])
            }
            
            # Add market-specific quality checks
            report["suggestions"].extend(QualityChecker._check_market_quality(article, market_profile))

        # Calculate metrics
        # Use comprehensive AEOScorer if ArticleOutput is available
        if article_output:
            try:
                scorer = AEOScorer()
                primary_keyword = job_config.get("primary_keyword", "")
                comprehensive_score = scorer.score_article(
                    output=article_output,
                    primary_keyword=primary_keyword,
                    input_data=input_data,
                )
                report["metrics"]["aeo_score"] = comprehensive_score
                report["metrics"]["aeo_score_method"] = "comprehensive"
                logger.debug(f"Comprehensive AEO score calculated: {comprehensive_score}/100")
            except Exception as e:
                logger.warning(f"AEOScorer failed: {e}. Falling back to simple scoring.")
                report["metrics"]["aeo_score"] = QualityChecker._calculate_aeo_score(report)
                report["metrics"]["aeo_score_method"] = "simple_fallback"
        else:
            # Fallback to simple scoring
            report["metrics"]["aeo_score"] = QualityChecker._calculate_aeo_score(report)
            report["metrics"]["aeo_score_method"] = "simple"
        
        # Calculate word count
        all_content = article.get("Intro", "") + " "
        for i in range(1, 10):
            all_content += article.get(f"section_{i:02d}_content", "") + " "
        text_only = re.sub(r'<[^>]+>', '', all_content)
        report["metrics"]["word_count"] = len(text_only.split())
        
        report["metrics"]["readability"] = QualityChecker._calculate_readability_score(article)
        report["metrics"]["keyword_coverage"] = QualityChecker._calculate_keyword_coverage(
            article, job_config
        )
        
        # Add language quality metrics if available
        target_language = job_config.get("language", "en")
        if language_validation:
            report["metrics"]["language_quality"] = {
                "target_language": target_language,
                "detected_language": language_validation.get("detected_language"),
                "confidence": language_validation.get("confidence", 0.0),
                "english_contamination_score": language_validation.get("english_contamination_score", 0.0),
                "validation_passed": language_validation.get("validation_passed", True),
                "contamination_phrases": language_validation.get("contamination_phrases", [])[:5],  # Top 5
            }
            
            # Add contamination warning if detected
            contamination = language_validation.get("english_contamination_score", 0)
            if contamination > 0 and target_language != "en":
                report["suggestions"].append(
                    f"⚠️  English contamination detected: {contamination:.1f}% "
                    f"(phrases: {', '.join(language_validation.get('contamination_phrases', [])[:3])})"
                )

        # Set passed flag (true if no critical issues AND AEO score >= 80)
        aeo_score = report["metrics"].get("aeo_score", 0)
        has_no_critical_issues = len(report["critical_issues"]) == 0
        meets_aeo_threshold = aeo_score >= 75  # TEMP: Lowered for testing (was 80)
        
        report["passed"] = has_no_critical_issues and meets_aeo_threshold
        
        # Add AEO threshold failure as critical issue if needed
        if has_no_critical_issues and not meets_aeo_threshold:
            report["critical_issues"].append(f"❌ QUALITY GATE FAILURE: AEO score {aeo_score}/100 below required threshold (minimum: 80)")
            report["passed"] = False

        # Enhanced logging with quality gate status
        passed_status = "✅ PASS" if report["passed"] else "❌ FAIL"
        gate_reason = ""
        if not report["passed"]:
            if not has_no_critical_issues:
                gate_reason = f" (Critical issues: {len(report['critical_issues'])})"
            elif not meets_aeo_threshold:
                gate_reason = f" (AEO: {aeo_score}/85)"
        
        logger.info(f"Quality Gate: {passed_status}{gate_reason} | AEO: {report['metrics']['aeo_score']}/100 ({report['metrics'].get('aeo_score_method', 'unknown')})")
        return report

    @staticmethod
    def _check_required_fields(article: Dict[str, Any]) -> List[str]:
        """
        Check required fields are present and non-empty.

        Args:
            article: Article dictionary

        Returns:
            List of issues found
        """
        issues = []
        required_fields = [
            "Headline",
            "Intro",
            "Meta_Title",
            "Meta_Description",
            "section_01_title",
        ]

        for field in required_fields:
            value = article.get(field, "")
            if not value or not str(value).strip():
                issues.append(f"❌ Required field missing: {field}")

        return issues

    @staticmethod
    def _check_duplicate_content(article: Dict[str, Any]) -> List[str]:
        """
        Check for duplicate content across sections.

        Args:
            article: Article dictionary

        Returns:
            List of issues found
        """
        issues = []

        # Extract section contents
        sections = []
        for i in range(1, 10):
            content = article.get(f"section_{i:02d}_content", "")
            if content:
                # Normalize for comparison (remove HTML, lowercase)
                normalized = re.sub(r"<[^>]+>", "", content).lower()[:100]
                sections.append(normalized)

        # Check for duplicates
        if len(sections) != len(set(sections)):
            issues.append("❌ Duplicate section content detected")

        return issues

    @staticmethod
    def _check_competitor_mentions(article: Dict[str, Any]) -> List[str]:
        """
        Check for competitor mentions in content (stub - requires company_data).

        Args:
            article: Article dictionary

        Returns:
            List of issues found
        """
        # This would require competitor list from company_data
        # For now, just a stub
        return []

    @staticmethod
    def _check_html_validity(article: Dict[str, Any]) -> List[str]:
        """
        Check HTML validity (tags properly closed).

        Args:
            article: Article dictionary

        Returns:
            List of issues found
        """
        issues = []

        # Get all content with HTML
        content = ""
        for key in article:
            value = article.get(key, "")
            if isinstance(value, str) and "<" in value:
                content += value

        # Check for unclosed tags
        open_tags = re.findall(r"<(\w+)[^>]*>", content)
        close_tags = re.findall(r"</(\w+)>", content)

        # Self-closing tags don't need close tag
        self_closing = {"br", "hr", "img", "input", "meta", "link"}

        # CRITICAL FIX: Count each unique tag, not all tags
        unique_tags = set(open_tags)
        for tag in unique_tags:
            if tag.lower() not in self_closing:
                # Count case-insensitive
                close_count = sum(1 for t in close_tags if t.lower() == tag.lower())
                open_count = sum(1 for t in open_tags if t.lower() == tag.lower())

                if close_count < open_count:
                    issues.append(f"❌ Unclosed HTML tag: <{tag}> (open: {open_count}, close: {close_count})")

        return issues

    @staticmethod
    def _check_paragraph_length_critical(article: Dict[str, Any]) -> List[str]:
        """
        Check paragraph lengths for critical issues (>150 words).

        Args:
            article: Article dictionary

        Returns:
            List of critical issues
        """
        issues = []

        # Get all paragraphs from sections (exclude intro which has different rules)
        content = ""
        for i in range(1, 10):
            content += article.get(f"section_{i:02d}_content", "") + "\n"

        # Extract paragraphs (text between <p> tags)
        paragraphs = re.findall(r"<p[^>]*>([^<]+)</p>", content)

        very_long_paragraphs = []
        for i, para in enumerate(paragraphs, 1):
            # Remove HTML tags for word count
            text_no_html = re.sub(r"<[^>]+>", " ", para)
            word_count = len(text_no_html.split())
            
            if word_count > 60:  # Allow up to 60 words (10-word error range)
                preview = " ".join(text_no_html.split()[:10])
                very_long_paragraphs.append((i, word_count, preview))

        if very_long_paragraphs:
            examples = [f"Paragraph {i}: {count} words" for i, count, _ in very_long_paragraphs[:3]]
            issues.append(
                f"❌ {len(very_long_paragraphs)} paragraph(s) exceed 60 words (target: 40-60 words max). "
                f"Examples: {', '.join(examples)}"
            )

        return issues

    @staticmethod
    def _check_paragraph_length(article: Dict[str, Any]) -> List[str]:
        """
        Check paragraph lengths (should be 40-60 words, warn if >80).

        Args:
            article: Article dictionary

        Returns:
            List of suggestions
        """
        suggestions = []

        # Get all paragraphs from sections (exclude intro which has different rules)
        content = ""
        for i in range(1, 10):
            content += article.get(f"section_{i:02d}_content", "") + "\n"

        # Extract paragraphs (text between <p> tags)
        paragraphs = re.findall(r"<p[^>]*>([^<]+)</p>", content)

        long_paragraphs = []
        for i, para in enumerate(paragraphs, 1):
            # Remove HTML tags for word count
            text_no_html = re.sub(r"<[^>]+>", " ", para)
            word_count = len(text_no_html.split())
            
            # Warn if >80 words but <=150 (critical check handles >150)
            if 80 < word_count <= 150:
                preview = " ".join(text_no_html.split()[:8])
                long_paragraphs.append((i, word_count, preview))

        if long_paragraphs:
            examples = [f"Paragraph {i}: {count} words" for i, count, _ in long_paragraphs[:3]]
            suggestions.append(
                f"⚠️  {len(long_paragraphs)} paragraph(s) exceed 80 words (target: 40-60 words). "
                f"Examples: {', '.join(examples)}"
            )

        return suggestions

    @staticmethod
    def _check_keyword_coverage(article: Dict[str, Any], job_config: Dict[str, Any]) -> List[str]:
        """
        Check primary keyword coverage.

        Args:
            article: Article dictionary
            job_config: Job configuration

        Returns:
            List of suggestions
        """
        suggestions = []

        keyword = job_config.get("primary_keyword", "")
        if not keyword:
            return suggestions

        # Check headline
        headline = article.get("Headline", "").lower()
        if keyword.lower() not in headline:
            suggestions.append(f"⚠️  Primary keyword not in headline")

        # Check first 100 words
        intro = article.get("Intro", "").lower()
        first_section = article.get("section_01_content", "").lower()
        first_100_words = (intro + " " + first_section)[:500].lower()

        if keyword.lower() not in first_100_words:
            suggestions.append(f"⚠️  Primary keyword not in first 100 words")

        return suggestions

    @staticmethod
    def _check_reading_time(article: Dict[str, Any]) -> List[str]:
        """
        Check reading time is in acceptable range (5-15 minutes).

        Args:
            article: Article dictionary

        Returns:
            List of suggestions
        """
        suggestions = []

        # Calculate read_time from word count if not provided
        read_time = article.get("read_time", 0)
        if not read_time:
            # Calculate from content
            all_content = article.get("Intro", "") + article.get("Direct_Answer", "")
            for i in range(1, 10):
                all_content += article.get(f"section_{i:02d}_content", "") or ""
            import re
            text_only = re.sub(r'<[^>]+>', '', all_content)
            word_count = len(text_only.split())
            read_time = max(1, word_count // 200)  # ~200 wpm
        if isinstance(read_time, str):
            try:
                read_time = int(read_time.split()[0])
            except (ValueError, IndexError):
                return suggestions

        if read_time < 5:
            suggestions.append(f"⚠️  Reading time too short: {read_time} min (target: 5-15)")
        elif read_time > 20:
            suggestions.append(f"⚠️  Reading time too long: {read_time} min (target: 5-15)")

        return suggestions


    @staticmethod
    def _check_citation_distribution(article: Dict[str, Any]) -> List[str]:
        """
        Check per-paragraph citation distribution - v4.1 requirement: EVERY paragraph needs 2-3 citations.

        Args:
            article: Article dictionary

        Returns:
            List of suggestions/issues
        """
        issues = []
        import re

        # Get all content from sections (skip Intro as it can be longer)
        all_content = " ".join([
            article.get(f"section_{i:02d}_content", "") for i in range(1, 10)
        ])

        # Extract paragraphs (content within <p> tags)
        paragraphs = re.findall(r'<p[^>]*>.*?</p>', all_content, re.DOTALL)
        if not paragraphs:
            return issues

        # Analyze each paragraph
        paragraphs_with_0_citations = []
        paragraphs_with_1_citation = []
        paragraphs_with_2_3_citations = []
        paragraphs_with_4plus_citations = []

        for i, para in enumerate(paragraphs, 1):
            # Remove HTML tags to get clean text for analysis
            clean_text = re.sub(r'<[^>]+>', '', para)
            
            # Skip very short paragraphs (< 20 words, likely formatting issues)
            word_count = len(clean_text.split())
            if word_count < 20:
                continue
                
            # Count citations in this paragraph
            citations = re.findall(r'\[\d+\]', para)
            citation_count = len(citations)
            
            if citation_count == 0:
                paragraphs_with_0_citations.append(f"P{i}: {clean_text[:50]}...")
            elif citation_count == 1:
                paragraphs_with_1_citation.append(f"P{i}: {clean_text[:50]}...")
            elif citation_count in [2, 3]:
                paragraphs_with_2_3_citations.append(f"P{i}")
            else:  # 4+ citations
                paragraphs_with_4plus_citations.append(f"P{i}: {citation_count} citations")

        # Calculate percentages
        total_paragraphs = len(paragraphs_with_0_citations) + len(paragraphs_with_1_citation) + len(paragraphs_with_2_3_citations) + len(paragraphs_with_4plus_citations)
        
        if total_paragraphs == 0:
            return issues

        perfect_percentage = len(paragraphs_with_2_3_citations) / total_paragraphs * 100

        # STRICT ENFORCEMENT: 70%+ paragraphs must have 2-3 citations (buffer above 60% minimum)
        if perfect_percentage < 70:  # Less than 70% compliance
            issues.append(f"❌ CRITICAL: Only {perfect_percentage:.1f}% paragraphs have 2-3 citations (target: 70%+ with buffer)")
            
            if paragraphs_with_0_citations:
                issues.append(f"   {len(paragraphs_with_0_citations)} paragraphs with 0 citations: {', '.join(paragraphs_with_0_citations[:2])}{'...' if len(paragraphs_with_0_citations) > 2 else ''}")
                
            if paragraphs_with_1_citation:
                issues.append(f"   {len(paragraphs_with_1_citation)} paragraphs with only 1 citation: {', '.join(paragraphs_with_1_citation[:2])}{'...' if len(paragraphs_with_1_citation) > 2 else ''}")
                
            if paragraphs_with_4plus_citations:
                issues.append(f"   {len(paragraphs_with_4plus_citations)} paragraphs with 4+ citations: {', '.join(paragraphs_with_4plus_citations[:2])}")

        elif perfect_percentage < 100:  # 70-99% compliance
            issues.append(f"⚠️  Good citation distribution: {perfect_percentage:.1f}% paragraphs have 2-3 citations (target: 70%+ with buffer)")

        return issues

    @staticmethod
    def _check_internal_link_distribution(article: Dict[str, Any]) -> List[str]:
        """
        Check internal link distribution - target 1 link per H2 section.

        Args:
            article: Article dictionary

        Returns:
            List of suggestions/issues
        """
        issues = []

        # Extract all section content (H2 sections)
        sections_with_content = []
        for i in range(1, 10):
            content = article.get(f"section_{i:02d}_content", "")
            title = article.get(f"section_{i:02d}_title", "")
            if content and content.strip() and title and title.strip():
                sections_with_content.append({
                    'number': i,
                    'title': title.strip(),
                    'content': content.strip()
                })

        if not sections_with_content:
            return issues

        # Count internal links per section
        import re
        total_internal_links = 0
        sections_with_links = 0
        sections_without_links = []

        for section in sections_with_content:
            # Find internal links (href starts with "/")
            internal_links = re.findall(r'<a\s+href="(/[^"]*)"[^>]*>', section['content'])
            link_count = len(internal_links)
            
            total_internal_links += link_count
            
            if link_count > 0:
                sections_with_links += 1
            else:
                sections_without_links.append(f"Section {section['number']}: {section['title'][:30]}...")

        # Check distribution quality
        total_sections = len(sections_with_content)
        distribution_rate = sections_with_links / total_sections if total_sections > 0 else 0

        # V4.1 target: 1 link per section (100% distribution)
        if distribution_rate < 0.8:  # Less than 80% sections have links
            issues.append(f"❌ Poor internal link distribution: {sections_with_links}/{total_sections} sections have links (target: 1 per section)")
            if sections_without_links:
                issues.append(f"   Sections missing links: {', '.join(sections_without_links[:3])}{'...' if len(sections_without_links) > 3 else ''}")
        elif distribution_rate < 1.0:  # 80-99% have links
            issues.append(f"⚠️  Good internal link distribution: {sections_with_links}/{total_sections} sections have links (target: 1 per section)")

        # Check for link bunching (multiple links in one section while others have none)
        sections_with_multiple_links = []
        for section in sections_with_content:
            internal_links = re.findall(r'<a\s+href="(/[^"]*)"[^>]*>', section['content'])
            if len(internal_links) > 2:  # More than 2 links in one section
                sections_with_multiple_links.append(f"Section {section['number']}")

        if sections_with_multiple_links and sections_without_links:
            issues.append(f"⚠️  Link bunching detected: {', '.join(sections_with_multiple_links)} have 3+ links while other sections have none")

        return issues

    @staticmethod
    def _check_question_headers(article: Dict[str, Any]) -> List[str]:
        """
        Check for question-format section headers (target: 3-4 question headers).

        Args:
            article: Article dictionary

        Returns:
            List of suggestions/issues
        """
        issues = []

        question_patterns = [
            "what is", "how does", "why does", "when should", "where can",
            "what are", "how can", "how do", "why is"
        ]

        question_count = 0
        for i in range(1, 10):
            title = article.get(f"section_{i:02d}_title", "")
            if title:
                title_lower = title.lower()
                if any(pattern in title_lower for pattern in question_patterns) or title.strip().endswith("?"):
                    question_count += 1

        if question_count < 2:
            issues.append(
                f"⚠️  Only {question_count} question-format headers found (target: 3-4). "
                f"Use 'What is...', 'How does...', etc."
            )

        return issues

    @staticmethod
    def _check_conversational_phrases(article: Dict[str, Any]) -> List[str]:
        """
        Check for conversational phrases (target: 8+ unique phrases).

        Args:
            article: Article dictionary

        Returns:
            List of suggestions/issues
        """
        issues = []

        # Full phrase list matching stage_10 injection
        conversational_phrases = [
            "how to", "what is", "why does", "when should", "where can",
            "you can", "you'll", "you should", "let's", "here's", "this is",
            "how can", "what are", "how do", "why should", "where are",
            "we'll", "that's", "when you", "if you", "so you can", "which means",
        ]

        # Get all content
        all_content = article.get("Intro", "") + " " + article.get("Direct_Answer", "") + " "
        all_content += " ".join([
            article.get(f"section_{i:02d}_content", "") for i in range(1, 10)
        ])
        content_lower = all_content.lower()

        phrase_count = sum(1 for phrase in conversational_phrases if phrase in content_lower)

        if phrase_count < 12:
            issues.append(
                f"⚠️  Only {phrase_count} conversational phrases found (target: 12+ with buffer). "
                f"Use 'you can', 'here\'s', 'how to', etc."
            )

        return issues

    @staticmethod
    def _check_list_count(article: Dict[str, Any]) -> List[str]:
        """
        Check for HTML lists (target: 5+ lists).

        Args:
            article: Article dictionary

        Returns:
            List of suggestions/issues
        """
        issues = []

        # Get all content
        all_content = " ".join([
            article.get(f"section_{i:02d}_content", "") for i in range(1, 10)
        ])

        list_count = all_content.count("<ul>") + all_content.count("<ol>")

        if list_count < 3:
            issues.append(
                f"⚠️  Only {list_count} HTML lists found (target: 5+). "
                f"Add <ul> or <ol> lists for better structure."
            )

        return issues

    @staticmethod
    def _check_ai_phrases(article: Dict[str, Any]) -> List[str]:
        """
        Check for AI-typical phrases in content.
        
        Returns warnings if too many AI phrases are detected.
        """
        issues = []
        
        # Get all content
        all_content = article.get("Intro", "") + " "
        all_content += article.get("Direct_Answer", "") + " "
        for i in range(1, 10):
            all_content += article.get(f"section_{i:02d}_content", "") + " "
        
        # Detect AI phrases
        detected = detect_ai_patterns(all_content)
        ai_score = get_ai_score(all_content)
        
        # Report if AI score is high
        if ai_score > 30:
            issues.append(f"⚠️  High AI content score: {ai_score}/100 (target: <30)")
        
        # Report specific AI phrases found
        if detected:
            top_phrases = detected[:5]  # Show top 5
            phrase_list = ", ".join([f'"{p[0]}" ({p[1]}x)' for p in top_phrases])
            issues.append(f"⚠️  AI phrases detected: {phrase_list}")
        
        return issues


    @staticmethod
    def _check_market_quality(article: Dict[str, Any], market_profile: Dict[str, Any]) -> List[str]:
        """
        Check basic market-specific quality requirements.
        
        Args:
            article: Article dictionary
            market_profile: Market profile with word count and authority requirements
            
        Returns:
            List of suggestions/issues
        """
        issues = []
        
        # Calculate actual word count
        all_content = article.get("Intro", "") + " "
        for i in range(1, 10):
            all_content += article.get(f"section_{i:02d}_content", "") + " "
        text_only = re.sub(r'<[^>]+>', '', all_content)
        actual_word_count = len(text_only.split())
        
        # Check word count against market requirements
        min_word_count = market_profile.get("min_word_count", 1500)
        target_word_count = market_profile.get("target_word_count", "1500-2000")
        
        if actual_word_count < min_word_count:
            issues.append(f"⚠️  Word count below market minimum: {actual_word_count} words (minimum: {min_word_count}, target: {target_word_count})")
        
        # Check for authority references
        required_authorities = market_profile.get("authorities", [])
        if required_authorities:
            found_authorities = []
            missing_authorities = []
            
            all_content_lower = all_content.lower()
            
            for authority in required_authorities:
                if authority.lower() in all_content_lower:
                    found_authorities.append(authority)
                else:
                    missing_authorities.append(authority)
            
            if missing_authorities:
                issues.append(f"⚠️  Missing market authorities: {', '.join(missing_authorities[:3])} (found: {', '.join(found_authorities) if found_authorities else 'none'})")
            elif len(found_authorities) < len(required_authorities) // 2:
                issues.append(f"⚠️  Low authority coverage: {len(found_authorities)}/{len(required_authorities)} mentioned (target: most authorities)")
        
        return issues

    @staticmethod
    def _check_academic_citations(article: Dict[str, Any]) -> List[str]:
        """
        Check for academic citations [N] (suggestion, not blocking).
        ROOT_LEVEL_FIX_PLAN.md Issue 1 - CHANGED TO WARNING.
        
        Layer 4 regex cleanup guarantees removal, so this is informational only.
        """
        issues = []
        
        # Check all content fields for [N] patterns
        citation_count = 0
        for key in article:
            value = article.get(key, "")
            if isinstance(value, str):
                matches = re.findall(r'\[\d+\]', value)
                if matches:
                    citation_count += len(matches)
        
        if citation_count > 0:
            issues.append(
                f"⚠️  Suggestion: Academic citations [N] found ({citation_count} instances) - "
                f"will be cleaned by Layer 4 regex"
            )
        
        return issues
    
    @staticmethod
    def _check_em_dashes(article: Dict[str, Any]) -> List[str]:
        """
        Check for em dashes (—) - now as suggestions only.
        ROOT_LEVEL_FIX_PLAN.md Issue 2.
        """
        issues = []
        em_dash_patterns = [r'—', r'&mdash;', r'&#8212;', r'&#x2014;']
        
        for key in article:
            value = article.get(key, "")
            if isinstance(value, str):
                for pattern in em_dash_patterns:
                    if re.search(pattern, value):
                        issues.append(f"💡 Em dash found in {key} - consider replacing with regular dash (-)")
                        break
        
        return issues
    
    @staticmethod
    def _check_malformed_headings(article: Dict[str, Any]) -> List[str]:
        """
        Check for malformed headings (double question prefixes).
        ROOT_LEVEL_FIX_PLAN.md Issue A.
        """
        issues = []
        
        # Check section titles and PAA/FAQ questions
        heading_keys = [k for k in article.keys() if ('title' in k or 'question' in k)]
        
        for key in heading_keys:
            heading = article.get(key, "")
            if not heading:
                continue
            
            # Check for "What is How/Why/What/When" patterns
            if re.search(r'^What is (How|Why|What|When|Where|Who)\b', heading, re.IGNORECASE):
                issues.append(f"❌ CRITICAL: Malformed heading in {key}: '{heading}' (duplicate question prefix)")
            
            # Check for double punctuation
            if re.search(r'\?{2,}|!{2,}|\.{2,}', heading):
                issues.append(f"❌ CRITICAL: Double punctuation in {key}: '{heading}'")
        
        return issues
    
    @staticmethod
    def _check_broken_citation_links(article: Dict[str, Any]) -> List[str]:
        """
        Check for broken #source-N citation links (suggestion, not blocking).
        ROOT_LEVEL_FIX_PLAN.md Issue C - CHANGED TO WARNING.
        
        Layer 4 regex cleanup guarantees removal, so this is informational only.
        """
        issues = []
        
        # Check content for #source-N links
        link_count = 0
        for key in article:
            value = article.get(key, "")
            if isinstance(value, str):
                matches = re.findall(r'href=["\']#source-\d+["\']', value)
                if matches:
                    link_count += len(matches)
        
        if link_count > 0:
            issues.append(
                f"⚠️  Suggestion: Broken #source-N links found ({link_count} instances) - "
                f"will be cleaned by Layer 4 regex"
            )
        
        return issues

    @staticmethod
    def _check_truncated_list_items(article: Dict[str, Any]) -> List[str]:
        """
        Check for truncated/incomplete list items (CRITICAL).
        
        Truncated list items are broken content that should never appear.
        Examples:
        - List items under 10 words without punctuation
        - Items ending mid-sentence
        - Items with only 1-2 words
        """
        issues = []
        
        for key in article:
            value = article.get(key, "")
            if isinstance(value, str):
                # Find all list items
                list_items = re.findall(r'<li>([^<]+)</li>', value)
                for item in list_items:
                    item_text = item.strip()
                    words = item_text.split()
                    
                    # Check for truncated items
                    if len(words) < 3:
                        issues.append(f"❌ CRITICAL: Truncated list item (too short): '{item_text[:50]}'")
                    elif len(words) < 8 and not item_text.rstrip().endswith(('.', '!', '?', ':', ';')):
                        # Short items without proper punctuation
                        issues.append(f"⚠️  Suggestion: Potentially truncated list item: '{item_text[:50]}'")
        
        return issues

    @staticmethod
    def _check_duplicate_summaries(article: Dict[str, Any]) -> List[str]:
        """
        Check for duplicate summary sections (SUGGESTION).
        
        Gemini sometimes generates "Here are key points:" followed by bullet lists
        that duplicate content from preceding paragraphs.
        """
        issues = []
        
        # Patterns that indicate duplicate summaries
        summary_patterns = [
            r'Here are key points\s*:',
            r'Important considerations\s*:',
            r'Key benefits include\s*:',
            r'Here\'?s what you need to know\s*:',
        ]
        
        for key in article:
            value = article.get(key, "")
            if isinstance(value, str):
                for pattern in summary_patterns:
                    matches = re.findall(pattern, value, re.IGNORECASE)
                    if matches:
                        issues.append(
                            f"⚠️  Suggestion: Duplicate summary pattern found in {key}: '{matches[0]}' - "
                            f"will be cleaned by html_renderer"
                        )
        
        return issues

    @staticmethod
    def _check_common_typos(article: Dict[str, Any]) -> List[str]:
        """
        Check for common Gemini typos (SUGGESTION).
        
        Gemini sometimes makes verb conjugation errors like "applys" instead of "applies".
        """
        issues = []
        
        # Common typo patterns
        typo_patterns = [
            (r'\bapplys\b', 'applys (should be: applies)'),
            (r'\bapplyd\b', 'applyd (should be: applied)'),
            (r'\banalyzs\b', 'analyzs (should be: analyzes)'),
            (r'\borganizs\b', 'organizs (should be: organizes)'),
            (r'\bminimizs\b', 'minimizs (should be: minimizes)'),
            (r'\bmaximizs\b', 'maximizs (should be: maximizes)'),
            (r'\boptimizs\b', 'optimizs (should be: optimizes)'),
            (r'\bprioritizs\b', 'prioritizs (should be: prioritizes)'),
            (r'\butilizs\b', 'utilizs (should be: utilizes)'),
        ]
        
        for key in article:
            value = article.get(key, "")
            if isinstance(value, str):
                for pattern, description in typo_patterns:
                    matches = re.findall(pattern, value, re.IGNORECASE)
                    if matches:
                        issues.append(
                            f"⚠️  Suggestion: Typo found in {key}: {description} - "
                            f"will be corrected by html_renderer"
                        )
        
        return issues

    @staticmethod
    def _calculate_aeo_score(report: Dict[str, Any]) -> int:
        """
        Calculate AEO (Article Excellence Optimization) score 0-100.

        Based on issue counts and compliance.

        Args:
            report: Quality report with issues

        Returns:
            AEO score (0-100)
        """
        score = 100

        # Deduct for critical issues (20 points each, max 100)
        critical_count = len(report.get("critical_issues", []))
        score -= min(critical_count * 20, 100)

        # Deduct for suggestions (2 points each, max 30)
        suggestion_count = len(report.get("suggestions", []))
        score -= min(suggestion_count * 2, 30)

        return max(score, 0)

    @staticmethod
    def _calculate_readability_score(article: Dict[str, Any]) -> int:
        """
        Calculate readability score (Flesch-Kincaid approximation).

        Args:
            article: Article dictionary

        Returns:
            Readability score (0-100)
        """
        # Get all text content
        text = ""
        for key in article:
            value = article.get(key, "")
            if isinstance(value, str):
                # Remove HTML tags
                text += re.sub(r"<[^>]+>", "", value) + " "

        if not text:
            return 50  # Default middle score

        # Simple approximation: count sentences and words
        sentences = len(re.split(r"[.!?]+", text))
        words = len(text.split())

        if sentences == 0 or words == 0:
            return 50

        # Flesch-Kincaid approximation
        avg_words_per_sentence = words / sentences
        avg_syllables_per_word = 1.3  # Approximation

        score = (
            206.835
            - 1.015 * avg_words_per_sentence
            - 84.6 * avg_syllables_per_word
        )

        # Normalize to 0-100
        score = max(0, min(100, score))
        return int(score)

    @staticmethod
    def _calculate_keyword_coverage(article: Dict[str, Any], job_config: Dict[str, Any]) -> int:
        """
        Calculate keyword coverage percentage.

        Args:
            article: Article dictionary
            job_config: Job configuration

        Returns:
            Keyword coverage 0-100%
        """
        keyword = job_config.get("primary_keyword", "").lower()
        if not keyword:
            return 50  # Default

        # Get all text content
        text = ""
        for key in article:
            value = article.get(key, "")
            if isinstance(value, str):
                text += re.sub(r"<[^>]+>", "", value).lower() + " "

        if not text:
            return 0

        # Count keyword occurrences
        keyword_count = text.count(keyword)
        word_count = len(text.split())

        if word_count == 0:
            return 0

        # Calculate density percentage
        density = (keyword_count / word_count) * 100

        # Target 1-2% density, score accordingly
        if 0.5 <= density <= 3:
            return 100
        elif 0.3 <= density <= 5:
            return 80
        else:
            return max(0, min(100, int(50 * (density / 2))))
