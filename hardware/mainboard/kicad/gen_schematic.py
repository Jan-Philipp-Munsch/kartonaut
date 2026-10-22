"""Write the KiCad project and the hierarchical schematic of mainboard rev B from circuit.py.

Every pin gets a short wire stub and a net label (local if the net stays on its sheet, global if it
crosses sheets), so the schematic reads as a set of blocks per sheet. Symbols are copied from the
KiCad 10 standard library and from lib/ into each sheet's lib_symbols, as eeschema does itself.

Run:  python gen_schematic.py        (no KiCad Python needed; KiCad 10 must be installed for the libs)
"""
import json
import math
import os
import uuid
from pathlib import Path

import circuit
from sexpr import Q, dumps, find, findall, parse, prop

HERE = Path(__file__).resolve().parent
KICAD = Path(os.environ.get("KICAD10_DIR", Path.home() / "AppData/Local/Programs/KiCad/10.0"))
STD_SYM = KICAD / "share/kicad/symbols"
PROJECT = "mainboard"
VERSION = "20250114"
G = 1.27                     # schematic grid
NS = uuid.UUID("6d1c3c1e-6f0a-4c39-9a1e-2b6e4a7d9e01")   # stable UUIDs: same input, same file


def uid(*parts):
    return Q(str(uuid.uuid5(NS, "/".join(map(str, parts)))))


def snap(x):
    return round(x / G) * G


# ---------------------------------------------------------------- symbol libraries
_libs = {}


def _lib(name):
    if name not in _libs:
        path = HERE / "lib" / f"{name}.kicad_sym" if name in ("lcsc", "mainboard") else STD_SYM / f"{name}.kicad_sym"
        _libs[name] = parse(path.read_text(encoding="utf-8"))
    return _libs[name]


def _modernize(node):
    """Old-format symbols (easyeda2kicad writes 2021 syntax): drop (id n), bare hide -> (hide yes)."""
    if not isinstance(node, list):
        return node
    out = []
    for x in node:
        if isinstance(x, list) and x and x[0] == "id":
            continue
        if x == "hide" and node and node[0] in ("effects", "pin_names", "pin_numbers"):
            out.append(["hide", "yes"])
            continue
        out.append(_modernize(x))
    return out


def lib_symbol(lib_id):
    """Flattened copy of a library symbol named 'Lib:Name', as stored in a schematic."""
    libname, name = lib_id.split(":")
    syms = {s[1]: s for s in findall(_lib(libname), "symbol")}
    sym = syms[name]
    ext = find(sym, "extends")
    if ext:
        parent = lib_symbol(f"{libname}:{ext[1]}")
        pname = ext[1]
        flat = [x for x in parent if not (isinstance(x, list) and x and x[0] in ("property", "symbol"))]
        flat[1] = Q(lib_id)
        flat += [x for x in sym if isinstance(x, list) and x and x[0] == "property"]
        for unit in findall(parent, "symbol"):
            u = list(unit)
            u[1] = Q(str(unit[1]).replace(pname, name, 1))
            flat.append(u)
        return _modernize(flat)
    out = list(sym)
    out[1] = Q(lib_id)
    return _modernize(out)


def sym_pins(symdef):
    """pin number -> (x, y, angle, name, type) in library coordinates (y up)."""
    pins = {}
    for unit in findall(symdef, "symbol"):
        for p in findall(unit, "pin"):
            at = find(p, "at")
            num = str(find(p, "number")[1])
            pins[num] = (float(at[1]), float(at[2]), int(float(at[3])) if len(at) > 3 else 0,
                         str(find(p, "name")[1]), p[1])
    return pins


def sym_box(symdef):
    """Bounding box of the body graphics and pin ends (library coordinates)."""
    xs, ys = [], []
    for unit in findall(symdef, "symbol"):
        for g in unit:
            if not isinstance(g, list):
                continue
            for k in ("start", "end", "center", "at"):
                c = find(g, k)
                if c and g[0] != "text":
                    xs.append(float(c[1]))
                    ys.append(float(c[2]))
            pts = find(g, "pts")
            if pts:
                for xy in findall(pts, "xy"):
                    xs.append(float(xy[1]))
                    ys.append(float(xy[2]))
    for x, y, *_ in sym_pins(symdef).values():
        xs.append(x)
        ys.append(y)
    if not xs:
        return (-2.54, -2.54, 2.54, 2.54)
    return (min(xs), min(ys), max(xs), max(ys))


