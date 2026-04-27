# Authentication and authorization

## Mechanism overview

- **JWT** signed with **HS256**, secret from server env `SECRET_KEY`.
- **Access token** payload includes `sub` (user **email**), `type: "access"`, `exp`.
- **Refresh token** payload: same `sub`, `type: "refresh"`, longer `exp`.
- Protected routes use **`Authorization: Bearer <access_token>`** (see `OAuth2PasswordBearer` in `app/api/deps.py`).

## Token lifetimes (defaults)

From `app/core/config.py` (overridable via env in `.env`):

| Setting | Env variable | Default |
|---------|----------------|---------|
| Access TTL | `ACCESS_TOKEN_EXPIRE_MINUTES` | **30** minutes |
| Refresh TTL | `REFRESH_TOKEN_EXPIRE_MINUTES` | **10080** minutes (= 7 days) |

## Endpoints

All paths below are under **`/api/v1/auth`**.

### Register

`POST /api/v1/auth/register`

**Body** (`RegisterRequest`):

| Field | Type | Constraints |
|-------|------|----------------|
| `email` | string | Valid email |
| `password` | string | 8–128 chars |
| `full_name` | string \| null | max 255 |

**Responses**

- **`201`** — `UserOut` (user profile; **no tokens** returned).
- **`409`** — `{"detail": "User with this email already exists."}`

After register, the client should typically call **login** (or show “check email” if you add verification later).

### Login

`POST /api/v1/auth/login`

**Body** (`LoginRequest`): `email`, `password` (same length rules as register).

**Responses**

- **`200`** — `TokenPair`:
  - `access_token` (string)
  - `refresh_token` (string)
  - `token_type` — always `"bearer"` in practice
- **`401`** — `{"detail": "Invalid email or password."}`
- **`403`** — `{"detail": "User account is not activated."}` when `is_activated` is false

### Refresh

`POST /api/v1/auth/refresh`

**Body** (`RefreshRequest`):

```json
{ "refresh_token": "<refresh_jwt>" }
```

**Responses**

- **`200`** — new `TokenPair` (rotation: new access **and** new refresh).
- **`401`** — expired/invalid refresh, wrong `type`, or unknown user (`detail` messages vary; see `app/domains/auth/router.py`).

### Current user profile

`GET /api/v1/users/me` — requires **Bearer access token**.

Returns `UserOut`: `id`, `email`, `full_name`, `role`, `is_activated`, `created_at`, `updated_at`.

**Errors**

- **`401`** — missing/invalid/expired access token, wrong token type.
- **`403`** — `{"detail": "User account is not activated."}` on protected routes using `get_current_user`.

## Frontend token lifecycle (recommended)

1. **Login success** → persist `access_token` and `refresh_token` (see storage options below).
2. **Attach** `Authorization: Bearer ${accessToken}` on every API call except `/auth/login`, `/auth/register`, `/auth/refresh`.
3. **On `401`** with message **`Access token expired.`** (from `get_current_user`):
   - Call `POST /auth/refresh` with stored refresh token.
   - Replace both tokens in storage.
   - **Retry** the failed request **once**.
4. **On any other `401`** from protected routes → clear session and redirect to login.
5. **Logout** → delete both tokens client-side (no server revoke endpoint in this codebase).

### Storage options (trade-offs)

| Approach | Pros | Cons |
|----------|------|------|
| **Memory only** | XSS cannot exfiltrate after full page reload if paired with strict CSP | Lost on refresh |
| **sessionStorage** | Survives reload within tab | XSS can read |
| **httpOnly cookie** | Not readable from JS | Requires BFF or cookie-capable login flow; **not implemented by this API** |

This API is **Bearer-oriented**; simplest SPA approach is **memory + refresh in sessionStorage** or **both in sessionStorage** for MVP, with awareness of XSS risk.

## Roles (`UserRole`)

Serialized JSON values (lowercase):

| Value | Meaning |
|-------|---------|
| `candidate` | Default for new registrations; can apply and manage own applications |
| `recruiter` | Companies, job CRUD for owned/joined companies, view applications per job |
| `admin` | Moderation queue, reports queue, approve/reject jobs, resolve/dismiss reports |

**Register** creates users via `create_user(..., role=UserRole.CANDIDATE)` by default (`app/services/user_service.py`).

## Permission matrix (HTTP)

| Endpoint pattern | Candidate | Recruiter | Admin |
|------------------|-----------|-----------|-------|
| `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh` | public | public | public |
| `GET /users/me` | ✓ | ✓ | ✓ |
| `GET /jobs`, `GET /jobs/{id}` | public | public | public |
| `POST /jobs`, `GET /jobs/me`, `PUT/PATCH/DELETE /jobs/{id}` | ✗ | ✓ | ✗ |
| `GET/POST /companies`, `POST .../recruiters` | ✗ | ✓ (owner rules in service) | ✗ |
| `POST /applications`, `GET /applications/me`, `POST /applications/cv-presign` | ✓ | ✗ | ✗ |
| `GET /applications/jobs/{job_id}` | ✗ | ✓ | ✗ |
| `PATCH /applications/{id}/status` | ✗ | ✓ | ✓ |
| `GET /applications/{id}/cv-download`, `GET .../history` | ✓ (own app) | ✓ (job access) | ✓ |
| `GET /admin/moderation/jobs`, approve/reject | ✗ | ✗ | ✓ |
| `GET /admin/reports`, resolve/dismiss | ✗ | ✗ | ✓ |
| `POST /admin/reports/jobs/{job_id}` | ✓ (any activated user) | ✓ | ✓ |
| `GET /notifications/health` | public | public | public |

Exact behavior for “own resource” vs “insufficient permissions” is **`403`** with a string `detail` from `PermissionError` or `require_roles`.

## Swagger “Authorize” vs JSON login

`OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")` is used for **Bearer** extraction. The login route expects a **JSON body** (`LoginRequest`), not OAuth2 form `username`/`password`. In Swagger UI you may need to login manually via the `/auth/login` request body, then paste the token into **Authorize**.
