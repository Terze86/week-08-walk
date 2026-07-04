#!/usr/bin/env python3
"""ui_patterns — reusable "professional app" spec generator.

Proven pattern from the Quality Log build (11 screens, ~665 controls, imported
on the tenant): every screen gets a blue header bar with a role selector, a
white left sidebar with grouped nav buttons (live CountRows counts +
active-screen highlight), a table-style gallery (grey uppercase header row,
aligned columns, coloured status pills, role-gated Approve button), and a modal
entry form (full-screen scrim + centred white card; 3 columns when a form has
more than 10 fields so it fits within 768px).

Usage (see examples/example_styled_app.py):

    from ui_patterns import StyledApp
    app = StyledApp("MyApp", title="My App")
    app.add_log("Cases", coll="colCases", screen="scrCases", group="LOGS",
                desc="All cases.",
                fields=[("Case", "Case No.", "text", None),
                        ("SO", "SO", "dd", '["RA","CS"]'),
                        ("Remarks", "Remarks", "multi", None)],
                table=[("Case", 1.4), ("SO", 0.8), ("Remarks", 3.0)])
    spec = app.build(onstart_data='ClearCollect(colCases, {SN:1, Case:"X", SO:"RA", Remarks:"", Status:"Pending"})')
    json.dump(spec, open("appspec.json", "w"), indent=2)

Then compile with msapp_compiler.py as usual. Field kinds: "text" (single-line
input), "multi" (multi-line input, spans the full card width), "dd" (dropdown;
items = raw Power Fx table string). Every record automatically gets SN and
Status ("Pending" on save; Approve patches it to "Approved").
"""

# palette (matches the approved prototype)
BLUE = "RGBA(56, 96, 178, 1)"
BLUE_D = "RGBA(40, 64, 122, 1)"
NAV_ACTIVE = "RGBA(231, 237, 251, 1)"
WHITE = "RGBA(255, 255, 255, 1)"
INK = "RGBA(31, 36, 48, 1)"
MUTED = "RGBA(107, 114, 128, 1)"
HEAD_TXT = "RGBA(84, 96, 122, 1)"
LINE = "RGBA(227, 231, 238, 1)"
BG = "RGBA(245, 246, 250, 1)"
HEAD_BG = "RGBA(240, 243, 249, 1)"
OK_BG = "RGBA(228, 246, 236, 1)"
OK_TX = "RGBA(27, 138, 90, 1)"
PEND_BG = "RGBA(254, 243, 226, 1)"
PEND_TX = "RGBA(161, 92, 0, 1)"
SCRIM = "RGBA(20, 26, 40, 0.45)"

# geometry (1366x768 tablet layout)
HEAD_H = 56
SIDE_W = 250
CONTENT_X = SIDE_W + 24
CONTENT_W = 1366 - CONTENT_X - 24
STATUS_W, ACT_W = 96, 96
FIELD_AREA = CONTENT_W - STATUS_W - ACT_W


def lbl(name, text, x, y, w, size=13, weight="Normal", color=INK, h=24,
        align="Left", fill=None):
    p = {"Text": text, "X": str(x), "Y": str(y), "Width": str(w), "Height": str(h),
         "Size": str(size), "FontWeight": "FontWeight.%s" % weight, "Color": color,
         "Align": "Align.%s" % align, "VerticalAlign": "VerticalAlign.Middle"}
    if fill:
        p["Fill"] = fill
    return {"type": "label", "name": name, "properties": p}


def rect(name, x, y, w, h, fill, visible=None):
    p = {"X": str(x), "Y": str(y), "Width": str(w), "Height": str(h), "Fill": fill}
    if visible:
        p["Visible"] = visible
    return {"type": "rectangle", "name": name, "properties": p}


