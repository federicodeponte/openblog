"""
Stage 2b: Quality Refinement

🛡️ LAYER 2 (Detection + Best-Effort Fix)

This stage is part of a 3-layer production quality system:
- Layer 1: Prevention (main prompt rules)
- Layer 2: Detection + best-effort Gemini fix (this stage) [NON-BLOCKING]
- Layer 3: Guaranteed regex cleanup (html_renderer.py)

Detects quality issues:
1. Keyword over-optimization (too many mentions)
2. First paragraph too short
3. AI language markers (em dashes, robotic phrases)

Attempts Gemini-based surgical edits via RewriteEngine.
If Gemini fails, Layer 3 (regex) will catch remaining issues.

Runs AFTER Stage 3 (Extraction) but BEFORE Stage 4-9 (Parallel stages).
Only executes if quality issues are detected.
"""

import logging
import re
from typing import Dict, List, Any, Optional

from ..core import ExecutionContext, Stage
from ..models.output_schema import ArticleOutput
from ..rewrites import (
    RewriteEngine,
    RewriteInstruction,
    RewriteMode,
    targeted_rewrite
)

logger = logging.getLogger(__name__)


class QualityIssue:
    """
    Represents a detected quality issue.
    """
    def __init__(
        self,
        issue_type: str,
        severity: str,
        description: str,
        current_value: Any,
        target_value: Any,
        field: str
    ):
        self.issue_type = issue_type
        self.severity = severity  # "critical", "warning", "info"
        self.description = description
        self.current_value = current_value
        self.target_value = target_value
        self.field = field
    
    def __repr__(self):
        return f"QualityIssue({self.issue_type}, {self.severity}, field={self.field})"


