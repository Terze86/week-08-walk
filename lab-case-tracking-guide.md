# Lab Case Tracking App — Complete Build Guide

This guide walks a complete beginner through every step of building a Power Apps canvas app for lab case review tracking, backed by two Microsoft Lists and with Teams notifications via Power Automate. Read every section before you start — understanding the overall structure will make individual steps much clearer.

**What you will build:**
- A tablet-format Power Apps canvas app (1366 × 768 px)
- 7 screens covering both the Reviewer and Reportee workflows
- Integration with two Microsoft Lists
- Two Power Automate flows for Teams notifications

**Prerequisites:**
- Microsoft 365 account with Power Apps, Power Automate, and Microsoft Lists/SharePoint access
- The existing **Lab Cases** Microsoft List (already set up)
- Microsoft Teams access
- A browser at [make.powerapps.com](https://make.powerapps.com) and [make.powerautomate.com](https://make.powerautomate.com)

---

## Table of Contents

1. [Part 1: Create the Case Issues Microsoft List](#part-1-create-the-case-issues-microsoft-list)
2. [Part 2: Create the Power App — Setup and Data](#part-2-create-the-power-app--setup-and-data)
3. [Part 3: Build Each Screen](#part-3-build-each-screen)
   - [Step 1 — App OnStart (Variables)](#step-1--app-onstart-variables)
   - [Step 2 — HomeScreen](#step-2--homescreen)
   - [Step 3 — ReviewerCaseListScreen](#step-3--reviewercaselistscreen)
   - [Step 4 — ReviewerCaseDetailScreen](#step-4--reviewercasedetailscreen)
   - [Step 5 — ReviewerAddIssueScreen](#step-5--revieweraddissuescreen)
   - [Step 6 — LIMSCopyScreen](#step-6--limscopysceen)
   - [Step 7 — ReporteeCaseListScreen](#step-7--reporteecaselistscreen)
   - [Step 8 — ReporteeIssueScreen](#step-8--reporteeissuescreen)
4. [Part 4: Power Automate Flows](#part-4-power-automate-flows)
5. [Part 5: Testing Checklist](#part-5-testing-checklist)

---

## Part 1: Create the Case Issues Microsoft List

This new list stores individual issues that reviewers log against cases.

### Steps

1. Go to **SharePoint** or **Microsoft Lists** (lists.microsoft.com)
2. Click **+ New list** → **Blank list**
3. Name it **Case Issues**
4. Add the following columns:

| Column Name    | Type              | Details |
|----------------|-------------------|---------|
| Title          | Single line text  | Rename to **Issue ID** (auto-generated, or use the default Title column) |
| SubcaseID      | Single line text  | The Sub-case ID this issue belongs to (we use text to match your Cases list) |
| IssueDescription | Multiple lines of text | Set to **Plain text**, not rich text |
| IssueType      | Choice            | Add your choices (e.g., Documentation Error, Calculation Error, Missing Information, Procedural Error, Formatting Issue, Other) |
| IssueTier      | Choice            | Choices: **T1**, **T2**, **T3** |
| SOReply        | Multiple lines of text | Plain text — reportee's response |
| IssueStatus    | Choice            | Choices: **Open**, **Completed** — Default: **Open** |
| ReviewRound    | Number            | Default value: **1** — tracks which review round the issue was created in |
| CreatedByUser  | Person            | Automatically captured or manually set |

### How to add a column

1. In the list, click **+ Add column** (top right of the column headers)
2. Select the column type (Text, Choice, Number, Person)
3. Enter the column name
4. For **Choice** columns, add each option on a separate line
5. Click **Save**

> **Tip:** You can reorder columns by dragging the column headers.

---

## Part 2: Update Your Existing Cases List

Ensure your existing Cases list has the **Task status** column (Choice type) with these options:

- Ready for Review
- In Review
- Reviewed
- Case Completed

If these choices don't exist yet:
1. Click the **Task status** column header → **Column settings** → **Edit**
2. Add any missing choices
3. Click **Save**

Also verify the **Reviewer** column exists (Person type). This is used for notifications.

---

## Part 3: Build the Power App

### 3.1 — Create a New Canvas App

1. Go to [make.powerapps.com](https://make.powerapps.com)
2. Click **+ Create** → **Blank app** → **Blank canvas app**
3. Name it **Lab Case Tracker**
4. Choose **Tablet** format (better for data-heavy screens)
5. Click **Create**

### 3.2 — Connect Data Sources

1. In the left panel, click the **Data** icon (cylinder)
2. Click **+ Add data**
3. Search for **SharePoint**
4. Select your SharePoint site
5. Select both lists:
   - Your **Cases** list (the existing one)
   - **Case Issues** (the new one)
6. Click **Connect**

> **Note:** The list names below assume your Cases list is called `Cases` and the issues list is called `CaseIssues`. Replace with your actual list names in all formulas.

### 3.3 — Set Up a Global Variable for Role

We'll use a variable to track whether the user is a Reviewer or Reportee.

1. Select **App** in the Tree view (left panel)
2. Set **OnStart** to:

```
Set(varRole, "");
Set(varSelectedCase, Blank());
Set(varCurrentRound, 1)
```

---

### 3.4 — Screen 1: Home Screen (Role Selection)

**Add controls:**

1. **Label** — Title
   - Text: `"Lab Case Tracker"`
   - Font size: 28, Bold, centered
   - Position: center top

2. **Label** — Subtitle
   - Text: `"Select your role to get started"`
   - Font size: 16, color gray

3. **Button** — Reviewer
   - Text: `"Reviewer"`
   - OnSelect:
   ```
   Set(varRole, "Reviewer");
   Navigate(ScreenReviewerList, ScreenTransition.Fade)
   ```
   - Fill: `RGBA(0, 120, 212, 1)` (Microsoft blue)
   - Size: 220 x 80

4. **Button** — Reportee
   - Text: `"Reportee"`
   - OnSelect:
   ```
   Set(varRole, "Reportee");
   Navigate(ScreenReporteeList, ScreenTransition.Fade)
   ```
   - Fill: `RGBA(0, 120, 212, 1)`
   - Size: 220 x 80

5. **Icon / Image** (optional) — add a search icon for Reviewer and a document icon for Reportee above each button.

---

### 3.5 — Screen 2: Reviewer Case List

Create a new screen: **Insert** → **New screen** → **Blank**. Rename to `ScreenReviewerList`.

**Add controls:**

1. **Label** — Title
   - Text: `"Cases — Ready for Review"`
   - Font size: 22, Bold

2. **Dropdown** — Status Filter
   - Items: `["Ready for Review", "In Review", "All Active"]`
   - Name it `drpReviewerStatus`
   - Default: `"Ready for Review"`

3. **Text Input** — Search box
   - Name it `txtReviewerSearch`
   - HintText: `"Search by Sub-case ID..."`

4. **Gallery** — Vertical gallery (blank template)
   - Name it `galReviewerCases`
   - Items formula:

   ```
   SortByColumns(
       Filter(
           Cases,
           // Status filter
           If(
               drpReviewerStatus.Selected.Value = "All Active",
               'Task status'.Value <> "Case Completed",
               'Task status'.Value = drpReviewerStatus.Selected.Value
           ),
           // Search filter
           Or(
               txtReviewerSearch.Text = "",
               StartsWith('Sub-case ID', txtReviewerSearch.Text)
           )
       ),
       "Due date",
       SortOrder.Ascending
   )
   ```

5. **Inside the gallery**, add labels for each visible field:
   - `ThisItem.'Sub-case ID'`
   - `ThisItem.'Submission date'`
   - `ThisItem.'Due date'`
   - `ThisItem.'Case Type'`
   - `ThisItem.'FLOW case?'`
   - `ThisItem.'No. of Exhibits'`
   - `ThisItem.'ID SO'`
   - `ThisItem.Reviewer.DisplayName`
   - `ThisItem.'Task status'.Value`

6. **Button** inside gallery — "Start Review"
   - Visible: `ThisItem.'Task status'.Value = "Ready for Review"`
   - OnSelect:
   ```
   Patch(
       Cases,
       ThisItem,
       {'Task status': {Value: "In Review"}}
   );
   Set(varSelectedCase, ThisItem);
   Navigate(ScreenReviewerDetail, ScreenTransition.Fade)
   ```

7. **Gallery OnSelect** (for clicking the row):
   ```
   Set(varSelectedCase, ThisItem);
   Navigate(ScreenReviewerDetail, ScreenTransition.Fade)
   ```

8. **Button** — Back to Home
   - Text: `"← Switch Role"`
   - OnSelect: `Navigate(ScreenHome, ScreenTransition.Fade)`

---

### 3.6 — Screen 3: Reviewer Case Detail / Issue Entry

Create a new screen: `ScreenReviewerDetail`.

#### A — Case Info Header

Add a **Display Form** or individual labels:

```
varSelectedCase.'Sub-case ID'
varSelectedCase.'Submission date'
varSelectedCase.'Due date'
varSelectedCase.'Case Type'
varSelectedCase.'FLOW case?'
varSelectedCase.'No. of Exhibits'
varSelectedCase.'ID SO'
varSelectedCase.Reviewer.DisplayName
varSelectedCase.'Task status'.Value
```

Arrange these in a grid layout (3 columns x 3 rows of labels).

#### B — Existing Issues Gallery

1. **Gallery** — Name it `galIssues`
   - Items:
   ```
   SortByColumns(
       Filter(
           CaseIssues,
           SubcaseID = varSelectedCase.'Sub-case ID'
       ),
       "ReviewRound",
       SortOrder.Ascending
   )
   ```

2. Inside the gallery, add labels:
   - Issue Tier: `ThisItem.IssueTier.Value` — add conditional color:
     ```
     If(ThisItem.IssueTier.Value = "T1", RGBA(164,38,44,1),
        ThisItem.IssueTier.Value = "T2", RGBA(131,92,0,1),
        RGBA(0,69,120,1))
     ```
   - Issue Type: `ThisItem.IssueType.Value`
   - Description: `ThisItem.IssueDescription`
   - Round: `"Round " & ThisItem.ReviewRound`
   - Status: `ThisItem.IssueStatus.Value`
   - SO Reply (if exists):
     ```
     If(!IsBlank(ThisItem.SOReply), "SO Reply: " & ThisItem.SOReply, "")
     ```

#### C — Add Issue Form

1. **Text Input** (multiline) — Name: `txtIssueDesc`
   - Mode: `TextMode.MultiLine`
   - HintText: `"Describe the issue found..."`

2. **Dropdown** — Name: `drpIssueType`
   - Items: `Choices(CaseIssues.IssueType)`

3. **Dropdown** — Name: `drpIssueTier`
   - Items: `Choices(CaseIssues.IssueTier)`

4. **Button** — "Add Issue"
   - OnSelect:
   ```
   If(
       IsBlank(txtIssueDesc.Text) || IsBlank(drpIssueType.Selected.Value) || IsBlank(drpIssueTier.Selected.Value),
       Notify("Please fill in all fields.", NotificationType.Warning),
       Patch(
           CaseIssues,
           Defaults(CaseIssues),
           {
               SubcaseID: varSelectedCase.'Sub-case ID',
               IssueDescription: txtIssueDesc.Text,
               IssueType: drpIssueType.Selected,
               IssueTier: drpIssueTier.Selected,
               IssueStatus: {Value: "Open"},
               ReviewRound: Coalesce(
                   Max(
                       Filter(CaseIssues, SubcaseID = varSelectedCase.'Sub-case ID'),
                       ReviewRound
                   ),
                   1
               )
           }
       );
       Reset(txtIssueDesc);
       Reset(drpIssueType);
       Reset(drpIssueTier);
       Notify("Issue added.", NotificationType.Success)
   )
   ```

#### D — Action Buttons

1. **Button** — "Mark as Reviewed"
   - OnSelect:
   ```
   If(
       CountRows(Filter(CaseIssues, SubcaseID = varSelectedCase.'Sub-case ID')) = 0,
       Notify("Add at least one issue before marking as Reviewed.", NotificationType.Warning),
       Patch(
           Cases,
           varSelectedCase,
           {'Task status': {Value: "Reviewed"}}
       );
       Notify(varSelectedCase.'Sub-case ID' & " marked as Reviewed.", NotificationType.Success);
       Navigate(ScreenReviewerList, ScreenTransition.Fade)
   )
   ```
   - Fill: `RGBA(216, 59, 1, 1)` (orange-red)

2. **Button** — "Case Completed"
   - OnSelect:
   ```
   Patch(
       Cases,
       varSelectedCase,
       {'Task status': {Value: "Case Completed"}}
   );
   Notify(varSelectedCase.'Sub-case ID' & " marked as Case Completed.", NotificationType.Success);
   Navigate(ScreenReviewerList, ScreenTransition.Fade)
   ```
   - Fill: `RGBA(16, 124, 16, 1)` (green)

3. **Button** — "← Back to Case List"
   - OnSelect: `Navigate(ScreenReviewerList, ScreenTransition.Fade)`

---

### 3.7 — Screen 4: Reportee Case List

Create a new screen: `ScreenReporteeList`.

This is similar to the Reviewer list but filtered for the reportee's cases.

1. **Dropdown** — Status Filter (`drpReporteeStatus`)
   - Items: `["Reviewed", "All My Cases"]`

2. **Text Input** — Search (`txtReporteeSearch`)

3. **Gallery** — `galReporteeCases`
   - Items:
   ```
   SortByColumns(
       Filter(
           Cases,
           If(
               drpReporteeStatus.Selected.Value = "All My Cases",
               true,
               'Task status'.Value = "Reviewed"
           ),
           Or(
               txtReporteeSearch.Text = "",
               StartsWith('Sub-case ID', txtReporteeSearch.Text)
           )
       ),
       "Due date",
       SortOrder.Ascending
   )
   ```

   > **Note:** If you want to filter only the reportee's own cases, add this condition:
   > `'ID SO'.Email = User().Email` (assuming ID SO is the reportee's person column)

4. Inside gallery, show the same columns plus an **open issue count**:
   ```
   CountRows(
       Filter(
           CaseIssues,
           SubcaseID = ThisItem.'Sub-case ID',
           IssueStatus.Value = "Open"
       )
   ) & " open issues"
   ```

5. **Gallery OnSelect**:
   ```
   Set(varSelectedCase, ThisItem);
   Navigate(ScreenReporteeDetail, ScreenTransition.Fade)
   ```

---

### 3.8 — Screen 5: Reportee Issue Response

Create a new screen: `ScreenReporteeDetail`.

#### A — Case Info Header

Same as the Reviewer detail header (read-only labels showing `varSelectedCase` fields).

#### B — Issues Gallery with Reply

1. **Gallery** — `galReporteeIssues`
   - Items:
   ```
   Filter(
       CaseIssues,
       SubcaseID = varSelectedCase.'Sub-case ID'
   )
   ```

2. Inside gallery, add:
   - Labels for: Tier, Type, Description, Round
   - **Text Input** (multiline) for SO Reply:
     - Name: `txtSOReply`
     - Default: `ThisItem.SOReply`
     - HintText: `"Enter your response..."`
   - **Checkbox** — Mark as Completed:
     - Name: `chkCompleted`
     - Default: `If(ThisItem.IssueStatus.Value = "Completed", true, false)`
   - **Button** — "Save Reply" (inside the gallery):
     - OnSelect:
     ```
     Patch(
         CaseIssues,
         ThisItem,
         {
             SOReply: txtSOReply.Text,
             IssueStatus: If(chkCompleted.Value, {Value: "Completed"}, {Value: "Open"})
         }
     );
     Notify("Reply saved.", NotificationType.Success)
     ```

#### C — Submit Button

1. **Button** — "Submit & Return to Ready for Review"
   - OnSelect:
   ```
   Patch(
       Cases,
       varSelectedCase,
       {'Task status': {Value: "Ready for Review"}}
   );
   Notify(varSelectedCase.'Sub-case ID' & " returned to Ready for Review.", NotificationType.Success);
   Navigate(ScreenReporteeList, ScreenTransition.Fade)
   ```
   - **DisplayMode** (to disable when not all issues completed):
   ```
   If(
       CountRows(
           Filter(
               CaseIssues,
               SubcaseID = varSelectedCase.'Sub-case ID',
               IssueStatus.Value = "Open"
           )
       ) = 0 &&
       CountRows(
           Filter(
               CaseIssues,
               SubcaseID = varSelectedCase.'Sub-case ID'
           )
       ) > 0,
       DisplayMode.Edit,
       DisplayMode.Disabled
   )
   ```

2. **Label** — Pending message
   - Text:
   ```
   If(
       Self.DisplayMode = DisplayMode.Disabled,
       "All issues must be marked as Completed before submitting.",
       ""
   )
   ```
   - Replace `Self` with reference to the submit button.

---

## Part 4: Power Automate — Teams Notifications

### 4.1 — Flow 1: Notify Reportee When Status Changes to "Reviewed"

This notifies the reportee (ID SO) that their case has been reviewed and has issues.

1. Go to [make.powerautomate.com](https://make.powerautomate.com)
2. Click **+ Create** → **Automated cloud flow**
3. Name: **Notify Reportee — Case Reviewed**
4. Trigger: **When an item is modified** (SharePoint)
   - Site Address: your SharePoint site
   - List Name: your Cases list

5. Add a **Condition**:
   - `Task status Value` **is equal to** `Reviewed`

6. **If yes** branch — add action: **Post message in a chat or channel** (Microsoft Teams)
   - Post as: **Flow bot**
   - Post in: **Channel** (select your lab team and channel)
   - Message:
   ```
   🔍 Case Reviewed — Action Required

   Sub-case ID: [Sub-case ID from the trigger]
   Case Type: [Case Type from the trigger]
   Reviewer: [Reviewer DisplayName from the trigger]

   Issues have been found. Please open the Lab Case Tracker app to review and respond.
   ```

7. Click **Save**

### 4.2 — Flow 2: Notify Reviewer When Status Changes Back to "Ready for Review"

This notifies the original reviewer that the reportee has addressed the issues.

1. Create another **Automated cloud flow**
2. Name: **Notify Reviewer — Ready for Re-review**
3. Trigger: **When an item is modified** (SharePoint)
   - Same site and list

4. Add a **Condition**:
   - `Task status Value` **is equal to** `Ready for Review`

5. **If yes** — to send notification to the specific reviewer:
   - Add action: **Get user profile (V2)** (Office 365 Users)
     - User (UPN): `Reviewer Email` from the trigger
   - Add action: **Post message in a chat or channel** (Microsoft Teams)
     - Post as: **Flow bot**
     - Post in: **Chat with Flow bot**
     - Recipient: the Reviewer's email from the trigger
     - Message:
     ```
     ✅ Case Ready for Re-review

     Sub-case ID: [Sub-case ID]
     Case Type: [Case Type]

     The reportee has addressed the issues. Please open the Lab Case Tracker app to review.
     ```

6. Click **Save**

### 4.3 — Preventing Duplicate Triggers

Since the flow triggers on **any** modification, add a condition to check the status value. The condition step above already handles this, but for extra safety:

- Add a **Trigger condition** (in the trigger's settings → "…" → Settings → Trigger Conditions):
  - For Flow 1: `@equals(triggerOutputs()?['body/TaskStatus/Value'], 'Reviewed')`
  - For Flow 2: `@equals(triggerOutputs()?['body/TaskStatus/Value'], 'Ready for Review')`

> **Note:** Replace `TaskStatus` with the actual internal name of your Task status column. You can find this in list settings → click the column → look at the URL for `Field=`.

---

## Part 5: Testing the Full Workflow

Use this checklist to test the complete cycle:

### Test 1: Reviewer Flow

- [ ] Open the app, select **Reviewer**
- [ ] Verify cases with "Ready for Review" status appear
- [ ] Click **Start Review** on a case — verify status changes to "In Review"
- [ ] Add an issue with description, type, and tier — verify it appears in the list
- [ ] Add a second issue — verify both show
- [ ] Click **Mark as Reviewed** — verify status changes and you return to the case list
- [ ] Verify the Teams notification is sent to the reportee

### Test 2: Reportee Flow

- [ ] Open the app, select **Reportee**
- [ ] Verify the case with "Reviewed" status appears with open issue count
- [ ] Click the case — verify all issues are displayed
- [ ] Enter SO Reply for each issue
- [ ] Mark each issue as Completed
- [ ] Verify the **Submit** button enables when all issues are completed
- [ ] Click **Submit & Return to Ready for Review**
- [ ] Verify the Teams notification is sent to the reviewer

### Test 3: Re-review Cycle

- [ ] Switch to Reviewer role
- [ ] Filter for "Ready for Review" — verify the case reappears
- [ ] Open the case — verify previous issues show with SO Replies
- [ ] Add a new issue (should be a new round) or mark as **Case Completed**
- [ ] Verify the full cycle works end-to-end

### Test 4: Edge Cases

- [ ] Try to mark as Reviewed with zero issues — should show warning
- [ ] Try to submit as reportee with open issues — button should be disabled
- [ ] Search/filter on both case lists — verify they work
- [ ] Verify data persists in Microsoft Lists (open the lists directly to check)

---

## Tips and Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| Dropdown shows no choices | Ensure `Items` is set to `Choices(CaseIssues.IssueType)` not a hardcoded list |
| Gallery not refreshing after Patch | Add `Refresh(Cases)` or `Refresh(CaseIssues)` after the Patch command |
| Person column shows blank | Use `.DisplayName` to show the name, e.g., `ThisItem.Reviewer.DisplayName` |
| Flow triggers multiple times | Add trigger conditions (see section 4.3) |
| "Delegation warning" on Filter | This is normal for < 2000 items. For larger lists, add indexes to filtered columns in list settings |

### Refresh Pattern

After any `Patch()` call, add `Refresh()` to ensure the gallery shows updated data:

```
Patch(Cases, varSelectedCase, {'Task status': {Value: "Reviewed"}});
Refresh(Cases);
Navigate(ScreenReviewerList, ScreenTransition.Fade)
```

### Styling Tips

- Use consistent colors from the prototype:
  - Primary blue: `RGBA(0, 120, 212, 1)`
  - Success green: `RGBA(16, 124, 16, 1)`
  - Warning red: `RGBA(164, 38, 44, 1)`
  - Background: `RGBA(243, 242, 241, 1)`
- Set all screen Fill to `RGBA(243, 242, 241, 1)` for the light gray background
- Use rectangles with Fill `RGBA(255, 255, 255, 1)` and rounded corners as card containers

---

## Summary of Screens

| # | Screen Name | Role | Purpose |
|---|------------|------|---------|
| 1 | ScreenHome | Both | Role selection |
| 2 | ScreenReviewerList | Reviewer | View and filter cases for review |
| 3 | ScreenReviewerDetail | Reviewer | View case details, add issues, change status |
| 4 | ScreenReporteeList | Reportee | View cases that need issue responses |
| 5 | ScreenReporteeDetail | Reportee | Reply to issues, mark completed, submit back |

## Summary of Lists

| List | Purpose |
|------|---------|
| Cases (existing) | Stores case metadata and status |
| Case Issues (new) | Stores individual issues per case with replies |
