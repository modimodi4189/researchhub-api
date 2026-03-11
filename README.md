# ResearchHub API

An AI-powered research paper organization system built with FastAPI. Features semantic search, automatic summarization, and categorization using open-source ML models - no external API costs.

## Features

- **RESTful API** - Full CRUD operations for research papers
- **JWT Authentication** - Secure user registration and login
- **Semantic Search** - Find papers by meaning using vector embeddings (FAISS + sentence-transformers)
- **Auto-Summarization** - FLAN-T5 generates paper summaries
- **Zero-Shot Classification** - Categorize papers without training data
- **Collections** - Organize papers into custom collections
- **PDF Extraction** - Extract text from uploaded PDFs
- **Rate Limiting** - Built-in protection against abuse
- **Async Processing** - Celery + Redis for background tasks

## Tech Stack

| Category | Technology |
|----------|-----------|
| Framework | FastAPI |
| Database | PostgreSQL (async via asyncpg) |
| Cache/Queue | Redis |
| Task Queue | Celery |
| Auth | JWT (python-jose) |
| ML | sentence-transformers, FAISS, FLAN-T5, transformers |
| Container | Docker |

## Quick Start

### Prerequisites

- Docker & Docker Compose

### Setup

1. Clone the repository
2. Create environment file:
   ```bash
   cp .env.example .env
   ```
3. Start the services:
   ```bash
   docker-compose up -d
   ```

The API will be available at `http://localhost:8000`

### API Documentation

Interactive documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login and get token |
| POST | `/api/v1/auth/refresh` | Refresh access token |

### Papers
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/papers` | List user's papers |
| POST | `/api/v1/papers` | Create new paper |
| GET | `/api/v1/papers/{id}` | Get paper by ID |
| PATCH | `/api/v1/papers/{id}` | Update paper |
| DELETE | `/api/v1/papers/{id}` | Delete paper |
| POST | `/api/v1/papers/{id}/summarize` | Generate summary |
| POST | `/api/v1/papers/{id}/classify` | Categorize paper |

### Search
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/search/my` | Search own papers |
| GET | `/api/v1/search/public` | Search all public papers |
| GET | `/api/v1/search/similar/{id}` | Find similar papers |

### Collections
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/collections` | List collections |
| POST | `/api/v1/collections` | Create collection |
| GET | `/api/v1/collections/{id}` | Get collection |
| PATCH | `/api/v1/collections/{id}` | Update collection |
| DELETE | `/api/v1/collections/{id}` | Delete collection |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://postgres:postgres@localhost:5432/researchhub` |
| `SECRET_KEY` | JWT signing key | (required) |
| `ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry | `30` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `APP_NAME` | Application name | `ResearchHub API` |
| `DEBUG` | Debug mode | `True` |

## Project Structure

```
researchhub-api/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── auth/          # Authentication endpoints
│   │       ├── papers/        # Paper CRUD + ML endpoints
│   │       ├── collections/   # Collection management
│   │       └── search/        # Semantic search endpoints
│   ├── core/
│   │   ├── config.py          # Settings
│   │   ├── security.py       # JWT utilities
│   │   └── logging.py         # Logging config
│   ├── db/
│   │   ├── models.py          # SQLAlchemy models
│   │   └── database.py        # DB connection
│   ├── ml/
│   │   ├── embeddings.py      # Sentence-transformers
│   │   ├── faiss_index.py    # Vector database
│   │   ├── index_manager.py  # Search logic
│   │   ├── summarizer.py      # FLAN-T5
│   │   └── classifier.py     # Zero-shot classification
│   ├── schemas/               # Pydantic models
│   ├── tasks/                 # Celery tasks
│   ├── celery.py             # Celery config
│   └── main.py               # FastAPI app
├── tests/                     # Test files
├── docker-compose.yml        # Docker orchestration
├── Dockerfile               # API container
└── requirements.txt          # Python dependencies
```

## Development

### Running Tests

```bash
# Set environment variables
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/researchhub_test"
export REDIS_URL="redis://localhost:6379/0"
export SECRET_KEY="test-secret"

pytest tests/ -v
```

### Running Locally (without Docker)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn app.main:app --reload
```

## License

MIT

## Author

Built as a portfolio project demonstrating:
- RESTful API design with FastAPI
- JWT authentication
- PostgreSQL with async SQLAlchemy
- Vector-based semantic search
- ML model integration (summarization, classification)
- Docker containerization
- CI/CD with GitHub Actions
