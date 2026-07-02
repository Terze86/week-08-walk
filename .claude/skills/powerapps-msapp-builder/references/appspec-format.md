# App Spec Format

The compiler input is a single JSON file describing the whole app. All property values are **raw Power Fx InvariantScript strings** — exactly what you'd type in the Studio formula bar (string literals therefore need embedded quotes: `"\"My App\""`). The same text is written to the JSON `Rules` and (with a leading `=`) to the YAML mirror.

```json
{
  "name": "CaseTracker",
  "onstart": "Set(varReady, true);\nClearCollect(colStatuses, [\"Draft\", \"Completed\"])",
  "screens": [
    {
      "name": "scrLanding",
      "properties": { "Fill": "RGBA(245, 246, 250, 1)" },
      "controls": [
        {
          "type": "label",
          "name": "lblHeader",
          "properties": {
            "Text": "\"Case Tracker\"",
            "X": "40", "Y": "24", "Width": "600", "Height": "48",
            "Size": "24", "FontWeight": "FontWeight.Bold"
          }
        },
        {
          "type": "button",
          "name": "btnNew",
          "properties": {
            "Text": "\"New Case\"",
            "OnSelect": "Navigate(scrEntry, ScreenTransition.Fade)",
            "X": "40", "Y": "96"
          }
        },
        {
          "type": "gallery",
          "name": "galCases",
          "properties": {
            "Items": "Filter(Cases, Owner = User().Email)",
            "TemplateSize": "70", "TemplatePadding": "0",
            "X": "40", "Y": "170", "Width": "1286", "Height": "500"
          },
          "children": [
            {
              "type": "label",
              "name": "galCaseTitle",
              "properties": { "Text": "ThisItem.Title", "X": "16", "Y": "12" }
            },
            {
              "type": "button",
              "name": "galBtnOpen",
              "properties": {
                "Text": "\"Open\"",
                "OnSelect": "Set(varCase, ThisItem); Navigate(scrEntry)",
                "X": "Parent.TemplateWidth - 140", "Y": "12"
              }
            }
          ]
        }
      ]
    },
    { "name": "scrEntry", "controls": [ ... ] }
  ]
}
```

## Fields

- `name` — app name; used for the .msapp filename and Properties.json.
- `onstart` — optional; replaces App OnStart in both `Controls/1.json` and `Src/App.pa.yaml`.
- `screens[]` — order = screen order. Each: `name`, optional `properties` (screen rules like `Fill`), `controls[]`.
- control `type` — must exist in the donor harvest (`manifest.json` lists available types). Typical: `label`, `button`, `text` (text input), `dropdown`, `gallery` (with default children), `gallery_blank`, `rectangle`, `icon`.
- control `properties` — any rule; existing template rules are overwritten, unknown ones are appended (Behavior category auto-detected for On* handlers).
- `children` — galleries only: controls placed inside the gallery's item template. Their `Parent` and coordinates are relative to the gallery template, handled by the compiler.

## Authoring rules (verifier enforces most)

- Position every control explicitly (X, Y, Width, Height) — templates carry the donor's geometry otherwise.
- Choice column reads need `.Value`; writes use `{Value: "..."}`.
- No `SortBy()`, no `Navigate(scr, None)` — old tenants reject both.
- Variables `var`-prefixed; never `FormMode`, `SelectedEntry`, etc.
- Rectangles: no `ZIndex`, `App.Width` for full-width bars, always give X/Y/Height, place them EARLY in the control list (rendered behind later controls).
- Galleries need `TemplateSize` + `TemplatePadding` or they render empty.
