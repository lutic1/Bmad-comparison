# Quickstart: Verifying API Rate Limiting

**Feature**: `001-api-rate-limiting`
**Date**: 2026-05-19

## Prerequisites

```bash
pip install -e ".[dev]"
uvicorn api.main:app --reload
```

The server runs on `http://localhost:8000` by default.

## 1. Verify Rate Limit Headers on Normal Requests

Any request within quota should return the three `X-RateLimit-*` headers:

```bash
curl -s -I http://localhost:8000/health
```

Expected headers in response:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: <unix timestamp>
```

## 2. Verify Per-User Scoping

Two different users have independent counters:

```bash
curl -s -I -H "X-User-Id: 1" http://localhost:8000/health
curl -s -I -H "X-User-Id: 2" http://localhost:8000/health
```

Both should show `X-RateLimit-Remaining: 99` — independent windows.

## 3. Trigger a Rate Limit (429)

Send requests over the limit. With defaults (100 req/60 s) this script
exhausts the quota and triggers a 429:

```bash
for i in $(seq 1 101); do
  curl -s -o /dev/null -w "%{http_code}\n" -H "X-User-Id: 999" http://localhost:8000/health
done
```

The 101st request should return `429`. Verify the body:

```bash
curl -s -H "X-User-Id: 999" http://localhost:8000/health | python3 -m json.tool
```

Expected:
```json
{
  "detail": "Rate limit exceeded",
  "retry_after": 37
}
```

And headers include `Retry-After: 37` (or similar seconds-until-reset value).

## 4. Verify Reset After Window

After the window resets (wait for `Retry-After` seconds), confirm the client
can make requests again:

```bash
sleep <retry_after_value>
curl -s -I -H "X-User-Id: 999" http://localhost:8000/health
```

Expected: `HTTP/1.1 200 OK` with `X-RateLimit-Remaining: 99`.

## 5. Run the Test Suite

```bash
pytest tests/test_rate_limiter.py -v
```

All tests should pass. Run the full suite to check for regressions:

```bash
pytest
```
