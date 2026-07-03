# msapp-workflow.md — Build importable Power Apps .msapp files from scratch

Portable handoff for another Claude chat / agent. Goal: describe an app in plain
language, compile a complete, import-ready `.msapp`, and deliver it as `.txt`
files + a Python rebuild script for a locked-down (HSA) laptop that only has
Jupyter. Confirmed working on the tenant: three probe imports passed (including
brand-new screens that never existed in Studio), and a real 11-screen app
("Quality Log") was built this way.

---

## 0. What you MUST have in the workspace first

This doc alone is not enough — the method runs a Python compiler that needs the
skill folder. Upload/clone the **`powerapps-msapp-builder`** skill folder so this
layout exists:

```
powerapps-msapp-builder/
├── scripts/
│   ├── harvest_donor.py       # one-time: extract registries/templates from a Studio export
│   ├── msapp_compiler.py      # spec.json -> .msapp (+ .txt bundle + rebuild script)
│   ├── verify_msapp.py        # invariant checker (every crash cause is a named check)
│   └── selftest.py            # end-to-end pipeline smoke test (synthetic donor)
├── assets/donor-harvest/      # COMMITTED. registries + control templates. DO NOT regenerate unless imports break.
│   ├── manifest.json
│   ├── raw/                   # untouched donor tree (Header/Properties/References/Src/Controls)
│   └── templates/             # one JSON per control type: label,button,text,dropdown,gallery,gallery_blank,rectangle,icon,image,screen
├── references/                # msapp-internals.md, appspec-format.md, powerfx-sharepoint-patterns.md, probe-protocol.md, why-from-scratch-failed.md
└── templates/                 # example-appspec.json, probe1/probe2 specs
```

The donor harvest was made once from the user's "4ControlType" Studio export. It
carries the tenant registries (Templates.json, Themes.json), the SharePoint
connection, and a clean template of every control type. **Never hand-edit
Templates.json/Themes.json; never mix templates from two donors.**

Sanity check the environment before building:
```bash
cd powerapps-msapp-builder
python3 scripts/selftest.py            # must end: SELFTEST PASSED
python3 scripts/verify_msapp.py assets/donor-harvest/raw   # must end: OK — 0 errors
```

---

## 1. The core idea (why this works when "from scratch" used to fail)

An `.msapp` is a ZIP of ~20 interlocking files with strict cross-file invariants
(template registry, control counts, unique ControlUniqueId, per-type Index
sequences, global PublishOrderIndex, editor state, YAML↔JSON mirrors). The old
approach *grafted* new controls into a Studio export and crashed on one stale
invariant with an opaque error. This compiler instead **emits every file of the
app from one in-memory model**, so all invariants are computed together and can't
drift. Registries that genuinely can't be fabricated come from the committed
donor harvest.

---

## 2. The build loop (exact commands)

```bash
cd powerapps-msapp-builder

# 1) Write an app spec JSON (see §3). For small apps write it by hand; for big
#    apps write a Python generator that emits it (see §5, the Quality Log).

# 2) Compile: spec -> extracted tree -> verify -> pack .msapp -> .txt bundle
python3 scripts/msapp_compiler.py \
    --spec /path/to/appspec.json \
    --harvest assets/donor-harvest \
    --out /path/to/build

# 3) (optional) re-run the standalone verifier on the extracted tree
python3 scripts/verify_msapp.py /path/to/build/extracted
```

`--out` produces:
- `build/<AppName>.msapp` (the real file),
- `build/extracted/` (the unpacked tree, for inspection/diffing),
- `build/txt/` (every file flattened to `<path with __>.txt`),
- `build/rebuild_notebook.py` (Jupyter script with the exact FILE_MAP).

**Rule: never deliver a build with verifier errors.** Warnings need judgement
(read them). Compiler prints `WARN dropped context-bound template rules ...` when
a gallery-seeded template (rectangle/image/icon) is placed at screen level and
its `ThisItem`/sibling-referencing rules are stripped — that's expected/safe.

Probe ladder (only needed the FIRST time on a new tenant or after re-harvest):
```bash
python3 scripts/msapp_compiler.py --repack-donor --harvest assets/donor-harvest --out build/probe0
python3 scripts/msapp_compiler.py --spec templates/probe1-donor-equivalent.json --harvest assets/donor-harvest --out build/probe1
python3 scripts/msapp_compiler.py --spec templates/probe2-helloworld.json --harvest assets/donor-harvest --out build/probe2
```
Send all three; user imports in order; first failure isolates the layer. On THIS
tenant the ladder already passed — skip it and build real apps directly.

---

## 3. App spec format

One JSON file. All property values are **raw Power Fx strings** (exactly what
you'd type in the Studio formula bar — so string literals need embedded quotes:
`"\"My App\""`). The compiler writes each value to the JSON rules and to the YAML
mirror. Control `type` must be one the donor has: `label, button, text` (text
input), `dropdown, gallery` (browse layout, has seeded item controls),
`gallery_blank` (empty — USE THIS when you add your own gallery children),
`rectangle, icon, image`.

