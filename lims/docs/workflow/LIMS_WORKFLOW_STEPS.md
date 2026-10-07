# LIMS workflow steps

## 1. Staff access and workspaces

1. Maintain staff accounts and assign access through the LIMS Admin.
2. Each person signs in using their own account.
3. Provide separate workspaces for Case Scientist, Screening Lab Officer, DNA Lab Officer, Reviewer, CODIS Scientist and LIMS Admin.
4. The Case Scientist also performs profile reading. Use different people for the two independent readings.
5. Show each person the work and records needed for their role and assignments.
6. Limit CODIS Scientists to the requests, selected profiles and files specifically shared with them.

## 2. Case registration and exhibit receipt

1. Register a case from paper information or review an electronic submission.
2. Record the case reference, client, actual submitter, investigating officer, contact details and case information.
3. Create the laboratory subcase and record the exhibits submitted for examination.
4. Give each exhibit an identifier and barcode.
5. Check each exhibit's description, marking and seal against the submission.
6. Accept or reject exhibits individually. Record the reason for each rejection.
7. Prepare the receipt for the selected accepted exhibits and show any rejected exhibits separately.
8. Obtain the actual submitter's signature and record the receiving staff member.
9. Complete the receipt and retain the signed receipt record.
10. Record any refusal, failed signature or handover exception for follow-up.
11. Record where the received exhibits are stored and who has custody, where applicable.

## 3. Assignment and chain of custody

1. Assign a Case Scientist to the laboratory subcase.
2. Assign or claim the exhibit examination for a Screening Lab Officer.
3. Keep examination assignment separate from physical custody.
4. Scan a barcode or select an item when retrieving, storing or handing it over.
5. Record the source and destination person, location, or person and location, together with the movement time.
6. For a batch movement, select the exact items and one common destination.
7. Check all selected items before completing the batch movement.
8. For a person-to-person handover, the designated receiving person signs in and accepts the selected items.
9. Record later sample and material movements in the same way throughout laboratory work.
10. Request or authorize a custody correction with a reason when an earlier entry is wrong. Retain the original movement and the correction history.

## 4. Screening, sampling and scientific authorization

1. The Screening Lab Officer opens the assigned exhibit.
2. Record screening observations, examined sites and methods used.
3. Create the required samples and link each sample to its source exhibit and sampling site.
4. Generate sample identifiers and print their labels.
5. Complete the screening record for that exhibit.
6. The Case Scientist reviews the screening and proposed work.
7. Authorize the required DNA tests for the selected samples.
8. Allow individual exhibits and samples to progress while other exhibits in the case remain outstanding.

## 5. Exhibit photographs and documentation

1. Take and upload photographs for the exhibit.
2. Add captions and site details, and prepare any required crop, rotation or annotations.
3. Preserve the original photographs and complete the examination narrative.
4. The Screening Lab Officer completes and signs the documentation.
5. The Case Scientist reviews and signs the same documentation version.
6. If corrections are needed, prepare a new version and repeat the applicable sign-offs.
7. Authorized DNA work may proceed while photograph documentation is still outstanding.

## 6. Resources and bench preparation

1. Record the reagents, lots, containers and instruments used for laboratory work.
2. Check that the required resources are available and suitable for use.
3. Record the applicable resource checks and release decisions.
4. Exclude expired, withdrawn or unsuitable resources from new work.
5. Record actual resource use against the relevant batch.
6. Retain earlier usage records if a resource is later withdrawn, and review the affected work.

## 7. DNA extraction

1. The DNA Lab Officer selects authorized extraction requests and the corresponding samples.
2. Prepare the extraction plate, sample positions, controls, reagents and volumes.
3. A batch may contain samples from more than one case; preserve each sample's case association.
4. Confirm the plate setup and prepare the reference worksheet.
5. Retrieve the selected samples and record their custody movements.
6. Load the samples, reagents or master mixes, and volumes for extraction.
7. A different DNA Lab Officer independently checks the loaded sample positions, reagents or master mixes, and volumes.
8. Record the independent check and resolve any failed check before starting extraction.
9. Perform the extraction.
10. Record the outcome of each sample and control, and complete the batch record.
11. Link the resulting material to its source sample and extraction work.
12. Record the applicable QC review separately from batch completion.

## 8. Quantification

1. Select the extracted material for quantification and prepare the plate setup.
2. Prepare and export the QuantStudio 5 setup file.
3. Load the instrument setup and perform quantification.
4. Import the returned results and link them to the correct samples, materials and execution.
5. Review the results and record the applicable QC decision.
6. The Case Scientist decides the next test for each sample based on the results.

## 9. Amplification

1. Select the authorized amplification requests and materials.
2. Use GlobalFiler as the default amplification route.
3. When required, the Case Scientist selects Yfiler Plus or Fusion 6C based on the GlobalFiler results.
4. Prepare the amplification plate, controls, reagents and worksheet.
5. Perform amplification. A mandatory second-person pre-run setup check is not part of this amplification step.
6. Record each sample and control outcome, complete the batch record, and record the applicable QC review.
7. Link the amplified material to the source sample and earlier work.

## 10. Capillary electrophoresis

1. Select the authorized CE requests and amplified materials.
2. Prepare the CE plate and required controls, within the 96-position layout.
3. Prepare the instrument setup and reference worksheet.
4. Perform the CE run.
5. Record sample and control outcomes, complete the run, and record the applicable QC review.
6. Make the completed run available for independent profile reading.

## 11. Independent profile reading and approval

