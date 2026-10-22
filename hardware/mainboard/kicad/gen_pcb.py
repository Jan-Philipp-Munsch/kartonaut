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
# Rev B1 (README section 5.3): the 2S path on the right (XT30 at the TVC end, VBAT_PROT along the right
# edge to the arming switch at the nose), the 1S path on the left (switch, battery, charger, buck-boost,
# radio), flat parts only in the SD-card path (v 18..30) and under the USB plug, decoder and mux under
# the Teensy next to their pins, J_STACK beside the right socket row where all its signals are.
# Footprint origin positions. Rotation 180 turns a horizontal connector's mouth from -y to +y etc.
EDGE_U_, RAIL_U_ = 25.75, 23.75          # runs along the right edge (see CORRIDORS)
ANCHORS = {
    "A1": (0.0, 60.5, 0),           # Teensy: USB toward the nose (+v), SD toward the TVC
    "U4": (0.0, 60.5, 0),           # IMU on the roll axis under the Teensy; chip X = +u, Y = +v
    # left strip, TVC end: switch, 1S battery, charger cable
    "J3": (-22.5, 16.3, 0),         # J_SW, PH-4 top entry
    "J2": (-22.5, 22.8, 0),         # J_BAT1, PH-2 top entry
    "J17": (-15.0, 22.8, 0),        # J_CHG1, PH-3 top entry
    "Q2": (-22.0, 26.8, 0),         # 1S reverse protection right above the battery plug
    "F2": (-19.5, 30.6, 0),         # 1S polyfuse
    "C10": (-19.6, 34.6, 180),      # 1S input capacitor at the buck-boost: VSYS_IN pad toward U2
    "Q7": (-13.5, 29.5, 0),         # 1S load switch between the fuse and the buck-boost
    # centre, TVC end (SD-card path: only flat parts)
    "C4": (-3.8, 16.8, 0),          # 330 uF polymer at VSERVO, next to the servo pins
    "C5": (-3.8, 22.3, 0),
    "R_SH1": (4.8, 25.6, 180),      # shunt: VBAT_PROT pad toward Q6 (+u), VSERVO pad up to the bus, sense taps down
    "U6": (4.4, 21.8, 0),           # INA239 right below the sense taps
    # right strip, TVC end: 2S entry, a straight chain up from the XT30 plus pin
    "Q1": (10.8, 17.8, 180),        # reverse protection: drain toward the XT30 plus pin, source up to F1
    "F1": (10.8, 22.6, 90),         # 2S polyfuse
    "Q6": (15.0, 24.3, 0),          # load switch, drain (+u): VBAT_PROT left over F1 to the shunt, right to the edge
    "J18": (19.0, 19.6, 0),         # J_CHG2, PH-2 top entry
    # right strip: actuators
    "J7": (12.4, 34.0, 0),          # servo 3 (chute), XH-3 top entry
    "J16": (12.4, 41.5, 0),         # servo 4 (legs), XH-3 top entry
    "J8": (12.4, 48.7, 0),          # roll motor, XH-2 top entry
    "U7": (16.5, 54.5, 0),          # DRV8833, 2.8 mm channel to the VSERVO rail for its right pin row
    # under the Teensy (parts up to 3 mm): decoder and mux at their Teensy pins (24, 25, 30, 31, 38)
    "U11": (-3.0, 32.0, 0),         # 1S charger (SOT-23-5), flat, between the 1S path and the mux
    "U12": (-3.1, 40.5, 90),
    "U13": (3.1, 40.5, 90),
    # left strip: buck-boost 5V_SYS, >= 25 mm from the IMU
    "U2": (-15.5, 36.0, 0),         # L1/L2 pins (11, 9) face the nose; U2 and L2 >= 25 mm from the IMU
    "L2": (-15.5, 40.7, 0),         # straight above U2: pad 1 at pin 11 (L1), pad 2 at pin 9 (L2), no crossing
    # under the Teensy, nose end: hold-up behind D1 right at the VIN pin (A1), flat polymer parts
    "C16": (0.0, 75.6, 0),          # 470 uF hold-up at TEENSY_VIN
    "C17": (0.0, 81.0, 0),
    "D1": (0.0, 86.4, 0),           # 5V_SYS -> TEENSY_VIN
    # left strip: radio, then GPS, camera, LEDs toward the nose
    "U10": (-17.6, 61.5, 180),      # LoRa module, ANT side toward the nose; 0.5 mm from the edge (B17)
    "J11": (-17.0, 79.6, 0),        # GPS, GH-4 top entry
    "J13": (-17.0, 86.6, 0),        # camera, GH-3 top entry
    "J14": (-17.0, 93.6, 0),        # external LEDs, GH-3 top entry
    "U3": (-21.0, 100.0, 0),        # LDO 3V3_RF
    # right strip: logic beside the right socket row
    "J15": (11.2, 82.4, 0),         # J_STACK 2x10, pin 1 at the nose end, rows along v
    "J4": (19.0, 77.5, 90),         # arming (key switch), XH-2 top entry: VBAT_PROT comes up the right edge,
                                    # VBAT_ARMED goes on along it to the pyro plugs
    "U14": (19.5, 66.0, 0),         # LDO 3V3_EXP for J_STACK
    "TP1": (EDGE_U_, 44.0, 0),      # test points VBAT_PROT and VSERVO right on their runs along the edge
    "TP4": (RAIL_U_, 66.0, 0),
    "BZ1": (12.1, 90.7, 0),         # buzzer, 12 mm, clear of the USB plug space
    "J12": (20.3, 101.4, 90),       # Qwiic, SH-4 top entry
}
EDGE = {  # ref: (edge, u of the footprint origin, rot) - the courtyard is moved flush with that edge
    "J5": ("bottom", -14.4, 0),     # servo yaw, XH-3 side entry
    "J6": ("bottom", -2.8, 0),      # servo pitch
    "J1": ("bottom", 10.2, 180),    # XT30PW-M, mouth toward the TVC end, clear of hole H2
    "J9": ("top", -13.0, 180),      # pyro 1..4, XH-2 side entry toward the nose
    "J10": ("top", -3.5, 180),
    "J19": ("top", 6.0, 180),       # pyro 3 (DNP)
    "J20": ("top", 15.5, 180),      # pyro 4 (DNP)
}
# Pyro channels: one column under each plug (centre u), TVS under pin 1, FET under pin 2 (drain up)
PYRO_COLS = {1: ("J9", "D2", "Q3", -14.25), 2: ("J10", "D3", "Q4", -4.75), 3: ("J19", "D5", "Q8", 4.75),
             4: ("J20", "D6", "Q9", 14.25)}
