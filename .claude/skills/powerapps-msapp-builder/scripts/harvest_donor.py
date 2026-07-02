#!/usr/bin/env python3
"""One-time donor harvest: extract a Studio-exported .msapp into reusable assets.

Produces <out>/raw/ (the untouched donor tree) plus manifest.json describing:
  - control templates found (by Template.Name), stored under templates/
  - the screen template
  - YAML control-type strings per template name (parsed from donor Src/*.pa.yaml)
  - max ControlUniqueId, ControlCount conventions, screen names

Usage: python harvest_donor.py donor.msapp [--out assets/donor-harvest]
"""
import argparse
import copy
import json
import os
import re
import shutil
import sys
import zipfile


def load_controls(raw_dir):
    """Return list of (filename, data) for Controls/*.json."""
    out = []
    cdir = os.path.join(raw_dir, "Controls")
    for fname in sorted(os.listdir(cdir)):
        if fname.endswith(".json"):
            with open(os.path.join(cdir, fname), encoding="utf-8") as f:
                out.append((fname, json.load(f)))
    return out


def walk_nodes(node):
    yield node
    for child in node.get("Children") or []:
        yield from walk_nodes(child)


def parse_yaml_type_map(raw_dir, name_to_template):
    """Map Template.Name -> {'control': 'Label@2.5.1', 'variant': 'Vertical'|None}
    by matching donor YAML entries against control names from the JSON."""
    type_map = {}
    src_dir = os.path.join(raw_dir, "Src")
    if not os.path.isdir(src_dir):
        return type_map
    entry_re = re.compile(
        r"-\s+(\w+):\s*\n(\s+)Control:\s*(\S+)\s*\n(?:\2Variant:\s*(\S+)\s*\n)?"
    )
    for fname in os.listdir(src_dir):
        if not fname.endswith(".yaml") or fname.startswith("_"):
            continue
        with open(os.path.join(src_dir, fname), encoding="utf-8") as f:
            text = f.read()
        for m in entry_re.finditer(text):
            ctrl_name, _, control_str, variant = m.groups()
            tname = name_to_template.get(ctrl_name)
            if tname and tname not in type_map:
                type_map[tname] = {"control": control_str, "variant": variant}
    return type_map


def harvest(msapp_path, out_dir):
    raw_dir = os.path.join(out_dir, "raw")
    tpl_dir = os.path.join(out_dir, "templates")
    shutil.rmtree(out_dir, ignore_errors=True)
    os.makedirs(raw_dir)
    os.makedirs(tpl_dir)

    with zipfile.ZipFile(msapp_path) as zf:
        zf.extractall(raw_dir)

    controls = load_controls(raw_dir)

    app_file = None
    screens = []          # (filename, TopParent)
    templates = {}        # Template.Name -> full control node
    name_to_template = {} # control name -> Template.Name
    max_uid = 0

    for fname, data in controls:
        top = data.get("TopParent", {})
        tname = (top.get("Template") or {}).get("Name", "")
        if tname in ("appinfo", "appInfo") or top.get("Name") == "App":
            app_file = fname
        elif tname == "screen":
            screens.append((fname, top))
        for node in walk_nodes(top):
            node_tname = (node.get("Template") or {}).get("Name", "")
            uid = node.get("ControlUniqueId")
            if uid and str(uid).isdigit():
                max_uid = max(max_uid, int(uid))
            name_to_template[node.get("Name", "")] = node_tname
            if node_tname in ("screen", "appinfo", "appInfo", "groupContainer"):
                continue
            # Skip galleryTemplate as a standalone template; it travels inside gallery
            if node_tname == "galleryTemplate":
                continue
            if node_tname and node_tname not in templates:
                templates[node_tname] = copy.deepcopy(node)

    if app_file is None:
        sys.exit("ERROR: could not find the App node (Controls/1.json) in the donor.")
    if not screens:
        sys.exit("ERROR: donor has no screens.")

    # Distinguish full vs blank gallery if two gallery seeds exist
    gallery_variants = {}
    for fname, data in controls:
        for node in walk_nodes(data.get("TopParent", {})):
            if (node.get("Template") or {}).get("Name") == "gallery":
                tmpl_children = []
                for ch in node.get("Children") or []:
                    if (ch.get("Template") or {}).get("Name") == "galleryTemplate":
                        tmpl_children = ch.get("Children") or []
                key = "gallery_blank" if len(tmpl_children) == 0 else "gallery"
                if key not in gallery_variants:
                    gallery_variants[key] = copy.deepcopy(node)
    templates.pop("gallery", None)
    templates.update(gallery_variants)
    if "gallery" not in templates and "gallery_blank" in templates:
        templates["gallery"] = templates["gallery_blank"]

    # Screen template: first screen, children stripped
    screen_tpl = copy.deepcopy(screens[0][1])
    screen_tpl["Children"] = []

    for tname, node in templates.items():
        with open(os.path.join(tpl_dir, f"{tname}.json"), "w", encoding="utf-8") as f:
            json.dump(node, f, indent=1)
    with open(os.path.join(tpl_dir, "screen.json"), "w", encoding="utf-8") as f:
        json.dump(screen_tpl, f, indent=1)

    yaml_type_map = parse_yaml_type_map(raw_dir, name_to_template)

    # ControlCount convention: which template names the donor's Properties.json counts
    with open(os.path.join(raw_dir, "Properties.json"), encoding="utf-8") as f:
        props = json.load(f)
    control_count_keys = sorted((props.get("ControlCount") or {}).keys())

    manifest = {
        "source_msapp": os.path.basename(msapp_path),
        "app_controls_file": app_file,
        "screen_files": [f for f, _ in screens],
        "screen_names": [t.get("Name") for _, t in screens],
        "templates": sorted(templates.keys()),
        "max_uid": max_uid,
        "yaml_type_map": yaml_type_map,
        "control_count_keys": control_count_keys,
        "has_checksum_file": os.path.exists(os.path.join(raw_dir, "checksum.json")),
    }
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Harvested donor into {out_dir}")
    print(f"  screens: {manifest['screen_names']}")
    print(f"  control templates: {manifest['templates']}")
    print(f"  max ControlUniqueId: {max_uid}")
    if manifest["has_checksum_file"]:
        print("  WARNING: donor contains checksum.json — newer format; "
              "probe ladder is mandatory before shipping real apps.")
    missing = [t for t in ("label", "button", "text", "dropdown", "gallery", "rectangle")
               if t not in templates]
    if missing:
        print(f"  NOTE: donor lacks seed controls for: {missing} — "
              f"apps cannot use those types until a richer donor is harvested.")
    return manifest


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("msapp")
    ap.add_argument("--out", default="assets/donor-harvest")
    args = ap.parse_args()
    harvest(args.msapp, args.out)