# ---------------------------------------------------------------- schematic items
def font(size=1.27):
    return ["font", ["size", size, size]]


def prop_node(name, value, x, y, hide=False, justify=None, angle=0):
    eff = ["effects", font()]
    if justify:
        eff.append(["justify"] + justify)
    if hide:
        eff.append(["hide", "yes"])
    return ["property", Q(name), Q(value), ["at", round(x, 3), round(y, 3), angle], eff]


OUTWARD = {0: (-1, 0, 180), 180: (1, 0, 0), 90: (0, 1, 270), 270: (0, -1, 90)}   # lib angle -> dx, dy, label angle


class Sheet:
    def __init__(self, stem, title, page_title, page_no, root_uuid, sheet_uuid, global_nets):
        self.stem, self.title, self.page_title, self.page_no = stem, title, page_title, page_no
        self.root_uuid, self.sheet_uuid = root_uuid, sheet_uuid
        self.globals = global_nets
        self.items = []
        self.libsyms = {}
        self.path = f"/{root_uuid}/{sheet_uuid}"

    def place_symbol(self, lib_id, ref, value, fp, x, y, pinnets, fields, dnp=False, side_text=False):
        if lib_id not in self.libsyms:
            self.libsyms[lib_id] = lib_symbol(lib_id)
        sd = self.libsyms[lib_id]
        pins = sym_pins(sd)
        x0, y0, x1, y1 = sym_box(sd)
        node = ["symbol", ["lib_id", Q(lib_id)], ["at", x, y, 0], ["unit", 1],
                ["exclude_from_sim", "no"], ["in_bom", "no" if ref.startswith(("#", "H", "TP", "NT", "JP")) else "yes"],
                ["on_board", "no" if ref.startswith("#") else "yes"], ["dnp", "yes" if dnp else "no"],
                ["uuid", uid(self.stem, ref)]]
        top, bottom = y - y1, y - y0
        hide_ref = ref.startswith("#")
        if side_text:
            node.append(prop_node("Reference", ref, x + x1 + 1.5, y - 0.8, hide=hide_ref, justify=["left"]))
            node.append(prop_node("Value", value, x + x1 + 1.5, y + 1.6, hide=hide_ref, justify=["left"]))
        else:
            up = _extent(pinnets, pins, 270)
            down = _extent(pinnets, pins, 90)
            node.append(prop_node("Reference", ref, x, top - up - 1.6, hide=hide_ref))
            node.append(prop_node("Value", value, x, bottom + down + 1.6, hide=hide_ref))
        node.append(prop_node("Footprint", fp, x, bottom + 3.2, hide=True))
        node.append(prop_node("Datasheet", str(prop(sd, "Datasheet")[2]) if prop(sd, "Datasheet") else "", x, bottom, hide=True))
        for k, v in fields.items():
            node.append(prop_node(k, v, x, bottom, hide=True))
        for num in pins:
            node.append(["pin", Q(num), ["uuid", uid(self.stem, ref, "pin", num)]])
        node.append(["instances", ["project", Q(PROJECT), ["path", Q(self.path), ["reference", Q(ref)], ["unit", 1]]]])
        self.items.append(node)
        # wires, labels, no-connects
        for num, (px, py, ang, _, kind) in pins.items():
            ex, ey = x + px, y - py
            net = pinnets.get(num)
            PIN_POS[(ref, num)] = (ex, ey, str(uid(self.stem, ref, "pin", num)), self.path)
            if net is None:
                self.items.append(["no_connect", ["at", round(ex, 3), round(ey, 3)], ["uuid", uid(self.stem, ref, num, "nc")]])
                continue
            dx, dy, lang = OUTWARD[ang % 360]
            lx, ly = ex + dx * 2.54, ey + dy * 2.54
            self.items.append(["wire", ["pts", ["xy", round(ex, 3), round(ey, 3)], ["xy", round(lx, 3), round(ly, 3)]],
                               ["stroke", ["width", 0], ["type", "default"]], ["uuid", uid(self.stem, ref, num, "w")]])
            just = {0: ["left"], 180: ["right"], 90: ["left"], 270: ["right"]}[lang]
            if net in self.globals:
                self.items.append(["global_label", Q(net), ["shape", "passive"], ["at", round(lx, 3), round(ly, 3), lang],
                                   ["fields_autoplaced", "yes"],
                                   ["effects", font(), ["justify"] + just],
                                   ["uuid", uid(self.stem, ref, num, "gl")]])
            else:
                self.items.append(["label", Q(net), ["at", round(lx, 3), round(ly, 3), lang],
                                   ["fields_autoplaced", "yes"],
                                   ["effects", font(), ["justify"] + just + ["bottom"]],
                                   ["uuid", uid(self.stem, ref, num, "l")]])

    def text(self, s, x, y, size=1.27, bold=False):
        f = ["font", ["size", size, size]] + ([["bold", "yes"]] if bold else [])
        self.items.append(["text", Q(s), ["exclude_from_sim", "no"], ["at", x, y, 0],
                           ["effects", f, ["justify", "left", "bottom"]], ["uuid", uid(self.stem, "text", s[:40], x, y)]])

    def write(self):
        paper = getattr(self, "paper", "A3")
        root = ["kicad_sch", ["version", VERSION], ["generator", Q("eeschema")], ["generator_version", Q("10.0")],
                ["uuid", Q(self.sheet_uuid)], ["paper", Q(paper)],
                ["title_block", ["title", Q(f"Mainboard rev B - {self.title}")], ["date", Q("2026-10-21")],
                 ["rev", Q("B")], ["company", Q("Kartonaut")],
                 ["comment", 1, Q(self.page_title)],
                 ["comment", 2, Q("erzeugt aus circuit.py (gen_schematic.py)")]],
                ["lib_symbols"] + list(self.libsyms.values())] + self.items + [["embedded_fonts", "no"]]
        (HERE / f"{self.stem}.kicad_sch").write_text(dumps(root) + "\n", encoding="utf-8")


