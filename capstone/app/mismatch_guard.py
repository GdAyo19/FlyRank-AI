"""
Mismatch guard - the safety layer that decides if a recommendation is good enough.
Combines tag validation, semantic similarity thresholds, and confidence scores.
"""

import os
from typing import Optional
from app.schemas import ClassificationResult, GuardResult


class MismatchGuard:
    """
    Production safety layer that rejects incorrect recommendations.
    Combines multiple signals to make a decision.
    """

    # Categories that are semantically incompatible
    CATEGORY_CONFLICTS = {
        "animal": ["vehicle", "building", "object", "person"],
        "person": ["animal", "vehicle", "building", "object"],
        "vehicle": ["animal", "person", "building", "object"],
        "building": ["animal", "person", "vehicle"],
        "object": ["animal", "person", "vehicle"],
        "landscape": ["person", "vehicle"],
        "other": []
    }

    def __init__(
        self,
        similarity_threshold: float = 0.75,
        low_confidence_threshold: float = 0.6,
        category_weight: float = 0.4,
        similarity_weight: float = 0.4,
        confidence_weight: float = 0.2
    ):
        self.similarity_threshold = similarity_threshold
        self.low_confidence_threshold = low_confidence_threshold
        self.category_weight = category_weight
        self.similarity_weight = similarity_weight
        self.confidence_weight = confidence_weight

    def evaluate(
        self,
        post_category: Optional[str],
        image_classification: ClassificationResult,
        similarity_score: float
    ) -> GuardResult:
        """
        Evaluate whether an image-post pairing should pass the guard.

        Returns:
            GuardResult with pass/fail and detailed explanation
        """
        reasons = []

        # Check 1: Category mismatch (hard fail)
        category_match = self._check_category_match(post_category, image_classification.category)
        if not category_match:
            reasons.append(
                f"Category mismatch: post expects '{post_category}', "
                f"image has '{image_classification.category}'"
            )

        # Check 2: Similarity threshold (hard fail)
        similarity_acceptable = similarity_score >= self.similarity_threshold
        if not similarity_acceptable:
            reasons.append(
                f"Similarity score {similarity_score:.3f} below threshold "
                f"{self.similarity_threshold}"
            )

        # Check 3: Confidence check (soft fail - flag instead of reject)
        confidence_acceptable = image_classification.confidence >= self.low_confidence_threshold
        if not confidence_acceptable:
            reasons.append(
                f"Low confidence: {image_classification.confidence:.3f} "
                f"(threshold: {self.low_confidence_threshold})"
            )

        # Determine overall pass/fail
        # Hard fails: category mismatch OR low similarity
        # Soft fail: low confidence (flagged but might still pass)
        hard_fail = not category_match or not similarity_acceptable
        soft_fail = not confidence_acceptable

        passed = not hard_fail and not soft_fail
        if hard_fail:
            explanation = "REJECTED: " + "; ".join(reasons)
        elif soft_fail:
            explanation = "FLAGGED: " + "; ".join(reasons)
        else:
            explanation = (
                f"PASSED: category={image_classification.category}, "
                f"similarity={similarity_score:.3f}, "
                f"confidence={image_classification.confidence:.3f}"
            )

        return GuardResult(
            passed=passed,
            explanation=explanation,
            similarity_score=similarity_score,
            category_match=category_match,
            confidence_acceptable=confidence_acceptable
        )

    def _check_category_match(
        self,
        post_category: Optional[str],
        image_category: Optional[str]
    ) -> bool:
        """
        Check if categories are compatible.
        Returns False if they're in conflict.
        """
        if post_category is None or image_category is None:
            return True  # Can't check, so pass

        post_cat = post_category.lower().strip()
        img_cat = image_category.lower().strip()

        if post_cat == img_cat:
            return True

        # Check for conflicts
        conflicts = self.CATEGORY_CONFLICTS.get(post_cat, [])
        if img_cat in conflicts:
            return False

        return True


# Singleton instance with defaults from environment
_guard: Optional[MismatchGuard] = None


def get_mismatch_guard() -> MismatchGuard:
    """Get or create the mismatch guard singleton."""
    global _guard
    if _guard is None:
        similarity_threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.75"))
        low_confidence_threshold = float(os.getenv("LOW_CONFIDENCE_THRESHOLD", "0.6"))
        _guard = MismatchGuard(
            similarity_threshold=similarity_threshold,
            low_confidence_threshold=low_confidence_threshold
        )
    return _guard
