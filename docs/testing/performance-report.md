# Performance & bottleneck analysis report

> All numbers below come from real Locust runs performed while building this repository.
> Raw CSV and HTML reports are in `docs/evidence/load-tests/`.

## Test environment (be precise about what was measured)
| Item | Value |
|---|---|
| Host | Linux sandbox, **2 vCPU**, ~7 GB RAM, shared by the load generator, the API and the DB |
| API | FastAPI under uvicorn, **1 worker**, run directly (not in a container), port 8000 |
| DB | PostgreSQL 16 (local), sample data + accumulated load-test data |
| Load generator | Locust 2.47, same host |
| Scenario | `load-testing/locustfile.py`: each virtual user registers once, then a mix of list (10), dashboard (5), filter (4), create (3), update (2), delete (1), health (1) |

Because the generator and the system under test share 2 vCPUs, the absolute numbers are
conservative. On your laptop, re-run against Compose (`http://localhost:8080`) and record
the results in `docs/evidence/`.

## 1. Baseline — 25 users, spawn 5/s, 2 min
| Metric | Result | SLO | |
|---|---|---|---|
| Requests | 2,405 | | |
| Throughput | 20.2 req/s | | |
| Failures | **0 (0.00 %)** | < 0.5 % | ✅ |
| p50 / p95 / p99 (all) | 10 / **24** / 600 ms | p95 < 300 ms | ✅ |
| p95 `GET /tasks` | 15 ms | | |
| p95 `GET /analytics/summary` | 24 ms | | |
| p95 `POST /auth/register` | 940 ms | | expected: bcrypt cost 12 |

The p99 of 600 ms is entirely registration requests (25 bcrypt hashes during spawn-up).

## 2. Stress — 100 users, spawn 10/s, 90 s: **bottleneck found**
| Metric | Before fix |
|---|---|
| Requests | 182 |
| Throughput | **2.7 req/s** |
| Failures | **72 (39.6 %)**, HTTP 500 |
| p50 / p95 | 27,000 / 59,000 ms |

**Diagnosis**
1. The backend log showed 112 occurrences of
   `QueuePool limit of size 5 overflow 10 reached, connection timed out, timeout 30.00`.
2. Code review of `/auth/register` and `/auth/login` showed that a pooled DB connection was
   checked out (first `SELECT`) **before** the ~250 ms bcrypt computation and held during it.
3. With 100 users registering in 10 s, 40 threadpool workers competed for 15 connections
   while doing CPU work. The pool drained, every other request waited 30 s, and then returned 500.

This is a classic *resource held across slow work* bottleneck: CPU-bound work was
serialising access to an I/O resource.

## 3. Fixes (one at a time, re-measured after each)
| # | Change | File |
|---|---|---|
| F1 | Hash the password **before** opening the DB transaction in `register`; in `login`, read the user, end the transaction (`rollback()` returns the connection), *then* run bcrypt | `app/api/routes/auth.py` |
| F1 | `pool_timeout=5` and a handler that maps pool timeouts / DB errors to **503 + Retry-After** instead of a 30 s hang then 500 | `app/db/session.py`, `app/main.py` |
| F2 | Cap concurrent bcrypt operations at the CPU count (`BoundedSemaphore`), so CPU work stops starving the threads that hold connections | `app/core/security.py` |
| — | Regression test: pool exhaustion must return 503 | `tests/integration/test_platform.py` |

## 4. Results (same 100-user stress profile)
| Metric | Before | After F1 | After F1+F2 | Change |
|---|---|---|---|---|
| Requests completed | 182 | 3,636 | **4,454** | 24× |
| Throughput | 2.7 req/s | 40.8 req/s | **50.0 req/s** | 18.5× |
| Failure ratio | 39.56 % | 1.93 % | **0.67 %** | −98 % |
| Error type | 500 (30 s hang) | 503 (fast) | 503 (fast) | fail-fast |
| p50 | 27,000 ms | 13 ms | **11 ms** | |
| p95 (all) | 59,000 ms | 5,200 ms | **170 ms** | within 300 ms SLO |
| p95 `GET /tasks` | 59,000 ms | 34 ms | **23 ms** | |
| p95 `POST /auth/register` | 59,000 ms | 14,000 ms | 12,000 ms | still CPU-bound |

## 5. Interpretation and remaining limits
- Read and write endpoints are now fast under 4× the baseline load (p95 23 ms for listing).
- The remaining 0.67 % failures and slow registrations all come from the **registration burst**:
  100 bcrypt hashes in 10 s need roughly 25 CPU-seconds on a 2-vCPU host that is also running
  Locust and PostgreSQL. This is intentional work-factor cost (the security/performance trade-off),
  not a defect.
- **Scaling answer:** this is CPU-bound and stateless, so scale horizontally. The HPA scales
  backend pods at 70 % CPU, and each pod brings its own CPU budget and connection pool.
  Keep `replicas × (pool_size + max_overflow)` below PostgreSQL's `max_connections` (100).
- Alternatives considered: lowering the bcrypt cost (rejected, weakens password storage);
  argon2id with tuned memory cost (future); async endpoints (doesn't help CPU-bound hashing).

## 6. How to reproduce
```bash
locust -f load-testing/locustfile.py --host http://localhost:8080 --headless -u 25  -r 5  -t 2m  --csv results/baseline
locust -f load-testing/locustfile.py --host http://localhost:8080 --headless -u 100 -r 10 -t 90s --csv results/stress
```
Watch Grafana during the run: the **p95 latency by route**, **in-flight requests** and
**PostgreSQL connections** panels show exactly the pattern described above.