def label_width(net):
    return len(net) * 1.2 + 4.0 if net else 0.0


FLAG_COUNT = [0]
PIN_POS = {}        # (ref, pin) -> (x mm, y mm, pin uuid, sheet path), for ERC exclusions
FLAG_REF = {}       # net -> power flag reference
PAPER = {"A3": (420.0, 297.0), "A2": (594.0, 420.0)}


def _extent(p_pins, pins, side):
    return max([label_width(p_pins.get(n)) for n, (px, py, a, *_) in pins.items() if a % 360 == side] + [0])


def _entry(lib_id, pinnets, ref, value):
    """Size of one symbol cell and the offset of the symbol origin inside it."""
    sd = lib_symbol(lib_id)
    pins = sym_pins(sd)
    bx0, by0, bx1, by1 = sym_box(sd)
    left, right = _extent(pinnets, pins, 0), _extent(pinnets, pins, 180)
    up, down = _extent(pinnets, pins, 270), _extent(pinnets, pins, 90)
    side_text = not any(a % 180 == 0 for (_, _, a, *_) in pins.values())   # only top/bottom pins: text to the right
    text_w = max(len(ref), len(value)) * 1.2 + 3 if side_text else 0
    w = max((bx1 - bx0) + left + right + text_w + 5, 14)
    h = (by1 - by0) + up + down + (4 if side_text else 9)
    ox = left - bx0 + 2.5
    oy = up + by1 + (2 if side_text else 5)
    return w, h, ox, oy, side_text


