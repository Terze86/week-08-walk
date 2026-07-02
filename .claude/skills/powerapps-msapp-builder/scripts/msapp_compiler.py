#!/usr/bin/env python3
"""Compile an app spec into a complete, import-ready .msapp.

Strategy: never graft into a Studio export. Start from the harvested donor's
registries (Header, Properties, References/*, Resources/*), regenerate every
screen/control/YAML/editor-state file from one in-memory model, recompute all
cross-file invariants, verify, pack, and emit the .txt delivery bundle.

Identity conventions (measured from a real Studio export, July 2026):
  - ControlUniqueId: unique app-wide; App=1, Host=3, screens/controls from 4
  - Controls file name = screen's ControlUniqueId
  - Index: per (parent, Template.Name, VariantName) sequence starting at 0
  - PublishOrderIndex: 0 for App/Host/screens; one global 0..N-1 sequence over
    all non-screen controls, DFS order across screens in screen order
  - Src/*.pa.yaml holds a DELTA of properties (subset of JSON rules)

Usage:
  python msapp_compiler.py --spec appspec.json --harvest assets/donor-harvest --out build/MyApp
  python msapp_compiler.py --repack-donor --harvest assets/donor-harvest --out build/probe0
"""
import argparse
import copy
import json
import os
import re
import shutil
import sys
import zipfile
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify_msapp import verify  # noqa: E402

BEHAVIOR_PROPS = re.compile(r"^On[A-Z]")

# Fallbacks when the donor YAML didn't reveal a type string
STATIC_YAML_TYPES = {
    "label": {"control": "Label@2.5.1", "variant": None},
    "button": {"control": "Classic/Button@2.2.0", "variant": None},
    "text": {"control": "Classic/TextInput@2.3.2", "variant": None},
    "dropdown": {"control": "Classic/DropDown@2.3.1", "variant": None},
    "gallery": {"control": "Gallery@2.15.0", "variant": "Vertical"},
    "gallery_blank": {"control": "Gallery@2.15.0", "variant": "Vertical"},
    "rectangle": {"control": "Rectangle@2.3.0", "variant": None},
    "icon": {"control": "Classic/Icon@2.5.0", "variant": None},
    "image": {"control": "Image@2.2.3", "variant": None},
}

META_KEYS = ("__spec_props", "__yaml_info")


def set_rule(ctrl, prop, value):
    """Overwrite an existing rule's InvariantScript or append a new rule.
    New properties are also appended to ControlPropertyState as plain strings
    (the V9-confirmed convention); existing entries are never restructured."""
    for rule in ctrl["Rules"]:
        if rule["Property"] == prop:
            rule["InvariantScript"] = value
            return
    category = "Behavior" if BEHAVIOR_PROPS.match(prop) else "Design"
    if prop in ("Items", "Default", "Text", "Value"):
        category = "Data"
    ctrl["Rules"].append({
        "Property": prop,
        "Category": category,
        "InvariantScript": value,
        "RuleProviderType": "Unknown",
    })
    cps = ctrl.setdefault("ControlPropertyState", [])
    for entry in cps:
        if entry == prop or (isinstance(entry, dict)
                             and entry.get("InvariantPropertyName") == prop):
            return
    cps.append(prop)


def get_rule(ctrl, prop):
    for rule in ctrl.get("Rules") or []:
        if rule["Property"] == prop:
            return rule["InvariantScript"]
    return None


def walk(node):
    yield node
    for child in node.get("Children") or []:
        yield from walk(child)


def rewrite_formulas(subtree_root, rename_map):
    """Rewrite control-name references in every rule of a subtree after
    renaming (donor gallery children reference siblings, e.g. Title1.Y)."""
    if not rename_map:
        return
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(k) for k in rename_map) + r")\b")
    for node in walk(subtree_root):
        for rule in node.get("Rules") or []:
            rule["InvariantScript"] = pattern.sub(
                lambda m: rename_map[m.group(1)], rule["InvariantScript"])


def strip_meta(node):
    for n in walk(node):
        for key in META_KEYS:
            n.pop(key, None)