class QualityRefinementStage(Stage):
    """
    Stage 2b: Quality Refinement (conditional).
    
    Detects and fixes quality issues in Gemini output:
    - Keyword over/under-optimization
    - Paragraph length issues
    - AI language markers
    
    Uses RewriteEngine for surgical edits.
    """
    
    stage_num = 2  # Runs between Stage 2 and 3
    stage_name = "Quality Refinement"
    
    # Quality thresholds
    KEYWORD_TARGET_MIN = 5
    KEYWORD_TARGET_MAX = 8
    FIRST_PARAGRAPH_MIN_WORDS = 60
    FIRST_PARAGRAPH_MAX_WORDS = 100
    
    # AI marker patterns
    AI_MARKERS = {
        "em_dash": "—",
        "robotic_phrases": [
            "Here's how",
            "Here's what",
            "Key points:",
            "Key benefits include:",
            "Important considerations:",
            "That's why similarly",
            "If you want another",
            "You'll find to"
        ]
    }
    
    async def execute(self, context: ExecutionContext) -> ExecutionContext:
        """
        Execute Stage 2b: Comprehensive content transformation (ALWAYS RUNS).
        
        This stage ALWAYS runs to transform content using Gemini 3.0 Pro Preview.
        Single comprehensive pass that fixes all content quality issues at once.
        
        Args:
            context: ExecutionContext with structured_data from Stage 3
        
        Returns:
            Updated context with transformed structured_data
        """
        logger.info(f"Stage 2b: {self.stage_name}")
        
        # Validate input
        if not context.structured_data:
            logger.warning("No structured_data available, skipping transformation")
            return context
        
        # ALWAYS run comprehensive content transformation
        logger.info("🔧 Running mandatory comprehensive content transformation...")
        
        # Detect quality issues (for metrics/logging only, not for conditional execution)
        issues = self._detect_quality_issues(context)
        
        # Calculate detailed pre-transformation metrics
        article_content = context.structured_data
        
        # Count specific issue types
        citation_count = 0
        em_dash_count = 0
        label_count = 0
        weird_passage_count = 0
        
        for issue in issues:
            if "citation" in issue.description.lower() or "[" in issue.description:
                citation_count += 1
            elif "em dash" in issue.description.lower() or "—" in issue.description:
                em_dash_count += 1
            elif "label" in issue.description.lower() or "standalone" in issue.description.lower():
                label_count += 1
            elif "malformed" in issue.description.lower() or "weird" in issue.description.lower():
                weird_passage_count += 1
        
        # Log comprehensive pre-transformation metrics
        critical_issues = [i for i in issues if i.severity == "critical"]
        warning_issues = [i for i in issues if i.severity == "warning"]
        
        logger.info(f"📊 Pre-transformation quality analysis:")
        logger.info(f"   Total issues detected: {len(issues)}")
        logger.info(f"   Critical: {len(critical_issues)}")
        logger.info(f"   Warnings: {len(warning_issues)}")
        logger.info(f"")
        logger.info(f"   Issue breakdown:")
        logger.info(f"   - Academic citations [N]: {citation_count}")
        logger.info(f"   - Em dashes (—): {em_dash_count}")
        logger.info(f"   - Standalone labels: {label_count}")
        logger.info(f"   - Malformed/weird passages: {weird_passage_count}")
        
        if issues:
            logger.info(f"")
            logger.info(f"   Sample issues (first 5):")
            for issue in issues[:5]:
                logger.info(f"   • {issue.severity.upper()}: {issue.description[:80]}")
        
        # Build comprehensive rewrite instruction
        rewrite = self._build_comprehensive_rewrite(context)
        
        if not rewrite:
            logger.warning("Failed to build comprehensive rewrite instruction, skipping transformation")
            return context
        
        logger.info(f"🔧 Applying comprehensive content transformation...")
        logger.info("🔄 Using Gemini 3.0 Pro Preview for intelligent fixes (non-blocking)...")
        
        # Execute comprehensive rewrite
        try:
            article_dict = context.structured_data.dict()
            
            # Execute single comprehensive transformation
            updated_article = await targeted_rewrite(
                article=article_dict,
                rewrites=[rewrite]  # Single comprehensive rewrite
            )
            
            # Update context with transformed data
            context.structured_data = ArticleOutput(**updated_article)
            
            logger.info("✅ Comprehensive content transformation complete")
            
            # Re-check quality (for metrics logging)
            remaining_issues = self._detect_quality_issues(context)
            
            # Calculate post-transformation metrics
            new_citation_count = 0
            new_em_dash_count = 0
            new_label_count = 0
            new_weird_passage_count = 0
            
            for issue in remaining_issues:
                if "citation" in issue.description.lower() or "[" in issue.description:
                    new_citation_count += 1
                elif "em dash" in issue.description.lower() or "—" in issue.description:
                    new_em_dash_count += 1
                elif "label" in issue.description.lower() or "standalone" in issue.description.lower():
                    new_label_count += 1
                elif "malformed" in issue.description.lower() or "weird" in issue.description.lower():
                    new_weird_passage_count += 1
            
            if remaining_issues:
                success_rate = (1 - len(remaining_issues)/max(len(issues), 1)) * 100
                logger.info(f"")
                logger.info(f"📊 Post-transformation metrics:")
                logger.info(f"   Remaining issues: {len(remaining_issues)}")
                logger.info(f"   Transformation success rate: {success_rate:.1f}%")
                logger.info(f"")
                logger.info(f"   Issue reduction:")
                logger.info(f"   - Academic citations [N]: {citation_count} → {new_citation_count}")
                logger.info(f"   - Em dashes (—): {em_dash_count} → {new_em_dash_count}")
                logger.info(f"   - Standalone labels: {label_count} → {new_label_count}")
                logger.info(f"   - Malformed/weird passages: {weird_passage_count} → {new_weird_passage_count}")
                logger.info(f"")
                logger.info("🛡️  Stage 10 (regex safety net) will handle remaining issues")
            else:
                logger.info(f"")
                logger.info("✅ All quality issues resolved by Gemini transformation")
                logger.info("📊 Post-transformation: 100% success rate")
                logger.info(f"")
                logger.info(f"   All issues fixed:")
                logger.info(f"   - Academic citations [N]: {citation_count} → 0")
                logger.info(f"   - Em dashes (—): {em_dash_count} → 0")
                logger.info(f"   - Standalone labels: {label_count} → 0")
                logger.info(f"   - Malformed/weird passages: {weird_passage_count} → 0")
        
        except Exception as e:
            logger.warning(f"⚠️  Comprehensive transformation failed: {str(e)}")
            logger.info("🛡️  Continuing with original content - Stage 10 (regex) will fix issues")
            logger.info("📊 This failure is logged but does NOT block the pipeline")
        
        return context
    
    def _detect_quality_issues(self, context: ExecutionContext) -> List[QualityIssue]:
        """
        Detect quality issues in structured_data.
        
        Returns:
            List of QualityIssue objects
        """
        issues = []
        data = context.structured_data
        job_config = context.job_config or {}
        
        primary_keyword = job_config.get("primary_keyword", "")
        
        # Issue 1: Keyword over/under-optimization
        if primary_keyword:
            keyword_issue = self._check_keyword_density(data, primary_keyword)
            if keyword_issue:
                issues.append(keyword_issue)
        
        # Issue 2: First paragraph too short/long
        first_para_issue = self._check_first_paragraph_length(data)
        if first_para_issue:
            issues.append(first_para_issue)
        
        # Issue 3: AI language markers
        ai_marker_issues = self._check_ai_markers(data)
        issues.extend(ai_marker_issues)
        
        # ROOT_LEVEL_FIX_PLAN.md checks
        # Issue 4: Academic citations [N]
        citation_issues = self._check_academic_citations_stage2b(data)
        issues.extend(citation_issues)
        
        # Issue 5: Em dashes
        em_dash_issues = self._check_em_dashes_stage2b(data)
        issues.extend(em_dash_issues)
        
        # Issue 6: Malformed headings
        heading_issues = self._check_malformed_headings_stage2b(data)
        issues.extend(heading_issues)
        
        return issues
    
    def _check_keyword_density(
        self,
        data: ArticleOutput,
        primary_keyword: str
    ) -> Optional[QualityIssue]:
        """
        Check if primary keyword is over/under-optimized.
        """
        # Count keyword mentions in content
        content_fields = ["Headline", "Intro"]
        
        # Add all section content fields
        for i in range(1, 10):
            field_name = f"section_{i:02d}_content"
            content_fields.append(field_name)
        
        # Concatenate all content
        all_content = " ".join([
            str(getattr(data, field, ""))
            for field in content_fields
            if getattr(data, field, None)
        ])
        
        # Count keyword (case-insensitive)
        keyword_count = all_content.lower().count(primary_keyword.lower())
        
        if keyword_count < self.KEYWORD_TARGET_MIN:
            return QualityIssue(
                issue_type="keyword_underuse",
                severity="warning",
                description=f"Keyword '{primary_keyword}' appears only {keyword_count} times (target: {self.KEYWORD_TARGET_MIN}-{self.KEYWORD_TARGET_MAX})",
                current_value=keyword_count,
                target_value=f"{self.KEYWORD_TARGET_MIN}-{self.KEYWORD_TARGET_MAX}",
                field="all_content"
            )
        
        elif keyword_count > self.KEYWORD_TARGET_MAX:
            return QualityIssue(
                issue_type="keyword_overuse",
                severity="critical",
                description=f"Keyword '{primary_keyword}' appears {keyword_count} times (target: {self.KEYWORD_TARGET_MIN}-{self.KEYWORD_TARGET_MAX})",
                current_value=keyword_count,
                target_value=f"{self.KEYWORD_TARGET_MIN}-{self.KEYWORD_TARGET_MAX}",
                field="all_sections"
            )
        
        return None
    
    def _check_first_paragraph_length(
        self,
        data: ArticleOutput
    ) -> Optional[QualityIssue]:
        """
        Check if first paragraph is too short or too long.
        """
        # Get first section content
        first_section = getattr(data, "section_01_content", "")
        
        if not first_section:
            return None
        
        # Extract first <p> tag
        first_p_match = re.search(r'<p>(.*?)</p>', first_section, re.DOTALL)
        
        if not first_p_match:
            return None
        
        first_paragraph = first_p_match.group(1)
        
        # Strip HTML tags from paragraph for word count
        text_only = re.sub(r'<[^>]+>', '', first_paragraph)
        word_count = len(text_only.split())
        
        if word_count < self.FIRST_PARAGRAPH_MIN_WORDS:
            return QualityIssue(
                issue_type="first_paragraph_short",
                severity="critical",
                description=f"First paragraph is only {word_count} words (target: {self.FIRST_PARAGRAPH_MIN_WORDS}-{self.FIRST_PARAGRAPH_MAX_WORDS})",
                current_value=word_count,
                target_value=f"{self.FIRST_PARAGRAPH_MIN_WORDS}-{self.FIRST_PARAGRAPH_MAX_WORDS}",
                field="section_01_content"
            )
        
        elif word_count > self.FIRST_PARAGRAPH_MAX_WORDS:
            return QualityIssue(
                issue_type="first_paragraph_long",
                severity="warning",
                description=f"First paragraph is {word_count} words (target: {self.FIRST_PARAGRAPH_MIN_WORDS}-{self.FIRST_PARAGRAPH_MAX_WORDS})",
                current_value=word_count,
                target_value=f"{self.FIRST_PARAGRAPH_MIN_WORDS}-{self.FIRST_PARAGRAPH_MAX_WORDS}",
                field="section_01_content"
            )
        
        return None
    
    def _check_ai_markers(self, data: ArticleOutput) -> List[QualityIssue]:
        """
        Check for AI language markers (em dashes, robotic phrases).
        """
        issues = []
        
        # Concatenate all content
        content_fields = ["Intro"] + [f"section_{i:02d}_content" for i in range(1, 10)]
        all_content = " ".join([
            str(getattr(data, field, ""))
            for field in content_fields
            if getattr(data, field, None)
        ])
        
        # Check for em dashes
        em_dash_count = all_content.count(self.AI_MARKERS["em_dash"])
        if em_dash_count > 0:
            issues.append(QualityIssue(
                issue_type="em_dashes",
                severity="warning",
                description=f"Found {em_dash_count} em dashes (—) - AI marker",
                current_value=em_dash_count,
                target_value=0,
                field="all_content"
            ))
        
        # Check for robotic phrases
        found_phrases = [
            phrase for phrase in self.AI_MARKERS["robotic_phrases"]
            if phrase in all_content
        ]
        
        if found_phrases:
            issues.append(QualityIssue(
                issue_type="robotic_phrases",
                severity="warning",
                description=f"Found {len(found_phrases)} robotic phrases: {', '.join(found_phrases[:3])}{'...' if len(found_phrases) > 3 else ''}",
                current_value=found_phrases,
                target_value=[],
                field="all_content"
            ))
        
        return issues
    
    def _issues_to_rewrites(
        self,
        issues: List[QualityIssue],
        context: ExecutionContext
    ) -> List[RewriteInstruction]:
        """
        Convert quality issues to rewrite instructions.
        """
        rewrites = []
        job_config = context.job_config or {}
        primary_keyword = job_config.get("primary_keyword", "")
        
        for issue in issues:
            # Only fix critical issues and warnings (skip info)
            if issue.severity not in ["critical", "warning"]:
                continue
            
            if issue.issue_type == "keyword_overuse":
                # Generate semantic variations
                variations = self._generate_keyword_variations(primary_keyword)
                
                rewrites.append(RewriteInstruction(
                    target="all_sections",
                    instruction=f"Reduce '{primary_keyword}' from {issue.current_value} to {self.KEYWORD_TARGET_MIN}-{self.KEYWORD_TARGET_MAX} mentions. Replace excess with variations.",
                    mode=RewriteMode.QUALITY_FIX,
                    preserve_structure=True,
                    min_similarity=0.75,
                    max_similarity=0.95,
                    context={
                        "keyword": primary_keyword,
                        "current_count": issue.current_value,
                        "target_min": self.KEYWORD_TARGET_MIN,
                        "target_max": self.KEYWORD_TARGET_MAX,
                        "variations": variations
                    }
                ))
            
            elif issue.issue_type == "keyword_underuse":
                # Don't auto-fix underuse (risky to add keywords)
                # Just log it
                logger.info(f"Skipping keyword underuse fix (current={issue.current_value}, target={self.KEYWORD_TARGET_MIN}+)")
            
            elif issue.issue_type == "first_paragraph_short":
                rewrites.append(RewriteInstruction(
                    target="section_01_content",
                    instruction=f"First paragraph is only {issue.current_value} words. Expand to {self.FIRST_PARAGRAPH_MIN_WORDS}-{self.FIRST_PARAGRAPH_MAX_WORDS} words with context, examples, or data.",
                    mode=RewriteMode.QUALITY_FIX,
                    preserve_structure=True,
                    min_similarity=0.50,
                    max_similarity=0.85,
                    context={
                        "current_words": issue.current_value,
                        "target_min": self.FIRST_PARAGRAPH_MIN_WORDS,
                        "target_max": self.FIRST_PARAGRAPH_MAX_WORDS,
                        "paragraph_index": 1
                    }
                ))
            
            elif issue.issue_type == "first_paragraph_long":
                # Don't auto-fix long paragraphs (may be intentional)
                logger.info(f"Skipping long paragraph fix (current={issue.current_value} words)")
            
            elif issue.issue_type in ["em_dashes", "robotic_phrases"]:
                markers_found = []
                if issue.issue_type == "em_dashes":
                    markers_found.append(f"Em dashes (—) x{issue.current_value}")
                if issue.issue_type == "robotic_phrases":
                    markers_found.extend(issue.current_value)
                
                rewrites.append(RewriteInstruction(
                    target="all_content",
                    instruction="Remove AI language markers: em dashes and robotic phrases.",
                    mode=RewriteMode.QUALITY_FIX,
                    preserve_structure=True,
                    min_similarity=0.80,
                    max_similarity=0.95,
                    context={
                        "markers_found": markers_found
                    }
                ))
        
        return rewrites
    
    def _generate_keyword_variations(self, primary_keyword: str) -> List[str]:
        """
        Generate semantic variations for a keyword.
        
        This is a simple heuristic - could be improved with NLP.
        """
        # Extract the main concept (last 1-2 words usually)
        words = primary_keyword.split()
        
        variations = [
            "these tools",
            "these solutions",
            "these platforms",
            "the technology",
            "this approach"
        ]
        
        # Try to generate more specific variations
        if "AI" in primary_keyword or "artificial intelligence" in primary_keyword.lower():
            variations.extend([
                "AI assistants",
                "AI systems",
                "intelligent tools",
                "automated solutions"
            ])
        
        if "code" in primary_keyword.lower():
            variations.extend([
                "code generators",
                "development tools",
                "coding assistants"
            ])
        
        if "tool" in primary_keyword.lower():
            variations.extend([
                "software",
                "applications",
                "utilities"
            ])
        
        # Return unique variations (max 5)
        return list(dict.fromkeys(variations))[:5]
    
    def _check_academic_citations_stage2b(self, data: ArticleOutput) -> List[QualityIssue]:
        """
        Check for academic citations [N] (WARNING ONLY).
        ROOT_LEVEL_FIX_PLAN.md Issue 1 - CHANGED TO WARNING.
        
        Layer 4 regex cleanup guarantees removal, so this is informational only.
        """
        issues = []
        
        # Check all content fields
        all_text = data.Intro + " ".join([
            getattr(data, f"section_{i:02d}_content", "")
            for i in range(1, 10)
            if getattr(data, f"section_{i:02d}_content", "")
        ])
        
        if re.search(r'\[\d+\]', all_text):
            count = len(re.findall(r'\[\d+\]', all_text))
            issues.append(QualityIssue(
                issue_type="academic_citations",
                severity="warning",  # CHANGED FROM "critical" TO "warning"
                description=f"Academic citations [N] detected ({count} instances) - Layer 4 will clean",
                current_value=count,
                target_value=0,
                field="all_content"
            ))
        
        return issues
    
    def _check_em_dashes_stage2b(self, data: ArticleOutput) -> List[QualityIssue]:
        """
        Check for forbidden em dashes.
        ROOT_LEVEL_FIX_PLAN.md Issue 2.
        """
        issues = []
        
        # Check all content fields
        all_text = data.Intro + " ".join([
            getattr(data, f"section_{i:02d}_content", "")
            for i in range(1, 10)
            if getattr(data, f"section_{i:02d}_content", "")
        ])
        
        em_dash_patterns = [r'—', r'&mdash;', r'&#8212;', r'&#x2014;']
        total_count = 0
        
        for pattern in em_dash_patterns:
            matches = re.findall(pattern, all_text)
            total_count += len(matches)
        
        if total_count > 0:
            issues.append(QualityIssue(
                issue_type="em_dashes",
                severity="critical",
                description=f"Em dashes found ({total_count} instances)",
                current_value=total_count,
                target_value=0,
                field="all_content"
            ))
        
        return issues
    
    def _check_malformed_headings_stage2b(self, data: ArticleOutput) -> List[QualityIssue]:
        """
        Check for malformed headings (double question prefixes).
        ROOT_LEVEL_FIX_PLAN.md Issue A.
        """
        issues = []
        
        # Check section titles
        for i in range(1, 10):
            title_field = f"section_{i:02d}_title"
            title = getattr(data, title_field, "")
            
            if not title:
                continue
            
            # Check for "What is How/Why/What" patterns
            if re.search(r'^What is (How|Why|What|When|Where|Who)\b', title, re.IGNORECASE):
                issues.append(QualityIssue(
                    issue_type="malformed_heading",
                    severity="critical",
                    description=f"Malformed heading: '{title}' (duplicate question prefix)",
                    current_value=title,
                    target_value=re.sub(r'^What is ', '', title, flags=re.IGNORECASE),
                    field=title_field
                ))
        
        return issues
    
    def _build_comprehensive_rewrite(self, context: ExecutionContext) -> Optional[RewriteInstruction]:
        """
        Build a single comprehensive rewrite instruction for all content.
        
        This method creates ONE RewriteInstruction that fixes ALL issues at once:
        - Academic citations [N] → inline natural language
        - Standalone labels → natural list integration
        - Em dashes → contextual commas/removal
        - Robotic transitions → natural flow
        - Malformed headings → clean headings
        - Weird word passages → natural sentences
        - Incomplete sentences → complete thoughts
        - Double punctuation → single
        - Keyword overuse → natural distribution
        
        Args:
            context: ExecutionContext with all data
        
        Returns:
            RewriteInstruction for comprehensive transformation, or None if failed
        """
        try:
            # Extract citation metadata (will be populated by Stage 4 in parallel)
            # Note: Stage 2b runs BEFORE Stage 4, so citations might not be available yet
            # We'll pass empty list and handle in the prompt
            citations_list = context.parallel_results.get("citations_list") if hasattr(context, 'parallel_results') else None
            citations_data = []
            
            if citations_list and hasattr(citations_list, 'citations'):
                for citation in citations_list.citations:
                    citations_data.append({
                        'number': citation.number,
                        'url': citation.url,
                        'title': citation.title,
                    })
                logger.info(f"   Found {len(citations_data)} citations for inline transformation")
            else:
                # Citations not available yet (Stage 4 runs in parallel after Stage 2b)
                # Extract from Sources field instead
                sources_text = context.structured_data.Sources or ""
                if sources_text:
                    # Quick parse of [N]: URL – Title format
                    citation_pattern = r'\[(\d+)\]:\s*([^\s]+)\s*(?:–|-)?\s*([^\n]+)'
                    matches = re.findall(citation_pattern, sources_text)
                    for match in matches:
                        citations_data.append({
                            'number': int(match[0]),
                            'url': match[1],
                            'title': match[2].strip(),
                        })
                    logger.info(f"   Extracted {len(citations_data)} citations from Sources field")
            
            # Build context for the rewrite
            rewrite_context = {
                "citations": citations_data,
                "primary_keyword": context.job_config.get("primary_keyword", ""),
                "company_name": context.company_data.get("company_name", ""),
                "language": context.language or "en",
            }
            
            # Create comprehensive rewrite instruction
            rewrite = RewriteInstruction(
                target="all_content",  # Process entire article
                instruction="Comprehensive content transformation - fix all quality issues",
                mode=RewriteMode.COMPREHENSIVE_TRANSFORM,
                preserve_structure=True,
                min_similarity=0.70,  # Allow significant changes for comprehensive fix
                max_similarity=0.95,
                max_attempts=2,  # Only retry once if validation fails
                temperature=0.3,  # Lower temperature for consistent, predictable transformations
                context=rewrite_context
            )
            
            logger.info(f"   Built comprehensive rewrite instruction:")
            logger.info(f"   - Target: all content")
            logger.info(f"   - Citations available: {len(citations_data)}")
            logger.info(f"   - Primary keyword: {rewrite_context['primary_keyword'][:50]}...")
            
            return rewrite
        
        except Exception as e:
            logger.error(f"Failed to build comprehensive rewrite: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