def layout_sheet(sh, parts, flags):
    """Functional blocks (circuit.group) packed onto the page; each block framed with its title."""
    blocks = []
    for name in dict.fromkeys(p.group for p in parts):
        blocks.append((name, [p for p in parts if p.group == name]))
    if flags:
        blocks.append(("Power-Flags fuer den ERC", [("#FLG", n) for n in flags]))

    def pack(block_parts, max_w):
        cells, x, y, row_h, used_w = [], 0.0, 0.0, 0.0, 0.0
        for p in block_parts:
            if isinstance(p, tuple):
                w, h, ox, oy, side = _entry("power:PWR_FLAG", {"1": p[1]}, "#FLG00", "PWR_FLAG")
            else:
                w, h, ox, oy, side = _entry(p.lib, p.pins, p.ref, p.value)
            if x > 0 and x + w > max_w:
                x, y, row_h = 0.0, y + row_h, 0.0
            cells.append((p, x + ox, y + oy, side))
            x += w
            used_w = max(used_w, x)
            row_h = max(row_h, h)
        return cells, used_w, y + row_h

    for paper in ("A3", "A2"):
        PW, PH = PAPER[paper]
        X0, X1, Y0, Y1 = 20.0, PW - 20.0, 30.0, PH - 45.0
        placed, x, y, row_h, ok = [], X0, Y0, 0.0, True
        for name, bp in blocks:
            n_big = sum(1 for q in bp if not isinstance(q, tuple) and not q.lib.startswith(("Device:", "Connector:TestPoint", "Jumper:")))
            max_w = 150.0 if n_big or len(bp) > 8 else 110.0
            cells, bw, bh = pack(bp, max_w)
            bw, bh = bw + 6, bh + 10
            if x > X0 and x + bw > X1:
                x, y, row_h = X0, y + row_h + 4, 0.0
            placed.append((name, x, y, bw, bh, cells))
            x += bw + 4
            row_h = max(row_h, bh)
        if y + row_h <= Y1:
            break
    sh.paper = paper
    for name, bx, by, bw, bh, cells in placed:
        sh.items.append(["rectangle", ["start", round(bx, 2), round(by, 2)], ["end", round(bx + bw, 2), round(by + bh, 2)],
                         ["stroke", ["width", 0.2], ["type", "dash"], ["color", 120, 120, 120, 1]],
                         ["fill", ["type", "none"]], ["uuid", uid(sh.stem, "frame", name)]])
        sh.text(name, round(bx + 2, 2), round(by + 5, 2), size=1.8, bold=True)
        for p, cx, cy, side in cells:
            sx, sy = snap(bx + 3 + cx), snap(by + 8 + cy)
            if isinstance(p, tuple):
                FLAG_COUNT[0] += 1
                ref = f"#FLG{FLAG_COUNT[0]:02d}"
                FLAG_REF[p[1]] = ref
                sh.place_symbol("power:PWR_FLAG", ref, "PWR_FLAG", "", sx, sy, {"1": p[1]}, {}, side_text=side)
                continue
            fields = {}
            if p.lcsc:
                fields["LCSC"] = p.lcsc
            if p.func:
                fields["Funktion"] = p.func
            if p.descr:
                fields["Description"] = p.descr
            sh.place_symbol(p.lib, p.ref, p.value, p.fp, sx, sy, p.pins, fields, dnp=p.dnp, side_text=side)


