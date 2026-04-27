# Environment setup and deployment notes

## Running the backend locally

See repository [README.md](../../README.md):

- Copy `.env.example` → `.env`
- `docker compose up -d --build`
- Health: `http://localhost:8000/health` (or `APP_PORT` if changed)

Default app port in Docker/README context is **8000**.

## Frontend environment variables (suggested)

Your SPA/build tool may use different prefixes; typical names:

| Variable | Example | Purpose |
|----------|---------|---------|
| `PUBLIC_API_BASE_URL` | `http://localhost:8000` | Origin only; client prepends `/api/v1` |
| or `PUBLIC_API_URL` | `http://localhost:8000/api/v1` | Full API prefix |

**Recommendation**: store **origin** separately from path so you can call `/health` without duplicating `/api/v1`.

## OpenAPI and interactive docs

When the API process is running:

| URL | Purpose |
|-----|---------|
| `/docs` | Swagger UI |
| `/redoc` | ReDoc |
| `/openapi.json` | Machine-readable schema |

Production teams often **disable public `/docs`** behind auth or remove in hardened builds — confirm for your deployment.

## CORS and same-origin policy

`app/main.py` does **not** add `CORSMiddleware`.

Implications:

- A SPA at `http://localhost:5173` calling `http://localhost:8000` will hit **browser CORS** unless you:
  - **Proxy** `/api` through the dev server (Vite `server.proxy`, Next rewrites), or
  - Add CORS on the API (future backend change).

**Recommended for local dev**: dev-server proxy so the browser sees **same origin**.

## MinIO and presigned URLs

Server env (from `.env.example`):

- `MINIO_ENDPOINT` — used by the Python MinIO client to build presigned URLs.
- For **browser-direct** PUT/GET, the hostname in presigned URLs must resolve on the **user’s machine**.

Common patterns:

| Environment | Approach |
|-------------|----------|
| Local Docker + SPA on host | Set `MINIO_ENDPOINT` to `localhost:9000` (or host gateway IP) instead of `minio:9000` for dev, **or** proxy MinIO through nginx on `localhost`. |
| Production | Public S3/MinIO endpoint + TLS (`minio_secure=true` when appropriate). |

Also configure:

- `MINIO_BUCKET`, keys, `MINIO_SECURE`

## Notifications and background work

- `NOTIFICATIONS_ENABLED` toggles whether notification tasks are enqueued (see notifications health endpoint).
- Email delivery uses `EMAIL_TRANSPORT=log` by default (no network). Celery worker processes async tasks.

**Frontend impact**: after successful apply or status change, **email may arrive later**; do not block UI on email delivery.

## Security headers and HTTPS

For production:

- Terminate TLS at reverse proxy (nginx, Caddy, cloud LB).
- Consider strict CSP if storing tokens in `sessionStorage`.

This repo does not define frontend hosting — align with your platform (Vercel, Netlify, static S3, etc.).

## Health checks for orchestration

- **API**: `GET /health`
- **Notifications gate**: `GET /api/v1/notifications/health` (includes `notifications_enabled`)

Use `/health` for k8s liveness unless you need the deeper signal.
