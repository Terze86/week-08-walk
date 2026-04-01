# Power Apps Structure — Staff Directory

## App Type

Canvas App (Phone layout recommended for mobile accessibility; Tablet layout if you prefer a wide directory view).

---

## Connectors Required

Add these data connections when building the app:

| Connector | Purpose |
|-----------|---------|
| **SharePoint** | Read/write StaffDirectory list; upload/retrieve signature attachments |
| **Office 365 Users** | Get the signed-in user's Azure AD Object ID (`MyProfile().Id`) |
| **Office 365 Groups** | Check if the signed-in user is in the `StaffDirAdmins` group |

---

## Screens

| Screen name | Who sees it | Purpose |
|-------------|-------------|---------|
| `scr_Loading` | All users | Displays a loading indicator while `App.OnStart` runs its async checks |
| `scr_Register` | New users only | Self-registration form — shown when no profile exists for the current user |
| `scr_MyProfile` | Normal users (with profile) | Read-only view of own profile with an Edit button and signature display |
| `scr_EditProfile` | Own user + admins | Edit form — pre-populated with `gblSelectedRecord`; shared by both roles |
| `scr_Directory` | Admins only | Searchable, filterable gallery of all active staff profiles |
| `scr_AdminDetail` | Admins only | Full detail view of a selected staff member with Edit and Deactivate options |

---

## Navigation Flow

```
App.OnStart
    ├─ Set gblAdminGroupId (constant)
    ├─ Set gblIsAdmin  (Office365Groups check)
    └─ Set gblCurrentProfile  (LookUp in StaffDirectory)
              │
              ├─ IsBlank(gblCurrentProfile) ──► scr_Register
              ├─ gblIsAdmin = true          ──► scr_Directory
              └─ (else)                    ──► scr_MyProfile

scr_Register
    └─ Submit ──► creates record ──► scr_MyProfile (normal) or scr_Directory (admin)

scr_MyProfile
    └─ Edit button ──► Set(gblSelectedRecord, gblCurrentProfile) ──► scr_EditProfile

scr_EditProfile
    ├─ Save ──► Patch record, upload signature if changed ──► Back()
    └─ Cancel ──► Back()

scr_Directory
    ├─ Search / filter controls filter the gallery in real time
    └─ Tap gallery row ──► Set(gblSelectedRecord, ThisItem) ──► scr_AdminDetail

scr_AdminDetail
    ├─ Edit button ──► scr_EditProfile
    ├─ Deactivate button ──► Patch IsActive=false ──► scr_Directory
    └─ Back button ──► scr_Directory
```

---

## Global Variables

Set once in `App.OnStart` and used across all screens.

| Variable | Type | Set by | Purpose |
|----------|------|--------|---------|
| `gblAdminGroupId` | Text | `App.OnStart` | Azure AD Object ID of the `StaffDirAdmins` group. Replace the placeholder value with your actual group GUID. |
| `gblIsAdmin` | Boolean | `App.OnStart` | `true` if the signed-in user is a member of the admin group. Used for visibility rules and navigation logic. |
| `gblCurrentProfile` | Record | `App.OnStart` (and after register/edit) | The signed-in user's StaffDirectory record. `Blank()` if no profile exists yet. |
| `gblSelectedRecord` | Record | Gallery `OnSelect`, Edit button `OnSelect` | The record currently being viewed or edited. Used by `scr_EditProfile` and `scr_AdminDetail`. |
| `gblShowDeactivateConfirm` | Boolean | Deactivate button | Controls the visibility of the deactivate confirmation overlay on `scr_AdminDetail`. |
| `gblSignatureChanged` | Boolean | `img_Signature` `OnChange` | Set to `true` when the user uploads or draws a new signature, so the Save formula knows to call `SharePoint.AddAttachment()`. |

---

## Screen-by-Screen Control Inventory

### scr_Loading

| Control | Type | Property | Value |
|---------|------|----------|-------|
| `lbl_Loading` | Label | Text | `"Loading, please wait…"` |
| `ico_Spinner` | Icon | Icon | `Icon.Sync` (or a timer-driven spinner image) |

This screen is the app's start screen. `App.OnStart` runs and navigates away once all variables are set.

---

### scr_Register

| Control | Type | Notes |
|---------|------|-------|
| `txt_FullName` | Text input | Full Name. Required. |
| `txt_JobTitle` | Text input | Job Title. Required. |
| `drp_Department` | Dropdown | Items: `Choices(StaffDirectory.Department)` |
| `txt_WorkEmail` | Text input | Work Email. Validated with `IsMatch(..., Match.Email)`. |
| `img_RegSignature` | Add picture | Captures signature image. Optional at registration. |
| `btn_Register` | Button | Text: `"Create Profile"`. Submit logic in `05-power-fx-formulas.md`. |
| `lbl_RegError` | Label | Visible: `!IsBlank(gblRegError)`. Displays validation messages. |

