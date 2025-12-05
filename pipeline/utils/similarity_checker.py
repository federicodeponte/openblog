"""
Content Similarity Checker - SEO-level duplicate detection.

Language-agnostic, scalable duplicate detection for blog content.

Detects content cannibalization like SEObility/Screaming Frog:
- Keyword cannibalization (same target keyword)
- Title/meta overlap
- Heading similarity (H2s covering same topics)  
- Content overlap (character shingles - works for ANY language)
- FAQ/PAA duplication

Design principles:
- Language-agnostic: Uses character shingles, not word-based stop words
- Scalable: SQLite storage with indexed lookups
- Standalone: No external dependencies

Usage:
    checker = ContentSimilarityChecker()
    
    # Check before generating
    issues = checker.check_keyword(new_keyword)
    
    # Check after generating  
    report = checker.check_article(new_article)
    if report.is_duplicate:
        print(f"Too similar to: {report.similar_to}")
    
    # Store for future checks
    checker.store_article(article)
"""

import json
import os
import re
import sqlite3
import hashlib
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Set, Tuple
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class ArticleFingerprint:
    """Fingerprint of an article for similarity comparison."""
    slug: str
    primary_keyword: str
    meta_title: str
    headings: List[str]  # H2s normalized
    shingles: Set[str]  # Character-level shingles (language-agnostic)
    faq_questions: List[str]
    intro_fingerprint: str  # Hash of normalized intro
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['shingles'] = list(d['shingles'])  # Convert set to list for JSON
        return d
    
    @classmethod
    def from_dict(cls, data: dict) -> "ArticleFingerprint":
        data['shingles'] = set(data.get('shingles', []))
        return cls(**data)


@dataclass 
class SimilarityReport:
    """Detailed similarity report."""
    is_duplicate: bool
    overall_score: float  # 0-100
    similar_to: Optional[str] = None
    
    # Detailed scores
    keyword_match: bool = False
    title_similarity: float = 0.0
    heading_overlap: float = 0.0
    content_overlap: float = 0.0  # Shingle-based (Jaccard)
    faq_overlap: float = 0.0
    
    # Specific issues found
    issues: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return asdict(self)


