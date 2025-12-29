# SWESphere Backend

A FastAPI-based backend for the SWESphere social media platform.

## Features

- **Async-first**: Built with FastAPI and async SQLAlchemy for high performance
- **JWT Authentication**: Secure token-based authentication with Redis blacklisting
- **PostgreSQL**: Robust relational database with full-text search capabilities
- **Redis**: Session management, caching, and Celery broker
- **Celery**: Background task processing for emails and notifications

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL 16 with SQLAlchemy 2.0 async
- **Cache/Broker**: Redis 7
- **Task Queue**: Celery
- **Auth**: JWT with python-jose + bcrypt

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 16
- Redis 7

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Set up environment variables
cp .env.example .env
# Edit .env with your settings

# Run database migrations
alembic upgrade head

# Start the development server
uvicorn app.main:app --reload --port 8000
```

### Docker Development

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f web

# Run migrations
docker compose exec web alembic upgrade head
```

## Project Structure

```
backend/
├── app/
│   ├── api/              # API routes and dependencies
│   │   └── v1/           # API version 1 endpoints
│   ├── core/             # Security, config, events
│   ├── db/               # Database session and base
│   ├── models/           # SQLAlchemy models
│   ├── repositories/     # Data access layer
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic
│   └── workers/          # Celery tasks
├── migrations/           # Alembic migrations
├── tests/               # Test suite
└── docker-compose.yml   # Docker orchestration
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py -v
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `JWT_SECRET_KEY` | Secret for JWT signing | Required |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry | `30` |
| `CORS_ORIGINS` | Allowed origins | `["http://localhost:5173"]` |
| `ENVIRONMENT` | Environment name | `development` |

## License

MIT