---

### scr_MyProfile

All controls are read-only labels bound to `gblCurrentProfile`.

| Control | Type | Text / Image property |
|---------|------|-----------------------|
| `lbl_FullName` | Label | `gblCurrentProfile.Title` |
| `lbl_JobTitle` | Label | `gblCurrentProfile.JobTitle` |
| `lbl_Department` | Label | `gblCurrentProfile.Department.Value` |
| `lbl_WorkEmail` | Label | `gblCurrentProfile.WorkEmail` |
| `img_SignatureDisplay` | Image | See formula in `05-power-fx-formulas.md` — retrieves attachment URL |
| `btn_Edit` | Button | Text: `"Edit Profile"`. Navigates to `scr_EditProfile`. |

---

### scr_EditProfile

Shared by normal users (editing own record) and admins (editing any record).

| Control | Type | Default value | Notes |
|---------|------|---------------|-------|
| `txt_EditFullName` | Text input | `gblSelectedRecord.Title` | |
| `txt_EditJobTitle` | Text input | `gblSelectedRecord.JobTitle` | |
| `drp_EditDepartment` | Dropdown | `gblSelectedRecord.Department.Value` | Items: `Choices(StaffDirectory.Department)` |
| `txt_EditWorkEmail` | Text input | `gblSelectedRecord.WorkEmail` | |
| `img_EditSignature` | Add picture | — | Upload new signature image. Optional. |
| `img_EditSignaturePreview` | Image | See formulas — shows existing or newly uploaded signature | |
| `btn_Save` | Button | — | See save formula in `05-power-fx-formulas.md` |
| `btn_Cancel` | Button | — | `Back()` |
| `lbl_EditError` | Label | — | Validation error display |

---

### scr_Directory

| Control | Type | Notes |
|---------|------|-------|
| `txt_Search` | Text input | Placeholder: `"Search by name, department, or job title"` |
| `drp_FilterDept` | Dropdown | Items: `["All"] & Choices(StaffDirectory.Department)`. Default: `"All"` |
| `gal_Directory` | Gallery (vertical) | Items formula in `05-power-fx-formulas.md`. Each row shows name, title, department. |
| `lbl_NoResults` | Label | Visible: `CountRows(gal_Directory.AllItems) = 0`. Text: `"No results found."` |
| `btn_Refresh` | Button | `ClearCollect(colAllStaff, Filter(StaffDirectory, IsActive = true))` — manual refresh |

Inside the gallery template:
| Control | Bound to |
|---------|---------|
| `lbl_GalName` | `ThisItem.Title` |
| `lbl_GalJobTitle` | `ThisItem.JobTitle` |
| `lbl_GalDept` | `ThisItem.Department.Value` |

---

### scr_AdminDetail

| Control | Type | Notes |
|---------|------|-------|
| `lbl_DetailName` | Label | `gblSelectedRecord.Title` |
| `lbl_DetailJobTitle` | Label | `gblSelectedRecord.JobTitle` |
| `lbl_DetailDept` | Label | `gblSelectedRecord.Department.Value` |
| `lbl_DetailEmail` | Label | `gblSelectedRecord.WorkEmail` |
| `img_DetailSignature` | Image | Signature display — same pattern as `scr_MyProfile` |
| `btn_DetailEdit` | Button | Navigates to `scr_EditProfile` |
| `btn_Deactivate` | Button | Sets `gblShowDeactivateConfirm = true` to show confirm overlay |
| `btn_Back` | Button | `Navigate(scr_Directory, ScreenTransition.Slide)` |

**Deactivate confirmation overlay** (layered on top):
| Control | Type | Notes |
|---------|------|-------|
| `rect_ConfirmBg` | Rectangle | Semi-transparent fill. Visible: `gblShowDeactivateConfirm` |
| `lbl_ConfirmMsg` | Label | Text: `"Deactivate this profile? This will hide them from the directory."`. Visible: same |
| `btn_ConfirmYes` | Button | Text: `"Deactivate"`. Patch + navigate. See formulas. |
| `btn_ConfirmNo` | Button | Text: `"Cancel"`. `Set(gblShowDeactivateConfirm, false)` |

---

## Role-Based Visibility Summary

| Element | Visible formula |
|---------|----------------|
| `btn_Deactivate` on `scr_AdminDetail` | `gblIsAdmin` |
| `scr_Directory` access | Guard in `OnVisible`: `If(!gblIsAdmin, Navigate(scr_MyProfile, ScreenTransition.None))` |
| "Back to Directory" link on `scr_AdminDetail` | Always visible (only admins can reach this screen) |
| `scr_AdminDetail` access | Guard in `OnVisible`: `If(!gblIsAdmin, Navigate(scr_MyProfile, ScreenTransition.None))` |
