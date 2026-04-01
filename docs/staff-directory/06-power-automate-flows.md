# Power Automate Flows — Staff Directory

Three flows support the staff directory. All are **Automated cloud flows** built in Power Automate (`make.powerautomate.com`).

**Recommended practice:** Create all flows using a dedicated service account (e.g. `staffdir-automation@yourdomain.com`) so they remain active if a specific person leaves the organisation.

---

## Flow 1 — Welcome Email on New Profile

Sends a welcome message to the new employee when their profile is created.

### Trigger

**SharePoint — When an item is created**

| Setting | Value |
|---------|-------|
| Site Address | `https://yourtenant.sharepoint.com/sites/yoursite` |
| List Name | `StaffDirectory` |

### Actions

#### 1. Compose — Build the app URL

> Action type: **Data Operation — Compose**

Input:
```
https://apps.powerapps.com/play/YOUR-APP-ID-HERE?tenantId=YOUR-TENANT-ID
```

Replace with the actual Play URL of your published Power Apps app. This is found in the app's **Details** page in Power Apps Studio.

---

#### 2. Send an email (V2) — Welcome the new staff member

> Action type: **Office 365 Outlook — Send an email (V2)**

| Field | Value |
|-------|-------|
| To | `@{triggerOutputs()?['body/WorkEmail']}` |
| Subject | `Welcome to the Staff Directory, @{triggerOutputs()?['body/Title']}!` |
| Body (HTML) | See template below |

**Email body HTML:**
```html
<p>Hi @{triggerOutputs()?['body/Title']},</p>

<p>Your staff directory profile has been created. You can view and update
your profile at any time using the link below.</p>

<p><a href="@{outputs('Compose')}">Open Staff Directory</a></p>

<p>Your current profile details:</p>
<ul>
  <li><strong>Name:</strong> @{triggerOutputs()?['body/Title']}</li>
  <li><strong>Job Title:</strong> @{triggerOutputs()?['body/JobTitle']}</li>
  <li><strong>Department:</strong> @{triggerOutputs()?['body/Department/Value']}</li>
  <li><strong>Work Email:</strong> @{triggerOutputs()?['body/WorkEmail']}</li>
</ul>

<p>If any of these details are incorrect, please log in and edit your profile.</p>

<p>Thanks,<br>The IT Team</p>
```

---

## Flow 2 — Admin Notification on New Profile

Notifies administrators when a new staff member creates a profile. Uses Microsoft Teams for notification (recommended) or email.

### Trigger

Same as Flow 1: **SharePoint — When an item is created** on the `StaffDirectory` list.

### Option A: Post to a Teams channel (recommended)

#### 1. Post message in a chat or channel

> Action type: **Microsoft Teams — Post message in a chat or channel**

| Field | Value |
|-------|-------|
| Post as | Flow bot |
| Post in | Channel |
| Team | *(select your admin team)* |
| Channel | `#staff-directory-admin` *(or your chosen channel)* |
| Message | See template below |

**Message:**
```
📋 New staff profile created

**Name:** @{triggerOutputs()?['body/Title']}
**Job Title:** @{triggerOutputs()?['body/JobTitle']}
**Department:** @{triggerOutputs()?['body/Department/Value']}
**Work Email:** @{triggerOutputs()?['body/WorkEmail']}
**Created:** @{formatDateTime(triggerOutputs()?['body/Created'], 'dd MMM yyyy HH:mm')}
```

### Option B: Email all admin group members

If you prefer email over Teams, use these actions instead:

#### 1. Get group members

> Action type: **Office 365 Groups — List group members**

| Field | Value |
|-------|-------|
| Group Id | *(your StaffDirAdmins group Object ID)* |

#### 2. Apply to each — send email to each admin

> Action type: **Control — Apply to each**

Input: `value` from the previous step's output

Inside the loop, add:

> Action type: **Office 365 Outlook — Send an email (V2)**

