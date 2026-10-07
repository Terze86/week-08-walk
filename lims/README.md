# Forensic DNA LIMS

A laboratory information management system built around the laboratory's own casework process. That process is described in [`docs/workflow/LIMS_WORKFLOW_STEPS.md`](docs/workflow/LIMS_WORKFLOW_STEPS.md) and numbered as requirements in [`docs/URS.md`](docs/URS.md).

**Status: Phase 1 in progress.**
- **Done:** the cross-cutting core, the staff/admin console, and sections 2–3: case registration, exhibit checks and receipt with the submitter's signature, assignments, and chain of custody (store, retrieve, batch moves with scan checks, receiver-accepted handovers, authorised corrections).
- **Next:** section 4 onward (screening and sampling).

## Open it in your browser (GitHub Codespaces)

You need only a browser and your GitHub account; nothing is installed on your computer.

1. Go to https://github.com/Terze86/week-08-walk.
2. Switch the branch selector (top left, usually showing `main`) to **`ccr-27a8ef5e-bu03qk`**.
3. Click the green **Code** button → **Codespaces** tab → **Create codespace on ccr-27a8ef5e-bu03qk**.
4. Wait for the first build, about 3–5 minutes. It installs everything, creates the database and loads demo data.
5. The LIMS opens in a new browser tab. If it doesn't: open the **PORTS** tab at the bottom of the Codespace and click the globe icon next to **5173 (DNA LIMS)**.
6. Sign in with one of the demo accounts:

| Account | Role |
|---|---|
| `admin1` | LIMS Admin (staff, clients, locations, audit trail) |
| `cs1`, `cs2` | Case Scientist |
| `slo1` | Screening Lab Officer |
| `dlo1`, `dlo2` | DNA Lab Officer |
| `rev1` | Reviewer |
| `codis1` | CODIS Scientist |

**Things to know**
- The address is private to your GitHub account unless you change the port's visibility.
- Demo data only: don't enter real casework.
- Each time you come back, the app restarts automatically. If the page doesn't load, run `bash .devcontainer/start.sh` in the Codespace terminal. Logs are in `/tmp/lims-api.log` and `/tmp/lims-web.log`.
- Codespaces stop after 30 minutes idle and count against your free monthly hours. Delete the Codespace from https://github.com/codespaces when you no longer need it.

## Run it on your Mac

You need Homebrew. If you don't have it, install it from https://brew.sh (one command in Terminal; it asks for your Mac password).

```bash
git clone https://github.com/Terze86/week-08-walk.git
cd week-08-walk
git checkout ccr-27a8ef5e-bu03qk
bash lims/scripts/run-on-mac.sh      # first run installs Python, Node, PostgreSQL (~5–10 min)
```

The LIMS then opens at http://localhost:5173. Sign in with the demo accounts listed above.
- **Stop it:** `bash lims/scripts/stop.sh`
- **Start it again:** rerun `run-on-mac.sh`, which takes seconds after the first time.
- **Get the latest version:** `git pull`, then rerun the script.

With Claude Desktop on your Mac, you can instead ask it to do all of this ("run `lims/scripts/run-on-mac.sh` and open the LIMS"). It can then show the app in its built-in browser while you test together.

## Layout

```
lims/
  backend/            FastAPI + SQLAlchemy + Alembic (Python 3.12+)
    app/core/         cross-cutting core used by every workflow module
    app/modules/      domain modules: identity, admin, reference (clients,
                      locations), items, cases, receipt, custody, work (queues)
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

## Casework so far (sections 2–3)

| Step | Where |
|---|---|
| Register a case (paper or electronic) and its laboratory subcase | `modules/cases` · Cases page |
| Record exhibits; each gets an identifier and barcode | `modules/cases`, `modules/items` |
| Check description, marking and seal; accept, or reject with a reason | exhibit state machine in `cases/service.py` |
| Receipt for selected accepted exhibits, with rejected ones listed separately; capture the submitter's signature; retain the signed record | `modules/receipt` · Receipt page (printable) |
| Refusal, failed signature or other exception, kept for follow-up | receipt `exception` state · My work |
| Assign a Case Scientist; assign or claim an exhibit examination (separate from custody) | access grants · Case page |
| Store, retrieve and batch-move items; every item scanned again before completing | `modules/custody` · Custody page |
| Person-to-person handover accepted only by the designated receiver | `custody.accept_handover` · My work |
| Custody correction requested, then authorised; the original entry is kept | `custody.request_correction` / `decide_correction` |

### Decisions to confirm with the laboratory
These are marked `CONFIRM` in `backend/app/modules/cases/policy.py`:
- **Reception roles:** Case Scientists and Screening Lab Officers register cases, check exhibits and complete receipts.
- **Assigning Case Scientists:** done by Case Scientists or Reviewers.
- **Authorising custody corrections:** done by Case Scientists or Reviewers. An authoriser may request and authorise in one step.
- **Visibility:** casework staff see all cases in their own laboratories. "My work" lists only what is assigned to them. CODIS Scientists and LIMS Admins see no casework.
- **Placeholder formats:** identifiers such as `C2026-000001`, `EX2026-0000001` and `R2026-000001`.

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
.venv/bin/python -m app.seed           # dev accounts admin1 cs1 cs2 slo1 dlo1 dlo2 rev1 codis1,
                                       # demo clients and locations
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
pytest -q --urs-report=../var/traceability.json     # uses lims_test (rebuilt each run)
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