class Compiler:
    def __init__(self, harvest_dir):
        self.harvest_dir = harvest_dir
        with open(os.path.join(harvest_dir, "manifest.json"), encoding="utf-8") as f:
            self.manifest = json.load(f)
        self.raw_dir = os.path.join(harvest_dir, "raw")
        self.templates = {}
        tpl_dir = os.path.join(harvest_dir, "templates")
        for fname in os.listdir(tpl_dir):
            with open(os.path.join(tpl_dir, fname), encoding="utf-8") as f:
                self.templates[fname[:-5]] = json.load(f)
        self.yaml_types = dict(STATIC_YAML_TYPES)
        self.yaml_types.update(self.manifest.get("yaml_type_map") or {})
        self.yaml_controls = self.manifest.get("yaml_controls") or {}
        self.banner = self.manifest.get("yaml_banner") or ""
        self.warnings = []

    # ---------- control construction ----------

    def make_control(self, ctype, name, parent_name, spec_props,
                    screen_level=True):
        if ctype not in self.templates:
            raise SystemExit(
                f"ERROR: no '{ctype}' template in donor harvest "
                f"(available: {sorted(t for t in self.templates if t != 'screen')}). "
                f"Harvest a donor that has a seed control of this type.")
        ctrl = copy.deepcopy(self.templates[ctype])
        ctrl["Name"] = name
        ctrl["Parent"] = parent_name
        ctrl["__spec_props"] = sorted(spec_props or [])
        ctrl["__yaml_info"] = self.yaml_types.get(ctype) or {}
        if (ctrl.get("Template") or {}).get("Name") != "gallery":
            ctrl["Children"] = []
        else:
            self._prepare_gallery(ctrl, name)
        self._sanitize_template_rules(ctrl, spec_props, screen_level)
        for prop, value in (spec_props or {}).items():
            set_rule(ctrl, prop, str(value))
        return ctrl

    def _sanitize_template_rules(self, ctrl, spec_props, screen_level):
        """Some donor seeds live inside a gallery (rectangle, image, icon), so
        their template rules carry context-bound formulas (ThisItem.*,
        Select(Parent), references to donor siblings like Separator1). Drop
        such rules unless the spec overrides them — the property falls back to
        its default. ThisItem/Parent references are legit inside galleries, so
        only stale donor-name references are dropped there."""
        if (ctrl.get("Template") or {}).get("Name") == "gallery":
            return  # gallery seeds sit at screen level; items handled on rename
        spec_set = set(spec_props or {})
        # Hard rule: screen-level rectangles must not carry ZIndex (donor
        # rectangle seeds come from inside a gallery and inherit ZIndex>0,
        # which renders the bar on top of its own labels). Drop it unless the
        # spec explicitly sets one.
        if (screen_level and (ctrl.get("Template") or {}).get("Name") == "rectangle"
                and "ZIndex" not in spec_set):
            ctrl["Rules"] = [r for r in ctrl.get("Rules") or []
                             if r["Property"] != "ZIndex"]
            ctrl["ControlPropertyState"] = [
                e for e in ctrl.get("ControlPropertyState") or []
                if (e.get("InvariantPropertyName") if isinstance(e, dict) else e)
                != "ZIndex"]
        donor_names = [n for n in self.yaml_controls if n]
        donor_re = (re.compile(r"\b(" + "|".join(map(re.escape, donor_names))
                               + r")\b") if donor_names else None)
        ctx_re = re.compile(r"\bThisItem\b|\bParent\b")
        drop = []
        for rule in ctrl.get("Rules") or []:
            if rule["Property"] in spec_set:
                continue
            script = rule["InvariantScript"]
            stale = donor_re.search(script) if donor_re else None
            ctx = screen_level and ctx_re.search(script)
            if stale or ctx:
                drop.append(rule["Property"])
        if not drop:
            return
        ctrl["Rules"] = [r for r in ctrl["Rules"] if r["Property"] not in drop]
        ctrl["ControlPropertyState"] = [
            e for e in ctrl.get("ControlPropertyState") or []
            if (e.get("InvariantPropertyName") if isinstance(e, dict) else e)
            not in drop]
        self.warnings.append(
            f"{ctrl['Name']}: dropped context-bound template rules "
            f"{drop} (set them in the spec if needed)")

    def _prepare_gallery(self, gal, gal_name):
        """Gallery anatomy (measured from Studio): item controls are DIRECT
        children of the gallery (Parent = gallery name, Index = 0), alongside
        one internal galleryTemplate node. Rename everything for app-wide name
        uniqueness, then rewrite formulas that referenced the old names
        (donor items reference siblings, e.g. Subtitle1 uses Title1.Y)."""
        rename_map = {}
        for child in gal.get("Children") or []:
            if (child.get("Template") or {}).get("Name") == "galleryTemplate":
                rename_map[child["Name"]] = f"{gal_name}Template"
                child["Name"] = f"{gal_name}Template"
            else:
                new_name = f"{gal_name}_{child['Name']}"
                rename_map[child["Name"]] = new_name
                # donor items keep their harvested YAML metadata
                info = self.yaml_controls.get(child["Name"])
                if info:
                    child["__yaml_info"] = info
                    child["__spec_props"] = []
                child["Name"] = new_name
            child["Parent"] = gal_name
        rewrite_formulas(gal, rename_map)

    def build_screen(self, screen_spec):
        scr = copy.deepcopy(self.templates["screen"])
        scr["Name"] = screen_spec["name"]
        scr["Children"] = []
        scr["__spec_props"] = sorted(screen_spec.get("properties") or [])
        for prop, value in (screen_spec.get("properties") or {}).items():
            set_rule(scr, prop, str(value))
        for cspec in screen_spec.get("controls") or []:
            ctrl = self.make_control(cspec["type"], cspec["name"],
                                     scr["Name"], cspec.get("properties"))
            for child_spec in cspec.get("children") or []:
                # gallery items are direct children of the gallery
                # (Parent = gallery name, Index stays 0 — donor convention)
                item = self.make_control(child_spec["type"], child_spec["name"],
                                         ctrl["Name"],
                                         child_spec.get("properties"),
                                         screen_level=False)
                item["Index"] = 0
                ctrl["Children"].append(item)
            scr["Children"].append(ctrl)
        return scr

    # ---------- YAML emission (delta convention, like Studio) ----------

    def _yaml_prop(self, prop, script, indent):
        pad = " " * indent
        if "\n" in script:
            lines = script.split("\n")
            out = [f"{pad}{prop}: |-", f"{pad}  ={lines[0]}"]
            out += [f"{pad}  {ln}" for ln in lines[1:]]
            return "\n".join(out)
        return f"{pad}{prop}: ={script}"

    def _yaml_prop_names(self, ctrl):
        """Studio writes a delta: harvested-per-template prop names plus
        whatever the spec explicitly set, alphabetized. Only names that exist
        as JSON rules are emitted (e.g. donor 'Items.Value' has no rule)."""
        info = ctrl.get("__yaml_info") or {}
        names = set(info.get("props") or [])
        names.update(ctrl.get("__spec_props") or [])
        have = {r["Property"] for r in ctrl.get("Rules") or []}
        return sorted(n for n in names if n in have)

    def _yaml_control(self, ctrl, indent):
        pad = " " * indent
        info = ctrl.get("__yaml_info") or {}
        tname = (ctrl.get("Template") or {}).get("Name", "")
        control_str = info.get("control")
        if not control_str:
            fallback = self.yaml_types.get(tname) or {}
            control_str = fallback.get("control", f"{tname}@0.0.0")
            self.warnings.append(f"{ctrl['Name']}: no harvested YAML type for "
                                 f"'{tname}' — used fallback {control_str}")
        lines = [f"{pad}- {ctrl['Name']}:",
                 f"{pad}    Control: {control_str}"]
        if info.get("variant"):
            lines.append(f"{pad}    Variant: {info['variant']}")
        prop_names = self._yaml_prop_names(ctrl)
        if prop_names:
            lines.append(f"{pad}    Properties:")
            for prop in prop_names:
                lines.append(self._yaml_prop(prop, get_rule(ctrl, prop),
                                             indent + 6))
        # gallery item controls nest directly under the gallery in YAML;
        # the galleryTemplate node itself is not written
        item_children = []
        for child in ctrl.get("Children") or []:
            if (child.get("Template") or {}).get("Name") == "galleryTemplate":
                item_children.extend(child.get("Children") or [])
            else:
                item_children.append(child)
        if item_children:
            lines.append(f"{pad}    Children:")
            for child in item_children:
                lines.append(self._yaml_control(child, indent + 6))
        return "\n".join(lines)

    def screen_yaml(self, scr):
        lines = []
        if self.banner:
            lines.append(self.banner)
        lines += ["Screens:", f"  {scr['Name']}:"]
        prop_names = set(self.manifest.get("screen_yaml_props") or [])
        prop_names.update(scr.get("__spec_props") or [])
        have = {r["Property"] for r in scr.get("Rules") or []}
        prop_names = sorted(n for n in prop_names if n in have)
        if prop_names:
            lines.append("    Properties:")
            for prop in prop_names:
                lines.append(self._yaml_prop(prop, get_rule(scr, prop), 6))
        children = scr.get("Children") or []
        if children:
            lines.append("    Children:")
            for ctrl in children:
                lines.append(self._yaml_control(ctrl, 6))
        return "\n".join(lines) + "\n"

    def editor_state_yaml(self, donor_text, screen_names):
        if "ScreensOrder" not in donor_text:
            self.warnings.append("_EditorState.pa.yaml: donor has no ScreensOrder "
                                 "key — copied verbatim; screen list may be stale")
            return donor_text
        lines = []
        if self.banner:
            lines.append(self.banner)
        lines.append("EditorState:")
        lines.append("  ScreensOrder:")
        lines += [f"    - {n}" for n in screen_names]
        return "\n".join(lines) + "\n"

    def replace_onstart_yaml(self, app_yaml_text, onstart):
        result = self._replace_onstart_yaml(app_yaml_text, onstart)
        return result if result.endswith("\n") else result + "\n"

    def _replace_onstart_yaml(self, app_yaml_text, onstart):
        block_lines = onstart.split("\n")
        m = re.search(r"^(\s*)OnStart:.*$", app_yaml_text, re.MULTILINE)
        if m:
            indent = m.group(1)
            new_block = [f"{indent}OnStart: |-", f"{indent}  ={block_lines[0]}"]
            new_block += [f"{indent}  {ln}" for ln in block_lines[1:]]
            start = m.start()
            rest = app_yaml_text[m.end():]
            consumed = 0
            for line in rest.splitlines(keepends=True):
                if line.strip() and not line.startswith(indent + " "):
                    break
                consumed += len(line)
            return app_yaml_text[:start] + "\n".join(new_block) + rest[consumed:]
        m = re.search(r"^(\s*)Properties:\s*$", app_yaml_text, re.MULTILINE)
        if m:
            indent = m.group(1) + "  "
            new_block = [f"{indent}OnStart: |-", f"{indent}  ={block_lines[0]}"]
            new_block += [f"{indent}  {ln}" for ln in block_lines[1:]]
            return (app_yaml_text[:m.end()] + "\n" + "\n".join(new_block)
                    + app_yaml_text[m.end():])
        self.warnings.append("App.pa.yaml: could not locate OnStart/Properties — "
                             "OnStart set in JSON only; inspect App.pa.yaml manually")
        return app_yaml_text

    # ---------- top-level build ----------

    def compile(self, spec, out_dir):
        extracted = os.path.join(out_dir, "extracted")
        shutil.rmtree(out_dir, ignore_errors=True)
        shutil.copytree(self.raw_dir, extracted)

        # drop donor screens (Controls files + YAML mirrors)
        for fname in self.manifest["screen_files"]:
            path = os.path.join(extracted, "Controls", fname)
            if os.path.exists(path):
                os.remove(path)
        for sname in self.manifest["screen_names"]:
            path = os.path.join(extracted, "Src", f"{sname}.pa.yaml")
            if os.path.exists(path):
                os.remove(path)

        # App node
        app_path = os.path.join(extracted, "Controls",
                                self.manifest["app_controls_file"])
        with open(app_path, encoding="utf-8") as f:
            app_data = json.load(f)
        app_top = app_data["TopParent"]
        onstart = spec.get("onstart")
        if onstart:
            set_rule(app_top, "OnStart", onstart)

        # screens
        screens = [self.build_screen(s) for s in spec.get("screens") or []]
        if not screens:
            raise SystemExit("ERROR: spec has no screens")

        # name uniqueness across the whole app
        names = [n["Name"] for n in walk(app_top)]
        for scr in screens:
            names += [n["Name"] for n in walk(scr)]
        dupes = {n for n in names if names.count(n) > 1}
        if dupes:
            raise SystemExit(f"ERROR: duplicate control names in spec: {sorted(dupes)}")

        # identity pass — one consistent sweep, conventions measured from Studio:
        #   uid: sequential from max(App-file uids, 3)+1
        #   Index: per (parent, Template.Name, VariantName) sequence
        #   PublishOrderIndex: screens 0; non-screen controls one global DFS sequence
        app_uids = [int(n["ControlUniqueId"]) for n in walk(app_top)
                    if str(n.get("ControlUniqueId", "")).isdigit()]
        uid = max(app_uids + [3]) + 1
        publish_order = 0
        for i, scr in enumerate(screens):
            scr["Index"] = i
            scr["PublishOrderIndex"] = 0
            for node in walk(scr):
                node["ControlUniqueId"] = str(uid)
                uid += 1
                if node is not scr:
                    node["PublishOrderIndex"] = publish_order
                    publish_order += 1
            # Index: per-(type, variant) sequence for DIRECT screen children
            # only; gallery items all keep Index=0 (measured donor convention)
            counters = defaultdict(int)
            for child in scr.get("Children") or []:
                key = ((child.get("Template") or {}).get("Name", ""),
                       child.get("VariantName", ""))
                child["Index"] = counters[key]
                counters[key] += 1

        # Src YAMLs BEFORE stripping build metadata
        src_dir = os.path.join(extracted, "Src")
        app_yaml_path = os.path.join(src_dir, "App.pa.yaml")
        if onstart and os.path.exists(app_yaml_path):
            with open(app_yaml_path, encoding="utf-8") as f:
                text = f.read()
            with open(app_yaml_path, "w", encoding="utf-8") as f:
                f.write(self.replace_onstart_yaml(text, onstart))
        for scr in screens:
            with open(os.path.join(src_dir, f"{scr['Name']}.pa.yaml"), "w",
                      encoding="utf-8") as f:
                f.write(self.screen_yaml(scr))
        es_path = os.path.join(src_dir, "_EditorState.pa.yaml")
        if os.path.exists(es_path):
            with open(es_path, encoding="utf-8") as f:
                text = f.read()
            with open(es_path, "w", encoding="utf-8") as f:
                f.write(self.editor_state_yaml(
                    text, [s["Name"] for s in screens]))

        # write Controls files (screen file name = screen uid)
        with open(app_path, "w", encoding="utf-8") as f:
            json.dump(app_data, f, indent=1)
        for scr in screens:
            strip_meta(scr)
            fname = f"{scr['ControlUniqueId']}.json"
            with open(os.path.join(extracted, "Controls", fname), "w",
                      encoding="utf-8") as f:
                json.dump({"TopParent": scr}, f, indent=1)

        # Properties.json: recompute ControlCount using the donor's convention
        self._update_properties(extracted, app_top, screens, spec.get("name"))

        return extracted

    def _update_properties(self, extracted, app_top, screens, app_name):
        props_path = os.path.join(extracted, "Properties.json")
        with open(props_path, encoding="utf-8") as f:
            props = json.load(f)
        # measured donor convention: ControlCount lists only some template
        # names (donor: screen + label) and does NOT count gallery
        # descendants. Reproduce exactly: count only the donor's declared
        # keys, skipping anything inside a gallery.
        declared_keys = set(self.manifest.get("control_count_keys") or [])
        counts = {}

        def count(node, in_gallery):
            tname = (node.get("Template") or {}).get("Name", "")
            if tname in declared_keys and not in_gallery:
                counts[tname] = counts.get(tname, 0) + 1
            for child in node.get("Children") or []:
                count(child, in_gallery or tname == "gallery")

        for root in [app_top] + screens:
            count(root, False)
        if "ControlCount" in props:
            props["ControlCount"] = counts
        with open(props_path, "w", encoding="utf-8") as f:
            json.dump(props, f, indent=1)


