---
name: powerapps-msapp-builder
description: "Generate complete, import-ready Power Apps Canvas .msapp files from scratch — no user-created screens or seed controls per app. Compiles an app spec (screens + controls + Power Fx) into a full .msapp using a one-time harvested donor export, then delivers it as .txt files + a Jupyter rebuild script for restricted (HSA-style) laptops. Use when the user asks to 'create a Power App', 'build an msapp', or requests a new canvas app delivered via text files."
version: 1.0.0
---

# Power Apps .msapp Builder — From-Scratch App Compiler

Successor to `powerapps-solution-design` (V1–V17). That skill could only *clone* controls inside a user-exported .msapp, so the user had to create every screen and one seed control of every type in Studio before the agent could do anything. This skill removes that requirement: after a **one-time donor harvest**, every app is generated fully from scratch — any number of screens, any names, any controls — and the user only imports.

Read `references/why-from-scratch-failed.md` for the root-cause analysis of why the old approach couldn't do this. Short version: an .msapp is ~20 interlocking files with strict cross-file invariants (template registry, control counts, UID/Index sequences, editor state, YAML↔JSON mirrors). The old skill *grafted* changes into Studio exports, so one stale registry file crashed the import with an opaque error. This skill instead *emits every file consistently from one generator* — the same strategy as Microsoft's own MSAppGenerator (.NET), ported to pure Python.

## The workflow

### Phase 0 — One-time bootstrap (once per tenant, EVER)

The only thing that cannot be fabricated is tenant/Studio-generated registry content: `References/Templates.json` (full widget XML per control type), `References/Themes.json`, connection GUIDs in `References/DataSources.json`, and `Header.json` version stamps. These are harvested **once** from any real Studio export ("the donor"):

1. User creates ONE donor app in Studio (or reuses an existing export, e.g. the old "4ControlType app"): blank tablet app, one screen, one of each control type they'll ever want (label, button, text input, dropdown, gallery with items, blank gallery, rectangle, icon), SharePoint data source(s) connected. Export .msapp, send it (as .txt parts if mail blocks it — reverse of the delivery flow).
2. Run: `python scripts/harvest_donor.py donor.msapp --out assets/donor-harvest`
3. Commit `assets/donor-harvest/` to this skill. Done forever — every future app request is Phase 1 onward with zero Studio work.

**Donor freshness rule:** if imports start failing after a Power Apps platform update, ask for one fresh export and re-harvest. Control types not seeded in the donor cannot be generated (the compiler will tell you); harvest a richer donor to unlock them.

**Connections rule:** connections cannot be invented. Lists/connectors present in the donor carry into every generated app. For a new list the user either re-exports a donor with it added, or adds the data source post-import in Studio (Data → Add data — two clicks, no screen building).

### Phase 1 — Requirements → app spec

Gather requirements as before (screens, SharePoint schema, formulas — the Power Fx patterns and gotchas from the old skill still apply; see `references/msapp-internals.md` for the condensed rules table). Then write an **app spec** JSON: screens, controls, properties as raw Power Fx. Format: `references/appspec-format.md`, example: `templates/example-appspec.json`.

### Phase 2 — Compile

```bash
python scripts/msapp_compiler.py --spec appspec.json \
    --harvest assets/donor-harvest --out build/MyApp
```

This emits the extracted tree, runs the invariant verifier (`scripts/verify_msapp.py`), packs `MyApp.msapp`, and produces the delivery bundle: flattened `.txt` files + a self-contained Jupyter rebuild script with the exact FILE_MAP. **Never send a build with verifier errors.** Warnings need judgment — read them.

### Phase 3 — Deliver

Send the `.txt` files + `rebuild_notebook.py` contents (paste script into email body — the user pastes it into a Jupyter cell, edits the folder path, runs, imports the resulting .msapp). Include: change summary, import steps (Import app → From file), "App → ⋯ → Run OnStart" reminder, and the rollback line ("if import fails, your previous app is untouched").

### Phase 4 — First-ever build: run the probe ladder

Because we cannot import-test locally, the FIRST time this pipeline is used against a tenant (or after re-harvest), do NOT send a full app. Send the probes from `references/probe-protocol.md` (repacked donor → recompiled donor-equivalent → tiny 2-screen hello-world). Each is a 1-minute import for the user and isolates exactly which layer fails if one does. After the ladder passes once, go straight to full apps.

## Hard rules (inherited from V1–V17 evidence, enforced by the verifier)

- `copy.deepcopy()` templates; never hand-build `ControlPropertyState` (mixed types: strings + one complex object for Text).
- Templates and registries must come from the SAME harvest — never mix donors.
- `ControlUniqueId` unique app-wide, sequential; screen's Controls file is named `<uid>.json`.
- `Index` is a per-control-type sequence among direct screen children (duplicates within a type silently delete the screen); gallery items keep Index=0. `PublishOrderIndex`: screens 0, non-screen controls one global gapless 0..N-1 DFS sequence. (Measured from the real donor — see `references/msapp-internals.md`.)
- YAML is a delta of the JSON rules (Studio convention); the compiler emits both from one source of truth with values always taken from JSON, so drift is impossible.
- No `%RESERVED%` enum prefixes; no `ZIndex` on rectangles; `App.Width` not hardcoded 1366; lowest-common-denominator Power Fx (no `SortBy()`, no `Navigate(scr, None)`, `.Value` on choice reads, `var`-prefixed variables).

## Fallbacks if a generated app won't import

1. Bisect with the probe ladder (`references/probe-protocol.md`) — find the failing layer, don't guess.
2. Degrade to the old confirmed path: user exports a baseline with seed controls, clone same-app (V8/V9 technique — documented in `references/msapp-internals.md`).
3. YAML paste: modern Power Apps Studio supports copying/pasting controls as YAML directly onto a screen. If the user's tenant has it, you can deliver per-screen YAML snippets they paste — no import at all. Worth one test on their tenant.
