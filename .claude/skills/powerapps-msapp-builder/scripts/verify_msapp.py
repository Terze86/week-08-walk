#!/usr/bin/env python3
"""Invariant verifier for an extracted .msapp tree.

Every ERROR here corresponds to a confirmed import-crash cause from the
V1-V17 project history; WARNINGs are visual/compat issues that import fine
but misbehave. Never ship a build with errors.

Usage: python verify_msapp.py <extracted-msapp-dir>
Importable: from verify_msapp import verify  ->  (errors, warnings)
"""
import json
import os
import re
import sys


def _walk(node):
    yield node
    for child in node.get("Children") or []:
        yield from _walk(child)


def _load_controls(build_dir):
    out = []
    cdir = os.path.join(build_dir, "Controls")
    for fname in sorted(os.listdir(cdir)):
        if fname.endswith(".json"):
            with open(os.path.join(cdir, fname), encoding="utf-8") as f:
                out.append((fname, json.load(f)))
    return out


def verify(build_dir):
    errors, warnings = [], []
    controls = _load_controls(build_dir)

    all_nodes = []
    for fname, data in controls:
        top = data.get("TopParent", {})
        for node in _walk(top):
            all_nodes.append((fname, node))

        tname = (top.get("Template") or {}).get("Name", "")
        # Controls file must be named after the TopParent's uid
        expected = f"{top.get('ControlUniqueId')}.json"
        if fname != expected:
            errors.append(f"{fname}: filename should be {expected} "
                          f"(TopParent uid={top.get('ControlUniqueId')})")
        # Index uniqueness per (type, variant) among DIRECT screen children —
        # Studio sequences Index per control type at screen level (duplicates
        # there silently delete the screen, V16), but gallery items all keep
        # Index=0 (measured donor convention), so deeper levels are exempt.
        if tname == "screen":
            seen = {}
            for ch in top.get("Children") or []:
                key = ((ch.get("Template") or {}).get("Name", ""),
                       ch.get("VariantName", ""), ch.get("Index"))
                if key in seen:
                    errors.append(
                        f"{fname} ({top.get('Name')}): duplicate Index="
                        f"{ch.get('Index')} for type {key[0]}/{key[1]} "
                        f"({seen[key]} vs {ch.get('Name')})")
                seen[key] = ch.get("Name")

    # UID uniqueness app-wide
    seen_uid = {}
    for fname, node in all_nodes:
        uid = str(node.get("ControlUniqueId"))
        if uid in seen_uid:
            errors.append(f"duplicate ControlUniqueId={uid}: "
                          f"{seen_uid[uid]} vs {node.get('Name')} ({fname})")
        seen_uid[uid] = node.get("Name")

    # PublishOrderIndex convention (measured from a real Studio export):
    # App/Host/screens all 0; non-screen controls form one global 0..N-1
    # sequence across screens. Gaps crash import (V13/V15).
    poi = []
    for fname, node in all_nodes:
        tname = (node.get("Template") or {}).get("Name", "")
        if tname in ("screen", "appinfo", "appInfo", "hostControl"):
            if int(node.get("PublishOrderIndex", 0)) != 0:
                warnings.append(f"{fname} {node.get('Name')}: {tname} has "
                                f"PublishOrderIndex={node.get('PublishOrderIndex')} "
                                f"(Studio uses 0)")
            continue
        poi.append(int(node.get("PublishOrderIndex", 0)))
    if sorted(poi) != list(range(len(poi))):
        spoi = sorted(poi)
        dupes = {p for p in spoi if spoi.count(p) > 1}
        detail = f"duplicates={sorted(dupes)}" if dupes else f"sequence={spoi[:20]}..."
        errors.append(f"PublishOrderIndex not a clean 0..N-1 sequence over "
                      f"non-screen controls ({detail})")

    # ControlPropertyState: Text entry must stay a complex object where template had one
    for fname, node in all_nodes:
        cps = node.get("ControlPropertyState") or []
        has_text_rule = any(r.get("Property") == "Text" for r in node.get("Rules") or [])
        text_entries = [e for e in cps if isinstance(e, dict)
                        and e.get("InvariantPropertyName") == "Text"]
        if has_text_rule and "Text" in [e for e in cps if isinstance(e, str)] and text_entries:
            errors.append(f"{fname} {node.get('Name')}: Text appears twice in "
                          f"ControlPropertyState (string AND object)")

    # Parent name references resolve
    names = {n.get("Name") for _, n in all_nodes}
    for fname, node in all_nodes:
        parent = node.get("Parent", "")
        if parent and parent not in names:
            errors.append(f"{fname} {node.get('Name')}: Parent='{parent}' "
                          f"does not exist in the app")

    # Template registration: every Template.Id must appear in Templates.json
    tpl_path = os.path.join(build_dir, "References", "Templates.json")
    tpl_text = ""
    if os.path.exists(tpl_path):
        with open(tpl_path, encoding="utf-8") as f:
            tpl_text = f.read()
    for fname, node in all_nodes:
        tpl = node.get("Template") or {}
        tid, tname = tpl.get("Id", ""), tpl.get("Name", "")
        if tname in ("appinfo", "appInfo", "screen", "galleryTemplate",
                     "hostControl"):
            continue
        if tpl_text and tid and tid not in tpl_text and tname not in tpl_text:
            errors.append(f"{fname} {node.get('Name')}: Template.Id '{tid}' "
                          f"not registered in References/Templates.json")

    # ControlCount in Properties.json matches actual counts. Measured donor
    # convention: only some template names are listed, and gallery
    # descendants are NOT counted.
    props_path = os.path.join(build_dir, "Properties.json")
    with open(props_path, encoding="utf-8") as f:
        props = json.load(f)
    declared = props.get("ControlCount") or {}
    actual = {}

    def count(node, in_gallery):
        tname = (node.get("Template") or {}).get("Name", "")
        if tname and not in_gallery:
            actual[tname] = actual.get(tname, 0) + 1
        for child in node.get("Children") or []:
            count(child, in_gallery or tname == "gallery")

    for _fname, data in controls:
        count(data.get("TopParent", {}), False)
    for key, cnt in declared.items():
        if actual.get(key, 0) != cnt:
            errors.append(f"Properties.json ControlCount['{key}']={cnt} "
                          f"but actual (excluding gallery descendants)="
                          f"{actual.get(key, 0)}")

    # Screen YAML mirrors exist and mention every control name
    src_dir = os.path.join(build_dir, "Src")
    for fname, data in controls:
        top = data.get("TopParent", {})
        if (top.get("Template") or {}).get("Name") != "screen":
            continue
        ypath = os.path.join(src_dir, f"{top.get('Name')}.pa.yaml")
        if not os.path.exists(ypath):
            errors.append(f"missing YAML mirror Src/{top.get('Name')}.pa.yaml")
            continue
        with open(ypath, encoding="utf-8") as f:
            ytext = f.read()
        for node in _walk(top):
            nm = node.get("Name")
            tn = (node.get("Template") or {}).get("Name")
            if tn in ("screen", "galleryTemplate"):
                continue
            if nm and nm not in ytext:
                errors.append(f"{ypath}: control '{nm}' present in JSON but not in YAML")

    # ---- content scans: crash + compat + visual rules ----
    for root, _dirs, files in os.walk(build_dir):
        for f in files:
            path = os.path.join(root, f)
            rel = os.path.relpath(path, build_dir)
            try:
                with open(path, encoding="utf-8") as fh:
                    text = fh.read()
            except (UnicodeDecodeError, PermissionError):
                continue
            # %RESERVED% legitimately appears in Studio's registry files
            # (Templates.json, Themes.json); it is only a defect inside
            # control formulas and YAML
            if rel.startswith("Src") or rel.startswith("Controls"):
                if "%RESERVED%" in text or ".RESERVED%" in text:
                    errors.append(f"{rel}: contains %RESERVED% enum prefix")
                if re.search(r"\bSortBy\s*\(", text):
                    warnings.append(f"{rel}: SortBy() — unsupported on old Power Fx tenants")
                if re.search(r"Navigate\([^)]*,\s*None\s*\)", text):
                    warnings.append(f"{rel}: Navigate(scr, None) — unsupported; drop the None")
                if "Width: =1366" in text or '"InvariantScript": "1366"' in text:
                    warnings.append(f"{rel}: hardcoded width 1366 — use App.Width")

    # Rectangle-specific visual rules — only for rectangles placed directly
    # on a screen (gallery-item rectangles like separators legitimately
    # carry ZIndex in Studio's own output)
    for fname, data in controls:
        top = data.get("TopParent", {})
        if (top.get("Template") or {}).get("Name") != "screen":
            continue
        for node in top.get("Children") or []:
            if (node.get("Template") or {}).get("Name") not in ("rectangle", "shape"):
                continue
            rules = {r.get("Property"): r.get("InvariantScript")
                     for r in node.get("Rules") or []}
            if rules.get("ZIndex") not in (None, "0"):
                warnings.append(f"{fname} {node.get('Name')}: screen-level rectangle "
                                f"has ZIndex={rules.get('ZIndex')} — will cover "
                                f"text; remove it")
            for req in ("X", "Y", "Height"):
                if req not in rules:
                    warnings.append(f"{fname} {node.get('Name')}: rectangle missing {req}")

    # Gallery visibility rules
    for fname, node in all_nodes:
        if (node.get("Template") or {}).get("Name") != "gallery":
            continue
        rules = {r.get("Property") for r in node.get("Rules") or []}
        if "TemplateSize" not in rules:
            warnings.append(f"{fname} {node.get('Name')}: gallery missing TemplateSize "
                            f"— renders empty")

    if os.path.exists(os.path.join(build_dir, "checksum.json")):
        warnings.append("build contains checksum.json (newer format) — contents were NOT "
                        "recomputed; run the probe ladder before shipping")

    return errors, warnings


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: verify_msapp.py <extracted-msapp-dir>")
    errors, warnings = verify(sys.argv[1])
    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    if errors:
        print(f"\n{len(errors)} error(s) — DO NOT SHIP THIS BUILD")
        sys.exit(1)
    print(f"\nOK — 0 errors, {len(warnings)} warning(s)")


if __name__ == "__main__":
    main()