# ---------- packing & delivery ----------

def pack_msapp(extracted, msapp_path):
    with zipfile.ZipFile(msapp_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(extracted):
            for fname in sorted(files):
                full = os.path.join(root, fname)
                arc = os.path.relpath(full, extracted).replace(os.sep, "/")
                zf.write(full, arc)
    with zipfile.ZipFile(msapp_path) as zf:
        bad = zf.testzip()
        if bad:
            raise SystemExit(f"ERROR: corrupt zip member {bad}")


def make_txt_bundle(extracted, out_dir, app_name):
    txt_dir = os.path.join(out_dir, "txt")
    shutil.rmtree(txt_dir, ignore_errors=True)
    os.makedirs(txt_dir)
    file_map = {}
    for root, _dirs, files in os.walk(extracted):
        for fname in sorted(files):
            full = os.path.join(root, fname)
            rel = os.path.relpath(full, extracted).replace(os.sep, "/")
            flat = os.path.splitext(rel.replace("/", "__"))[0] + ".txt"
            if flat in file_map:  # extension collision after splitext
                flat = rel.replace("/", "__") + ".txt"
            file_map[flat] = rel
            shutil.copy2(full, os.path.join(txt_dir, flat))

    map_lines = ",\n".join(f'    "{k}": "{v}"' for k, v in sorted(file_map.items()))
    script = f'''# Rebuild {app_name}.msapp from the .txt attachments — run in Jupyter.
# 1) Save ALL .txt attachments into ONE folder.
# 2) Change FOLDER below to that folder's path.
# 3) Run this cell. It creates {app_name}.msapp in the same folder.
# 4) Power Apps -> Import app / Open -> From file -> select the .msapp.
# 5) After opening: App -> ... -> Run OnStart, then F5 to test.
import os, zipfile

FOLDER = r"C:\\Users\\you\\Downloads\\{app_name}-files"  # <-- CHANGE THIS

FILE_MAP = {{
{map_lines}
}}

missing = [t for t in FILE_MAP if not os.path.exists(os.path.join(FOLDER, t))]
if missing:
    raise SystemExit("Missing files: " + ", ".join(missing))

out = os.path.join(FOLDER, "{app_name}.msapp")
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
    for txt_name, arc_path in FILE_MAP.items():
        with open(os.path.join(FOLDER, txt_name), "rb") as f:
            zf.writestr(arc_path, f.read())
print("Done:", out, os.path.getsize(out), "bytes")
'''
    script_path = os.path.join(out_dir, "rebuild_notebook.py")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script)
    return txt_dir, script_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec")
    ap.add_argument("--harvest", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--repack-donor", action="store_true",
                    help="probe 0: pack the raw donor unchanged")
    ap.add_argument("--skip-verify", action="store_true")
    args = ap.parse_args()

    comp = Compiler(args.harvest)

    if args.repack_donor:
        os.makedirs(args.out, exist_ok=True)
        extracted = os.path.join(args.out, "extracted")
        shutil.rmtree(extracted, ignore_errors=True)
        shutil.copytree(comp.raw_dir, extracted)
        name = "Probe0-DonorRepack"
    else:
        if not args.spec:
            ap.error("--spec is required unless --repack-donor")
        with open(args.spec, encoding="utf-8") as f:
            spec = json.load(f)
        name = spec.get("name", "App")
        extracted = comp.compile(spec, args.out)

    for w in comp.warnings:
        print(f"WARN  {w}")

    if not args.skip_verify:
        errors, warnings = verify(extracted)
        for w in warnings:
            print(f"WARN  {w}")
        for e in errors:
            print(f"ERROR {e}")
        if errors:
            sys.exit(f"\n{len(errors)} verifier error(s) — build NOT packed. Fix first.")

    msapp_path = os.path.join(args.out, f"{name}.msapp")
    pack_msapp(extracted, msapp_path)
    txt_dir, script_path = make_txt_bundle(extracted, args.out, name)
    n_txt = len(os.listdir(txt_dir))
    print(f"\nBuilt {msapp_path}")
    print(f"Delivery bundle: {n_txt} .txt files in {txt_dir}")
    print(f"Rebuild script:  {script_path}")


if __name__ == "__main__":
    main()
