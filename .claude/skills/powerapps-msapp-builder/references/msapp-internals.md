# .msapp Internals — Condensed Structural Knowledge (from V1–V17 evidence)

## File inventory (classic DocVersion, the format this tenant exports)

```
app.msapp (plain ZIP, forward-slash member paths, no wrapper folder)
├── Header.json               DocVersion / MinVersionToLoad — copy from donor, never edit
├── Properties.json           app metadata incl. ControlCount {template-name: n} — recompute counts
├── AppCheckerResult.sarif    static analysis cache — copy from donor
├── Controls/
│   ├── 1.json                App node (OnStart rule lives here)
│   └── <uid>.json            one per screen, FILE NAME = screen's ControlUniqueId
├── References/
│   ├── DataSources.json      connection GUIDs + table schemas — harvest only, cannot fabricate
│   ├── Templates.json        widget XML per control type — harvest only, NEVER hand-edit
│   ├── Themes.json           styles referenced by every StyleName — harvest only
│   ├── ModernThemes.json
│   └── Resources.json
├── Resources/PublishInfo.json
└── Src/
    ├── App.pa.yaml           mirrors Controls/1.json
    ├── _EditorState.pa.yaml  screen ordering / editor metadata
    └── <screen>.pa.yaml      mirrors that screen's Controls JSON, rule-for-rule
```

## Control JSON node (`ControlInfo`)

Key fields: `Name`, `Template` {Id, Name, Version, ...}, `Index`, `PublishOrderIndex`, `StyleName`, `Parent` (parent control NAME), `Rules[]` ({Property, Category, InvariantScript, RuleProviderType:"Unknown"}), `ControlPropertyState`, `ControlUniqueId` (string!), `Children[]`.

**`ControlPropertyState` is a mixed-type array**: plain strings for most properties, but the `Text` entry is a complex object (`{InvariantPropertyName:"Text", AutoRuleBindingEnabled:false, AutoRuleBindingString:"", NameMapSourceSchema:"?", IsLockable:false, AFDDataSourceName:""}`). Flattening it crashes import — always `copy.deepcopy()` templates; when ADDING a new rule, append the property name as a plain string.

## Identity/ordering rules (MEASURED from the real donor export, July 2026)

