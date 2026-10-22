"""Build the board of mainboard rev B: footprints, nets, placement, outline, planes, rule areas.

Runs in KiCad's own Python (it needs the pcbnew module):

    "%LOCALAPPDATA%/Programs/KiCad/10.0/bin/python.exe" gen_pcb.py place     # board without tracks
    "%LOCALAPPDATA%/Programs/KiCad/10.0/bin/python.exe" gen_pcb.py dsn       # + Specctra export for Freerouting
    "%LOCALAPPDATA%/Programs/KiCad/10.0/bin/python.exe" gen_pcb.py ses       # import routed session, fill zones

Placement follows mainboard_placement.svg (outline.py): connectors at the end faces, converters in
the left strip away from the IMU, sensors and logic in the right strip, IMU under the Teensy on the
roll axis. Connectors and ICs are anchored by hand (ANCHORS, EDGE); passives are placed by a greedy
search next to the pad of their owner part (place_passives). Board coordinates: u across (0 on the
roll axis), v along the rocket (0 at the TVC end) as in outline.py; KiCad x = X0 + 27 + u,
y = Y0 + 120 - v (nose at the top of the screen).
"""
import math
import os
import sys
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import circuit                      # noqa: E402
import outline                      # noqa: E402  (hardware/mainboard/outline.py: board size, holes)
from gen_schematic import lib_symbol, sym_pins, uid   # noqa: E402
from sexpr import prop              # noqa: E402

KICAD = Path(os.environ.get("KICAD10_DIR", Path.home() / "AppData/Local/Programs/KiCad/10.0"))
STD_FP = KICAD / "share/kicad/footprints"
PCB = Path(os.environ.get("MAINBOARD_PCB", HERE / "mainboard.kicad_pcb"))
X0, Y0 = 100.0, 50.0
W, L = outline.BOARD_W, outline.BOARD_L
MM = pcbnew.FromMM


def XY(u, v):
    return X0 + W / 2 + u, Y0 + L - v


def UV(x, y):
    return x - X0 - W / 2, Y0 + L - y


def P(u, v):
    x, y = XY(u, v)
    return pcbnew.VECTOR2I(MM(x), MM(y))


# ---------------------------------------------------------------- placement data (u, v in mm; rot in degrees)
# Footprint origin positions. Rotation 180 turns a horizontal connector's mouth from -y to +y etc.
ANCHORS = {
    "A1": (0.0, 60.5, 0),           # Teensy: USB toward the nose (+v), SD toward the TVC
    "U4": (0.0, 60.5, 0),           # IMU on the roll axis under the Teensy; chip X = +u, Y = +v
    # left strip, TVC end: power entry
    "J3": (-21.5, 19.3, 0),         # J_SW, PH-4 top entry, right above the XT30
    "J2": (-10.0, 19.3, 0),         # J_BAT1, PH-2 top entry
    "R_SH1": (-23.5, 27.0, 90),     # shunt along the strip
    "U6": (-16.5, 26.5, 0),         # INA219 next to the shunt (Kelvin taps short)
    # left strip: buck-boost 5V_SYS, >= 25 mm from the IMU
    "U2": (-15.5, 44.0, 0),         # L1/L2 pins (11, 9) face the nose
    "L2": (-15.5, 48.7, 0),         # straight above U2: pad 1 at pin 11 (L1), pad 2 at pin 9 (L2), no crossing
    "C19": (-21.4, 56.2, 0),        # 1000 uF polymer at 5V_SYS
    # left strip: radio, GPS and signals toward the nose
    "U10": (-17.9, 74.5, 180),      # LoRa module, ANT side toward the nose; castellated pads reach 0.9 mm
                                    # past the body: 0.2 mm to the edge, 0.53 mm to the Teensy pads
    "U3": (-13.0, 90.0, 0),         # LDO 3V3_RF above the module
    "J11": (-17.0, 97.5, 0),        # GPS, GH-4 top entry
    "J13": (-17.0, 104.5, 0),       # camera, GH-3 top entry
    "J14": (-16.0, 111.5, 0),       # external LEDs, GH-3 top entry
    # centre, TVC end
    "C3": (0.0, 18.0, 0),           # 1000 uF at VSERVO, between the servo connectors
    # right strip: actuators
    "J7": (11.0, 19.0, 0),          # chute servo, XH-3 top entry
    "J8": (20.5, 25.5, 0),          # roll motor, PH-2 top entry
    "U1": (16.5, 31.5, 180),        # 5V_SERVO buck, SW pin toward L1
    "L1": (22.5, 33.0, 90),
    "C11": (12.5, 41.5, 0),         # 470 uF at 5V_SERVO
    "U7": (21.5, 49.0, 90),         # DRV8833
    "R20": (16.9, 47.5, 0),         # nSLEEP pull-up right at pin 1 (the placer put it out of reach)
    # right strip: logic and sensors
    "U8": (13.5, 60.0, 0),
    "U9": (13.5, 66.0, 0),
    "LED1": (22.0, 60.0, 0),
    "LED2": (22.0, 66.0, 0),
    "J12": (21.0, 75.0, 0),         # Qwiic, top entry
    "J15": (12.0, 90.0, 0),         # J_EXP 2x7, rows along v
    "U5": (21.5, 85.0, 0),          # BMP390, far from coils and CPU
    "BZ1": (13.0, 98.5, 0),         # buzzer, 12 mm, |u| < 25
}
EDGE = {  # ref: (edge, u of the footprint origin, rot) - the courtyard is moved flush with that edge
    "J1": ("bottom", -15.3, 180),   # XT30PW-M, mouth toward the TVC end, clear of hole H1
    "J5": ("bottom", -2.3, 0),      # servo yaw, XH-3 side entry
    "J6": ("bottom", 9.9, 0),       # servo pitch
    "J4": ("top", -6.0, 180),       # arming switch, PH-2 side entry, toward the nose
    "J10": ("top", 3.0, 180),       # pyro 2
    "J9": ("top", 13.5, 180),       # pyro 1
}
HOLES = {f"H{i + 1}": xy for i, xy in enumerate(outline.HOLES)}

