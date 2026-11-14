"""Pydantic v2 schemas used for structured LLM outputs and API responses.

Every model response is validated against these schemas; invalid output triggers
bounded retries and, failing that, marks the story for manual review rather than
accepting malformed content.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExtractedClaims(BaseModel):
    """Structured output from the article-research / verification step."""
    summary: str = Field(default="", description="Neutral 1-2 sentence summary")
    key_claims: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)


class VerificationOutput(BaseModel):
    status: str = Field(
        default="REQUIRES_REVIEW",
        description="VERIFIED|PARTIALLY_VERIFIED|UNVERIFIED|CONTRADICTED|REQUIRES_REVIEW",
    )
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    supporting_sources: list[str] = Field(default_factory=list)
    contradicting_sources: list[str] = Field(default_factory=list)
    editorial_notes: str = ""


class TechnicalAnalysis(BaseModel):
    technical_depth: str = ""
    developer_implications: list[str] = Field(default_factory=list)
    business_implications: list[str] = Field(default_factory=list)


class XPostOutput(BaseModel):
    content: str = Field(description="The X post text, within platform length")
    evidence: list[str] = Field(default_factory=list, description="Facts + source URLs used")


class LinkedInPostOutput(BaseModel):
    content: str = Field(description="LinkedIn post, natural paragraphs")
    evidence: list[str] = Field(default_factory=list)


class QualityReview(BaseModel):
    approved: bool = Field(default=False)
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
