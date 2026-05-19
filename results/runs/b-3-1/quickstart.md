# Quickstart: Verifying API Rate Limiting

**Feature**: 001-api-rate-limiting
**Date**: 2026-05-18

---

## Prerequisites

- Service running locally (`uvicorn src.api.main:app --reload`)
- A user created and their `id` known (see step 1 below)

---

## Step 1: Create a test user

```bash
curl -s -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"email": "ratelimit@example.com", "name": "Rate Test"}' | python3 -m json.tool
```

Note the returned `id` (e.g., `1`). Use it as `X-User-Id` in subsequent requests.

---

## Step 2: Confirm rate limit headers on a normal request

```bash
curl -s -i http://localhost:8000/users/1 \
  -H "X-User-Id: 1"
```

Expected response headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: <unix timestamp>
```

---

## Step 3: Exhaust the rate limit (shell loop)

The default limit is 100 req/min. To trigger a 429 quickly during manual testing, temporarily lower the limit or use the following loop (which will hit the limit after 100 iterations):

```bash
for i in $(seq 1 105); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    http://localhost:8000/users/1 -H "X-User-Id: 1")
  echo "Request $i: $STATUS"
done
```

Requests 1–100 return `200`. Requests 101–105 return `429`.

---

## Step 4: Confirm 429 response shape

```bash
curl -s -i http://localhost:8000/users/1 -H "X-User-Id: 1"
# (after quota is exhausted)
```

Expected:
```
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: <timestamp>
Retry-After: <seconds>

{"detail":"rate limit exceeded"}
```

---

## Step 5: Confirm other users are unaffected

```bash
# Create a second user
curl -s -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"email": "other@example.com", "name": "Other User"}' | python3 -m json.tool

# Make a request as user 2 — should return 200 even though user 1 is rate limited
curl -s -i http://localhost:8000/users/2 -H "X-User-Id: 2"
```

---

## Running the test suite

```bash
pytest tests/test_rate_limit.py -v
```