for _ch, (_j, _d, _q, _c) in PYRO_COLS.items():
    ANCHORS[_d] = (_c + 1.6, 103.6, 270)
    ANCHORS[_q] = (_c - 2.4, 105.3, 0)
HOLES = {f"H{i + 1}": xy for i, xy in enumerate(outline.HOLES)}

STRIP_L, STRIP_R = (-26.4, -9.3), (9.3, 26.4)       # beside the Teensy socket courtyards
RIGHT_IN = (9.3, 22.8)                              # right strip without the VBAT_PROT run along the edge
BOARD = (-26.4, 26.4, 0.6, 119.4)
NOSE_MID = (-12.0, 16.0, 88.0, 107.4)               # under the USB plug (flat parts only) and beside the arming plug
# Regions for the passives of each schematic block (u0, u1, v0, v1)
REGIONS = {
    "2S: Akku, Verpolschutz, Sicherung, Lastschalter": (5.5, 22.8, 13.0, 30.0),
    "2S: Spannungsmessung, Shunt und INA239": (-9.3, 22.8, 13.0, 36.0),
    "2S: Servo-Schiene VSERVO": (-9.3, 9.3, 13.0, 30.0),
    "1S: Akku, Verpolschutz, Sicherung, Lastschalter": (-25.4, -6.1, 13.0, 34.0),
    "1S: Lader MCP73831": (-25.4, 6.1, 13.0, 37.0),
    "1S: Buck-Boost U2 -> 5V_SYS, Teensy-VIN": (-25.4, -6.1, 27.0, 48.0),
    "LDOs 3V3_RF und 3V3_EXP, Sensorinsel, Sternpunkt": BOARD,
    "Teensy 4.1": BOARD,
    "CS-Decoder und Analogmux": (-6.1, 6.1, 31.0, 54.0),
    "Stapelstecker J_STACK, Befestigung, Testpunkte": BOARD,
    "IMU ICM-42688-P, SPI1": (-6.1, 6.1, 50.0, 71.0),
    "Barometer BMP390, SPI1": (15.8, 22.8, 57.0, 76.0),
    "Qwiic, I2C": (-6.1, 22.8, 57.0, 84.0),
    "LoRa E22-400T22S, Serial8": (-25.4, -9.3, 44.0, 80.0),
    "GPS, Serial1": (-25.4, -9.3, 74.0, 108.0),
    "Servos": (-13.0, 22.8, 8.0, 46.0),
    "Rollmotor DRV8833": (*RIGHT_IN, 40.0, 58.0),
    "Arming": (9.3, 22.8, 84.0, 107.2),
    "Messteiler am Analogmux": (-9.3, 9.3, 34.0, 91.0),
    "Pyro-Kanal 1": NOSE_MID, "Pyro-Kanal 2": NOSE_MID, "Pyro-Kanal 3": NOSE_MID, "Pyro-Kanal 4": NOSE_MID,
    "Status-LEDs": (-25.4, -9.3, 74.0, 108.0),
    "Summer": (-12.0, 22.8, 84.0, 107.4),
    "Kamera": (-25.4, -9.3, 74.0, 108.0),
}
REF_REGIONS = {"NT1": (5.5, 22.8, 13.0, 30.0),      # star point right at the 2S minus of J1
               "JP1": (-25.4, -6.1, 13.0, 34.0), "JP2": (-25.4, -6.1, 13.0, 34.0),
               "C6": (-13.0, 22.8, 8.0, 60.0), "C9": (-25.4, 9.3, 13.0, 56.0),
               "U15": (-6.1, 6.1, 66.0, 73.0), "C31": (-6.1, 6.1, 66.0, 73.0), "C32": (-6.1, 6.1, 66.0, 73.0),
               "C21": (9.3, 22.8, 54.0, 84.0), "C22": (9.3, 22.8, 54.0, 84.0),
               "FB1": (-9.3, 22.8, 40.0, 84.0), "C23": (-9.3, 22.8, 40.0, 84.0)}
