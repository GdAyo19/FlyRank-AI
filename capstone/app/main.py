"""
Main FastAPI application for the AI Image Matching Engine.
Defines all API endpoints and application lifecycle.
"""

import os
import logging
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    init_db, get_db, Image, Post, ImageEmbedding,
    PostEmbedding, Suggestion, ProcessingJob
)
from app.schemas import (
    ImageResponse, PostCreate, PostResponse,
    SuggestionResponse, ReviewAction, EvalSummary, EvalResult,
    ProcessingJobResponse
)
from app.vision_service import get_vision_service
from app.embedding_service import get_embedding_service
from app.mismatch_guard import get_mismatch_guard
from app.background_processor import get_processor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Image storage directory
IMAGES_DIR = Path("images")
IMAGES_DIR.mkdir(exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - initialize DB on startup."""
    await init_db()
    logger.info("Database initialized")
    yield


app = FastAPI(
    title="AI Image Matching Engine",
    description="Matches blog posts with relevant images using semantic understanding and safety guards.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health & info endpoints
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    """Service root - basic info."""
    return {
        "name": "AI Image Matching Engine",
        "version": "1.0.0",
        "endpoints": {
            "images": "/images",
            "posts": "/posts",
            "suggestions": "/posts/{id}/images",
            "review": "/suggestions/{id}/review",
            "jobs": "/jobs"
        }
    }


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Image endpoints
# ---------------------------------------------------------------------------

@app.post("/images", response_model=ImageResponse, status_code=201)
async def upload_image(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload an image for processing.
    The image will be classified in the background.
    """
    # Validate file type
    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(400, f"Invalid file type. Allowed: {allowed_types}")

    # Save image to disk
    file_path = IMAGES_DIR / file.filename
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Create image record
    image = Image(
        filename=file.filename,
        filepath=str(file_path),
        processed=False
    )
    db.add(image)
    await db.commit()
    await db.refresh(image)

    # Queue background processing
    background_tasks.add_task(
        get_processor().process_image,
        image.id
    )

    return image


@app.get("/images", response_model=list[ImageResponse])
async def list_images(
    category: Optional[str] = None,
    processed: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """List all images with optional filters."""
    query = select(Image)

    if category:
        query = query.where(Image.category == category)
    if processed is not None:
        query = query.where(Image.processed == processed)

    query = query.order_by(Image.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@app.get("/images/{image_id}", response_model=ImageResponse)
async def get_image(image_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single image by ID."""
    result = await db.execute(select(Image).where(Image.id == image_id))
    image = result.scalar_one_or_none()
    if not image:
        raise HTTPException(404, "Image not found")
    return image


@app.get("/images/{image_id}/embedding")
async def get_image_embedding(image_id: int, db: AsyncSession = Depends(get_db)):
    """Get the embedding vector for an image."""
    result = await db.execute(
        select(ImageEmbedding).where(ImageEmbedding.image_id == image_id)
    )
    embedding = result.scalar_one_or_none()
    if not embedding:
        raise HTTPException(404, "Embedding not found")
    return {
        "image_id": image_id,
        "embedding": embedding.embedding,
        "model": embedding.model_name
    }


# ---------------------------------------------------------------------------
# Post endpoints
# ---------------------------------------------------------------------------

@app.post("/posts", response_model=PostResponse, status_code=201)
async def create_post(
    post_data: PostCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Create a new post and queue it for embedding generation."""
    post = Post(
        title=post_data.title,
        content=post_data.content,
        category=post_data.category,
        processed=False
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)

    # Queue embedding generation in background
    background_tasks.add_task(
        _process_post_embedding,
        post.id
    )

    return post


async def _process_post_embedding(post_id: int):
    """Helper to process a single post embedding."""
    processor = get_processor()
    await processor.process_post_embeddings([post_id])


@app.get("/posts", response_model=list[PostResponse])
async def list_posts(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List all posts with optional category filter."""
    query = select(Post)
    if category:
        query = query.where(Post.category == category)
    query = query.order_by(Post.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@app.get("/posts/{post_id}", response_model=PostResponse)
async def get_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single post by ID."""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(404, "Post not found")
    return post


# ---------------------------------------------------------------------------
# Matching & suggestion endpoints
# ---------------------------------------------------------------------------

@app.get("/posts/{post_id}/images", response_model=list[SuggestionResponse])
async def get_image_suggestions(
    post_id: int,
    limit: int = 5,
    db: AsyncSession = Depends(get_db)
):
    """
    Get ranked image suggestions for a post.
    Applies the mismatch guard to filter out bad matches.
    """
    # Get the post
    post_result = await db.execute(select(Post).where(Post.id == post_id))
    post = post_result.scalar_one_or_none()
    if not post:
        raise HTTPException(404, "Post not found")

    # Get post embedding
    post_emb_result = await db.execute(
        select(PostEmbedding).where(PostEmbedding.post_id == post_id)
    )
    post_embedding_record = post_emb_result.scalar_one_or_none()
    if not post_embedding_record:
        raise HTTPException(400, "Post not yet processed. Try again shortly.")

    post_embedding = post_embedding_record.embedding

    # Get all processed image embeddings
    img_emb_result = await db.execute(
        select(ImageEmbedding.image_id, ImageEmbedding.embedding)
        .join(Image, Image.id == ImageEmbedding.image_id)
        .where(Image.processed == True)
    )
    image_embeddings = img_emb_result.all()

    if not image_embeddings:
        return []

    # Rank by similarity
    embedding_service = get_embedding_service()
    ranked = embedding_service.rank_by_similarity(post_embedding, image_embeddings)

    # Apply mismatch guard to top candidates
    guard = get_mismatch_guard()
    suggestions = []

    for image_id, similarity_score in ranked[:limit * 2]:  # Check more than needed
        # Get image metadata
        img_result = await db.execute(select(Image).where(Image.id == image_id))
        image = img_result.scalar_one_or_none()
        if not image or not image.subject:
            continue

        # Build classification result from stored metadata
        from app.schemas import ClassificationResult
        classification = ClassificationResult(
            subject=image.subject,
            category=image.category or "other",
            attributes=image.attributes or [],
            caption=image.caption or "",
            confidence=image.confidence or 0.0
        )

        # Run guard check
        guard_result = guard.evaluate(
            post_category=post.category,
            image_classification=classification,
            similarity_score=similarity_score
        )

        # Create or update suggestion
        existing = await db.execute(
            select(Suggestion)
            .where(and_(
                Suggestion.post_id == post_id,
                Suggestion.image_id == image_id
            ))
        )
        suggestion = existing.scalar_one_or_none()

        if suggestion:
            suggestion.similarity_score = similarity_score
            suggestion.guard_passed = guard_result.passed
            suggestion.guard_explanation = guard_result.explanation
        else:
            suggestion = Suggestion(
                post_id=post_id,
                image_id=image_id,
                similarity_score=similarity_score,
                guard_passed=guard_result.passed,
                guard_explanation=guard_result.explanation,
                status="pending"
            )
            db.add(suggestion)

        suggestions.append(suggestion)

        # Stop if we have enough passing suggestions
        if len([s for s in suggestions if s.guard_passed]) >= limit:
            break

    await db.commit()

    # Refresh suggestions with image data
    result_suggestions = []
    for s in suggestions[:limit]:
        await db.refresh(s)
        # Load image relationship
        img_res = await db.execute(select(Image).where(Image.id == s.image_id))
        img = img_res.scalar_one_or_none()
        s.image = img
        result_suggestions.append(s)

    return result_suggestions


@app.get("/posts/{post_id}/no-match")
async def check_no_match(post_id: int, db: AsyncSession = Depends(get_db)):
    """
    Check if no image passes the guard for a post.
    Returns the best candidate and why it was rejected.
    """
    post_result = await db.execute(select(Post).where(Post.id == post_id))
    post = post_result.scalar_one_or_none()
    if not post:
        raise HTTPException(404, "Post not found")

    post_emb_result = await db.execute(
        select(PostEmbedding).where(PostEmbedding.post_id == post_id)
    )
    post_embedding_record = post_emb_result.scalar_one_or_none()
    if not post_embedding_record:
        return {"has_match": False, "reason": "Post not yet processed"}

    # Get all suggestions for this post
    suggestions_result = await db.execute(
        select(Suggestion)
        .where(Suggestion.post_id == post_id)
        .order_by(Suggestion.similarity_score.desc())
        .limit(1)
    )
    top_suggestion = suggestions_result.scalar_one_or_none()

    if top_suggestion and top_suggestion.guard_passed:
        return {"has_match": True, "suggestion_id": top_suggestion.id}

    # No match - explain why
    if top_suggestion:
        return {
            "has_match": False,
            "reason": top_suggestion.guard_explanation,
            "best_score": top_suggestion.similarity_score
        }

    return {"has_match": False, "reason": "No candidates found"}


# ---------------------------------------------------------------------------
# Review endpoints
# ---------------------------------------------------------------------------

@app.get("/suggestions", response_model=list[SuggestionResponse])
async def list_suggestions(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List all suggestions with optional status filter."""
    query = select(Suggestion)
    if status:
        query = query.where(Suggestion.status == status)
    query = query.order_by(Suggestion.created_at.desc())
    result = await db.execute(query)
    suggestions = result.scalars().all()

    # Load image data for each suggestion
    for s in suggestions:
        img_res = await db.execute(select(Image).where(Image.id == s.image_id))
        s.image = img_res.scalar_one_or_none()

    return suggestions


@app.post("/suggestions/{suggestion_id}/review", response_model=SuggestionResponse)
async def review_suggestion(
    suggestion_id: int,
    review: ReviewAction,
    db: AsyncSession = Depends(get_db)
):
    """Approve or reject a suggestion."""
    result = await db.execute(
        select(Suggestion).where(Suggestion.id == suggestion_id)
    )
    suggestion = result.scalar_one_or_none()
    if not suggestion:
        raise HTTPException(404, "Suggestion not found")

    suggestion.status = review.action + "d"  # "approve" -> "approved"
    suggestion.reviewer_notes = review.notes
    from datetime import datetime
    suggestion.reviewed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(suggestion)

    # Load image
    img_res = await db.execute(select(Image).where(Image.id == suggestion.image_id))
    suggestion.image = img_res.scalar_one_or_none()

    return suggestion


# ---------------------------------------------------------------------------
# Background job endpoints
# ---------------------------------------------------------------------------

@app.post("/jobs/process-images")
async def queue_image_processing(
    background_tasks: BackgroundTasks,
    image_ids: Optional[list[int]] = None,
    db: AsyncSession = Depends(get_db)
):
    """Queue images for background processing."""
    if image_ids is None:
        # Process all unprocessed images
        result = await db.execute(
            select(Image.id).where(Image.processed == False)
        )
        image_ids = [row[0] for row in result.all()]

    if not image_ids:
        return {"message": "No images to process", "count": 0}

    background_tasks.add_task(
        get_processor().process_batch,
        image_ids
    )

    return {"message": f"Queued {len(image_ids)} images for processing", "count": len(image_ids)}


@app.post("/jobs/process-posts")
async def queue_post_processing(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Queue all unprocessed posts for embedding generation."""
    result = await db.execute(
        select(Post.id).where(Post.processed == False)
    )
    post_ids = [row[0] for row in result.all()]

    if not post_ids:
        return {"message": "No posts to process", "count": 0}

    background_tasks.add_task(
        get_processor().process_post_embeddings,
        post_ids
    )

    return {"message": f"Queued {len(post_ids)} posts for processing", "count": len(post_ids)}


@app.get("/jobs", response_model=list[ProcessingJobResponse])
async def list_jobs(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List processing jobs with optional status filter."""
    query = select(ProcessingJob)
    if status:
        query = query.where(ProcessingJob.status == status)
    query = query.order_by(ProcessingJob.created_at.desc()).limit(100)
    result = await db.execute(query)
    return result.scalars().all()


@app.get("/jobs/costs")
async def get_processing_costs(db: AsyncSession = Depends(get_db)):
    """Get total processing costs."""
    result = await db.execute(
        select(
            func.sum(ProcessingJob.vision_cost),
            func.sum(ProcessingJob.embedding_cost),
            func.count(ProcessingJob.id)
        )
    )
    row = result.one_or_none()
    return {
        "total_vision_cost": row[0] or 0.0,
        "total_embedding_cost": row[1] or 0.0,
        "total_jobs": row[2] or 0
    }


# ---------------------------------------------------------------------------
# Evaluation endpoints
# ---------------------------------------------------------------------------

@app.get("/eval/precision", response_model=EvalSummary)
async def evaluate_precision(db: AsyncSession = Depends(get_db)):
    """
    Calculate top-1 precision against the evaluation dataset.
    Requires eval_data/eval_set.json to exist.
    """
    import json
    eval_path = Path("eval_data/eval_set.json")

    if not eval_path.exists():
        raise HTTPException(404, "Evaluation dataset not found at eval_data/eval_set.json")

    with open(eval_path) as f:
        eval_set = json.load(f)

    results = []
    correct = 0
    guard_passes = 0

    for item in eval_set:
        post_id = item["post_id"]
        expected_image_id = item["expected_image_id"]

        # Get the top suggestion for this post
        result = await db.execute(
            select(Suggestion)
            .where(Suggestion.post_id == post_id)
            .order_by(Suggestion.similarity_score.desc())
            .limit(1)
        )
        top_suggestion = result.scalar_one_or_none()

        suggested_id = top_suggestion.image_id if top_suggestion else None
        is_correct = suggested_id == expected_image_id
        guard_passed = top_suggestion.guard_passed if top_suggestion else False

        if is_correct:
            correct += 1
        if guard_passed:
            guard_passes += 1

        results.append(EvalResult(
            post_id=post_id,
            expected_image_id=expected_image_id,
            suggested_image_id=suggested_id,
            is_correct=is_correct,
            guard_passed=guard_passed
        ))

    total = len(eval_set)
    precision = correct / total if total > 0 else 0.0
    guard_rate = guard_passes / total if total > 0 else 0.0

    return EvalSummary(
        total_posts=total,
        top_1_precision=precision,
        guard_pass_rate=guard_rate,
        results=results
    )