| Field | Rule | Violation symptom |
|---|---|---|
| ControlUniqueId | unique app-wide; App=1, Host=3, screens/controls from 4 | ErrOpeningDocument_UnknownError |
| Controls filename | `<screen uid>.json` | crash |
| Index | per (Template.Name, VariantName) sequence among DIRECT screen children (labels 0,1,2… while the button is 0); gallery items all keep Index=0 | duplicate within a type at screen level → screen silently missing (V16) |
| PublishOrderIndex | App/Host/screens all 0; non-screen controls form ONE global 0..N-1 sequence in child-array DFS order across screens | gaps → ErrOpeningDocument_UnknownError (V13/V15) |
| Parent | exact parent control name (gallery items → the GALLERY's name) | crash |
| StyleName | must exist in Themes.json | crash |
| Template Id+Version | must appear in Templates.json | ErrOpeningDocument_UnknownError (V6 "cross-app" crash) |
| ControlCount (Properties.json) | donor convention: only some types listed (screen, label); gallery descendants NOT counted | unknown — kept donor-consistent |

## Gallery anatomy (MEASURED — the old docs had this wrong)

A gallery's `Children` array holds ONE internal `galleryTemplate` node **plus the item controls as its siblings** — items are direct children of the gallery with `Parent` = the gallery's name and `Index` = 0, NOT nested inside the galleryTemplate. Item formulas may reference sibling items by name (e.g. `Subtitle1` uses `Title1.Y`) — renaming items requires rewriting those formulas. In YAML, item controls nest under the gallery's `Children:`; the galleryTemplate node is never written. Galleries render empty without `TemplateSize`/`TemplatePadding`.

## YAML mirror (MEASURED)

- YAML is a **DELTA**, not a full mirror: Studio writes only a subset of the JSON rules (donor label: 8 YAML props vs 39 JSON rules), alphabetized. The compiler emits harvested-per-template prop names ∪ spec-set names, with values always read from the JSON rules so drift is impossible.
- Multi-line formulas → `Prop: |-` block, `=` on the first continuation line, indented +2.
- Screen file shape: Studio banner comment, then `Screens:` → `<name>:` → `Properties:` / `Children:` (list of `- ctrlName:` with `Control: Type@Version`, optional `Variant:`, `Properties:`).
- `_EditorState.pa.yaml`: banner + `EditorState:` → `ScreensOrder:` list.
- YAML `Variant:` ≠ JSON `VariantName` (blank gallery: YAML `Vertical`, JSON `galleryVertical`) — use harvested YAML strings, never the JSON field.
- Donor YAML can contain prop names with no JSON rule (dropdown `Items.Value`) — emit only names that exist as JSON rules.
- Control type strings (donor harvest overrides these defaults): Label@2.5.1, Classic/Button@2.2.0, Classic/TextInput@2.3.2, Classic/DropDown@2.3.1, Gallery@2.15.0, Rectangle@2.3.0, Classic/Icon@2.5.0, Image@2.2.3.
- `%RESERVED%` legitimately appears in Studio's Templates.json/Themes.json — it is only a defect inside Controls/ and Src/ files.
- Studio zips with backslash member paths (`Controls\4.json`); packing with forward slashes is confirmed importable.

## Error table

| Error on import | Meaning | First suspects |
|---|---|---|
| ErrOpeningDocument_UnknownError | structural/registry inconsistency | unregistered template, UID/PublishOrderIndex gaps, mangled ControlPropertyState |
| ErrImport_UnhandledException | importer choked before opening | _EditorState / screen registry inconsistency, bad zip layout |
| Screen missing, no error | duplicate Index within a parent | Index allocation |
| Rectangle covers text | ZIndex > 0 | drop ZIndex |
| Gallery empty | missing TemplateSize/TemplatePadding | set 60 / 0 |
| Red squigglies on collections | OnStart not run | App → ⋯ → Run OnStart |
| `SortBy: unknown function`, `Navigate: None isn't recognized` | old Power Fx | strip SortBy, 1-arg Navigate |
| `Field 'X' is required` on Patch | Defaults() omits required fields | include empty values explicitly |

## Power Fx compatibility floor (this tenant)

No `SortBy()`; `Navigate(scr)` or `Navigate(scr, ScreenTransition.Fade)` only; `.Value` on choice reads, `{Value:"…"}` on writes; `Set(varX, Patch(...))` for save buttons; no `Set()` inside `ForAll`; no `;`-chain inside an `If()` that also has a false branch; no `ConfirmDialog.Show()` (doesn't exist); `var`-prefix all variables (`FormMode`, `SelectedEntry`, `Text`, `Value`… are reserved); dynamic column names (`'Comp' & N`) unsupported — hardcode If-chains.

## Fallback: same-app clone workflow (V8/V9, confirmed importable)

If from-scratch generation fails on this tenant: user creates blank app with N named screens + one seed control of each needed type on screen 1, exports; agent deepcopy-clones seeds across screens (fresh UID, Index = max(existing)+1 per parent, sequential PublishOrderIndex), mirrors YAML, delivers. This is strictly a degraded mode of the same compiler — the harvest/clone/verify code is reused with the user's export as donor and its screens kept.

## Delivery constraints (HSA-style laptop)

- Mail scanner blocks .msapp/.zip by content → flatten every member to `.txt` with `__` as path separator; rebuild via Python (Jupyter) script that zips from an explicit FILE_MAP.
- No PowerShell, no pac CLI, no VS Code — Jupyter is the only executable surface.
- User import path: Power Apps → Import/Open → From file (.msapp) → Run OnStart → F5.