REF_REGIONS.update({f"TP{i}": BOARD for i in range(1, 12)})   # test points: next to their net, anywhere
# SD card and USB plug sit at Teensy height (8.5 mm sockets): flat SMD parts may go underneath,
# tall THT parts not. The placer only places SMD passives, so these are checked for anchors only.
KEEPOUTS = [(u0, u1, v0, v1) for _, u0, u1, v0, v1 in outline.KEEPOUTS]
UNDER_TEENSY = (-6.1, 6.1, 30.0, 91.0)          # parts up to 3 mm high (every part the placer places)
UNDER_OK = ("IMU ICM-42688-P, SPI1",)           # only the IMU block inside the 5 mm circle around the IMU
FLAT = {"TP1", "TP4", "U4", "U11", "U12", "U13", "C4", "C5", "R_SH1", "U6", "C16", "C17", "D1", "Q3", "Q4", "Q8", "Q9", "D2", "D3", "D5", "D6"}   # anchored parts of at most 3.1 mm height
IMU_VIA_R = 2.6                                 # board rule: no vias under the chip
IMU_KEEP_R = 5.0                                # spec section 8: no vias and no inner tracks within 5 mm of the IMU
# Silkscreen: front carries short names, the back the logo, title and pin-out (JLC: 1.0 mm text, 0.15 mm stroke)
LABELS = {  # front, next to the connector instead of its J number
    "J1": "2S", "J2": "1S", "J3": "SW", "J4": "ARM", "J5": "YAW", "J6": "PITCH", "J7": "CHUTE", "J8": "MOT",
    "J9": "PYRO1", "J10": "PYRO2", "J11": "GPS", "J12": "QWIIC", "J13": "CAM", "J14": "LED", "J15": "STACK",
    "J16": "LEGS", "J17": "CHG1S", "J18": "CHG2S", "J19": "PYRO3", "J20": "PYRO4",
}
PINOUT = {  # back, pin 1 first; one word per pin (checked against circuit.py), J15 only its supply pins
    "J1": "+ -", "J2": "+ -", "J3": "1S GND 2S GNDP", "J4": "2S ARM", "J5": "S + -", "J6": "S + -", "J7": "S + -",
    "J8": "A B", "J9": "+ -", "J10": "+ -", "J11": "3V3 GND TX RX", "J12": "GND 3V3 SDA SCL",
    "J13": "5V TRG GND", "J14": "5V DAT GND", "J15": "1:GND 2:GNDP 3:3V3 4:5V 5,6:VSRV",
    "J16": "S + -", "J17": "VBUS GND LED", "J18": "+ -", "J19": "+ -", "J20": "+ -",
}
TP_LABELS = {"VBAT_PROT": "VBAT", "VSYS_IN": "VSYS", "5V_SYS": "5V", "VSERVO": "VSRV", "3V3_EXP": "3V3X",
             "3V3_RF": "3V3RF", "GND": "GND"}   # test points by net, not TPn
SILK_H, SILK_T = 1.0, 0.15
NAME, REV = "KARTONAUT", "MAINBOARD REV B1"
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
    return p.lib.startswith(("Device:R", "Device:C", "Device:L", "Device:D", "Device:Ferrite", "Connector:TestPoint")) and ref != "R_SH1"


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
        if p.dnp:                          # pyro 3/4 and the second barometer (E5, C2): footprint only
            attrs |= pcbnew.FP_DNP | pcbnew.FP_EXCLUDE_FROM_POS_FILES
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
        if p.ref == "U7":                  # exposed pad with thermal vias: solid to the GND_PWR plane
            fp.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
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
    clash += [(a, "SD/USB-Freiraum") for a in placed if not a.startswith(("A1", "H")) and a not in FLAT
              and any(overlap(placed[a], k) for k in KEEPOUTS)]
    return placed, clash


# Decoupling and setup parts that belong to one IC although another part shares their net first
OWNERS = {"C21": "U14", "C22": "U14", "C8": "U11", "C9": "U11", "R13": "U11", "C3": "U6", "C24": "U12",
          "C25": "U13", "C18": "U3", "C19": "U3", "C20": "U3", "C29": "U5", "C30": "U5", "C31": "U15", "C32": "U15",
          "C33": "U10", "C34": "U10", "C35": "U7", "C36": "U7", "C37": "U7", "C38": "U7", "C44": "U8", "C45": "LED1", "C46": "LED2",
          "C26": "U4", "C27": "U4", "C28": "U4", "C13": "U2", "C14": "U2", "C15": "U2"}


def owner_target(p, fps, placed):
    """Where a passive wants to sit: at the pad of an already placed part sharing a signal net."""
    own = OWNERS.get(p.ref)
    if own and (own in placed):
        for pad in fps[own].Pads():
            if pad.GetNetname() in p.pins.values() and pad.GetNetname() not in ("GND", "GND_PWR"):
                q = pad.GetPosition()
                return UV(pcbnew.ToMM(q.x), pcbnew.ToMM(q.y))
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


RINGS_WIDE = sorted(((du * 0.5, dv * 0.5) for du in range(-110, 111) for dv in range(-240, 241)),
                    key=lambda d: d[0] ** 2 + d[1] ** 2)