```json
{
  "name": "MyApp",
  "onstart": "Set(varX, true);\nClearCollect(colItems, {Id:1, Name:\"A\"})",
  "screens": [
    {
      "name": "scrHome",
      "properties": { "Fill": "RGBA(245,246,250,1)" },
      "controls": [
        { "type": "rectangle", "name": "bar",
          "properties": { "X":"0","Y":"0","Width":"App.Width","Height":"56","Fill":"RGBA(56,96,178,1)" } },
        { "type": "label", "name": "lblTitle",
          "properties": { "Text":"\"My App\"","X":"24","Y":"12","Width":"400","Height":"32","Size":"19","FontWeight":"FontWeight.Bold","Color":"RGBA(255,255,255,1)" } },
        { "type": "button", "name": "btnGo",
          "properties": { "Text":"\"Open\"","OnSelect":"Navigate(scrTwo, ScreenTransition.None)","X":"24","Y":"90","Width":"160","Height":"40" } },
        { "type": "gallery_blank", "name": "galItems",
          "properties": { "Items":"colItems","TemplateSize":"48","TemplatePadding":"0","X":"24","Y":"150","Width":"800","Height":"500" },
          "children": [
            { "type":"label","name":"gTitle","properties":{ "Text":"ThisItem.Name","X":"8","Y":"6","Width":"400","Height":"24" } }
          ]
        }
      ]
    },
    { "name": "scrTwo", "controls": [ /* ... */ ] }
  ]
}
```

Field notes:
- `onstart` optional; replaces App.OnStart in both JSON and YAML.
- screen `properties` = screen-level rules (e.g. `Fill`).
- control `properties` = any Power Fx rule; existing template rules are
  overwritten, unknown ones appended (Behavior category auto-detected for On*).
- gallery `children` = controls placed inside the gallery's item template.
  Their coordinates are relative to the row; `Index` stays 0 (donor convention).
- Position everything (X/Y/Width/Height) — templates otherwise keep donor
  geometry. Galleries need `TemplateSize` + `TemplatePadding` or render empty.

---

## 4. Delivery (locked-down laptop: Jupyter only, mail scanner blocks archives)

Never send `.msapp` or `.zip` (blocked by content inspection even if renamed).
Send the individual `.txt` files + the rebuild script.

- **Claude Code / this chat:** send the `build/txt/` files (a zip of the txt
  folder is fine to hand over in chat) + `rebuild_notebook.py`. The user emails
  the `.txt` files to their own work address.
- **Hermes (Gmail-capable agent):** email each `.txt` as an individual
  attachment to the work address and paste `rebuild_notebook.py` into the body.
  Attachments must live under `~/.workspace-mcp/attachments/` (`/tmp/` is
  rejected).

User steps (put these in a HOW-TO-IMPORT.txt in the bundle):
1. Save all `.txt` files (incl. `rebuild_notebook.py`) in ONE folder.
2. Open Jupyter, paste `rebuild_notebook.py`, set `FOLDER`, run → `<AppName>.msapp`.
3. make.powerapps.com → Apps → Import canvas app (or Open → Browse) → the .msapp.
4. **App → ⋯ → Run OnStart** (REQUIRED — loads collections; galleries look empty until you do).
5. F5 to play.
6. If import fails, nothing on the tenant changes — report the exact error + step.

---

## 5. Worked example — the "Quality Log" app (big app pattern)

Rebuilt two Excel workbooks (Quality_Log + submission_problems) into ONE
11-screen canvas app. Design decisions the user approved: **M365 identity +
roles** (no passwords), **consolidate identical-schema tabs** into one list with
a "type" column (e.g. 9 method tabs → one Method Log with a Log Type dropdown),
**entry-only first** (approval-email workflow deferred), backed by **in-memory
collections** seeded in OnStart so it imports with ZERO tenant setup.

Because it was ~665 controls, the spec was produced by a **Python generator**
(`gen_quality_log_spec.py`) rather than hand-written — this is the right pattern
for anything non-trivial. The generator:
- defines each log as `{coll, screen, var, group, restrict, fields[], table[]}`,
- emits per screen: blue header + role dropdown, white left **sidebar nav**
  (grouped, live `CountRows` counts, active-screen highlight), a **table-style
  gallery** (grey uppercase header row aligned to `gallery_blank` children +
  coloured status "pill" labels), and a **modal entry form** (full-screen scrim
  rectangle + centred white card, all `Visible = varShowX`; New sets it true,
  Save does `Collect(...)`+false, Cancel false),
- switches the modal to a **3-column layout** when a form has >10 fields so the
  card fits within 768px.

