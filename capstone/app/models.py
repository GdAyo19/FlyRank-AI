"""
Database models for the AI Image Matching Engine.
Defines tables for images, posts, embeddings, suggestions, and reviews.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Text, Boolean,
    DateTime, ForeignKey, Index, JSON
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship
import os


class Base(DeclarativeBase):
    pass


class Image(Base):
    """Stores image metadata after vision model classification."""
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(512), nullable=False)
    subject = Column(String(255), nullable=True)
    category = Column(String(100), nullable=True)
    attributes = Column(JSON, nullable=True)
    caption = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    is_flagged = Column(Boolean, default=False)
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to embeddings
    embeddings = relationship("ImageEmbedding", back_populates="image", cascade="all, delete-orphan")


class ImageEmbedding(VectorMixin):
    """Stores vector embeddings for image captions."""
    __tablename__ = "image_embeddings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    image_id = Column(Integer, ForeignKey("images.id"), nullable=False)
    embedding = Column(JSON, nullable=False)  # Store as JSON array
    model_name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    image = relationship("Image", back_populates="embeddings")

    __table_args__ = (
        Index("idx_image_embeddings_image_id", "image_id"),
    )


class Post(Base):
    """Blog posts to match images against."""
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    embeddings = relationship("PostEmbedding", back_populates="post", cascade="all, delete-orphan")
    suggestions = relationship("Suggestion", back_populates="post", cascade="all, delete-orphan")


class PostEmbedding(Base):
    """Stores vector embeddings for post content."""
    __tablename__ = "post_embeddings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    embedding = Column(JSON, nullable=False)
    model_name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    post = relationship("Post", back_populates="embeddings")

    __table_args__ = (
        Index("idx_post_embeddings_post_id", "post_id"),
    )


class Suggestion(Base):
    """Pairs of images suggested for posts with guard results."""
    __tablename__ = "suggestions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    image_id = Column(Integer, ForeignKey("images.id"), nullable=False)
    similarity_score = Column(Float, nullable=False)
    guard_passed = Column(Boolean, nullable=False)
    guard_explanation = Column(Text, nullable=True)
    status = Column(String(50), default="pending")  # pending, approved, rejected
    reviewed_at = Column(DateTime, nullable=True)
    reviewer_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    post = relationship("Post", back_populates="suggestions")
    image = relationship("Image")

    __table_args__ = (
        Index("idx_suggestions_post_id", "post_id"),
        Index("idx_suggestions_status", "status"),
    )


class ProcessingJob(Base):
    """Tracks background processing jobs for images."""
    __tablename__ = "processing_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    image_id = Column(Integer, ForeignKey("images.id"), nullable=False)
    status = Column(String(50), default="queued")  # queued, processing, completed, failed
    attempts = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    error_message = Column(Text, nullable=True)
    vision_cost = Column(Float, default=0.0)
    embedding_cost = Column(Float, default=0.0)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class VectorMixin:
    """Mixin for tables that store vector embeddings."""
    pass


# Database engine and session factory
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./image_matching.db")
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """Create all tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """Dependency for getting database sessions."""
    async with async_session() as session:
        yield session