FALLBACK = []                       # parts placed outside their region (reported by build)


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
            imu = (-IMU_KEEP_R - 1.0, IMU_KEEP_R + 1.0, ANCHORS["U4"][1] - IMU_KEEP_R - 1.0,
                   ANCHORS["U4"][1] + IMU_KEEP_R + 1.0)

            def search(reg, gap, rings):
                for du, dv in rings:
                    u, v = target[0] + du, target[1] + dv
                    for rot in (0, 90):
                        b0 = shapes[rot]
                        box = (b0[0] + u, b0[1] + u, b0[2] + v, b0[3] + v)
                        if not inside(box, reg) or not inside(box, region_board):
                            continue
                        if p.group not in UNDER_OK and overlap(box, imu):
                            continue
                        if any(overlap(box, b, gap) for b in placed.values()):
                            continue
                        return (u, v, rot, box)
                return None
            gap = 0.2 if p.group.startswith("IMU") or p.ref == "NT1" else 0.35   # routing channels
            ok = search(region, gap, RINGS)
            if not ok:                      # second chance: anywhere, as close to the owner as possible
                ok = search(region_board, 0.25, RINGS_WIDE)
                if ok:
                    FALLBACK.append(p.ref)
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


# B.Cu is the supply plane (layer type power): GND_PWR under everything fed from the 2S pack, 5V_SYS
# under the 1S side. GND_PWR: the TVC band (servos, XT30), the centre under the VSERVO buffer, the right
# strip with the actuators, the outer right strip beside J_STACK and the nose band under pyro, arming
# and buzzer, so every 2S return runs as plane to the star point (spec section 8), not as a long track.
SPLIT_GND_PWR = [(-26.7, 0.3), (26.7, 0.3), (26.7, 119.7), (-19.5, 119.7), (-19.5, 99.0), (-9.4, 99.0),
                 (-9.4, 89.0), (16.0, 89.0), (16.0, 56.0), (9.4, 56.0), (9.4, 30.5), (-9.4, 30.5), (-9.4, 13.0),
                 (-26.7, 13.0)]
SPLIT_5V_SYS = [(-26.7, 13.0), (-9.4, 13.0), (-9.4, 30.5), (9.4, 30.5), (9.4, 56.0), (16.0, 56.0), (16.0, 89.0),
                (-9.4, 89.0), (-9.4, 99.0), (-19.5, 99.0), (-19.5, 119.7), (-26.7, 119.7)]


