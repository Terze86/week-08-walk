# Lab Case Tracking App — Complete Power Apps Build Guide

This guide walks a complete beginner through every single step of building a Power Apps canvas app for lab case review tracking. Every screen, every control, every formula, and every setting is documented in full. Read the entire guide once before you start — understanding the whole structure will make each individual step much clearer.

**What you will build:**
- A tablet-format Power Apps canvas app (1366 × 768 px)
- 6 screens covering both the Reviewer and Reportee workflows
- Integration with two Microsoft Lists (SharePoint)
- Two Power Automate flows for Microsoft Teams notifications

**Prerequisites:**
- A Microsoft 365 account with licences for Power Apps, Power Automate, SharePoint/Microsoft Lists, and Microsoft Teams
- The existing **Lab Cases** SharePoint list (already set up in your site)
- A web browser open at [make.powerapps.com](https://make.powerapps.com)
- A second tab open at [make.powerautomate.com](https://make.powerautomate.com)

---

## How to Read This Guide

Every control section contains a **Properties table** like this:

| Property | Value |
|----------|-------|
| X | 20 |
| Y | 68 |
| Width | 400 |

- **X** and **Y** are the top-left corner of the control on the canvas (in pixels).
- **Width** and **Height** are the size of the control (in pixels).
- **Text**, **Items**, **Default** etc. are the formula or value you type into the formula bar.
- When you see `RGBA(0, 120, 212, 1)` that is the exact colour code you enter in the Fill or Color property.

### Where is the formula bar?

The formula bar sits at the very top of the Power Apps Studio, just below the toolbar. It looks like a long text box. Whenever you click a control on the canvas or select a property in the right-hand Properties pane, the formula bar shows the current value. To edit it, click inside the bar, delete the existing content, and type the new formula.

### How to rename a control

In the left panel (the Tree View), right-click any control and choose **Rename**. Give it the name shown in this guide. Consistent naming is essential — every formula in this guide refers to controls by name.

### How to reference SharePoint columns with spaces

If a SharePoint column name contains a space (e.g., `Sub-case ID`) you must wrap it in single quotes inside formulas:

```
ThisItem.'Sub-case ID'
```

Without the single quotes, Power Apps will show a red error under the formula.

---

## Table of Contents

1. [Part 1 — Create the Case Issues Microsoft List](#part-1--create-the-case-issues-microsoft-list)
2. [Part 2 — Verify the Lab Cases List](#part-2--verify-the-lab-cases-list)
3. [Part 3 — Create the Power App and Connect Data](#part-3--create-the-power-app-and-connect-data)
4. [Part 4 — App OnStart Variables](#part-4--app-onstart-variables)
5. [Part 5 — Screen by Screen Build](#part-5--screen-by-screen-build)
   - [Screen 1: HomeScreen](#screen-1-homescreen)
   - [Screen 2: ReviewerCaseListScreen](#screen-2-reviewercaselistscreen)
   - [Screen 3: ReviewerCaseDetailScreen](#screen-3-reviewercasedetailscreen)
   - [Screen 4: LIMSCopyScreen](#screen-4-limscopysceen)
   - [Screen 5: ReporteeCaseListScreen](#screen-5-reporteecaselistscreen)
   - [Screen 6: ReporteeIssueScreen](#screen-6-reporteeissuescreen)
6. [Part 6 — Power Automate Flows](#part-6--power-automate-flows)
7. [Part 7 — Testing Checklist](#part-7--testing-checklist)

---

## Design Reference (Global Constants)

Keep these values in mind throughout the build. They apply to every screen.

| Setting | Value |
|---------|-------|
| Canvas width | 1366 |
| Canvas height | 768 |
| Header bar Y | 0 |
| Header bar Height | 60 |
| Header bar Fill | `RGBA(0, 120, 212, 1)` |
| Content start Y | 68 |
| Left margin X | 20 |
| Right edge limit (X + Width) | 1346 |
| Screen background Fill | `RGBA(243, 242, 241, 1)` |
| Card background Fill | `RGBA(255, 255, 255, 1)` |
| Primary blue | `RGBA(0, 120, 212, 1)` |
| Dark text colour | `RGBA(50, 49, 48, 1)` |
| Muted text colour | `RGBA(96, 94, 92, 1)` |
| Standard button Height | 40 |
| Standard label Height | 32 |
| Gallery row height | 52 |
| Font (all controls) | `Font.'Segoe UI'` |

**Status badge colours:**

| Status | Fill | Color |
|--------|------|-------|
| Ready for Review | `RGBA(255, 244, 206, 1)` | `RGBA(131, 92, 0, 1)` |
| In Review | `RGBA(210, 232, 255, 1)` | `RGBA(0, 69, 120, 1)` |
| Reviewed | `RGBA(255, 224, 214, 1)` | `RGBA(164, 38, 44, 1)` |
| Case Completed | `RGBA(223, 246, 221, 1)` | `RGBA(16, 124, 16, 1)` |

**Issue tier badge colours:**

| Tier | Fill | Color |
|------|------|-------|
| T1 — Minor | `RGBA(232, 245, 233, 1)` | `RGBA(46, 125, 50, 1)` |
| T2 — Major | `RGBA(255, 248, 225, 1)` | `RGBA(245, 127, 23, 1)` |
| T3 — Critical | `RGBA(255, 235, 238, 1)` | `RGBA(198, 40, 40, 1)` |

---

## Part 1 — Create the Case Issues Microsoft List

This new SharePoint list stores every issue that a reviewer logs against a case. Each item in this list belongs to one case in the Lab Cases list, linked by the case's SharePoint ID.

### Step-by-step

1. Open a browser and go to your **SharePoint site** (the same site that holds the Lab Cases list). You can also go to [lists.microsoft.com](https://lists.microsoft.com) and click **+ New list**.
2. Click **+ New list**.
3. Click **Blank list**.
4. In the **Name** field type: `Case Issues`
5. Leave **Show in site navigation** checked.
6. Click **Create**.

You will now see an empty list with just a **Title** column. Leave the Title column as-is. It will serve as an auto-reference field.

### Add the following columns

For each column below, click **+ Add column** at the right end of the column headers, select the column type, fill in the settings, and click **Save**.

#### Column 1: CaseID

| Setting | Value |
|---------|-------|
| Column type | Number |
| Name | `CaseID` |
| Description | Stores the SharePoint ID (integer) of the linked Lab Cases item |
| Required | No |
| Default value | (leave blank) |

#### Column 2: SubcaseID

| Setting | Value |
|---------|-------|
| Column type | Single line of text |
| Name | `SubcaseID` |
| Description | Copy of the Sub-case ID from the Lab Cases list — used for display and filtering |
| Required | No |

#### Column 3: IssueDescription

| Setting | Value |
|---------|-------|
| Column type | Multiple lines of text |
| Name | `IssueDescription` |
| Specify the type of text allowed | Plain text |
| Required | No |

#### Column 4: IssueType

| Setting | Value |
|---------|-------|
| Column type | Choice |
| Name | `IssueType` |
| Choices (one per line) | Documentation Error |
| | Calculation Error |
| | Missing Information |
| | Procedural Error |
| | Formatting Issue |
| | Other |
| Allow manual entry | Yes |
| Default value | (none) |

#### Column 5: IssueTier

| Setting | Value |
|---------|-------|
| Column type | Choice |
| Name | `IssueTier` |
| Choices (one per line) | T1 |
| | T2 |
| | T3 |
| Default value | T1 |

#### Column 6: SOReply

| Setting | Value |
|---------|-------|
| Column type | Multiple lines of text |
| Name | `SOReply` |
| Specify the type of text allowed | Plain text |
| Description | The reportee's written response to this issue |

#### Column 7: IssueStatus

| Setting | Value |
|---------|-------|
| Column type | Choice |
| Name | `IssueStatus` |
| Choices (one per line) | Open |
| | Completed |
| Default value | Open |

#### Column 8: ReportInLIMS

| Setting | Value |
|---------|-------|
| Column type | Yes/No |
| Name | `ReportInLIMS` |
| Default value | Yes (checked) |

#### Column 9: ReviewRound

| Setting | Value |
|---------|-------|
| Column type | Number |
| Name | `ReviewRound` |
| Default value | 1 |
| Description | Tracks which review round this issue was created in |

---

## Part 2 — Verify the Lab Cases List

Check that your existing **Lab Cases** list has all the required columns. If any are missing, add them now using the same method described above.

### Required columns

| Column display name | Internal / formula name | Type | Notes |
|---------------------|------------------------|------|-------|
| Title | `Title` | Single line | Default SharePoint column — leave as-is |
| Sub-case ID | `'Sub-case ID'` | Single line | The unique case reference number |
| Submission date | `'Submission date'` | Date only | |
| Due date | `'Due date'` | Date only | |
| Case Type | `'Case Type'` | Choice | Your lab's case type values |
| FLOW case? | `'FLOW case?'` | Yes/No | Indicates if the case is a FLOW case |
| No. of Exhibits | `'No. of Exhibits'` | Number | |
| ID SO | `'ID SO'` | Person | The reportee (submitting officer) |
| Reviewer | `Reviewer` | Person | The reviewer assigned |
| Task status | `'Task status'` | Choice | Must have exactly: Ready for Review, In Review, Reviewed, Case Completed |
| Remarks | `Remarks` | Multiple lines | Optional notes |

### Verify Task status choices

1. Click the **Task status** column header.
2. Click **Column settings** → **Edit**.
3. Make sure these four choices exist exactly as written (case-sensitive):
   - `Ready for Review`
   - `In Review`
   - `Reviewed`
   - `Case Completed`
4. Click **Save**.

---

## Part 3 — Create the Power App and Connect Data

### 3.1 Create a new Canvas App

1. Go to [make.powerapps.com](https://make.powerapps.com).
2. In the left navigation, click **+ Create**.
3. Click **Blank app**.
4. Click **Blank canvas app**.
5. In the **App name** field type: `Lab Case Tracker`
6. Under **Format**, select **Tablet**.
7. Click **Create**.

Power Apps Studio opens. You will see a blank white canvas in the centre, a left panel (Tree View), a right panel (Properties), and a top toolbar.

### 3.2 Set the canvas size

Power Apps tablet layout defaults to 1366 × 768 but let us confirm:

1. Click **File** (top-left) → **Settings**.
2. Under **Screen size + orientation**, verify Width is `1366` and Height is `768`.
3. If not, set them manually and click **Apply**.
4. Click the back arrow to return to the canvas.

### 3.3 Set the screen background

1. Click anywhere on the blank white canvas (the screen itself, not a control).
2. In the right Properties panel, click **Fill**.
3. Click **Custom** and enter the hex code `F3F2F1` (or use the RGBA formula `RGBA(243, 242, 241, 1)`).

### 3.4 Connect the SharePoint data sources

1. In the left panel, click the **Data** icon (looks like a cylinder/database).
2. Click **+ Add data**.
3. In the search box type `SharePoint`.
4. Click **SharePoint** in the results.
5. A dialog asks for the SharePoint site URL. Paste your site URL (e.g., `https://yourcompany.sharepoint.com/sites/YourSite`) and click the arrow.
6. You will see a list of lists on that site. Check the box next to **Lab Cases**.
7. Check the box next to **Case Issues**.
8. Click **Connect**.

Both lists now appear in the Data pane on the left. In all formulas throughout this guide, the lists are referenced as `'Lab Cases'` and `'Case Issues'` (with single quotes because they contain spaces).

---

## Part 4 — App OnStart Variables

Global variables are values that are accessible from any screen. We initialise them when the app first opens.

### How to set App OnStart

1. In the left Tree View panel, click **App** (it is at the very top of the tree, above all screens).
2. In the top-left dropdown (the property selector, just above the formula bar), make sure it says **OnStart**.
3. Click in the formula bar and replace everything with:

```
Set(gblUserRole, "");
Set(gblSelectedCase, Blank());
Set(gblLIMSText, "")
```

**What each line does:**
- `Set(gblUserRole, "")` — Creates a global variable called `gblUserRole` and sets it to empty text. This will later hold either `"Reviewer"` or `"Reportee"`.
- `Set(gblSelectedCase, Blank())` — Creates `gblSelectedCase` which will hold the full record (row) of whichever case the user taps. `Blank()` means it starts as nothing.
- `Set(gblLIMSText, "")` — Creates `gblLIMSText` which will hold the formatted text to copy to the LIMS system.

---

## Part 5 — Screen by Screen Build

### How to add a new screen

1. In the Tree View left panel, right-click on the current screen name.
2. Click **Add screen** → **Blank**.
3. Right-click the new screen in the tree and click **Rename**.
4. Type the screen name as shown in this guide.

Repeat this to create all 6 screens before you start adding controls. Name them:
- `HomeScreen`
- `ReviewerCaseListScreen`
- `ReviewerCaseDetailScreen`
- `LIMSCopyScreen`
- `ReporteeCaseListScreen`
- `ReporteeIssueScreen`

---

### Screen 1: HomeScreen

This is the landing screen. The user selects their role here and is sent to the appropriate case list.

**Overview of controls on this screen:**

| Control | Type | Purpose |
|---------|------|---------|
| HomeHeader | Rectangle | Blue top bar |
| HomeHeaderTitle | Label | App title in the header |
| HomeCenterTitle | Label | Large title in the middle of the page |
| HomeCenterSubtitle | Label | Subtitle text |
| ReviewerCard | Rectangle | Card background for Reviewer button |
| ReviewerIcon | Icon | Magnifying glass |
| ReviewerCardTitle | Label | "Reviewer" |
| ReviewerCardSubtitle | Label | "Review cases & log issues" |
| ReviewerCardButton | Button | Invisible tap target over the card |
| ReporteeCard | Rectangle | Card background for Reportee button |
| ReporteeIcon | Icon | Document/memo icon |
| ReporteeCardTitle | Label | "Reportee" |
| ReporteeCardSubtitle | Label | "Respond to issues & update status" |
| ReporteeCardButton | Button | Invisible tap target over the card |

#### Control: HomeHeader (Rectangle)

This is the blue bar across the top of every screen.

In the **Insert** menu (top toolbar), click **Shapes** → **Rectangle**. Rename it `HomeHeader`.

| Property | Value |
|----------|-------|
| X | 0 |
| Y | 0 |
| Width | 1366 |
| Height | 60 |
| Fill | `RGBA(0, 120, 212, 1)` |
| BorderThickness | 0 |

#### Control: HomeHeaderTitle (Label)

In the **Insert** menu, click **Text** → **Label**. Rename it `HomeHeaderTitle`.

| Property | Value |
|----------|-------|
| X | 20 |
| Y | 0 |
| Width | 400 |
| Height | 60 |
| Text | `"Lab Case Tracker"` |
| Color | `RGBA(255, 255, 255, 1)` |
| FontSize | 18 |
| FontWeight | `FontWeight.Bold` |
| Font | `Font.'Segoe UI'` |
| VerticalAlign | `VerticalAlign.Middle` |
| Fill | `RGBA(0, 0, 0, 0)` |
| BorderThickness | 0 |

#### Control: HomeCenterTitle (Label)

| Property | Value |
|----------|-------|
| X | 383 |
| Y | 200 |
| Width | 600 |
| Height | 50 |
| Text | `"Lab Case Tracker"` |
| Color | `RGBA(50, 49, 48, 1)` |
| FontSize | 32 |
| FontWeight | `FontWeight.Bold` |
| Font | `Font.'Segoe UI'` |
| Align | `Align.Center` |
| Fill | `RGBA(0, 0, 0, 0)` |
| BorderThickness | 0 |

#### Control: HomeCenterSubtitle (Label)

| Property | Value |
|----------|-------|
| X | 383 |
| Y | 258 |
| Width | 600 |
| Height | 32 |
| Text | `"Select your role to get started"` |
| Color | `RGBA(96, 94, 92, 1)` |
| FontSize | 16 |
| FontWeight | `FontWeight.Normal` |
| Align | `Align.Center` |
| Fill | `RGBA(0, 0, 0, 0)` |
| BorderThickness | 0 |

#### Control: ReviewerCard (Rectangle)

Insert → Shapes → Rectangle. Rename to `ReviewerCard`.

| Property | Value |
|----------|-------|
| X | 303 |
| Y | 320 |
| Width | 340 |
| Height | 200 |
| Fill | `RGBA(255, 255, 255, 1)` |
| BorderColor | `RGBA(225, 223, 221, 1)` |
| BorderThickness | 1 |
| RadiusTopLeft | 8 |
| RadiusTopRight | 8 |
| RadiusBottomLeft | 8 |
| RadiusBottomRight | 8 |

#### Control: ReviewerIcon (Icon)

Insert → Icons → Search (magnifying glass). Rename to `ReviewerIcon`.

| Property | Value |
|----------|-------|
| X | 443 |
| Y | 348 |
| Width | 60 |
| Height | 60 |
| Color | `RGBA(0, 120, 212, 1)` |
| Fill | `RGBA(0, 0, 0, 0)` |

#### Control: ReviewerCardTitle (Label)

| Property | Value |
|----------|-------|
| X | 303 |
| Y | 424 |
| Width | 340 |
| Height | 36 |
| Text | `"Reviewer"` |
| Color | `RGBA(50, 49, 48, 1)` |
| FontSize | 20 |
| FontWeight | `FontWeight.Bold` |
| Align | `Align.Center` |
| Fill | `RGBA(0, 0, 0, 0)` |

#### Control: ReviewerCardSubtitle (Label)

| Property | Value |
|----------|-------|
| X | 303 |
| Y | 464 |
| Width | 340 |
| Height | 32 |
| Text | `"Review cases & log issues"` |
| Color | `RGBA(96, 94, 92, 1)` |
| FontSize | 13 |
| Align | `Align.Center` |
| Fill | `RGBA(0, 0, 0, 0)` |

#### Control: ReviewerCardButton (Button)

This invisible button sits on top of the card so the entire card is clickable.

Insert → Button. Rename to `ReviewerCardButton`.

| Property | Value |
|----------|-------|
| X | 303 |
| Y | 320 |
| Width | 340 |
| Height | 200 |
| Text | `""` |
| Fill | `RGBA(0, 0, 0, 0)` |
| HoverFill | `RGBA(0, 120, 212, 0.1)` |
| PressedFill | `RGBA(0, 120, 212, 0.2)` |
| BorderThickness | 0 |
| OnSelect | `Set(gblUserRole, "Reviewer"); Navigate(ReviewerCaseListScreen, ScreenTransition.Fade)` |

**What the OnSelect formula does:** It sets the global variable `gblUserRole` to the text `"Reviewer"`, then tells Power Apps to go to the `ReviewerCaseListScreen` using a smooth fade transition.

#### Control: ReporteeCard (Rectangle)

| Property | Value |
|----------|-------|
| X | 723 |
| Y | 320 |
| Width | 340 |
| Height | 200 |
| Fill | `RGBA(255, 255, 255, 1)` |
| BorderColor | `RGBA(225, 223, 221, 1)` |
| BorderThickness | 1 |
| RadiusTopLeft | 8 |
| RadiusTopRight | 8 |
| RadiusBottomLeft | 8 |
| RadiusBottomRight | 8 |

#### Control: ReporteeIcon (Icon)

Insert → Icons → Document (or Message). Rename to `ReporteeIcon`.

| Property | Value |
|----------|-------|
| X | 863 |
| Y | 348 |
| Width | 60 |
| Height | 60 |
| Color | `RGBA(0, 120, 212, 1)` |
| Fill | `RGBA(0, 0, 0, 0)` |

#### Control: ReporteeCardTitle (Label)

| Property | Value |
|----------|-------|
| X | 723 |
| Y | 424 |
| Width | 340 |
| Height | 36 |
| Text | `"Reportee"` |
| Color | `RGBA(50, 49, 48, 1)` |
| FontSize | 20 |
| FontWeight | `FontWeight.Bold` |
| Align | `Align.Center` |
| Fill | `RGBA(0, 0, 0, 0)` |

#### Control: ReporteeCardSubtitle (Label)

| Property | Value |
|----------|-------|
| X | 723 |
| Y | 464 |
| Width | 340 |
| Height | 32 |
| Text | `"Respond to issues & update status"` |
| Color | `RGBA(96, 94, 92, 1)` |
| FontSize | 13 |
| Align | `Align.Center` |
| Fill | `RGBA(0, 0, 0, 0)` |

#### Control: ReporteeCardButton (Button)

| Property | Value |
|----------|-------|
| X | 723 |
| Y | 320 |
| Width | 340 |
| Height | 200 |
| Text | `""` |
| Fill | `RGBA(0, 0, 0, 0)` |
| HoverFill | `RGBA(0, 120, 212, 0.1)` |
| PressedFill | `RGBA(0, 120, 212, 0.2)` |
| BorderThickness | 0 |
| OnSelect | `Set(gblUserRole, "Reportee"); Navigate(ReporteeCaseListScreen, ScreenTransition.Fade)` |


---

### Screen 2: ReviewerCaseListScreen

This screen shows the reviewer all cases in two separate tables: new cases waiting for review, and cases where the reportee has addressed issues and sent them back.

**Overview of controls:**

| Control | Type | Purpose |
|---------|------|---------|
| RCLHeader | Rectangle | Blue top bar |
| RCLHeaderBreadcrumb | Label | "Reviewer > Case List" |
| RCLSwitchRoleBtn | Button | Returns to HomeScreen |
| RCLPageTitle | Label | "Reviewer — Case List" |
| RCLSearchInput | Text input | Search by Sub-case ID |
| RCLTable1Header | Label | "New Cases — Pending Review" section title |
| RCLTable1ColHeaders | (group of labels) | Column header labels for table 1 |
| RCLNewCasesGallery | Vertical gallery | Shows new/in-review cases |
| RCLTable2Header | Label | "Returning Cases — Reportee Completed Changes" |
| RCLTable2ColHeaders | (group of labels) | Column header labels for table 2 |
| RCLReturningGallery | Vertical gallery | Shows returning cases |

#### Layout dimensions for the two tables

The screen is 768 px tall. After the header (60 px) and page title + search (about 90 px), you have roughly 618 px for the two tables. We allocate 280 px each with a 20 px gap between them.

| Zone | Y start | Height |
|------|---------|--------|
| Header | 0 | 60 |
| Page title + search | 68 | 80 |
| Table 1 section header | 158 | 34 |
| Table 1 column headers | 192 | 40 |
| Table 1 gallery | 232 | 200 |
| Table 2 section header | 442 | 34 |
| Table 2 column headers | 476 | 40 |
| Table 2 gallery | 516 | 200 |

#### Control: RCLHeader (Rectangle)

| Property | Value |
|----------|-------|
| X | 0 |
| Y | 0 |
| Width | 1366 |
| Height | 60 |
| Fill | `RGBA(0, 120, 212, 1)` |
| BorderThickness | 0 |

#### Control: RCLHeaderBreadcrumb (Label)

| Property | Value |
|----------|-------|
| X | 20 |
| Y | 0 |
| Width | 500 |
| Height | 60 |
| Text | `"Reviewer  >  Case List"` |
| Color | `RGBA(255, 255, 255, 1)` |
| FontSize | 16 |
| FontWeight | `FontWeight.Semibold` |
| VerticalAlign | `VerticalAlign.Middle` |
| Fill | `RGBA(0, 0, 0, 0)` |
| BorderThickness | 0 |

#### Control: RCLSwitchRoleBtn (Button)

| Property | Value |
|----------|-------|
| X | 1206 |
| Y | 10 |
| Width | 140 |
| Height | 40 |
| Text | `"Switch Role"` |
| Fill | `RGBA(255, 255, 255, 0.2)` |
| Color | `RGBA(255, 255, 255, 1)` |
| FontSize | 13 |
| FontWeight | `FontWeight.Normal` |
| BorderColor | `RGBA(255, 255, 255, 0.5)` |
| BorderThickness | 1 |
| RadiusTopLeft | 4 |
| RadiusTopRight | 4 |
| RadiusBottomLeft | 4 |
| RadiusBottomRight | 4 |
| OnSelect | `Navigate(HomeScreen, ScreenTransition.Fade)` |

#### Control: RCLPageTitle (Label)

| Property | Value |
|----------|-------|
| X | 20 |
| Y | 68 |
| Width | 600 |
| Height | 36 |
| Text | `"Reviewer — Case List"` |
| Color | `RGBA(50, 49, 48, 1)` |
| FontSize | 22 |
| FontWeight | `FontWeight.Bold` |
| Fill | `RGBA(0, 0, 0, 0)` |
| BorderThickness | 0 |

#### Control: RCLSearchInput (Text input)

Insert → Input → Text input. Rename to `RCLSearchInput`.

| Property | Value |
|----------|-------|
| X | 20 |
| Y | 112 |
| Width | 400 |
| Height | 36 |
| HintText | `"Search by Sub-case ID..."` |
| Fill | `RGBA(255, 255, 255, 1)` |
| BorderColor | `RGBA(225, 223, 221, 1)` |
| BorderThickness | 1 |
| RadiusTopLeft | 4 |
| RadiusTopRight | 4 |
| RadiusBottomLeft | 4 |
| RadiusBottomRight | 4 |
| FontSize | 14 |

#### Control: RCLTable1Header (Label)

| Property | Value |
|----------|-------|
| X | 20 |
| Y | 158 |
| Width | 1326 |
| Height | 34 |
| Text | `"New Cases — Pending Review"` |
| Color | `RGBA(50, 49, 48, 1)` |
| FontSize | 15 |
| FontWeight | `FontWeight.Bold` |
| Fill | `RGBA(0, 0, 0, 0)` |
| BorderThickness | 0 |

#### Column header labels for Table 1

Add 10 separate labels side by side at Y=192, Height=40. Each has Fill=`RGBA(243, 242, 241, 1)`, FontWeight=`FontWeight.Bold`, FontSize=13, Color=`RGBA(50, 49, 48, 1)`, VerticalAlign=`VerticalAlign.Middle`.

| Control name | X | Width | Text |
|--------------|---|-------|------|
| RCL1ColSubcase | 20 | 130 | `"Sub-case ID"` |
| RCL1ColSubmit | 152 | 110 | `"Submission Date"` |
| RCL1ColDue | 264 | 100 | `"Due Date"` |
| RCL1ColType | 366 | 120 | `"Case Type"` |
| RCL1ColFlow | 488 | 70 | `"FLOW?"` |
| RCL1ColExhibits | 560 | 80 | `"Exhibits"` |
| RCL1ColIDSO | 642 | 140 | `"ID SO"` |
| RCL1ColReviewer | 784 | 140 | `"Reviewer"` |
| RCL1ColStatus | 926 | 140 | `"Status"` |
| RCL1ColAction | 1068 | 130 | `"Action"` |

#### Control: RCLNewCasesGallery (Vertical Gallery)

Insert → Gallery → Vertical. Rename to `RCLNewCasesGallery`.

| Property | Value |
|----------|-------|
| X | 20 |
| Y | 232 |
| Width | 1326 |
| Height | 200 |
| TemplateHeight | 52 |
| TemplatePadding | 0 |
| ShowScrollbar | true |
| Fill | `RGBA(255, 255, 255, 1)` |

**Items formula:**

```
Sort(
    Filter(
        'Lab Cases',
        Or(
            And(
                'Task status'.Value = "Ready for Review",
                CountRows(
                    Filter('Case Issues', CaseID = ThisRecord.ID)
                ) = 0
            ),
            'Task status'.Value = "In Review"
        ),
        Or(
            RCLSearchInput.Text = "",
            StartsWith('Sub-case ID', RCLSearchInput.Text)
        )
    ),
    'Due date',
    SortOrder.Ascending
)
```

**What this formula does:**

The `Filter` function returns only rows from `Lab Cases` where either:
- The status is `"Ready for Review"` AND there are zero issues in `Case Issues` for that case (meaning no reviewer has logged issues yet), OR
- The status is `"In Review"` (already started but not finished).

The `Or(RCLSearchInput.Text = "", StartsWith(...))` part makes the search work: if the search box is empty it shows everything; otherwise it shows only rows where the Sub-case ID starts with the typed text.

`Sort` then orders everything by Due date ascending (earliest due first).

**Controls inside the gallery template:**

The template is 52 px tall. Add the following controls inside the gallery (in the template area). Their X and Width values match the column headers above.

##### RCLNew_SubcaseID (Label)

| Property | Value |
|----------|-------|
| X | 0 |
| Y | 0 |
| Width | 130 |
| Height | 52 |
| Text | `ThisItem.'Sub-case ID'` |
| FontSize | 13 |
| Color | `RGBA(50, 49, 48, 1)` |
| Fill | `RGBA(0, 0, 0, 0)` |
| VerticalAlign | `VerticalAlign.Middle` |
| PaddingLeft | 6 |

##### RCLNew_SubmitDate (Label)

| Property | Value |
|----------|-------|
| X | 132 |
| Y | 0 |
| Width | 110 |
| Height | 52 |
| Text | `Text(ThisItem.'Submission date', "dd/mm/yyyy")` |
| FontSize | 12 |
| Color | `RGBA(96, 94, 92, 1)` |
| Fill | `RGBA(0, 0, 0, 0)` |
| VerticalAlign | `VerticalAlign.Middle` |

##### RCLNew_DueDate (Label)

| Property | Value |
|----------|-------|
| X | 244 |
| Y | 0 |
| Width | 100 |
| Height | 52 |
| Text | `Text(ThisItem.'Due date', "dd/mm/yyyy")` |
| FontSize | 12 |
| Color | `RGBA(96, 94, 92, 1)` |
| Fill | `RGBA(0, 0, 0, 0)` |
| VerticalAlign | `VerticalAlign.Middle` |

##### RCLNew_CaseType (Label)

| Property | Value |
|----------|-------|
| X | 346 |
| Y | 0 |
| Width | 120 |
| Height | 52 |
| Text | `ThisItem.'Case Type'.Value` |
| FontSize | 12 |
| Fill | `RGBA(0, 0, 0, 0)` |
| VerticalAlign | `VerticalAlign.Middle` |

##### RCLNew_Flow (Label)

| Property | Value |
|----------|-------|
| X | 468 |
| Y | 0 |
| Width | 70 |
| Height | 52 |
| Text | `If(ThisItem.'FLOW case?', "Yes", "No")` |
| FontSize | 12 |
| Fill | `RGBA(0, 0, 0, 0)` |
| VerticalAlign | `VerticalAlign.Middle` |

##### RCLNew_Exhibits (Label)

| Property | Value |
|----------|-------|
| X | 540 |
| Y | 0 |
| Width | 80 |
| Height | 52 |
| Text | `Text(ThisItem.'No. of Exhibits')` |
| FontSize | 12 |
| Fill | `RGBA(0, 0, 0, 0)` |
| VerticalAlign | `VerticalAlign.Middle` |

##### RCLNew_IDSO (Label)

| Property | Value |
|----------|-------|
| X | 622 |
| Y | 0 |
| Width | 140 |
| Height | 52 |
| Text | `ThisItem.'ID SO'.DisplayName` |
| FontSize | 12 |
| Fill | `RGBA(0, 0, 0, 0)` |
| VerticalAlign | `VerticalAlign.Middle` |

##### RCLNew_Reviewer (Label)

| Property | Value |
|----------|-------|
| X | 764 |
| Y | 0 |
| Width | 140 |
| Height | 52 |
| Text | `ThisItem.Reviewer.DisplayName` |
| FontSize | 12 |
| Fill | `RGBA(0, 0, 0, 0)` |
| VerticalAlign | `VerticalAlign.Middle` |

##### RCLNew_StatusBadge (Label)

This label shows a coloured status badge.

| Property | Value |
|----------|-------|
| X | 906 |
| Y | 10 |
| Width | 130 |
| Height | 32 |
| Text | `ThisItem.'Task status'.Value` |
| FontSize | 11 |
| FontWeight | `FontWeight.Semibold` |
| Align | `Align.Center` |
| VerticalAlign | `VerticalAlign.Middle` |
| RadiusTopLeft | 12 |
| RadiusTopRight | 12 |
| RadiusBottomLeft | 12 |
| RadiusBottomRight | 12 |
| Fill | `Switch(ThisItem.'Task status'.Value, "Ready for Review", RGBA(255, 244, 206, 1), "In Review", RGBA(210, 232, 255, 1), "Reviewed", RGBA(255, 224, 214, 1), RGBA(223, 246, 221, 1))` |
| Color | `Switch(ThisItem.'Task status'.Value, "Ready for Review", RGBA(131, 92, 0, 1), "In Review", RGBA(0, 69, 120, 1), "Reviewed", RGBA(164, 38, 44, 1), RGBA(16, 124, 16, 1))` |

**What the Switch formula does:** `Switch` is like a series of if/else checks. It looks at the Task status value and picks the matching fill colour. If none match (the last argument), it falls through to the Case Completed green.

##### RCLNew_ActionBtn (Button)

| Property | Value |
|----------|-------|
| X | 1046 |
| Y | 8 |
| Width | 120 |
| Height | 36 |
| Text | `If(ThisItem.'Task status'.Value = "Ready for Review", "Start Review", "")` |
| Visible | `ThisItem.'Task status'.Value = "Ready for Review"` |
| Fill | `RGBA(0, 120, 212, 1)` |
| Color | `RGBA(255, 255, 255, 1)` |
| FontSize | 12 |
| RadiusTopLeft | 4 |
| RadiusTopRight | 4 |
| RadiusBottomLeft | 4 |
| RadiusBottomRight | 4 |
| OnSelect | `Patch('Lab Cases', ThisItem, {'Task status': {Value: "In Review"}}); Set(gblSelectedCase, ThisItem); Navigate(ReviewerCaseDetailScreen, ScreenTransition.Fade)` |

**What the OnSelect formula does:**
1. `Patch('Lab Cases', ThisItem, ...)` — Updates the Task status to "In Review" in the SharePoint list directly. `ThisItem` refers to the specific row this button is in.
2. `Set(gblSelectedCase, ThisItem)` — Saves the entire case record into the global variable so the detail screen can display it.
3. `Navigate(ReviewerCaseDetailScreen, ...)` — Moves the user to the detail screen.

##### Row separator line (Rectangle)

| Property | Value |
|----------|-------|
| X | 0 |
| Y | 51 |
| Width | 1326 |
| Height | 1 |
| Fill | `RGBA(225, 223, 221, 1)` |

**Gallery OnSelect (set on the gallery itself, not a button inside it):**

Click the gallery frame (not any control inside it), then find the **OnSelect** property:

```
Set(gblSelectedCase, ThisItem);
Navigate(ReviewerCaseDetailScreen, ScreenTransition.Fade)
```

#### Control: RCLTable2Header (Label)

| Property | Value |
|----------|-------|
| X | 20 |
| Y | 442 |
| Width | 1326 |
| Height | 34 |
| Text | `"Returning Cases — Reportee Completed Changes"` |
| Color | `RGBA(50, 49, 48, 1)` |
| FontSize | 15 |
| FontWeight | `FontWeight.Bold` |
| Fill | `RGBA(0, 0, 0, 0)` |

#### Column header labels for Table 2

Same styling as Table 1 headers but at Y=476. Add these labels:

| Control name | X | Width | Text |
|--------------|---|-------|------|
| RCL2ColSubcase | 20 | 130 | `"Sub-case ID"` |
| RCL2ColSubmit | 152 | 110 | `"Submission Date"` |
| RCL2ColDue | 264 | 100 | `"Due Date"` |
| RCL2ColType | 366 | 120 | `"Case Type"` |
| RCL2ColFlow | 488 | 70 | `"FLOW?"` |
| RCL2ColExhibits | 560 | 80 | `"Exhibits"` |
| RCL2ColIDSO | 642 | 140 | `"ID SO"` |
| RCL2ColReviewer | 784 | 140 | `"Reviewer"` |
| RCL2ColStatus | 926 | 100 | `"Status"` |
| RCL2ColIssues | 1028 | 80 | `"Issues"` |
| RCL2ColAction | 1110 | 106 | `"Action"` |

#### Control: RCLReturningGallery (Vertical Gallery)

Insert → Gallery → Vertical. Rename to `RCLReturningGallery`.

| Property | Value |
|----------|-------|
| X | 20 |
| Y | 516 |
| Width | 1326 |
| Height | 200 |
| TemplateHeight | 52 |
| TemplatePadding | 0 |
| ShowScrollbar | true |
| Fill | `RGBA(255, 255, 255, 1)` |

**Items formula:**

```
Sort(
    Filter(
        'Lab Cases',
        'Task status'.Value = "Ready for Review",
        CountRows(
            Filter('Case Issues', CaseID = ThisRecord.ID)
        ) > 0,
        Or(
            RCLSearchInput.Text = "",
            StartsWith('Sub-case ID', RCLSearchInput.Text)
        )
    ),
    'Due date',
    SortOrder.Ascending
)
```

**What this formula does:** Shows only cases where the status is "Ready for Review" AND there is at least one issue record in Case Issues linked to that case. This means the reportee has addressed the issues and returned the case.

**Controls inside RCLReturningGallery template:**

Add the same label controls as in Table 1 (SubcaseID through Reviewer) at the same X positions and Y=0, Height=52. Then add:

##### RCLRet_StatusBadge (Label)

Same formula as RCLNew_StatusBadge above, X=906, Y=10, Width=100, Height=32.

##### RCLRet_IssuesBadge (Label)

Shows a count of issues in an amber badge.

| Property | Value |
|----------|-------|
| X | 1028 |
| Y | 10 |
| Width | 70 |
| Height | 32 |
| Text | `CountRows(Filter('Case Issues', CaseID = ThisItem.ID)) & " issues"` |
| FontSize | 11 |
| FontWeight | `FontWeight.Semibold` |
| Align | `Align.Center` |
| VerticalAlign | `VerticalAlign.Middle` |
| Fill | `RGBA(255, 248, 225, 1)` |
| Color | `RGBA(245, 127, 23, 1)` |
| RadiusTopLeft | 12 |
| RadiusTopRight | 12 |
| RadiusBottomLeft | 12 |
| RadiusBottomRight | 12 |

##### RCLRet_ActionBtn (Button)

| Property | Value |
|----------|-------|
| X | 1108 |
| Y | 8 |
| Width | 106 |
| Height | 36 |
| Text | `"Re-review"` |
| Fill | `RGBA(0, 120, 212, 1)` |
| Color | `RGBA(255, 255, 255, 1)` |
| FontSize | 12 |
| RadiusTopLeft | 4 |
| RadiusTopRight | 4 |
| RadiusBottomLeft | 4 |
| RadiusBottomRight | 4 |
| OnSelect | `Set(gblSelectedCase, ThisItem); Navigate(ReviewerCaseDetailScreen, ScreenTransition.Fade)` |

**RCLReturningGallery OnSelect:**

```
Set(gblSelectedCase, ThisItem);
Navigate(ReviewerCaseDetailScreen, ScreenTransition.Fade)
```


---

### Screen 3: ReviewerCaseDetailScreen

This is the most complex screen. It shows full case details, a scrollable list of existing issues, a form to add new issues, and action buttons.

Because this screen has a lot of vertical content, we use a scrollable container for the issues section.

**Overview of sections:**

| Section | Y | Purpose |
|---------|---|---------|
| Header bar | 0 | Blue bar with back button |
| Case Details card | 68 | Read-only grid of case fields |
| Issues card | 280 | Gallery of existing issues |
| Add New Issue card | (below issues) | Form to add a new issue |
| Action bar | 708 | Three action buttons at the bottom |

Because the Issues card height varies with the number of issues, we use a fixed-height scrollable gallery for issues, and push the Add Issue card and Action bar to fixed Y positions near the bottom.

#### Control: RCDHeader (Rectangle)

| Property | Value |
|----------|-------|
| X | 0 |
| Y | 0 |
| Width | 1366 |
| Height | 60 |
| Fill | `RGBA(0, 120, 212, 1)` |

#### Control: RCDBackBtn (Button)

| Property | Value |
|----------|-------|
| X | 20 |
| Y | 10 |
| Width | 200 |
| Height | 40 |
| Text | `"← Back to Case List"` |
| Fill | `RGBA(255, 255, 255, 0.2)` |
| Color | `RGBA(255, 255, 255, 1)` |
| FontSize | 13 |
| BorderColor | `RGBA(255, 255, 255, 0.5)` |
| BorderThickness | 1 |
| RadiusTopLeft | 4 |
| RadiusTopRight | 4 |
| RadiusBottomLeft | 4 |
| RadiusBottomRight | 4 |
| OnSelect | `Navigate(ReviewerCaseListScreen, ScreenTransition.Back)` |

#### Case Details Card

Add a Rectangle as the card background:

| Property | Value |
|----------|-------|
| Name | RCDCaseCard |
| X | 20 |
| Y | 68 |
| Width | 1326 |
| Height | 200 |
| Fill | `RGBA(255, 255, 255, 1)` |
| BorderColor | `RGBA(225, 223, 221, 1)` |
| BorderThickness | 1 |
| RadiusTopLeft | 8 |
| RadiusTopRight | 8 |
| RadiusBottomLeft | 8 |
| RadiusBottomRight | 8 |

Add a label for the card title:

| Property | Value |
|----------|-------|
| Name | RCDCaseCardTitle |
| X | 36 |
| Y | 76 |
| Width | 300 |
| Height | 28 |
| Text | `"Case Details"` |
| FontSize | 15 |
| FontWeight | `FontWeight.Bold` |
| Color | `RGBA(50, 49, 48, 1)` |
| Fill | `RGBA(0, 0, 0, 0)` |

Now add field label pairs (field name + value) in a 3-column grid layout. Each pair uses a small grey label above and a value label below. Layout starts at Y=112, with rows at Y=112 and Y=152 and Y=192.

**Row 1 (Y=112 for field names, Y=134 for values):**

| Field | Name label X | Value label X | Width | Name Text | Value Text |
|-------|-------------|---------------|-------|-----------|------------|
| Sub-case ID | 36 | 36 | 200 | `"Sub-case ID"` | `gblSelectedCase.'Sub-case ID'` |
| Status | 250 | 250 | 220 | `"Status"` | (use badge label below) |
| Submission Date | 484 | 484 | 180 | `"Submission Date"` | `Text(gblSelectedCase.'Submission date', "dd/mm/yyyy")` |

For the **Status badge value** add a label with:

| Property | Value |
|----------|-------|
| Name | RCDStatusBadge |
| X | 250 |
| Y | 134 |
| Width | 160 |
| Height | 28 |
| Text | `gblSelectedCase.'Task status'.Value` |
| FontSize | 12 |
| FontWeight | `FontWeight.Semibold` |
| Align | `Align.Center` |
| VerticalAlign | `VerticalAlign.Middle` |
| RadiusTopLeft | 12 |
| RadiusTopRight | 12 |
| RadiusBottomLeft | 12 |
| RadiusBottomRight | 12 |
| Fill | `Switch(gblSelectedCase.'Task status'.Value, "Ready for Review", RGBA(255, 244, 206, 1), "In Review", RGBA(210, 232, 255, 1), "Reviewed", RGBA(255, 224, 214, 1), RGBA(223, 246, 221, 1))` |
| Color | `Switch(gblSelectedCase.'Task status'.Value, "Ready for Review", RGBA(131, 92, 0, 1), "In Review", RGBA(0, 69, 120, 1), "Reviewed", RGBA(164, 38, 44, 1), RGBA(16, 124, 16, 1))` |

**Row 2 (Y=152 for field names, Y=174 for values):**

| Field | X | Width | Name | Value |
|-------|---|-------|------|-------|
| Due Date | 36 | 180 | `"Due Date"` | `Text(gblSelectedCase.'Due date', "dd/mm/yyyy")` |
| Case Type | 250 | 200 | `"Case Type"` | `gblSelectedCase.'Case Type'.Value` |
| FLOW Case | 484 | 180 | `"FLOW Case"` | `If(gblSelectedCase.'FLOW case?', "Yes", "No")` |

**Row 3 (Y=192 for field names, Y=214 for values):**

| Field | X | Width | Name | Value |
|-------|---|-------|------|-------|
| No. of Exhibits | 36 | 180 | `"No. of Exhibits"` | `Text(gblSelectedCase.'No. of Exhibits')` |
| ID SO | 250 | 200 | `"ID SO"` | `gblSelectedCase.'ID SO'.DisplayName` |
| Reviewer | 484 | 200 | `"Reviewer"` | `gblSelectedCase.Reviewer.DisplayName` |

For all field name labels use: FontSize=11, Color=`RGBA(96, 94, 92, 1)`, Height=18, Fill=transparent.
For all value labels use: FontSize=13, Color=`RGBA(50, 49, 48, 1)`, Height=26, Fill=transparent.

#### Issues Card

Add a rectangle for the card background:

| Property | Value |
|----------|-------|
| Name | RCDIssuesCard |
| X | 20 |
| Y | 278 |
| Width | 760 |
| Height | 390 |
| Fill | `RGBA(255, 255, 255, 1)` |
| BorderColor | `RGBA(225, 223, 221, 1)` |
| BorderThickness | 1 |
| RadiusTopLeft | 8 |
| RadiusTopRight | 8 |
| RadiusBottomLeft | 8 |
| RadiusBottomRight | 8 |

Add a label:

| Property | Value |
|----------|-------|
| Name | RCDIssuesCardTitle |
| X | 36 |
| Y | 286 |
| Width | 300 |
| Height | 28 |
| Text | `"Issues"` |
| FontSize | 15 |
| FontWeight | `FontWeight.Bold` |
| Color | `RGBA(50, 49, 48, 1)` |
| Fill | `RGBA(0, 0, 0, 0)` |

Add an issue count badge next to the title:

| Property | Value |
|----------|-------|
| Name | RCDIssueCount |
| X | 100 |
| Y | 289 |
| Width | 80 |
| Height | 22 |
| Text | `CountRows(Filter('Case Issues', CaseID = gblSelectedCase.ID)) & " issues"` |
| FontSize | 11 |
| Align | `Align.Center` |
| VerticalAlign | `VerticalAlign.Middle` |
| Fill | `RGBA(210, 232, 255, 1)` |
| Color | `RGBA(0, 69, 120, 1)` |
| RadiusTopLeft | 10 |
| RadiusTopRight | 10 |
| RadiusBottomLeft | 10 |
| RadiusBottomRight | 10 |

#### Control: RCDIssuesGallery (Vertical Gallery)

Insert → Gallery → Vertical. Rename to `RCDIssuesGallery`.

| Property | Value |
|----------|-------|
| X | 20 |
| Y | 320 |
| Width | 760 |
| Height | 340 |
| TemplateHeight | 120 |
| TemplatePadding | 0 |
| ShowScrollbar | true |
| Fill | `RGBA(255, 255, 255, 1)` |

**Items formula:**

```
SortByColumns(
    Filter(
        'Case Issues',
        CaseID = gblSelectedCase.ID
    ),
    "ReviewRound",
    SortOrder.Ascending
)
```

**What this does:** Shows all issues for the currently selected case, ordered by the review round (so issues from round 1 appear before round 2 etc.).

**Controls inside RCDIssuesGallery template (TemplateHeight=120):**

##### RCDIss_TierBadge (Label)

| Property | Value |
|----------|-------|
| X | 8 |
| Y | 8 |
| Width | 80 |
| Height | 24 |
| Text | `ThisItem.IssueTier.Value` |
| FontSize | 11 |
| FontWeight | `FontWeight.Semibold` |
| Align | `Align.Center` |
| VerticalAlign | `VerticalAlign.Middle` |
| RadiusTopLeft | 10 |
| RadiusTopRight | 10 |
| RadiusBottomLeft | 10 |
| RadiusBottomRight | 10 |
| Fill | `Switch(ThisItem.IssueTier.Value, "T1", RGBA(232, 245, 233, 1), "T2", RGBA(255, 248, 225, 1), RGBA(255, 235, 238, 1))` |
| Color | `Switch(ThisItem.IssueTier.Value, "T1", RGBA(46, 125, 50, 1), "T2", RGBA(245, 127, 23, 1), RGBA(198, 40, 40, 1))` |

**What this Switch does:** T1=Minor gets green styling, T2=Major gets amber, anything else (T3=Critical) gets red.

##### RCDIss_TypeBadge (Label)

| Property | Value |
|----------|-------|
| X | 96 |
| Y | 8 |
| Width | 160 |
| Height | 24 |
| Text | `ThisItem.IssueType.Value` |
| FontSize | 11 |
| FontWeight | `FontWeight.Semibold` |
| Align | `Align.Center` |
| VerticalAlign | `VerticalAlign.Middle` |
| RadiusTopLeft | 10 |
| RadiusTopRight | 10 |
| RadiusBottomLeft | 10 |
| RadiusBottomRight | 10 |
| Fill | `RGBA(243, 242, 241, 1)` |
| Color | `RGBA(50, 49, 48, 1)` |

##### RCDIss_RoundLabel (Label)

| Property | Value |
|----------|-------|
| X | 264 |
| Y | 8 |
| Width | 100 |
| Height | 24 |
| Text | `"Round " & Text(ThisItem.ReviewRound)` |
| FontSize | 11 |
| Color | `RGBA(96, 94, 92, 1)` |
| Fill | `RGBA(0, 0, 0, 0)` |
| VerticalAlign | `VerticalAlign.Middle` |

##### RCDIss_StatusBadge (Label)

| Property | Value |
|----------|-------|
| X | 372 |
| Y | 8 |
| Width | 100 |
| Height | 24 |
| Text | `ThisItem.IssueStatus.Value` |
| FontSize | 11 |
| FontWeight | `FontWeight.Semibold` |
| Align | `Align.Center` |
| VerticalAlign | `VerticalAlign.Middle` |
| RadiusTopLeft | 10 |
| RadiusTopRight | 10 |
| RadiusBottomLeft | 10 |
| RadiusBottomRight | 10 |
| Fill | `If(ThisItem.IssueStatus.Value = "Completed", RGBA(223, 246, 221, 1), RGBA(255, 224, 214, 1))` |
| Color | `If(ThisItem.IssueStatus.Value = "Completed", RGBA(16, 124, 16, 1), RGBA(164, 38, 44, 1))` |

##### RCDIss_LIMSBadge (Label)

| Property | Value |
|----------|-------|
| X | 480 |
| Y | 8 |
| Width | 100 |
| Height | 24 |
| Text | `If(ThisItem.ReportInLIMS, "Report in LIMS", "")` |
| Visible | `ThisItem.ReportInLIMS` |
| FontSize | 10 |
| Align | `Align.Center` |
| VerticalAlign | `VerticalAlign.Middle` |
| RadiusTopLeft | 10 |
| RadiusTopRight | 10 |
| RadiusBottomLeft | 10 |
| RadiusBottomRight | 10 |
| Fill | `RGBA(210, 232, 255, 1)` |
| Color | `RGBA(0, 69, 120, 1)` |

##### RCDIss_Description (Label)

| Property | Value |
|----------|-------|
| X | 8 |
| Y | 38 |
| Width | 730 |
| Height | 32 |
| Text | `ThisItem.IssueDescription` |
| FontSize | 13 |
| Color | `RGBA(50, 49, 48, 1)` |
| Fill | `RGBA(0, 0, 0, 0)` |
| VerticalAlign | `VerticalAlign.Top` |

##### RCDIss_ReplyBox (Rectangle — blue background box)

Only visible when SO Reply is not blank.

| Property | Value |
|----------|-------|
| X | 8 |
| Y | 74 |
| Width | 730 |
| Height | 36 |
| Fill | `RGBA(232, 243, 252, 1)` |
| RadiusTopLeft | 4 |
| RadiusTopRight | 4 |
| RadiusBottomLeft | 4 |
| RadiusBottomRight | 4 |
| Visible | `!IsBlank(ThisItem.SOReply)` |

##### RCDIss_ReplyLabel (Label inside blue box)

| Property | Value |
|----------|-------|
| X | 14 |
| Y | 76 |
| Width | 718 |
| Height | 32 |
| Text | `"SO Reply: " & ThisItem.SOReply` |
| FontSize | 12 |
| Color | `RGBA(0, 69, 120, 1)` |
| Fill | `RGBA(0, 0, 0, 0)` |
| VerticalAlign | `VerticalAlign.Middle` |
| Visible | `!IsBlank(ThisItem.SOReply)` |

##### Row separator (Rectangle)

| Property | Value |
|----------|-------|
| X | 0 |
| Y | 119 |
| Width | 760 |
| Height | 1 |
| Fill | `RGBA(225, 223, 221, 1)` |

#### Add New Issue Card

This card sits to the right of the issues gallery.

Add a rectangle:

| Property | Value |
|----------|-------|
| Name | RCDAddIssueCard |
| X | 792 |
| Y | 278 |
| Width | 554 |
| Height | 390 |
| Fill | `RGBA(255, 255, 255, 1)` |
| BorderColor | `RGBA(225, 223, 221, 1)` |
| BorderThickness | 1 |
| RadiusTopLeft | 8 |
| RadiusTopRight | 8 |
| RadiusBottomLeft | 8 |
| RadiusBottomRight | 8 |

Add a label:

| Property | Value |
|----------|-------|
| Name | RCDAddIssueTitle |
| X | 808 |
| Y | 286 |
| Width | 520 |
| Height | 28 |
| Text | `"Add New Issue"` |
| FontSize | 15 |
| FontWeight | `FontWeight.Bold` |
| Color | `RGBA(50, 49, 48, 1)` |
| Fill | `RGBA(0, 0, 0, 0)` |

#### Control: RCDIssueDescInput (Text Input — multiline)

Insert → Input → Text input. Rename to `RCDIssueDescInput`.

| Property | Value |
|----------|-------|
| X | 808 |
| Y | 322 |
| Width | 520 |
| Height | 100 |
| Mode | `TextMode.MultiLine` |
| HintText | `"Describe the issue found..."` |
| Fill | `RGBA(255, 255, 255, 1)` |
| BorderColor | `RGBA(225, 223, 221, 1)` |
| BorderThickness | 1 |
| RadiusTopLeft | 4 |
| RadiusTopRight | 4 |
| RadiusBottomLeft | 4 |
| RadiusBottomRight | 4 |
| FontSize | 13 |

#### Control: RCDIssueTypeLabel (Label)

| Property | Value |
|----------|-------|
| X | 808 |
| Y | 430 |
| Width | 250 |
| Height | 22 |
| Text | `"Issue Type"` |
| FontSize | 12 |
| FontWeight | `FontWeight.Semibold` |
| Color | `RGBA(50, 49, 48, 1)` |
| Fill | `RGBA(0, 0, 0, 0)` |

#### Control: RCDIssueTypeDropdown (Dropdown)

Insert → Input → Dropdown. Rename to `RCDIssueTypeDropdown`.

| Property | Value |
|----------|-------|
| X | 808 |
| Y | 454 |
| Width | 250 |
| Height | 40 |
| Items | `Choices('Case Issues'.IssueType)` |
| Fill | `RGBA(255, 255, 255, 1)` |
| BorderColor | `RGBA(225, 223, 221, 1)` |
| BorderThickness | 1 |
| RadiusTopLeft | 4 |
| RadiusTopRight | 4 |
| RadiusBottomLeft | 4 |
| RadiusBottomRight | 4 |
| FontSize | 13 |

**What `Choices('Case Issues'.IssueType)` does:** It reads the available Choice values directly from the SharePoint column definition. This means if you add or remove choices in SharePoint, the dropdown automatically updates — you do not need to maintain a hardcoded list in the app.

#### Control: RCDIssueTierLabel (Label)

| Property | Value |
|----------|-------|
| X | 1076 |
| Y | 430 |
| Width | 250 |
| Height | 22 |
| Text | `"Issue Tier"` |
| FontSize | 12 |
| FontWeight | `FontWeight.Semibold` |
| Color | `RGBA(50, 49, 48, 1)` |
| Fill | `RGBA(0, 0, 0, 0)` |

#### Control: RCDIssueTierDropdown (Dropdown)

| Property | Value |
|----------|-------|
| Name | RCDIssueTierDropdown |
| X | 1076 |
| Y | 454 |
| Width | 250 |
| Height | 40 |
| Items | `["T1 — Minor", "T2 — Major", "T3 — Critical"]` |
| Fill | `RGBA(255, 255, 255, 1)` |
| BorderColor | `RGBA(225, 223, 221, 1)` |
| BorderThickness | 1 |
| RadiusTopLeft | 4 |
| RadiusTopRight | 4 |
| RadiusBottomLeft | 4 |
| RadiusBottomRight | 4 |
| FontSize | 13 |

> **Note on Tier dropdown:** The dropdown shows user-friendly labels like "T1 — Minor". When saving to SharePoint we extract just the tier code. The formula in the Add Issue button (below) uses `Left(RCDIssueTierDropdown.Selected.Value, 2)` to get "T1", "T2", or "T3".

#### Control: RCDReportInLIMSCheckbox (Checkbox)

Insert → Input → Checkbox. Rename to `RCDReportInLIMSCheckbox`.

| Property | Value |
|----------|-------|
| X | 808 |
| Y | 504 |
| Width | 200 |
| Height | 32 |
| Text | `"Report in LIMS"` |
| Default | `true` |
| FontSize | 13 |
| Color | `RGBA(50, 49, 48, 1)` |
| Fill | `RGBA(0, 0, 0, 0)` |

#### Control: RCDAddIssueBtn (Button)

| Property | Value |
|----------|-------|
| X | 808 |
| Y | 548 |
| Width | 520 |
| Height | 40 |
| Text | `"+ Add Issue"` |
| Fill | `RGBA(0, 120, 212, 1)` |
| Color | `RGBA(255, 255, 255, 1)` |
| FontSize | 14 |
| FontWeight | `FontWeight.Semibold` |
| RadiusTopLeft | 4 |
| RadiusTopRight | 4 |
| RadiusBottomLeft | 4 |
| RadiusBottomRight | 4 |

**OnSelect formula:**

```
If(
    IsBlank(RCDIssueDescInput.Text) ||
    IsBlank(RCDIssueTypeDropdown.Selected.Value) ||
    IsBlank(RCDIssueTierDropdown.Selected.Value),
    Notify("Please fill in the description, issue type, and tier before adding.", NotificationType.Warning),
    Patch(
        'Case Issues',
        Defaults('Case Issues'),
        {
            CaseID: gblSelectedCase.ID,
            SubcaseID: gblSelectedCase.'Sub-case ID',
            IssueDescription: RCDIssueDescInput.Text,
            IssueType: {Value: RCDIssueTypeDropdown.Selected.Value},
            IssueTier: {Value: Left(RCDIssueTierDropdown.Selected.Value, 2)},
            IssueStatus: {Value: "Open"},
            ReportInLIMS: RCDReportInLIMSCheckbox.Value,
            ReviewRound: Coalesce(
                Max(
                    Filter('Case Issues', CaseID = gblSelectedCase.ID),
                    ReviewRound
                ),
                1
            )
        }
    );
    Reset(RCDIssueDescInput);
    Reset(RCDIssueTypeDropdown);
    Reset(RCDIssueTierDropdown);
    Reset(RCDReportInLIMSCheckbox);
    Refresh('Case Issues');
    Notify("Issue added successfully.", NotificationType.Success)
)
```

**Step-by-step explanation of this formula:**

1. `If(IsBlank(...) || IsBlank(...) || IsBlank(...), Notify(...), ...)` — First checks that all three required fields are filled in. If any are blank it shows a yellow warning notification and stops. The `||` symbol means "or".
2. `Patch('Case Issues', Defaults('Case Issues'), {...})` — Creates a new row in the Case Issues list. `Defaults('Case Issues')` is the Power Apps way of saying "this is a brand new record, not an update to an existing one".
3. `CaseID: gblSelectedCase.ID` — Links the issue to the case by storing the SharePoint item ID of the selected case.
4. `IssueType: {Value: RCDIssueTypeDropdown.Selected.Value}` — SharePoint Choice columns require the value wrapped in `{Value: "..."}` format.
5. `IssueTier: {Value: Left(RCDIssueTierDropdown.Selected.Value, 2)}` — Takes only the first 2 characters ("T1", "T2", or "T3") from the dropdown selection.
6. `ReviewRound: Coalesce(Max(...), 1)` — Finds the highest existing ReviewRound number for this case. If there are no existing issues (no existing round), `Max` returns blank, and `Coalesce` returns `1` instead of blank.
7. `Reset(...)` — Clears each input control back to its default state after saving.
8. `Refresh('Case Issues')` — Tells Power Apps to re-read the list from SharePoint so the gallery shows the new issue immediately.

#### Action Bar

The action bar sits at the very bottom of the screen. Add a rectangle background:

| Property | Value |
|----------|-------|
| Name | RCDActionBar |
| X | 0 |
| Y | 706 |
| Width | 1366 |
| Height | 62 |
| Fill | `RGBA(255, 255, 255, 1)` |
| BorderColor | `RGBA(225, 223, 221, 1)` |
| BorderThickness | 1 |

#### Control: RCDCopyLIMSBtn (Button)

| Property | Value |
|----------|-------|
| X | 20 |
| Y | 718 |
| Width | 220 |
| Height | 40 |
| Text | `"Copy Issues for LIMS"` |
| Fill | `RGBA(243, 242, 241, 1)` |
| Color | `RGBA(50, 49, 48, 1)` |
| FontSize | 13 |
| BorderColor | `RGBA(225, 223, 221, 1)` |
| BorderThickness | 1 |
| RadiusTopLeft | 4 |
| RadiusTopRight | 4 |
| RadiusBottomLeft | 4 |
| RadiusBottomRight | 4 |
| OnSelect | `Set(gblLIMSText, Concat(Filter('Case Issues', CaseID = gblSelectedCase.ID, ReportInLIMS = true), IssueType.Value & "  " & IssueDescription & Char(13) & Char(10))); Navigate(LIMSCopyScreen, ScreenTransition.Fade)` |

**What the OnSelect formula does:**
- `Filter('Case Issues', CaseID = gblSelectedCase.ID, ReportInLIMS = true)` — Selects only issues for this case that are flagged to report in LIMS.
- `Concat(...)` — Joins all of those records into a single text string. Each record contributes: the Issue Type, two spaces, the description, then a newline (`Char(13) & Char(10)` is a Windows-style line break).
- `Set(gblLIMSText, ...)` — Stores the resulting text in the global variable so LIMSCopyScreen can display it.

#### Control: RCDMarkReviewedBtn (Button)

| Property | Value |
|----------|-------|
| X | 900 |
| Y | 718 |
| Width | 210 |
| Height | 40 |
| Text | `"Mark as Reviewed"` |
| Fill | `RGBA(0, 120, 212, 1)` |
| Color | `RGBA(255, 255, 255, 1)` |
| FontSize | 13 |
| FontWeight | `FontWeight.Semibold` |
| RadiusTopLeft | 4 |
| RadiusTopRight | 4 |
| RadiusBottomLeft | 4 |
| RadiusBottomRight | 4 |

**OnSelect formula:**

```
If(
    CountRows(Filter('Case Issues', CaseID = gblSelectedCase.ID)) = 0,
    Notify(
        "You must add at least one issue before marking this case as Reviewed.",
        NotificationType.Warning
    ),
    Patch(
        'Lab Cases',
        gblSelectedCase,
        {'Task status': {Value: "Reviewed"}}
    );
    Set(gblSelectedCase, LookUp('Lab Cases', ID = gblSelectedCase.ID));
    Refresh('Lab Cases');
    Notify(
        gblSelectedCase.'Sub-case ID' & " has been marked as Reviewed. The reportee will be notified.",
        NotificationType.Success
    );
    Navigate(ReviewerCaseListScreen, ScreenTransition.Fade)
)
```

**What this does:**
1. Checks that at least one issue exists. If not, shows a warning and stops.
2. Uses `Patch` to update the Task status to "Reviewed" in SharePoint.
3. `Set(gblSelectedCase, LookUp(...))` — Refreshes `gblSelectedCase` with the newly updated record so the status badge updates immediately if the user navigates back.
4. Notifies the user and goes back to the case list. (The Teams notification is handled by the Power Automate flow you will set up in Part 6.)

#### Control: RCDCaseCompletedBtn (Button)

| Property | Value |
|----------|-------|
| X | 1124 |
| Y | 718 |
| Width | 222 |
| Height | 40 |
| Text | `"Case Completed"` |
| Fill | `RGBA(16, 124, 16, 1)` |
| Color | `RGBA(255, 255, 255, 1)` |
| FontSize | 13 |
| FontWeight | `FontWeight.Semibold` |
| RadiusTopLeft | 4 |
| RadiusTopRight | 4 |
| RadiusBottomLeft | 4 |
| RadiusBottomRight | 4 |

**OnSelect formula:**

```
Patch(
    'Lab Cases',
    gblSelectedCase,
    {'Task status': {Value: "Case Completed"}}
);
Refresh('Lab Cases');
Notify(
    gblSelectedCase.'Sub-case ID' & " has been marked as Case Completed.",
    NotificationType.Success
);
Navigate(ReviewerCaseListScreen, ScreenTransition.Fade)
```


---

### Screen 4: LIMSCopyScreen

This screen shows a read-only text area with all LIMS-reportable issues formatted for pasting into the lab's LIMS system.

#### Control: LCHeader (Rectangle)

| Property | Value |
|----------|-------|
| X | 0 |
| Y | 0 |
| Width | 1366 |
| Height | 60 |
| Fill | `RGBA(0, 120, 212, 1)` |

#### Control: LCHeaderTitle (Label)

| Property | Value |
|----------|-------|
| X | 20 |
| Y | 0 |
| Width | 500 |
| Height | 60 |
| Text | `"Copy Issues for LIMS"` |
| Color | `RGBA(255, 255, 255, 1)` |
| FontSize | 18 |
| FontWeight | `FontWeight.Bold` |
| VerticalAlign | `VerticalAlign.Middle` |
| Fill | `RGBA(0, 0, 0, 0)` |

#### Control: LCCard (Rectangle)

| Property | Value |
|----------|-------|
| X | 183 |
| Y | 88 |
| Width | 1000 |
| Height | 580 |
| Fill | `RGBA(255, 255, 255, 1)` |
| BorderColor | `RGBA(225, 223, 221, 1)` |
| BorderThickness | 1 |
| RadiusTopLeft | 8 |
| RadiusTopRight | 8 |
| RadiusBottomLeft | 8 |
| RadiusBottomRight | 8 |

#### Control: LCCardTitle (Label)

| Property | Value |
|----------|-------|
| X | 199 |
| Y | 104 |
| Width | 968 |
| Height | 36 |
| Text | `"Copy Issues for LIMS"` |
| FontSize | 20 |
| FontWeight | `FontWeight.Bold` |
| Color | `RGBA(50, 49, 48, 1)` |
| Fill | `RGBA(0, 0, 0, 0)` |

#### Control: LCCardSubtitle (Label)

| Property | Value |
|----------|-------|
| X | 199 |
| Y | 144 |
| Width | 968 |
| Height | 32 |
| Text | `"The text below contains all issues marked Report in LIMS. Copy and paste it into your LIMS system."` |
| FontSize | 13 |
| Color | `RGBA(96, 94, 92, 1)` |
| Fill | `RGBA(0, 0, 0, 0)` |

#### Control: LCCaseHeaderLabel (Label)

| Property | Value |
|----------|-------|
| X | 199 |
| Y | 180 |
| Width | 968 |
| Height | 26 |
| Text | `"Case: " & gblSelectedCase.'Sub-case ID'` |
| FontSize | 13 |
| FontWeight | `FontWeight.Semibold` |
| Color | `RGBA(50, 49, 48, 1)` |
| Fill | `RGBA(0, 0, 0, 0)` |

#### Control: LCTextArea (Text input — read only)

This is a text input set to read-only mode so the user can select and copy the text.

Insert → Input → Text input. Rename to `LCTextArea`.

| Property | Value |
|----------|-------|
| X | 199 |
| Y | 210 |
| Width | 968 |
| Height | 380 |
| Mode | `TextMode.MultiLine` |
| Default | `"Case: " & gblSelectedCase.'Sub-case ID' & Char(13) & Char(10) & "Review Issues for LIMS:" & Char(13) & Char(10) & Char(13) & Char(10) & gblLIMSText` |
| DisplayMode | `DisplayMode.View` |
| Fill | `RGBA(250, 250, 250, 1)` |
| BorderColor | `RGBA(225, 223, 221, 1)` |
| BorderThickness | 1 |
| RadiusTopLeft | 4 |
| RadiusTopRight | 4 |
| RadiusBottomLeft | 4 |
| RadiusBottomRight | 4 |
| FontSize | 13 |
| Color | `RGBA(50, 49, 48, 1)` |

**What the Default formula does:**
- Constructs the header: `"Case: "` followed by the Sub-case ID.
- Then a line break (`Char(13) & Char(10)` produces a new line).
- Then `"Review Issues for LIMS:"` as the section heading.
- Then two line breaks (a blank line).
- Then `gblLIMSText` which was built on the previous screen using `Concat`.

`DisplayMode.View` means the text box shows the text and allows selecting/copying, but the user cannot edit it.

#### Control: LCCloseBtn (Button)

| Property | Value |
|----------|-------|
| X | 199 |
| Y | 604 |
| Width | 160 |
| Height | 40 |
| Text | `"Close"` |
| Fill | `RGBA(243, 242, 241, 1)` |
| Color | `RGBA(50, 49, 48, 1)` |
| BorderColor | `RGBA(225, 223, 221, 1)` |
| BorderThickness | 1 |
| RadiusTopLeft | 4 |
| RadiusTopRight | 4 |
| RadiusBottomLeft | 4 |
| RadiusBottomRight | 4 |
| FontSize | 13 |
| OnSelect | `Navigate(ReviewerCaseDetailScreen, ScreenTransition.Back)` |

#### Control: LCCopyBtn (Button)

| Property | Value |
|----------|-------|
| X | 375 |
| Y | 604 |
| Width | 200 |
| Height | 40 |
| Text | `"Copy to Clipboard"` |
| Fill | `RGBA(0, 120, 212, 1)` |
| Color | `RGBA(255, 255, 255, 1)` |
| FontSize | 13 |
| FontWeight | `FontWeight.Semibold` |
| RadiusTopLeft | 4 |
| RadiusTopRight | 4 |
| RadiusBottomLeft | 4 |
| RadiusBottomRight | 4 |
| OnSelect | `Copy(LCTextArea.Text); Notify("Text copied to clipboard.", NotificationType.Success)` |

**What `Copy(LCTextArea.Text)` does:** The built-in `Copy` function puts the given text onto the user's system clipboard, exactly as if they had pressed Ctrl+C. After copying, a green success notification appears.

---

### Screen 5: ReporteeCaseListScreen

This screen shows the reportee (submitting officer) all cases assigned to them that have been reviewed and need attention.

#### Control: RPLHeader (Rectangle)

| Property | Value |
|----------|-------|
| X | 0 |
| Y | 0 |
| Width | 1366 |
| Height | 60 |
| Fill | `RGBA(0, 120, 212, 1)` |

#### Control: RPLHeaderBreadcrumb (Label)

| Property | Value |
|----------|-------|
| X | 20 |
| Y | 0 |
| Width | 500 |
| Height | 60 |
| Text | `"Reportee  >  My Cases"` |
| Color | `RGBA(255, 255, 255, 1)` |
| FontSize | 16 |
| FontWeight | `FontWeight.Semibold` |
| VerticalAlign | `VerticalAlign.Middle` |
| Fill | `RGBA(0, 0, 0, 0)` |

#### Control: RPLSwitchRoleBtn (Button)

| Property | Value |
|----------|-------|
| X | 1206 |
| Y | 10 |
| Width | 140 |
| Height | 40 |
| Text | `"Switch Role"` |
| Fill | `RGBA(255, 255, 255, 0.2)` |
| Color | `RGBA(255, 255, 255, 1)` |
| FontSize | 13 |
| BorderColor | `RGBA(255, 255, 255, 0.5)` |
| BorderThickness | 1 |
| RadiusTopLeft | 4 |
| RadiusTopRight | 4 |
| RadiusBottomLeft | 4 |
| RadiusBottomRight | 4 |
| OnSelect | `Navigate(HomeScreen, ScreenTransition.Fade)` |

#### Control: RPLPageTitle (Label)

| Property | Value |
|----------|-------|
| X | 20 |
| Y | 68 |
| Width | 700 |
| Height | 36 |
| Text | `"My Cases — Reviewed  (" & CountRows(Filter('Lab Cases', 'Task status'.Value = "Reviewed", 'ID SO'.Email = User().Email)) & ")"` |
| Color | `RGBA(50, 49, 48, 1)` |
| FontSize | 22 |
| FontWeight | `FontWeight.Bold` |
| Fill | `RGBA(0, 0, 0, 0)` |

**What this formula does:** Counts how many cases have status "Reviewed" AND belong to the currently logged-in user (matching their email to the ID SO person column), then shows that number in parentheses after the title.

#### Control: RPLSearchInput (Text input)

| Property | Value |
|----------|-------|
| X | 20 |
| Y | 112 |
| Width | 300 |
| Height | 36 |
| HintText | `"Search by Sub-case ID..."` |
| Fill | `RGBA(255, 255, 255, 1)` |
| BorderColor | `RGBA(225, 223, 221, 1)` |
| BorderThickness | 1 |
| RadiusTopLeft | 4 |
| RadiusTopRight | 4 |
| RadiusBottomLeft | 4 |
| RadiusBottomRight | 4 |
| FontSize | 14 |

#### Control: RPLStatusDropdown (Dropdown)

Insert → Input → Dropdown. Rename to `RPLStatusDropdown`.

| Property | Value |
|----------|-------|
| X | 330 |
| Y | 112 |
| Width | 280 |
| Height | 36 |
| Items | `["Reviewed (Action Required)", "All My Cases"]` |
| Default | `"Reviewed (Action Required)"` |
| Fill | `RGBA(255, 255, 255, 1)` |
| BorderColor | `RGBA(225, 223, 221, 1)` |
| BorderThickness | 1 |
| RadiusTopLeft | 4 |
| RadiusTopRight | 4 |
| RadiusBottomLeft | 4 |
| RadiusBottomRight | 4 |
| FontSize | 13 |

#### Column header labels for the Reportee case list

Add these labels at Y=158, Height=40, same styling as the reviewer column headers.

| Control name | X | Width | Text |
|--------------|---|-------|------|
| RPLColSubcase | 20 | 130 | `"Sub-case ID"` |
| RPLColSubmit | 152 | 110 | `"Submission Date"` |
| RPLColDue | 264 | 100 | `"Due Date"` |
| RPLColType | 366 | 120 | `"Case Type"` |
| RPLColFlow | 488 | 70 | `"FLOW?"` |
| RPLColExhibits | 560 | 80 | `"Exhibits"` |
| RPLColIDSO | 642 | 140 | `"ID SO"` |
| RPLColReviewer | 784 | 140 | `"Reviewer"` |
| RPLColStatus | 926 | 130 | `"Status"` |
| RPLColIssues | 1058 | 120 | `"Issues"` |

#### Control: RPLCasesGallery (Vertical Gallery)

| Property | Value |
|----------|-------|
| X | 20 |
| Y | 198 |
| Width | 1326 |
| Height | 530 |
| TemplateHeight | 52 |
| TemplatePadding | 0 |
| ShowScrollbar | true |
| Fill | `RGBA(255, 255, 255, 1)` |

**Items formula:**

```
Sort(
    Filter(
        'Lab Cases',
        'ID SO'.Email = User().Email,
        If(
            RPLStatusDropdown.Selected.Value = "All My Cases",
            true,
            'Task status'.Value = "Reviewed"
        ),
        Or(
            RPLSearchInput.Text = "",
            StartsWith('Sub-case ID', RPLSearchInput.Text)
        )
    ),
    'Due date',
    SortOrder.Ascending
)
```

**What this does:**
- `'ID SO'.Email = User().Email` — Filters to show only the logged-in user's cases. `User().Email` returns the email of the person currently using the app.
- The `If(RPLStatusDropdown... = "All My Cases", true, ...)` part shows all cases when "All My Cases" is selected, or only "Reviewed" cases otherwise.
- The search filter works the same as in the reviewer list.

**Controls inside RPLCasesGallery template:**

Add the same set of labels as in the reviewer gallery (SubcaseID, SubmitDate, DueDate, CaseType, Flow, Exhibits, IDSO, Reviewer, StatusBadge) using the same X positions and formulas.

Then add the open issue count label:

##### RPL_IssuesLabel (Label)

| Property | Value |
|----------|-------|
| X | 1058 |
| Y | 10 |
| Width | 110 |
| Height | 32 |
| Text | `CountRows(Filter('Case Issues', CaseID = ThisItem.ID, IssueStatus.Value = "Open")) & " open"` |
| FontSize | 11 |
| FontWeight | `FontWeight.Semibold` |
| Align | `Align.Center` |
| VerticalAlign | `VerticalAlign.Middle` |
| RadiusTopLeft | 12 |
| RadiusTopRight | 12 |
| RadiusBottomLeft | 12 |
| RadiusBottomRight | 12 |
| Fill | `If(CountRows(Filter('Case Issues', CaseID = ThisItem.ID, IssueStatus.Value = "Open")) > 0, RGBA(255, 224, 214, 1), RGBA(223, 246, 221, 1))` |
| Color | `If(CountRows(Filter('Case Issues', CaseID = ThisItem.ID, IssueStatus.Value = "Open")) > 0, RGBA(164, 38, 44, 1), RGBA(16, 124, 16, 1))` |

**What the Fill/Color formula does:** If there are open issues the badge turns red (urgent). If all issues are resolved it turns green (done).

Also add a row separator Rectangle at Y=51, Height=1, Width=1326, Fill=`RGBA(225, 223, 221, 1)`.

**Gallery OnSelect:**

```
Set(gblSelectedCase, ThisItem);
Navigate(ReporteeIssueScreen, ScreenTransition.Fade)
```

---

### Screen 6: ReporteeIssueScreen

This is where the reportee reads the reviewer's issues, writes replies, marks issues as completed, and submits the case back.

#### Control: RPIHeader (Rectangle)

| Property | Value |
|----------|-------|
| X | 0 |
| Y | 0 |
| Width | 1366 |
| Height | 60 |
| Fill | `RGBA(0, 120, 212, 1)` |

#### Control: RPIBackBtn (Button)

| Property | Value |
|----------|-------|
| X | 20 |
| Y | 10 |
| Width | 200 |
| Height | 40 |
| Text | `"← Back to Case List"` |
| Fill | `RGBA(255, 255, 255, 0.2)` |
| Color | `RGBA(255, 255, 255, 1)` |
| FontSize | 13 |
| BorderColor | `RGBA(255, 255, 255, 0.5)` |
| BorderThickness | 1 |
| RadiusTopLeft | 4 |
| RadiusTopRight | 4 |
| RadiusBottomLeft | 4 |
| RadiusBottomRight | 4 |
| OnSelect | `Navigate(ReporteeCaseListScreen, ScreenTransition.Back)` |

#### Case Details Card (same as Reviewer detail screen)

Add the same Case Details card (rectangle + field labels) at Y=68, same structure as in Screen 3. Use exactly the same fields and formulas (all reading from `gblSelectedCase`). The card should be:

| Property | Value |
|----------|-------|
| Name | RPICaseCard |
| X | 20 |
| Y | 68 |
| Width | 1326 |
| Height | 200 |

Add all the same field label pairs inside it (Sub-case ID, Status badge, Submission Date, Due Date, Case Type, FLOW Case, No. of Exhibits, ID SO, Reviewer) — same X positions, same formulas as described in Screen 3.

#### Issues to Address Card

Add a rectangle:

| Property | Value |
|----------|-------|
| Name | RPIIssuesCard |
| X | 20 |
| Y | 278 |
| Width | 1326 |
| Height | 390 |
| Fill | `RGBA(255, 255, 255, 1)` |
| BorderColor | `RGBA(225, 223, 221, 1)` |
| BorderThickness | 1 |
| RadiusTopLeft | 8 |
| RadiusTopRight | 8 |
| RadiusBottomLeft | 8 |
| RadiusBottomRight | 8 |

Add a card title label:

| Property | Value |
|----------|-------|
| Name | RPIIssuesCardTitle |
| X | 36 |
| Y | 286 |
| Width | 400 |
| Height | 28 |
| Text | `"Issues to Address"` |
| FontSize | 15 |
| FontWeight | `FontWeight.Bold` |
| Color | `RGBA(50, 49, 48, 1)` |
| Fill | `RGBA(0, 0, 0, 0)` |

Add a subtitle label:

| Property | Value |
|----------|-------|
| Name | RPIIssuesSubtitle |
| X | 36 |
| Y | 318 |
| Width | 1290 |
| Height | 22 |
| Text | `"Reply to each issue and mark as completed. All issues must be addressed before submitting."` |
| FontSize | 12 |
| Color | `RGBA(96, 94, 92, 1)` |
| Fill | `RGBA(0, 0, 0, 0)` |

#### Control: RPIIssuesGallery (Vertical Gallery)

| Property | Value |
|----------|-------|
| X | 20 |
| Y | 344 |
| Width | 1326 |
| Height | 316 |
| TemplateHeight | 160 |
| TemplatePadding | 0 |
| ShowScrollbar | true |
| Fill | `RGBA(255, 255, 255, 1)` |

**Items formula:**

```
SortByColumns(
    Filter(
        'Case Issues',
        CaseID = gblSelectedCase.ID
    ),
    "ReviewRound",
    SortOrder.Ascending
)
```

**Controls inside RPIIssuesGallery template (TemplateHeight=160):**

##### RPI_TierBadge (Label)

Same styling as RCDIss_TierBadge. X=8, Y=8, Width=80, Height=24.

##### RPI_TypeBadge (Label)

Same styling as RCDIss_TypeBadge. X=96, Y=8, Width=160, Height=24.

##### RPI_RoundLabel (Label)

X=264, Y=8, Width=100, Height=24. Text=`"Round " & Text(ThisItem.ReviewRound)`.

##### RPI_StatusBadge (Label)

Same as RCDIss_StatusBadge. X=372, Y=8, Width=100, Height=24.

##### RPI_Description (Label)

| Property | Value |
|----------|-------|
| X | 8 |
| Y | 38 |
| Width | 1280 |
| Height | 32 |
| Text | `ThisItem.IssueDescription` |
| FontSize | 13 |
| Color | `RGBA(50, 49, 48, 1)` |
| Fill | `RGBA(0, 0, 0, 0)` |

##### RPI_ReplyLabel (Label — above the text input)

| Property | Value |
|----------|-------|
| X | 8 |
| Y | 74 |
| Width | 200 |
| Height | 20 |
| Text | `"Your Reply"` |
| FontSize | 11 |
| FontWeight | `FontWeight.Semibold` |
| Color | `RGBA(96, 94, 92, 1)` |
| Fill | `RGBA(0, 0, 0, 0)` |

##### RPI_ReplyInput (Text input — multiline)

This is the key editable field where the reportee types their response.

| Property | Value |
|----------|-------|
| X | 8 |
| Y | 94 |
| Width | 1100 |
| Height | 56 |
| Mode | `TextMode.MultiLine` |
| Default | `ThisItem.SOReply` |
| HintText | `"Enter your response to this issue..."` |
| Fill | `RGBA(255, 255, 255, 1)` |
| BorderColor | `RGBA(225, 223, 221, 1)` |
| BorderThickness | 1 |
| RadiusTopLeft | 4 |
| RadiusTopRight | 4 |
| RadiusBottomLeft | 4 |
| RadiusBottomRight | 4 |
| FontSize | 13 |

**Important:** Inside a gallery, you cannot use `Reset()` to clear inputs because each row has its own copy. The `Default` property is pre-populated from `ThisItem.SOReply`, so existing replies show up when the user opens the screen.

##### RPI_CompletedCheckbox (Checkbox)

| Property | Value |
|----------|-------|
| X | 1118 |
| Y | 110 |
| Width | 200 |
| Height | 32 |
| Text | `"Mark as completed"` |
| Default | `ThisItem.IssueStatus.Value = "Completed"` |
| FontSize | 12 |
| Color | `RGBA(50, 49, 48, 1)` |
| Fill | `RGBA(0, 0, 0, 0)` |

##### RPI_SaveReplyBtn (Button)

| Property | Value |
|----------|-------|
| X | 1118 |
| Y | 94 |
| Width | 200 |
| Height | 36 |
| Text | `"Save Reply"` |
| Fill | `RGBA(0, 120, 212, 1)` |
| Color | `RGBA(255, 255, 255, 1)` |
| FontSize | 12 |
| RadiusTopLeft | 4 |
| RadiusTopRight | 4 |
| RadiusBottomLeft | 4 |
| RadiusBottomRight | 4 |

**OnSelect formula:**

```
Patch(
    'Case Issues',
    ThisItem,
    {
        SOReply: RPI_ReplyInput.Text,
        IssueStatus: If(
            RPI_CompletedCheckbox.Value,
            {Value: "Completed"},
            {Value: "Open"}
        )
    }
);
Refresh('Case Issues');
Notify("Reply saved.", NotificationType.Success)
```

**What this does:**
- `Patch('Case Issues', ThisItem, {...})` — Updates the existing issue record. `ThisItem` is the specific issue in this gallery row.
- `SOReply: RPI_ReplyInput.Text` — Saves whatever the reportee typed into the reply box.
- `IssueStatus: If(RPI_CompletedCheckbox.Value, {Value: "Completed"}, {Value: "Open"})` — If the checkbox is ticked, sets the status to Completed; otherwise leaves it Open.
- `Refresh('Case Issues')` — Forces the gallery to re-read from SharePoint so status badges update immediately.

> **Note on control names inside galleries:** When a gallery contains multiple rows, Power Apps appends numbers to control names internally (e.g., `RPI_ReplyInput_1`, `RPI_ReplyInput_2`). In the **OnSelect** formula of a button inside the same gallery row, you reference the controls by their template name (without the number), e.g., `RPI_ReplyInput.Text`. Power Apps resolves to the correct row automatically.

##### Row separator (Rectangle)

X=0, Y=159, Width=1326, Height=1, Fill=`RGBA(225, 223, 221, 1)`.

#### Submit Button and Helper Text

Add the submit button below the issues card:

#### Control: RPISubmitBtn (Button)

| Property | Value |
|----------|-------|
| X | 20 |
| Y | 674 |
| Width | 500 |
| Height | 48 |
| Text | `"Submit & Return to Ready for Review"` |
| FontSize | 15 |
| FontWeight | `FontWeight.Semibold` |
| RadiusTopLeft | 4 |
| RadiusTopRight | 4 |
| RadiusBottomLeft | 4 |
| RadiusBottomRight | 4 |

**DisplayMode formula** (determines whether the button is clickable or greyed out):

```
If(
    CountRows(
        Filter(
            'Case Issues',
            CaseID = gblSelectedCase.ID,
            IssueStatus.Value = "Open"
        )
    ) = 0
    &&
    CountRows(
        Filter('Case Issues', CaseID = gblSelectedCase.ID)
    ) > 0,
    DisplayMode.Edit,
    DisplayMode.Disabled
)
```

**What this does:** The button is only enabled (`DisplayMode.Edit`) when ALL of these are true:
- There are zero Open issues (all have been marked Completed), AND
- There is at least one issue total (prevents submitting a case that has no issues logged at all).

Otherwise the button is greyed out (`DisplayMode.Disabled`).

**Fill formula** (changes colour based on DisplayMode):

```
If(
    CountRows(Filter('Case Issues', CaseID = gblSelectedCase.ID, IssueStatus.Value = "Open")) = 0
    &&
    CountRows(Filter('Case Issues', CaseID = gblSelectedCase.ID)) > 0,
    RGBA(0, 120, 212, 1),
    RGBA(161, 159, 157, 1)
)
```

**Color**: `RGBA(255, 255, 255, 1)`

**OnSelect formula:**

```
Patch(
    'Lab Cases',
    gblSelectedCase,
    {'Task status': {Value: "Ready for Review"}}
);
Refresh('Lab Cases');
Notify(
    gblSelectedCase.'Sub-case ID' & " has been submitted back for re-review.",
    NotificationType.Success
);
Navigate(ReporteeCaseListScreen, ScreenTransition.Fade)
```

**What this does:** Sets the case status back to "Ready for Review". This will trigger the Power Automate flow (set up in Part 6) to notify the reviewer.

#### Control: RPIHelperText (Label)

This label shows a helpful message while the submit button is disabled.

| Property | Value |
|----------|-------|
| X | 530 |
| Y | 680 |
| Width | 600 |
| Height | 36 |
| Text | `If(CountRows(Filter('Case Issues', CaseID = gblSelectedCase.ID, IssueStatus.Value = "Open")) > 0, "All issues must be marked as completed before submitting.", "")` |
| FontSize | 13 |
| Color | `RGBA(164, 38, 44, 1)` |
| Fill | `RGBA(0, 0, 0, 0)` |
| VerticalAlign | `VerticalAlign.Middle` |


---

## Part 6 — Power Automate Flows

Power Automate flows run automatically in the background when data changes in SharePoint. You do not need to call them from Power Apps — they trigger on their own.

### How to create a new automated flow

1. Open a new browser tab and go to [make.powerautomate.com](https://make.powerautomate.com).
2. Click **+ Create** in the left navigation.
3. Click **Automated cloud flow**.
4. Give the flow a name (as specified below).
5. In the **Choose your flow's trigger** search box, type `SharePoint` and select **When an item is modified**.
6. Click **Create**.

---

### Flow 1: Notify Reportee When Case Is Marked as Reviewed

**Flow name:** `Notify Reportee — Case Reviewed`

**Purpose:** When a reviewer marks a case as "Reviewed", the reportee (ID SO) receives a Teams message telling them to address the issues.

#### Step 1: Trigger — When an item is modified

Click the trigger block and fill in:

| Field | Value |
|-------|-------|
| Site Address | Your SharePoint site URL (e.g., `https://yourcompany.sharepoint.com/sites/YourSite`) |
| List Name | `Lab Cases` |

#### Step 2: Add a Condition

Click **+ New step**. Search for **Condition** and select it.

In the Condition block, configure the left side to check the Task status:

- Click the left box and then click the lightning bolt icon (**Dynamic content**).
- Scroll down and find **Task status Value** (it will appear under "When an item is modified").
- Set the middle dropdown to **is equal to**.
- In the right box type exactly: `Reviewed`

This means the flow will only continue (do the next steps) when the item was modified and the Task status is now "Reviewed".

#### Step 3: If yes — Get the reportee's email

In the **If yes** branch, click **Add an action**.

Search for **Get user profile (V2)** from the **Office 365 Users** connector. Select it.

| Field | Value |
|-------|-------|
| User (UPN) | Click **Dynamic content** → select **ID SO Email** |

This step looks up the full user profile of the person in the "ID SO" column so we can send them a Teams message.

#### Step 4: Post a Teams message to the reportee

In the same **If yes** branch, click **Add an action**.

Search for **Post message in a chat or channel** from Microsoft Teams. Select it.

| Field | Value |
|-------|-------|
| Post as | Flow bot |
| Post in | Chat with Flow bot |
| Recipient | Click **Dynamic content** → select **Mail** from the "Get user profile" step above |
| Message | (see below) |

**Message body — click the Message field and compose:**

```
🔍 Case Reviewed — Action Required

Sub-case ID: [Dynamic content: Sub-case ID]
Case Type: [Dynamic content: Case Type Value]
Reviewer: [Dynamic content: Reviewer DisplayName]

Issues have been found with this case. Please open the Lab Case Tracker app to review the issues and respond.
```

To insert dynamic content: click inside the Message field, then click the **lightning bolt** icon at the edge of the field to open the Dynamic content panel. Click the field name to insert it.

#### Step 5: If no — Do nothing

Leave the **If no** branch empty. Click the X on any auto-added steps to remove them.

#### Step 6: Add trigger condition (prevents unnecessary trigger runs)

1. Click the **three dots (...)** on the trigger block at the top.
2. Click **Settings**.
3. Scroll to **Trigger Conditions**.
4. Click **+ Add**.
5. In the box enter:

```
@equals(triggerOutputs()?['body/Task_x0020_status/Value'], 'Reviewed')
```

> **Note:** SharePoint internal column names replace spaces with `_x0020_`. The internal name for "Task status" is typically `Task_x0020_status`. You can verify this by going to your SharePoint list → Settings → clicking the column name → looking at the URL, which will show `Field=Task_x0020_status` or similar.

6. Click **Done** then **Save** the flow.

#### Step 7: Save

Click **Save** at the top right. Test by opening the app, marking a case as Reviewed, and checking whether the Teams message appears.

---

### Flow 2: Notify Reviewer When Reportee Submits Case Back

**Flow name:** `Notify Reviewer — Ready for Re-review`

**Purpose:** When a reportee submits their responses and the case status returns to "Ready for Review" AND the case already has issues (meaning this is a returning case, not a first-time submission), the reviewer receives a Teams message.

#### Step 1: Trigger — When an item is modified

| Field | Value |
|-------|-------|
| Site Address | Your SharePoint site URL |
| List Name | `Lab Cases` |

#### Step 2: Add a Condition

Check whether the Task status is now "Ready for Review":

- Left: **Task status Value** (Dynamic content from trigger)
- Middle: **is equal to**
- Right: `Ready for Review`

#### Step 3: If yes — Check whether issues exist (nested condition)

Inside the **If yes** branch, add another **Condition** to verify this is a returning case (has issues), not a brand new submission:

1. Click **Add an action** inside the If yes branch.
2. Search for **Get items** (SharePoint). Select it.

| Field | Value |
|-------|-------|
| Site Address | Your SharePoint site URL |
| List Name | `Case Issues` |
| Filter Query | `CaseID eq ` then insert **Dynamic content: ID** from the trigger |
| Top Count | `1` |

3. After the Get items step, add a **Condition**:
   - Left: Click **Expression**, type `length(body('Get_items')?['value'])` and click OK.
   - Middle: **is greater than**
   - Right: `0`

This checks whether any issues exist for this case.

#### Step 4: If yes (issues exist) — Get reviewer email

Add an action: **Get user profile (V2)**

| Field | Value |
|-------|-------|
| User (UPN) | Dynamic content → **Reviewer Email** |

#### Step 5: Post Teams message to reviewer

Add action: **Post message in a chat or channel** (Teams)

| Field | Value |
|-------|-------|
| Post as | Flow bot |
| Post in | Chat with Flow bot |
| Recipient | Dynamic content → **Mail** from the Get user profile step |
| Message | (see below) |

**Message body:**

```
✅ Case Ready for Re-review

Sub-case ID: [Dynamic content: Sub-case ID]
Case Type: [Dynamic content: Case Type Value]

The reportee has addressed the issues and returned this case for re-review. Please open the Lab Case Tracker app to review.
```

#### Step 6: Add trigger condition

As with Flow 1, add a trigger condition to prevent unnecessary runs:

```
@equals(triggerOutputs()?['body/Task_x0020_status/Value'], 'Ready for Review')
```

#### Step 7: Save and test

Click **Save**. Test by having a reportee submit a case back and checking whether the reviewer receives the message.

---

### About Trigger Conditions

**Why use trigger conditions?** Without them, the flow would run every single time any field on any item in the Lab Cases list is changed — even if someone just updated the Remarks field or changed the Reviewer. Trigger conditions are evaluated before the flow actually runs, so they stop unnecessary executions early and help you stay within your Power Automate run limits.

**Finding internal column names:** If your trigger condition formula doesn't work, you may need to find the exact internal name of your "Task status" column. To do this:
1. Go to your SharePoint list.
2. Click **Settings** (gear icon) → **List settings**.
3. Under **Columns**, click **Task status**.
4. Look at the URL bar — it will contain something like `Field=Task%5Fx0020%5Fstatus`. Decode the `%5F` as underscore and `%20` as space to get the internal name.

---

## Part 7 — Testing Checklist

Work through this checklist top-to-bottom to verify the entire app works correctly. Each test assumes the previous tests passed.

### Pre-test setup

- [ ] At least two test case records exist in the Lab Cases list with status "Ready for Review"
- [ ] The Case Issues list exists and is connected in the app
- [ ] Both Power Automate flows are saved and turned on
- [ ] You have two Microsoft 365 test accounts available: one as Reviewer, one as Reportee (ID SO)
- [ ] Both test accounts have access to the SharePoint site and the app

---

### Test Block 1: HomeScreen

- [ ] Open the app. The HomeScreen appears with blue header, title, subtitle, and two cards.
- [ ] Both cards (Reviewer and Reportee) are visible and side by side.
- [ ] Clicking anywhere on the Reviewer card (not just the button) navigates to ReviewerCaseListScreen.
- [ ] The global variable `gblUserRole` is set to "Reviewer" (you can verify this using the app Monitor tool in Power Apps Studio).
- [ ] Navigate back (use browser back or re-open app), click Reportee card — navigates to ReporteeCaseListScreen.
- [ ] `gblUserRole` is set to "Reportee".

---

### Test Block 2: ReviewerCaseListScreen

- [ ] The breadcrumb "Reviewer > Case List" appears in the header.
- [ ] "Switch Role" button is visible top-right.
- [ ] Clicking Switch Role returns to HomeScreen.
- [ ] Table 1 ("New Cases — Pending Review") shows test cases with status "Ready for Review" and no issues.
- [ ] Table 2 ("Returning Cases — Reportee Completed Changes") is empty (no cases with issues yet).
- [ ] The search box filters Table 1 results as you type.
- [ ] The "Start Review" button appears only on "Ready for Review" rows in Table 1.
- [ ] Clicking "Start Review" on a case:
  - [ ] Changes the case status to "In Review" in the SharePoint list (verify directly in SharePoint).
  - [ ] Navigates to ReviewerCaseDetailScreen.
  - [ ] `gblSelectedCase` holds the correct case record.
- [ ] Clicking anywhere on a row (not the button) also navigates to ReviewerCaseDetailScreen.
- [ ] The "In Review" case now shows in Table 1 without a "Start Review" button.

---

### Test Block 3: ReviewerCaseDetailScreen — Case Details

- [ ] All case fields display correctly: Sub-case ID, Status, Submission Date, Due Date, Case Type, FLOW Case, No. of Exhibits, ID SO, Reviewer.
- [ ] The Status badge shows the correct colour for "In Review" (blue).
- [ ] "← Back to Case List" button returns to ReviewerCaseListScreen.

---

### Test Block 4: ReviewerCaseDetailScreen — Add Issues

- [ ] The Issues gallery is empty (no issues yet).
- [ ] The issue count badge shows "0 issues".
- [ ] Clicking "+ Add Issue" with blank fields shows a warning notification and does NOT add a record.
- [ ] Filling in Description, Issue Type, and Issue Tier then clicking "+ Add Issue":
  - [ ] Creates a new record in the Case Issues list (verify in SharePoint).
  - [ ] The new issue appears in the Issues gallery immediately.
  - [ ] The issue count badge increments to "1 issues".
  - [ ] The Description, Type, and Tier fields reset to empty after adding.
  - [ ] "Report in LIMS" checkbox defaults to checked.
- [ ] Add a second issue. Both appear in the gallery.
- [ ] The T1/T2/T3 tier badges show the correct green/amber/red colours.

---

### Test Block 5: ReviewerCaseDetailScreen — Mark as Reviewed

- [ ] Clicking "Mark as Reviewed" before adding any issues shows a warning.
- [ ] After adding at least one issue, clicking "Mark as Reviewed":
  - [ ] Changes the case status to "Reviewed" in SharePoint.
  - [ ] A success notification appears.
  - [ ] You are returned to ReviewerCaseListScreen.
  - [ ] The case no longer appears in Table 1 (no longer "Ready for Review" or "In Review").
- [ ] The Power Automate Flow 1 fires and the reportee (ID SO) receives a Teams message. Check the Teams account of the person in the ID SO column.

---

### Test Block 6: LIMSCopyScreen

- [ ] Navigate back to the case detail screen (click the case row).
- [ ] At least one issue has "Report in LIMS" checked.
- [ ] Click "Copy Issues for LIMS":
  - [ ] Navigates to LIMSCopyScreen.
  - [ ] The text area shows the formatted issues text with "Case: [Sub-case ID]" header and each LIMS-flagged issue listed.
  - [ ] Issues with Report in LIMS = No are NOT included in the text.
  - [ ] "Copy to Clipboard" button copies the text (paste into Notepad to verify).
  - [ ] "Close" button returns to ReviewerCaseDetailScreen.

---

### Test Block 7: ReporteeCaseListScreen

- [ ] Logged in as (or pretending to be) the reportee (ID SO person on the case).
- [ ] Navigate to HomeScreen → Reportee.
- [ ] The page title shows the correct count of Reviewed cases.
- [ ] The case from Test Block 5 appears in the list with status "Reviewed".
- [ ] The Issues column shows a red badge with the correct open issue count.
- [ ] The search box and status dropdown filter the list correctly.
- [ ] Selecting "All My Cases" from the dropdown shows cases at all statuses.
- [ ] Clicking a row navigates to ReporteeIssueScreen with the correct case.

---

### Test Block 8: ReporteeIssueScreen

- [ ] Case Details card shows all the correct read-only fields.
- [ ] All issues from the reviewer appear in the issues gallery.
- [ ] Tier, Type, and Round badges display correctly.
- [ ] The Submit button is DISABLED (greyed out) because issues are still open.
- [ ] The helper text "All issues must be marked as completed before submitting." is visible.
- [ ] For each issue:
  - [ ] The reply text input is editable.
  - [ ] Typing a reply and clicking "Save Reply" saves it to SharePoint.
  - [ ] The reply persists if you navigate away and back.
  - [ ] Checking the "Mark as completed" checkbox and clicking "Save Reply" changes the issue status to "Completed".
  - [ ] The status badge in the gallery updates to show "Completed" (green).
- [ ] After marking ALL issues as Completed:
  - [ ] The Submit button becomes ENABLED (blue).
  - [ ] The helper text disappears.
- [ ] Clicking "Submit & Return to Ready for Review":
  - [ ] Sets the case status to "Ready for Review" in SharePoint.
  - [ ] A success notification appears.
  - [ ] You are returned to ReporteeCaseListScreen.
  - [ ] The case no longer appears in the "Reviewed (Action Required)" filter (or its status badge has changed).
  - [ ] Power Automate Flow 2 fires and the reviewer receives a Teams message.

---

### Test Block 9: Reviewer Re-review Cycle

- [ ] Logged back in as the Reviewer. Navigate to ReviewerCaseListScreen.
- [ ] Table 2 ("Returning Cases — Reportee Completed Changes") now shows the case.
- [ ] The Issues count badge on Table 2 shows the correct number of issues.
- [ ] Clicking "Re-review" (or clicking the row) opens ReviewerCaseDetailScreen.
- [ ] All existing issues show with SO Replies in blue boxes.
- [ ] A new issue can be added (it will get a ReviewRound number of 2 if the formula works correctly — verify by checking the Case Issues list in SharePoint after adding).
- [ ] "Case Completed" button changes status to "Case Completed" and returns to the case list.
- [ ] The completed case does NOT appear in Table 1 or Table 2 (it is filtered out because its status is "Case Completed").

---

### Test Block 10: Edge Cases

- [ ] Try submitting as Reportee with one remaining Open issue — submit button stays disabled.
- [ ] Try adding an issue with only some fields filled in — warning appears, no record created.
- [ ] Open the app on a case that has zero issues. The Issues gallery shows "0 issues" badge. "Mark as Reviewed" button shows a warning.
- [ ] Verify that the LIMS text does NOT include issues where ReportInLIMS = No (uncheck the LIMS checkbox when adding an issue to test this).
- [ ] Verify delegation: if you have more than 500 cases in the Lab Cases list, check whether the gallery still filters and sorts correctly. If not, add indexes to the "Task status" and "Sub-case ID" columns in SharePoint list settings (go to List settings → Indexed columns → Add a new index).

---

## Tips, Troubleshooting, and Common Mistakes

### Delegation warnings

Power Apps shows a blue delegation warning triangle on gallery Items formulas that use certain functions on large lists. For lists under 2,000 items this is not a problem. For larger lists:

1. In your SharePoint list, go to **Settings** → **Indexed columns** → **Create a new index**.
2. Add an index on **Task status** and another on **Sub-case ID**.
3. In Power Apps, go to **File** → **Settings** → **General** → increase **Data row limit** to 2000.

### Gallery not refreshing

If the gallery does not update after a `Patch`, add `Refresh('Lab Cases')` or `Refresh('Case Issues')` after the Patch call:

```
Patch('Lab Cases', gblSelectedCase, {'Task status': {Value: "Reviewed"}});
Refresh('Lab Cases');
Navigate(ReviewerCaseListScreen, ScreenTransition.Fade)
```

### Person columns showing blank

Person column values require `.DisplayName` or `.Email`:

- Display the person's name: `ThisItem.Reviewer.DisplayName`
- Get their email: `ThisItem.Reviewer.Email`
- Check if current user: `ThisItem.'ID SO'.Email = User().Email`

### Choice columns need {Value: "..."} in Patch

When patching a Choice column you must wrap the value:

```
// CORRECT:
Patch('Lab Cases', gblSelectedCase, {'Task status': {Value: "Reviewed"}})

// WRONG — will cause an error:
Patch('Lab Cases', gblSelectedCase, {'Task status': "Reviewed"})
```

### Flow triggers on every change

Use trigger conditions on both flows (as described in Part 6) to prevent them running on every single field edit.

### Date formatting

`Text(ThisItem.'Submission date', "dd/mm/yyyy")` formats a date for display. Power Apps stores dates in ISO format internally. Always use `Text()` with a format string when displaying dates in labels.

### The `||` and `&&` operators

In Power Apps formulas:
- `||` means OR
- `&&` means AND
- `!` means NOT (so `!IsBlank(x)` means "x is not blank")

### Testing flows without waiting

After saving a Power Automate flow, you can test it immediately by clicking **Test** (top right in the flow editor), choosing **Manually**, then clicking **Test**. You will need to provide a sample trigger input or go to the actual list and modify an item.

### Common formula errors

| Error | Likely cause | Fix |
|-------|-------------|-----|
| Red underline on `'Sub-case ID'` | Missing single quotes | Wrap column names with spaces in single quotes |
| "The name is not valid" | Control name typo | Check spelling of the control name in Tree View |
| Gallery shows blank rows | Items formula references wrong list | Verify the list name in the Items formula matches exactly |
| Patch creates duplicate records | Using `ThisItem` instead of `Defaults()` for new records | Use `Defaults('Case Issues')` for new records, `ThisItem` only for updates |
| Dropdown shows "[Object]" | Choice column not using `.Value` | Add `.Value` e.g. `RCDIssueTypeDropdown.Selected.Value` |

---

## Quick Reference: Screen Navigation Map

```
HomeScreen
├── [Reviewer card] → ReviewerCaseListScreen
│   ├── [Row tap / Re-review] → ReviewerCaseDetailScreen
│   │   ├── [Copy Issues for LIMS] → LIMSCopyScreen
│   │   │   └── [Close] → ReviewerCaseDetailScreen
│   │   ├── [Mark as Reviewed] → ReviewerCaseListScreen
│   │   └── [Case Completed] → ReviewerCaseListScreen
│   └── [Switch Role] → HomeScreen
└── [Reportee card] → ReporteeCaseListScreen
    ├── [Row tap] → ReporteeIssueScreen
    │   ├── [Submit] → ReporteeCaseListScreen
    │   └── [Back] → ReporteeCaseListScreen
    └── [Switch Role] → HomeScreen
```

---

## Quick Reference: Global Variables

| Variable | Type | Set in | Used for |
|----------|------|--------|---------|
| `gblUserRole` | Text ("Reviewer" or "Reportee") | HomeScreen role buttons | (Optional filtering / future personalisation) |
| `gblSelectedCase` | Record from Lab Cases | Any gallery OnSelect | Populating all detail screens |
| `gblLIMSText` | Text | RCDCopyLIMSBtn OnSelect | Displaying LIMS-formatted text on LIMSCopyScreen |

---

## Quick Reference: All Screen Names and Their Purposes

| Screen | Purpose |
|--------|---------|
| `HomeScreen` | Role selection landing page |
| `ReviewerCaseListScreen` | Shows all cases awaiting review (new and returning) |
| `ReviewerCaseDetailScreen` | Case detail, issue logging, status actions |
| `LIMSCopyScreen` | Formatted LIMS text for clipboard copy |
| `ReporteeCaseListScreen` | Shows reportee's cases needing attention |
| `ReporteeIssueScreen` | Issue response, completion marking, case return |

---

*End of Guide*
