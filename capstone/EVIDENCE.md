# EVIDENCE.md

This document provides proof that each requirement in the capstone specification has been met.

## AI Processing

### ✅ Vision model produces structured output validated against schema

**File**: `app/vision_service.py`

The `classify_image` method returns a `ClassificationResult` that is validated by Pydantic:

```python
# Line 78-83
def _parse_classification(self, raw_text: str) -> ClassificationResult:
    # Parse and validate the vision model's response.
    # Never trusts invalid responses - raises on validation failure.
    data = json.loads(cleaned)
    return ClassificationResult(**data)
```

**Schema definition** (`app/schemas.py`):
```python
class ClassificationResult(BaseModel):
    subject: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., min_length=1, max_length=100)
    attributes: list[str] = Field(default_factory=list)
    caption: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)
```

### ✅ Low-confidence classifications are flagged instead of accepted

**File**: `app/models.py`, Line 68

```python
image.is_flagged = classification.confidence < 0.6
```

**File**: `app/mismatch_guard.py`, Line 85-89

```python
confidence_acceptable = image_classification.confidence >= self.low_confidence_threshold
if not confidence_acceptable:
    reasons.append(
        f"Low confidence: {image_classification.confidence:.3f} "
        f"(threshold: {self.low_confidence_threshold})"
    )
```

### ✅ Images are processed through batch background job with retries

**File**: `app/background_processor.py`, Lines 25-100

```python
async def process_image(self, image_id: int) -> bool:
    # ... processing logic ...
    job.attempts += 1
    # Retry if we haven't exceeded max attempts
    if job.attempts < job.max_retries:
        await asyncio.sleep(2 ** job.attempts)  # Exponential backoff
        return await self.process_image(image_id)
```

---

## Matching System

### ✅ Vision and embedding costs are tracked per call

**File**: `app/vision_service.py`, Lines 36-38

```python
# Calculate cost based on tokens used
usage = response.usage
total_tokens = usage.total_tokens if usage else 0
cost = (total_tokens / 1000) * self.COST_PER_1K_TOKENS
```

**File**: `app/background_processor.py`, Lines 88-91

```python
job.vision_cost = vision_cost
# ... later ...
job.embedding_cost = embedding_cost
```

**API endpoint** (`app/main.py`):
```python
@app.get("/jobs/costs")
async def get_processing_costs(db: AsyncSession = Depends(get_db)):
    # Returns total_vision_cost, total_embedding_cost, total_jobs
```

### ✅ Image and post embeddings are stored; posts return ranked image suggestions

**Database models** (`app/models.py`):
```python
class ImageEmbedding(Base):
    image_id = Column(Integer, ForeignKey("images.id"), nullable=False)
    embedding = Column(JSON, nullable=False)

class PostEmbedding(Base):
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    embedding = Column(JSON, nullable=False)
```

**Ranking endpoint** (`app/main.py`):
```python
@app.get("/posts/{post_id}/images")
async def get_image_suggestions(post_id: int, limit: int = 5, ...):
    # Ranks by similarity and applies guard
```

### ✅ Semantic matching works for equivalent concepts

The system uses OpenAI's `text-embedding-3-small` model which produces 1536-dimensional vectors that capture semantic meaning. Terms like "red fox", "Vulpes vulpes", and "wild fox species" produce similar embeddings because the model understands semantic relationships.

**File**: `app/embedding_service.py`, Lines 15-18

```python
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
```

---

## Safety Layer

### ✅ Mismatch guard rejects incorrect recommendations

**File**: `app/mismatch_guard.py`, Lines 43-100

```python
def evaluate(self, post_category, image_classification, similarity_score):
    # Check 1: Category mismatch (hard fail)
    category_match = self._check_category_match(post_category, image_classification.category)
    
    # Check 2: Similarity threshold (hard fail)
    similarity_acceptable = similarity_score >= self.similarity_threshold
    
    # Check 3: Confidence check (soft fail)
    confidence_acceptable = image_classification.confidence >= self.low_confidence_threshold
```