def imu_circle(r=IMU_KEEP_R, n=24):
    u0, v0 = ANCHORS["U4"][:2]
    return [(u0 + r * math.cos(2 * math.pi * k / n), v0 + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


# Current paths as F.Cu zones of their net (review B13): drawn before routing, so Freerouting sees them
# as planes of that net and only adds the short stubs. Waypoints are (u, v) or "REF.PAD"; consecutive
# points are joined by an axis-parallel L (along u first, "v" as fourth item: along v first).
EDGE_U = EDGE_U_                                      # outer run along the right edge (u 24.9..26.6): VBAT_PROT, VBAT_ARMED
RAIL_U = RAIL_U_                                      # inner run (u 22.9..24.6): VSERVO to the right strip
BUS_V = 28.8                                        # VSERVO bus right below the Teensy sockets (v 28.1..29.5)
CORRIDORS = [
    # 2S entry chain: XT30 plus -> Q1 drain; Q1 source -> F1; F1 -> Q6 source
    ("VBAT2_RAW", 1.2, ["J1.1", "Q1.3"]),
    ("VBAT2_REV", 1.0, ["Q1.2", "F1.1"], "v"),
    ("VBAT2_F", 1.0, ["F1.2", "Q6.2"], "v"),
    # DRV8833 VM straight to the VSERVO rail
    ("VSERVO", 0.6, ["U7.12", (RAIL_U, "U7.12")]),
    # servo 3 and 4: from the inner rail above the pin row (clear of the minus pin) down to the plus pin
    ("VSERVO", 0.9, [(RAIL_U, 35.7), ("J7.2", 35.7)]),
    ("VSERVO", 0.9, ["J7.2", ("J7.2", 35.7)], "v"),
    ("VSERVO", 0.9, [(RAIL_U, 43.2), ("J16.2", 43.2)]),
    ("VSERVO", 0.9, ["J16.2", ("J16.2", 43.2)], "v"),
    # pyro: FET drain straight up to pin 2 of its plug (5 A pulse)
    ("PYRO1_NEG", 1.0, ["Q3.3", ("Q3.3", "J9.2")], "v"),
    ("PYRO2_NEG", 1.0, ["Q4.3", ("Q4.3", "J10.2")], "v"),
    ("PYRO3_NEG", 1.0, ["Q8.3", ("Q8.3", "J19.2")], "v"),
    ("PYRO4_NEG", 1.0, ["Q9.3", ("Q9.3", "J20.2")], "v"),
    # 2S: Q6 drain -> over F1 -> shunt; Q6 drain -> outer run -> arming plug J4 (VBAT_PROT, A6)
    ("VBAT_PROT", 1.4, [("R_SH1.1", 26.7), ("Q6.3", 26.7)]),
    ("VBAT_PROT", 1.1, ["Q6.3", ("Q6.3", 26.7)], "v"),
    ("VBAT_PROT", 1.4, ["Q6.3", ("EDGE", "Q6.3")]),
    ("VBAT_PROT", 1.7, [("EDGE", 23.6), ("EDGE", "J4.1")]),
    ("VBAT_PROT", 1.8, [("EDGE", "J4.1"), "J4.1"]),
    # arming plug J4 -> outer run -> band behind the pins of the four pyro plugs (VBAT_ARMED), down to each TVS
    ("VBAT_ARMED", 1.8, ["J4.2", ("EDGE", "J4.2")]),
    ("VBAT_ARMED", 1.7, [("EDGE", "J4.2"), (EDGE_U, 112.9)]),
    ("VBAT_ARMED", 2.0, [(EDGE_U, 112.9), ("J9.1", 112.9)]),
    ("VBAT_ARMED", 1.6, [("J9.1", "D2.1"), ("J9.1", 112.9)], "v"),
    ("VBAT_ARMED", 1.6, [("J10.1", "D3.1"), ("J10.1", 112.9)], "v"),
    ("VBAT_ARMED", 1.6, [("J19.1", "D5.1"), ("J19.1", 112.9)], "v"),
    ("VBAT_ARMED", 1.6, [("J20.1", "D6.1"), ("J20.1", 112.9)], "v"),
    # VSERVO: shunt -> bus across the board -> buffer column -> both TVC servo plugs; bus -> inner rail
    ("VSERVO", 1.9, ["R_SH1.4", ("R_SH1.4", BUS_V)], "v"),
    ("VSERVO", 1.4, [("C5.1", BUS_V), (RAIL_U, BUS_V)]),
    ("VSERVO", 2.0, [("C5.1", BUS_V), ("C5.1", 10.1)], "v"),
    ("VSERVO", 4.2, [("J5.2", 10.1), ("J6.2", 10.1)]),
    ("VSERVO", 1.7, [(RAIL_U, 28.1), (RAIL_U, 72.0)], "v"),
    # 1S input at the buck-boost (A7): wide up to the VQFN pins, the zone fill necks down there
    ("VSYS_IN", 1.0, ["C10.1", ("U2.1", "C10.1")]),
    ("VSYS_IN", 0.8, ["C10.1", ("C10.1", "U2.12")], "v"),
    ("VSYS_IN", 0.6, [("C10.1", "U2.12"), "U2.12"]),
]


def pad_uv(fps, ref, num):
    for pad in fps[ref].Pads():
        if pad.GetNumber() == num:
            q = pad.GetPosition()
            return UV(pcbnew.ToMM(q.x), pcbnew.ToMM(q.y))
    raise KeyError(f"{ref}.{num}")


def add_corridors(board, fps, draw=True):
    """Draw the CORRIDORS as zones; returns their boxes (u0, u1, v0, v1). With draw=False only the
    boxes, which the placer keeps free of other parts."""
    def pt(x):
        if isinstance(x, str):
            return pad_uv(fps, *x.split("."))
        a, b = x
        u = EDGE_U if a == "EDGE" else (pad_uv(fps, *a.split("."))[0] if isinstance(a, str) else a)
        v = pad_uv(fps, *b.split("."))[1] if isinstance(b, str) else b
        return u, v
    boxes, per_net = [], {}
    for net, w, way, *opt in CORRIDORS:
        pts = [pt(x) for x in way]
        for a, b in zip(pts, pts[1:]):
            mid = (a[0], b[1]) if opt and opt[0] == "v" else (b[0], a[1])
            for s0, s1 in ((a, mid), (mid, b)):
                if abs(s0[0] - s1[0]) < 1e-6 and abs(s0[1] - s1[1]) < 1e-6:
                    continue
                box = (min(s0[0], s1[0]) - w / 2, max(s0[0], s1[0]) + w / 2,
                       min(s0[1], s1[1]) - w / 2, max(s0[1], s1[1]) + w / 2)
                box = (max(box[0], -W / 2 + 0.4), min(box[1], W / 2 - 0.4), box[2], box[3])
                boxes.append(box)
                per_net.setdefault(net, []).append(box)
    if draw:                                         # one zone per net: the union of its rectangles
        for net, rects in per_net.items():
            z = rect_zone(board, net, [pcbnew.F_Cu], rects[0], priority=2, solid=True, name=f"{net} Strompfad")
            o = z.Outline()
            for u0, u1, v0, v1 in rects[1:]:
                o.NewOutline()
                for u, v in ((u0, v0), (u1, v0), (u1, v1), (u0, v1)):
                    q = P(u, v)
                    o.Append(q.x, q.y, o.OutlineCount() - 1)
            o.Simplify()
    return boxes


WIDE_PATHS = {"VBAT_PROT", "VBAT_ARMED", "VSERVO"}     # runs other parts' stubs dock onto


def carve_corridors(board):
    """Freerouting reads a zone as its plain outline, without the clearance cut-outs around pads of
    other nets that KiCad's fill makes; every such pad would be a short. So fill the current-path
    zones once and take the filled shape as their new outline. Returns the number of zones kept."""
    zones = [z for z in board.Zones() if z.GetZoneName().endswith("Strompfad")]
    pcbnew.ZONE_FILLER(board).Fill(zones)
    kept = 0
    for z in zones:
        poly = z.GetFilledPolysList(pcbnew.F_Cu)
        if poly.OutlineCount() == 0:
            board.Delete(z)
            continue
        o = z.Outline()                              # edited in place: SetOutline() would take
        o.RemoveAllContours()                        # ownership of a Python object (crash)
        for i in range(poly.OutlineCount()):
            o.AddOutline(poly.COutline(i))           # holes (other pads inside) become notches
            for h in range(poly.HoleCount(i)):
                o.AddHole(poly.CHole(i, h), o.OutlineCount() - 1)
        o.Fracture()
        z.SetIsFilled(False)
        kept += 1
        # Freerouting does not treat a copper zone on a signal layer as an obstacle for other nets and
        # would route straight through it. A rule area of the same shape keeps tracks and vias out while
        # routing; import_ses() deletes these again.
        k = pcbnew.ZONE(board)
        ls = pcbnew.LSET()
        ls.AddLayer(pcbnew.F_Cu)
        k.SetLayerSet(ls)
        core = pcbnew.SHAPE_POLY_SET(o)          # 0.6 mm smaller than the copper: 1 mm tracks of the
        rim = 0.6 if z.GetNetname() in WIDE_PATHS else 0.3   # 1 mm / 0.5 mm stubs dock at the rim
        core.Deflate(MM(rim), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.01))
        if core.OutlineCount() == 0:
            continue
        ko = k.Outline()
        for i in range(core.OutlineCount()):
            ko.AddOutline(core.COutline(i))
        k.SetIsRuleArea(True)
        k.SetDoNotAllowTracks(True)
        k.SetDoNotAllowVias(True)
        k.SetDoNotAllowZoneFills(False)
        k.SetDoNotAllowPads(False)
        k.SetDoNotAllowFootprints(False)
        k.SetZoneName(f"{z.GetNetname()} frei halten")
        board.Add(k)
    return kept


def add_pours(board):
    """GND pours on F.Cu and In2.Cu - added after routing, so Freerouting sees free signal layers."""
    for layer in (pcbnew.F_Cu, pcbnew.In2_Cu):
        rect_zone(board, "GND", [layer], FULL, name=f"GND {board.GetLayerName(layer)}", solid=True)


def add_zones(board, fps):
    rect_zone(board, "GND", [pcbnew.In1_Cu], FULL, name="GND In1.Cu")     # solid plane (layer type power)
    rect_zone(board, "GND_PWR", [pcbnew.B_Cu], SPLIT_GND_PWR, name="GND_PWR B.Cu")
    rect_zone(board, "5V_SYS", [pcbnew.B_Cu], SPLIT_5V_SYS, name="5V_SYS B.Cu")
    # spec §8, review B16: no vias within 5 mm of the IMU on any layer, no inner tracks there; only
    # the SPI lines and INT come in, on F.Cu straight from the Teensy pads
    rect_zone(board, None, [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu], imu_circle(IMU_VIA_R, 16),
              rule={"vias"}, name="IMU ohne Vias")
    rect_zone(board, None, [pcbnew.In2_Cu], imu_circle(), rule={"tracks"}, name="IMU ruhige Masse")
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
    no_via = []
    iu, iv = ANCHORS["U4"][:2]
    b = crt_box(fps["U10"])
    no_via.append((b[0] + 2.6, b[1] - 2.6, b[2] + 1.5, b[3] - 1.5))

    def rect_dist(x, y, bb):
        x0, x1 = pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetRight())
        y0, y1 = pcbnew.ToMM(bb.GetTop()), pcbnew.ToMM(bb.GetBottom())
        dx = max(x0 - x, 0, x - x1)
        dy = max(y0 - y, 0, y - y1)
        return math.hypot(dx, dy)

    corr = add_corridors(board, fps, draw=False)
    imu_group = {p.ref for p in circuit.PARTS if p.group.startswith("IMU")}
    own_imu = False

    def free(x, y, own, net):
        u, v = UV(x, y)
        if abs(u) > W / 2 - 1.0 or v < 1.0 or v > L - 1.0:
            return False
        if any(r[0] - 0.3 < u < r[1] + 0.3 and r[2] - 0.3 < v < r[3] + 0.3 for r in no_via):
            return False
        r = math.hypot(u - iu, v - iv)
        if r < IMU_VIA_R + 0.4 or (r < IMU_KEEP_R + 0.4 and not own_imu):
            return False
        if any(b[0] - 0.4 < u < b[1] + 0.4 and b[2] - 0.4 < v < b[3] + 0.4 for b in corr):
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
        own_imu = fp.GetReference() in imu_group       # the IMU's own ground vias may sit within 5 mm
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
    for i, box in enumerate(add_corridors(board, fps, draw=False)):   # keep the current paths free
        placed[f"~path{i}"] = box
    failed = place_passives(fps, placed)
    add_zones(board, fps)
    ncorr = len(add_corridors(board, fps))
    nvias = add_plane_vias(board, fps)
    print(f"{ncorr} current-path zones on F.Cu, {carve_corridors(board)} kept after cutting out other pads")
    print(f"{nvias} plane vias next to SMD pads of GND, GND_PWR, 5V_SYS")
    lost = add_silk(board, fps)
    pcbnew.SaveBoard(str(PCB), board, True)
    set_stackup()
    fix_model_paths()
    print(f"placed {len([r for r in placed if not r.startswith('~')]) - 1} of {len(fps)} footprints")
    if clash:
        print("fixed parts colliding:", clash)
    if FALLBACK:
        print("placed outside their region:", FALLBACK)
    if failed:
        print("no place found for:", failed)
    if lost:
        print("silkscreen without a free spot (on F.Fab):", lost)
    return board


