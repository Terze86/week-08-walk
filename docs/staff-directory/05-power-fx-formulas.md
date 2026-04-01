# Power Fx Formulas — Staff Directory

All formulas reference the SharePoint site and list using the connections added in Power Apps Studio. Replace `"YOUR-GROUP-OBJECT-ID-HERE"` with the actual Azure AD Object ID of the `StaffDirAdmins` group and `"https://yourtenant.sharepoint.com/sites/yoursite"` with your actual SharePoint site URL.

---

## App.OnStart

Runs once when any user opens the app. Sets all global variables and navigates to the correct starting screen.

```powerfx
// 1. Store the admin group's Azure AD Object ID as a constant
Set(gblAdminGroupId, "YOUR-GROUP-OBJECT-ID-HERE");

// 2. Check whether the signed-in user is in the admin group.
//    Office365Groups.IsMemberOfGroup() checks direct membership.
//    Office365Users.MyProfile().Id returns the user's stable AAD Object ID (GUID).
Set(
    gblIsAdmin,
    Office365Groups.IsMemberOfGroup(
        gblAdminGroupId,
        Office365Users.MyProfile().Id
    ).value
);

// 3. Look up the current user's profile in StaffDirectory.
//    User().Email returns the UPN of the signed-in user.
//    Lower() prevents case-sensitivity mismatches.
Set(
    gblCurrentProfile,
    LookUp(
        StaffDirectory,
        Lower(UserPrincipalName) = Lower(User().Email)
    )
);

// 4. Navigate to the appropriate screen based on the above checks.
If(
    IsBlank(gblCurrentProfile),
        Navigate(scr_Register, ScreenTransition.Fade),
    gblIsAdmin,
        Navigate(scr_Directory, ScreenTransition.Fade),
    Navigate(scr_MyProfile, ScreenTransition.Fade)
)
```

> **Note on timing:** `App.OnStart` runs asynchronously. The app displays `scr_Loading` (the start screen) while OnStart is executing, then navigates away once the `If` block runs. This means users briefly see the loading screen — which is intentional.

---

## scr_Register

### btn_Register.OnSelect

```powerfx
// Step 1: Validate all required fields
If(
    IsBlank(txt_FullName.Text),
        Set(gblRegError, "Full Name is required."),

    IsBlank(txt_JobTitle.Text),
        Set(gblRegError, "Job Title is required."),

    IsBlank(drp_Department.Selected.Value),
        Set(gblRegError, "Please select a Department."),

    IsBlank(txt_WorkEmail.Text),
        Set(gblRegError, "Work Email is required."),

    !IsMatch(txt_WorkEmail.Text, Match.Email),
        Set(gblRegError, "Please enter a valid email address."),

    // Step 2: All valid — create the profile record
    With(
        {
            newRecord: Patch(
                StaffDirectory,
                Defaults(StaffDirectory),
                {
                    Title:              txt_FullName.Text,
                    JobTitle:           txt_JobTitle.Text,
                    Department:         { Value: drp_Department.Selected.Value },
                    WorkEmail:          txt_WorkEmail.Text,
                    AADObjectId:        Office365Users.MyProfile().Id,
                    UserPrincipalName:  User().Email,
                    IsActive:           true
                }
            )
        },

        // Step 3: If a signature was provided, upload it as an attachment
        If(
            !IsBlank(img_RegSignature.Image),
            SharePoint.AddAttachment(
                "https://yourtenant.sharepoint.com/sites/yoursite",
                "StaffDirectory",
                newRecord.ID,
                "signature.png",
                img_RegSignature.Image
            )
        );

        // Step 4: Refresh the global profile variable
        Set(
            gblCurrentProfile,
            LookUp(StaffDirectory, Lower(UserPrincipalName) = Lower(User().Email))
        );

        // Step 5: Clear any previous error
        Set(gblRegError, "");

        // Step 6: Navigate to the appropriate screen
        If(
            gblIsAdmin,
            Navigate(scr_Directory, ScreenTransition.Fade),
            Navigate(scr_MyProfile, ScreenTransition.Fade)
        )
    )
)
```

### lbl_RegError.Visible and lbl_RegError.Text

```powerfx
// Visible
!IsBlank(gblRegError)

// Text
gblRegError
```

---

## scr_MyProfile

### scr_MyProfile.OnVisible

