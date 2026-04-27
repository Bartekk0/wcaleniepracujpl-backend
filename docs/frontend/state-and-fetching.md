# State management and data fetching

This document is **framework-agnostic**: apply with TanStack Query, RTK Query, SWR, Apollo-like patterns, or hand-rolled `fetch` + stores.

## Principles

1. **Server is source of truth** — no HTTP caching headers were added in the explored FastAPI app; assume data can change any time.
2. **No WebSockets** — refetch on interval, on window focus, or after mutations.
3. **Lists lack totals** — job list pagination has no `total_count`; design UI without “page X of Y” unless you add a backend field later.

## Suggested query key structure

Namespace keys by domain and include stable IDs:

| Resource | Key pattern | Example |
|----------|-------------|---------|
| Current user | `["me"]` | — |
| Public jobs | `["jobs", "public", query]` | include serialized filters + page |
| Recruiter jobs | `["jobs", "me", query]` | — |
| Job detail | `["jobs", jobId]` | number |
| Companies | `["companies"]` | — |
| My applications | `["applications", "me", status]` | status or `"all"` |
| Job applications | `["applications", "job", jobId, status]` | recruiter |
| Application detail (if you add endpoint later) | N/A | currently compose from list |
| CV download URL | `["applications", id, "cv-download"]` | short TTL — don’t cache long |
| Admin moderation queue | `["admin", "moderation", "jobs"]` | — |
| Admin reports | `["admin", "reports", statusFilter]` | — |

## Cache invalidation map

| User action | Invalidate / refetch |
|-------------|----------------------|
| Login / logout | All protected queries; clear keys |
| Register | Optional: nothing (user not logged in) |
| Create job | `["jobs", "me", ...]`, `["admin", "moderation", "jobs"]` |
| Update job (PUT/PATCH) | `["jobs", jobId]`, `["jobs", "me", ...]`, public list (job may disappear from public until re-approved) |
| Delete job | Remove `["jobs", jobId]`; refetch lists |
| Admin approve/reject job | `["admin", "moderation", "jobs"]`, `["jobs", ...]`, `["jobs", jobId]` |
| Submit application | `["applications", "me", ...]`; optionally `["applications", "job", jobId, ...]` for recruiters |
| Change application status | Both candidate and recruiter views for that `job_id` / `me` |
| Submit job report | `["admin", "reports", ...]` for admins |

## Optimistic updates

| Operation | Safe for optimistic UI? | Notes |
|-----------|-------------------------|--------|
| PATCH job | Risky | Moderation flips to `pending`; server is canonical |
| PATCH application status | Risky | Strict transition graph; wait for server |
| POST application | No | Use pending button + refetch on success |

Prefer **pessimistic** flows for writes that change moderation or legal-ish state.

## Presigned URL handling

- **Do not** store `upload_url` / `download_url` in global cache like normal REST entities.
- Treat them as **ephemeral** (≈ 1 hour). Regenerate on demand.

## Concurrent requests and refresh

If implementing **token refresh**:

- Serialize refresh so **only one** refresh runs if multiple requests fail with expired access at once (mutex / single-flight).
- Queue failed requests during refresh, then replay with new access token.

## Polling guidelines (optional)

| View | Interval suggestion |
|------|---------------------|
| Admin moderation queue | 15–60s or manual refresh |
| Recruiter applications inbox | 30–120s or on focus |
| Public job board | on navigation + pull-to-refresh |

Adjust for scale and UX; backend has no push channel.

## Derived UI state

- **“Published” to candidates** means job `moderation_status === "approved"` **and** apply will succeed.
- Recruiter sees **`pending`** after edits — show banner “Awaiting moderation”.