def export_dsn(tag=""):
    board = pcbnew.LoadBoard(str(PCB))
    # In1 and B.Cu are power layers for the router: no wires there. Tried and rejected (22.10.): the two
    # as signal layers under a full wire_keepout, so that Freerouting sees the planes as conduction
    # areas (668 clearance violations, every via of another net against the GND plane); and the pads
    # that already have a plane via taken out of the netlist (146 violations, fixed stubs against
    # netless pads). The router therefore fans those pads out a second time and lists about 55 of
    # them as open at the end; on the board they are connected, KiCad's DRC is the measure.
    board.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER)
    board.SetLayerType(pcbnew.B_Cu, pcbnew.LT_POWER)
    out = HERE / "out" / f"mainboard{tag}.dsn"
    out.parent.mkdir(exist_ok=True)
    ok = pcbnew.ExportSpecctraDSN(board, str(out))
    s = out.read_text(encoding="utf-8")
    for cls in () if os.environ.get("DSN_ALL_LAYERS") else ("Strom",):   # A6: 2S nets never on In2
        i = s.index(f"(class {cls} ")
        j = s.index("(circuit", i)
        s = s[:j] + "(circuit\n        (use_layer F.Cu)" + s[j + len("(circuit"):]
        # the current itself runs in the CORRIDORS zones; what the router adds to these nets are the
        # stubs of dividers, gate resistors, capacitors and test points: 0.5 mm, not the class 1.0 mm
        k = s.index("(width 1000)", j)
        s = s[:k] + "(width 500)" + s[k + len("(width 1000)"):]
    # Everything that is on the board already is fixed for the router: in the first run the plane vias
    # with their stubs, in the finishing passes the whole wiring. Routable, the router may move or rip
    # them, and the session file would then be the only record of them; fixed items stay on the board
    # and merge_ses() adds only what the router made. (It does not stop the fanout stage from treating
    # those pads as open, see above.)
    s = s.replace("(type route)", "(type fix)")
    # spec section 8 / B16: the router places no via within 5 mm of the IMU (the board rule is 2.6 mm,
    # so the IMU's own ground vias set by add_plane_vias may stay in the ring). The keepout is the
    # 5 mm disc with a hole around every via that is already there; a disc over fixed vias made
    # Freerouting report 22 "unfixable violations" on every run.
    x, y = XY(*ANCHORS["U4"][:2])
    keep = "".join('    (via_keepout "IMU 5 mm" (polygon {} 0 {}))\n'.format(layer, pts)
                   for pts in imu_keepout_polys(board, x, y) for layer in ("F.Cu", "In2.Cu"))
    i = s.index("    (via_keepout")
    s = s[:i] + keep + s[i:]
    out.write_text(s, encoding="utf-8")
    print("dsn", ok, out, f"({s.count('(type fix)')} fixed items, {keep.count('via_keepout')} IMU keepout polygons)")


