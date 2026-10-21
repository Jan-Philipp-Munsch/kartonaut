"""Project library for the mainboard rev B.

Writes lib/mainboard.kicad_sym (Teensy 4.1 on two 1x24 sockets) and
lib/mainboard.pretty/Teensy41_Socket.kicad_mod, and fixes the pin types of the four parts that
easyeda2kicad converted from LCSC into lib/lcsc.kicad_sym (it marks every pin "unspecified",
which ERC cannot check). The LCSC parts themselves are fetched once with

    python -m easyeda2kicad --full --lcsc_id C1850418 C5124834 C109322 C2903765 \
        --output lib/lcsc --project-relative

TPS63070RNMR (C109322): the datasheet has VOUT on pins 7 and 8 and VIN on 12 and 13. The LCSC symbol
lists only 7 and 12, and the LCSC footprint draws pads 8 and 13 as extra pads numbered 7 and 12, so
both pins are connected. When this footprint is swapped (e.g. for a KiCad standard VQFN-15), add pins
8 (5V_SYS) and 13 (VSYS_IN) in circuit.py.

Teensy 4.1 pinout (PJRC card, top view, USB at the top):
    left row,  top to bottom: GND, 0..12, 3.3V, 24..32
    right row, top to bottom: VIN, GND, 3.3V, 23..13, GND, 41..33
Rows 15.24 mm apart, 2.54 mm pitch, 24 pins each. Pads 1..24 are the left row, 25..48 the right.
The five pads at the SD end (VBAT, 3.3V, GND, Program, On/Off) are not on the socket.
"""
from pathlib import Path

from sexpr import Q, dumps, find, findall, parse

HERE = Path(__file__).resolve().parent
LIB = HERE / "lib"

LEFT = ["GND"] + [str(i) for i in range(0, 13)] + ["3V3"] + [str(i) for i in range(24, 33)]
RIGHT = ["VIN", "GND", "3V3"] + [str(i) for i in range(23, 12, -1)] + ["GND"] + [str(i) for i in range(41, 32, -1)]
assert len(LEFT) == 24 and len(RIGHT) == 24
TEENSY_PINS = {i + 1: n for i, n in enumerate(LEFT + RIGHT)}   # pad number -> pin name
PITCH, ROW = 2.54, 15.24


def teensy_pad(name):
    """Pad number of a Teensy pin name ('0'..'41', 'VIN'); unique names only."""
    hits = [k for k, v in TEENSY_PINS.items() if v == name]
    assert len(hits) == 1, name
    return str(hits[0])


def _pin(num, name, kind, x, y, ang):
    return ["pin", kind, "line", ["at", x, y, ang], ["length", 2.54],
            ["name", Q(name), ["effects", ["font", ["size", 1.27, 1.27]]]],
            ["number", Q(str(num)), ["effects", ["font", ["size", 1.27, 1.27]]]]]


def _prop(name, value, x, y, hide=False):
    eff = ["effects", ["font", ["size", 1.27, 1.27]]]
    if hide:
        eff.append(["hide", "yes"])
    return ["property", Q(name), Q(value), ["at", x, y, 0], eff]


def teensy_symbol():
    w, top = 12.7, 30.48
    pins = []
    seen_3v3 = False
    for num, name in TEENSY_PINS.items():
        left = num <= 24
        idx = (num - 1) % 24
        y = top - idx * PITCH
        if name == "GND":
            kind = "power_in"
        elif name == "VIN":
            kind = "power_in"
        elif name == "3V3":
            kind = "passive" if seen_3v3 else "power_out"   # two 3V3 pins: only one may drive
            seen_3v3 = True
        else:
            kind = "bidirectional"
        label = name if not name.isdigit() else f"D{name}"
        pins.append(_pin(num, label, kind, -w - 2.54 if left else w + 2.54, y, 0 if left else 180))
    body = ["symbol", Q("Teensy4.1_Socket_0_1"),
            ["rectangle", ["start", -w, top + 2.54], ["end", w, top - 24 * PITCH],
             ["stroke", ["width", 0.254], ["type", "default"]], ["fill", ["type", "background"]]],
            ["text", Q("USB"), ["at", 0, top + 1.0, 0], ["effects", ["font", ["size", 1.27, 1.27]]]]]
    unit = ["symbol", Q("Teensy4.1_Socket_1_1")] + pins
    return ["symbol", Q("Teensy4.1_Socket"), ["exclude_from_sim", "no"], ["in_bom", "yes"], ["on_board", "yes"],
            _prop("Reference", "U", 0, top + 5.08),
            _prop("Value", "Teensy4.1_Socket", 0, top + 3.6),
            _prop("Footprint", "mainboard:Teensy41_Socket", 0, -35, True),
            _prop("Datasheet", "https://www.pjrc.com/store/teensy41.html", 0, -37, True),
            _prop("Description", "Teensy 4.1 plugged into two 1x24 female headers (2.54 mm, 8.5 mm high)", 0, -39, True),
            body, unit]


