# Feature 01: Project Setup & Infrastructure

## Overview

Bootstrap the FairLens monorepo with all dependencies, environment configuration, Docker containerization, and dev tooling. This is the foundation every other feature builds on.

---

## Backend Setup

### Directory Structure

Create the following structure inside `backend/`:

```
backend/
├── main.py                  # FastAPI app entry point
├── config.py                # Settings via pydantic-settings
├── pyproject.toml           # Dependencies
├── routes/
│   └── __init__.py
├── pipeline/
│   └── __init__.py
├── metrics/
│   └── __init__.py
├── rag/
│   └── __init__.py
├── db/
│   ├── __init__.py
│   ├── connection.py        # Async SQLAlchemy engine + session
│   └── models.py            # ORM models (Feature 02)
├── schemas/
│   └── __init__.py          # Pydantic request/response models
└── uploads/                 # Uploaded files directory (gitignored)
```

### Dependencies (`pyproject.toml`)

Update `pyproject.toml` with all required dependencies:

```toml
[project]
name = "fairlens-backend"
version = "0.1.0"
description = "FairLens AI Bias Detection & Remediation Platform - Backend"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastapi[standard]>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "python-multipart>=0.0.12",
    "sqlalchemy[asyncio]>=2.0.36",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.6.0",
    "pandas>=2.2.0",
    "numpy>=1.26.0",
    "scipy>=1.14.0",
    "openpyxl>=3.1.0",
    "fairlearn>=0.10.0",
    "aif360>=0.6.1",
    "scikit-learn>=1.5.0",
    "langgraph>=0.2.0",
    "langchain>=0.3.0",
    "langchain-anthropic>=0.3.0",
    "langchain-openai>=0.2.0",
    "langchain-community>=0.3.0",
    "pgvector>=0.3.0",
    "python-dotenv>=1.0.0",
    "aiofiles>=24.1.0",
]
```

### `config.py` — Application Settings

```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # App
    APP_NAME: str = "FairLens"
    DEBUG: bool = True
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/fairlens"

    # LLM
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    LLM_PROVIDER: str = "anthropic"  # "anthropic" or "openai"
    LLM_MODEL: str = "claude-sonnet-4-20250514"

    # File uploads
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 100

    class Config:
        env_file = ".env"

settings = Settings()
```

### `main.py` — FastAPI App

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from config import settings
from db.connection import init_db
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    await init_db()
    yield
    # Shutdown (cleanup if needed)

app = FastAPI(
    title=settings.APP_NAME,
    description="AI Bias Detection & Remediation Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "app": settings.APP_NAME}
```

### `db/connection.py` — Async Database Connection

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def init_db():
    from db.models import Base  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
```

---

## Frontend Setup

The frontend is already scaffolded with Next.js 16, React 19, and Tailwind CSS v4.

### Additional Dependencies to Install

```bash
cd frontend
npm install recharts lucide-react clsx axios react-dropzone
npm install -D @types/node
```

- **recharts** — Charts and data visualization
- **lucide-react** — Icon library
- **clsx** — Conditional classnames
- **axios** — HTTP client for API calls
- **react-dropzone** — File upload drag & drop

### Create API Client (`frontend/lib/api.ts`)

```typescript
import axios from 'axios';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: `${API_BASE}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Upload with progress tracking
export const uploadFile = (
  file: File,
  onProgress?: (percent: number) => void
) => {
  const formData = new FormData();
  formData.append('file', file);

  return api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (e.total && onProgress) {
        onProgress(Math.round((e.loaded * 100) / e.total));
      }
    },
  });
};
```

### Create `.env.local` for Frontend

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Environment Configuration

### Root `.env.example`

Create at `e:\FairLens\.env.example`:

```env
# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=fairlens
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/fairlens

# LLM API Keys (at least one required)
ANTHROPIC_API_KEY=your-anthropic-key-here
OPENAI_API_KEY=your-openai-key-here
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-20250514

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Docker Configuration

### `docker-compose.yml` (Root)

```yaml
version: '3.8'

services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      POSTGRES_DB: ${POSTGRES_DB:-fairlens}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - db
    volumes:
      - ./backend:/app
      - uploads:/app/uploads

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    env_file:
      - .env
    depends_on:
      - backend

volumes:
  pgdata:
  uploads:
```

### `backend/Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .
COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### `frontend/Dockerfile`

```dockerfile
FROM node:20-alpine

WORKDIR /app
COPY package*.json .
RUN npm ci
COPY . .

CMD ["npm", "run", "dev"]
```

---

## Verification

After setup, the following should work:

1. `docker-compose up` starts all three services without errors
2. `GET http://localhost:8000/api/health` returns `{"status": "healthy", "app": "FairLens"}`
3. `http://localhost:3000` loads the Next.js frontend
4. PostgreSQL is accessible on port 5432 with pgvector extension enabled