def imu_keepout_polys(board, x, y, n=48):
    """Point lists (DSN units: um, y up) of the 5 mm via keepout around the IMU, minus the vias that are
    already inside it (the IMU's own ground vias), as hole-free polygons."""
    def circle(cx, cy, r):
        c = pcbnew.SHAPE_POLY_SET()
        c.NewOutline()
        for k in range(n):
            a = 2 * math.pi * k / n
            c.Append(int(MM(cx + r * math.cos(a))), int(MM(cy + r * math.sin(a))))
        return c
    poly = circle(x, y, IMU_KEEP_R)
    for t in board.GetTracks():
        if t.GetClass() != "PCB_VIA":
            continue
        vx, vy = pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y)
        if math.hypot(vx - x, vy - y) < IMU_KEEP_R + 0.5:
            poly.BooleanSubtract(circle(vx, vy, pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) / 2 + 0.25))
    poly.Fracture()
    out = []
    for i in range(poly.OutlineCount()):
        o = poly.COutline(i)
        if o.PointCount() < 3:
            continue
        out.append(" ".join("{:.1f} {:.1f}".format(o.CPoint(k).x / 1000, -o.CPoint(k).y / 1000)
                            for k in range(o.PointCount())))
    return out


def import_ses(tag=""):
    """First run: take the session into the board and add the GND pours. KiCad's SES import replaces
    the whole wiring, and Freerouting leaves fixed items (the plane vias and their stubs) out of the
    session file, so the session goes into a copy and only what is new is taken over (merge_ses)."""
    merge_ses(tag, pours=True)


def merge_ses(tag="_fix", pours=False):
    """Add the tracks of a session that routed only the remaining connections (existing wiring was
    exported as fixed) to the board, keeping what is there."""
    board = pcbnew.LoadBoard(str(PCB))
    if pours and not any(z.GetZoneName() == "GND F.Cu" for z in board.Zones()):
        add_pours(board)
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
    print(f"{n} tracks and vias added from the session, {len(board.GetTracks())} on the board")


