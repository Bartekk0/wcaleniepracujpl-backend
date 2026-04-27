# Error handling for API clients

## Response envelope

FastAPI uses the standard Starlette/FastAPI error body:

```json
{ "detail": <string | array | object> }
```

There is **no** global custom error schema in `app/main.py`; behavior is mostly stock **`HTTPException`** plus Pydantic validation.

## `detail` shapes you must support

### 1) String `detail` (most business and auth errors)

Examples:

```json
{ "detail": "Invalid email or password." }
```

```json
{ "detail": "Insufficient permissions." }
```

```json
{ "detail": "Job not found." }
```

**Frontend rule**: if `typeof detail === "string"`, show it as the primary user message (optionally map known strings to localized copy).

### 2) Validation array (typical `422` from Pydantic / `RequestValidationError`)

Example shape (simplified):

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["query", "page_size"],
      "msg": "Input should be less than or equal to 100",
      "input": "200"
    }
  ]
}
```

**Frontend rule**: if `Array.isArray(detail)`, render field errors (use `loc` + `msg`) or flatten to a bullet list.

### 3) Custom `422` with string `detail` (applications status filter)

`GET /api/v1/applications/me?status=bad` returns:

```json
{ "detail": "Invalid status value: bad." }
```

So **`422` is not always an array** — treat **`422.detail`** as **`string | array`**.

## Recommended client normalizer

Pseudocode:

```text
function parseApiError(status, body):
  detail = body?.detail
  if typeof detail == "string":
    return { kind: "message", message: detail, status }
  if Array.isArray(detail):
    return { kind: "validation", fields: detail, status }
  if detail is object:
    return { kind: "structured", raw: detail, status }
  return { kind: "unknown", raw: body, status }
```

## Status code playbook

| Code | When | Client action |
|------|------|----------------|
| **`400`** | Bad input / rule violation not mapped to 404/409 | Show `detail` string; fix form |
| **`401`** | Bad credentials, bad/expired token, wrong token type | If “Access token expired.” → refresh once; else logout |
| **`403`** | Wrong role, inactive account, permission errors | Redirect to “not allowed” or home |
| **`404`** | Missing resource | Show not found; refresh lists if stale |
| **`409`** | Conflict (duplicate email, duplicate application, already moderated, invalid transition) | Show message; refresh entity |
| **`422`** | Validation | Parse array or string `detail` |
| **`204`** | Successful delete job | Expect **empty body** |

## Auth-specific messages (non-exhaustive)

From `app/api/deps.py` and `app/domains/auth/router.py`:

| Message | Typical status | Meaning |
|---------|----------------|---------|
| `Access token expired.` | 401 | Refresh flow |
| `Invalid access token.` | 401 | Logout / re-login |
| `Invalid token type.` | 401 | Sent refresh as access or vice versa |
| `Refresh token expired.` | 401 | Full re-auth |
| `Invalid refresh token.` | 401 | Full re-auth |
| `User account is not activated.` | 403 (login) or 403 (`/users/me`) | Block app until activation |

## Do not rely on `technologie.md` for errors

Some markdown in the repo may mention Redis rate limiting or similar. **HTTP rate limiting is not evident in the FastAPI app layer** at documentation time — do not build UX assuming throttling unless you add it or measure infra-level limits.