def write_symbols():
    lib = ["kicad_symbol_lib", ["version", "20241209"], ["generator", Q("build_lib.py")],
           ["generator_version", Q("1.0")], teensy_symbol()]
    (LIB / "mainboard.kicad_sym").write_text(dumps(lib) + "\n", encoding="utf-8")


def write_footprint():
    pads = []
    for num in TEENSY_PINS:
        left = num <= 24
        idx = (num - 1) % 24
        x = -ROW / 2 if left else ROW / 2
        y = -11.5 * PITCH + idx * PITCH
        shape = "rect" if num == 1 else "circle"
        pads.append(f'\t(pad "{num}" thru_hole {shape} (at {x:.3f} {y:.3f}) (size 1.7 1.7) (drill 1.0) '
                    f'(layers "*.Cu" "*.Mask"))')
    W, L = 17.78, 60.96 + 0.2     # Teensy 4.1: 0.7 x 2.4 in
    hl, hw = L / 2, W / 2
    sw = ROW / 2 + 1.35           # socket body half-width (2.54 mm wide strip)
    lines = []

    def rect(layer, x0, y0, x1, y1, width):
        lines.append(f'\t(fp_rect (start {x0:.3f} {y0:.3f}) (end {x1:.3f} {y1:.3f}) '
                     f'(stroke (width {width}) (type solid)) (fill no) (layer "{layer}"))')

    rect("F.Fab", -hw, -hl, hw, hl, 0.1)
    rect("F.Fab", -5.0, -hl - 1.0, 5.0, -hl + 4.5, 0.1)          # USB-Micro-B overhang
    rect("F.SilkS", -sw, -hl - 0.2, -ROW / 2 + 1.35, hl + 0.2, 0.12)
    rect("F.SilkS", ROW / 2 - 1.35, -hl - 0.2, sw, hl + 0.2, 0.12)
    # Courtyard only around the two socket strips: the space between them (under the Teensy, up to
    # 3 mm high) carries the IMU and small SMD parts. The Teensy outline itself is on F.Fab.
    for sx in (-ROW / 2, ROW / 2):
        rect("F.CrtYd", sx - 1.52, -hl - 0.25, sx + 1.52, hl + 0.25, 0.05)
    txt = ('\t(fp_text user "USB" (at 0 {:.3f}) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))\n'
           '\t(fp_text user "SD" (at 0 {:.3f}) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))\n'
           .format(-hl + 2.0, hl - 2.0))
    socket = "${KICAD10_3DMODEL_DIR}/Connector_PinSocket_2.54mm.3dshapes/PinSocket_1x24_P2.54mm_Vertical.step"
    models = "".join(f'\t(model "{m}" (offset (xyz {x:.3f} {y:.3f} {z})) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))\n'
                     for m, x, y, z in [(socket, -ROW / 2, 11.5 * PITCH, 0), (socket, ROW / 2, 11.5 * PITCH, 0),
                                        ("${KIPRJMOD}/lib/mainboard.3dshapes/Teensy41.step", 0, 0, 0)])
    fp = ('(footprint "Teensy41_Socket" (version 20241229) (generator "build_lib.py")\n'
          '\t(layer "F.Cu")\n'
          '\t(descr "Teensy 4.1 on two 1x24 female headers, rows 15.24 mm apart; pads 1-24 left row, 25-48 right row, USB at -y")\n'
          '\t(attr through_hole)\n'
          '\t(property "Reference" "REF**" (at 0 {:.3f} 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))\n'
          '\t(property "Value" "Teensy41_Socket" (at 0 {:.3f} 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))\n'
          .format(-hl - 2.5, hl + 1.5)
          + "\n".join(lines) + "\n" + txt + "\n".join(pads) + "\n" + models + ")\n")
    (LIB / "mainboard.pretty").mkdir(exist_ok=True)
    (LIB / "mainboard.pretty" / "Teensy41_Socket.kicad_mod").write_text(fp, encoding="utf-8")


# Pin types for the LCSC symbols, by pin name (anything not listed: passive)
LCSC_TYPES = {
    "VDD": "power_in", "VDDIO": "power_in", "GND": "power_in", "VSS": "power_in", "PGND": "power_in",
    "VCC": "power_in", "Vin": "power_in", "Vout": "power_out", "Vaux": "passive",
    "AP_CS": "input", "AP_SCL/AP_SCLK": "input", "AP_SDA/AP_SDIO/AP_SDI": "bidirectional",
    "AP_SDO/AP_AD0": "output", "INT1/INT": "output", "INT2/FSYNC/CLKIN": "input", "RESV": "passive",
    "SCK": "input", "SDI": "bidirectional", "SDO": "input", "CSB": "input", "INT": "output",
    "EN": "input", "PS/SYNC": "input", "Vsel": "input", "PG": "open_collector", "FB": "input", "FB2": "passive",
    "L1": "passive", "L2": "passive",
    "TXD": "output", "RXD": "input", "AUX": "output", "M0": "input", "M1": "input", "RESET": "input",
    "ANT": "passive", "NC": "no_connect",
}