STRIP_L, STRIP_R = (-26.4, -9.3), (9.3, 26.4)       # beside the Teensy socket courtyards
BOARD = (-26.4, 26.4, 0.6, 119.4)
# Regions for the passives of each schematic block (u0, u1, v0, v1)
REGIONS = {
    "2S: Akku, Verpolschutz, Hauptschalter": (-26.4, -2.0, 10.0, 26.0),
    "2S: Spannungsmessung und Strommessung INA219": (*STRIP_L, 20.0, 38.0),
    "2S: Servo-Schiene VSERVO": (-9.0, 9.3, 10.0, 31.0),
    "2S: Buck U1 -> 5V_SERVO": (*STRIP_R, 22.0, 46.0),
    "1S: Akku, Verpolschutz, Spannungsmessung": (*STRIP_L, 20.0, 40.0),
    "1S: Buck-Boost U2 -> 5V_SYS, Teensy-VIN": (*STRIP_L, 36.0, 61.0),
    "LDO U3 -> 3V3_RF, Sternpunkt, Testpunkte": (*STRIP_L, 86.0, 96.0),
    "Teensy 4.1": BOARD,
    "Erweiterung, Befestigung, Testpunkte": BOARD,
    "IMU ICM-42688-P, SPI1": (-6.0, 6.0, 50.0, 71.0),
    "Barometer BMP390 und I2C": (*STRIP_R, 70.0, 92.0),
    "LoRa E22-400T22S, Serial8": (*STRIP_L, 58.0, 96.0),
    "GPS, Serial1": (*STRIP_L, 92.0, 116.0),
    "Servos": (-9.0, 26.4, 8.0, 31.0),
    "Rollmotor DRV8833": (*STRIP_R, 38.0, 58.0),
    "Arming": (-14.0, 26.4, 88.0, 119.4),
    "Pyro-Kanal 1": (-14.0, 26.4, 88.0, 119.4),
    "Pyro-Kanal 2": (-14.0, 26.4, 88.0, 119.4),
    "Status-LEDs": (*STRIP_R, 54.0, 72.0),
    "Summer": (0.0, 26.4, 86.0, 112.0),
    "Kamera": (*STRIP_L, 92.0, 116.0),
}
REF_REGIONS = {"NT1": (-14.0, -2.0, 8.0, 24.0)}        # star point right at the 2S minus of J1
REF_REGIONS.update({f"TP{i}": BOARD for i in range(1, 10)})   # test points: next to their net, anywhere
# SD card and USB plug sit at Teensy height (8.5 mm sockets): flat SMD parts may go underneath,
# tall THT parts not. The placer only places SMD passives, so these are checked for anchors only.
KEEPOUTS = [(u0, u1, v0, v1) for _, u0, u1, v0, v1 in outline.KEEPOUTS]
UNDER_TEENSY = (-6.1, 6.1, 30.0, 91.0)          # only parts up to 3 mm high, i.e. the IMU block
# Silkscreen: front carries short names, the back the logo, title and pin-out (JLC: 1.0 mm text, 0.15 mm stroke)
LABELS = {  # front, next to the connector instead of its J number
    "J1": "2S", "J2": "1S", "J3": "SW", "J4": "ARM", "J5": "YAW", "J6": "PITCH", "J7": "CHUTE", "J8": "MOT",
    "J9": "PYRO1", "J10": "PYRO2", "J11": "GPS", "J12": "QWIIC", "J13": "CAM", "J14": "LED", "J15": "EXP",
}
PINOUT = {  # back, pin 1 first; one word per pin (checked against circuit.py), J15 only its supply pins
    "J1": "+ -", "J2": "+ -", "J3": "1S 1S 2S 2S", "J4": "2S ARM", "J5": "S + -", "J6": "S + -", "J7": "S 5V -",
    "J8": "A B", "J9": "+ -", "J10": "+ -", "J11": "3V3 GND TX RX", "J12": "GND 3V3 SDA SCL",
    "J13": "5V TRG GND", "J14": "5V DAT GND", "J15": "1:3V3 2:GND 14:5V",
}
TP_LABELS = {"VBAT_PROT": "VBAT", "VSYS_IN": "VSYS", "5V_SYS": "5V", "VSERVO": "VSRV", "5V_SERVO": "5VS",
             "3V3_RF": "3V3RF", "GND": "GND", "SDA": "SDA", "SCL": "SCL"}   # test points by net, not TPn
SILK_H, SILK_T = 1.0, 0.15
NAME, REV = "KARTONAUT", "MAINBOARD REV B"
MASK_COLOR = "Blue"


# ---------------------------------------------------------------- helpers
def fp_dir(lib):
    return HERE / "lib" / f"{lib}.pretty" if lib in ("mainboard", "lcsc") else STD_FP / f"{lib}.pretty"


# The KiCad library names a 3D model for these footprints but does not ship it; build_lib.py makes one.
# Models() only hands out copies, so the path is replaced in the saved file (fix_model_paths).
OWN_MODELS = {"${KICAD10_3DMODEL_DIR}/Connector_AMASS.3dshapes/AMASS_XT30PW-M_1x02_P2.50mm_Horizontal.step":
              "${KIPRJMOD}/lib/mainboard.3dshapes/XT30PW-M.step"}


def fix_model_paths():
    s = PCB.read_text(encoding="utf-8")
    for a, b in OWN_MODELS.items():
        s = s.replace(f'(model "{a}"', f'(model "{b}"')
    PCB.write_text(s, encoding="utf-8")


def load_fp(fpid):
    lib, name = fpid.split(":")
    fp = pcbnew.FootprintLoad(str(fp_dir(lib)), name)
    assert fp, fpid
    fp.SetFPID(pcbnew.LIB_ID(lib, name))

    return fp


def passive(ref):
    p = next(q for q in circuit.PARTS if q.ref == ref)
    return p.lib.startswith(("Device:R", "Device:C", "Device:L", "Device:D", "Connector:TestPoint")) and ref != "R_SH1"


def crt_box(fp):
    """Courtyard bounding box in (u0, u1, v0, v1)."""
    poly = fp.GetCourtyard(pcbnew.F_CrtYd)
    bb = poly.BBox() if poly.OutlineCount() else fp.GetBoundingBox(False)
    x0, y0 = pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop())
    x1, y1 = pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom())
    (u0, v1), (u1, v0) = UV(x0, y0), UV(x1, y1)
    return (u0, u1, v0, v1)


def overlap(a, b, gap=0.0):
    return a[0] < b[1] + gap and b[0] < a[1] + gap and a[2] < b[3] + gap and b[2] < a[3] + gap


def inside(a, r):
    return a[0] >= r[0] and a[1] <= r[1] and a[2] >= r[2] and a[3] <= r[3]


def set_pose(fp, u, v, rot):
    fp.SetOrientationDegrees(rot)
    fp.SetPosition(P(u, v))


# ---------------------------------------------------------------- board
def new_board():
    b = pcbnew.CreateEmptyBoard()
    b.SetCopperLayerCount(4)
    pcbnew.SaveBoard(str(PCB), b, True)
    board = pcbnew.LoadBoard(str(PCB))         # attaches mainboard.kicad_pro (rules, net classes)
    board.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER)   # solid GND plane, Freerouting keeps off it
    board.SetLayerType(pcbnew.B_Cu, pcbnew.LT_POWER)     # split supply plane GND_PWR / 5V_SYS
    return board


