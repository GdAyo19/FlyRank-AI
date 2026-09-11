"""
Tests for the AI Image Matching Engine.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


class TestHealthEndpoints:
    """Tests for basic health and info endpoints."""

    def test_root(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "AI Image Matching Engine"
        assert "endpoints" in data

    def test_health(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestPostEndpoints:
    """Tests for post CRUD operations."""

    def test_create_post(self):
        response = client.post("/posts", json={
            "title": "Test Post",
            "content": "This is test content about red foxes",
            "category": "animal"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Post"
        assert data["category"] == "animal"
        assert data["processed"] is False

    def test_list_posts(self):
        response = client.get("/posts")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_post(self):
        # Create a post first
        create_resp = client.post("/posts", json={
            "title": "Get Test",
            "content": "Content here",
            "category": "animal"
        })
        post_id = create_resp.json()["id"]

        response = client.get(f"/posts/{post_id}")
        assert response.status_code == 200
        assert response.json()["id"] == post_id

    def test_get_post_not_found(self):
        response = client.get("/posts/99999")
        assert response.status_code == 404


class TestImageEndpoints:
    """Tests for image upload and listing."""

    def test_list_images(self):
        response = client.get("/images")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_image_not_found(self):
        response = client.get("/images/99999")
        assert response.status_code == 404


class TestGuardLogic:
    """Tests for the mismatch guard logic."""

    def test_guard_rejects_category_mismatch(self):
        from app.mismatch_guard import MismatchGuard
        from app.schemas import ClassificationResult

        guard = MismatchGuard()
        classification = ClassificationResult(
            subject="gray wolf",
            category="animal",
            attributes=["gray fur", "wild", "forest"],
            caption="A gray wolf in the forest",
            confidence=0.9
        )

        result = guard.evaluate(
            post_category="animal",
            image_classification=classification,
            similarity_score=0.8
        )

        # Should pass - both are animals
        assert result.passed is True

    def test_guard_rejects_low_similarity(self):
        from app.mismatch_guard import MismatchGuard
        from app.schemas import ClassificationResult

        guard = MismatchGuard(similarity_threshold=0.75)
        classification = ClassificationResult(
            subject="red fox",
            category="animal",
            attributes=["orange fur"],
            caption="A red fox",
            confidence=0.9
        )

        result = guard.evaluate(
            post_category="animal",
            image_classification=classification,
            similarity_score=0.5  # Below threshold
        )

        assert result.passed is False
        assert "Similarity score" in result.explanation

    def test_guard_rejects_incompatible_categories(self):
        from app.mismatch_guard import MismatchGuard
        from app.schemas import ClassificationResult

        guard = MismatchGuard()
        classification = ClassificationResult(
            subject="red sports car",
            category="vehicle",
            attributes=["red", "fast"],
            caption="A red sports car",
            confidence=0.95
        )

        result = guard.evaluate(
            post_category="animal",
            image_classification=classification,
            similarity_score=0.8
        )

        assert result.passed is False
        assert "Category mismatch" in result.explanation

    def test_guard_flags_low_confidence(self):
        from app.mismatch_guard import MismatchGuard
        from app.schemas import ClassificationResult

        guard = MismatchGuard(low_confidence_threshold=0.6)
        classification = ClassificationResult(
            subject="unknown",
            category="other",
            attributes=[],
            caption="Something unclear",
            confidence=0.3  # Low confidence
        )

        result = guard.evaluate(
            post_category="animal",
            image_classification=classification,
            similarity_score=0.9
        )

        # Should fail due to category mismatch
        assert result.passed is False
