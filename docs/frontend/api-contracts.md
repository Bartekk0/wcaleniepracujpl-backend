# API contracts

Base URL: **`{API_ORIGIN}/api/v1`**

Unless noted, send **`Content-Type: application/json`** and **`Accept: application/json`**.

## Conventions

### Authentication

Protected routes: header **`Authorization: Bearer <access_token>`**.

### JSON naming

Pydantic v2 responses use **field names as defined in schemas**. Example: job list items expose tags as JSON key **`tags`** (serialization alias from `tag_slugs_list` in `JobOut`).

### Dates

`datetime` fields are ISO-8601 strings with timezone where the DB/driver provides them (see `UserOut`, `JobOut`, etc.).

---

## Health

| Method | Path | Auth |
|--------|------|------|
| `GET` | `/health` | No |

**Response** `200`: `{"status": "ok"}`

*(Note: `/health` is **not** under `/api/v1`.)*

---

## Auth — `/api/v1/auth`

| Method | Path | Body | Success |
|--------|------|------|---------|
| `POST` | `/register` | `RegisterRequest` | `201` `UserOut` |
| `POST` | `/login` | `LoginRequest` | `200` `TokenPair` |
| `POST` | `/refresh` | `RefreshRequest` | `200` `TokenPair` |

See [auth-and-roles.md](auth-and-roles.md) for errors.

---

## Users — `/api/v1/users`

| Method | Path | Auth | Success |
|--------|------|------|---------|
| `GET` | `/me` | Bearer | `200` `UserOut` |

---

## Companies — `/api/v1/companies`

All require **recruiter** role.

| Method | Path | Body | Success |
|--------|------|------|---------|
| `POST` | `` | `CompanyCreateRequest` | `201` `CompanyOut` |
| `GET` | `` | — | `200` `CompanyOut[]` (owner’s companies) |
| `POST` | `/{company_id}/recruiters` | `CompanyRecruiterAddRequest` | `201` `CompanyRecruiterOut` |

**`CompanyCreateRequest`**

| Field | Type | Notes |
|-------|------|--------|
| `name` | string | 1–255 |
| `website_url` | string \| null | max 500 |
| `location` | string \| null | max 255 |
| `description` | string \| null | |

**`CompanyRecruiterAddRequest`**: `{ "recruiter_user_id": <int> }`

**Typical errors**: `403` permission, `404` company not found, `409` duplicate membership.

---

## Jobs — `/api/v1/jobs`

### Public

| Method | Path | Query | Success |
|--------|------|-------|---------|
| `GET` | `` | see below | `200` `JobOut[]` |
| `GET` | `/{job_id}` | — | `200` `JobOut` |

**Public list** only returns jobs with **`moderation_status: "approved"`**.

**`GET /jobs` query parameters**

| Query | Type | Default | Notes |
|-------|------|---------|--------|
| `company_id` | int | — | optional filter |
| `title_query` | string | — | min 1 if set; ilike `%value%` |
| `location` | string | — | min 1 if set |
| `employment_type` | string | — | min 1 if set |
| `page` | int | `1` | ≥ 1 |
| `page_size` | int | `20` | 1–100 |
| `tag` | string[] | — | repeat param: `?tag=python&tag=backend` |

**Tag filter semantics**: multiple `tag` values = **AND** (job must have all listed tag slugs). Maximum **24** tag filters; exceeding yields **422** (validation).

**Sorting**: fixed server-side — **`Job.id` descending** (newer IDs first). No client-controlled sort.

**Pagination response**: **plain JSON array** — no `total`, `has_more`, or cursor. To infer “maybe more”, request `page_size + 1` client-side or accept unknown total.

**`JobOut`** (representative):

| Field | Type |
|-------|------|
| `id` | int |
| `company_id` | int |
| `title` | string |
| `location` | string \| null |
| `employment_type` | string \| null |
| `description` | string |
| `moderation_status` | `"pending"` \| `"approved"` \| `"rejected"` |
| `tags` | string[] (slug list) |
| `created_at`, `updated_at` | datetime |

### Recruiter-only

| Method | Path | Body | Success |
|--------|------|------|---------|
| `POST` | `` | `JobCreateRequest` | `201` `JobOut` |
| `GET` | `/me` | same query as public list | `200` `JobOut[]` |
| `PUT` | `/{job_id}` | `JobReplaceRequest` | `200` `JobOut` |
| `PATCH` | `/{job_id}` | `JobPartialUpdateRequest` | `200` `JobOut` |
| `DELETE` | `/{job_id}` | — | `204` no body |

**`JobCreateRequest`**: `JobWriteBody` + **`company_id`** (int).

**`JobWriteBody` / `JobReplaceRequest`**: `title`, `location`, `employment_type`, `description`, `tags` (array; normalized, max 24, de-duplicated by slug on write).

**`JobPartialUpdateRequest`**: all fields optional but **at least one** must be present (otherwise validation error).

**Business rules**

