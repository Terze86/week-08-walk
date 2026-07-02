#!/usr/bin/env python3
"""One-time donor harvest: extract a Studio-exported .msapp into reusable assets.

Produces <out>/raw/ (the untouched donor tree) plus manifest.json describing:
  - control templates found (by harvest key), stored under templates/
  - the screen template
  - per-control YAML metadata parsed from donor Src/*.pa.yaml:
      Control type string, Variant string, and the property-name DELTA that
      Studio writes to YAML (YAML is a subset of the JSON rules)
  - the Studio comment banner, max ControlUniqueId, ControlCount conventions

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

# App-internal node types that are never offered as spec control types
INTERNAL_TEMPLATES = {"screen", "appinfo", "appInfo", "hostControl",
                      "galleryTemplate", "groupContainer"}


def load_controls(raw_dir):
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


def parse_screen_yaml(text):
    """Parse a donor screen .pa.yaml into per-control YAML metadata.

    Returns (screen_props, controls) where controls maps control name ->
    {"control": str, "variant": str|None, "props": [names]}. The format is
    regular enough for an indentation-based scan; property entries are lines
    '<name>: =...' or '<name>: |-' directly under a Properties: line.
    """
    lines = [ln for ln in text.splitlines() if not ln.lstrip().startswith("#")]
    controls = {}
    screen_props = []
    stack = []  # (indent_of_entry, control_name)
    cur_props_indent = None   # exact indent of property lines being collected
    cur_target = None         # list to append prop names to
    prop_re = re.compile(r"^(\s*)([\w.']+):\s*(\|-|=.*|)$")
    entry_re = re.compile(r"^(\s*)-\s+(\w+):\s*$")

    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())

        m = entry_re.match(line)
        if m:
            name = m.group(2)
            controls[name] = {"control": None, "variant": None, "props": []}
            stack.append((indent, name))
            cur_props_indent = None
            cur_target = None
            continue

        while stack and indent <= stack[-1][0]:
            stack.pop()
            cur_props_indent = None
            cur_target = None

        stripped = line.strip()
        cur_name = stack[-1][1] if stack else None
        if stripped.startswith("Control:") and cur_name:
            controls[cur_name]["control"] = stripped.split(":", 1)[1].strip()
            continue
        if stripped.startswith("Variant:") and cur_name:
            controls[cur_name]["variant"] = stripped.split(":", 1)[1].strip()
            continue
        if stripped == "Properties:":
            cur_props_indent = indent + 2
            cur_target = (controls[cur_name]["props"] if cur_name
                          else screen_props)
            continue
        if stripped == "Children:":
            cur_props_indent = None
            cur_target = None
            continue
        if cur_target is not None and cur_props_indent is not None:
            pm = prop_re.match(line)
            if pm and len(pm.group(1)) == cur_props_indent:
                cur_target.append(pm.group(2))
    return screen_props, controls


def harvest(msapp_path, out_dir):
    raw_dir = os.path.join(out_dir, "raw")
    tpl_dir = os.path.join(out_dir, "templates")
    shutil.rmtree(out_dir, ignore_errors=True)
    os.makedirs(raw_dir)
    os.makedirs(tpl_dir)

    # Studio zips with backslash member paths (Controls\4.json); normalize so
    # extraction produces real directories on POSIX. Packing with forward
    # slashes is confirmed importable (V7-V17 rebuild scripts used them).
    with zipfile.ZipFile(msapp_path) as zf:
        for info in zf.infolist():
            rel = info.filename.replace("\\", "/").strip("/")
            if not rel or info.is_dir():
                continue
            dest = os.path.join(raw_dir, *rel.split("/"))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with zf.open(info) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out)

    controls = load_controls(raw_dir)

    app_file = None
    screens = []            # (filename, TopParent)
    templates = {}          # harvest key -> full control node
    template_sources = {}   # harvest key -> donor control name
    max_uid = 0

    for fname, data in controls:
        top = data.get("TopParent", {})
        tname = (top.get("Template") or {}).get("Name", "")
        if tname in ("appinfo", "appInfo") or top.get("Name") == "App":
            app_file = fname
        elif tname == "screen":
            screens.append((fname, top))
        for node in walk_nodes(top):
            uid = node.get("ControlUniqueId")
            if uid and str(uid).isdigit():
                max_uid = max(max_uid, int(uid))
            node_tname = (node.get("Template") or {}).get("Name", "")
            if not node_tname or node_tname in INTERNAL_TEMPLATES:
                continue
            key = node_tname
            if node_tname == "gallery":
                # item controls are SIBLINGS of the galleryTemplate node,
                # direct children of the gallery (measured Studio structure)
                items = [ch for ch in node.get("Children") or []
                         if (ch.get("Template") or {}).get("Name")
                         != "galleryTemplate"]
                key = "gallery" if items else "gallery_blank"
            if key not in templates:
                templates[key] = copy.deepcopy(node)
                template_sources[key] = node.get("Name", "")

    if app_file is None:
        sys.exit("ERROR: could not find the App node (Controls/1.json) in the donor.")
    if not screens:
        sys.exit("ERROR: donor has no screens.")
    if "gallery" not in templates and "gallery_blank" in templates:
        templates["gallery"] = templates["gallery_blank"]
        template_sources["gallery"] = template_sources["gallery_blank"]

    # Screen template: first screen, children stripped
    screen_tpl = copy.deepcopy(screens[0][1])
    screen_tpl["Children"] = []

    for key, node in templates.items():
        with open(os.path.join(tpl_dir, f"{key}.json"), "w", encoding="utf-8") as f:
            json.dump(node, f, indent=1)
    with open(os.path.join(tpl_dir, "screen.json"), "w", encoding="utf-8") as f:
        json.dump(screen_tpl, f, indent=1)

    # ---- YAML metadata (Studio writes a DELTA of properties to YAML) ----
    src_dir = os.path.join(raw_dir, "Src")
    yaml_controls = {}      # donor control name -> {control, variant, props}
    screen_yaml_props = []  # prop-name delta on the screen node itself
    banner = ""
    for fname in sorted(os.listdir(src_dir)):
        if not fname.endswith(".pa.yaml"):
            continue
        with open(os.path.join(src_dir, fname), encoding="utf-8") as f:
            text = f.read()
        if not banner:
            banner_lines = []
            for ln in text.splitlines():
                if ln.startswith("#"):
                    banner_lines.append(ln)
                elif banner_lines:
                    break
            banner = "\n".join(banner_lines)
        if fname.startswith("_") or fname == "App.pa.yaml":
            continue
        sprops, ctrls = parse_screen_yaml(text)
        if sprops and not screen_yaml_props:
            screen_yaml_props = sprops
        yaml_controls.update(ctrls)

    # per-template-key YAML metadata via the seed control's donor name
    yaml_type_map = {}
    for key, src_name in template_sources.items():
        info = yaml_controls.get(src_name)
        if info and info.get("control"):
            yaml_type_map[key] = info

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
        "template_sources": template_sources,
        "max_uid": max_uid,
        "yaml_type_map": yaml_type_map,
        "yaml_controls": yaml_controls,
        "screen_yaml_props": screen_yaml_props,
        "yaml_banner": banner,
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
