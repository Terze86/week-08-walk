# Plan: Forensic DNA LIMS built from the lab's workflow (LIMS_WORKFLOW_STEPS.md)

## Context
The lab has documented its full casework process in 19 sections, from staff access through case closure (`LIMS_WORKFLOW_STEPS.md`). The goal is a **production** LIMS that enforces that process: role-based workspaces, chain of custody, per-item progression, independent checks and readings, versioned sign-offs, CODIS file exchange, reporting and evidence disposition. All of it needs a complete, tamper-evident audit trail suitable for ISO/IEC 17025 forensic accreditation.

Decisions already made by the user:
- **Platform:** custom web app (not Power Apps, LabWare or Streamlit)
- **Target:** production system
- **Sequencing:** build the *whole workflow thinly first*, then deepen each part

The current repo (`week-08-walk`) holds an unrelated Streamlit course demo and a Power Apps skill. The LIMS will go in a new self-contained top-level `lims/` folder on branch `ccr-27a8ef5e-bu03qk`, so nothing existing is touched. **Recommendation:** move it to its own repo before go-live, because validation, access control and release management are easier that way.

---

## 1. Architecture

| Concern | Choice | Why |
|---|---|---|
| Backend | Python 3.12, **FastAPI**, SQLAlchemy 2, Alembic, Pydantic v2 | Mature and typed, with strong file parsing libraries (openpyxl, pypdf, lxml) for instrument and Excel exchange |
| Database | **PostgreSQL 16** | Transactions, row-level security, triggers that enforce append-only history |
| Frontend | **React + TypeScript (Vite)**, TanStack Query, OpenAPI-generated client | Plate grids, barcode-scan flows and reading-comparison views need a rich client |
| Auth | **OIDC SSO** (Entra ID, since the lab is on M365) + app-side roles and lab assignments | Covers 1.2, "each person signs in using their own account"; disabled accounts are blocked centrally |
| Files | S3-compatible object store (MinIO on-prem) with **object lock / WORM**, SHA-256 content addressing | Original photos, GeneMapper exports, EPGs, CODIS files and issued reports must never change (5.3, 11.5, 13.8, 17.8) |
| Jobs | Postgres-backed job queue + worker process | Label printing, report delivery and email, with failed-job tracking and retry for 19.3 |
| PDFs | WeasyPrint (report render) + pypdf (signature stamping) | Covers 17.8 |
| Labels | ZPL to network Zebra printers (adapter interface so another model can be plugged in) | Covers 2.4 and 4.4 |
| Deploy | Docker Compose (postgres, minio, api, worker, web) → on-prem or GCC hosting | Hosting target to be confirmed |

### Cross-cutting core (build once, use in all 19 sections)
1. **Audit event log** (19.6, 19.4): every command writes `audit_event(actor, time, action, entity, before/after, reason)` in the same transaction. Postgres triggers reject UPDATE/DELETE on audit and history tables.
2. **Corrections, never edits** (3.10, 11.5, 13.8, 16.7, 17.10): a correction is a new record that points to the original. The UI shows the current value plus its history.
3. **Versioned documents + bound sign-offs** (5.5–5.6, 11.7, 17.4–17.7): `DocumentVersion` stores a content hash. `SignOff(version_id, hash, signer, meaning, time)` is valid only for that exact version, so a new version invalidates pending sign-offs.
4. **E-signature**: re-authentication plus a stated meaning ("Reviewed", "Approved", "Independent check"), in the style of 21 CFR Part 11.
5. **State machines** (`core/workflow.py`): declarative transitions with guards. Each transition is audited and requires a reason where configured. State is held **per exhibit or sample**, not per case (4.8, 5.7).
6. **Separation-of-duties guards** (central, unit-tested):
   - Two profile readers must be different Case Scientists (1.4, 11.1).
   - The extraction loader and the independent checker must be different DNA Lab Officers (7.7).
   - Admin and technical review are both required, even when one Reviewer does both (17.4).
   - Final sign-off is done by the assigned technical Reviewer (17.7).
   - Admins cannot alter scientific decisions (19.4).
