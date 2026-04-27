# Frontend implementation checklist

Use this as a **linear** backlog from empty repo to MVP against this backend.

## Phase 0 — Project setup

- [ ] Choose stack (React/Vue/Svelte/etc.) and TypeScript (recommended).
- [ ] Configure **`PUBLIC_API_BASE_URL`** (or equivalent) pointing at running backend.
- [ ] Add **dev proxy** so browser calls same origin in development (avoid CORS pain).
- [ ] Optional: codegen from **`/openapi.json`** when server is up.

## Phase 1 — HTTP client

- [ ] Implement `apiClient.request(method, path, { query, body, token })`.
- [ ] Prefix all business calls with **`/api/v1`**.
- [ ] Attach **`Authorization: Bearer`** when access token exists.
- [ ] Implement **`parseApiError`** handling `detail` as **string OR array** (see [error-handling.md](error-handling.md)).
- [ ] Implement **refresh single-flight** on `401` + `"Access token expired."` then retry once.

## Phase 2 — Auth UX

- [ ] Screens: **Register**, **Login** (and optional **Logout** in nav).
- [ ] `POST /api/v1/auth/register` → show success → navigate to login.
- [ ] `POST /api/v1/auth/login` → store `TokenPair`.
- [ ] `GET /api/v1/users/me` on app boot when token exists → hydrate `user.role`, `is_activated`.
- [ ] Gate routes: block app or show message when `is_activated === false` and API returns **403** on `/users/me`.
- [ ] Role-based route groups: **candidate**, **recruiter**, **admin** (see [auth-and-roles.md](auth-and-roles.md) matrix).

## Phase 3 — Public job board

- [ ] `GET /api/v1/jobs` with query builder for `page`, `page_size`, filters, repeated `tag`.
- [ ] UX: explain **AND** semantics for multiple tags; cap UI at **24** tags to match server.
- [ ] `GET /api/v1/jobs/{id}` job detail page.
- [ ] Handle **`404`** as true missing **or** not approved (same message for apply path).

## Phase 4 — Candidate flows

- [ ] Apply form: `job_id`, optional `cover_letter`, optional CV.
- [ ] CV pipeline:
  - [ ] `POST /api/v1/applications/cv-presign`
  - [ ] `PUT` file to `upload_url`
  - [ ] `POST /api/v1/applications` with `cv_object_key`
- [ ] Verify MinIO URL hostname works from browser (fix `MINIO_ENDPOINT` / proxy if not).
- [ ] `GET /api/v1/applications/me` with optional `status` filter; handle **string** `422` for bad status.
- [ ] `GET /api/v1/applications/{id}/history` timeline UI.
- [ ] `GET /api/v1/applications/{id}/cv-download` → redirect to `download_url`.

## Phase 5 — Recruiter flows

- [ ] `POST /api/v1/companies`, `GET /api/v1/companies`.
- [ ] `POST /api/v1/companies/{id}/recruiters` for inviting co-recruiters by `recruiter_user_id`.
- [ ] `POST /api/v1/jobs` with `company_id` and job body.
- [ ] `GET /api/v1/jobs/me` dashboard (show `moderation_status`).
- [ ] `PUT/PATCH/DELETE /api/v1/jobs/{id}` with permission error UX (**403** / **404**).
- [ ] `GET /api/v1/applications/jobs/{job_id}` inbox with optional status filter.
- [ ] Recruiter cannot use candidate-only endpoints — hide/disable based on `user.role`.

## Phase 6 — Admin flows

- [ ] `GET /api/v1/admin/moderation/jobs` queue.
- [ ] Approve / reject: `POST .../approve` and `POST .../reject` with optional `note`.
- [ ] Reports: `GET /api/v1/admin/reports?status_filter=...`
- [ ] Resolve / dismiss: `POST .../resolve`, `POST .../dismiss` with optional `note`.
- [ ] Handle **`409`** for already moderated / already handled reports.

## Phase 7 — Cross-cutting

- [ ] **Report job** (any logged-in user): `POST /api/v1/admin/reports/jobs/{job_id}` with `reason`.
- [ ] **Notifications health** (ops/debug): `GET /api/v1/notifications/health`.
- [ ] Global **`/health`** indicator for “API up” (optional).

## Phase 8 — Polish

- [ ] Loading and empty states for unpaginated totals (jobs list).
- [ ] Form validation aligned with Pydantic limits (password length, report reason length, etc.).
- [ ] Accessibility for auth forms and tables.
- [ ] E2E tests against docker-compose stack (smoke: login → list jobs → apply).

## Done criteria

- All personas can complete their **primary loop** without reading Python source:
  - Candidate: browse → apply (with/without CV) → see application list.
  - Recruiter: create company → post job → see moderation state → see applications after approval.
  - Admin: moderate jobs → handle reports.
