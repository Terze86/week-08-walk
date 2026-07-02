#!/usr/bin/env python3
"""Compile an app spec into a complete, import-ready .msapp.

Strategy: never graft into a Studio export. Start from the harvested donor's
registries (Header, Properties, References/*, Resources/*), regenerate every
screen/control/YAML/editor-state file from one in-memory model, recompute all
cross-file invariants, verify, pack, and emit the .txt delivery bundle.

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


def walk(node):
    yield node
    for child in node.get("Children") or []:
        yield from walk(child)


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
        self.warnings = []

    # ---------- control construction ----------

    def make_control(self, ctype, name, parent_name, spec_props):
        if ctype not in self.templates:
            raise SystemExit(
                f"ERROR: no '{ctype}' template in donor harvest "
                f"(available: {sorted(t for t in self.templates if t != 'screen')}). "
                f"Harvest a donor that has a seed control of this type.")
        ctrl = copy.deepcopy(self.templates[ctype])
        ctrl["Name"] = name
        ctrl["Parent"] = parent_name
        if (ctrl.get("Template") or {}).get("Name") != "gallery":
            ctrl["Children"] = []
        else:
            self._prepare_gallery(ctrl, name)
        for prop, value in (spec_props or {}).items():
            set_rule(ctrl, prop, str(value))
        return ctrl

    def _prepare_gallery(self, gal, gal_name):
        """Rename the gallery's internal template child (and any donor-seeded
        item controls) so names stay unique when the type is used repeatedly."""
        for child in gal.get("Children") or []:
            if (child.get("Template") or {}).get("Name") == "galleryTemplate":
                child["Name"] = f"{gal_name}Template"
                child["Parent"] = gal_name
                for item in child.get("Children") or []:
                    item["Name"] = f"{gal_name}_{item['Name']}"
                    item["Parent"] = child["Name"]

    def gallery_item_parent(self, gal):
        for child in gal.get("Children") or []:
            if (child.get("Template") or {}).get("Name") == "galleryTemplate":
                return child
        raise SystemExit(f"ERROR: gallery '{gal['Name']}' template has no "
                         f"galleryTemplate child — re-harvest the donor.")

    def build_screen(self, screen_spec):
        scr = copy.deepcopy(self.templates["screen"])
        scr["Name"] = screen_spec["name"]
        scr["Children"] = []
        for prop, value in (screen_spec.get("properties") or {}).items():
            set_rule(scr, prop, str(value))
        for cspec in screen_spec.get("controls") or []:
            ctrl = self.make_control(cspec["type"], cspec["name"],
                                     scr["Name"], cspec.get("properties"))
            for child_spec in cspec.get("children") or []:
                tmpl_child = self.gallery_item_parent(ctrl)
                item = self.make_control(child_spec["type"], child_spec["name"],
                                         tmpl_child["Name"],
                                         child_spec.get("properties"))
                tmpl_child["Children"].append(item)
            scr["Children"].append(ctrl)
        return scr

    # ---------- YAML emission ----------

    def _yaml_prop(self, prop, script, indent):
        pad = " " * indent
        if "\n" in script:
            lines = script.split("\n")
            out = [f"{pad}{prop}: |-", f"{pad}  ={lines[0]}"]
            out += [f"{pad}  {ln}" for ln in lines[1:]]
            return "\n".join(out)
        return f"{pad}{prop}: ={script}"

    def _yaml_control(self, ctrl, indent):
        pad = " " * indent
        tname = (ctrl.get("Template") or {}).get("Name", "")
        ytype = self.yaml_types.get(tname) or self.yaml_types.get("label")
        # gallery vs gallery_blank share Template.Name 'gallery'
        if tname == "gallery" and "gallery" in self.yaml_types:
            ytype = self.yaml_types["gallery"]
        lines = [f"{pad}- {ctrl['Name']}:",
                 f"{pad}    Control: {ytype['control']}"]
        if ytype.get("variant"):
            lines.append(f"{pad}    Variant: {ytype['variant']}")
        lines.append(f"{pad}    Properties:")
        for rule in ctrl.get("Rules") or []:
            lines.append(self._yaml_prop(rule["Property"],
                                         rule["InvariantScript"], indent + 6))
        # gallery item controls nest directly under the gallery in YAML;
        # the galleryTemplate node itself is not written
        item_children = []
        for child in ctrl.get("Children") or []:
            if (child.get("Template") or {}).get("Name") == "galleryTemplate":
                item_children = child.get("Children") or []
            else:
                item_children.append(child)
        if item_children:
            lines.append(f"{pad}    Children:")
            for child in item_children:
                lines.append(self._yaml_control(child, indent + 6))
        return "\n".join(lines)

    def screen_yaml(self, scr):
        lines = ["Screens:", f"  {scr['Name']}:"]
        rules = scr.get("Rules") or []
        if rules:
            lines.append("    Properties:")
            for rule in rules:
                lines.append(self._yaml_prop(rule["Property"],
                                             rule["InvariantScript"], 6))
        children = scr.get("Children") or []
        if children:
            lines.append("    Children:")
            for ctrl in children:
                lines.append(self._yaml_control(ctrl, 6))
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
            # consume old block: following lines indented deeper than OnStart
            start = m.start()
            end = m.end()
            rest = app_yaml_text[end:]
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

    def rebuild_editor_state(self, text, screen_names):
        if "ScreenOrder" in text:
            m = re.search(r"^(\s*)ScreenOrder:\s*$", text, re.MULTILINE)
            if m:
                indent = m.group(1)
                item_indent = indent + "  "
                rest = text[m.end():]
                consumed = 0
                for line in rest.splitlines(keepends=True):
                    if line.strip() and not re.match(rf"^{indent}\s+-", line):
                        break
                    consumed += len(line)
                items = "\n" + "\n".join(f"{item_indent}- {n}" for n in screen_names)
                return text[:m.end()] + items + "\n" + rest[consumed:]
        # per-screen top-level blocks: replicate the first donor screen block
        donor_screens = self.manifest.get("screen_names") or []
        for donor_name in donor_screens:
            m = re.search(rf"^{re.escape(donor_name)}:\s*$", text, re.MULTILINE)
            if m:
                block_re = re.compile(
                    r"^(\w+):\s*\n((?:[ \t]+\S.*\n?|\s*\n)*)", re.MULTILINE)
                blocks = {b.group(1): b.group(2) for b in block_re.finditer(text)}
                tmpl_body = blocks.get(donor_name, "")
                keep = [f"{k}:\n{v}" for k, v in blocks.items()
                        if k not in donor_screens]
                new = [f"{n}:\n{tmpl_body}" for n in screen_names]
                return "".join(keep + new)
        self.warnings.append("_EditorState.pa.yaml: unrecognized shape — copied "
                             "verbatim from donor; screen list may be stale "
                             "(probe ladder will catch it)")
        return text

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

        # identity pass: UIDs, Index, PublishOrderIndex — one consistent sweep
        app_uids = [int(n["ControlUniqueId"]) for n in walk(app_top)
                    if str(n.get("ControlUniqueId", "")).isdigit()]
        uid = max(app_uids + [3]) + 1
        publish_order = 0
        for node in walk(app_top):
            node["PublishOrderIndex"] = publish_order
            publish_order += 1
        for i, scr in enumerate(screens):
            scr["Index"] = i
            for node in walk(scr):
                node["ControlUniqueId"] = str(uid)
                uid += 1
                node["PublishOrderIndex"] = publish_order
                publish_order += 1
            for parent in walk(scr):
                for j, child in enumerate(parent.get("Children") or []):
                    child["Index"] = j

        # write Controls files (screen file name = screen uid)
        with open(app_path, "w", encoding="utf-8") as f:
            json.dump(app_data, f, indent=1)
        for scr in screens:
            fname = f"{scr['ControlUniqueId']}.json"
            with open(os.path.join(extracted, "Controls", fname), "w",
                      encoding="utf-8") as f:
                json.dump({"TopParent": scr}, f, indent=1)

        # Properties.json: recompute ControlCount using the donor's convention
        self._update_properties(extracted, app_top, screens, spec.get("name"))

        # Src YAMLs
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
                f.write(self.rebuild_editor_state(
                    text, [s["Name"] for s in screens]))

        return extracted

    def _update_properties(self, extracted, app_top, screens, app_name):
        props_path = os.path.join(extracted, "Properties.json")
        with open(props_path, encoding="utf-8") as f:
            props = json.load(f)
        # donor convention: template names present in the donor tree but absent
        # from its declared ControlCount are excluded from counting
        donor_names = set()
        for fname in os.listdir(os.path.join(self.raw_dir, "Controls")):
            if not fname.endswith(".json"):
                continue
            with open(os.path.join(self.raw_dir, "Controls", fname),
                      encoding="utf-8") as f:
                data = json.load(f)
            for node in walk(data.get("TopParent", {})):
                donor_names.add((node.get("Template") or {}).get("Name", ""))
        declared_keys = set(self.manifest.get("control_count_keys") or [])
        excluded = donor_names - declared_keys if declared_keys else set()

        counts = {}
        for node in walk(app_top):
            tname = (node.get("Template") or {}).get("Name", "")
            if tname and tname not in excluded:
                counts[tname] = counts.get(tname, 0) + 1
        for scr in screens:
            for node in walk(scr):
                tname = (node.get("Template") or {}).get("Name", "")
                if tname and tname not in excluded:
                    counts[tname] = counts.get(tname, 0) + 1
        if "ControlCount" in props:
            props["ControlCount"] = counts
        if app_name and "Name" in props:
            props["Name"] = app_name
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
