"""Build the requirement-to-test traceability matrix.

    cd backend && pytest --urs-report=../var/traceability.json
    python tools/traceability.py var/traceability.json > var/traceability.md

Exits non-zero if any test cites an ID that is not in docs/URS.md, or if any
test linked to a requirement failed.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_urs import requirement_ids  # noqa: E402


def main(report_path: str) -> int:
    results = json.loads(Path(report_path).read_text())
    if not results:
        print("The test report contains no requirement-tagged results", file=sys.stderr)
        return 1
    known = requirement_ids()
    by_req: dict[str, list[dict]] = defaultdict(list)
    unknown: set[str] = set()
    for result in results:
        for rid in result["urs"]:
            if rid not in known:
                unknown.add(rid)
            by_req[rid].append(result)

    covered = [r for r in known if by_req.get(r)]
    failed = sorted(
        {rid for rid, rs in by_req.items() for r in rs if r["outcome"] != "passed"}
    )

    print("# Requirement traceability matrix\n")
    print(f"Requirements with at least one test: **{len(covered)} / {len(known)}**\n")
    print("| Requirement | Tests | Result |\n|---|---|---|")
    for rid in known:
        tests = by_req.get(rid, [])
        if not tests:
            print(f"| {rid} | — | not yet covered |")
            continue
        status = "PASS" if all(t["outcome"] == "passed" for t in tests) else "FAIL"
        names = "<br>".join(t["test"] for t in tests)
        print(f"| {rid} | {names} | {status} |")

    if unknown:
        print(f"\nUnknown requirement IDs cited by tests: {sorted(unknown)}", file=sys.stderr)
    if failed:
        print(f"\nRequirements with failing tests: {failed}", file=sys.stderr)
    return 1 if unknown or failed else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    raise SystemExit(main(sys.argv[1]))
