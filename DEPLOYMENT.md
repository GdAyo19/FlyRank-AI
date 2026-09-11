# AI Image Matching Engine - Deployment Guide

## What This App Does

This is a backend service that matches blog posts with relevant images using AI. It:

1. **Classifies images** using GPT-4V (vision model) - identifies subjects, categories, attributes
2. **Creates embeddings** - converts text to vectors for semantic search
3. **Matches posts to images** - finds the best image for each post
4. **Safety guard** - rejects bad matches and explains why
5. **Review workflow** - approve or reject suggested pairings

---

## Prerequisites

Before you start, you need:

- [Python 3.11+](https://www.python.org/downloads/)
- [Git](https://git-scm.com/downloads)
- An [OpenAI API key](#how-to-get-an-openai-api-key) (costs ~$1-5 for testing)

---

## How to Get an OpenAI API Key

### Step 1: Create an OpenAI Account

1. Go to [https://platform.openai.com](https://platform.openai.com)
2. Click **Sign Up**
3. Sign up with email, Google, or Microsoft

### Step 2: Add Payment Method

1. Once logged in, click your profile icon (top right)
2. Go to **Billing** → **Payment methods**
3. Add a credit card

> **Cost estimate**: Testing this app uses ~$1-5 total. The vision model costs ~$0.03 per image, and embeddings cost ~$0.00002 per text.

### Step 3: Create API Key

1. Go to [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Click **Create new secret key**
3. Name it something like "capstone-deployment"
4. Click **Create**
5. **Copy the key immediately** - you won't see it again!
6. It looks like: `sk-proj-abc123xyz789...`

> **Important**: Keep this key secret. Never share it or commit it to GitHub.

---

## Local Deployment

### 1. Clone the Repository

```bash
git clone https://github.com/GdAyo19/FlyRank-AI.git
cd FlyRank-AI
git checkout deployment-guide
```

### 2. Set Up Python Environment

```bash
cd capstone

# Create virtual environment
python -m venv venv

# Activate it
# On Mac/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
# Copy the example file
cp .env.example .env
```

Now edit the `.env` file and add your OpenAI API key:

```
OPENAI_API_KEY=sk-proj-your-key-here
DATABASE_URL=sqlite+aiosqlite:///./image_matching.db
SIMILARITY_THRESHOLD=0.75
LOW_CONFIDENCE_THRESHOLD=0.6
```

Replace `sk-proj-your-key-here` with the key you copied from OpenAI.

### 5. Initialize Database and Sample Data

```bash
# Create database tables
python -c "import asyncio; from app.models import init_db; asyncio.run(init_db())"

# Add sample posts
python scripts/seed_data.py
```

### 6. Start the Server

```bash
uvicorn app.main:app --reload --port 8000
```

### 7. Open the API Docs

Go to: [http://localhost:8000/docs](http://localhost:8000/docs)

You'll see the interactive API documentation where you can test all endpoints.

---

## Cloud Deployment (Render - Free)

### Step 1: Push to GitHub

```bash
git push -u origin deployment-guide
```

### Step 2: Create Render Account

1. Go to [https://render.com](https://render.com)
2. Sign up with GitHub

### Step 3: Create Web Service

1. Click **New +** → **Web Service**
2. Connect your GitHub repository
3. Configure:
   - **Name**: `ai-image-matching`
   - **Branch**: `deployment-guide`
   - **Runtime**: Python
   - **Build Command**: `cd capstone && pip install -r requirements.txt`
   - **Start Command**: `cd capstone && uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Step 4: Add Environment Variables

In Render dashboard, go to **Environment** tab and add:

| Key | Value |
|-----|-------|
| `OPENAI_API_KEY` | `sk-proj-your-key-here` |
| `DATABASE_URL` | `sqlite+aiosqlite:///./image_matching.db` |
| `SIMILARITY_THRESHOLD` | `0.75` |
| `LOW_CONFIDENCE_THRESHOLD` | `0.6` |

### Step 5: Deploy

Click **Create Web Service** and wait 2-3 minutes.

Your app will be live at: `https://ai-image-matching.onrender.com`

---

## Cloud Deployment (Railway)

1. Go to [https://railway.app](https://railway.app)
2. Sign up with GitHub
3. Click **New Project** → **Deploy from GitHub repo**
4. Select your repo and branch
5. Add the same environment variables as above
6. Railway will auto-deploy

---

## How to Use the App

### 1. Upload Images

```bash
curl -X POST http://localhost:8000/images \
  -F "file=@your-image.jpg"
```

Or use the `/images` endpoint in the API docs.

### 2. Create Posts

```bash
curl -X POST http://localhost:8000/posts \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Behavior of Red Foxes",
    "content": "Red foxes are intelligent animals...",
    "category": "animal"
  }'
```

### 3. Get Image Suggestions

```bash
curl http://localhost:8000/posts/1/images
```

### 4. Review Suggestions

```bash
curl -X POST http://localhost:8000/suggestions/1/review \
  -H "Content-Type: application/json" \
  -d '{"action": "approve", "notes": "Great match!"}'
```

### 5. Check Processing Costs

```bash
curl http://localhost:8000/jobs/costs
```

### 6. Run Evaluation

```bash
curl http://localhost:8000/eval/precision
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Service info |
| GET | `/health` | Health check |
| POST | `/images` | Upload image |
| GET | `/images` | List images |
| GET | `/images/{id}` | Get image |
| POST | `/posts` | Create post |
| GET | `/posts` | List posts |
| GET | `/posts/{id}` | Get post |
| GET | `/posts/{id}/images` | Get suggestions |
| GET | `/posts/{id}/no-match` | Check no match |
| GET | `/suggestions` | List suggestions |
| POST | `/suggestions/{id}/review` | Approve/reject |
| POST | `/jobs/process-images` | Queue images |
| POST | `/jobs/process-posts` | Queue posts |
| GET | `/jobs` | List jobs |
| GET | `/jobs/costs` | Get costs |
| GET | `/eval/precision` | Run evaluation |

---

## Troubleshooting

### "OPENAI_API_KEY not set"
Make sure you edited `.env` and added your key.

### "ModuleNotFoundError"
Run `pip install -r requirements.txt` again.

### Database errors
Delete `image_matching.db` and re-run the init commands:
```bash
python -c "import asyncio; from app.models import init_db; asyncio.run(init_db())"
python scripts/seed_data.py
```

### Port already in use
Use a different port:
```bash
uvicorn app.main:app --reload --port 8001
```

---

## Project Structure

```
capstone/
├── app/
│   ├── main.py              # API endpoints
│   ├── models.py            # Database tables
│   ├── schemas.py           # Data validation
│   ├── vision_service.py    # Image classification (GPT-4V)
│   ├── embedding_service.py # Vector embeddings
│   ├── mismatch_guard.py    # Safety layer
│   └── background_processor.py # Batch jobs
├── scripts/
│   └── seed_data.py         # Sample data
├── tests/
│   └── test_api.py          # Tests
├── eval_data/
│   └── eval_set.json        # Evaluation dataset
├── requirements.txt
├── .env.example
└── README.md
```

---

## Cost Summary

| Operation | Cost |
|-----------|------|
| Image classification (GPT-4V) | ~$0.03 per image |
| Embedding generation | ~$0.00002 per text |
| **Total for 40 images + 10 posts** | **~$2-3** |

---

## Need Help?

If you get stuck, check:
1. [OpenAI API docs](https://platform.openai.com/docs)
2. [FastAPI docs](https://fastapi.tiangolo.com/)
3. [Render docs](https://render.com/docs)
