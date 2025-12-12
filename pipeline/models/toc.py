"""
Table of Contents (ToC) Model

Represents navigation labels for article sections.

Structure:
- toc_01 through toc_09: Short labels for navigation
- Full section titles are in ArticleOutput
- ToC labels are 1-2 words maximum for readability
"""

from typing import Optional, Dict, List
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class TOCEntry(BaseModel):
    """
    Single table of contents entry.

    Attributes:
        section_num: Section number (1-9)
        full_title: Full section title (from ArticleOutput)
        short_label: Short label for navigation (1-2 words)
    """

    section_num: int = Field(..., description="Section number (1-9)", ge=1, le=9)
    full_title: str = Field(..., description="Full section title")
    short_label: str = Field(..., description="Short label (1-2 words)")

    @property
    def toc_key(self) -> str:
        """Get the toc_XX key format."""
        return f"toc_{self.section_num:02d}"

    def word_count(self) -> int:
        """Get word count of label."""
        return len(self.short_label.split())

    def __repr__(self) -> str:
        """String representation."""
        return f"TOCEntry({self.section_num}: {self.short_label})"


class TableOfContents(BaseModel):
    """
    Complete table of contents.

    Maps section numbers to short navigation labels.
    """

    entries: List[TOCEntry] = Field(default_factory=list, description="ToC entries")

    def add_entry(
        self, section_num: int, full_title: str, short_label: str
    ) -> "TableOfContents":
        """
        Add a ToC entry.

        Args:
            section_num: Section number (1-9)
            full_title: Full section title
            short_label: Short navigation label (1-2 words)

        Returns:
            self for chaining
        """
        entry = TOCEntry(section_num=section_num, full_title=full_title, short_label=short_label)
        self.entries.append(entry)
        return self

    def to_dict(self) -> Dict[str, str]:
        """
        Convert to dictionary format {01: label, 02: label, ...}.

        NOTE: Uses simple numeric keys (01, 02) not toc_01, toc_02
        because stage_10_cleanup flattens nested dicts with prefix.
        So toc["01"] becomes toc_01 after flattening.

        Returns:
            Dictionary with numeric keys and short labels as values.
        """
        result = {}
        for entry in self.entries:
            # Use simple numeric key, will become toc_01 after flattening
            result[f"{entry.section_num:02d}"] = entry.short_label
        return result

    def get_entry(self, section_num: int) -> Optional[TOCEntry]:
        """Get entry by section number."""
        for entry in self.entries:
            if entry.section_num == section_num:
                return entry
        return None

    def validate_labels(self) -> bool:
        """
        Validate all labels meet requirements.

        Requirements:
        - 1-2 words per label
        - Non-empty
        - Not too long

        Returns:
            True if all valid, False otherwise
        """
        valid = True
        for entry in self.entries:
            word_count = entry.word_count()
            if word_count == 0:
                logger.warning(f"Empty label for section {entry.section_num}")
                valid = False
            elif word_count > 2:
                logger.warning(
                    f"Label too long for section {entry.section_num}: "
                    f"{word_count} words (max 2)"
                )
                valid = False

            if len(entry.short_label) > 50:
                logger.warning(
                    f"Label too long for section {entry.section_num}: "
                    f"{len(entry.short_label)} chars"
                )
                valid = False

        return valid

    def count(self) -> int:
        """Get number of entries."""
        return len(self.entries)

    def __repr__(self) -> str:
        """String representation."""
        return f"TableOfContents({len(self.entries)} entries)"