def draw_outline(board):
    hw, cr = W / 2, outline.CORNER_R

    def seg(a, b):
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(P(*a))
        s.SetEnd(P(*b))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(MM(0.1))
        board.Add(s)

    def arc(c, start, mid, end):
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
        s.SetArcGeometry(P(*start), P(*mid), P(*end))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(MM(0.1))
        board.Add(s)

    seg((-hw + cr, 0), (hw - cr, 0))
    seg((hw, cr), (hw, L - cr))
    seg((hw - cr, L), (-hw + cr, L))
    seg((-hw, L - cr), (-hw, cr))
    k = cr * (1 - math.sqrt(0.5))
    arc(None, (hw - cr, 0), (hw - k, k), (hw, cr))
    arc(None, (hw, L - cr), (hw - k, L - k), (hw - cr, L))
    arc(None, (-hw + cr, L), (-hw + k, L - k), (-hw, L - cr))
    arc(None, (-hw, cr), (-hw + k, k), (-hw + cr, 0))


def add_footprints(board):
    netinfo = {}
    for name in circuit.nets():
        n = pcbnew.NETINFO_ITEM(board, name)
        board.Add(n)
        netinfo[name] = n
    fps = {}
    for p in circuit.PARTS:
        pins = sym_pins(lib_symbol(p.lib))
        for num, net in list(p.pins.items()):
            if net is None and num in pins:
                name = f"unconnected-({p.ref}-{pins[num][3]}-Pad{num})"
                n = pcbnew.NETINFO_ITEM(board, name)
                board.Add(n)
                netinfo[name] = n
                p.pins[num] = name
    sheet_uuid = {s: str(uid("sheet", s)) for s, _, _ in circuit.SHEETS}
    titles = {s: t for s, t, _ in circuit.SHEETS}
    for p in circuit.PARTS:
        fp = load_fp(p.fp)
        fp.SetReference(p.ref)
        fp.SetValue(p.value)
        fp.SetPath(pcbnew.KIID_PATH(f"{sheet_uuid[p.sheet]}/{uid(p.sheet, p.ref)}"))
        fp.SetSheetname(titles[p.sheet])
        fp.SetSheetfile(f"{p.sheet}.kicad_sch")
        if p.lcsc:
            fp.SetField("LCSC", p.lcsc)
        if p.func:
            fp.SetField("Funktion", p.func)
        if p.descr:
            fp.SetField("Description", p.descr)
        ds = prop(lib_symbol(p.lib), "Datasheet")
        if ds and str(ds[2]):
            fp.SetField("Datasheet", str(ds[2]))
        for f in fp.GetFields():           # extra fields are data for BOM and parity, not silkscreen
            if not (f.IsReference() or f.IsValue()):
                f.SetVisible(False)
        attrs = fp.GetAttributes()
        if p.ref.startswith(("TP", "H", "NT", "JP")):
            attrs |= pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES
        fp.SetAttributes(attrs)
        for pad in fp.Pads():
            net = p.pins.get(pad.GetNumber())
            if net:
                pad.SetNet(netinfo[net])
        if passive(p.ref):
            fp.Reference().SetLayer(pcbnew.F_Fab)          # passives: designator on the assembly drawing only
        fp.Value().SetLayer(pcbnew.F_Fab)
        for item in fp.GraphicalItems():
            if isinstance(item, pcbnew.PCB_TEXT) and item.GetLayer() == pcbnew.F_SilkS:
                item.SetLayer(pcbnew.F_Fab)
        board.Add(fp)
        fps[p.ref] = fp
    return fps


def place_fixed(board, fps):
    placed = {}
    for ref, (u, v, rot) in ANCHORS.items():
        set_pose(fps[ref], u, v, rot)
        placed[ref] = crt_box(fps[ref])
    for ref, (edge, u, rot) in EDGE.items():
        fp = fps[ref]
        set_pose(fp, u, 50.0, rot)
        b = crt_box(fp)
        dv = (-b[2] - 0.3) if edge == "bottom" else (L - b[3] + 0.3)   # mouth 0.3 mm past the edge
        set_pose(fp, u, 50.0 + dv, rot)
        placed[ref] = crt_box(fp)
    # the Teensy blocks only its two socket strips, not the space between them
    a = placed.pop("A1")
    placed["A1:L"] = (a[0], a[0] + 3.04, a[2], a[3])
    placed["A1:R"] = (a[1] - 3.04, a[1], a[2], a[3])
    for ref, (u, v) in HOLES.items():
        set_pose(fps[ref], u, v, 0)
        placed[ref] = (u - 3.0, u + 3.0, v - 3.0, v + 3.0)
    # report collisions between fixed parts (the Teensy courtyard covers only the socket strips)
    refs = list(placed)
    clash = [(a, b) for i, a in enumerate(refs) for b in refs[i + 1:]
             if overlap(placed[a], placed[b])]
    clash += [(a, "SD/USB-Freiraum") for a in placed if not a.startswith(("A1", "U4")) and any(overlap(placed[a], k) for k in KEEPOUTS)]
    return placed, clash


def owner_target(p, fps, placed):
    """Where a passive wants to sit: at the pad of an already placed part sharing a signal net."""
    best = None
    for net in p.pins.values():
        if not net or net in ("GND", "GND_PWR"):
            continue
        for q in circuit.PARTS:
            if q.ref == p.ref or (q.ref not in placed and q.ref + ":L" not in placed):
                continue
            for pin, n2 in q.pins.items():
                if n2 != net:
                    continue
                for pad in fps[q.ref].Pads():
                    if pad.GetNumber() == pin:
                        pos = pad.GetPosition()
                        u, v = UV(pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y))
                        score = (0 if q.group == p.group else 1, 0 if q.ref[0] in "UAJQ" else 1)
                        if best is None or score < best[0]:
                            best = (score, (u, v))
    return best[1] if best else None


RINGS = sorted(((du * 0.5, dv * 0.5) for du in range(-60, 61) for dv in range(-60, 61)),
               key=lambda d: d[0] ** 2 + d[1] ** 2)


