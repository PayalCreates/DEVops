# ADR-0002: FastAPI + React/Vite + PostgreSQL

**Status:** Accepted

## Context
We need a realistic web application (auth, CRUD, analytics) that is quick to build so
most of the effort goes into the platform, and that has good tooling for testing,
OpenAPI docs and type safety.

## Decision
- **Backend:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 (sync), Alembic.
- **Frontend:** React 19 + TypeScript + Vite, no UI framework and no chart library (charts are hand-written SVG).
- **Database:** PostgreSQL 16.

## Alternatives considered
| Option | Why not |
|---|---|
| Django | Heavier and more opinionated; we want explicit control of auth and middleware to demonstrate it. |
| Async SQLAlchemy | More moving parts; sync endpoints run in FastAPI's threadpool and were sufficient (see the performance report). |
| MySQL / MongoDB | PostgreSQL has better constraint support, `pg_dump` custom format and a mature exporter. |
| Recharts / MUI | Each dependency adds to the supply-chain attack surface and bundle size; the charts we need are about 60 lines of SVG. |

## Consequences
+ Automatic OpenAPI docs at `/docs`; strong input validation from type hints.
+ Small frontend bundle (≈88 KB gzipped JS).
− Sync DB access means CPU-heavy work (bcrypt) must be kept off pooled connections. This was found and fixed with load testing.
