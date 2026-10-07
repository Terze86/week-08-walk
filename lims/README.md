# Forensic DNA LIMS

A laboratory information management system built around the laboratory's own casework process. That process is described in [`docs/workflow/LIMS_WORKFLOW_STEPS.md`](docs/workflow/LIMS_WORKFLOW_STEPS.md) and numbered as requirements in [`docs/URS.md`](docs/URS.md).

**Status: Phase 0 (foundations).** The cross-cutting core and the staff/admin console are in place. Casework modules (case registration through disposition) arrive in Phase 1.

## Layout

```
lims/
  backend/            FastAPI + SQLAlchemy + Alembic (Python 3.12+)
    app/core/         cross-cutting core used by every workflow module
    app/modules/      domain modules (identity, admin; casework modules in Phase 1)
    alembic/          migrations (append-only triggers installed here)
    tests/            pytest suite, tagged with URS requirement IDs
  frontend/           React + TypeScript (Vite) workspaces per role
  docs/
    workflow/         the laboratory's workflow description (source of truth)
    URS.md            generated requirements, one ID per workflow step
  tools/              URS generator and traceability matrix
  docker-compose.yml  local stack: postgres, minio, api, worker, web
```

## Core building blocks (`backend/app/core`)

| Module | What it guarantees | Workflow refs |
|---|---|---|
| `audit.py` | Every action is written to an append-only, SHA-256 hash-chained audit trail with actor, time, reason and before/after values. `verify_chain` detects tampering. | WF-19.04, WF-19.06 |
| `db.py` + migrations | `@append_only` tables reject UPDATE, DELETE and TRUNCATE through a Postgres trigger. Corrections are new records. | WF-03.10, WF-11.05, WF-17.10 |
| `workflow.py` | Declarative per-item state machines with role checks, mandatory reasons and guards. Every transition is audited. | WF-04.08, WF-05.07 |
| `sod.py` | Separation-of-duties rules in one reviewable place: independent readers, independent extraction check, designated handover receiver, final sign-off by the assigned technical reviewer, admin ≠ scientist, CODIS scope. | WF-01.04, WF-07.07, WF-03.08, WF-17.07, WF-19.04, WF-01.06 |
| `documents.py` | Versioned documents. An e-signature binds to the exact version's content hash and needs fresh re-authentication; a new version requires every sign-off to be repeated. | WF-05.04–06, WF-17.04–07 |
| `files.py` | Write-once, content-addressed file storage (local for dev, S3 Object Lock for production) with a hash check on every read. | WF-05.03, WF-13.08, WF-17.08 |
| `access.py` | Record-level grants: assignments and CODIS shares, revoked with a reason and never deleted. | WF-01.05, WF-01.06, WF-03.01–02 |
| `ids.py` | Gap-free identifiers and barcode values per type and year (formats are placeholders until the lab confirms them). | WF-02.04, WF-04.04 |
| `jobs.py` | Postgres job queue for printing and delivery. Failed jobs surface to the admin for a retry or resolution, with a reason. | WF-19.03 |
| `auth.py` | OIDC bearer tokens (e.g. Entra ID) mapped to LIMS accounts; dev-header sign-in for development only. Production config refuses dev auth and local file storage. | WF-01.02 |

Domain modules (Phase 1+) use these pieces rather than reimplementing them.

## Running locally

Requirements: Python 3.12+, Node 22, PostgreSQL 16.

```bash
# database
createuser -P lims            # password: lims
createdb -O lims lims && createdb -O lims lims_test

# backend
cd backend
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
export LIMS_DATABASE_URL=postgresql+psycopg://lims:lims@localhost:5432/lims
.venv/bin/alembic upgrade head
.venv/bin/python -m app.seed           # dev accounts: admin1 cs1 cs2 slo1 dlo1 dlo2 rev1 codis1
.venv/bin/uvicorn app.main:app --reload
.venv/bin/python -m app.worker         # background jobs (separate terminal)

# frontend
cd ../frontend && npm install && npm run dev   # http://localhost:5173
```

Or, with Docker: `docker compose up --build`, then open http://localhost:8080.

## Checks

```bash
cd backend
ruff check . && ruff format --check . && mypy app
pytest -q --urs-report ../var/traceability.json     # uses lims_test (rebuilt each run)
python ../tools/traceability.py ../var/traceability.json > ../var/traceability.md
python ../tools/gen_urs.py --check                  # URS.md matches the workflow doc
cd ../frontend && npm run build
```

### Requirement traceability
Tests cite requirements with `@pytest.mark.urs("WF-07.07")`. CI publishes the requirement → test → result matrix as a build artifact, and it becomes the backbone of the IQ/OQ/PQ validation package. A test cites a requirement only when it proves that requirement end to end. Core tests therefore cite only the staff-access, admin and audit requirements that the core already satisfies. Casework requirements are cited by the Phase 1 module tests that wire the core into each step.

## Production notes (for Phase 3)
- The application's database role must **not** own the tables: the owner can disable triggers. Migrations run as an owner role, and the API runs as a role with INSERT/SELECT (plus UPDATE only on mutable tables).
- The S3 bucket must be created with Object Lock enabled; retention is `LIMS_S3_OBJECT_LOCK_DAYS`.
- E-signatures in production need the frontend to request a fresh login (`prompt=login`) and send that ID token as `X-Reauth-Token`.
- Configure through `LIMS_*` environment variables (see `backend/app/core/config.py`).
