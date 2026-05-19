# Contract: Rate Limit Response Headers

**Feature**: `001-api-rate-limiting`
**Applies to**: All API responses (every endpoint, every HTTP method)

## Headers Present on Every Response

### `X-RateLimit-Limit`

- **Type**: integer string
- **Value**: The configured maximum number of requests allowed per window for this scope.
- **Example**: `X-RateLimit-Limit: 100`

### `X-RateLimit-Remaining`

- **Type**: integer string, minimum `0`
- **Value**: Number of requests the client may still make in the current window.
  Never goes below `0`, even when the client is rate-limited.
- **Example**: `X-RateLimit-Remaining: 42`

### `X-RateLimit-Reset`

- **Type**: integer string (Unix timestamp, seconds since epoch)
- **Value**: The point in time at which the current window expires and the counter
  resets. Clients may resume at or after this timestamp.
- **Example**: `X-RateLimit-Reset: 1716163200`

## Additional Header on 429 Responses Only

### `Retry-After`

- **Type**: integer string (seconds)
- **Value**: Number of seconds the client MUST wait before retrying.
  Equivalent to `X-RateLimit-Reset - current_unix_time`, rounded up.
- **Example**: `Retry-After: 37`
- **Reference**: RFC 6585, Section 4.

## Invariants

- All four `X-RateLimit-*` headers MUST be present on all responses, including 429s.
- `Retry-After` MUST only appear on 429 responses.
- `X-RateLimit-Remaining` MUST be `0` when `Retry-After` is present.
- `X-RateLimit-Reset` and `Retry-After` MUST be consistent:
  `Retry-After == X-RateLimit-Reset - floor(current_unix_time)`.
