"""
Content Cleanup Pipeline - Consolidated content sanitization.

This module follows SOLID principles:
- Single Responsibility: Each CleanupRule handles one type of cleanup
- Open/Closed: New rules can be added without modifying existing code
- Liskov Substitution: All rules implement the same interface
- Interface Segregation: Rules only need pattern and replacement
- Dependency Inversion: Pipeline depends on abstract rules, not concrete implementations

Consolidates 100+ scattered regex operations into a single, efficient pipeline.
"""

import re
import logging
from typing import List, Dict, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto

logger = logging.getLogger(__name__)


class CleanupCategory(Enum):
    """Categories of cleanup operations for organization and logging."""
    CITATION = auto()      # Citation-related cleanup
    FORMATTING = auto()    # Markdown/HTML formatting
    PUNCTUATION = auto()   # Punctuation fixes
    CONTENT = auto()       # Content-level cleanup (duplicates, etc.)
    WHITESPACE = auto()    # Whitespace normalization
    SANITIZATION = auto()  # Security/HTML sanitization


@dataclass
class CleanupRule:
    """
    A single cleanup rule with pattern and replacement.
    
    Attributes:
        name: Human-readable name for logging
        pattern: Regex pattern to match
        replacement: Replacement string or callable
        category: Category for organization
        flags: Regex flags (default: 0)
        enabled: Whether rule is active
        priority: Lower numbers run first (default: 100)
    """
    name: str
    pattern: str
    replacement: str
    category: CleanupCategory
    flags: int = 0
    enabled: bool = True
    priority: int = 100


