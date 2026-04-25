# Job Board Backend

Backend API for a Job Board MVP (candidate, recruiter, admin) built with Python and FastAPI.

## Stack

- Python
- FastAPI
- SQLAlchemy + Alembic
- PostgreSQL
- Redis + Celery
- MinIO (S3-compatible)
- Docker Compose

## Prerequisites

- Docker
- Docker Compose

## Quick Start

1. Copy environment file:

   ```powershell
   copy .env.example .env
   ```

2. Start local services:

   ```powershell
   docker compose up -d --build
   ```

3. Check API health (after app files are added):

   ```text
   http://localhost:8000/health
   ```

4. MinIO console:

   ```text
   http://localhost:9001
   ```
