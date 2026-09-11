"""
Vision service for image classification using OpenAI's vision model.
Processes images and returns structured metadata with cost tracking.
"""

import base64
import httpx
from pathlib import Path
from typing import Optional
from openai import AsyncOpenAI

from app.schemas import ClassificationResult


class VisionService:
    """Handles image classification using OpenAI's vision API."""

    VISION_MODEL = "gpt-4-vision-preview"
    COST_PER_1K_TOKENS = 0.03  # $0.03 per 1K tokens for gpt-4-vision-preview

    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def classify_image(self, image_path: str) -> tuple[ClassificationResult, float]:
        """
        Classify an image using the vision model.

        Returns:
            Tuple of (ClassificationResult, cost_in_usd)
        """
        image_data = self._encode_image(image_path)

        response = await self.client.chat.completions.create(
            model=self.VISION_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an image classifier. Analyze the image and return "
                        "structured JSON with: subject (main subject), category "
                        "(animal, landscape, object, person, vehicle, building, other), "
                        "attributes (list of visible characteristics), caption "
                        "(brief description), and confidence (0.0-1.0). "
                        "Return ONLY valid JSON, no markdown or explanations."
                    )
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}",
                                "detail": "high"
                            }
                        },
                        {
                            "type": "text",
                            "text": "Classify this image with structured metadata."
                        }
                    ]
                }
            ],
            max_tokens=300
        )

        # Calculate cost based on tokens used
        usage = response.usage
        total_tokens = usage.total_tokens if usage else 0
        cost = (total_tokens / 1000) * self.COST_PER_1K_TOKENS

        # Parse and validate the response
        raw_text = response.choices[0].message.content
        result = self._parse_classification(raw_text)

        return result, cost

    def _encode_image(self, image_path: str) -> str:
        """Encode image file to base64 string."""
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _parse_classification(self, raw_text: str) -> ClassificationResult:
        """
        Parse and validate the vision model's response.
        Never trusts invalid responses - raises on validation failure.
        """
        import json

        # Strip any markdown formatting the model might add
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from vision model: {e}")

        # Validate against schema - will raise ValidationError if invalid
        return ClassificationResult(**data)


vision_service: Optional[VisionService] = None


def get_vision_service() -> VisionService:
    """Get or create the vision service singleton."""
    global vision_service
    if vision_service is None:
        import os
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        vision_service = VisionService(api_key)
    return vision_service