```powerfx
// Refresh the profile in case it was just edited
Set(
    gblCurrentProfile,
    LookUp(StaffDirectory, Lower(UserPrincipalName) = Lower(User().Email))
);

// Load the signature attachment URL for display
Set(
    gblCurrentSignatureUrl,
    With(
        { attachments: SharePoint.GetAttachments(
            "https://yourtenant.sharepoint.com/sites/yoursite",
            "StaffDirectory",
            gblCurrentProfile.ID
          )
        },
        // Find the attachment named "signature.png"
        LookUp(attachments, Lower(FileName) = "signature.png").AbsoluteUri
    )
)
```

### img_SignatureDisplay.Image

```powerfx
If(
    !IsBlank(gblCurrentSignatureUrl),
    gblCurrentSignatureUrl,
    // Show a placeholder if no signature is uploaded
    SampleImage   // Replace with your own placeholder image control or blank
)
```

### btn_Edit.OnSelect

```powerfx
Set(gblSelectedRecord, gblCurrentProfile);
Set(gblSignatureChanged, false);
Navigate(scr_EditProfile, ScreenTransition.Slide)
```

---

## scr_EditProfile

### scr_EditProfile.OnVisible

```powerfx
// Load existing signature for preview
Set(
    gblEditSignatureUrl,
    With(
        { attachments: SharePoint.GetAttachments(
            "https://yourtenant.sharepoint.com/sites/yoursite",
            "StaffDirectory",
            gblSelectedRecord.ID
          )
        },
        LookUp(attachments, Lower(FileName) = "signature.png").AbsoluteUri
    )
);
Set(gblSignatureChanged, false)
```

### img_EditSignature (Add picture control) — OnChange

```powerfx
// Flag that a new signature has been provided
Set(gblSignatureChanged, true)
```

### img_EditSignaturePreview.Image

Shows the newly uploaded image if one was selected; otherwise shows the existing signature from SharePoint.

```powerfx
If(
    gblSignatureChanged,
    img_EditSignature.Image,           // Newly uploaded — base64 data URI
    gblEditSignatureUrl                // Existing — URL from SharePoint
)
```

### btn_Save.OnSelect

```powerfx
// Step 1: Validate
If(
    IsBlank(txt_EditFullName.Text),
        Set(gblEditError, "Full Name is required."),

    IsBlank(txt_EditJobTitle.Text),
        Set(gblEditError, "Job Title is required."),

    IsBlank(drp_EditDepartment.Selected.Value),
        Set(gblEditError, "Please select a Department."),

    IsBlank(txt_EditWorkEmail.Text),
        Set(gblEditError, "Work Email is required."),

    !IsMatch(txt_EditWorkEmail.Text, Match.Email),
        Set(gblEditError, "Please enter a valid email address."),

    // Step 2: Update the record
    Patch(
        StaffDirectory,
        gblSelectedRecord,
        {
            Title:      txt_EditFullName.Text,
            JobTitle:   txt_EditJobTitle.Text,
            Department: { Value: drp_EditDepartment.Selected.Value },
            WorkEmail:  txt_EditWorkEmail.Text
        }
    );

    // Step 3: Upload new signature if changed
    If(
        gblSignatureChanged,
        // Delete existing attachment first to avoid duplicates
        SharePoint.DeleteAttachment(
            "https://yourtenant.sharepoint.com/sites/yoursite",
            "StaffDirectory",
            gblSelectedRecord.ID,
            "signature.png"
        );
        // Upload the new one
        SharePoint.AddAttachment(
            "https://yourtenant.sharepoint.com/sites/yoursite",
            "StaffDirectory",
            gblSelectedRecord.ID,
            "signature.png",
            img_EditSignature.Image
        )
    );

    // Step 4: If the user edited their own profile, refresh gblCurrentProfile
    If(
        Lower(gblSelectedRecord.UserPrincipalName) = Lower(User().Email),
        Set(
            gblCurrentProfile,
            LookUp(StaffDirectory, Lower(UserPrincipalName) = Lower(User().Email))
        )
    );

    Set(gblEditError, "");
    Back()
)
```

> **Note on `SharePoint.DeleteAttachment`:** This is required before re-uploading to avoid duplicate attachments named `signature.png`. If the attachment does not exist (first-time save with a signature), the `DeleteAttachment` call will return an error that Power Apps will silently swallow — the `AddAttachment` call will still succeed. Alternatively, wrap the delete in an `IfError()` block if you want to be explicit.

