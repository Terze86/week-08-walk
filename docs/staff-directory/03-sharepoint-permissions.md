# SharePoint Permissions — StaffDirectory

## Goal

| Who | Can do |
|-----|--------|
| Any authenticated user | Read all profiles, create their own profile, edit only their own profile |
| `StaffDirAdmins` M365 group members | Read, create, and edit any profile; deactivate profiles |
| Site owners | Full control for maintenance |

The key principle: **SharePoint item-level permissions are the real security boundary.** The Power Apps role checks (`gblIsAdmin`) only control the UX. Even if a normal user bypassed the app, SharePoint would still prevent them from editing another person's record.

---

## Step 1 — Create the Admin M365 Group

Before setting list permissions, create the group that will identify admin/power users.

1. Go to **Microsoft 365 Admin Center** (`admin.microsoft.com`) > **Groups** > **Active groups** > **Add a group**
2. Choose group type: **Microsoft 365** or **Security** (either works with the Office365Groups connector)
3. Name: `StaffDirAdmins` (or your preferred name)
4. Add all admin/power users as members
5. After creation, open the group and copy the **Object ID** from the group properties. You will need this GUID when building the Power Apps app.

---

## Step 2 — Break Permission Inheritance on the List

By default, the StaffDirectory list inherits permissions from the SharePoint site. You must break this inheritance to apply custom list-level permissions.

1. Open the **StaffDirectory** list
2. Go to **Settings** (gear icon) > **List settings** > **Permissions for this list**
3. Click **Stop Inheriting Permissions**
4. Confirm when prompted

---

## Step 3 — Set List-Level Permissions

Remove any inherited permissions that are too broad, then add:

| Principal | Permission level | How to add |
|-----------|-----------------|------------|
| **Everyone except external users** (or your "All Staff" group) | **Contribute** | Grant this permission to the broad group — Contribute allows creating new items and editing items you own |
| **StaffDirAdmins** | **Edit** | Grant this to the admin group — Edit allows modifying any item in the list |
| **Site Collection Administrators** | **Full Control** | These are usually already present; do not remove |

> **Note on "Contribute" vs "Edit":**
> - **Contribute**: Can add new items and edit/delete items *created by themselves* (when combined with item-level permissions below)
> - **Edit**: Bypasses item-level restrictions — can edit/delete *any* item in the list

---

## Step 4 — Configure Item-Level Permissions

This is the critical server-side access control setting.

1. Go to **List settings** > **Advanced settings**
2. Scroll to the **Item-level Permissions** section
3. Set:

| Setting | Value |
|---------|-------|
| Read access | **Read all items** |
| Create and Edit access | **Create items and edit items that were created by the user** |

4. Click **OK** to save

**Why these settings:**
- **Read all items** — everyone can see the full directory (needed for the admin view and general browsing)
- **Edit own items only** — normal users with Contribute cannot edit another person's record at the SharePoint level, even if they somehow access the list directly
- Admin group members have the **Edit** permission level which overrides item-level restrictions

---

## Step 5 — Permissions for StaffDirectoryAuditLog

The audit log list should be restricted — only admins and the flow service account need access.

1. Break inheritance on the `StaffDirectoryAuditLog` list (same steps as above)
2. Remove all broad permissions (remove "Everyone except external users")
3. Add:

| Principal | Permission level |
|-----------|-----------------|
| `StaffDirAdmins` | Read (view only — admins should not edit audit records) |
| Flow service account (the account that owns the Power Automate flows) | Contribute |
| Site Collection Administrators | Full Control |

---

## Step 6 — Share the Power Apps App

After building the app (see `07-setup-guide.md`):

1. Open the app in Power Apps Studio
2. Click **File** > **Share**
3. Share with: **Everyone in your organisation** (or the specific group of staff who should have access)
4. Permission: **User** (they can run the app but not edit it)
5. Share the **StaffDirectory** SharePoint connection as part of the app share — Power Apps will prompt for this

---

## Permission Summary Matrix

| Action | Normal user | Admin user |
|--------|-------------|------------|
| Open the app | Yes | Yes |
| View own profile | Yes | Yes |
| View all profiles (in app) | No (app redirects away) | Yes |
| View all profiles (direct list access) | Yes (read-only) | Yes |
| Create own profile | Yes | Yes |
| Edit own profile | Yes | Yes |
| Edit another user's profile (in app) | No (app prevents) | Yes |
| Edit another user's profile (direct list access) | **No (SharePoint blocks)** | Yes |
| Deactivate a profile | No | Yes |
| Access audit log list | No | Yes (read only) |

---

## Important Notes

**The app is not the security boundary.** Always rely on SharePoint permissions as the authoritative enforcement layer.

**Service account for flows:** The Power Automate flows run under the credentials of the account that created them (the flow owner). This account must have **Contribute** permissions on both `StaffDirectory` (to write audit entries and send emails via Outlook) and `StaffDirectoryAuditLog`. Consider creating a dedicated service account (e.g. `staffdir-automation@yourdomain.com`) and using that account to create all flows, so the flows don't break if a specific person leaves.

**Guest users:** External/guest users are excluded from the broad "Everyone except external users" group by default. If you need contractors or external staff to have profiles, explicitly add them to the list permissions and to the app share.