def btn(name, text, x, y, w, h, onselect, fill=BLUE, color=WHITE, visible=None,
        weight="Semibold", size=13):
    p = {"Text": text, "OnSelect": onselect, "X": str(x), "Y": str(y),
         "Width": str(w), "Height": str(h), "Fill": fill, "Color": color,
         "FontWeight": "FontWeight.%s" % weight, "Size": str(size)}
    if visible:
        p["Visible"] = visible
    return {"type": "button", "name": name, "properties": p}


class StyledApp:
    def __init__(self, name, title=None, roles=None, approver_role="Management",
                 default_role="Quality"):
        self.name = name
        self.title = title or name
        self.roles = roles or ["Quality", "SO", "Management"]
        self.approver_role = approver_role
        self.default_role = default_role
        self.logs = {}   # display name -> cfg

    def add_log(self, display_name, coll, screen, group, desc, fields, table,
                restrict=False, banner=None):
        """restrict: False = all roles; True = hide from SO; or a raw Power Fx
        visibility expression string. banner: optional banner text (shown amber
        above the table, e.g. explaining a consolidation)."""
        self.logs[display_name] = {
            "coll": coll, "screen": screen, "var": "varShow" + screen[3:],
            "group": group, "desc": desc, "fields": fields, "table": table,
            "restrict": restrict, "banner": banner,
        }

    # ---------- shared chrome ----------

    def _vis(self, cfg):
        r = cfg["restrict"]
        if r is True:
            return 'varRole <> "SO"'
        if isinstance(r, str) and r:
            return r
        return "true"

    def _sidebar(self, cur):
        out = [rect("sbBg_" + cur, 0, HEAD_H, SIDE_W, 768 - HEAD_H, WHITE),
               rect("sbLine_" + cur, SIDE_W - 1, HEAD_H, 1, 768 - HEAD_H, LINE)]
        y = HEAD_H + 18
        last_group = None
        for name, cfg in self.logs.items():
            if cfg["group"] != last_group:
                out.append(lbl("grp_%s_%s" % (cfg["screen"], cur),
                               '"%s"' % cfg["group"], 18, y, SIDE_W - 30,
                               11, "Bold", MUTED, 18))
                y += 24
                last_group = cfg["group"]
            active = cfg["screen"] == cur
            out.append(btn(
                "nav_%s_%s" % (cfg["screen"], cur),
                '"%s   (" & CountRows(%s) & ")"' % (name, cfg["coll"]),
                0, y, SIDE_W, 40,
                "Navigate(%s, ScreenTransition.None)" % cfg["screen"],
                fill=NAV_ACTIVE if active else WHITE,
                color=BLUE_D if active else INK,
                weight="Bold" if active else "Normal", size=13,
                visible=self._vis(cfg)))
            y += 44
        return out

    def _header(self, cur):
        role_items = "[" + ",".join('"%s"' % r for r in self.roles) + "]"
        return [
            rect("hdrBar_" + cur, 0, 0, "App.Width", HEAD_H, BLUE),
            lbl("hdrTitle_" + cur, '"%s"' % self.title, 24, 12, 520, 19, "Bold", WHITE, 32),
            lbl("hdrRoleLbl_" + cur, '"Signed in as " & varEmail & "  |  Role"',
                900, 18, 300, 12, "Normal", WHITE, 22, "Right"),
            {"type": "dropdown", "name": "hdrRole_" + cur,
             "properties": {"Items": role_items, "Default": "varRole",
                            "OnChange": "Set(varRole, Self.Selected.Value)",
                            "X": "1216", "Y": "12", "Width": "126", "Height": "32"}},
        ]

    # ---------- per-log screen ----------

    def _table_columns(self, cfg):
        total = sum(w for _, w in cfg["table"])
        field_lbl = {f[0]: f[1] for f in cfg["fields"]}
        cols, off = [], 8
        for safe, wt in cfg["table"]:
            w = int(FIELD_AREA * wt / total) - 8
            cols.append((safe, field_lbl[safe], off, w))
            off += int(FIELD_AREA * wt / total)
        return cols

    def _form_inputs(self, cfg):
        out = []
        for f in cfg["fields"]:
            safe, _, kind, _ = f
            pre = "dd" if kind == "dd" else "in"
            out.append(("%s_%s_%s" % (cfg["screen"], pre, safe), f))
        return out

    def _log_screen(self, name, cfg):
        coll, var, scr = cfg["coll"], cfg["var"], cfg["screen"]
        controls = self._header(scr) + self._sidebar(scr)

        controls.append(lbl(scr + "Title", '"%s"' % name, CONTENT_X, HEAD_H + 18,
                            600, 20, "Bold", INK, 30))
        controls.append(lbl(scr + "Desc", '"%s"' % cfg["desc"], CONTENT_X,
                            HEAD_H + 52, CONTENT_W - 180, 13, "Normal", MUTED, 22))
        resets = ";".join("Reset(%s)" % c for c, _ in self._form_inputs(cfg))
        controls.append(btn(scr + "New", '"+ New Entry"', 1216, HEAD_H + 20, 126, 38,
                            (resets + ";" if resets else "") + "Set(%s, true)" % var))

        table_y = HEAD_H + 92
        if cfg.get("banner"):
            controls.append(lbl(scr + "Banner", '"%s"' % cfg["banner"], CONTENT_X,
                                HEAD_H + 84, CONTENT_W, 12, "Normal", PEND_TX, 30,
                                "Left", PEND_BG))
            table_y = HEAD_H + 124

        cols = self._table_columns(cfg)
        controls.append(rect(scr + "Head", CONTENT_X, table_y, CONTENT_W, 32, HEAD_BG))
        for safe, label, off, w in cols:
            controls.append(lbl("%s_h_%s" % (scr, safe), '"%s"' % label.upper(),
                                CONTENT_X + off, table_y, w, 11, "Semibold",
                                HEAD_TXT, 32))
        controls.append(lbl(scr + "hStatus", '"STATUS"', CONTENT_X + FIELD_AREA + 8,
                            table_y, STATUS_W, 11, "Semibold", HEAD_TXT, 32))

        gal_children = []
        for safe, label, off, w in cols:
            gal_children.append(lbl("%s_c_%s" % (scr, safe), "ThisItem.%s" % safe,
                                    off, 6, w, 12.5, "Normal", INK, 36))
        gal_children.append(lbl(scr + "_cStatus", "ThisItem.Status",
                                FIELD_AREA + 8, 8, STATUS_W - 8, 11, "Semibold",
                                'If(ThisItem.Status = "Approved", %s, %s)' % (OK_TX, PEND_TX),
                                22, "Center",
                                'If(ThisItem.Status = "Approved", %s, %s)' % (OK_BG, PEND_BG)))
        gal_children.append(btn(
            scr + "_cApprove", '"Approve"', FIELD_AREA + STATUS_W + 8, 6, ACT_W - 12, 30,
            'Patch(%s, ThisItem, {Status: "Approved"}); Notify("Approved", NotificationType.Success)' % coll,
            fill=BLUE, color=WHITE, size=11,
            visible='varRole = "%s" And ThisItem.Status <> "Approved"' % self.approver_role))
        controls.append({
            "type": "gallery_blank", "name": scr + "Gal",
            "properties": {"Items": coll, "TemplateSize": "48", "TemplatePadding": "0",
                           "X": str(CONTENT_X), "Y": str(table_y + 32),
                           "Width": str(CONTENT_W),
                           "Height": str(768 - table_y - 32 - 16), "Fill": WHITE},
            "children": gal_children,
        })

        controls += self._modal(name, cfg)
        return {"name": scr, "properties": {"Fill": BG}, "controls": controls}

    def _modal(self, name, cfg):
        scr, var, coll = cfg["screen"], cfg["var"], cfg["coll"]
        inputs = self._form_inputs(cfg)
        ncols = 3 if len(cfg["fields"]) > 10 else 2
        if ncols == 3:
            CARD_X, CARD_W, CARD_Y, colW = 300, 766, 60, 224
            col_x = [CARD_X + 24, CARD_X + 260, CARD_X + 496]
            fullW = 718
        else:
            CARD_X, CARD_W, CARD_Y, colW = 388, 590, 96, 250
            col_x = [CARD_X + 24, CARD_X + 304]
            fullW = 530
        colA = col_x[0]
        controls = [rect(scr + "Scrim", 0, 0, "App.Width", "App.Height", SCRIM,
                         visible=var)]
        body = []
        ys = [96] * ncols

        def ay(rel):
            return CARD_Y + rel
        for cname, (safe, label, kind, items) in inputs:
            if kind == "multi":
                y = max(ys)
                body.append(lbl("%s_l_%s" % (scr, safe), '"%s"' % label, colA,
                                ay(y), fullW, 11, "Semibold", HEAD_TXT, 18, fill=WHITE))
                body.append({"type": "text", "name": cname, "properties": {
                    "X": str(colA), "Y": str(ay(y + 20)), "Width": str(fullW),
                    "Height": "60", "Mode": "TextMode.MultiLine", "Visible": var}})
                ys = [y + 90] * ncols
            else:
                i = ys.index(min(ys))
                x, y = col_x[i], ys[i]
                ys[i] += 60
                body.append(lbl("%s_l_%s" % (scr, safe), '"%s"' % label, x, ay(y),
                                colW, 11, "Semibold", HEAD_TXT, 18, fill=WHITE))
                props = {"X": str(x), "Y": str(ay(y + 20)), "Width": str(colW),
                         "Height": "32", "Visible": var}
                if kind == "dd":
                    props["Items"] = items
                    body.append({"type": "dropdown", "name": cname, "properties": props})
                else:
                    body.append({"type": "text", "name": cname, "properties": props})
        card_h = max(ys) + 8 + 56 - 96 + 24
        controls.append(rect(scr + "Card", CARD_X, CARD_Y, CARD_W, card_h, WHITE,
                             visible=var))
        controls.append(lbl(scr + "MTitle", '"New entry — %s"' % name, colA,
                            CARD_Y + 16, fullW, 16, "Bold", BLUE_D, 26, fill=WHITE))
        controls += body
        pairs = ["SN: CountRows(%s) + 1" % coll]
        for cname, (safe, _, kind, _) in inputs:
            val = "%s.Selected.Value" % cname if kind == "dd" else "%s.Text" % cname
            pairs.append("%s: %s" % (safe, val))
        pairs.append('Status: "Pending"')
        save = ('Collect(%s, {%s}); Set(%s, false); '
                'Notify("Entry added (pending approval)", NotificationType.Success)'
                % (coll, ", ".join(pairs), var))
        save_y = CARD_Y + card_h - 52
        controls.append(btn(scr + "Save", '"Save"', colA, save_y, 150, 38, save,
                            visible=var))
        controls.append(btn(scr + "Cancel", '"Cancel"', colA + 162, save_y, 120, 38,
                            "Set(%s, false)" % var, fill=WHITE, color=BLUE_D,
                            visible=var))
        return controls

    # ---------- assembly ----------

    def build(self, onstart_data=""):
        """onstart_data: extra OnStart Power Fx (your ClearCollect seeds). The
        role bootstrap + varShow inits are added automatically."""
        if not self.logs:
            raise ValueError("add_log() at least once before build()")
        parts = [
            "Set(varEmail, User().Email)",
            'ClearCollect(colUsers, {Email: varEmail, Role: "%s"})' % self.default_role,
            'Set(varRole, Coalesce(LookUp(colUsers, Email = varEmail).Role, "%s"))'
            % self.default_role,
        ]
        parts += ["Set(%s, false)" % c["var"] for c in self.logs.values()]
        onstart = ";\n".join(parts)
        if onstart_data.strip():
            onstart += ";\n" + onstart_data.strip().rstrip(";")
        screens = [self._log_screen(n, c) for n, c in self.logs.items()]
        return {"name": self.name, "onstart": onstart, "screens": screens}
