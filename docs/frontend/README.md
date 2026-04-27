# Frontend integration blueprint

This folder contains **framework-agnostic** documentation for building a client application against the **wcaleniepracujpl-backend** FastAPI API.

## Who this is for

- Frontend engineers scaffolding a SPA or multi-page app.
- Full-stack developers wiring a separate frontend repo to this backend.

## Quick facts

| Topic | Detail |
|--------|--------|
| API base path | `{origin}/api/v1` |
| Health (no version prefix) | `GET {origin}/health` |
| Auth | JWT Bearer (`Authorization: Bearer <access_token>`) |
| OpenAPI (when server runs) | `GET /openapi.json`, UI: `/docs`, `/redoc` |
| Real-time | No WebSockets/SSE in this backend; use polling if needed |

## Document map

1. **[Architecture](architecture.md)** — Layers, modules, route slices (candidate / recruiter / admin), API client boundaries.
2. **[Auth and roles](auth-and-roles.md)** — Register, login, refresh, token storage, role matrix, guards.
3. **[API contracts](api-contracts.md)** — Endpoint catalog, query params, bodies, enums, pagination.
4. **[Error handling](error-handling.md)** — `detail` shapes, status codes, client-side normalization.
5. **[Uploads and files](uploads-and-files.md)** — CV presign upload (PUT to MinIO) and presign download.
6. **[State and fetching](state-and-fetching.md)** — Query keys, cache invalidation, optimistic updates.
7. **[Setup, env, deploy](setup-env-and-deploy.md)** — Local/dev URLs, CORS/proxy, MinIO URL reachability, production notes.
8. **[Implementation checklist](implementation-checklist.md)** — Step-by-step from zero to MVP.

## Source of truth in this repo

When in doubt, prefer:

- Routers: `app/api/router.py`, `app/domains/*/router.py`, `app/api/routes/users.py`
- Schemas: `app/schemas/*.py`, `app/domains/*/schemas.py`
- Auth: `app/api/deps.py`, `app/core/security.py`, `app/domains/auth/router.py`

## Known integration caveats

- **CORS** is not configured in `app/main.py` — a browser SPA on another origin needs a **reverse proxy** or explicit CORS on the API.
- **Presigned MinIO URLs** use `MINIO_ENDPOINT` from the server; that host must be **reachable from the browser** for direct PUT/GET.
- **`422` responses**: `detail` may be a **string** (custom handlers) or a **list** (Pydantic validation). Normalize in the client.