def main():
    root_uuid = str(uid("root"))
    net_sheets = {}
    for p in circuit.PARTS:
        for net in p.pins.values():
            if net:
                net_sheets.setdefault(net, set()).add(p.sheet)
    for s, flags in circuit.PWR_FLAGS.items():
        for net in flags:
            net_sheets.setdefault(net, set()).add(s)
    # all labels global: net names in the netlist stay plain ("VBAT_MEAS", not "/Versorgung/VBAT_MEAS"),
    # so they match the board, the net class patterns and the spec
    globals_ = set(net_sheets)

    sheet_nodes = []
    for i, (stem, title, page_title) in enumerate(circuit.SHEETS):
        sheet_uuid = str(uid("sheet", stem))
        sh = Sheet(stem, title, page_title, i + 2, root_uuid, sheet_uuid, globals_)
        parts = [p for p in circuit.PARTS if p.sheet == stem]
        sh.text(page_title, 25.4, 22.0, size=2.54, bold=True)
        layout_sheet(sh, parts, circuit.PWR_FLAGS.get(stem, []))
        sh.write()
        bx, by = 30 + (i % 4) * 90, 50 + (i // 4) * 60
        sheet_nodes.append(["sheet", ["at", bx, by], ["size", 70, 35], ["exclude_from_sim", "no"], ["in_bom", "yes"],
                            ["on_board", "yes"], ["dnp", "no"], ["fields_autoplaced", "yes"],
                            ["stroke", ["width", 0.1524], ["type", "solid"]], ["fill", ["color", 0, 0, 0, 0.0]],
                            ["uuid", Q(sheet_uuid)],
                            prop_node("Sheetname", title, bx, by - 0.7, justify=["left", "bottom"]),
                            prop_node("Sheetfile", f"{stem}.kicad_sch", bx, by + 35.6, justify=["left", "top"]),
                            ["instances", ["project", Q(PROJECT), ["path", Q(f"/{root_uuid}"), ["page", Q(str(i + 2))]]]]])
        # one-line content summary inside the sheet box
        sheet_nodes.append(["text", Q(page_title.replace(", ", ",\n", 2)), ["exclude_from_sim", "no"], ["at", bx + 2, by + 6, 0],
                            ["effects", font(), ["justify", "left", "top"]], ["uuid", uid("roottext", stem)]])

    notes = [
        "Kartonaut - Flugcomputer-Mainboard rev B (54 x 120 mm, 4 Lagen, JLCPCB)",
        "Spezifikation: hardware/mainboard/README.md; Design Guide: docs/DesignGuide_Mainboard_revB.md",
        "Massen: GND = Logik und 1S-Minus; GND_PWR = Rueckstrom aller 2S-Verbraucher. Einzige Verbindung: NT1 am 2S-Minus.",
        "Dieser Schaltplan wird von gen_schematic.py aus circuit.py erzeugt. Aenderungen dort machen, dann neu erzeugen.",
    ]
    root_items = [["text", Q(n), ["exclude_from_sim", "no"], ["at", 30, 180 + 7 * k, 0],
                   ["effects", font(2.0 if k == 0 else 1.5), ["justify", "left", "bottom"]], ["uuid", uid("note", k)]]
                  for k, n in enumerate(notes)]
    root = ["kicad_sch", ["version", VERSION], ["generator", Q("eeschema")], ["generator_version", Q("10.0")],
            ["uuid", Q(root_uuid)], ["paper", Q("A3")],
            ["title_block", ["title", Q("Mainboard rev B")], ["date", Q("2026-10-21")], ["rev", Q("B")],
             ["company", Q("Kartonaut")], ["comment", 1, Q("Teensy 4.1, ICM-42688-P, BMP390, E22-400T22S, 1S + 2S")]],
            ["lib_symbols"]] + sheet_nodes + root_items + [
        ["sheet_instances", ["path", Q("/"), ["page", Q("1")]]], ["embedded_fonts", "no"]]
    (HERE / f"{PROJECT}.kicad_sch").write_text(dumps(root) + "\n", encoding="utf-8")

    (HERE / "sym-lib-table").write_text(
        '(sym_lib_table\n  (version 7)\n'
        '  (lib (name "mainboard")(type "KiCad")(uri "${KIPRJMOD}/lib/mainboard.kicad_sym")(options "")(descr "Teensy 4.1"))\n'
        '  (lib (name "lcsc")(type "KiCad")(uri "${KIPRJMOD}/lib/lcsc.kicad_sym")(options "")(descr "easyeda2kicad: ICM-42688-P, BMP390, TPS63070, E22"))\n)\n',
        encoding="utf-8")
    (HERE / "fp-lib-table").write_text(
        '(fp_lib_table\n  (version 7)\n'
        '  (lib (name "mainboard")(type "KiCad")(uri "${KIPRJMOD}/lib/mainboard.pretty")(options "")(descr "Teensy 4.1 socket"))\n'
        '  (lib (name "lcsc")(type "KiCad")(uri "${KIPRJMOD}/lib/lcsc.pretty")(options "")(descr "easyeda2kicad footprints"))\n)\n',
        encoding="utf-8")
    write_project()
    print(f"{PROJECT}.kicad_sch + {len(circuit.SHEETS)} sheets, {len(circuit.PARTS)} parts, {len(globals_)} global nets")


def erc_exclusions():
    """Exclusion keys as eeschema 10 stores them, positions in 100 nm:
    type|x|y|main item uuid|aux item uuid|marker sheet path|main item sheet path|aux item sheet path"""
    out = []
    for kind, a, b, why in circuit.ERC_EXCLUSIONS:
        items = []
        for ref, pin in (a, b):
            if ref.startswith("#FLG:"):
                ref = FLAG_REF[ref[5:]]
            items.append(PIN_POS[(ref, pin)])
        (x, y, ua, pa), (_, _, ub, pb) = items
        out.append([f"{kind}|{round(x * 10000)}|{round(y * 10000)}|{ua}|{ub}|{pa}|{pa}|{pb}", why])
    return out


def write_project():
    """Project file with JLC-capable design rules and the net classes of circuit.NETCLASSES."""
    classes = [{"name": "Default", "track_width": 0.2, "clearance": 0.15, "via_diameter": 0.6, "via_drill": 0.3,
                "microvia_diameter": 0.3, "microvia_drill": 0.1, "diff_pair_width": 0.2, "diff_pair_gap": 0.25,
                "wire_width": 6, "bus_width": 12, "line_style": 0, "pcb_color": "rgba(0, 0, 0, 0.000)",
                "schematic_color": "rgba(0, 0, 0, 0.000)", "priority": 2147483647}]
    patterns = []
    for i, (name, (tw, cl, vd, vdr, nets)) in enumerate(circuit.NETCLASSES.items()):
        classes.append({"name": name, "track_width": tw, "clearance": cl, "via_diameter": vd, "via_drill": vdr,
                        "microvia_diameter": 0.3, "microvia_drill": 0.1, "diff_pair_width": 0.2, "diff_pair_gap": 0.25,
                        "wire_width": 6, "bus_width": 12, "line_style": 0, "pcb_color": "rgba(0, 0, 0, 0.000)",
                        "schematic_color": "rgba(0, 0, 0, 0.000)", "priority": i})
        patterns += [{"netclass": name, "pattern": n} for n in nets]
    pro = {
        "board": {"design_settings": {
            "defaults": {"board_outline_line_width": 0.1, "copper_line_width": 0.2, "copper_text_size_h": 1.5,
                         "copper_text_size_v": 1.5, "copper_text_thickness": 0.3, "silk_line_width": 0.12,
                         "silk_text_size_h": 0.8, "silk_text_size_v": 0.8, "silk_text_thickness": 0.12},
            "rules": {"min_clearance": 0.127, "min_track_width": 0.09, "min_via_diameter": 0.45,
                      "min_through_hole_diameter": 0.2, "min_via_annular_width": 0.075, "min_hole_clearance": 0.25,
                      "min_hole_to_hole": 0.25, "min_copper_edge_clearance": 0.2, "min_silk_clearance": 0.0,
                      "min_text_height": 0.6, "min_text_thickness": 0.1, "solder_mask_to_copper_clearance": 0.0},
            "track_widths": [0.0, 0.2, 0.3, 0.6, 1.2, 2.0],
            "via_dimensions": [{"diameter": 0.0, "drill": 0.0}, {"diameter": 0.6, "drill": 0.3}, {"diameter": 0.8, "drill": 0.4}],
        }},
        "meta": {"filename": f"{PROJECT}.kicad_pro", "version": 3},
        "net_settings": {"classes": classes, "meta": {"version": 4}, "netclass_patterns": patterns},
        "erc": {"erc_exclusions": erc_exclusions()},
        "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
        "sheets": [[str(uid("root")), "Root"]] + [[str(uid("sheet", s)), t] for s, t, _ in circuit.SHEETS],
        "text_variables": {},
    }
    (HERE / f"{PROJECT}.kicad_pro").write_text(json.dumps(pro, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
