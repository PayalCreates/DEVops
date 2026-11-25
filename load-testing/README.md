# Load & performance testing (Locust)

## Profiles

| Profile | Users | Spawn rate | Duration | Purpose |
|---|---|---|---|---|
| smoke | 5 | 5/s | 30 s | Script sanity check |
| baseline | 25 | 5/s | 3 min | Normal load reference numbers |
| stress | 100 | 10/s | 5 min | Find the knee of the latency curve |
| soak | 25 | 5/s | 30 min | Memory leaks, connection-pool exhaustion |

## Run

```powershell
# Windows (Python venv)
pip install locust==2.47.0
locust -f load-testing/locustfile.py --host http://localhost:8080 --headless -u 25 -r 5 -t 3m `
  --csv load-testing/results/baseline --html load-testing/results/baseline.html
```

```bash
# Linux / WSL — or the web UI via Compose: docker compose --profile loadtest up -d locust  → http://localhost:8089
./load-testing/run.sh baseline
```

The run **fails (exit 1)** if p95 > 300 ms or failures > 1 % — the same targets as the
SLOs in `docs/sre/slos.md`, so a load test is a direct SLO check.

## Bottleneck analysis checklist

1. Watch the Grafana dashboard during the run: p95 by route, in-flight requests, DB connections.
2. Identify the slowest route in the Locust stats (`*_stats.csv`).
3. Correlate: CPU-bound (container CPU at limit) vs I/O-bound (DB time) vs pool-bound
   (in-flight climbs while CPU is idle → SQLAlchemy pool too small).
4. Change **one** thing, re-run the same profile, compare CSVs.
5. Record before/after in `docs/testing/performance-report.md`.

Results from the run performed while building this repo are in
`docs/testing/performance-report.md`.