1. Two different Case Scientists independently read the profiles in GeneMapper.
2. Each reader exports their own GeneMapper TXT file and uploads it for the correct run.
3. Compare the two submitted readings.
4. Show any differences and record profile-specific issues.
5. If correction is needed, correct the reading in GeneMapper and upload a new export. Retain the previous export.
6. Repeat comparison until the current independent readings agree.
7. The Reviewer approves the matched profile versions.
8. Keep any unresolved profile issues visible even when the readings agree.

## 12. EPG attachment and Case Scientist review

1. Upload the EPG PDFs after profile approval.
2. Link each PDF to the correct sample, test, execution and profile version.
3. The Case Scientist reviews the approved profiles, EPGs, issues and relevant laboratory results.
4. Accept the suitable profiles or request further work or repeats, with reasons.
5. For a repeat, select the required stage and method, carry out the work, and link the resulting profile to the earlier profile.
6. Review the repeat result and resolve or explicitly disposition the repeat requirement.
7. EPG attachment itself does not require an additional scientific PDF approval.

## 13. CODIS reference requests, when required

1. The DNA Case Scientist identifies the external reference profile or profiles required and records the purpose of the request.
2. Select the CODIS Scientist responsible and send the request through LIMS.
3. The assigned CODIS Scientist opens and accepts the request.
4. Obtain the requested reference file from CODIS.
5. Upload the original CODIS-format reference file to the request and record the response.
6. Make the submitted response and file available to the requesting DNA Case Scientist.
7. The Case Scientist downloads and reviews the returned reference file.
8. Accept the response or request a correction. Retain earlier files and responses when a correction is supplied.

## 14. Profile submission to CODIS, when required

1. The DNA Case Scientist selects the exact approved and accepted profile versions to submit.
2. Record the submission reference and purpose, and select the responsible CODIS Scientist.
3. Share only the selected profiles and the required supporting profile file with that CODIS Scientist.
4. The CODIS Scientist accepts the request and retrieves the shared profiles or file.
5. The CODIS Scientist manually uploads the profiles into the external CODIS system.
6. Record the external submission reference and acknowledgement in LIMS, with any returned supporting file.
7. The DNA Case Scientist reviews the acknowledgement and completes the request or asks for a correction.

## 15. CODIS search, when required

1. The DNA Case Scientist selects the exact approved and accepted profile versions to search.
2. Record the search reference and purpose, and select the responsible CODIS Scientist.
3. Share only those selected profiles and the required search input file.
4. The CODIS Scientist accepts the request and retrieves the shared profiles or file.
5. The CODIS Scientist manually performs the search in the external CODIS system.
6. Obtain the original search output file, including the returned profile or match information.
7. Upload that output file to the LIMS search request and record the response.
8. The DNA Case Scientist downloads and reviews the returned search results.
9. Accept the response or request a correction. Retain every submitted result version and its review.

## 16. Interpretation

1. The Case Scientist selects the approved, accepted profiles to use for interpretation.
2. Create a populated copy of the appropriate Excel RMP or CPI template using those selected profiles.
3. Perform the interpretation in Excel using the laboratory's applicable rules.
4. Export the interpretation XML from Excel.
5. Import the returned XML into LIMS and link it to the correct selected profile versions and interpretation work.
6. Review the imported interpretation and resolve any required further work.
7. If interpretation changes, retain the earlier version and prepare the revised interpretation.

## 17. Report drafting, review and issue

1. The Case Scientist drafts the report using the selected profiles, interpretations and supporting examination records.
2. Submit the report version for administrative and technical review.
3. The Reviewer records the administrative review decision and any findings.
4. The Reviewer records the technical review decision and any findings. Both reviews must occur, even if the same qualified Reviewer performs them.
5. The report drafter addresses requested changes and submits the revised version for review.
6. Complete outstanding required documentation, repeats and review findings before final issue.
7. The assigned technical Reviewer performs the final sign-off on the reviewed report version.
8. Apply the signature image to the approved report PDF and retain the exact issued file.
9. Deliver the issued report to the intended recipient and record its delivery outcome and acknowledgement.
10. If an issued report needs an amendment, create an amended version and repeat administrative review, technical review, sign-off and delivery. Retain the earlier issued report.

## 18. Case closure and evidence disposition

1. Confirm that the laboratory subcase's required work and reporting are complete.
2. Close the completed laboratory subcase.
3. Close the parent case when all required laboratory subcases and obligations are complete.
4. Reopen the affected subcase and parent case when new required work or an issued-report amendment is needed.
5. For evidence collection, scan the issued report barcode and identify the eligible exhibits or samples.
6. Select the exact items to return, including partial collections where required.
7. Verify the actual collector's identity and record the physical handover and custody change.
8. For disposal, check outstanding work and holds, obtain the required authorization, and record any movement to a disposal location.
9. Record the actual destruction separately from movement to a disposal location, with the required confirmation and evidence.
10. Retain the examination records, files and custody history after return or destruction.

## 19. Administration and quality support

1. The LIMS Admin maintains staff access, role and laboratory assignments, and enabled or disabled account status.
2. Maintain the laboratory's locations and relevant reference information.
3. Investigate failed supporting tasks, such as printing or delivery, and record the resolution or retry.
4. Review access changes and workflow history without altering scientific decisions or earlier records.
5. Keep quality documents in SharePoint and link the relevant document and version to the applicable laboratory work.
6. Record the person, time and reason for workflow actions, corrections and changes throughout the process.
