# Contract: Rate Limit HTTP Headers

**Feature**: 001-api-rate-limiting
**Date**: 2026-05-19

## Scope

Every HTTP response from the API MUST include rate limit headers.
Throttled responses (HTTP 429) MUST additionally include `Retry-After`
and a structured error body.

## Headers — All Responses

| Header                | Type    | Description                                              |
|-----------------------|---------|----------------------------------------------------------|
| `X-RateLimit-Limit`   | integer | Total request quota for the current window               |
| `X-RateLimit-Remaining` | integer | Requests remaining before throttling kicks in          |
| `X-RateLimit-Reset`   | integer | Unix timestamp (UTC seconds) when the quota window resets |

### Example (normal response)

```
HTTP/1.1 200 OK
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 42
X-RateLimit-Reset: 1716163260
Content-Type: application/json
```

## Headers — Throttled Response (HTTP 429)

Includes all headers above, plus:

| Header        | Type    | Description                                    |
|---------------|---------|------------------------------------------------|
| `Retry-After` | integer | Seconds the client MUST wait before retrying   |

### Example (throttled response)

```
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1716163260
Retry-After: 37
Content-Type: application/json

{"detail": "Rate limit exceeded"}
```

## Constraints

- `X-RateLimit-Remaining` MUST NOT go below `0`.
- `X-RateLimit-Reset` MUST be a Unix timestamp in whole seconds (integer).
- `Retry-After` MUST equal `ceil(window_end - now)` in seconds.
- The middleware MUST NOT process the request body before deciding to
  reject a throttled request.
- Client identity is resolved per the rules in `data-model.md`:
  authenticated clients use their user ID; unauthenticated clients use IP.

## Error Body Schema

```json
{
  "detail": "Rate limit exceeded"
}
```

This matches the FastAPI default `HTTPException` response shape, keeping
error handling consistent with the rest of the service.