class ContentSimilarityChecker:
    """
    Language-agnostic content similarity checker using character shingles.
    
    Shingles = overlapping substrings of k characters.
    Works for ANY language without stop word lists.
    
    Thresholds:
    - DUPLICATE_THRESHOLD: 70% = definite duplicate
    - WARNING_THRESHOLD: 50% = potential cannibalization
    """
    
    DUPLICATE_THRESHOLD = 70.0
    WARNING_THRESHOLD = 50.0
    SHINGLE_SIZE = 5  # 5-character shingles (good balance)
    MIN_SHINGLES = 100  # Minimum shingles to store per article
    
    def __init__(self, db_path: str = "content_fingerprints.db"):
        """
        Initialize with SQLite storage for scalability.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database with proper schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    slug TEXT PRIMARY KEY,
                    primary_keyword TEXT,
                    meta_title TEXT,
                    headings TEXT,  -- JSON array
                    shingles TEXT,  -- JSON array of hashed shingles
                    faq_questions TEXT,  -- JSON array
                    intro_fingerprint TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_keyword ON articles(primary_keyword)")
            conn.commit()
    
    # ========== SHINGLE EXTRACTION (Language-Agnostic) ==========
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for comparison - language-agnostic.
        
        - Lowercase
        - Remove HTML tags
        - Collapse whitespace
        - Keep all unicode characters (works for any language)
        """
        if not text:
            return ""
        text = text.lower()
        text = re.sub(r'<[^>]+>', ' ', text)  # Remove HTML
        text = re.sub(r'\s+', ' ', text)  # Collapse whitespace
        text = text.strip()
        return text
    
    def _extract_shingles(self, text: str, k: int = None) -> Set[str]:
        """
        Extract character-level shingles (k-grams).
        
        Character shingles work for ANY language because they don't
        depend on word boundaries or stop words.
        
        Args:
            text: Input text
            k: Shingle size (default: SHINGLE_SIZE)
            
        Returns:
            Set of shingle hashes (for efficient storage/comparison)
        """
        k = k or self.SHINGLE_SIZE
        text = self._normalize_text(text)
        
        if len(text) < k:
            return set()
        
        shingles = set()
        for i in range(len(text) - k + 1):
            shingle = text[i:i+k]
            # Hash for efficient storage (8 chars = 32 bits)
            shingle_hash = hashlib.md5(shingle.encode('utf-8')).hexdigest()[:8]
            shingles.add(shingle_hash)
        
        return shingles
    
    def _jaccard_similarity(self, set1: Set[str], set2: Set[str]) -> float:
        """
        Calculate Jaccard similarity between two sets.
        
        Jaccard = |A ∩ B| / |A ∪ B|
        
        Works for any language since it's set-based.
        """
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    # ========== FINGERPRINT EXTRACTION ==========
    
    def extract_fingerprint(self, article: dict, slug: str = None) -> ArticleFingerprint:
        """
        Extract language-agnostic fingerprint from article.
        """
        # Slug
        slug = slug or article.get("slug") or self._generate_slug(
            article.get("Headline") or article.get("headline", "")
        )
        
        # Primary keyword (normalized)
        primary_keyword = self._normalize_text(
            article.get("primary_keyword") or article.get("keyword", "")
        )
        
        # Meta title
        meta_title = self._normalize_text(
            article.get("Meta_Title") or article.get("meta_title", "")
        )
        
        # Headings
        headings = self._extract_headings(article)
        
        # Content shingles (the main comparison mechanism)
        content_text = self._extract_full_content(article)
        shingles = self._extract_shingles(content_text)
        
        # FAQ questions
        faq_questions = self._extract_faq_questions(article)
        
        # Intro fingerprint
        intro = article.get("Intro") or article.get("intro", "")
        intro_fingerprint = hashlib.md5(
            self._normalize_text(intro[:500]).encode('utf-8')
        ).hexdigest()[:16]
        
        return ArticleFingerprint(
            slug=slug,
            primary_keyword=primary_keyword,
            meta_title=meta_title,
            headings=headings,
            shingles=shingles,
            faq_questions=faq_questions,
            intro_fingerprint=intro_fingerprint,
        )
    
    def _extract_full_content(self, article: dict) -> str:
        """Extract all text content for shingle generation."""
        parts = []
        
        # Headline (weighted 3x)
        headline = article.get("Headline") or article.get("headline", "")
        parts.extend([headline] * 3)
        
        # Intro
        parts.append(article.get("Intro") or article.get("intro", ""))
        
        # Sections
        for i in range(1, 15):
            content = (
                article.get(f"section_{i:02d}_content") or 
                article.get(f"Section_{i:02d}_Content", "")
            )
            if content:
                parts.append(content)
        
        # Key takeaways
        for i in range(1, 6):
            takeaway = (
                article.get(f"key_takeaway_{i:02d}") or 
                article.get(f"Key_Takeaway_{i:02d}", "")
            )
            if takeaway:
                parts.append(takeaway)
        
        return " ".join(parts)
    
    def _extract_headings(self, article: dict) -> List[str]:
        """Extract normalized headings."""
        headings = []
        
        # From ToC
        toc = article.get("table_of_contents") or article.get("ToC", [])
        if isinstance(toc, list):
            for item in toc:
                if isinstance(item, dict):
                    headings.append(self._normalize_text(item.get("title", "")))
                elif isinstance(item, str):
                    headings.append(self._normalize_text(item))
        
        # From sections
        for i in range(1, 15):
            heading = (
                article.get(f"section_{i:02d}_heading") or 
                article.get(f"Section_{i:02d}_Heading", "")
            )
            if heading:
                headings.append(self._normalize_text(heading))
        
        return [h for h in headings if h]
    
    def _extract_faq_questions(self, article: dict) -> List[str]:
        """Extract normalized FAQ questions."""
        questions = []
        
        for key in ["FAQ", "faq", "PAA", "paa"]:
            items = article.get(key, [])
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        q = item.get("question", "")
                        if q:
                            questions.append(self._normalize_text(q))
        
        return questions
    
    def _generate_slug(self, title: str) -> str:
        """Generate slug from title."""
        slug = self._normalize_text(title)
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s]+', '-', slug)
        return slug[:60]
    
    # ========== DATABASE OPERATIONS ==========
    
    def store_article(self, article: dict, slug: str = None):
        """Store article fingerprint in database."""
        fp = self.extract_fingerprint(article, slug)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO articles 
                (slug, primary_keyword, meta_title, headings, shingles, faq_questions, intro_fingerprint)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                fp.slug,
                fp.primary_keyword,
                fp.meta_title,
                json.dumps(fp.headings),
                json.dumps(list(fp.shingles)),
                json.dumps(fp.faq_questions),
                fp.intro_fingerprint,
            ))
            conn.commit()
        
        logger.info(f"Stored fingerprint for '{fp.slug}' ({len(fp.shingles)} shingles)")
    
    def _load_fingerprint(self, row: tuple) -> ArticleFingerprint:
        """Load fingerprint from database row."""
        return ArticleFingerprint(
            slug=row[0],
            primary_keyword=row[1],
            meta_title=row[2],
            headings=json.loads(row[3]) if row[3] else [],
            shingles=set(json.loads(row[4])) if row[4] else set(),
            faq_questions=json.loads(row[5]) if row[5] else [],
            intro_fingerprint=row[6] or "",
        )
    
    def _get_all_fingerprints(self) -> List[ArticleFingerprint]:
        """Load all fingerprints from database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT slug, primary_keyword, meta_title, headings, shingles, faq_questions, intro_fingerprint
                FROM articles
            """)
            return [self._load_fingerprint(row) for row in cursor.fetchall()]
    
    def remove_article(self, slug: str):
        """Remove article from database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM articles WHERE slug = ?", (slug,))
            conn.commit()
    
    def list_articles(self) -> List[str]:
        """List all stored article slugs."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT slug FROM articles ORDER BY created_at DESC")
            return [row[0] for row in cursor.fetchall()]
    
    def get_stats(self) -> dict:
        """Get database statistics."""
        with sqlite3.connect(self.db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
            return {
                "total_articles": count,
                "db_path": str(self.db_path),
                "db_size_kb": self.db_path.stat().st_size / 1024 if self.db_path.exists() else 0,
            }
    
    # ========== COMPARISON ==========
    
    def check_keyword(self, keyword: str) -> Tuple[bool, List[str]]:
        """
        Check if keyword is already targeted.
        
        Returns:
            (is_duplicate, list of slugs with same/similar keyword)
        """
        keyword = self._normalize_text(keyword)
        keyword_words = set(keyword.split())
        matches = []
        
        with sqlite3.connect(self.db_path) as conn:
            # Exact match first
            cursor = conn.execute(
                "SELECT slug FROM articles WHERE primary_keyword = ?",
                (keyword,)
            )
            for row in cursor.fetchall():
                matches.append(row[0])
            
            # Fuzzy match (80%+ word overlap)
            if not matches:
                cursor = conn.execute("SELECT slug, primary_keyword FROM articles")
                for slug, pk in cursor.fetchall():
                    pk_words = set(pk.split())
                    if pk_words and keyword_words:
                        overlap = len(pk_words & keyword_words) / max(len(pk_words), len(keyword_words))
                        if overlap >= 0.8:
                            matches.append(slug)
        
        return bool(matches), matches
    
    def check_article(self, article: dict, slug: str = None) -> SimilarityReport:
        """
        Check article against all stored fingerprints.
        
        Uses Jaccard similarity on character shingles for
        language-agnostic content comparison.
        """
        new_fp = self.extract_fingerprint(article, slug)
        existing = self._get_all_fingerprints()
        
        if not existing:
            return SimilarityReport(is_duplicate=False, overall_score=0.0)
        
        best_match = None
        best_score = 0.0
        best_report = None
        
        for old_fp in existing:
            if old_fp.slug == new_fp.slug:
                continue
            
            report = self._compare(new_fp, old_fp)
            if report.overall_score > best_score:
                best_score = report.overall_score
                best_match = old_fp.slug
                best_report = report
        
        if best_report is None:
            return SimilarityReport(is_duplicate=False, overall_score=0.0)
        
        best_report.similar_to = best_match
        best_report.is_duplicate = best_score >= self.DUPLICATE_THRESHOLD
        
        return best_report
    
    def _compare(self, new: ArticleFingerprint, old: ArticleFingerprint) -> SimilarityReport:
        """Compare two fingerprints using language-agnostic methods."""
        issues = []
        
        # 1. Keyword match (critical)
        keyword_match = new.primary_keyword == old.primary_keyword
        if keyword_match:
            issues.append(f"CRITICAL: Same target keyword")
        
        # 2. Title similarity (Jaccard on words)
        title_sim = self._word_similarity(new.meta_title, old.meta_title)
        if title_sim > 0.6:
            issues.append(f"High title similarity ({title_sim:.0%})")
        
        # 3. Heading overlap
        heading_overlap = self._list_overlap(new.headings, old.headings)
        if heading_overlap > 0.4:
            issues.append(f"Overlapping headings ({heading_overlap:.0%})")
        
        # 4. Content overlap (MAIN CHECK - shingle-based Jaccard)
        content_overlap = self._jaccard_similarity(new.shingles, old.shingles)
        if content_overlap > 0.2:
            issues.append(f"Content similarity ({content_overlap:.0%})")
        
        # 5. FAQ overlap
        faq_overlap = self._list_overlap(new.faq_questions, old.faq_questions)
        if faq_overlap > 0.4:
            issues.append(f"FAQ overlap ({faq_overlap:.0%})")
        
        # 6. Intro match
        intro_match = new.intro_fingerprint == old.intro_fingerprint
        if intro_match:
            issues.append("Identical intro")
        
        # Weighted overall score
        overall = (
            (30 if keyword_match else 0) +
            (title_sim * 15) +
            (heading_overlap * 15) +
            (content_overlap * 30) +  # Content is most important
            (faq_overlap * 5) +
            (5 if intro_match else 0)
        )
        
        return SimilarityReport(
            is_duplicate=False,
            overall_score=min(overall, 100),
            keyword_match=keyword_match,
            title_similarity=title_sim * 100,
            heading_overlap=heading_overlap * 100,
            content_overlap=content_overlap * 100,
            faq_overlap=faq_overlap * 100,
            issues=issues,
        )
    
    def _word_similarity(self, text1: str, text2: str) -> float:
        """Jaccard similarity on words (language-agnostic)."""
        if not text1 or not text2:
            return 0.0
        
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        return len(words1 & words2) / len(words1 | words2)
    
    def _list_overlap(self, list1: List[str], list2: List[str]) -> float:
        """Overlap ratio between two lists."""
        if not list1 or not list2:
            return 0.0
        
        # Use shingles for each item for fuzzy matching
        matches = 0
        for item1 in list1:
            for item2 in list2:
                sim = self._word_similarity(item1, item2)
                if sim > 0.7:  # 70% word match = same heading
                    matches += 1
                    break
        
        return matches / len(list1) if list1 else 0.0
    
    def clear(self):
        """Clear all stored fingerprints."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM articles")
            conn.commit()


# ========== CONVENIENCE FUNCTIONS ==========

def check_for_duplicates(
    article: dict,
    db_path: str = "content_fingerprints.db"
) -> SimilarityReport:
    """Quick check if article is duplicate."""
    checker = ContentSimilarityChecker(db_path)
    return checker.check_article(article)


def store_article_fingerprint(
    article: dict,
    slug: str = None,
    db_path: str = "content_fingerprints.db"
):
    """Store article fingerprint for future checks."""
    checker = ContentSimilarityChecker(db_path)
    checker.store_article(article, slug)