7. **Authorization**: role → workspace, plus *assignment-scoped* record access (1.5). CODIS Scientists get **explicit per-request shares** of named profile versions and files only, enforced in queries and by Postgres RLS (1.6, 14.3, 15.3).
8. **Item lineage graph**: one `Item` table (exhibit → sample → extract → amplified product). Every item has a barcode, a custody state and a parent link (4.3, 7.11, 9.7).

## 2. Domain modules → workflow sections

`lims/backend/app/modules/<name>/` each holds `models.py`, `schemas.py`, `service.py` (commands with guards), `router.py` and `tests/`.

| Module | Sections | Key entities |
|---|---|---|
| `identity` | 1, 19.1 | User, Role, LabAssignment, AccountStatus |
| `cases` | 2.1–2.3, 18.1–18.4 | Case, Client, Submitter, Officer, Subcase (open/closed/reopened) |
| `receipt` | 2.4–2.11 | Exhibit (accept/reject + reason), Receipt, SignatureCapture, HandoverException |
| `custody` | 3, 7.5, 18.5–18.9 | Location, CustodyMovement (person/location → person/location), BatchMovement, PendingHandover (receiver accepts), CustodyCorrection |
| `assignment` | 3.1–3.3 | Assignment (Case Scientist ↔ subcase; SLO ↔ exhibit exam), kept separate from custody |
| `screening` | 4 | ScreeningRecord, Site, Sample, TestAuthorization |
| `documentation` | 5 | Photo (original immutable + derived edits), Caption, Narrative, DocumentVersion, SignOff |
| `resources` | 6 | Reagent, Lot, Container, Instrument, ResourceCheck, ReleaseDecision, Usage, WithdrawalImpactReview |
| `batches` | 7–10 | Batch (type: extraction, quant, amp, CE), Plate (96-well), Position (sample or control), ReagentUse, IndependentCheck, PositionOutcome, QCReview (separate from batch completion) |
| `profiles` | 11–12 | ReadingUpload (per reader, per run, versioned), Comparison, Discrepancy, ProfileVersion, ProfileIssue, Approval, EPGAttachment, CSReview, RepeatRequest |
| `codis` | 13–15 | CodisRequest (reference, submission or search), ShareGrant, Response (versioned files), Review |
| `interpretation` | 16 | InterpretationWork, TemplateCopy (RMP/CPI), XMLImport (versioned) |
| `reports` | 17 | Report, ReportVersion, AdminReview, TechReview, FinalSignOff, IssuedFile (WORM), Delivery, Amendment |
| `disposition` | 18.5–18.10 | ReturnRequest, CollectorVerification, DisposalAuthorization, DestructionRecord, Hold |
| `admin` | 19 | Locations, reference data, FailedJob triage, AuditViewer, QualityDocLink (SharePoint URL + version) |

`lims/backend/app/integrations/` holds one adapter per file format, each with fixtures from real files:
- `quantstudio5` (setup export + results import) for section 8
- `ce_plate` (3500 plate record) for section 10
- `genemapper_txt` (import + allele-by-allele comparison) for section 11
- `excel_interp` (populate RMP/CPI template, import XML) for section 16
- `zpl_labels`
- `sharepoint_links` (Graph lookup later; manual URL first)

## 3. Frontend workspaces (1.3)
`lims/frontend/src/workspaces/`: `case-scientist/`, `screening/`, `dna-lab/`, `reviewer/`, `codis/`, `admin/`. Each workspace has a "My work" queue driven by assignments and state. Shared components:
- barcode scan input (keyboard-wedge scanners)
- 96-well plate editor
- versioned-document viewer with sign-off panel
- reading-diff table
- signature pad (submitter signature, 2.8)

## 4. Delivery phases

**Phase 0: Foundations (all later phases depend on it)**
- Scaffold `lims/` with docker-compose, CI (ruff, mypy, pytest, eslint, tsc, Playwright), Alembic baseline.
- Build the core pieces from §1: OIDC login, RBAC and assignment scoping, audit log + immutability triggers, file store with hashing, workflow engine, SoD guard library, e-signature, job queue, seed data.
- Write `lims/docs/URS.md`, which numbers every workflow step (`WF-07.07` = section 7, step 7). Tests are tagged with these IDs to give a requirement-to-test **traceability matrix** for validation.