STROM_NETS = set(circuit.NETCLASSES["Strom"][4])


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
    width, clear = MM(0.15), MM(0.2)     # the board rule (netclass clearance); 0.13 made DRC errors
    others = list(board.GetTracks()) + [p for fp in board.GetFootprints() for p in fp.Pads()]

    paths = [z for z in board.Zones() if z.GetZoneName().endswith("Strompfad")]
    pcbnew.ZONE_FILLER(board).Fill(paths)

    def in_path(layer, pts, net):
        """Does any point come within 0.4 mm of a current-path zone of another net?"""
        return any(z.GetNetCode() != net and z.IsOnLayer(layer) and z.HitTestFilledArea(layer, q, MM(0.4))
                   for z in paths for q in pts)

    def free(shape, layer, net):
        for it in others:
            if it.GetNetCode() == net or not it.IsOnLayer(layer):
                continue
            if it.GetEffectiveShape(layer).Collide(shape, clear):
                return False
        if layer == pcbnew.F_Cu:
            if isinstance(shape, pcbnew.SHAPE_SEGMENT):
                a, b = shape.GetSeg().A, shape.GetSeg().B
                pts = [pcbnew.VECTOR2I(int(a.x + (b.x - a.x) * k / 8), int(a.y + (b.y - a.y) * k / 8))
                       for k in range(9)]
            else:
                pts = [shape.GetCenter()]
            if in_path(layer, pts, net):
                return False
        return True

    def reach(it):
        """(position, layers) of the connectable ends of an item."""
        if it.GetClass() in ("PCB_TRACK", "PCB_ARC"):
            return [(it.GetStart(), [it.GetLayer()]), (it.GetEnd(), [it.GetLayer()])]
        if it.GetClass() == "PCB_VIA":
            return [(it.GetPosition(), copper)]
        return [(it.GetPosition(), copper if it.GetAttribute() == pcbnew.PAD_ATTRIB_PTH else [pcbnew.F_Cu])]

    def via_spots(it):
        """(via position, F.Cu stub start or None) candidates next to a pad, or at a track end."""
        if it.GetClass() in ("PCB_TRACK", "PCB_ARC"):
            if it.GetLayer() == pcbnew.F_Cu:
                return [(it.GetStart(), None), (it.GetEnd(), None)]
            return [(it.GetStart(), "here"), (it.GetEnd(), "here")]
        if it.GetClass() == "PCB_VIA":
            return [(it.GetPosition(), "here")]
        c = it.GetPosition()
        if it.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
            return [(c, "here")]
        bb = it.GetBoundingBox()
        half = max(bb.GetWidth(), bb.GetHeight()) / 2
        out = []
        for dist in (half + MM(0.55), half + MM(0.9), half + MM(1.4)):
            for ang in range(0, 360, 45):
                out.append((pcbnew.VECTOR2I(int(c.x + dist * math.cos(math.radians(ang))),
                                            int(c.y + dist * math.sin(math.radians(ang)))), c))
        return out

    iu, iv = ANCHORS["U4"][:2]

    def via_free(pos, net):
        u, v = UV(pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y))
        if math.hypot(u - iu, v - iv) < IMU_KEEP_R + 0.4 or abs(u) > W / 2 - 1.0:
            return False                       # spec 8 / B16: no foreign vias within 5 mm of the IMU
        shape = pcbnew.SHAPE_CIRCLE(pos, MM(0.3))
        return all(free(shape, l, net) for l in (pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu))

    def via_detour(items, net):
        """Pad/track end -> (stub) -> via -> In2 -> via -> (stub) -> other end. True if set."""
        for pa, sa in via_spots(items[0]):
            for pb, sb in via_spots(items[1]):
                segs = []
                if isinstance(sa, pcbnew.VECTOR2I):
                    segs.append((sa, pa, pcbnew.F_Cu))
                if isinstance(sb, pcbnew.VECTOR2I):
                    segs.append((sb, pb, pcbnew.F_Cu))
                segs.append((pa, pb, pcbnew.In2_Cu))
                need = [p_ for p_, s_ in ((pa, sa), (pb, sb)) if not isinstance(s_, str)]
                if not all(via_free(v, net) for v in need):
                    continue
                if not all(free(pcbnew.SHAPE_SEGMENT(a, b, width), l, net) for a, b, l in segs):
                    continue
                for v in need:
                    via = pcbnew.PCB_VIA(board)
                    via.SetPosition(v), via.SetWidth(MM(0.6)), via.SetDrill(MM(0.3)), via.SetNetCode(net)
                    board.Add(via)
                    others.append(via)
                for a, b, l in segs:
                    tr = pcbnew.PCB_TRACK(board)
                    tr.SetStart(a), tr.SetEnd(b), tr.SetLayer(l), tr.SetWidth(width), tr.SetNetCode(net)
                    board.Add(tr)
                    others.append(tr)
                return True
        return False

    done, failed = 0, []
    for u in d["unconnected_items"]:
        items = [board.ResolveItem(pcbnew.KIID(i["uuid"])) for i in u["items"]]
        if any(i is None for i in items):
            continue
        items = [i.Cast() for i in items]
        if any(i.GetClass() == "ZONE" for i in items):
            failed.append(items[0].GetNetname())
            continue
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
        if not placed and board.GetNetInfo().GetNetItem(net).GetNetname() not in STROM_NETS:
            placed = via_detour(items, net)
        if placed:
            done += 1
        else:
            failed.append(board.GetNetInfo().GetNetItem(net).GetNetname())
    for z in [z for z in board.Zones() if z.GetZoneName().endswith("frei halten")]:
        board.Delete(z)                        # routing keepouts of the current paths (carve_corridors)
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