| Field | Value |
|-------|-------|
| To | `@{items('Apply_to_each')?['mail']}` |
| Subject | `New staff profile: @{triggerOutputs()?['body/Title']}` |
| Body | Plain text or HTML summarising the new profile fields |

---

## Flow 3 — Audit Log on Profile Change

Writes a record to `StaffDirectoryAuditLog` every time a profile is modified.

### Trigger

**SharePoint — When an item is modified**

| Setting | Value |
|---------|-------|
| Site Address | `https://yourtenant.sharepoint.com/sites/yoursite` |
| List Name | `StaffDirectory` |

### Actions

#### 1. Compose — Snapshot current field values as JSON

> Action type: **Data Operation — Compose**

Input:
```json
{
  "Title": "@{triggerOutputs()?['body/Title']}",
  "JobTitle": "@{triggerOutputs()?['body/JobTitle']}",
  "Department": "@{triggerOutputs()?['body/Department/Value']}",
  "WorkEmail": "@{triggerOutputs()?['body/WorkEmail']}",
  "IsActive": "@{triggerOutputs()?['body/IsActive']}"
}
```

#### 2. Create item — Write to audit log

> Action type: **SharePoint — Create item**

| Setting | Value |
|---------|-------|
| Site Address | `https://yourtenant.sharepoint.com/sites/yoursite` |
| List Name | `StaffDirectoryAuditLog` |

| Column | Value |
|--------|-------|
| Title | `Audit: @{triggerOutputs()?['body/Title']}` |
| RecordId | `@{triggerOutputs()?['body/ID']}` |
| ChangedBy | `@{triggerOutputs()?['body/Editor/Email']}` |
| ChangedOn | `@{triggerOutputs()?['body/Modified']}` |
| FieldSnapshot | `@{outputs('Compose')}` |

> **Note:** The `Editor` field in the SharePoint trigger output contains the person who last modified the item. `Editor/Email` gives their email address.

---

## Flow 4 (Optional) — Weekly Cleanup Reminder

Reminds admins to review and permanently delete old deactivated profiles.

### Trigger

**Schedule — Recurrence**

| Setting | Value |
|---------|-------|
| Interval | 1 |
| Frequency | Week |
| Start time | Monday 09:00 your local timezone |

### Actions

#### 1. Get items — Find old deactivated profiles

> Action type: **SharePoint — Get items**

| Setting | Value |
|---------|-------|
| Site Address | `https://yourtenant.sharepoint.com/sites/yoursite` |
| List Name | `StaffDirectory` |
| Filter Query | `IsActive eq 0 and Modified lt '@{addDays(utcNow(), -90)}'` |

#### 2. Condition — Only proceed if any items were found

> Action type: **Control — Condition**

Condition: `@{length(body('Get_items')?['value'])} is greater than 0`

**If yes:**

#### 3. Send an email or Teams message to admins

List the deactivated profiles that are over 90 days old and prompt admins to review and permanently delete them.

**Email body example:**
```
The following deactivated staff profiles are more than 90 days old and may be eligible for permanent deletion:

@{body('Get_items')?['value']}

Please review these records in the StaffDirectory list and delete any that are no longer needed.
```

To format the list neatly, use a **Select** action before the email to extract just the names and modification dates, then use `join()` to format them as a readable list.

---

## Testing Flows

| Flow | How to test |
|------|------------|
| Flow 1 (Welcome Email) | Create a test item directly in the SharePoint list. Check that a welcome email arrives at the `WorkEmail` address. |
| Flow 2 (Admin Notification) | Create a test item. Check the Teams channel (or admin email) for the notification. |
| Flow 3 (Audit Log) | Modify any field of an existing item. Check the `StaffDirectoryAuditLog` list for a new entry. |
| Flow 4 (Cleanup) | Manually trigger the flow from Power Automate. Temporarily set the filter to 0 days to see all inactive records in the output. |