def place_passives(fps, placed):
    region_board = (-W / 2 + 0.6, W / 2 - 0.6, 0.6, L - 0.6)
    failed = []
    pending = [p for p in circuit.PARTS if p.ref not in placed and p.ref != "A1"]
    for _ in range(3):                      # owners may themselves be passives placed later
        rest = []
        for p in pending:
            target = owner_target(p, fps, placed)
            if target is None and p.ref == "NT1":           # star point: at the 2S minus pad of J1
                pad = [x for x in fps["J1"].Pads() if x.GetNumber() == "2"][0].GetPosition()
                target = UV(pcbnew.ToMM(pad.x), pcbnew.ToMM(pad.y))
            elif target is None and p.ref.startswith("TP"):  # GND test point: middle of the left strip
                target = (-20.0, 34.0)
            if target is None:
                rest.append(p)
                continue
            region = REF_REGIONS.get(p.ref, REGIONS.get(p.group, region_board))
            fp = fps[p.ref]
            shapes = {}
            for rot in (0, 90):
                set_pose(fp, 0.0, 0.0, rot)
                shapes[rot] = crt_box(fp)
            ok = None
            for du, dv in RINGS:
                u, v = target[0] + du, target[1] + dv
                for rot in (0, 90):
                    b0 = shapes[rot]
                    box = (b0[0] + u, b0[1] + u, b0[2] + v, b0[3] + v)
                    if not inside(box, region) or not inside(box, region_board):
                        continue
                    if p.group != "IMU ICM-42688-P, SPI1" and overlap(box, UNDER_TEENSY):
                        continue
                    gap = 0.2 if p.group.startswith("IMU") or p.ref == "NT1" else 0.35   # routing channels
                    if any(overlap(box, b, gap) for b in placed.values()):
                        continue
                    ok = (u, v, rot, box)
                    break
                if ok:
                    break
            if ok:
                set_pose(fp, ok[0], ok[1], ok[2])
                placed[p.ref] = ok[3]
            else:
                failed.append(p.ref)
        pending = rest
        if not pending:
            break
    return failed + [p.ref for p in pending]


