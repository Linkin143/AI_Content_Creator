"""SQLModel table definitions for the AEVRIX Content Intelligence Engine.

Covers the full persistent schema described in the specification. OAuth
tokens are stored encrypted (see app.security.encryption) - never plaintext.
Timestamps are stored in UTC.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import JSON as SA_JSON
from sqlalchemy import Column, Index
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class VerificationStatus(StrEnum):
    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    CONTRADICTED = "CONTRADICTED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"


class DraftStatus(StrEnum):
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    NEEDS_REVISION = "NEEDS_REVISION"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SCHEDULED = "SCHEDULED"
    PUBLISHING = "PUBLISHING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Platform(StrEnum):
    X = "x"
    LINKEDIN = "linkedin"


# ---------------------------------------------------------------------------
# Core tables
# ---------------------------------------------------------------------------
class User(SQLModel, table=True):
    __tablename__ = "users"
    id: int | None = Field(default=None, primary_key=True)
    telegram_user_id: int | None = Field(default=None, index=True)
    display_name: str = ""
    is_owner: bool = False
    created_at: datetime = Field(default_factory=utcnow)


class BrandProfile(SQLModel, table=True):
    __tablename__ = "brand_profiles"
    id: int | None = Field(default=None, primary_key=True)
    name: str = "Prince Kumar"
    biography: str = ""
    technical_expertise: list = Field(default_factory=list, sa_column=Column(SA_JSON))
    preferred_subjects: list = Field(default_factory=list, sa_column=Column(SA_JSON))
    writing_preferences: str = ""
    approved_viewpoints: list = Field(default_factory=list, sa_column=Column(SA_JSON))
    real_projects: list = Field(default_factory=list, sa_column=Column(SA_JSON))
    verified_achievements: list = Field(default_factory=list, sa_column=Column(SA_JSON))
    audience_interests: list = Field(default_factory=list, sa_column=Column(SA_JSON))
    restricted_topics: list = Field(default_factory=list, sa_column=Column(SA_JSON))
    project_notes: list = Field(default_factory=list, sa_column=Column(SA_JSON))
    updated_at: datetime = Field(default_factory=utcnow)


class Source(SQLModel, table=True):
    __tablename__ = "sources"
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    url: str
    category: str = "global_ai"
    region: str = "global"
    source_type: str = "rss"  # rss | api | arxiv | github | html
    priority: int = 5
    active: bool = True
    fetch_interval_hours: int = 24
    last_fetched: datetime | None = None
    last_error: str | None = None
    reliability_tier: int = 2  # 1 = primary/official, 2 = reputable, 3 = aggregator


class Article(SQLModel, table=True):
    __tablename__ = "articles"
    __table_args__ = (Index("ix_articles_canonical", "canonical_url"),)
    id: int | None = Field(default=None, primary_key=True)
    source_id: int | None = Field(default=None, foreign_key="sources.id", index=True)
    title: str = ""
    publisher: str = ""
    url: str = ""
    canonical_url: str = Field(default="", index=True)
    summary: str = ""
    content_snippet: str = ""
    published_at: datetime | None = Field(default=None, index=True)
    fetched_at: datetime = Field(default_factory=utcnow)
    category: str = ""
    region: str = ""
    content_fingerprint: str = Field(default="", index=True)
    cluster_id: int | None = Field(default=None, foreign_key="story_clusters.id")


class StoryCluster(SQLModel, table=True):
    __tablename__ = "story_clusters"
    id: int | None = Field(default=None, primary_key=True)
    title: str = ""
    representative_article_id: int | None = None
    article_ids: list = Field(default_factory=list, sa_column=Column(SA_JSON))
    created_at: datetime = Field(default_factory=utcnow)


class VerificationResult(SQLModel, table=True):
    __tablename__ = "verification_results"
    id: int | None = Field(default=None, primary_key=True)
    article_id: int | None = Field(default=None, foreign_key="articles.id", index=True)
    status: VerificationStatus = VerificationStatus.REQUIRES_REVIEW
    claims: list = Field(default_factory=list, sa_column=Column(SA_JSON))
    supporting_sources: list = Field(default_factory=list, sa_column=Column(SA_JSON))
    contradicting_sources: list = Field(default_factory=list, sa_column=Column(SA_JSON))
    confidence: float = 0.0
    editorial_notes: str = ""
    created_at: datetime = Field(default_factory=utcnow)


class ResearchRun(SQLModel, table=True):
    __tablename__ = "research_runs"
    id: int | None = Field(default=None, primary_key=True)
    run_id: str = Field(index=True)
    started_at: datetime = Field(default_factory=utcnow)
    finished_at: datetime | None = None
    window_hours: int = 24
    articles_found: int = 0
    stories_verified: int = 0
    drafts_generated: int = 0
    status: str = "running"
    errors: list = Field(default_factory=list, sa_column=Column(SA_JSON))


class RankedStory(SQLModel, table=True):
    __tablename__ = "ranked_stories"
    id: int | None = Field(default=None, primary_key=True)
    run_id: str = Field(index=True)
    article_id: int | None = Field(default=None, foreign_key="articles.id")
    score: float = 0.0
    technical_relevance: float = 0.0
    engineering_significance: float = 0.0
    freshness: float = 0.0
    audience_relevance: float = 0.0
    insight_opportunity: float = 0.0
    rationale: str = ""
    created_at: datetime = Field(default_factory=utcnow)


class Draft(SQLModel, table=True):
    __tablename__ = "drafts"
    id: int | None = Field(default=None, primary_key=True)
    run_id: str = Field(default="", index=True)
    article_id: int | None = Field(default=None, foreign_key="articles.id")
    platform: Platform = Platform.X
    status: DraftStatus = Field(default=DraftStatus.PENDING_REVIEW, index=True)
    current_version: int = 1
    content: str = ""
    sources: list = Field(default_factory=list, sa_column=Column(SA_JSON))
    evidence: list = Field(default_factory=list, sa_column=Column(SA_JSON))
    quality_score: float = 0.0
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class DraftVersion(SQLModel, table=True):
    __tablename__ = "draft_versions"
    id: int | None = Field(default=None, primary_key=True)
    draft_id: int = Field(foreign_key="drafts.id", index=True)
    version: int = 1
    content: str = ""
    change_reason: str = ""
    created_at: datetime = Field(default_factory=utcnow)


class Approval(SQLModel, table=True):
    __tablename__ = "approvals"
    id: int | None = Field(default=None, primary_key=True)
    draft_id: int = Field(foreign_key="drafts.id", index=True)
    version: int = 1
    decision: str = ""  # approved | rejected | rewrite_requested
    decided_by: int | None = None  # telegram user id
    feedback: str = ""
    created_at: datetime = Field(default_factory=utcnow)


class Schedule(SQLModel, table=True):
    __tablename__ = "schedules"
    id: int | None = Field(default=None, primary_key=True)
    draft_id: int = Field(foreign_key="drafts.id", index=True)
    version: int = 1
    scheduled_for: datetime = Field(index=True)
    status: str = "pending"  # pending | done | cancelled | failed
    created_at: datetime = Field(default_factory=utcnow)


class PublishedPost(SQLModel, table=True):
    __tablename__ = "published_posts"
    id: int | None = Field(default=None, primary_key=True)
    draft_id: int = Field(foreign_key="drafts.id", index=True)
    version: int = 1
    platform: Platform = Platform.X
    platform_post_id: str = ""
    url: str = ""
    manual: bool = False
    status: str = "published"  # published | failed | manual
    platform_response: dict = Field(default_factory=dict, sa_column=Column(SA_JSON))
    published_at: datetime = Field(default_factory=utcnow)


class SocialConnection(SQLModel, table=True):
    __tablename__ = "social_connections"
    id: int | None = Field(default=None, primary_key=True)
    platform: Platform = Field(index=True)
    account_name: str = ""
    account_id: str = ""
    access_token_enc: str = ""  # encrypted
    refresh_token_enc: str = ""  # encrypted
    expires_at: datetime | None = None
    scopes: str = ""
    connected_at: datetime = Field(default_factory=utcnow)
    active: bool = True


class EngagementMetric(SQLModel, table=True):
    __tablename__ = "engagement_metrics"
    id: int | None = Field(default=None, primary_key=True)
    published_post_id: int = Field(foreign_key="published_posts.id", index=True)
    likes: int = 0
    comments: int = 0
    shares: int = 0
    impressions: int = 0
    collected_at: datetime = Field(default_factory=utcnow)


class AgentRun(SQLModel, table=True):
    __tablename__ = "agent_runs"
    id: int | None = Field(default=None, primary_key=True)
    run_id: str = Field(index=True)
    node: str = ""
    status: str = ""
    detail: str = ""
    llm_calls: int = 0
    created_at: datetime = Field(default_factory=utcnow)


class SystemSetting(SQLModel, table=True):
    __tablename__ = "system_settings"
    id: int | None = Field(default=None, primary_key=True)
    key: str = Field(index=True, unique=True)
    value: str = ""
    updated_at: datetime = Field(default_factory=utcnow)


class AuditEvent(SQLModel, table=True):
    __tablename__ = "audit_events"
    id: int | None = Field(default=None, primary_key=True)
    actor: str = ""
    action: str = Field(index=True)
    entity_type: str = ""
    entity_id: str = ""
    detail: dict = Field(default_factory=dict, sa_column=Column(SA_JSON))
    created_at: datetime = Field(default_factory=utcnow)


ALL_MODELS = [
    User, BrandProfile, Source, Article, StoryCluster, VerificationResult,
    ResearchRun, RankedStory, Draft, DraftVersion, Approval, Schedule,
    PublishedPost, SocialConnection, EngagementMetric, AgentRun,
    SystemSetting, AuditEvent,
]
