# Setup Guide — Staff Directory

Follow these phases in order. Estimated total build time: 3–5 hours for a first-time builder.

---

## Prerequisites

- Microsoft 365 licence with SharePoint, Power Apps, and Power Automate access
- SharePoint site where the list will live (Site Owner or higher on that site)
- Ability to create Microsoft 365 Groups (Microsoft 365 Admin Centre access)
- Power Apps licence (included in most M365 plans — confirm yours includes canvas apps)

---

## Phase 1 — Create the Admin Group (15 min)

1. Go to **Microsoft 365 Admin Centre** (`admin.microsoft.com`)
2. Navigate to **Groups > Active groups > Add a group**
3. Select type **Microsoft 365** and click **Next**
4. Name: `StaffDirAdmins`. Add a description. Click **Next** through remaining steps and create.
5. Open the group once created. Go to the **General** tab.
6. Copy the **Object ID** (format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`). Save this — you'll need it in Phase 3.
7. Go to the **Members** tab and add all admin/power users.

---

## Phase 2 — Create the SharePoint Lists (30 min)

### StaffDirectory list

1. Go to your SharePoint site > **Site Contents** > **New > List > Blank list**
2. Name: `StaffDirectory`. Click **Create**.
3. **Rename the Title column:** Click the column header > **Column settings > Rename**. Set display name to `Full Name`. (Internal name stays `Title` — do not change that.)
4. Add columns (**+ Add column** from the column header area):

   | Column | Type | Settings |
   |--------|------|---------|
   | `JobTitle` | Single line of text | Required: No (enforced by app) |
   | `Department` | Choice | Enter choices from `02-sharepoint-list-schema.md`. No fill-in values. |
   | `WorkEmail` | Single line of text | — |
   | `AADObjectId` | Single line of text | — |
   | `UserPrincipalName` | Single line of text | — |
   | `IsActive` | Yes/No | Default value: **Yes** |

5. **Hide system fields from views:** Click **Full Name** column header > **Column settings > Edit**. Do the same for `AADObjectId` and `UserPrincipalName` — in their settings, uncheck **Show in forms** (optional but recommended to keep the list clean for end users browsing directly).

6. Create a view called **"Directory"**:
   - Columns: Full Name, Job Title, Department, Work Email
   - Filter: `Is Active is equal to Yes`
   - Sort: Full Name ascending

### StaffDirectoryAuditLog list

1. **New > List > Blank list**. Name: `StaffDirectoryAuditLog`.
2. Add columns:

   | Column | Type |
   |--------|------|
   | `RecordId` | Number |
   | `ChangedBy` | Single line of text |
   | `ChangedOn` | Date and Time |
   | `FieldSnapshot` | Multiple lines of text (Plain text) |

---

## Phase 3 — Set SharePoint Permissions (20 min)

Follow all steps in `03-sharepoint-permissions.md`:

1. Break list-level inheritance on `StaffDirectory`
2. Grant **Contribute** to "Everyone except external users"
3. Grant **Edit** to `StaffDirAdmins`
4. Set item-level permissions: **Read all items** / **Edit items created by user**
5. Restrict `StaffDirectoryAuditLog` to admins and the flow service account only

---

## Phase 4 — Build the Power Apps Canvas App (90–120 min)

1. Go to `make.powerapps.com` > **Create > Blank app > Blank canvas app**
2. Name: `Staff Directory`. Format: **Phone** (or Tablet). Click **Create**.

### Add data connections

3. In the left panel, click the **Data** icon (cylinder) > **Add data**
4. Search for and add:
   - **SharePoint** → connect to your site → select `StaffDirectory`
   - **Office 365 Users**
   - **Office 365 Groups**

### Create screens

5. Rename the default `Screen1` to `scr_Loading`.
6. Add remaining screens using the **+ New screen** button. Name each screen as listed in `04-power-apps-structure.md`.
7. Set `scr_Loading` as the **start screen** (right-click the screen in the screen panel > **Set as start screen**).

### Build each screen

For each screen, add controls and set their properties following `04-power-apps-structure.md`. Apply all formulas from `05-power-fx-formulas.md`.

Key steps per screen:

#### scr_Loading
- Add a Label with `"Loading, please wait…"`
- Set `App.OnStart` from `05-power-fx-formulas.md` (click **App** in the tree view > **OnStart** property)
- Replace `"YOUR-GROUP-OBJECT-ID-HERE"` with the Object ID from Phase 1

#### scr_Register
- Add text inputs for Full Name, Job Title, Work Email
- Add a Dropdown for Department: `Items = Choices(StaffDirectory.Department)`
- Add an **Add picture** control for the signature
- Add a Button labelled "Create Profile" with the registration formula

#### scr_MyProfile
- Add labels bound to `gblCurrentProfile` fields
- Add an Image control for the signature
- Add an Edit button

#### scr_EditProfile
- Add text inputs with `Default` properties bound to `gblSelectedRecord`
- Add an **Add picture** control for the signature upload
- Add an Image control for the signature preview
- Add Save and Cancel buttons

#### scr_Directory
- Add a Text input for search (`txt_Search`)
- Add a Dropdown for department filter: `Items = ["All"] & Choices(StaffDirectory.Department)`
- Add a Vertical gallery (`gal_Directory`) with the Items formula from `05-power-fx-formulas.md`
- Inside the gallery template, add labels for name, job title, department
- Set `OnVisible` formula (loads collection + admin guard)

#### scr_AdminDetail
- Add labels bound to `gblSelectedRecord`
- Add Image control for signature
- Add Edit, Deactivate, and Back buttons
- Add the deactivate confirmation overlay (Rectangle + Labels + 2 Buttons)

### Configure SharePoint site URL in formulas

6. In all formulas that reference `"https://yourtenant.sharepoint.com/sites/yoursite"`, replace this with your actual SharePoint site URL.

### Save and publish

7. **File > Save** regularly while building
8. When complete: **File > Publish**
9. Click the **Share** button. Share with **Everyone in your organisation** (or the relevant group). Ensure the SharePoint connection is also shared.
10. Copy the **Play URL** from the app's Details page — you'll need this for the welcome email in Phase 5.

---

## Phase 5 — Build Power Automate Flows (45 min)

Go to `make.powerautomate.com`.

### Flow 1 — Welcome Email

1. **Create > Automated cloud flow**
2. Name: `StaffDirectory - Welcome Email`
3. Trigger: **SharePoint — When an item is created**
4. Add actions from `06-power-automate-flows.md` (Flow 1 section)
5. Replace the app Play URL placeholder in the Compose action
6. **Save** and **Test** by creating a test item in the list

### Flow 2 — Admin Notification

1. **Create > Automated cloud flow**
2. Name: `StaffDirectory - Admin Notification`
3. Trigger: same SharePoint trigger
4. Add Teams post (or email loop) from `06-power-automate-flows.md` (Flow 2 section)
5. **Save** and **Test**

### Flow 3 — Audit Log

1. **Create > Automated cloud flow**
2. Name: `StaffDirectory - Audit Log`
3. Trigger: **SharePoint — When an item is modified**
4. Add the Compose + Create item actions from `06-power-automate-flows.md` (Flow 3 section)
5. **Save** and **Test** by editing a list item

### Flow 4 — Cleanup Reminder (optional)

1. **Create > Scheduled cloud flow**
2. Name: `StaffDirectory - Cleanup Reminder`
3. Set recurrence to weekly on Monday
4. Add actions from `06-power-automate-flows.md` (Flow 4 section)
5. **Save**

---

## Phase 6 — End-to-End Testing (30 min)

Use two test accounts: one that is **not** in `StaffDirAdmins`, and one that **is**.

| Test | Account | Expected result |
|------|---------|----------------|
| Open app (no profile) | Normal user | `scr_Register` displayed |
| Submit registration form | Normal user | Profile created in SharePoint, welcome email sent, app navigates to `scr_MyProfile` |
| Open app (profile exists) | Normal user | `scr_MyProfile` displayed with correct data |
| Edit profile | Normal user | Changes saved, signature (if uploaded) visible on profile |
| Try to access `scr_Directory` directly | Normal user | Redirected to `scr_MyProfile` |
| Open app | Admin user | `scr_Directory` displayed with all profiles |
| Search for a name | Admin user | Gallery filters correctly |
| Filter by department | Admin user | Gallery shows only that department |
| Tap a profile row | Admin user | `scr_AdminDetail` shown |
| Edit any profile | Admin user | Changes saved correctly |
| Upload signature for another user | Admin user | Signature saved and displayed |
| Deactivate a profile | Admin user | Confirm overlay appears; after confirm, profile disappears from gallery |
| Modify a profile | Either | Audit log entry created in `StaffDirectoryAuditLog` |

---

## Common Issues and Fixes

| Issue | Likely cause | Fix |
|-------|-------------|-----|
| App stays on loading screen forever | `App.OnStart` error, usually in the Groups connector call | Open the app in Edit mode, click App > OnStart, and run each line in the formula bar individually to identify the error |
| `gblIsAdmin` is always `false` for admins | Group Object ID is incorrect, or the user is not a *direct* member (may be nested) | Verify the GUID in `gblAdminGroupId`. Check group membership in Azure AD / Entra ID. |
| Signature does not save | `SharePoint.AddAttachment` call failing | Check that `img_EditSignature.Image` is not blank before calling AddAttachment. Also verify the SharePoint site URL is correct. |
| Signature not displaying | `SharePoint.GetAttachments` returning no results | Ensure attachments are enabled on the list (List Settings > Advanced Settings > Attachments = Enabled). Check the FileName filter in the `LookUp` — must match exactly `"signature.png"`. |
| Normal user can edit someone else's record (in list directly) | Item-level permissions not set | Revisit Phase 3 — confirm Advanced Settings shows "Create items and edit items that were created by the user" |
| Flow fails with permissions error | Flow owner lacks Contribute on the list | Ensure the account that owns the flows has Contribute (or higher) on both SharePoint lists |
| Department dropdown shows no items | SharePoint connection not refreshed after adding the Department column | In Power Apps Studio, go to Data > StaffDirectory > click the three dots > **Refresh** |