Command used each iteration:
```bash
python3 gen_quality_log_spec.py                         # writes appspec.json
python3 scripts/msapp_compiler.py --spec appspec.json --harvest assets/donor-harvest --out build
```
Result: `11 screens, ~665 controls`, verifier `OK — 0 errors`.

Modal z-order trick: add modal controls LAST in the screen's control list (later
= rendered on top). Order inside the modal: scrim → card → title → field
labels/inputs → Save/Cancel.

---

## 6. What WORKED (measured on the real donor + tenant)

- Whole-app generation from one model — imports cleanly, incl. brand-new screens.
- `copy.deepcopy()` of donor templates preserves the mixed-type
  `ControlPropertyState` (strings + one complex object for `Text`).
- Identity conventions (measured from a real Studio export):
  - ControlUniqueId unique app-wide; App=1, Host=3, screens/controls from 4;
    each screen's Controls file is named `<uid>.json`.
  - **Index** = per-`(Template.Name, VariantName)` sequence among a screen's
    DIRECT children (labels 0,1,2… while a button is 0); gallery items all keep
    Index=0.
  - **PublishOrderIndex** = App/Host/screens all 0; non-screen controls form ONE
    global gapless 0..N-1 sequence.
- Gallery anatomy: item controls are SIBLINGS of the internal `galleryTemplate`
  node (Parent = the gallery), NOT nested inside it. Use `gallery_blank` when you
  add your own children (the `gallery` type carries donor sample items).
- YAML is an alphabetized DELTA of the JSON rules (Studio writes ~8 of 39 label
  props); the compiler renders both from one rule list so they can't drift.
- `ScreenTransition.None` / `.Fade` are fine; consolidation via a Category/Agency
  dropdown works; collections give persistence-free demos.

## 7. What FAILED / gotchas (each is now enforced or handled)

- **ZIndex on screen-level rectangles** — donor rectangle template comes from
  inside a gallery and inherits `ZIndex=6`, which renders header bars ON TOP of
  their own labels. The compiler now STRIPS ZIndex on screen-level rectangles.
  (Verifier warns if any remains.)
- **Cross-app / from-scratch grafting** (the old method) → `ErrOpeningDocument_UnknownError`.
  Fixed by whole-file generation from the single donor harvest.
- **Duplicate Index within a type at screen level** → screen silently vanishes on
  import (no error). Verifier checks this.
- **PublishOrderIndex gaps** → `ErrOpeningDocument_UnknownError`. Verifier checks.
- **Studio zips use backslash paths** (`Controls\4.json`); harvester normalizes.
  Packing with forward slashes is confirmed importable.
- **`%RESERVED%`** legitimately appears in Templates.json/Themes.json — only a
  defect inside Controls/ or Src/ (verifier scopes the check there).
- Power Fx floor for this tenant: no `SortBy`; `Navigate(scr)` or
  `Navigate(scr, ScreenTransition.Fade)` (never `Navigate(scr, None)`); `.Value`
  on SharePoint choice reads and `{Value:"…"}` on writes; `var`-prefix all
  variables (`FormMode`, `SelectedEntry`, `Text`, `Value`… are reserved);
  `Set(varX, Patch(...))` for saves; include ALL required fields when
  `Patch(List, Defaults(List), …)`; no `Set()` inside `ForAll`; no
  `ConfirmDialog.Show()` (doesn't exist). Full list:
  `references/powerfx-sharepoint-patterns.md`.

## 8. Error → cause → fix (for import failures reported by the user)

| Error on import | Cause | Fix |
|---|---|---|
| `ErrOpeningDocument_UnknownError` | registry/identity inconsistency | re-run `verify_msapp.py`; check Index/PublishOrderIndex, template registration |
| `ErrImport_UnhandledException` | editor-state / zip layout | check `_EditorState.pa.yaml` ScreensOrder, zip member paths |
| screen missing, no error | duplicate Index within a type | fix Index allocation (verifier catches) |
| gallery empty | missing TemplateSize/TemplatePadding, or OnStart not run | set both; App → ⋯ → Run OnStart |
| rectangle covers text | ZIndex>0 on a screen rectangle | remove it (compiler now auto-strips) |
| `SortBy: unknown` / `Navigate: None` | old Power Fx | strip SortBy; 1-arg Navigate |
| red squigglies on collections | OnStart not run yet | App → ⋯ → Run OnStart |

## 9. Next steps not yet done (for context)

- Wire SharePoint lists (consolidated Method Log + specialised + Users + Emails)
  so data persists, then migrate history (e.g. ~2,646 strange-peaks rows) via a
  separate Excel→SharePoint import — NOT part of the .msapp.
- Add the "Send for Approval" email workflow (Office 365 Outlook connector +
  Emails audit list).
- Connections can't be fabricated in the .msapp: the donor's SharePoint
  connection carries over; a NEW list is added post-import in Studio
  (Data → Add data) or by re-harvesting a donor that already has it.
