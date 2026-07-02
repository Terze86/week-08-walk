# Power Fx & SharePoint Patterns for This Tenant

Distilled from `powerapps-solution-design` V1–V17 (verified against the user's
HSA environment). Apply these when writing app-spec formulas and when planning
SharePoint lists. Violations either import fine but misbehave, or throw red
squigglies the user has to report back — both cost a delivery round-trip.

## Power Fx compatibility floor (older tenant runtime)

| Rule | Correct | Wrong |
|---|---|---|
| Sorting | plain `Filter()` — let SharePoint order | `SortBy(...)` (unknown function error) |
| Navigation | `Navigate(scr)` or `Navigate(scr, ScreenTransition.Fade)` | `Navigate(scr, None)` |
| Confirmation dialogs | separate popup screen or `Notify()` | `Confirm()` / `ConfirmDialog.Show()` (don't exist) |
| Dynamic column names | hardcoded If/Else chain per column | `'Comp' & N & '_Level'` |
| Behavior chains in If | `If(cond, a; b; c)` — NO false branch when chaining with `;` | `If(cond, a; b, elseExpr)` (parse error) |
| Counters in loops | no `Set()` inside `ForAll` — compute after with `CountRows(Filter(...))` | `Set(x, x+1)` inside `ForAll` |

## Variable naming

Always prefix app variables with `var` (`varMode`, `varSelectedEntry`).
`FormMode`, `SelectedEntry`, `Selected`, `Default`, `Text`, `Value`, `Items`,
`Visible` collide with built-ins → "Unexpected characters... 'Enum' where
'Ident' is expected" and buttons silently do nothing. Initialize all variables
in App OnStart.

## SharePoint choice columns (the #1 gotcha)

- **Read** returns a record: `ThisItem.Status.Value`, never `ThisItem.Status`.
- **Write** takes a record: `{Status: {Value: "Completed"}}` or
  `{Status: {Value: drp.Selected.Value}}`.
- Blank gallery columns / blank dropdowns after import = missing `.Value`.

## Patch patterns

- Save buttons: `Set(varSaved, Patch(List, target, {...}))` — a bare `Patch`
  loses the updated record reference.
- Creating rows: `Patch(List, Defaults(List), {...})` must explicitly include
  **every required column** (empty string / Blank()) — `Defaults()` does not,
  and you get `Field 'X' is required`.
- Email addresses: use plain text columns, NOT Person columns (claims format).
- Delete: `Remove(List, ThisItem)` guarded by a permission check +
  `Notify(...)`; style delete buttons `Fill = ColorValue("#D83B01")`.

## App OnStart

- Collections defined in OnStart show red squigglies until the user runs
  **App → ⋯ → Run OnStart** — tell them this in every delivery.
- A trailing/extra comma in a `Table({...},)` silently breaks ALL of OnStart
  (no squiggle at the offending line). Count brackets and commas before
  shipping; squigglies that survive Run OnStart mean an OnStart parse error.

## Master-detail forms (parent record + N child items)

Decide row-creation timing with the user: **eager** (create on New click via
`Patch(Defaults)`; Cancel = `Remove`; orphan rows possible) vs **lazy** (create
on first save; branch on `varMode`). Per-child Save + "Mark Complete" button
that patches `Status: {Value: "Completed"}` is the common shape. This user's
confirmed preferences: justifications optional, Mark Complete always enabled
(no fill gate), delete from the landing gallery (not the detail screen),
header fields editable in both New and Edit modes.

## Layout

- Forms taller than 768px: use a tall canvas (screen Height = last control Y +
  height + 80), NOT the Scrollable screen template (it swallows buttons).
- Galleries need `TemplateSize` + `TemplatePadding` or they render empty.
- Gallery card widths: `Parent.TemplateWidth - 10`; in-card buttons at
  `Parent.TemplateWidth - 90`.
- Full-width bars: `Width = App.Width`, never hardcoded 1366. No ZIndex on
  screen-level rectangles; list background rectangles BEFORE the text they
  sit behind (earlier in the control list renders behind).

## Email from the app (Office 365 Outlook connector)

`Office365Outlook.SendEmailV2(to, subject, body, {Cc: cc})`. The body is HTML:
`Char(10)` collapses — wrap with
`Substitute(body, Char(10), "<br>")` (and `"</p><p>"` for double newlines).
Bulk send: `ClearCollect` the eligible rows, `ForAll` with
`If(!IsBlank(email), SendEmailV2(...); Patch(...))`, then compute counts
after the loop.

## Post-import checklist to include in every delivery

1. Import: Power Apps → Import app / Open → From file → select .msapp.
2. App → ⋯ → Run OnStart (collections populate; squigglies clear).
3. F5 and walk every screen; check galleries show data and buttons navigate.
4. If a new SharePoint list is needed: Data → Add data → pick the list
   (connections can't be fabricated in the .msapp — donor's connection
   carries over, new lists are added here).
5. Rollback: existing apps are untouched; a failed import changes nothing.
