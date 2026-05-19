# Contract: Rate Limit Error Response

**Feature**: `001-api-rate-limiting`
**Triggered when**: A client exceeds their quota for the current window.

## HTTP Status

`429 Too Many Requests`

## Response Body

```json
{
  "detail": "Rate limit exceeded",
  "retry_after": 37
}
```

### Fields

| Field         | Type    | Description                                      |
|---------------|---------|--------------------------------------------------|
| `detail`      | string  | Always the literal string `"Rate limit exceeded"`|
| `retry_after` | integer | Seconds until the rate limit window resets       |

## Response Headers

All standard `X-RateLimit-*` headers are present (see `rate-limit-headers.md`),
plus `Retry-After` (seconds until reset).

## Consistency with Existing Error Format

This body uses the same `{"detail": "..."}` shape as FastAPI's built-in error
responses (e.g., 404 Not Found, 409 Conflict, 422 Unprocessable Entity), so
clients using generic error handling will work without changes.
The `retry_after` field is additive and does not break existing error parsers.