def rect_zone(board, net, layers, box, priority=0, rule=None, name="", solid=False):
    z = pcbnew.ZONE(board)
    ls = pcbnew.LSET()
    for l in layers:
        ls.AddLayer(l)
    z.SetLayerSet(ls)
    if len(box) == 4 and not isinstance(box[0], tuple):
        u0, u1, v0, v1 = box
        box = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    o = z.Outline()
    o.NewOutline()
    for u, v in box:
        p = P(u, v)
        o.Append(p.x, p.y)
    if rule:
        z.SetIsRuleArea(True)
        z.SetDoNotAllowTracks("tracks" in rule)
        z.SetDoNotAllowVias("vias" in rule)
        z.SetDoNotAllowZoneFills("fills" in rule)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
        z.SetZoneName(name)
    else:
        z.SetNetCode(board.GetNetInfo().GetNetItem(net).GetNetCode())
        z.SetAssignedPriority(priority)
        z.SetMinThickness(MM(0.2))
        z.SetLocalClearance(MM(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL if solid else pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(MM(0.3))
        z.SetThermalReliefSpokeWidth(MM(0.4))
        z.SetZoneName(name or net)
    board.Add(z)
    return z


FULL = (-W / 2 + 0.3, W / 2 - 0.3, 0.3, L - 0.3)


# B.Cu is the supply plane (layer type power): GND_PWR under the actuators, 5V_SYS everywhere else.
# GND_PWR reaches the pyro FETs at the nose through a 3.3 mm strip along the right edge and a band
# under the pyro area, so their return runs as plane to the star point (spec §8), not as a long track.
SPLIT_GND_PWR = [(-26.7, 0.3), (26.7, 0.3), (26.7, 119.7), (-14.0, 119.7), (-14.0, 100.0), (23.4, 100.0),
                 (23.4, 57.0), (-9.4, 57.0), (-9.4, 22.0), (-26.7, 22.0)]
SPLIT_5V_SYS = [(-26.7, 22.0), (-9.4, 22.0), (-9.4, 57.0), (23.4, 57.0), (23.4, 100.0), (-14.0, 100.0),
                (-14.0, 119.7), (-26.7, 119.7)]


def add_pours(board):
    """GND pours on F.Cu and In2.Cu - added after routing, so Freerouting sees free signal layers."""
    for layer in (pcbnew.F_Cu, pcbnew.In2_Cu):
        rect_zone(board, "GND", [layer], FULL, name=f"GND {board.GetLayerName(layer)}", solid=True)


def add_zones(board, fps):
    rect_zone(board, "GND", [pcbnew.In1_Cu], FULL, name="GND In1.Cu")     # solid plane (layer type power)
    rect_zone(board, "GND_PWR", [pcbnew.B_Cu], SPLIT_GND_PWR, name="GND_PWR B.Cu")
    rect_zone(board, "5V_SYS", [pcbnew.B_Cu], SPLIT_5V_SYS, name="5V_SYS B.Cu")
    # spec §8: no vias around the IMU on any layer, no tracks under it on the inner and back layers
    rect_zone(board, None, [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu], (-1.9, 1.9, 59.0, 62.0),
              rule={"vias"}, name="IMU ohne Vias")
    rect_zone(board, None, [pcbnew.In2_Cu], (-2.4, 2.4, 58.5, 62.5), rule={"tracks"},
              name="IMU ruhige Masse")
    # spec §8: LoRa module on a ground plane, no signals underneath (pads sit at its long edges)
    b = crt_box(fps["U10"])
    inner = (b[0] + 2.6, b[1] - 2.6, b[2] + 1.5, b[3] - 1.5)
    rect_zone(board, None, [pcbnew.F_Cu, pcbnew.In2_Cu], inner, rule={"tracks", "vias"}, name="LoRa ohne Signale")


class Courtyard:
    """Courtyard outline for the free-space test: round parts leave their bounding-box corners free.
    A courtyard in several pieces (the Teensy: one per pin row) counts as its bounding box, the body
    spans the gap."""

    def __init__(self, poly):
        self.poly, self.bbox = poly, poly.BBox()
        self.solid = poly.OutlineCount() > 1
        self.pts = []
        for i in range(poly.OutlineCount()):
            c = poly.COutline(i)
            n = c.PointCount()
            for k in range(n):
                a, b = c.CPoint(k), c.CPoint((k + 1) % n)
                steps = max(1, int(math.hypot(b.x - a.x, b.y - a.y) / MM(0.2)))
                self.pts += [pcbnew.VECTOR2I(int(a.x + (b.x - a.x) * j / steps), int(a.y + (b.y - a.y) * j / steps))
                             for j in range(steps)]

    def Intersects(self, box):
        if not self.bbox.Intersects(box):
            return False
        if self.solid or any(box.Contains(q) for q in self.pts):
            return True
        x0, x1, y0, y1 = box.GetLeft(), box.GetRight(), box.GetTop(), box.GetBottom()
        probe = [(x0, y0), (x1, y0), (x0, y1), (x1, y1), ((x0 + x1) // 2, (y0 + y1) // 2)]
        return any(self.poly.Contains(pcbnew.VECTOR2I(int(x), int(y))) for x, y in probe)


class Silk:
    """Free-space bookkeeping for one silkscreen side: text and logos go only where they keep clear of
    exposed copper (pads in the mask layer), footprint outlines, other parts' courtyards, the board
    edge and what is already placed. Vias are tented on both sides and may be printed over."""

    def __init__(self, board, fps, back=False):
        self.board, self.back = board, back
        self.layer = pcbnew.B_SilkS if back else pcbnew.F_SilkS
        mask = pcbnew.B_Mask if back else pcbnew.F_Mask
        self.pads = [p for fp in fps.values() for p in fp.Pads() if p.IsOnLayer(mask)]
        self.lines = [g for fp in fps.values() for g in fp.GraphicalItems()
                      if g.GetLayer() == self.layer and not isinstance(g, pcbnew.PCB_TEXT)]
        self.court = {} if back else {r: Courtyard(fp.GetCourtyard(pcbnew.F_CrtYd)) for r, fp in fps.items()
                                      if fp.GetCourtyard(pcbnew.F_CrtYd).OutlineCount()}
        # drilled pads mark the back even without a mask opening there (thermal vias in pads)
        self.holes = [(p.GetPosition(), p.GetDrillSize().x / 2) for fp in fps.values() for p in fp.Pads()
                      if back and p.GetDrillSize().x > 0]
        (x0, y0), (x1, y1) = XY(-W / 2 + 0.5, L - 0.5), XY(W / 2 - 0.5, 0.5)
        self.edge = pcbnew.BOX2I(pcbnew.VECTOR2I(MM(x0), MM(y0)), pcbnew.VECTOR2L(MM(x1 - x0), MM(y1 - y0)))
        self.taken = []

    def free(self, box, own=None, courtyards=True, under=()):
        if not self.edge.Contains(box):
            return False
        grown = pcbnew.BOX2I(box.GetPosition(), box.GetSize())
        grown.Inflate(MM(0.2))
        if any(grown.Intersects(t) for t in self.taken):
            return False
        if any(p.HitTest(box, False, MM(0.15)) for p in self.pads):
            return False
        if any(g.HitTest(box, False, MM(0.12)) for g in self.lines):
            return False
        if any(math.hypot(max(grown.GetLeft() - c.x, 0, c.x - grown.GetRight()),
                          max(grown.GetTop() - c.y, 0, c.y - grown.GetBottom())) < r for c, r in self.holes):
            return False
        return not courtyards or not any(r != own and r not in under and c.Intersects(box)
                                         for r, c in self.court.items())

    def text(self, s, size=SILK_H, bold=False):
        t = pcbnew.PCB_TEXT(self.board)
        t.SetText(s)
        t.SetLayer(self.layer)
        t.SetMirrored(self.back)
        style(t, size, bold)
        return t

    def put(self, t, candidates, own=None, under=()):
        """Try (x, y, angle) in mm until the text fits; keep it there. False if none fits."""
        for x, y, a in candidates:
            t.SetTextAngleDegrees(a)
            t.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
            box = t.GetBoundingBox()
            if self.free(box, own, under=under):
                self.taken.append(box)
                return True
        return False

    def around(self, t, box, gaps=(0.2, 0.6, 1.1)):
        """Candidate spots around a courtyard box: above and below first, then the sides (level, then
        upright), each centred, flush with a corner and past it; big parts also in their middle."""
        t.SetTextAngleDegrees(0)
        tb = t.GetBoundingBox()
        w, h = pcbnew.ToMM(tb.GetWidth()), pcbnew.ToMM(tb.GetHeight())
        x0, y0 = pcbnew.ToMM(box.GetLeft()), pcbnew.ToMM(box.GetTop())
        x1, y1 = pcbnew.ToMM(box.GetRight()), pcbnew.ToMM(box.GetBottom())
        cx, cy, bw, bh = (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0
        out = []
        for g in gaps:
            for dx in (0, -(bw - w) / 2, (bw - w) / 2, -(bw + w) / 2, (bw + w) / 2):
                out += [(cx + dx, y0 - g - h / 2, 0), (cx + dx, y1 + g + h / 2, 0)]
            for dy in (0, -(bh - h) / 2, (bh - h) / 2):
                out += [(x0 - g - w / 2, cy + dy, 0), (x1 + g + w / 2, cy + dy, 0)]
            for dy in (0, -(bh - w) / 2, (bh - w) / 2):
                out += [(x0 - g - h / 2, cy + dy, 90), (x1 + g + h / 2, cy + dy, 90)]
        if bw * bh > 150:
            out.append((cx, cy, 0))
        return out

    def scan(self, w, h, step=0.5):
        """Centres (u, v) of free w x h boxes, scanned over the board."""
        n_u, n_v = int((W - w) / step), int((L - h) / step)
        for i in range(n_v + 1):
            for j in range(n_u + 1):
                u, v = -W / 2 + w / 2 + j * step, h / 2 + i * step
                x, y = XY(u, v)
                box = pcbnew.BOX2I(pcbnew.VECTOR2I(MM(x - w / 2), MM(y - h / 2)), pcbnew.VECTOR2L(MM(w), MM(h)))
                if self.free(box):
                    yield u, v, box


def style(t, size=SILK_H, bold=False):
    t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
    t.SetTextThickness(MM(max(SILK_T, size * (0.2 if bold else 0.15))))
    t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
    t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    t.SetKeepUpright(False)


def set_stackup(path=PCB):
    """JLC 4-layer stackup JLC04161H-7628 with the solder mask colour; pcbnew keeps it once it is in the file."""
    s = path.read_text(encoding="utf-8")
    if "(stackup" in s:
        s = s.replace('(color "Green")', f'(color "{MASK_COLOR}")').replace('(color "Blue")', f'(color "{MASK_COLOR}")')
    else:
        mask = f'(color "{MASK_COLOR}")'
        diel = '(material "FR4") (epsilon_r 4.4) (loss_tangent 0.02)'
        stack = (
            '\t\t(stackup\n'
            '\t\t\t(layer "F.SilkS" (type "Top Silk Screen") (color "White"))\n'
            '\t\t\t(layer "F.Paste" (type "Top Solder Paste"))\n'
            f'\t\t\t(layer "F.Mask" (type "Top Solder Mask") {mask} (thickness 0.01))\n'
            '\t\t\t(layer "F.Cu" (type "copper") (thickness 0.035))\n'
            f'\t\t\t(layer "dielectric 1" (type "prepreg") (thickness 0.2104) {diel})\n'
            '\t\t\t(layer "In1.Cu" (type "copper") (thickness 0.0152))\n'
            f'\t\t\t(layer "dielectric 2" (type "core") (thickness 1.065) {diel})\n'
            '\t\t\t(layer "In2.Cu" (type "copper") (thickness 0.0152))\n'
            f'\t\t\t(layer "dielectric 3" (type "prepreg") (thickness 0.2104) {diel})\n'
            '\t\t\t(layer "B.Cu" (type "copper") (thickness 0.035))\n'
            f'\t\t\t(layer "B.Mask" (type "Bottom Solder Mask") {mask} (thickness 0.01))\n'
            '\t\t\t(layer "B.Paste" (type "Bottom Solder Paste"))\n'
            '\t\t\t(layer "B.SilkS" (type "Bottom Silk Screen") (color "White"))\n'
            '\t\t\t(copper_finish "ENIG")\n\t\t\t(dielectric_constraints no)\n\t\t)\n')
        s = s.replace("\t(setup\n", "\t(setup\n" + stack, 1)
    path.write_text(s, encoding="utf-8")


def add_silk(board, fps):
    """All silkscreen of the board; returns the references that found no free spot (moved to F.Fab)."""
    import logo
    front, back = Silk(board, fps), Silk(board, fps, back=True)
    lost = []

    # fixed items under the Teensy (visible with the Teensy pulled from its sockets)
    def fixed(s, u, v, size=SILK_H):
        t = front.text(s, size)
        t.SetPosition(P(u, v))
        board.Add(t)
        front.taken.append(t.GetBoundingBox())
    fixed("JLCJLCJLCJLC", 0.0, 80.0)                      # JLC order number
    # IMU axes (spec §2): X across (+u), Y toward the nose (+v), Z out of the board
    for (a, b_), lab in zip((((2.2, 60.5), (5.2, 60.5)), ((0.0, 62.7), (0.0, 65.7))), ("X", "Y")):
        for start, end in [(a, b_)] + [(b_, (b_[0] - 0.7, b_[1] + 0.5 * d) if lab == "X" else (b_[0] + 0.5 * d, b_[1] - 0.7))
                                       for d in (-1, 1)]:
            s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(P(*start))
            s.SetEnd(P(*end))
            s.SetLayer(pcbnew.F_SilkS)
            s.SetWidth(MM(SILK_T))
            board.Add(s)
    fixed("X", 4.6, 61.6, 0.8)
    fixed("Y", -1.0, 66.0, 0.8)
    fixed("IMU Z+", -3.6, 64.3, 0.8)

    # front: connector names, then designators of the parts one has to find (no passives)
    for ref, label in LABELS.items():
        fps[ref].Reference().SetLayer(pcbnew.F_Fab)
        t = front.text(label)
        if front.put(t, front.around(t, fps[ref].GetCourtyard(pcbnew.F_CrtYd).BBox()), own=ref):
            board.Add(t)
        else:
            lost.append(ref)
    for ref, fp in sorted(fps.items(), key=lambda kv: -kv[1].GetArea()):
        f = fp.Reference()
        if ref in LABELS:
            continue
        if ref.startswith(("H", "NT", "TP")) or passive(ref):
            f.SetLayer(pcbnew.F_Fab)
            continue
        f.SetLayer(pcbnew.F_SilkS)
        style(f)
        under = ("A1",) if ref == "U4" else ()           # the IMU sits under the Teensy
        if not front.put(f, front.around(f, fp.GetCourtyard(pcbnew.F_CrtYd).BBox()), own=ref, under=under):
            f.SetLayer(pcbnew.F_Fab)
            lost.append(ref)
    for ref, fp in fps.items():                            # test points by their net
        if ref.startswith("TP"):
            t = front.text(TP_LABELS[fp.GetValue()], 0.9)
            if front.put(t, front.around(t, fp.GetCourtyard(pcbnew.F_CrtYd).BBox(), gaps=(0.15, 0.5)), own=ref):
                board.Add(t)
            else:
                lost.append(ref)

    # front logo: small patch without lettering, name and revision beside it
    mark_d = 6.0
    for block_w, block_h in ((19.0, 6.4), (6.4, 6.4)):      # mark with name and revision, else the mark
        spot = next(front.scan(block_w, block_h), None)
        if not spot:
            continue
        u, v, box = spot
        x, y = XY(u - block_w / 2 + mark_d / 2 + 0.2, v)
        logo.Patch(x, y, mark_d).shapes(board, pcbnew.F_SilkS)
        if block_w > block_h:
            for s, dv, size, bold in ((NAME, 1.2, 1.4, True), (f"{REV[10:]} · 2026-10", -1.3, SILK_H, False)):
                t = front.text(s, size, bold)
                t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
                t.SetPosition(P(u - block_w / 2 + mark_d + 1.0, v + dv))
                board.Add(t)
        front.taken.append(box)
        break
    else:
        lost.append("front logo")

    # back: big patch, then the pin-out as one block (two if one does not fit)
    for d in (20.0, 18.0, 16.0):
        spot = next(back.scan(d, d + 3.0), None)
        if spot:
            u, v, box = spot
            x, y = XY(u, v + 1.5)
            logo.Patch(x, y, d, NAME, REV, mirror=True).shapes(board, pcbnew.B_SilkS)
            t = back.text("2026-10")
            t.SetPosition(P(u, v + 1.5 - d / 2 - 1.3))
            board.Add(t)
            back.taken.append(box)
            break
    else:
        lost.append("back logo")

    pins = {p.ref: p.pins for p in circuit.PARTS}
    for ref, words in PINOUT.items():
        assert ref == "J15" or len(words.split()) == len(pins[ref]), (ref, words, pins[ref])
    # two lines per connector (name, then its pins indented), as one block or split in two or three
    rows = [(f"{r} {LABELS[r]}", w) for r, w in PINOUT.items()]
    head = ("STECKER", "PIN 1 ZUERST")
    pitch, bw = 1.6, 15.5
    placed = []
    for blocks in ([rows], [rows[:8], rows[8:]], [rows[:5], rows[5:10], rows[10:]]):
        blocks = [[head] + blocks[0]] + blocks[1:]
        n0 = len(back.taken)
        for blk in blocks:
            bh = pitch * 2 * len(blk) + 0.6
            spot = next(back.scan(bw, bh), None)
            if not spot:
                break
            placed.append((blk, spot, bh))
            back.taken.append(spot[2])
        if len(placed) == len(blocks):
            break
        del back.taken[n0:]
        placed = []
    if not placed:
        lost.append("pin-out")
    for blk, (u, v, _), bh in placed:
        for k, (a, b_) in enumerate(blk):
            for line, (s, du) in enumerate(((a, 0.0), (b_, 1.5))):
                t = back.text(s, SILK_H, bold=line == 0)
                t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)   # KiCad mirrors the justification with the text
                t.SetPosition(P(u + bw / 2 - du, v + bh / 2 - 0.3 - pitch * (2 * k + line + 0.5)))
                board.Add(t)
    return lost


def relabel():
    """Silkscreen only, on the routed board: placement, tracks and zones stay as they are."""
    board = pcbnew.LoadBoard(str(PCB))
    old = [d for d in board.Drawings() if d.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS)]
    for d in old:                                          # start over; Delete, not Remove: a removed
        board.Delete(d)                                    # item freed by Python corrupts the board
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    lost = add_silk(board, fps)
    pcbnew.SaveBoard(str(PCB), board, True)
    set_stackup()
    print("silkscreen placed" + (f", no free spot (on F.Fab): {lost}" if lost else ""))


def in_poly(u, v, poly):
    inside_ = False
    for (u0, v0), (u1, v1) in zip(poly, poly[1:] + poly[:1]):
        if (v0 > v) != (v1 > v) and u < u0 + (v - v0) * (u1 - u0) / (v1 - v0):
            inside_ = not inside_
    return inside_


def add_plane_vias(board, fps):
    """One via to its plane next to every SMD pad of a plane net (decoupling return, router relief):
    GND to In1 everywhere, GND_PWR and 5V_SYS to B.Cu where the pad lies over its part of the split.

    Candidates around the pad in eight directions; a via is set where it keeps 0.2 mm from every
    pad and via of another net, stays off the board edge and out of the IMU and LoRa keepouts, and
    its 0.3 mm stub to the pad does not pass another net's pad."""
    planes = {"GND": None, "GND_PWR": SPLIT_GND_PWR, "5V_SYS": SPLIT_5V_SYS}
    netitem = {n: board.GetNetInfo().GetNetItem(n) for n in planes}
    via_r, clear = 0.3, 0.2
    pads = [(pad, pad.GetBoundingBox()) for fp in fps.values() for pad in fp.Pads()]
    vias = []
    no_via = [(-1.9, 1.9, 59.0, 62.0)]
    b = crt_box(fps["U10"])
    no_via.append((b[0] + 2.6, b[1] - 2.6, b[2] + 1.5, b[3] - 1.5))

    def rect_dist(x, y, bb):
        x0, x1 = pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetRight())
        y0, y1 = pcbnew.ToMM(bb.GetTop()), pcbnew.ToMM(bb.GetBottom())
        dx = max(x0 - x, 0, x - x1)
        dy = max(y0 - y, 0, y - y1)
        return math.hypot(dx, dy)

    def free(x, y, own, net):
        u, v = UV(x, y)
        if abs(u) > W / 2 - 1.0 or v < 1.0 or v > L - 1.0:
            return False
        if any(r[0] - 0.3 < u < r[1] + 0.3 and r[2] - 0.3 < v < r[3] + 0.3 for r in no_via):
            return False
        for pad, bb in pads:
            if pad is own:
                continue
            same = pad.GetNetname() == net
            if rect_dist(x, y, bb) < via_r + (0.05 if same else clear):
                return False
        return all(math.hypot(x - vx, y - vy) >= 2 * via_r + clear for vx, vy in vias)

    def stub_free(x0, y0, x1, y1, own, net):
        for k in range(1, 6):
            x, y = x0 + (x1 - x0) * k / 6, y0 + (y1 - y0) * k / 6
            for pad, bb in pads:
                if pad is not own and pad.GetNetname() != net and rect_dist(x, y, bb) < 0.15 + clear:
                    return False
        return True

    n = 0
    for fp in fps.values():
        for pad in fp.Pads():
            net = pad.GetNetname()
            if net not in planes or pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                continue
            c = pad.GetPosition()
            cx, cy = pcbnew.ToMM(c.x), pcbnew.ToMM(c.y)
            if planes[net] and not in_poly(*UV(cx, cy), planes[net]):
                continue
            bb = pad.GetBoundingBox()
            half = max(pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())) / 2
            done = False
            for dist in (half + 0.55, half + 0.9, half + 1.4):
                for ang in range(0, 360, 45):
                    x = cx + dist * math.cos(math.radians(ang))
                    y = cy + dist * math.sin(math.radians(ang))
                    if planes[net] and not all(in_poly(*UV(x + dx, y + dy), planes[net])
                                               for dx in (-0.5, 0, 0.5) for dy in (-0.5, 0, 0.5)):
                        continue        # the via itself must sit over its own part of the split
                    if free(x, y, pad, net) and stub_free(cx, cy, x, y, pad, net):
                        v = pcbnew.PCB_VIA(board)
                        v.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
                        v.SetWidth(MM(2 * via_r))
                        v.SetDrill(MM(0.3))
                        v.SetNet(netitem[net])
                        board.Add(v)
                        tr = pcbnew.PCB_TRACK(board)
                        tr.SetStart(c)
                        tr.SetEnd(pcbnew.VECTOR2I(MM(x), MM(y)))
                        tr.SetWidth(MM(0.3))
                        tr.SetLayer(pad.GetLayer() if pad.IsOnLayer(pcbnew.F_Cu) else pcbnew.F_Cu)
                        tr.SetNet(netitem[net])
                        board.Add(tr)
                        vias.append((x, y))
                        n += 1
                        done = True
                        break
                if done:
                    break
    return n


def build():
    board = new_board()
    draw_outline(board)
    fps = add_footprints(board)
    placed, clash = place_fixed(board, fps)
    failed = place_passives(fps, placed)
    add_zones(board, fps)
    nvias = add_plane_vias(board, fps)
    print(f"{nvias} plane vias next to SMD pads of GND, GND_PWR, 5V_SYS")
    lost = add_silk(board, fps)
    pcbnew.SaveBoard(str(PCB), board, True)
    set_stackup()
    fix_model_paths()
    print(f"placed {len(placed) - 1} of {len(fps)} footprints")
    if clash:
        print("fixed parts colliding:", clash)
    if failed:
        print("no place found for:", failed)
    if lost:
        print("silkscreen without a free spot (on F.Fab):", lost)
    return board


def export_dsn(tag=""):
    board = pcbnew.LoadBoard(str(PCB))
    board.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER)
    board.SetLayerType(pcbnew.B_Cu, pcbnew.LT_POWER)
    out = HERE / "out" / f"mainboard{tag}.dsn"
    out.parent.mkdir(exist_ok=True)
    ok = pcbnew.ExportSpecctraDSN(board, str(out))
    print("dsn", ok, out)