**Phase 1: Thin end-to-end walking skeleton (all 19 sections)**
- Minimal forms and queues so a single case can travel the whole path:
  register → receive (accept/reject) → custody → screen and sample → authorize → photos and sign-off → extraction batch with independent check → quant → amp (GlobalFiler) → CE → two reading uploads + comparison → approval → EPG → CS review → (CODIS request stub) → interpretation XML import → report draft → admin and tech review → sign-off → issue → deliver → close → return or dispose.
- Instrument and Excel files are plain **upload/download with manual linking**, and the parsers come later. Every guard and audit rule is enforced from day one.
- Exit criterion: one Playwright golden-path test that drives this full lifecycle with six different seeded users.

**Phase 2: Deepen, in dependency order**
1. Custody and barcodes: label printing, batch moves with per-item verification (3.7), receiver-acceptance handover (3.8), correction workflow.
2. Resources + plate builder: lot expiry and withdrawal blocking (6.4), usage capture, withdrawal impact review (6.6), multi-case plates (7.3), controls.
3. Instrument adapters: QuantStudio 5 export and import, CE plate record, GeneMapper TXT parsing + automatic comparison, discrepancy UI, re-upload loop (11.5–11.6).
4. Case Scientist decision points: next-test choice from quant (8.6), Yfiler Plus / Fusion 6C selection (9.3), repeat requests linked to earlier profiles (12.5–12.6).
5. Interpretation: auto-populated RMP/CPI Excel templates + XML import validation.
6. Reports: templated PDF, signature stamping, WORM issue, delivery tracking, amendments (17.10) + automatic subcase reopen (18.4).
7. CODIS: share grants, versioned responses, correction loop.
8. Disposition: holds and outstanding-work checks before disposal, destruction evidence.
9. Admin: failed-job console, access-change review, SharePoint quality-doc links.

**Phase 3: Production readiness**
- **Validation**: IQ/OQ/PQ protocols generated from the URS traceability matrix, PQ run on real (anonymised) historical cases, and a validation report signed off by Quality.
- **Security**: threat model, OWASP ASVS L2 review, external pen test, encryption at rest and in transit, session timeouts, least-privilege DB roles.
- **Ops**: backups with tested restore, DR target (RPO/RTO), monitoring and alerting, log retention policy, time synchronisation (NTP) for audit timestamps.
- **Migration**: import open cases, exhibits and custody state from the current system or paper; reconcile counts.
- **Go-live**: training per role, parallel run on live cases, cutover checklist, hypercare.

## 5. Inputs needed from the lab (not needed to start Phase 0–1)
- Example files: QuantStudio 5 setup + results export, 3500 plate record, GeneMapper TXT export, RMP/CPI Excel templates + their XML output, a sample report.
- Formats: case, exhibit, sample and barcode ID formats; label printer model and label sizes.
- Hosting target (on-prem or government cloud), SSO provider/tenant, email relay for report delivery.
- Control types per batch type, QC acceptance rules, retention periods, disposal authorization roles.

## 6. Verification
- **Unit tests** (pytest): every state transition and every SoD guard, positive and negative. Examples: the same officer cannot do the independent check; the same scientist cannot do both readings; an expired lot is rejected; a sign-off on an old version is invalid.
- **Immutability tests**: direct SQL UPDATE/DELETE on audit, history or issued-file tables must fail, and file hashes are re-verified on read.
- **Integration tests**: FastAPI TestClient against a real Postgres (testcontainers) + MinIO.
- **Parser tests**: each adapter is tested against real instrument and Excel files from §5, including malformed-file cases.
- **Access tests**: a CODIS Scientist cannot see unshared profiles; users without an assignment cannot read the case.
- **E2E**: Playwright (Chromium is preinstalled) runs the Phase 1 golden path plus key negative paths (rejected exhibit, failed independent check, reading discrepancy → re-upload → agreement, report amendment → reopen).
- **Traceability report**: CI publishes a URS-ID → test → pass/fail matrix, which feeds directly into validation.

## Immediate next step after approval
Phase 0:
1. Scaffold `lims/` (backend, frontend, docker-compose, CI).
2. Implement the cross-cutting core with tests.
3. Write `docs/URS.md` from the 19 sections.
4. Commit and push to `ccr-27a8ef5e-bu03qk`.
