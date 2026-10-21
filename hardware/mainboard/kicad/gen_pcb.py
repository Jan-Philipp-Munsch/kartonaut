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
from gen_schematic import uid       # noqa: E402

KICAD = Path(os.environ.get("KICAD10_DIR", Path.home() / "AppData/Local/Programs/KiCad/10.0"))
STD_FP = KICAD / "share/kicad/footprints"
PCB = HERE / "mainboard.kicad_pcb"
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
    "J3": (-21.0, 18.0, 0),         # J_SW, PH-4 top entry
    "J2": (-21.0, 25.5, 0),         # J_BAT1, PH-2 top entry
    "R_SH1": (-17.0, 33.0, 90),     # shunt, along the strip
    "U6": (-12.5, 33.5, 0),         # INA219 next to the shunt (Kelvin taps short)
    "U2": (-16.5, 46.0, 0),         # buck-boost, >= 25 mm from the IMU
    "L2": (-22.0, 46.0, 90),
    "C19": (-19.5, 54.5, 0),        # 1000 uF polymer at 5V_SYS
    "U10": (-17.0, 76.5, 180),      # LoRa module, pads 11-13 (ANT side) toward the nose
    "U3": (-13.5, 92.0, 0),         # LDO 3V3_RF above the module
    "C3": (0.0, 18.0, 0),           # 1000 uF at VSERVO, between the servo connectors' cables
    "J7": (10.0, 18.0, 0),          # chute servo, XH-3 top entry
    "J8": (20.5, 18.0, 0),          # roll motor, PH-2 top entry
    "U1": (17.0, 31.0, 0),          # 5V_SERVO buck in the right strip
    "L1": (22.0, 36.0, 90),
    "C11": (14.5, 40.0, 0),         # 470 uF at 5V_SERVO
    "U7": (19.5, 47.0, 90),         # DRV8833
    "U8": (13.5, 60.0, 0),
    "U9": (13.5, 66.0, 0),
    "LED1": (22.0, 60.0, 0),
    "LED2": (22.0, 66.0, 0),
    "J15": (12.0, 90.0, 0),         # J_EXP 2x7, rows along v
    "J12": (21.0, 75.0, 0),         # Qwiic, top entry
    "U5": (21.5, 85.0, 0),          # BMP390, far from coils and CPU
    "BZ1": (13.0, 98.0, 0),         # buzzer, 12 mm, |u| < 25
    "J11": (-17.0, 98.0, 0),        # GPS, GH-4 top entry
    "J13": (-17.0, 104.0, 0),       # camera, GH-3 top entry
    "J14": (-17.0, 110.0, 0),       # external LEDs, GH-3 top entry
    "NT1": (-9.0, 16.5, 90),        # star point next to the 2S minus pad of J1
}
EDGE = {  # ref: (edge, u of the footprint origin, rot) - the courtyard is moved flush with that edge
    "J1": ("bottom", -16.7, 180),   # XT30PW-M, mouth toward the TVC end
    "J5": ("bottom", -3.0, 0),      # servo yaw, XH-3 side entry
    "J6": ("bottom", 9.0, 0),       # servo pitch
    "J4": ("top", -6.0, 180),       # arming switch, PH-2 side entry, toward the nose
    "J10": ("top", 3.0, 180),       # pyro 2
    "J9": ("top", 13.5, 180),       # pyro 1
}
HOLES = {f"H{i + 1}": xy for i, xy in enumerate(outline.HOLES)}

# Regions for the passives of each schematic block (u0, u1, v0, v1)
REGIONS = {
    "2S: Akku, Verpolschutz, Hauptschalter": (-25.0, -2.0, 4.0, 30.0),
    "2S: Spannungsmessung und Strommessung INA219": (-25.5, -9.5, 26.0, 40.0),
    "2S: Servo-Schiene VSERVO": (-8.0, 8.0, 12.0, 30.0),
    "2S: Buck U1 -> 5V_SERVO": (9.5, 25.5, 22.0, 44.0),
    "1S: Akku, Verpolschutz, Spannungsmessung": (-25.5, -9.5, 20.0, 40.0),
    "1S: Buck-Boost U2 -> 5V_SYS, Teensy-VIN": (-25.5, -9.5, 38.0, 62.0),
    "LDO U3 -> 3V3_RF, Sternpunkt, Testpunkte": (-25.5, -9.5, 88.0, 96.0),
    "Teensy 4.1": (-25.5, 25.5, 0.0, 120.0),
    "Erweiterung, Befestigung, Testpunkte": (9.5, 25.5, 50.0, 95.0),
    "IMU ICM-42688-P, SPI1": (-6.0, 6.0, 48.0, 73.0),
    "Barometer BMP390 und I2C": (9.5, 25.5, 70.0, 92.0),
    "LoRa E22-400T22S, Serial8": (-25.5, -9.5, 58.0, 96.0),
    "GPS, Serial1": (-25.5, -9.5, 92.0, 115.0),
    "Servos": (-8.0, 25.5, 10.0, 30.0),
    "Rollmotor DRV8833": (9.5, 25.5, 38.0, 56.0),
    "Arming": (-12.0, 8.0, 103.0, 112.0),
    "Pyro-Kanal 1": (-12.0, 25.0, 92.0, 112.0),
    "Pyro-Kanal 2": (-12.0, 25.0, 92.0, 112.0),
    "Status-LEDs": (9.5, 25.5, 54.0, 72.0),
    "Summer": (5.0, 25.0, 88.0, 108.0),
    "Kamera": (-25.5, -9.5, 96.0, 112.0),
}
# Test points: (u, v) along the strips, reachable with probes when the Teensy is plugged in
TESTPOINTS = {"TP1": (-24.0, 30.0), "TP2": (-24.0, 38.0), "TP3": (-24.0, 60.0), "TP4": (-6.0, 26.0),
              "TP5": (24.0, 44.0), "TP6": (-24.0, 93.5), "TP7": (-10.5, 26.0), "TP8": (24.5, 52.0),
              "TP9": (24.5, 55.5)}