**Test proof** (`tests/test_api.py`):
```python
def test_guard_rejects_incompatible_categories(self):
    guard = MismatchGuard()
    classification = ClassificationResult(
        subject="red sports car",
        category="vehicle",  # Vehicle vs animal
        ...
    )
    result = guard.evaluate(
        post_category="animal",
        image_classification=classification,
        similarity_score=0.8
    )
    assert result.passed is False
    assert "Category mismatch" in result.explanation
```

### ✅ Rejections include a human-readable explanation

**File**: `app/mismatch_guard.py`, Lines 68-82

```python
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
```

### ✅ No confident match returns "no confident match" with reasons

**File**: `app/main.py`:

```python
@app.get("/posts/{post_id}/no-match")
async def check_no_match(post_id: int, ...):
    if top_suggestion and top_suggestion.guard_passed:
        return {"has_match": True, "suggestion_id": top_suggestion.id}
    
    if top_suggestion:
        return {
            "has_match": False,
            "reason": top_suggestion.guard_explanation,
            "best_score": top_suggestion.similarity_score
        }
    
    return {"has_match": False, "reason": "No candidates found"}
```

---

## Backend

### ✅ Database models with required indexes

**File**: `app/models.py`

```python
class Image(Base):
    # Fields: id, filename, filepath, subject, category, attributes, caption, confidence, is_flagged, processed, created_at, updated_at

class ImageEmbedding(Base):
    # Indexes:
    __table_args__ = (
        Index("idx_image_embeddings_image_id", "image_id"),
    )

class Post(Base):
    # Fields: id, title, content, category, processed, created_at, updated_at

class PostEmbedding(Base):
    __table_args__ = (
        Index("idx_post_embeddings_post_id", "post_id"),
    )

class Suggestion(Base):
    __table_args__ = (
        Index("idx_suggestions_post_id", "post_id"),
        Index("idx_suggestions_status", "status"),
    )

class ProcessingJob(Base):
    # Tracks: image_id, status, attempts, max_retries, error_message, vision_cost, embedding_cost
```

### ✅ API endpoints validated; review workflow exists

**File**: `app/main.py`

All endpoints use Pydantic schemas for request/response validation.

Review workflow:
```python
@app.post("/suggestions/{suggestion_id}/review")
async def review_suggestion(suggestion_id: int, review: ReviewAction, ...):
    # Accepts: {"action": "approve"|"reject", "notes": "optional"}
    # Updates status and reviewed_at timestamp
```

---

## Quality & Documentation

### ✅ README with architecture explanation and diagram

**File**: `README.md`

Contains:
- ASCII architecture diagram
- Data flow diagram
- Setup instructions
- API documentation with examples
- Project structure

### ✅ Labeled evaluation dataset

**File**: `eval_data/eval_set.json`

10 labeled post-to-image mappings for precision measurement.

### ✅ Evaluation endpoint

**File**: `app/main.py`:

```python
@app.get("/eval/precision", response_model=EvalSummary)
async def evaluate_precision(db: AsyncSession = Depends(get_db)):
    # Calculates top-1 precision against eval set
```

---

## Project Files

All required files present:

- [x] `app/main.py` - FastAPI application
- [x] `app/models.py` - Database models
- [x] `app/schemas.py` - Pydantic schemas
- [x] `app/vision_service.py` - Image classification
- [x] `app/embedding_service.py` - Vector embeddings
- [x] `app/mismatch_guard.py` - Safety layer
- [x] `app/background_processor.py` - Batch jobs
- [x] `tests/test_api.py` - API tests
- [x] `scripts/seed_data.py` - Sample data
- [x] `eval_data/eval_set.json` - Evaluation dataset
- [x] `requirements.txt` - Dependencies
- [x] `README.md` - Documentation
- [x] `.env.example` - Configuration template
