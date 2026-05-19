# Task 3 — Ambiguous

## Prompt (paste verbatim to the agent)

Add rate limiting to the API.

## Acceptance criteria

The point of this task is **how** the workflow handles a one-sentence brief,
not what it ships. Pass / fail is judged on two axes:

1. **Requirements surfacing.** Before writing implementation code, does the
   workflow elicit (or document its own assumptions about) at least four of
   the following?
   - which endpoints are limited (all? only writes? only auth-required?)
   - what the limits are (requests / second / minute / day)
   - per-user vs per-IP vs per-API-key
   - storage backend (in-memory dict? Redis? something else?)
   - what the response looks like when limited (status code, headers, body)
   - what happens on burst (token bucket? fixed window? leaky bucket?)
   - excluded paths (`/health`?)

   The operator records, in the run notes, how many of these were
   surfaced before code was written.

2. **Working implementation.** Whatever scope the workflow settles on must
   actually work end-to-end: hitting the limited endpoint enough times
   returns a `429` (or whatever response the workflow declared) and
   `pytest` passes including new tests for the rate limiter.

- No new third-party dependencies that pull in an external service the
  operator can't easily run locally (Redis-as-a-service is out; an
  in-process token bucket is fine; `slowapi` is fine).
- `/health` should remain unlimited unless the workflow has explicitly
  decided otherwise and documented that choice.

## What this probes

How aggressively each workflow drains ambiguity before coding. Plan Mode
will likely guess and ship; Spec Kit will write a spec; BMAD will run an
Analyst → PM elicitation. The interesting question is whether the extra
ceremony produces a meaningfully better outcome on a deliberately
under-specified task, and what it costs.