def import_ses(tag=""):
    board = pcbnew.LoadBoard(str(PCB))
    has_pours = any(z.GetZoneName() == "GND F.Cu" for z in board.Zones())   # from an earlier pass
    ok = pcbnew.ImportSpecctraSES(board, str(HERE / "out" / f"mainboard{tag}.ses"))  # tag: variant
    if not has_pours:
        add_pours(board)
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    pcbnew.SaveBoard(str(PCB), board, True)
    print("ses imported", ok, "tracks", len(board.GetTracks()))


def merge_ses(tag="_fix"):
    """Add the tracks of a session that routed only the remaining connections (existing wiring was
    exported as fixed) to the board, keeping what is there."""
    board = pcbnew.LoadBoard(str(PCB))
    other = pcbnew.LoadBoard(str(PCB))
    pcbnew.ImportSpecctraSES(other, str(HERE / "out" / f"mainboard{tag}.ses"))
    have = {(t.GetClass(), t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y, t.GetLayer())
            for t in board.GetTracks()}
    n = 0
    for t in other.GetTracks():
        key = (t.GetClass(), t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y, t.GetLayer())
        if key in have:
            continue
        net = board.GetNetInfo().GetNetItem(t.GetNetname())
        if t.GetClass() == "PCB_VIA":
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(t.GetPosition()), v.SetWidth(t.GetWidth(pcbnew.F_Cu)), v.SetDrill(t.GetDrill())
            v.SetNet(net)
            board.Add(v)
        else:
            nt = pcbnew.PCB_TRACK(board)
            nt.SetStart(t.GetStart()), nt.SetEnd(t.GetEnd()), nt.SetLayer(t.GetLayer()), nt.SetWidth(t.GetWidth())
            nt.SetNet(net)
            board.Add(nt)
        n += 1
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(str(PCB), board, True)
    print(f"{n} tracks and vias added from the finishing pass")


