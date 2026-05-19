# Contract: Rate Limit HTTP Interface

**Feature**: 001-api-rate-limiting
**Date**: 2026-05-18
**Scope**: All routes registered under `/users` and `/orders` routers

---

## Response Headers (all requests within quota)

Included on every response from rate-limited routes, regardless of whether the underlying handler succeeds or returns a business error (4xx/5xx).

| Header                  | Type    | Description                                                    | Example           |
|-------------------------|---------|----------------------------------------------------------------|-------------------|
| `X-RateLimit-Limit`     | integer | Maximum requests allowed in one window                        | `100`             |
| `X-RateLimit-Remaining` | integer | Requests remaining in the current window (0 when exhausted)   | `87`              |
| `X-RateLimit-Reset`     | integer | Unix timestamp (seconds) when the current window resets       | `1747612800`      |

---

## 429 Too Many Requests Response

Returned when a client exceeds their quota. The underlying handler is **not** called.

### Status Code

```
429 Too Many Requests
```

### Headers

All three headers above, plus:

| Header          | Type    | Description                                                    | Example |
|-----------------|---------|----------------------------------------------------------------|---------|
| `Retry-After`   | integer | Seconds until the client may retry (same value as reset delta) | `43`    |

### Body

```json
{
  "detail": "rate limit exceeded"
}
```

---

## Unauthenticated Requests

Requests with no `X-User-Id` header are **not** counted or rejected by the rate limiter. They pass through to the route's own auth dependency, which returns `401 Unauthorized` as before. No rate limit headers are added to these responses.

---

## Excluded Endpoints

| Path      | Reason                                              |
|-----------|-----------------------------------------------------|
| `GET /health` | Public health check; not mounted under a router |

---

## Header Accuracy Guarantee

- `X-RateLimit-Remaining` on the response to the N-th request reflects the remaining quota **after** that request is counted (i.e., `limit - N`).
- On a 429 response, `X-RateLimit-Remaining` is `0`.
- `X-RateLimit-Reset` is the Unix timestamp of `window_start + window_seconds`, computed at request time. It is consistent across all responses within the same window for a given client.
