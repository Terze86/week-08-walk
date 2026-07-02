# Why the Previous Skill Could Not Create .msapp Files From Scratch

The old skill (`powerapps-solution-design`, V1–V17) concluded "Generate from scratch — ❌ Impossible — no valid templates without Studio." That conclusion was **empirically honest but analytically wrong**. From-scratch generation is possible — Microsoft's own open-source `MSAppGenerator` (github.com/microsoft/PowerApps-Tooling, `Microsoft.PowerPlatform.PowerApps.Persistence`) does exactly this in .NET. The old skill failed for four compounding reasons, none of which is "the format is impossible."

## 1. It grafted instead of generating

Every failed attempt (V4 new screens, V6 cross-app clone, V13 rectangles into V11) took a **Studio export and surgically inserted foreign material** into it. An .msapp is ~20 files with mutual invariants:

| Invariant | Where it lives | What breaks when violated |
|---|---|---|
| Every `Template.Id`+`Version` used by any control must be registered | `References/Templates.json` (full widget XML per type) | `ErrOpeningDocument_UnknownError` |
| Per-template control counts must match reality | `Properties.json` → `ControlCount` | import crash / corrupt state |
| `ControlUniqueId` unique + coherent app-wide; screen file named `<uid>.json` | `Controls/*.json` | crash |
| `Index` unique per control type among a screen's direct children | `Controls/*.json` | **silent** screen deletion (V16) |
| `PublishOrderIndex` one gapless global sequence over non-screen controls | `Controls/*.json` | crash (V13/V15) |
| Screen list / editor ordering | `Src/_EditorState.pa.yaml` | crash on new screens (V4) |
| YAML mirrors JSON rule-for-rule | `Src/*.pa.yaml` ↔ `Controls/*.json` | crash or lost edits (V12) |
| `StyleName` must exist in theme | `References/Themes.json` | crash |
| `ControlPropertyState` mixed-type array preserved exactly | each control | crash when flattened (pre-V8) |

Grafting one new screen or one foreign control requires updating **all** of these at once. The old skill discovered them one crash at a time (each crash = an email round-trip to a locked-down laptop) and never assembled the complete list. Cloning-same-app "worked" precisely because it left every registry untouched — it was the only move that didn't require knowing the invariants.

## 2. "Cross-app cloning crashes" was a misdiagnosis

V6's crash was attributed to cloning from a *different* app, as if provenance itself were fatal. The actual mechanism: the foreign control's `Template.Version`, `StyleName`, and property state referenced a **registry (Templates.json/Themes.json) that wasn't in the target file**, and `ControlCount` went stale. Same-app cloning works because template + registry are guaranteed consistent — not because Power Apps fingerprints where a control came from. Consequence: cloning from a *bundled, harvested* donor into an app **built from that same donor's registries** is "same-app" in every way that matters. That is what the new compiler does.

## 3. Two files genuinely can't be hand-written — but they never needed to be

`References/Templates.json` (thousands of lines of widget XML per control type) and `References/Themes.json` are machine-generated and version-pinned to the tenant's Studio. The old skill was right that you can't author them by hand. The wrong inference was "therefore Studio must create every app shell." These files are **static per control-type/version** — harvest them once from any real export and reuse them for every app forever. Same for `Header.json` (`DocVersion`/`MinVersionToLoad`) and connection GUIDs in `DataSources.json`.

## 4. No feedback loop, so it converged on the safest ritual

The only test signal was a generic error code (`ErrOpeningDocument_UnknownError` carries zero diagnostics) after an email → Jupyter → import round-trip on the user's restricted laptop. Under those economics, the rational move was to stop exploring and lock in the one confirmed-safe path (user creates structure, agent edits formulas). That's how "we cannot create .msapp files from scratch" hardened from *untested with correct invariants* into doctrine.

## What the new skill changes

1. **Whole-file generation, never grafting.** The compiler emits every file of every app from one in-memory model, so all invariants are computed, not patched: UIDs and Controls filenames allocated together, Index/PublishOrderIndex assigned in one pass, `ControlCount` recomputed, `_EditorState` regenerated, YAML and JSON rendered from the same rule list (drift is structurally impossible).
2. **One-time donor harvest** supplies the un-authorable artifacts (Templates.json, Themes.json, Header.json, connections) and full per-type control templates (deepcopied, mixed-type `ControlPropertyState` intact).
3. **Machine-checked invariants** (`verify_msapp.py`) replace the old prose checklist — every crash cause from V4–V17 is a named check.
4. **Probe ladder** (see `probe-protocol.md`) turns the terrible feedback loop into a bisect: three one-minute imports isolate packing vs. compilation vs. new-structure failures before any real app ships.

## Residual risk (be honest with the user)

New-screen generation has never been *confirmed* to import on this tenant — the old V4 crash was a graft, not a clean generation, so the evidence against it doesn't apply, but positive evidence doesn't exist yet either. That's exactly what probe 3 in the ladder tests. If the platform importer turns out to validate something we can't see (e.g., a checksum file in newer DocVersions), fallback paths are documented in SKILL.md.
