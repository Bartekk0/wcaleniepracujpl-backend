- Python
  - główny język backendu.

- FastAPI
  - budowa REST API (oferty, aplikacje, auth, admin).
  - walidacja danych wejściowych i dokumentacja OpenAPI.

- SQLAlchemy + Alembic
  - ORM do pracy z bazą danych.
  - migracje schematu bazy.

- PostgreSQL
  - główna relacyjna baza danych (użytkownicy, oferty, aplikacje, statusy).

- Redis
  - broker/cache i obsługa kolejek zadań asynchronicznych.
  - rate limiting i anty-spam (np. na login/apply).

- Celery
  - background jobs (np. wysyłka maili, powiadomienia, zadania cykliczne).

- MinIO (S3-compatible)
  - storage plików (CV, załączniki, logo firm).

- Docker + Docker Compose
  - lokalne środowisko deweloperskie i spójne uruchamianie usług.
  - przygotowanie pod wdrożenie na serwer/staging.