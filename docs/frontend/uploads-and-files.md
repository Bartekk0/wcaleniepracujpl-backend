# CV uploads and downloads (presigned MinIO)

The API does **not** accept multipart CV uploads on `POST /applications`. Instead:

1. Candidate requests a **presigned PUT URL** and an **`object_key`**.
2. Browser (or native client) **PUTs the file bytes** directly to object storage.
3. Candidate submits the application JSON including **`cv_object_key`**.

## Presign upload

**Endpoint**: `POST /api/v1/applications/cv-presign`  
**Auth**: Bearer, **candidate** only.

**Request** (`CvPresignRequest`):

```json
{ "filename": "resume.pdf" }
```

**Response** (`CvPresignResponse`) `200`:

| Field | Type | Notes |
|-------|------|--------|
| `object_key` | string | Store this; pass to apply |
| `upload_url` | string | Presigned URL |
| `expires_in_seconds` | int | **3600** (1 hour) in current code |

### PUT file to `upload_url`

- Use **`PUT`** with raw file body (same as typical S3 presigned PUT).
- The MinIO client does not set a forced `Content-Type` in `presigned_put_object` — follow storage/browser defaults; if uploads fail, try explicit `Content-Type: application/pdf` (or detected MIME).

### Object key rules

Built server-side as:

`cv/{candidate_user_id}/{uuid}_{sanitized_filename}`

On apply, `cv_object_key` must:

- Start with `cv/{candidate_user_id}/`
- Be ≤ **512** characters

Otherwise the API returns **`400`** with a validation-style message (`ValueError` paths in `apply_to_job` / `validate_cv_object_key`).

## Submit application with CV

**Endpoint**: `POST /api/v1/applications`  
**Auth**: candidate.

```json
{
  "job_id": 123,
  "cover_letter": "Optional text",
  "cv_object_key": "cv/42/...._resume.pdf"
}
```

`cv_object_key` may be omitted/null if applying without CV (if product allows).

## Presign download

**Endpoint**: `GET /api/v1/applications/{application_id}/cv-download`  
**Auth**: candidate (own application), recruiter (access to job’s company), or admin.

**Response** `200` (`CvDownloadPresignResponse`):

```json
{
  "download_url": "https://...",
  "expires_in_seconds": 3600
}
```

Open `download_url` in a new tab or trigger download via `window.location` / native download API.

**Errors**

| `detail` | Status |
|----------|--------|
| `Application not found.` | 404 |
| `No CV uploaded for this application.` | 404 |
| Permission strings from `PermissionError` | 403 |

## Critical: browser must reach MinIO host

Presigned URLs are generated using **`MINIO_ENDPOINT`** from server settings (`app/storage/minio_client.py`).

In Docker Compose, `.env.example` sets `MINIO_ENDPOINT=minio:9000` — that works **inside** the Docker network but **not** from a browser on the host.

**Production / local SPA checklist**

- Expose MinIO (or S3) on a **public hostname** reachable by the client, **or**
- Put a **reverse proxy** (same origin as frontend) that forwards to MinIO, **or**
- Use a **backend proxy** upload pattern (not implemented here — would require new API routes).

If presigned URLs point to an internal hostname, uploads/downloads will fail from the browser with network errors.

## Security notes for frontend

- Treat `upload_url` / `download_url` as **secrets while valid** — they grant time-limited access.
- Do not log full presigned URLs in production analytics.
- Validate file size **client-side** for UX; **server should still enforce limits** if you extend the API (currently rely on storage/policy).