def teensy_model():
    """Simplified Teensy 4.1 on 8.5 mm sockets as STEP (CadQuery), for the 3D renders only."""
    try:
        import cadquery as cq
    except ImportError:
        print("cadquery missing: no Teensy 3D model")
        return
    z0 = 8.5                                       # socket height: Teensy PCB rests on the sockets
    pcb = cq.Workplane("XY").box(17.78, 60.96, 1.57, centered=(True, True, False)).translate((0, 0, z0))
    holes = cq.Workplane("XY")
    for sx in (-ROW / 2, ROW / 2):
        for i in range(24):
            holes = holes.union(cq.Workplane("XY").circle(0.5).extrude(1.6).translate((sx, -29.21 + i * PITCH, z0)))
    pcb = pcb.cut(holes)
    top = z0 + 1.57
    mcu = cq.Workplane("XY").box(10, 10, 1.2, centered=(True, True, False)).translate((0, -2.0, top))
    flash = cq.Workplane("XY").box(5, 6, 1.0, centered=(True, True, False)).translate((0, 10.5, top))
    usb = cq.Workplane("XY").box(7.5, 5.6, 2.6, centered=(True, True, False)).translate((0, 29.2, top))
    sd = cq.Workplane("XY").box(12.0, 11.5, 1.6, centered=(True, True, False)).translate((0, -25.0, z0 - 1.6))
    btn = cq.Workplane("XY").box(3.0, 2.2, 1.0, centered=(True, True, False)).translate((-5.0, 22.5, top))
    asm = cq.Assembly()
    asm.add(pcb, name="pcb", color=cq.Color(0.10, 0.35, 0.18))
    asm.add(mcu, name="mcu", color=cq.Color(0.12, 0.12, 0.12))
    asm.add(flash, name="flash", color=cq.Color(0.12, 0.12, 0.12))
    asm.add(usb, name="usb", color=cq.Color(0.75, 0.75, 0.78))
    asm.add(sd, name="sd", color=cq.Color(0.70, 0.70, 0.72))
    asm.add(btn, name="button", color=cq.Color(0.9, 0.9, 0.9))
    (LIB / "mainboard.3dshapes").mkdir(exist_ok=True)
    asm.save(str(LIB / "mainboard.3dshapes" / "Teensy41.step"))


def xt30_model():
    """XT30PW-M (horizontal, board connector) as a simple STEP: the KiCad library names a model for
    this footprint but does not ship it. Footprint origin = pin 1; the body extends toward -y (model +y)."""
    try:
        import cadquery as cq
    except ImportError:
        return
    body = cq.Workplane("XY").box(10.2, 12.9, 5.2, centered=(True, False, False)).translate((-2.5, 0.6, 0))
    for x in (0.0, -5.0):                                     # the two socket openings at the mouth
        body = body.cut(cq.Workplane("XY").box(3.2, 4.0, 3.0, centered=(True, False, False)).translate((x, 9.6, 1.1)))
    pins = cq.Workplane("XY")
    for x in (0.0, -5.0):
        pins = pins.union(cq.Workplane("XY").box(1.0, 1.0, 5.0, centered=(True, True, False)).translate((x, 0, -3.0)))
    asm = cq.Assembly()
    asm.add(body, name="body", color=cq.Color(0.95, 0.80, 0.15))
    asm.add(pins, name="pins", color=cq.Color(0.80, 0.65, 0.30))
    asm.save(str(LIB / "mainboard.3dshapes" / "XT30PW-M.step"))


def fix_lcsc_model_paths():
    for f in (LIB / "lcsc.pretty").glob("*.kicad_mod"):
        s = f.read_text(encoding="utf-8")
        s2 = s.replace("${KIPRJMOD}/lcsc.3dshapes/", "${KIPRJMOD}/lib/lcsc.3dshapes/")
        if s2 != s:
            f.write_text(s2, encoding="utf-8")


def fix_lcsc_pin_types():
    path = LIB / "lcsc.kicad_sym"
    tree = parse(path.read_text(encoding="utf-8"))
    for sym in findall(tree, "symbol"):
        for unit in findall(sym, "symbol"):
            for pin in findall(unit, "pin"):
                name = find(pin, "name")[1]
                pin[1] = LCSC_TYPES.get(str(name), "passive")
    path.write_text(dumps(tree) + "\n", encoding="utf-8")


if __name__ == "__main__":
    write_symbols()
    write_footprint()
    fix_lcsc_pin_types()
    fix_lcsc_model_paths()
    teensy_model()
    xt30_model()
    print("lib/mainboard.kicad_sym, lib/mainboard.pretty/Teensy41_Socket.kicad_mod written; lcsc pin types set")