def patch_unconnected():
    """Close what Freerouting left open (track ends a little short of their pad, out/drc.json).

    For every unconnected pair the nearest ends are joined by a straight 0.2 mm track on a copper
    layer both ends reach; if the ends sit on different layers, a via goes at the track end. Every
    candidate is checked against all copper of other nets (0.13 mm); only collision-free ones are set.
    The DRC run afterwards confirms the result."""
    import json
    board = pcbnew.LoadBoard(str(PCB))
    d = json.loads((HERE / "out" / "drc.json").read_text(encoding="utf-8"))
    copper = [pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
    width, clear = MM(0.15), MM(0.13)    # board minimum (JLC 4 layers): 0.127 mm
    others = list(board.GetTracks()) + [p for fp in board.GetFootprints() for p in fp.Pads()]

    def free(shape, layer, net):
        for it in others:
            if it.GetNetCode() == net or not it.IsOnLayer(layer):
                continue
            if it.GetEffectiveShape(layer).Collide(shape, clear):
                return False
        return True

    def reach(it):
        """(position, layers) of the connectable ends of an item."""
        if it.GetClass() in ("PCB_TRACK", "PCB_ARC"):
            return [(it.GetStart(), [it.GetLayer()]), (it.GetEnd(), [it.GetLayer()])]
        if it.GetClass() == "PCB_VIA":
            return [(it.GetPosition(), copper)]
        return [(it.GetPosition(), copper if it.GetAttribute() == pcbnew.PAD_ATTRIB_PTH else [pcbnew.F_Cu])]

    done, failed = 0, []
    for u in d["unconnected_items"]:
        items = [board.ResolveItem(pcbnew.KIID(i["uuid"])) for i in u["items"]]
        if any(i is None for i in items):
            continue
        items = [i.Cast() for i in items]
        net = items[0].GetNetCode()
        pairs = sorted(((a, b) for a in reach(items[0]) for b in reach(items[1])),
                       key=lambda ab: (ab[0][0] - ab[1][0]).EuclideanNorm())
        placed = False
        for (pa, la), (pb, lb) in pairs:
            for layer in [l for l in copper if l in la and l in lb]:      # same layer: one segment
                seg = pcbnew.SHAPE_SEGMENT(pa, pb, width)
                if free(seg, layer, net):
                    tr = pcbnew.PCB_TRACK(board)
                    tr.SetStart(pa), tr.SetEnd(pb), tr.SetLayer(layer), tr.SetWidth(width), tr.SetNetCode(net)
                    board.Add(tr)
                    others.append(tr)
                    placed = True
                    break
            if placed:
                break
            # different layers: via at the end that is a track end, stub on the other end's layer
            for (pv, lv), (pp, lp) in (((pa, la), (pb, lb)), ((pb, lb), (pa, la))):
                if len(lv) != 1:
                    continue
                via_shape = pcbnew.SHAPE_CIRCLE(pv, MM(0.3))
                if not all(free(via_shape, l, net) for l in copper + [pcbnew.In1_Cu] if l != pcbnew.In1_Cu):
                    continue
                for layer in lp:
                    seg = pcbnew.SHAPE_SEGMENT(pv, pp, width)
                    if free(seg, layer, net):
                        v = pcbnew.PCB_VIA(board)
                        v.SetPosition(pv), v.SetWidth(MM(0.6)), v.SetDrill(MM(0.3)), v.SetNetCode(net)
                        board.Add(v)
                        tr = pcbnew.PCB_TRACK(board)
                        tr.SetStart(pv), tr.SetEnd(pp), tr.SetLayer(layer), tr.SetWidth(width), tr.SetNetCode(net)
                        board.Add(tr)
                        others += [v, tr]
                        placed = True
                        break
                if placed:
                    break
            if placed:
                break
        if not placed:      # fine-pitch pad: leave it along its long axis, away from the IC, then dogleg
            pad = next((i for i in items if i.GetClass() == "PAD" and i.GetAttribute() == pcbnew.PAD_ATTRIB_SMD), None)
            end = next((i for i in items if i is not pad), None)
            if pad is not None and end is not None:
                c = pad.GetPosition()
                fc = pad.GetParentFootprint().GetPosition()
                bb = pad.GetBoundingBox()
                horiz = bb.GetWidth() >= bb.GetHeight()
                half = (bb.GetWidth() if horiz else bb.GetHeight()) / 2
                sign = 1 if ((c.x - fc.x) if horiz else (c.y - fc.y)) >= 0 else -1
                for extra in (0.25, 0.5, 0.8, 1.2):
                    d = int(half + MM(extra)) * sign
                    esc = pcbnew.VECTOR2I(c.x + d, c.y) if horiz else pcbnew.VECTOR2I(c.x, c.y + d)
                    for (pe, le) in reach(end):
                        if pcbnew.F_Cu not in le:
                            continue
                        for mid in (pcbnew.VECTOR2I(esc.x, pe.y), pcbnew.VECTOR2I(pe.x, esc.y), esc):
                            segs = [(c, esc), (esc, mid), (mid, pe)]
                            segs = [(a, b) for a, b in segs if a != b]
                            if all(free(pcbnew.SHAPE_SEGMENT(a, b, width), pcbnew.F_Cu, net) for a, b in segs):
                                for a, b in segs:
                                    tr = pcbnew.PCB_TRACK(board)
                                    tr.SetStart(a), tr.SetEnd(b), tr.SetLayer(pcbnew.F_Cu), tr.SetWidth(width)
                                    tr.SetNetCode(net)
                                    board.Add(tr)
                                    others.append(tr)
                                placed = True
                                break
                        if placed:
                            break
                    if placed:
                        break
        if placed:
            done += 1
        else:
            failed.append(board.GetNetInfo().GetNetItem(net).GetNetname())
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(str(PCB), board, True)
    print(f"{done} open connections patched" + (f", not possible: {failed}" if failed else ""))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "place"
    tag = sys.argv[2] if len(sys.argv) > 2 else ""
    if cmd == "place":
        build()
    elif cmd == "silk":
        relabel()
    else:
        {"dsn": export_dsn, "ses": import_ses, "merge": merge_ses, "patch": lambda _: patch_unconnected()}[cmd](tag)