KEEPOUTS = [(u0, u1, v0, v1) for _, u0, u1, v0, v1 in outline.KEEPOUTS]          # SD and USB plug
UNDER_TEENSY = (-6.1, 6.1, 30.0, 91.0)          # only parts up to 3 mm high, i.e. the IMU block
LABELS = {  # silkscreen next to connectors
    "J1": "2S + -", "J2": "1S", "J3": "SW 1S 1S 2S 2S", "J4": "ARM", "J5": "YAW S+-", "J6": "PITCH S+-",
    "J7": "CHUTE S+-", "J8": "MOT", "J9": "PYRO1", "J10": "PYRO2", "J11": "GPS", "J12": "QWIIC",
    "J13": "CAM", "J14": "LED", "J15": "EXP",
}


# ---------------------------------------------------------------- helpers
def fp_dir(lib):
    return HERE / "lib" / f"{lib}.pretty" if lib in ("mainboard", "lcsc") else STD_FP / f"{lib}.pretty"


def load_fp(fpid):
    lib, name = fpid.split(":")
    fp = pcbnew.FootprintLoad(str(fp_dir(lib)), name)
    assert fp, fpid
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


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
        attrs = fp.GetAttributes()
        if p.ref.startswith(("TP", "H", "NT", "JP")):
            attrs |= pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES
        fp.SetAttributes(attrs)
        for pad in fp.Pads():
            net = p.pins.get(pad.GetNumber())
            if net:
                pad.SetNet(netinfo[net])
        if p.lib.startswith(("Device:R", "Device:C", "Device:L", "Device:D", "Connector:TestPoint")) and p.ref not in ("R_SH1",):
            fp.Reference().SetLayer(pcbnew.F_Fab)          # passives: designator on the assembly drawing only
        else:
            fp.Reference().SetTextSize(pcbnew.VECTOR2I(MM(0.8), MM(0.8)))
            fp.Reference().SetTextThickness(MM(0.12))
        fp.Value().SetLayer(pcbnew.F_Fab)
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
    for ref, (u, v) in HOLES.items():
        set_pose(fps[ref], u, v, 0)
        placed[ref] = (u - 3.0, u + 3.0, v - 3.0, v + 3.0)
    for ref, (u, v) in TESTPOINTS.items():
        set_pose(fps[ref], u, v, 0)
        placed[ref] = crt_box(fps[ref])
    # report collisions between fixed parts (the Teensy courtyard covers only the socket strips)
    refs = list(placed)
    clash = [(a, b) for i, a in enumerate(refs) for b in refs[i + 1:]
             if overlap(placed[a], placed[b]) and {a, b} != {"A1", "U4"}]
    return placed, clash


def owner_target(p, fps, placed):
    """Where a passive wants to sit: at the pad of an already placed part sharing a signal net."""
    best = None
    for net in p.pins.values():
        if not net or net in ("GND", "GND_PWR"):
            continue
        for q in circuit.PARTS:
            if q.ref == p.ref or q.ref not in placed:
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
    pending = [p for p in circuit.PARTS if p.ref not in placed]
    for _ in range(3):                      # owners may themselves be passives placed later
        rest = []
        for p in pending:
            target = owner_target(p, fps, placed)
            if target is None:
                rest.append(p)
                continue
            region = REGIONS.get(p.group, region_board)
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
                    if any(overlap(box, k) for k in KEEPOUTS):
                        continue
                    if any(overlap(box, b, 0.15) for b in placed.values()):
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


