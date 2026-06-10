# End-to-End Recommendation System

A production-grade ML portfolio project: candidate generation, ranking, offline evaluation, and A/B testing — with a live dashboard.

**Live Demo:** `https://recsys-frontend-9vxz.onrender.com`  
**API Docs:** `https://recsys-backend-tjt0.onrender.com/docs`

---

## Architecture

```
Next.js Dashboard (Render)
      ↓  HTTPS
FastAPI Backend (Render)
  ├── Popularity Recommender (time-decayed item counts)
  ├── Content-Based (TF-IDF + cosine similarity)
  ├── Collaborative Filtering (Truncated SVD)
  └── LightGBM Ranker (re-ranks blended candidates)
      ↓
Supabase PostgreSQL
```

## ML Pipeline

| Stage | Model | Notes |
|-------|-------|-------|
| Candidate Generation | Popularity + CF + Content-Based | Union → dedup → top 50 |
| Re-Ranking | LightGBM LambdaRank | 11 features, ~200 trees |
| Cold-Start Fallback | Popularity | < 3 interactions |
| Diversity Control | Category cap (max 3/category) | Applied post-ranking |

## Offline Metrics

Computed with time-based 80/20 train/test split:

- Precision@K, Recall@K, NDCG@K, MRR
- Catalog coverage, pairwise diversity

## Project Structure

```
apps/
  backend/         FastAPI + SQLAlchemy + ML models
  frontend/        Next.js 14 dashboard
infra/
  docker-compose.yml
render.yaml        One-command Render deploy
```

## Local Development

### Backend

```bash
cd apps/backend
cp .env.example .env
# Edit .env: set DATABASE_URL to your Supabase connection string
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The backend seeds 50 users + 100 movies + ~985 events on first start. Then call:

```bash
curl -X POST http://localhost:8000/models/train
```

### Frontend

```bash
cd apps/frontend
cp .env.example .env.local
# Edit: NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev
```

### Docker Compose (both services)

```bash
# Add DATABASE_URL to .env in project root
cd infra
docker-compose up --build
```

## Deploy to Render

1. Fork / push this repo to GitHub.
2. In [Render dashboard](https://render.com), click **New → Blueprint** and connect your repo.
3. Render reads `render.yaml` and creates both services automatically.
4. Set `DATABASE_URL` in the `recsys-backend` service env vars:
   - Get it from Supabase → Project Settings → Database → Connection string (URI mode).
5. Deploy. The backend seeds on first boot; then hit `POST /models/train` once to train all models.

## API Contract

All responses use:
```json
{ "success": true, "data": {}, "request_id": "req_..." }
{ "success": false, "error": { "code": "...", "message": "..." } }
```

Key endpoints:

| Method | Path | Description |
|--------|------|-------------|
| POST | `/events` | Record user interaction |
| GET | `/recommendations/{user_id}` | Get personalised recs |
| POST | `/models/train` | Train all models |
| GET | `/evaluations/latest` | Offline metrics |
| GET | `/experiments` | A/B test results |
| GET | `/health` | Service health + model status |

## Tests

```bash
cd apps/backend
python -m pytest app/tests/ -v
```

10 tests covering events, recommendations, training, health, and A/B determinism.

## Security Notes

- No secrets in source — all via env vars
- CORS restricted to Render domains
- Inputs validated with Pydantic v2
- No raw SQL — all parameterised via SQLAlchemy ORM
- Structured JSON logs (no PII)
