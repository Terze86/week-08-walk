# Staff Directory — Overview

## Purpose

A centralised staff directory allowing all employees to view profiles and maintain their own information. Built entirely on the Microsoft Power Platform — no additional licensing or custom code required.

## Components

| Component | Role |
|-----------|------|
| **Microsoft Lists** (SharePoint) | Data store for all staff profiles, including signature images stored as list attachments |
| **Power Apps Canvas App** | User-facing interface — self-registration, profile viewing, profile editing, admin directory |
| **Power Automate** | Automation — welcome emails, admin notifications, audit logging |

## User Roles

| Role | How identified | What they can do |
|------|---------------|------------------|
| **New user** | No profile record found for their email | Prompted to self-register on first launch |
| **Normal user** | Has a profile; not in admin group | View and edit only their own profile |
| **Admin (Power User)** | Member of `StaffDirAdmins` M365 group | View and edit all profiles; deactivate profiles |

## Architecture

```
┌─────────────────────────────────────────────┐
│              Power Apps Canvas App          │
│                                             │
│  scr_Loading ──► scr_Register               │
│      │               │                      │
│      ├──► scr_MyProfile ──► scr_EditProfile │
│      │                                      │
│      └──► scr_Directory ──► scr_AdminDetail │
│                   │              │           │
│                   └──────────────┘           │
└──────────────────────┬──────────────────────┘
                       │ SharePoint connector
                       ▼
        ┌──────────────────────────┐
        │  Microsoft Lists         │
        │  StaffDirectory          │
        │  (with attachments)      │
        └──────────────┬───────────┘
                       │ triggers
                       ▼
        ┌──────────────────────────┐
        │  Power Automate Flows    │
        │  - Welcome Email         │
        │  - Admin Notification    │
        │  - Audit Log             │
        └──────────────────────────┘
```

## Profile Fields

| Field | Type | Notes |
|-------|------|-------|
| Full Name | Text | Required |
| Job Title | Text | Required |
| Department | Choice | Required |
| Work Email | Text (email) | Required |
| Signature | Image (attachment) | Uploaded by user; JPEG or PNG |

## Key Design Decisions

- **Server-side security**: SharePoint item-level permissions ensure normal users physically cannot edit others' records — even if someone manipulates the app. The app is a UX layer; SharePoint is the security boundary.
- **Soft delete**: Profiles are deactivated (`IsActive = false`) rather than hard-deleted, preserving history. A scheduled flow notifies admins of old inactive records for periodic cleanup.
- **Signature as attachment**: Signature images are stored as SharePoint list item attachments using the built-in `SharePoint.AddAttachment()` Power Fx function — no custom API calls or extra flows required.
- **Admin check at launch**: `Office365Groups.IsMemberOfGroup()` is called once in `App.OnStart` and cached in `gblIsAdmin`. Changing group membership takes effect on next app launch.

## File Index

| File | Contents |
|------|----------|
| `02-sharepoint-list-schema.md` | Exact column definitions for the StaffDirectory list |
| `03-sharepoint-permissions.md` | List and item-level permission settings |
| `04-power-apps-structure.md` | Screen inventory, navigation flow, global variables |
| `05-power-fx-formulas.md` | All Power Fx formulas screen by screen |
| `06-power-automate-flows.md` | Flow designs for all three automations |
| `07-setup-guide.md` | Step-by-step build instructions |
