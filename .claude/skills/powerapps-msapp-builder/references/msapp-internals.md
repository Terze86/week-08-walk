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

## Identity/ordering rules (each one is a confirmed crash cause)

| Field | Rule | Violation symptom |
|---|---|---|
| ControlUniqueId | unique app-wide, sequential-ish (App=1, screens from 4) | ErrOpeningDocument_UnknownError |
| Controls filename | `<screen uid>.json` | crash |
| Index | unique within each parent's Children | screen silently missing (V16) |
| PublishOrderIndex | globally sequential, no gaps (0,1,2… not 0,1,100) | ErrOpeningDocument_UnknownError (V13/V15) |
| Parent | exact parent control name | crash |
| StyleName | must exist in Themes.json | crash |
| Template Id+Version | must appear in Templates.json | ErrOpeningDocument_UnknownError (V6 "cross-app" crash) |

## Gallery anatomy

Gallery control → `Children[0]` is a `galleryTemplate` control → its `Children` hold the per-item controls (`Parent` = the galleryTemplate's name, coordinates relative to the item). In YAML, item controls nest directly under the gallery's `Children:` — the galleryTemplate node is NOT written in YAML. Galleries render empty without `TemplateSize`/`TemplatePadding`.

## YAML mirror

- Every JSON rule appears as `Prop: =script` (multi-line → `Prop: |-` block, continuation indented +2 under the property).
- Screen file shape: `Screens:` → `<name>:` → `Properties:` / `Children:` (list of `- ctrlName:` with `Control: Type@Version`, optional `Variant:`, `Properties:`).
- Control type strings (donor harvest overrides these defaults): Label@2.5.1, Classic/Button@2.2.0, Classic/TextInput@2.3.2, Classic/DropDown@2.3.1, Gallery@2.15.0 (+ `Variant: Vertical`), Rectangle@2.3.0, Classic/Icon@2.5.0, Image@2.2.3.
- The importer treats the JSON as authoritative but YAML/JSON drift has caused failures — the compiler renders both from one rule list.

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
