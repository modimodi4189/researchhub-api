# ResearchHub API

An AI-powered research paper organization system built with FastAPI. Features semantic search, automatic summarization, and zero-shot categorization using open-source ML models — no external API costs.

## Features

- **RESTful API** — Full CRUD for research papers and collections
- **JWT Authentication** — Secure registration, login, and token rotation
- **Semantic Search** — Find papers by meaning using FAISS vector search + sentence-transformers
- **Auto-Summarization** — distilbart-cnn-12-6 generates concise paper summaries
- **Zero-Shot Classification** — Categorize papers without labelled training data (BART-large-MNLI)
- **Collections** — Organize papers into named collections
- **Rate Limiting** — Per-endpoint protection on auth routes
- **Background Processing** — Celery + Redis for async ML indexing tasks
- **Alembic Migrations** — Schema versioned and reproducible

## Tech Stack

| Category | Technology |
|----------|-----------|
| Framework | FastAPI |
| Database | PostgreSQL (async via asyncpg) |
| ORM | SQLAlchemy 2.0 (async) |
| Cache / Queue | Redis |
| Task Queue | Celery |
| Auth | JWT (python-jose) with access + refresh token rotation |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Vector Store | FAISS (IndexIDMap) |
| Summarization | sshleifer/distilbart-cnn-12-6 |
| Classification | facebook/bart-large-mnli (zero-shot) |
| Migrations | Alembic |
| Container | Docker + Docker Compose |
| CI/CD | GitHub Actions → GHCR |

> **Why distilbart over FLAN-T5?** FLAN-T5 is an instruction-following model designed for prompted generation tasks. Running it through the `summarization` pipeline produces inconsistent output because it is not fine-tuned for extractive summarization. distilbart-cnn-12-6 is a distilled BART model specifically fine-tuned on CNN/DailyMail for summarization, making it the correct tool for this task.

## Quick Start

### Prerequisites

- Docker & Docker Compose
- A generated secret key (see below)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/modimodi4189/researchhub-api.git
   cd researchhub-api
   ```

2. Create your environment file and set a real secret key:
   ```bash
   cp .env.example .env
   # Generate a secure key:
   python -c "import secrets; print(secrets.token_hex(32))"
   # Paste the output as SECRET_KEY in .env
   ```

3. Start the services:
   ```bash
   docker-compose up -d
   ```

   The `migrate` service runs `alembic upgrade head` automatically before the API starts.

The API will be available at `http://localhost:8000`.

### API Documentation

Interactive docs available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login and receive token pair |
| POST | `/api/v1/auth/refresh` | Rotate refresh token |

### Papers
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/papers` | List user's papers (paginated, no content body) |
| POST | `/api/v1/papers` | Create new paper |
| GET | `/api/v1/papers/{id}` | Get paper with full content |
| PATCH | `/api/v1/papers/{id}` | Update paper |
| DELETE | `/api/v1/papers/{id}` | Delete paper |
| POST | `/api/v1/papers/{id}/summarize` | Generate summary (owner only) |
| POST | `/api/v1/papers/{id}/classify` | Categorize paper (owner only) |

### Search
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/search/my` | Semantic search over own papers |
| GET | `/api/v1/search/public` | Semantic search over public papers |
| GET | `/api/v1/search/similar/{id}` | Find similar papers |

### Collections
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/collections` | List collections (paginated) |
| POST | `/api/v1/collections` | Create collection |
| GET | `/api/v1/collections/{id}` | Get collection with papers |
| PATCH | `/api/v1/collections/{id}` | Rename collection |
| DELETE | `/api/v1/collections/{id}` | Delete collection |
| POST | `/api/v1/collections/{id}/papers/{paper_id}` | Add paper to collection |
| DELETE | `/api/v1/collections/{id}/papers/{paper_id}` | Remove paper from collection |

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | JWT signing key — generate with `secrets.token_hex(32)` | **Yes** |
| `DATABASE_URL` | PostgreSQL async connection string | **Yes** |
| `POSTGRES_PASSWORD` | Postgres password (used by docker-compose) | **Yes** |
| `REDIS_URL` | Redis connection string | **Yes** |
| `ALGORITHM` | JWT algorithm | Default: `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token TTL | Default: `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token TTL | Default: `7` |
| `FAISS_INDEX_DIR` | Directory for FAISS index files | Default: `ml_artifacts` |
| `DEBUG` | Debug mode (never `True` in production) | Default: `False` |

## Running Tests

Tests run inside Docker against a dedicated `test_researchhub` database. ML inference and Celery tasks are mocked — the suite runs in seconds with no GPU required.

```bash
# Create the test database (one-time setup)
docker exec -it researchhub-api-postgres-1 psql -U postgres -c "CREATE DATABASE test_researchhub;"

# Run Alembic migrations against the test database
docker exec -e DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/test_researchhub \
  -it researchhub-api-api-1 alembic upgrade head

# Run the test suite
docker exec -it researchhub-api-api-1 python -m pytest --tb=short
```

## Known Limitations

- **FAISS is single-machine** — horizontal scaling would require switching to pgvector, Pinecone, or Weaviate.
- **No token revocation** — refresh tokens are stateless JWTs; invalidation would require a Redis-backed blocklist.
- **FAISS ↔ DB consistency** — if the Celery worker is down during a deletion, the paper is removed from Postgres but its vector remains in the index until the next indexing run. Search returns no results for stale IDs (DB lookup filters them silently).
- **PDF upload** — `pdf_extractor.py` is implemented but not yet wired to a route.

## Project Structure

```
researchhub-api/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── auth/          # Registration, login, token rotation
│   │       ├── papers/        # Paper CRUD + summarize/classify
│   │       ├── collections/   # Collection management
│   │       └── search/        # Semantic search endpoints
│   ├── core/
│   │   ├── config.py          # Pydantic settings
│   │   ├── security.py        # JWT utilities
│   │   ├── executor.py        # Shared ThreadPoolExecutor for ML
│   │   └── logging.py         # Loguru configuration
│   ├── db/
│   │   ├── models.py          # SQLAlchemy models
│   │   └── database.py        # Async engine and session factory
│   ├── ml/
│   │   ├── embeddings.py      # sentence-transformers wrapper
│   │   ├── faiss_index.py     # FAISS IndexIDMap operations
│   │   ├── index_manager.py   # Per-user and public index management
│   │   ├── summarizer.py      # distilbart-cnn-12-6 summarization
│   │   ├── classifier.py      # Zero-shot classification
│   │   └── pdf_extractor.py   # PDF text extraction (not yet routed)
│   ├── schemas/               # Pydantic request/response models
│   ├── tasks/                 # Celery background tasks
│   ├── celery.py              # Celery app configuration
│   └── main.py                # FastAPI application factory
├── alembic/                   # Database migrations
├── tests/                     # pytest test suite (49 tests)
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## License

MIT

## Author

Built as a portfolio project demonstrating:
- Async FastAPI with SQLAlchemy 2.0
- JWT authentication with token rotation
- FAISS vector search with correct IndexIDMap usage
- ML model integration (summarization, zero-shot classification)
- Celery + Redis for background task processing
- Docker Compose with health-checked service dependencies
- Alembic schema migrations
- GitHub Actions CI/CD with automated testing
