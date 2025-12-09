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
        Execute Stage 2b: Detect and fix quality issues.
        
        Args:
            context: ExecutionContext with structured_data from Stage 2
        
        Returns:
            Updated context with refined structured_data
        """
        logger.info(f"Stage 2b: {self.stage_name}")
        
        # Validate input
        if not context.structured_data:
            logger.warning("No structured_data available, skipping refinement")
            return context
        
        # Detect quality issues
        issues = self._detect_quality_issues(context)
        
        if not issues:
            logger.info("✅ No quality issues detected, skipping refinement")
            return context
        
        # Log detected issues
        critical_issues = [i for i in issues if i.severity == "critical"]
        warning_issues = [i for i in issues if i.severity == "warning"]
        
        logger.info(f"🔍 Detected {len(issues)} quality issues:")
        logger.info(f"   Critical: {len(critical_issues)}")
        logger.info(f"   Warnings: {len(warning_issues)}")
        
        for issue in issues:
            logger.info(f"   {issue.severity.upper()}: {issue.description}")
        
        # Convert issues to rewrite instructions
        rewrites = self._issues_to_rewrites(issues, context)
        
        if not rewrites:
            logger.warning("No rewrites generated from issues, skipping refinement")
            return context
        
        logger.info(f"🔧 Applying {len(rewrites)} targeted rewrites...")
        logger.info("🔄 Attempting Gemini-based fixes (best effort, non-blocking)...")
        
        # Execute rewrites
        try:
            article_dict = context.structured_data.dict()
            
            updated_article = await targeted_rewrite(
                article=article_dict,
                rewrites=rewrites
            )
            
            # Update context with refined data
            context.structured_data = ArticleOutput(**updated_article)
            
            logger.info("✅ Gemini quality refinement complete")
            
            # Re-check quality (for logging)
            remaining_issues = self._detect_quality_issues(context)
            if remaining_issues:
                logger.warning(f"⚠️  {len(remaining_issues)} issues remain after Gemini refinement")
                logger.info("🛡️  Layer 3 (regex fallback) will catch these in html_renderer.py")
            else:
                logger.info("✅ All quality issues resolved by Gemini")
        
        except Exception as e:
            logger.warning(f"⚠️  Gemini refinement failed: {str(e)}")
            logger.info("🛡️  Continuing with original content - Layer 3 (regex) will fix issues")
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
        
        # Issue 4: Academic citations (needs conversion to natural language)
        academic_citation_issue = self._check_academic_citations(data)
        if academic_citation_issue:
            issues.append(academic_citation_issue)
        
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
    
    def _check_academic_citations(self, data: ArticleOutput) -> Optional[QualityIssue]:
        """
        Check for academic citations [1], [2], [1][2] that need conversion to natural language.
        """
        import re
        
        # Get all content fields
        content_fields = ["Headline", "Direct_Answer", "Intro"]
        for i in range(1, 10):
            content_fields.extend([
                f"section_{i:02d}_title",
                f"section_{i:02d}_content"
            ])
        
        # Check for academic citation patterns [N], [N][M], etc.
        academic_patterns = [
            r'\[\d+\]',  # [1], [2], etc.
            r'\[\d+\]\[\d+\]',  # [1][2], [2][3], etc.
            r'\[\d+\]\[\d+\]\[\d+\]',  # [1][2][3], etc.
        ]
        
        found_citations = []
        for field in content_fields:
            content = str(getattr(data, field, ""))
            if content:
                for pattern in academic_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        found_citations.extend([(field, match) for match in matches])
        
        if found_citations:
            return QualityIssue(
                issue_type="academic_citations",
                severity="critical",
                description=f"Found {len(found_citations)} academic citations [N] that must be converted to natural language inline links",
                current_value=len(found_citations),
                target_value=0,
                field="all_content"
            )
        
        return None
    
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
            
            elif issue.issue_type == "academic_citations":
                rewrites.append(RewriteInstruction(
                    target="all_content",
                    instruction="Convert academic citations [1], [2], [1][2] to natural language inline links. Replace [N] with contextual phrases like 'according to [source]', 'per [study]', '[company]'s research shows'. Format as: <a href=\"#source-N\" class=\"citation\">according to GitHub</a>",
                    mode=RewriteMode.QUALITY_FIX,
                    preserve_structure=True,
                    min_similarity=0.70,
                    max_similarity=0.90,
                    context={
                        "academic_citations_found": issue.current_value
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

