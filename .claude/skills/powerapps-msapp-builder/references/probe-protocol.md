# Probe Ladder — Validating the Pipeline With Minimum User Effort

We cannot import-test .msapp files ourselves; the only oracle is the user's Power Apps tenant, reached via email + Jupyter. A failed full app wastes an hour and yields one opaque error code. The ladder isolates failures layer by layer with three ~1-minute imports. Run it the FIRST time this pipeline is used on a tenant, and again after any re-harvest or platform update. Send all three probes in ONE email; the user imports them in order and reports the first failure.

## Probe 0 — Repack the donor unchanged
`harvest_donor.py` keeps the raw donor tree; pack it byte-for-byte (`msapp_compiler.py --repack-donor`).
- **Tests:** zip pipeline, .txt flatten/rebuild round-trip, delivery path.
- **If it fails:** the problem is packing/delivery, not generation. Check zip member paths (forward slashes, no root folder), file completeness, the rebuild FILE_MAP.

## Probe 1 — Recompile the donor's structure from spec
A spec that mirrors the donor: same screen count, same names, one control of each type, all regenerated through the compiler (fresh UIDs, recomputed counts, regenerated YAML/_EditorState).
- **Tests:** the generator's file emission against a structure known to be importable.
- **If it fails (probe 0 passed):** diff the build against the raw donor field-by-field (the old skill's structural-diff method) — the difference IS the bug. Usual suspects: `_EditorState` shape, `ControlCount` inclusion rules, PublishOrderIndex assignment, YAML header shape.

## Probe 2 — Hello-world with NEW structure
Two screens with new names, a label + button per screen, button navigates between them. This is the step the old skill never achieved.
- **Tests:** from-scratch screens — the core new capability.
- **If it fails (probe 1 passed):** screen-count-dependent state exists somewhere we're not updating. Compare probe 1 vs probe 2 builds; suspect Properties.json screen-related fields and _EditorState. If it cannot be cracked in two more probe iterations, fall back to the donor-screen strategy: ask for one donor per screen-count bucket (e.g. donors with 4 and 8 screens), rename screens instead of creating them (renaming is text-level and verified safe), hide unused screens.

## After the ladder passes
Go straight to full apps. Keep probe builds in the repo (`build/probes/`) as known-good references for future diffing.

## Reporting failures
Ask the user for: the exact error code (`ErrOpeningDocument_UnknownError` vs `ErrImport_UnhandledException` vs silent missing screen — they implicate different layers, see the error table in `msapp-internals.md`), and whether the import dialog appeared at all. Every new (cause → fix) pair goes into this file's changelog, not into chat history.