### btn_Cancel.OnSelect

```powerfx
Set(gblEditError, "");
Back()
```

### lbl_EditError.Visible and lbl_EditError.Text

```powerfx
// Visible
!IsBlank(gblEditError)

// Text
gblEditError
```

---

## scr_Directory

### scr_Directory.OnVisible

```powerfx
// Security guard — redirect non-admins
If(!gblIsAdmin, Navigate(scr_MyProfile, ScreenTransition.None));

// Load all active staff into a local collection for client-side filtering
// This avoids delegation issues with the 'in' (substring) search operator
ClearCollect(
    colAllStaff,
    Filter(StaffDirectory, IsActive = true)
)
```

### gal_Directory.Items

```powerfx
Sort(
    Filter(
        colAllStaff,

        // Department filter — skip if "All" selected
        drp_FilterDept.Selected.Value = "All" ||
            Department.Value = drp_FilterDept.Selected.Value,

        // Text search — case-insensitive substring match across key fields
        // The 'in' operator on a local collection is not subject to delegation limits
        IsBlank(txt_Search.Text) ||
            (
                txt_Search.Text in Title ||
                txt_Search.Text in JobTitle ||
                txt_Search.Text in Department.Value ||
                txt_Search.Text in WorkEmail
            )
    ),
    Title,
    Ascending
)
```

### gal_Directory.OnSelect

```powerfx
Set(gblSelectedRecord, ThisItem);
Navigate(scr_AdminDetail, ScreenTransition.Slide)
```

### drp_FilterDept.Items

```powerfx
["All"] & Choices(StaffDirectory.Department)
```

### btn_Refresh.OnSelect

```powerfx
ClearCollect(colAllStaff, Filter(StaffDirectory, IsActive = true))
```

---

## scr_AdminDetail

### scr_AdminDetail.OnVisible

```powerfx
// Security guard
If(!gblIsAdmin, Navigate(scr_MyProfile, ScreenTransition.None));

// Load signature URL for the selected record
Set(
    gblDetailSignatureUrl,
    With(
        { attachments: SharePoint.GetAttachments(
            "https://yourtenant.sharepoint.com/sites/yoursite",
            "StaffDirectory",
            gblSelectedRecord.ID
          )
        },
        LookUp(attachments, Lower(FileName) = "signature.png").AbsoluteUri
    )
);

// Reset the confirm overlay
Set(gblShowDeactivateConfirm, false)
```

### btn_DetailEdit.OnSelect

```powerfx
Set(gblSignatureChanged, false);
Navigate(scr_EditProfile, ScreenTransition.Slide)
```

### btn_Deactivate.OnSelect

```powerfx
Set(gblShowDeactivateConfirm, true)
```

### btn_ConfirmYes.OnSelect

```powerfx
Patch(
    StaffDirectory,
    gblSelectedRecord,
    { IsActive: false }
);
Set(gblShowDeactivateConfirm, false);
Notify("Profile deactivated.", NotificationType.Success);
Navigate(scr_Directory, ScreenTransition.Fade)
```

### btn_ConfirmNo.OnSelect

```powerfx
Set(gblShowDeactivateConfirm, false)
```

### Confirm overlay Visible property (rect_ConfirmBg, lbl_ConfirmMsg, btn_ConfirmYes, btn_ConfirmNo)

```powerfx
gblShowDeactivateConfirm
```

---

## Delegation Warning

The `colAllStaff` collection approach used on `scr_Directory` loads all active records locally and then filters client-side. This means **all records are retrieved from SharePoint at once**.

- Default row limit: 500 (Power Apps default). Increase to 2000 in **App Settings > Advanced > Data row limit**.
- For organisations with more than 2000 staff, replace the collection approach with server-side OData filtering using only delegation-safe predicates (`eq`, `StartsWith`).

```powerfx
// Delegation-safe alternative (no substring search — StartsWith only)
Sort(
    Filter(
        StaffDirectory,
        IsActive = true,
        drp_FilterDept.Selected.Value = "All" ||
            Department.Value = drp_FilterDept.Selected.Value,
        IsBlank(txt_Search.Text) ||
            StartsWith(Title, txt_Search.Text)
    ),
    Title,
    Ascending
)
```