class ContentCleanupPipeline:
    """
    Consolidated content cleanup pipeline.
    
    Runs all cleanup operations in a single, organized pass.
    Provides logging, statistics, and easy rule management.
    
    Usage:
        pipeline = ContentCleanupPipeline()
        clean_content = pipeline.process(dirty_content)
    """
    
    # Default cleanup rules organized by category
    DEFAULT_RULES: List[CleanupRule] = [
        # === CITATION CLEANUP (priority 10-19) ===
        CleanupRule(
            name="strip_linked_academic_citations",
            pattern=r'<a[^>]*href=["\']#source-\d+["\'][^>]*>\s*\[\d+\]\s*</a>',
            replacement='',
            category=CleanupCategory.CITATION,
            priority=10,
        ),
        CleanupRule(
            name="strip_standalone_academic_citations",
            pattern=r'\[\d+\]',
            replacement='',
            category=CleanupCategory.CITATION,
            priority=11,
        ),
        
        # === FORMATTING CLEANUP (priority 20-39) ===
        CleanupRule(
            name="markdown_bold_to_html",
            pattern=r'\*\*([^*]+)\*\*',
            replacement=r'<strong>\1</strong>',
            category=CleanupCategory.FORMATTING,
            priority=20,
        ),
        CleanupRule(
            name="markdown_italic_to_html",
            pattern=r'(?<!\*)\*([^*]+)\*(?!\*)',
            replacement=r'<em>\1</em>',
            category=CleanupCategory.FORMATTING,
            priority=21,
        ),
        CleanupRule(
            name="fix_double_paragraph_tags",
            pattern=r'<p>\s*<p>',
            replacement='<p>',
            category=CleanupCategory.FORMATTING,
            priority=25,
        ),
        CleanupRule(
            name="fix_unclosed_paragraph_tags",
            pattern=r'</p>\s*</p>',
            replacement='</p>',
            category=CleanupCategory.FORMATTING,
            priority=26,
        ),
        
        # === PUNCTUATION CLEANUP (priority 40-59) ===
        CleanupRule(
            name="fix_period_dash_pattern",
            pattern=r'\.\s*-\s+([A-Z])',
            replacement=r'. \1',
            category=CleanupCategory.PUNCTUATION,
            priority=40,
        ),
        CleanupRule(
            name="fix_colon_dash_spacing",
            pattern=r':\s*\n\s*-\s+',
            replacement=r':\n\n- ',
            category=CleanupCategory.PUNCTUATION,
            priority=41,
        ),
        CleanupRule(
            name="fix_space_before_punctuation",
            pattern=r' ([.,;:!?])',
            replacement=r'\1',
            category=CleanupCategory.PUNCTUATION,
            priority=42,
        ),
        CleanupRule(
            name="fix_missing_space_after_punctuation",
            pattern=r'([.,;:!?])([A-Z])',
            replacement=r'\1 \2',
            category=CleanupCategory.PUNCTUATION,
            priority=43,
        ),
        CleanupRule(
            name="fix_em_dash",
            pattern=r'—',
            replacement=' - ',
            category=CleanupCategory.PUNCTUATION,
            priority=44,
        ),
        CleanupRule(
            name="fix_en_dash",
            pattern=r'–',
            replacement='-',
            category=CleanupCategory.PUNCTUATION,
            priority=45,
        ),
        
        # === CONTENT CLEANUP (priority 60-79) ===
        CleanupRule(
            name="remove_duplicate_summary_intro_1",
            pattern=r'<p>\s*Here are (?:the )?key (?:points|takeaways|considerations|benefits)[:\s]*</p>',
            replacement='',
            category=CleanupCategory.CONTENT,
            flags=re.IGNORECASE,
            priority=60,
        ),
        CleanupRule(
            name="remove_inline_summary_intro",
            pattern=r'Here are (?:the )?key (?:points|takeaways|considerations|benefits):\s*',
            replacement='',
            category=CleanupCategory.CONTENT,
            flags=re.IGNORECASE,
            priority=60,
        ),
        CleanupRule(
            name="remove_duplicate_summary_intro_2",
            pattern=r'<p>\s*Important considerations[:\s]*</p>',
            replacement='',
            category=CleanupCategory.CONTENT,
            flags=re.IGNORECASE,
            priority=61,
        ),
        CleanupRule(
            name="remove_inline_important",
            pattern=r'Important considerations:\s*',
            replacement='',
            category=CleanupCategory.CONTENT,
            flags=re.IGNORECASE,
            priority=61,
        ),
        CleanupRule(
            name="remove_duplicate_summary_intro_3",
            pattern=r'<p>\s*Key benefits include[:\s]*</p>',
            replacement='',
            category=CleanupCategory.CONTENT,
            flags=re.IGNORECASE,
            priority=62,
        ),
        CleanupRule(
            name="remove_inline_key_benefits",
            pattern=r'Key benefits include:\s*',
            replacement='',
            category=CleanupCategory.CONTENT,
            flags=re.IGNORECASE,
            priority=62,
        ),
        CleanupRule(
            name="remove_matters_orphan",
            pattern=r'matters:\s*',
            replacement='',
            category=CleanupCategory.CONTENT,
            flags=re.IGNORECASE,
            priority=63,
        ),
        CleanupRule(
            name="fix_double_comma",
            pattern=r',\s*,',
            replacement=',',
            category=CleanupCategory.PUNCTUATION,
            priority=48,
        ),
        CleanupRule(
            name="fix_period_also_comma",
            pattern=r'\.\s*Also,\s*,',
            replacement='. Also,',
            category=CleanupCategory.PUNCTUATION,
            flags=re.IGNORECASE,
            priority=49,
        ),
        CleanupRule(
            name="remove_empty_list_items",
            pattern=r'<li>\s*</li>',
            replacement='',
            category=CleanupCategory.CONTENT,
            priority=65,
        ),
        CleanupRule(
            name="remove_punctuation_only_list_items",
            pattern=r'<li>\s*[.,;:\-]*\s*</li>',
            replacement='',
            category=CleanupCategory.CONTENT,
            priority=66,
        ),
        CleanupRule(
            name="remove_label_only_list_items",
            pattern=r'<li>\s*<strong>[^<]*:</strong>\s*</li>',
            replacement='',
            category=CleanupCategory.CONTENT,
            priority=67,
        ),
        CleanupRule(
            name="remove_empty_strong_paragraphs",
            pattern=r'<p>\s*<strong>[^<]+:</strong>\s*</p>',
            replacement='',
            category=CleanupCategory.CONTENT,
            priority=68,
        ),
        
        # === WHITESPACE CLEANUP (priority 80-89) ===
        CleanupRule(
            name="normalize_multiple_spaces",
            pattern=r'  +',
            replacement=' ',
            category=CleanupCategory.WHITESPACE,
            priority=80,
        ),
        CleanupRule(
            name="normalize_multiple_newlines",
            pattern=r'\n{3,}',
            replacement='\n\n',
            category=CleanupCategory.WHITESPACE,
            priority=81,
        ),
        
        # === TYPO CORRECTIONS (priority 70-79) ===
        CleanupRule(
            name="typo_applys",
            pattern=r'\bapplys\b',
            replacement='applies',
            category=CleanupCategory.CONTENT,
            flags=re.IGNORECASE,
            priority=70,
        ),
        CleanupRule(
            name="typo_applyd",
            pattern=r'\bapplyd\b',
            replacement='applied',
            category=CleanupCategory.CONTENT,
            flags=re.IGNORECASE,
            priority=70,
        ),
        CleanupRule(
            name="typo_analyzs",
            pattern=r'\banalyzs\b',
            replacement='analyzes',
            category=CleanupCategory.CONTENT,
            flags=re.IGNORECASE,
            priority=70,
        ),
        CleanupRule(
            name="typo_optimizs",
            pattern=r'\boptimizs\b',
            replacement='optimizes',
            category=CleanupCategory.CONTENT,
            flags=re.IGNORECASE,
            priority=70,
        ),
        CleanupRule(
            name="typo_utilizs",
            pattern=r'\butilizs\b',
            replacement='utilizes',
            category=CleanupCategory.CONTENT,
            flags=re.IGNORECASE,
            priority=70,
        ),
        
        # === GEMINI HALLUCINATION FIXES (priority 50-59) ===
        CleanupRule(
            name="fix_heres_this",
            pattern=r"Here's this\s+",
            replacement='This ',
            category=CleanupCategory.CONTENT,
            flags=re.IGNORECASE,
            priority=50,
        ),
        CleanupRule(
            name="fix_you_can_effective",
            pattern=r'\bYou can effective\s+',
            replacement='Effective ',
            category=CleanupCategory.CONTENT,
            flags=re.IGNORECASE,
            priority=51,
        ),
        CleanupRule(
            name="fix_so_you_can_strategy",
            pattern=r'\bso you can strategy\b',
            replacement='',
            category=CleanupCategory.CONTENT,
            flags=re.IGNORECASE,
            priority=52,
        ),
        CleanupRule(
            name="fix_youll_find_the",
            pattern=r"\bYou'll find The\s+",
            replacement='The ',
            category=CleanupCategory.CONTENT,
            flags=re.IGNORECASE,
            priority=53,
        ),
        CleanupRule(
            name="fix_orphaned_matters",
            pattern=r'<p>\s*(matters|so you can|if you want):\s*</p>',
            replacement='',
            category=CleanupCategory.CONTENT,
            flags=re.IGNORECASE,
            priority=54,
        ),
        CleanupRule(
            name="fix_double_punctuation",
            pattern=r'([.,;:!?])\1+',
            replacement=r'\1',
            category=CleanupCategory.PUNCTUATION,
            priority=46,
        ),
        CleanupRule(
            name="fix_period_also",
            pattern=r'<p>\s*\.\s*Also,\s*',
            replacement='<p>Also, ',
            category=CleanupCategory.PUNCTUATION,
            flags=re.IGNORECASE,
            priority=47,
        ),
        CleanupRule(
            name="fix_empty_paragraphs",
            pattern=r'<p>\s*</p>',
            replacement='',
            category=CleanupCategory.CONTENT,
            priority=69,
        ),
        CleanupRule(
            name="fix_empty_lists",
            pattern=r'<(ul|ol)>\s*</\1>',
            replacement='',
            category=CleanupCategory.CONTENT,
            flags=re.IGNORECASE,
            priority=69,
        ),
        
        # === WHITESPACE CLEANUP (priority 80-89) ===
        CleanupRule(
            name="normalize_multiple_spaces",
            pattern=r'  +',
            replacement=' ',
            category=CleanupCategory.WHITESPACE,
            priority=80,
        ),
        CleanupRule(
            name="normalize_multiple_newlines",
            pattern=r'\n{3,}',
            replacement='\n\n',
            category=CleanupCategory.WHITESPACE,
            priority=81,
        ),
        
        # === SANITIZATION (priority 90-99) ===
        CleanupRule(
            name="strip_html_entities",
            pattern=r'&nbsp;',
            replacement=' ',
            category=CleanupCategory.SANITIZATION,
            priority=90,
        ),
    ]
    
    def __init__(self, rules: Optional[List[CleanupRule]] = None):
        """
        Initialize the cleanup pipeline.
        
        Args:
            rules: Custom rules to use. If None, uses DEFAULT_RULES.
        """
        self.rules = sorted(
            rules or self.DEFAULT_RULES.copy(),
            key=lambda r: r.priority
        )
        self.stats: Dict[str, int] = {}
    
    def add_rule(self, rule: CleanupRule) -> None:
        """Add a new rule and re-sort by priority."""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority)
    
    def disable_rule(self, name: str) -> None:
        """Disable a rule by name."""
        for rule in self.rules:
            if rule.name == name:
                rule.enabled = False
                break
    
    def enable_rule(self, name: str) -> None:
        """Enable a rule by name."""
        for rule in self.rules:
            if rule.name == name:
                rule.enabled = True
                break
    
    def process(self, content: str, log_changes: bool = False) -> str:
        """
        Process content through all cleanup rules.
        
        Args:
            content: Content to clean
            log_changes: Whether to log each change made
            
        Returns:
            Cleaned content
        """
        if not content:
            return ""
        
        self.stats = {}
        original_length = len(content)
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            try:
                # Count matches before replacement
                matches = len(re.findall(rule.pattern, content, flags=rule.flags))
                
                if matches > 0:
                    content = re.sub(
                        rule.pattern,
                        rule.replacement,
                        content,
                        flags=rule.flags
                    )
                    self.stats[rule.name] = matches
                    
                    if log_changes:
                        logger.debug(f"  {rule.name}: {matches} replacements")
                        
            except re.error as e:
                logger.error(f"Regex error in rule '{rule.name}': {e}")
        
        # Log summary
        total_changes = sum(self.stats.values())
        if total_changes > 0:
            logger.info(f"🧹 ContentCleanupPipeline: {total_changes} changes across {len(self.stats)} rules")
        
        return content
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics from last process() call."""
        return self.stats.copy()
    
    def get_rules_by_category(self, category: CleanupCategory) -> List[CleanupRule]:
        """Get all rules in a category."""
        return [r for r in self.rules if r.category == category]


# Singleton instance for convenience
_default_pipeline: Optional[ContentCleanupPipeline] = None


def get_cleanup_pipeline() -> ContentCleanupPipeline:
    """Get the default cleanup pipeline (singleton)."""
    global _default_pipeline
    if _default_pipeline is None:
        _default_pipeline = ContentCleanupPipeline()
    return _default_pipeline


def cleanup_content(content: str) -> str:
    """
    Convenience function to clean content using default pipeline.
    
    This is the main entry point for content cleanup.
    Replaces scattered re.sub calls throughout the codebase.
    
    Args:
        content: Content to clean
        
    Returns:
        Cleaned content
    """
    return get_cleanup_pipeline().process(content)

