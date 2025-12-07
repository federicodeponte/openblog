"""
Pydantic models for structured refresh workflow output.
Forces Gemini to output strict JSON, preventing hallucinations.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class RefreshedSection(BaseModel):
    """
    A single refreshed content section.
    """
    heading: str = Field(
        ...,
        description="Section heading (e.g., 'Introduction', 'Key Benefits')",
        min_length=1,
        max_length=200
    )
    
    content: str = Field(
        ...,
        description="Updated section content in HTML format",
        min_length=10
    )
    
    change_summary: Optional[str] = Field(
        None,
        description="Brief summary of changes made to this section",
        max_length=500
    )
    
    @field_validator('heading')
    @classmethod
    def validate_heading(cls, v: str) -> str:
        """Ensure heading is clean and non-empty."""
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Heading cannot be empty or whitespace only")
        return cleaned
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Ensure content is substantial."""
        cleaned = v.strip()
        if len(cleaned) < 10:
            raise ValueError("Content must be at least 10 characters")
        return cleaned


class RefreshResponse(BaseModel):
    """
    Complete structured response for content refresh operation.
    """
    sections: List[RefreshedSection] = Field(
        ...,
        description="List of refreshed content sections",
        min_length=1
    )
    
    meta_description: Optional[str] = Field(
        None,
        description="Updated meta description (if requested)",
        max_length=160
    )
    
    changes_made: str = Field(
        ...,
        description="Overall summary of all changes made",
        min_length=10,
        max_length=1000
    )
    
    @field_validator('sections')
    @classmethod
    def validate_sections(cls, v: List[RefreshedSection]) -> List[RefreshedSection]:
        """Ensure at least one section is provided."""
        if not v:
            raise ValueError("At least one section must be provided")
        return v
    
    @field_validator('meta_description')
    @classmethod
    def validate_meta_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate meta description length if provided."""
        if v is not None:
            cleaned = v.strip()
            if len(cleaned) > 160:
                raise ValueError("Meta description must not exceed 160 characters")
            return cleaned if cleaned else None
        return v
