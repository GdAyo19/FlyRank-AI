# AI Image Matching Engine

A backend service that matches blog posts with relevant images using semantic understanding and safety guards.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AI Image Matching Engine                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐              │
│  │   Images     │      │    Posts     │      │   Review     │              │
│  │   Upload     │      │    Create    │      │   API        │              │
│  └──────┬───────┘      └──────┬───────┘      └──────┬───────┘              │
│         │                      │                      │                      │
│         ▼                      ▼                      ▼                      │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐              │
│  │   Vision     │      │  Embedding   │      │   Approve/   │              │
│  │   Model      │      │  Service     │      │   Reject     │              │
│  │  (GPT-4V)    │      │  (OpenAI)    │      │              │              │
│  └──────┬───────┘      └──────┬───────┘      └──────────────┘              │
│         │                      │                                            │
│         ▼                      ▼                                            │
│  ┌──────────────┐      ┌──────────────┐                                   │
│  │  Metadata    │      │   Vector     │                                   │
│  │  (subject,   │      │   Index      │                                   │
│  │   category,  │      │  (1536-dim)  │                                   │
│  │   caption)   │      │              │                                   │
│  └──────┬───────┘      └──────┬───────┘                                   │
│         │                      │                                            │
│         └──────────┬───────────┘                                            │
│                    ▼                                                        │
│           ┌──────────────┐                                                  │
│           │   Similarity │                                                  │
│           │   Ranking    │                                                  │
│           └──────┬───────┘                                                  │
│                  ▼                                                          │
│           ┌──────────────┐                                                  │
│           │   Mismatch   │                                                  │
│           │   Guard      │                                                  │
│           │              │                                                  │
│           │ • Category   │                                                  │
│           │ • Confidence │                                                  │
│           │ • Threshold  │                                                  │
│           └──────┬───────┘                                                  │
│                  ▼                                                          │
│           ┌──────────────┐                                                  │
│           │  Suggestion  │                                                  │
│           │  with        │                                                  │
│           │  Explanation │                                                  │
│           └──────────────┘                                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
Images ──(batch job)──► Vision Model ──► {tags, caption, confidence} ──► image_metadata
                            │                                            │
                            └── embed(caption) ──────────────────────────► image_vectors
                                                                             │
Posts ──────────────────────► embed(post text) ─────────────────────────────► post_vectors
                                                                             │
GET /posts/:id/images                                                        │
    ◄── Similarity Ranking (image_vectors × post_vector) ◄──────────────────┘
    ◄── Mismatch Guard (tags + threshold + confidence)
    │
    ├──► Suggested image (ranked, explained)
    │
    └──► "No good match" + explanation
```

## Features

- **Vision Classification**: GPT-4V produces structured metadata validated against schema
- **Semantic Matching**: OpenAI embeddings enable concept-based matching
- **Mismatch Guard**: Safety layer rejects incorrect recommendations with explanations
- **Background Processing**: Async batch jobs with retries and cost tracking
- **Review API**: Approve/reject workflow with full audit trail

## Setup

### Prerequisites

- Python 3.11+
- OpenAI API key

### Installation

```bash
cd capstone
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Configuration

```bash
cp .env.example .env
# Edit .env with your OpenAI API key
```

### Database Setup

```bash
# Initialize the database
python -c "import asyncio; from app.models import init_db; asyncio.run(init_db())"

# Seed sample posts
python scripts/seed_data.py
```

### Running the Server

```bash
uvicorn app.main:app --reload --port 8000
```

API documentation available at: http://localhost:8000/docs

## API Endpoints

### Images

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/images` | Upload image (queues background processing) |
| GET | `/images` | List images with optional filters |
| GET | `/images/{id}` | Get image details |
| GET | `/images/{id}/embedding` | Get image embedding vector |

### Posts

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/posts` | Create a post |
| GET | `/posts` | List posts |
| GET | `/posts/{id}` | Get post details |

### Matching

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/posts/{id}/images` | Get ranked image suggestions |
| GET | `/posts/{id}/no-match` | Check if no good match exists |

### Review

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/suggestions` | List all suggestions |
| POST | `/suggestions/{id}/review` | Approve or reject suggestion |

### Background Jobs

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/jobs/process-images` | Queue images for processing |
| POST | `/jobs/process-posts` | Queue posts for processing |
| GET | `/jobs` | List processing jobs |
| GET | `/jobs/costs` | Get total processing costs |

### Evaluation

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/eval/precision` | Calculate top-1 precision |

## Example Usage

### 1. Upload an image

```bash
curl -X POST http://localhost:8000/images \
  -F "file=@red_fox.jpg"
```

### 2. Create a post

```bash
curl -X POST http://localhost:8000/posts \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Behavior of Red Foxes",
    "content": "Red foxes are intelligent and adaptable animals...",
    "category": "animal"
  }'
```

### 3. Get image suggestions

```bash
curl http://localhost:8000/posts/1/images
```

Response:
```json
[
  {
    "id": 1,
    "post_id": 1,
    "image_id": 1,
    "similarity_score": 0.89,
    "guard_passed": true,
    "guard_explanation": "PASSED: category=animal, similarity=0.892, confidence=0.94",
    "status": "pending"
  }
]
```

### 4. Review a suggestion

```bash
curl -X POST http://localhost:8000/suggestions/1/review \
  -H "Content-Type: application/json" \
  -d '{"action": "approve", "notes": "Perfect match"}'
```

## Evaluation

The system includes a labeled evaluation dataset at `eval_data/eval_set.json` with 10 posts mapped to their correct images.

Run evaluation:
```bash
curl http://localhost:8000/eval/precision
```

## Cost Tracking

All AI operations track costs:

```bash
curl http://localhost:8000/jobs/costs
```

## Testing

```bash
pytest tests/ -v
```

## Project Structure

```
capstone/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── vision_service.py    # Image classification
│   ├── embedding_service.py # Vector embeddings
│   ├── mismatch_guard.py    # Safety layer
│   └── background_processor.py # Batch jobs
├── scripts/
│   └── seed_data.py         # Sample data
├── tests/
│   └── test_api.py          # API tests
├── eval_data/
│   └── eval_set.json        # Evaluation dataset
├── images/                  # Uploaded images
├── requirements.txt
├── .env.example
└── README.md
```

## License

MIT
