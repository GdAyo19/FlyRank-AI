"""
Embedding service for generating vector embeddings using OpenAI's embedding model.
Creates embeddings for image captions and post content for semantic matching.
"""

import numpy as np
from typing import Optional
from openai import AsyncOpenAI


class EmbeddingService:
    """Handles embedding generation for semantic matching."""

    EMBEDDING_MODEL = "text-embedding-3-small"
    COST_PER_1K_TOKENS = 0.00002  # $0.02 per 1M tokens for text-embedding-3-small
    EMBEDDING_DIMENSIONS = 1536

    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def get_embedding(self, text: str) -> tuple[list[float], float]:
        """
        Generate embedding for a single text.

        Returns:
            Tuple of (embedding_vector, cost_in_usd)
        """
        response = await self.client.embeddings.create(
            model=self.EMBEDDING_MODEL,
            input=text,
            dimensions=self.EMBEDDING_DIMENSIONS
        )

        # Calculate cost
        tokens_used = response.usage.total_tokens
        cost = (tokens_used / 1000) * self.COST_PER_1K_TOKENS

        embedding = response.data[0].embedding
        return embedding, cost

    async def get_embeddings_batch(self, texts: list[str]) -> tuple[list[list[float]], float]:
        """
        Generate embeddings for multiple texts in one API call.
        More efficient than calling get_embedding repeatedly.

        Returns:
            Tuple of (list of embedding vectors, total_cost_in_usd)
        """
        if not texts:
            return [], 0.0

        # OpenAI batch limit is 2048 texts
        all_embeddings = []
        total_cost = 0.0

        for i in range(0, len(texts), 2048):
            batch = texts[i:i + 2048]
            response = await self.client.embeddings.create(
                model=self.EMBEDDING_MODEL,
                input=batch,
                dimensions=self.EMBEDDING_DIMENSIONS
            )

            # Calculate cost for this batch
            tokens_used = response.usage.total_tokens
            total_cost += (tokens_used / 1000) * self.COST_PER_1K_TOKENS

            # Extract embeddings in order
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)

        return all_embeddings, total_cost

    @staticmethod
    def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
        """
        Calculate cosine similarity between two vectors.
        Returns value between -1 and 1, where 1 means identical.
        """
        a = np.array(vec_a, dtype=np.float32)
        b = np.array(vec_b, dtype=np.float32)

        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(np.dot(a, b) / (norm_a * norm_b))

    @staticmethod
    def rank_by_similarity(
        query_embedding: list[float],
        candidate_embeddings: list[tuple[int, list[float]]]
    ) -> list[tuple[int, float]]:
        """
        Rank candidates by similarity to query.

        Args:
            query_embedding: The embedding vector to compare against
            candidate_embeddings: List of (image_id, embedding_vector) tuples

        Returns:
            List of (image_id, similarity_score) sorted by descending similarity
        """
        scores = []
        for image_id, candidate_emb in candidate_embeddings:
            score = EmbeddingService.cosine_similarity(query_embedding, candidate_emb)
            scores.append((image_id, score))

        # Sort by score descending
        return sorted(scores, key=lambda x: x[1], reverse=True)


embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the embedding service singleton."""
    global embedding_service
    if embedding_service is None:
        import os
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        embedding_service = EmbeddingService(api_key)
    return embedding_service