- Recruiter must be **owner or member** of the job’s company; otherwise **`403`**.
- Unknown company / job returns **`404`** with string `detail`.
- After **PUT/PATCH**, moderation resets to **`pending`** (see backend `jobs/service.py`).

---

## Applications — `/api/v1/applications`

### Candidate

| Method | Path | Body | Success |
|--------|------|------|---------|
| `POST` | `` | `ApplicationCreateRequest` | `201` `ApplicationOut` |
| `POST` | `/cv-presign` | `CvPresignRequest` | `200` `CvPresignResponse` |
| `GET` | `/me` | query `status` optional | `200` `ApplicationOut[]` |

**`ApplicationCreateRequest`**

| Field | Type |
|-------|------|
| `job_id` | int |
| `cover_letter` | string \| null |
| `cv_object_key` | string \| null (max 512) |

**`GET /applications/me?status=`** — optional `status` must be one of: `submitted`, `reviewing`, `rejected`, `accepted`. Invalid value → **`422`** with **`detail` as a string** (not Pydantic list).

### Recruiter

| Method | Path | Query | Success |
|--------|------|-------|---------|
| `GET` | `/jobs/{job_id}` | `status` optional (same enum) | `200` `ApplicationOut[]` |

### Candidate, recruiter, or admin

| Method | Path | Success |
|--------|------|---------|
| `GET` | `/{application_id}/cv-download` | `200` `CvDownloadPresignResponse` |
| `GET` | `/{application_id}/history` | `200` `ApplicationEventOut[]` |

### Recruiter or admin

| Method | Path | Body | Success |
|--------|------|------|---------|
| `PATCH` | `/{application_id}/status` | `ApplicationStatusUpdateRequest` | `200` `ApplicationOut` |

**`ApplicationStatusUpdateRequest`**: `{ "status": "<ApplicationStatus>" }`

**Allowed transitions** (server-enforced):

| From | To |
|------|-----|
| `submitted` | `reviewing` |
| `reviewing` | `accepted`, `rejected` |
| `accepted` | *(none)* |
| `rejected` | *(none)* |

Invalid transition → **`409`** with descriptive string `detail`.

**`ApplicationOut`**: `id`, `job_id`, `candidate_user_id`, `cover_letter`, `cv_object_key`, `status`, `created_at`, `updated_at`.

**`ApplicationEventOut`**: `id`, `application_id`, `actor_user_id`, `from_status`, `to_status`, `note`, `created_at`.

**Apply errors (representative)**

| Condition | Status | `detail` (typical) |
|-----------|--------|---------------------|
| Job missing or **not approved** | `404` | `"Job not found."` |
| Duplicate application | `409` | `"Application already exists for this job."` |
| Bad CV key / validation | `400` | varies |

---

## Admin — `/api/v1/admin`

### Moderation (admin only)

| Method | Path | Body | Success |
|--------|------|------|---------|
| `GET` | `/moderation/jobs` | — | `200` `ModerationJobOut[]` |
| `POST` | `/moderation/jobs/{job_id}/approve` | `ModerationDecisionRequest` | `200` `ModerationActionResponse` |
| `POST` | `/moderation/jobs/{job_id}/reject` | `ModerationDecisionRequest` | `200` `ModerationActionResponse` |

**`ModerationDecisionRequest`**: `{ "note": string \| null }` (note max 2000).

**`ModerationActionResponse`**: `{ "job": ModerationJobOut, "audit_log": AdminAuditLogOut }`

Already moderated → **`409`**.

### Reports

| Method | Path | Auth | Body / query | Success |
|--------|------|------|--------------|---------|
| `POST` | `/reports/jobs/{job_id}` | any activated user | `CreateReportRequest` | `201` `ReportOut` |
| `GET` | `/reports` | admin | `status_filter` optional: `open` \| `resolved` \| `dismissed` | `200` `ReportOut[]` |
| `POST` | `/reports/{report_id}/resolve` | admin | `ReportDecisionRequest` | `200` `ReportActionResponse` |
| `POST` | `/reports/{report_id}/dismiss` | admin | `ReportDecisionRequest` | `200` `ReportActionResponse` |

**`CreateReportRequest`**: `reason` string 1–4000.

**`ReportDecisionRequest`**: `{ "note": string \| null }` (max 2000).

---

## Notifications — `/api/v1/notifications`

| Method | Path | Success |
|--------|------|---------|
| `GET` | `/health` | `200` `{ "status": "ok", "notifications_enabled": <bool> }` |

This does not return user-facing notifications; it reflects config / subsystem readiness. Email dispatch is async (Celery).

---

## Enum reference (JSON values)

| Enum | Values |
|------|--------|
| `UserRole` | `candidate`, `recruiter`, `admin` |
| `JobModerationStatus` | `pending`, `approved`, `rejected` |
| `ApplicationStatus` | `submitted`, `reviewing`, `rejected`, `accepted` |
| `ReportStatus` | `open`, `resolved`, `dismissed` |
