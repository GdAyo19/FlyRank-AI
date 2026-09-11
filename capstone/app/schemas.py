"""
Pydantic schemas for request/response validation.
These schemas define the contract for API endpoints.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from enum import Enum


class ClassificationResult(BaseModel):
    """Validated output from the vision model classification."""
    subject: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., min_length=1, max_length=100)
    attributes: list[str] = Field(default_factory=list)
    caption: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Ensure confidence is within valid range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return round(v, 4)


class ImageResponse(BaseModel):
    """Response schema for image data."""
    id: int
    filename: str
    filepath: str
    subject: Optional[str] = None
    category: Optional[str] = None
    attributes: Optional[list[str]] = None
    caption: Optional[str] = None
    confidence: Optional[float] = None
    is_flagged: bool = False
    processed: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class PostCreate(BaseModel):
    """Schema for creating a new post."""
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    category: Optional[str] = None


class PostResponse(BaseModel):
    """Response schema for post data."""
    id: int
    title: str
    content: str
    category: Optional[str] = None
    processed: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class SuggestionResponse(BaseModel):
    """Response schema for image suggestions."""
    id: int
    post_id: int
    image_id: int
    similarity_score: float
    guard_passed: bool
    guard_explanation: Optional[str] = None
    status: str
    image: Optional[ImageResponse] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewAction(BaseModel):
    """Schema for approving/rejecting a suggestion."""
    action: str = Field(..., pattern="^(approve|reject)$")
    notes: Optional[str] = None


class GuardResult(BaseModel):
    """Result from the mismatch guard."""
    passed: bool
    explanation: str
    similarity_score: float
    category_match: bool
    confidence_acceptable: bool


class ProcessingJobResponse(BaseModel):
    """Response schema for processing jobs."""
    id: int
    image_id: int
    status: str
    attempts: int
    error_message: Optional[str] = None
    vision_cost: float
    embedding_cost: float
    created_at: datetime

    class Config:
        from_attributes = True


class EvalResult(BaseModel):
    """Single evaluation result for precision measurement."""
    post_id: int
    expected_image_id: int
    suggested_image_id: Optional[int] = None
    is_correct: bool
    guard_passed: bool


class EvalSummary(BaseModel):
    """Summary of evaluation results."""
    total_posts: int
    top_1_precision: float
    guard_pass_rate: float
    results: list[EvalResult]
