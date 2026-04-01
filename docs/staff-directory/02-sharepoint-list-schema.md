# SharePoint List Schema — StaffDirectory

## List Configuration

- **List name**: `StaffDirectory`
- **Site**: Your organisation's SharePoint site (e.g. `https://yourtenant.sharepoint.com/sites/intranet`)
- **Template**: Blank list
- **Attachments**: Enabled (default) — used to store signature images

---

## Columns

### Core Profile Fields

| Display Name | Internal Name | Column Type | Required | Settings |
|---|---|---|---|---|
| Full Name | `Title` | Single line of text | Yes | Built-in column — rename display name to "Full Name" |
| Job Title | `JobTitle` | Single line of text | Yes | Max 255 characters |
| Department | `Department` | Choice | Yes | See choices below. No fill-in values. |
| Work Email | `WorkEmail` | Single line of text | Yes | Validated as email format in Power Apps |

### System / Identity Fields

| Display Name | Internal Name | Column Type | Required | Settings |
|---|---|---|---|---|
| AAD Object ID | `AADObjectId` | Single line of text | Yes | Azure AD Object ID (GUID) of the user. Stable unique key. **Hide from all list views.** |
| User Principal Name | `UserPrincipalName` | Single line of text | Yes | Login email (UPN). Used for matching the current user. **Hide from all list views.** |
| Is Active | `IsActive` | Yes/No | Yes | Default value: **Yes**. Set to No by admins to soft-delete a profile. |

### Auto-tracked (built-in, no action needed)

| Display Name | Notes |
|---|---|
| `ID` | Unique integer ID for each item — used by `SharePoint.AddAttachment()` for signature uploads |
| `Created` | Timestamp when record was first created |
| `Modified` | Timestamp of last modification |
| `Created By` | The M365 user who created the record (used by item-level permissions) |

---

## Department Choices

Configure these in the column settings. Add or remove choices to match your organisation.

```
Engineering
Product
Design
Sales
Marketing
Finance
HR
Operations
Legal
Executive
Other
```

---

## Signature Image — Attachments

Signatures are stored as attachments on each list item (not as a column).

- **File types accepted**: JPEG, PNG
- **Recommended max size**: 2 MB
- **Naming convention**: The Power Apps formula saves the file as `signature.png` (overwriting any previous signature for that user)
- **How it works**: Power Fx's built-in `SharePoint.AddAttachment()` function uploads the image directly from the app — no Power Automate flow required for this operation.

To display the signature, the app retrieves the attachment URL using `SharePoint.GetAttachments()`.

---

## Recommended List Views

### "Directory" view (default, all users)
- Columns: Full Name, Job Title, Department, Work Email
- Filter: `Is Active = Yes`
- Sort: Full Name (A → Z)
- **Item-level permissions**: All users can read all items

### "Admin" view (for list managers)
- Columns: Full Name, Job Title, Department, Work Email, Is Active, Created, Modified
- No filter — shows all records including inactive
- Sort: Modified (newest first)

---

## StaffDirectoryAuditLog List (for Flow 3)

Create a second list named `StaffDirectoryAuditLog` with the following columns:

| Display Name | Internal Name | Column Type | Notes |
|---|---|---|---|
| Title | `Title` | Single line | Auto-set by flow to "Audit: [Full Name]" |
| Record ID | `RecordId` | Number | ID of the modified StaffDirectory item |
| Modified By | `ChangedBy` | Single line | Email of the user who made the change |
| Changed On | `ChangedOn` | Date/Time | Timestamp from the flow trigger |
| Field Snapshot | `FieldSnapshot` | Multi-line text (Plain text) | JSON string of all field values at time of change |

This list does not need item-level permission changes — only admins (and the flow service account) should have access to it.
