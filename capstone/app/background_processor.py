"""
Background processor for batch image processing.
Handles async jobs with retries, progress tracking, and cost tracking.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Image, ProcessingJob, async_session
from app.vision_service import get_vision_service
from app.embedding_service import get_embedding_service
from app.schemas import ClassificationResult

logger = logging.getLogger(__name__)


class BackgroundProcessor:
    """
    Processes images in background jobs with retries and cost tracking.
    Never blocks API requests.
    """

    def __init__(self):
        self.active_jobs: dict[int, asyncio.Task] = {}

    async def process_image(self, image_id: int) -> bool:
        """
        Process a single image through vision and embedding pipeline.
        Creates a ProcessingJob entry and tracks all costs.

        Returns:
            True if successful, False otherwise
        """
        vision_service = get_vision_service()
        embedding_service = get_embedding_service()

        async with async_session() as db:
            # Get the image
            result = await db.execute(select(Image).where(Image.id == image_id))
            image = result.scalar_one_or_none()

            if image is None:
                logger.error(f"Image {image_id} not found")
                return False

            if image.processed:
                logger.info(f"Image {image_id} already processed, skipping")
                return True

            # Create or get processing job
            job_result = await db.execute(
                select(ProcessingJob)
                .where(ProcessingJob.image_id == image_id)
                .where(ProcessingJob.status.in_(["queued", "processing"]))
            )
            job = job_result.scalar_one_or_none()

            if job is None:
                job = ProcessingJob(image_id=image_id, status="queued")
                db.add(job)
                await db.commit()

            # Update job status
            job.status = "processing"
            job.attempts += 1
            job.started_at = datetime.utcnow()
            await db.commit()

            try:
                # Step 1: Classify image with vision model
                classification, vision_cost = await vision_service.classify_image(
                    image.filepath
                )
                job.vision_cost = vision_cost

                # Step 2: Update image metadata
                image.subject = classification.subject
                image.category = classification.category
                image.attributes = classification.attributes
                image.caption = classification.caption
                image.confidence = classification.confidence
                image.is_flagged = classification.confidence < 0.6

                # Step 3: Generate embedding for the caption
                embedding, embedding_cost = await embedding_service.get_embedding(
                    classification.caption
                )
                job.embedding_cost = embedding_cost

                # Step 4: Store the embedding
                from app.models import ImageEmbedding
                image_embedding = ImageEmbedding(
                    image_id=image_id,
                    embedding=embedding,
                    model_name=embedding_service.EMBEDDING_MODEL
                )
                db.add(image_embedding)

                # Mark as processed
                image.processed = True
                job.status = "completed"
                job.completed_at = datetime.utcnow()

                await db.commit()
                logger.info(
                    f"Image {image_id} processed successfully. "
                    f"Vision cost: ${vision_cost:.4f}, "
                    f"Embedding cost: ${embedding_cost:.4f}"
                )
                return True

            except Exception as e:
                job.status = "failed" if job.attempts >= job.max_retries else "queued"
                job.error_message = str(e)
                await db.commit()
                logger.error(f"Failed to process image {image_id}: {e}")

                # Retry if we haven't exceeded max attempts
                if job.attempts < job.max_retries:
                    await asyncio.sleep(2 ** job.attempts)  # Exponential backoff
                    return await self.process_image(image_id)

                return False

    async def process_batch(self, image_ids: list[int], batch_size: int = 5) -> dict:
        """
        Process multiple images as a batch job.
        Processes in chunks to control concurrency and costs.

        Returns:
            Summary dict with success/failure counts and total costs
        """
        results = {"success": 0, "failed": 0, "total_vision_cost": 0.0, "total_embedding_cost": 0.0}

        for i in range(0, len(image_ids), batch_size):
            batch = image_ids[i:i + batch_size]

            # Process batch concurrently
            tasks = [self.process_image(img_id) for img_id in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, Exception):
                    results["failed"] += 1
                    logger.error(f"Batch processing error: {result}")
                elif result:
                    results["success"] += 1
                else:
                    results["failed"] += 1

            # Small delay between batches to respect rate limits
            if i + batch_size < len(image_ids):
                await asyncio.sleep(1)

        # Get total costs from database
        async with async_session() as db:
            result = await db.execute(
                select(
                    func.sum(ProcessingJob.vision_cost),
                    func.sum(ProcessingJob.embedding_cost)
                ).where(ProcessingJob.image_id.in_(image_ids))
            )
            row = result.one_or_none()
            if row:
                results["total_vision_cost"] = row[0] or 0.0
                results["total_embedding_cost"] = row[1] or 0.0

        return results

    async def process_post_embeddings(self, post_ids: list[int]) -> dict:
        """
        Generate embeddings for posts in batch.
        """
        embedding_service = get_embedding_service()
        results = {"success": 0, "failed": 0, "total_cost": 0.0}

        async with async_session() as db:
            from app.models import Post, PostEmbedding

            for post_id in post_ids:
                try:
                    result = await db.execute(select(Post).where(Post.id == post_id))
                    post = result.scalar_one_or_none()

                    if post is None or post.processed:
                        continue

                    # Generate embedding from title + content
                    text = f"{post.title}\n\n{post.content}"
                    embedding, cost = await embedding_service.get_embedding(text)

                    # Store embedding
                    post_embedding = PostEmbedding(
                        post_id=post_id,
                        embedding=embedding,
                        model_name=embedding_service.EMBEDDING_MODEL
                    )
                    db.add(post_embedding)

                    post.processed = True
                    results["success"] += 1
                    results["total_cost"] += cost

                except Exception as e:
                    results["failed"] += 1
                    logger.error(f"Failed to process post {post_id}: {e}")

            await db.commit()

        return results


# Add missing import
from sqlalchemy import func

# Singleton instance
processor = BackgroundProcessor()


def get_processor() -> BackgroundProcessor:
    """Get the background processor singleton."""
    return processor