def rect_zone(board, net, layers, box, priority=0, rule=None, name=""):
    z = pcbnew.ZONE(board)
    ls = pcbnew.LSET()
    for l in layers:
        ls.AddLayer(l)
    z.SetLayerSet(ls)
    u0, u1, v0, v1 = box
    o = z.Outline()
    o.NewOutline()
    for u, v in ((u0, v0), (u1, v0), (u1, v1), (u0, v1)):
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
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(MM(0.3))
        z.SetThermalReliefSpokeWidth(MM(0.4))
        z.SetZoneName(name or net)
    board.Add(z)
    return z


def add_zones(board, fps):
    m = 0.3
    full = (-W / 2 + m, W / 2 - m, m, L - m)
    for layer in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
        rect_zone(board, "GND", [layer], full, name=f"GND {board.GetLayerName(layer)}")
    # spec §8: no vias around the IMU on any layer, no tracks under it on the inner and back layers
    rect_zone(board, None, [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu], (-2.6, 2.6, 58.3, 62.7),
              rule={"vias"}, name="IMU ohne Vias")
    rect_zone(board, None, [pcbnew.In2_Cu, pcbnew.B_Cu], (-3.5, 3.5, 57.0, 64.0), rule={"tracks"},
              name="IMU ruhige Masse")
    # spec §8: LoRa module on a ground plane, no signals underneath (pads sit at its long edges)
    b = crt_box(fps["U10"])
    inner = (b[0] + 2.6, b[1] - 2.6, b[2] + 1.5, b[3] - 1.5)
    rect_zone(board, None, [pcbnew.F_Cu, pcbnew.In2_Cu], inner, rule={"tracks", "vias"}, name="LoRa ohne Signale")


def add_silk(board, fps):
    def text(s, u, v, size=0.9, layer=pcbnew.F_SilkS, rot=0, bold=False):
        t = pcbnew.PCB_TEXT(board)
        t.SetText(s)
        t.SetPosition(P(u, v))
        t.SetLayer(layer)
        t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
        t.SetTextThickness(MM(size * (0.18 if bold else 0.13)))
        t.SetTextAngleDegrees(rot)
        board.Add(t)
        return t

    for ref, label in LABELS.items():
        b = crt_box(fps[ref])
        cu = (b[0] + b[1]) / 2
        if ref in EDGE and EDGE[ref][0] == "bottom":
            text(label, cu, b[3] + 0.9, 0.8)
        elif ref in EDGE:
            text(label, cu, b[2] - 0.9, 0.8)
        else:
            text(label, cu, b[3] + 0.9, 0.8)
    text("MISSION SPACE", 17.5, 112.5, 1.0, bold=True)
    text("MAINBOARD REV B", 17.5, 110.8, 0.8)
    text("2026-10", 17.5, 109.3, 0.8)
    text("JLCJLCJLCJLC", 0.0, 80.0, 0.8)                    # JLC order number, under the Teensy
    # IMU axes (spec §2): X across (+u), Y toward the nose (+v), Z out of the board
    for (a, b_), lab in zip((((2.2, 60.5), (5.2, 60.5)), ((0.0, 62.7), (0.0, 65.7))), ("X", "Y")):
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(P(*a))
        s.SetEnd(P(*b_))
        s.SetLayer(pcbnew.F_SilkS)
        s.SetWidth(MM(0.15))
        board.Add(s)
        for d in (-1, 1):
            h = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
            h.SetStart(P(*b_))
            if lab == "X":
                h.SetEnd(P(b_[0] - 0.7, b_[1] + 0.5 * d))
            else:
                h.SetEnd(P(b_[0] + 0.5 * d, b_[1] - 0.7))
            h.SetLayer(pcbnew.F_SilkS)
            h.SetWidth(MM(0.15))
            board.Add(h)
    text("X", 5.9, 60.5, 0.7)
    text("Y", 0.0, 66.4, 0.7)
    text("IMU Z+", -3.4, 64.3, 0.6)


def build():
    board = new_board()
    draw_outline(board)
    fps = add_footprints(board)
    placed, clash = place_fixed(board, fps)
    failed = place_passives(fps, placed)
    add_zones(board, fps)
    add_silk(board, fps)
    pcbnew.SaveBoard(str(PCB), board, True)
    print(f"placed {len(placed)} of {len(fps)} footprints")
    if clash:
        print("fixed parts colliding:", clash)
    if failed:
        print("no place found for:", failed)
    return board


def export_dsn():
    board = pcbnew.LoadBoard(str(PCB))
    board.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER)
    out = HERE / "out" / "mainboard.dsn"
    out.parent.mkdir(exist_ok=True)
    ok = pcbnew.ExportSpecctraDSN(board, str(out))
    print("dsn", ok, out)


def import_ses():
    board = pcbnew.LoadBoard(str(PCB))
    ok = pcbnew.ImportSpecctraSES(board, str(HERE / "out" / "mainboard.ses"))
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    pcbnew.SaveBoard(str(PCB), board, True)
    print("ses imported", ok, "tracks", len(board.GetTracks()))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "place"
    {"place": build, "dsn": export_dsn, "ses": import_ses}[cmd]()
