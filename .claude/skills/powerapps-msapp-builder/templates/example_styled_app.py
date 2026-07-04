#!/usr/bin/env python3
"""Example: build a professional-looking app spec with scripts/ui_patterns.py.

This is the pattern to copy for any non-trivial app request (the Quality Log —
11 screens, ~665 controls — was built exactly this way). Define your logs,
seed sample data in OnStart, build the spec, then compile:

    python3 templates/example_styled_app.py /tmp/appspec.json
    python3 scripts/msapp_compiler.py --spec /tmp/appspec.json \
        --harvest assets/donor-harvest --out /tmp/build
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "scripts"))
from ui_patterns import StyledApp  # noqa: E402

SO = '["RA","CS","KEV","TZH"]'

app = StyledApp("StyledExample", title="🧪 Lab Tracker (example)")

app.add_log(
    "Sample Log", coll="colSamples", screen="scrSamples", group="TRACKING",
    desc="Incoming samples and their processing state.",
    fields=[
        ("Case", "Case No.", "text", None),
        ("SO", "SO", "dd", SO),
        ("SampleType", "Sample Type", "dd", '["Swab","Blood","Bone"]'),
        ("Remarks", "Remarks", "multi", None),
    ],
    table=[("Case", 1.4), ("SO", 0.7), ("SampleType", 1.2), ("Remarks", 2.7)],
)

app.add_log(
    "Issues", coll="colIssues", screen="scrIssues", group="TRACKING",
    desc="Problems found during processing.", restrict=True,  # hidden from SO
    banner="Restricted log: hidden from the SO role.",
    fields=[
        ("Case", "Case No.", "text", None),
        ("ReportedBy", "Reported by", "dd", SO),
        ("Issue", "Issue", "text", None),
        ("Details", "Details", "multi", None),
    ],
    table=[("Case", 1.2), ("ReportedBy", 1.0), ("Issue", 1.6), ("Details", 2.4)],
)

spec = app.build(onstart_data="""
ClearCollect(colSamples,
  {SN: 1, Case: "1843-00062", SO: "RA", SampleType: "Blood", Remarks: "", Status: "Approved"},
  {SN: 2, Case: "1543-00123", SO: "CS", SampleType: "Swab", Remarks: "Urgent", Status: "Pending"}
);
ClearCollect(colIssues,
  {SN: 1, Case: "1543-00123", ReportedBy: "CS", Issue: "Mislabelled tube", Details: "", Status: "Pending"}
)""")

out = sys.argv[1] if len(sys.argv) > 1 else "example-styled-appspec.json"
with open(out, "w") as f:
    json.dump(spec, f, indent=2)
n = sum(len(s["controls"]) + sum(len(c.get("children", [])) for c in s["controls"])
        for s in spec["screens"])
print("wrote %s: %d screens, ~%d controls" % (out, len(spec["screens"]), n))
