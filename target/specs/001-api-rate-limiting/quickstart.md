# Quickstart: API Rate Limiting

**Feature**: 001-api-rate-limiting
**Date**: 2026-05-19

## Running the service

```bash
# Start with defaults (60 requests per 60-second window)
uvicorn src.api.main:app --reload

# Start with custom limits
RATE_LIMIT_REQUESTS=10 RATE_LIMIT_WINDOW_SECONDS=30 uvicorn src.api.main:app --reload
```

## Verifying rate limit headers

Every response includes rate limit headers:

```bash
curl -si http://localhost:8000/health | grep -i x-ratelimit
# X-RateLimit-Limit: 60
# X-RateLimit-Remaining: 59
# X-RateLimit-Reset: 1716163260
```

## Triggering a 429

With a low limit for manual testing:

```bash
RATE_LIMIT_REQUESTS=3 uvicorn src.api.main:app --reload

# Hit the limit
for i in 1 2 3 4; do curl -si http://localhost:8000/health | head -1; done
# HTTP/1.1 200 OK
# HTTP/1.1 200 OK
# HTTP/1.1 200 OK
# HTTP/1.1 429 Too Many Requests
```

## Per-client isolation

```bash
# Exhaust quota for user 1
for i in $(seq 1 61); do curl -s -o /dev/null http://localhost:8000/health \
  -H "X-User-Id: 1"; done

# User 2 is unaffected
curl -si http://localhost:8000/health -H "X-User-Id: 2" | head -1
# HTTP/1.1 200 OK
```

## Running tests

```bash
pytest tests/test_rate_limit.py -v
```

## Environment variables

| Variable                    | Default | Description                          |
|-----------------------------|---------|--------------------------------------|
| `RATE_LIMIT_REQUESTS`       | `60`    | Max requests allowed per window      |
| `RATE_LIMIT_WINDOW_SECONDS` | `60`    | Window duration in seconds           |

## Validation checklist

- [ ] Normal requests return `X-RateLimit-Limit`, `X-RateLimit-Remaining`,
      `X-RateLimit-Reset` headers
- [ ] Request N+1 (beyond limit) returns HTTP 429 with `Retry-After`
- [ ] After the window expires, the throttled client can request again
- [ ] Exhausting one client's quota does not affect another client's quota
- [ ] `RATE_LIMIT_REQUESTS` env var changes the enforced limit
