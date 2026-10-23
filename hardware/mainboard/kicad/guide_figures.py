"""Pictures for the board guide (system Python with Pillow): out/guide/*.png from out/guide/board.json
(guide_dump.py) and the renders in img/. Called by make_guide.py."""
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import circuit

HERE = Path(__file__).resolve().parent
OUT = HERE / "out" / "guide"
G = json.loads((OUT / "board.json").read_text(encoding="utf-8"))
FONT = "C:/Windows/Fonts/arial.ttf"
FONTB = "C:/Windows/Fonts/arialbd.ttf"
X0, Y0, X1, Y1 = G["outline"]

BG = (255, 255, 255)
BOARD = (232, 236, 242)
EDGE = (60, 60, 70)
LAYER_COL = {"F.Cu": (205, 55, 55), "In1.Cu": (140, 140, 150), "In2.Cu": (45, 105, 215), "B.Cu": (30, 150, 85)}
VIA = (235, 180, 40)


def font(size, bold=False):
    return ImageFont.truetype(FONTB if bold else FONT, size)


class Canvas:
    """Board region (x0..x1, y0..y1 in mm) drawn at s px/mm, 2x supersampled."""

    def __init__(self, x0, y0, x1, y1, s, margin=8, bg=BG):
        self.x0, self.y0, self.s, self.m = x0, y0, s * 2, margin * 2
        self.w = int((x1 - x0) * self.s) + 2 * self.m
        self.h = int((y1 - y0) * self.s) + 2 * self.m
        self.img = Image.new("RGB", (self.w, self.h), bg)
        self.d = ImageDraw.Draw(self.img, "RGBA")

    def P(self, x, y):
        return (self.m + (x - self.x0) * self.s, self.m + (y - self.y0) * self.s)

    def poly(self, ring, fill, outline=None, width=1):
        pts = [self.P(x, y) for x, y in ring]
        if len(pts) > 2:
            self.d.polygon(pts, fill=fill, outline=outline, width=width)

    def fills(self, fill_list, color):
        for ring, holes in fill_list:
            self.poly(ring, color)
            for h in holes:
                self.poly(h, BOARD + (255,))

    def line(self, x1, y1, x2, y2, w_mm, color):
        a, b = self.P(x1, y1), self.P(x2, y2)
        w = max(1, int(round(w_mm * self.s)))
        self.d.line([a, b], fill=color, width=w)
        r = w / 2
        for q in (a, b):
            self.d.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], fill=color)

    def circle(self, x, y, r_mm, fill=None, outline=None, width=2):
        cx, cy = self.P(x, y)
        r = r_mm * self.s
        self.d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill, outline=outline, width=width)

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, width=2):
        a, b = self.P(x0, y0), self.P(x1, y1)
        self.d.rectangle([a, b], fill=fill, outline=outline, width=width)

    def text(self, x, y, s, size=11, color=(20, 20, 20), bold=False, anchor="mm", halo=True):
        f = font(size * 2, bold)
        p = self.P(x, y)
        if halo:
            self.d.text(p, s, font=f, fill=color, anchor=anchor, stroke_width=4, stroke_fill=(255, 255, 255))
        else:
            self.d.text(p, s, font=f, fill=color, anchor=anchor)

    def board(self, color=BOARD):
        self.d.rounded_rectangle([self.P(X0, Y0), self.P(X1, Y1)], radius=1.5 * self.s, fill=color, outline=EDGE, width=3)

    def pad(self, p, color):
        cx, cy = self.P(p["x"], p["y"])
        sx, sy = p["sx"] * self.s / 2, p["sy"] * self.s / 2
        if p["round"] and abs(p["sx"] - p["sy"]) < 0.01:
            self.d.ellipse([cx - sx, cy - sy, cx + sx, cy + sy], fill=color)
        else:
            rot = math.radians(p["rot"])
            pts = []
            for ux, uy in ((-sx, -sy), (sx, -sy), (sx, sy), (-sx, sy)):
                pts.append((cx + ux * math.cos(rot) + uy * math.sin(rot), cy - ux * math.sin(rot) + uy * math.cos(rot)))
            self.d.polygon(pts, fill=color)
        if p["pth"]:
            r = p["drill"] * self.s / 2
            self.d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255))

    def save(self, name):
        img = self.img.resize((self.w // 2, self.h // 2), Image.LANCZOS)
        img.save(OUT / name)
        return OUT / name


def zone(name):
    return [z for z in G["zones"] if z["name"] == name]


# ------------------------------------------------------------------ 1. map of the parts
CATS = [
    ("2S-Leistung", (220, 70, 60), ["2S: Akku, Verpolschutz, Sicherung, Lastschalter", "2S: Servo-Schiene VSERVO", "Arming"]),
    ("Strommessung", (240, 150, 40), ["2S: Spannungsmessung, Shunt und INA239"]),
    ("1S-Versorgung", (235, 205, 50), ["1S: Akku, Verpolschutz, Sicherung, Lastschalter", "1S: Lader MCP73831",
                                        "1S: Buck-Boost U2 -> 5V_SYS, Teensy-VIN", "LDOs 3V3_RF und 3V3_EXP, Sensorinsel, Sternpunkt"]),
    ("Rechner, Logik", (70, 120, 220), ["Teensy 4.1", "CS-Decoder und Analogmux", "Messteiler am Analogmux"]),
    ("Sensoren", (60, 170, 90), ["IMU ICM-42688-P, SPI1", "Barometer BMP390, SPI1"]),
    ("Funk, GPS, Kamera", (150, 90, 200), ["LoRa E22-400T22S, Serial8", "GPS, Serial1", "Kamera"]),
    ("Servos, Motor", (40, 170, 180), ["Servos", "Rollmotor DRV8833"]),
    ("Pyro", (150, 60, 40), ["Pyro-Kanal 1", "Pyro-Kanal 2", "Pyro-Kanal 3", "Pyro-Kanal 4"]),
    ("Sonstiges", (150, 150, 160), ["Stapelstecker J_STACK, Befestigung, Testpunkte", "Status-LEDs", "Summer", "Qwiic, I2C"]),
]
GROUP = {p.ref: p.group for p in circuit.PARTS}
CAT_OF = {g: (name, col) for name, col, gs in CATS for g in gs}

CALLOUTS = [  # number, reference, short name, function
    ("J1", "XT30-Stecker", "2S-Akku (7,4 V) für Servos, Motor, Pyro"),
    ("Q1", "Verpolschutz 2S", "P-FET, sperrt bei falsch gepoltem Akku"),
    ("F1", "Sicherung 2S", "rückstellende Sicherung, 3 A Dauer, 6 A Auslösung"),
    ("Q6", "Lastschalter 2S", "schaltet den 2S-Pfad ein (Schalter SW)"),
    ("R_SH1", "Shunt 20 mΩ", "Messwiderstand für den Servostrom"),
    ("U6", "INA239", "misst Strom und Spannung am Shunt"),
    ("J18", "Ladebuchse 2S", "2S-Akku laden ohne Ausbau"),
    ("J2", "1S-Akku", "LiPo für Elektronik"),
    ("U11", "Lader MCP73831", "lädt den 1S-Akku über USB"),
    ("U2", "Buck-Boost TPS63070", "macht aus 3,0 bis 4,2 V stabil 5 V (5V_SYS)"),
    ("A1", "Teensy 4.1", "Hauptrechner, steckt auf zwei Buchsenleisten"),
    ("U4", "IMU ICM-42688-P", "Drehraten und Beschleunigung, auf der Rollachse"),
    ("U12", "CS-Decoder 74HC138", "wählt eines von 8 SPI-Geräten"),
    ("U13", "Analogmux 74HC4051", "schaltet 8 Messspannungen auf einen ADC-Pin"),
    ("U5", "Barometer BMP390", "Luftdruck, Höhe"),
    ("U10", "LoRa E22-400T22S", "Funk zur Bodenstation"),
    ("J11", "GPS", "Stecker für das GPS-Modul"),
    ("U7", "DRV8833", "Motortreiber für den Rollmotor"),
    ("J8", "Rollmotor", "Stecker des Rollmotors"),
    ("J5", "Servo Yaw", "TVC-Servo"),
    ("J6", "Servo Pitch", "TVC-Servo"),
    ("J7", "Servo Fallschirm", "Servo 3"),
    ("J16", "Servo Beine", "Servo 4"),
    ("J15", "J_STACK", "Stapelstecker zur oberen Platine"),
    ("J4", "Arming", "Schlüsselschalter: gibt die Pyro-Spannung frei"),
    ("J9", "Pyro 1", "Zünder-Stecker, darunter FET und Schutzdiode"),
    ("J20", "Pyro 4", "Zünder-Stecker (Pyro 3 und 4 unbestückt)"),
    ("BZ1", "Summer", "akustische Statusmeldung"),
    ("J12", "Qwiic", "I2C-Stecker für Erweiterungen"),
]


def fig_map():
    c = Canvas(X0, Y0, X1, Y1, 12)
    c.board()
    fps = {f["ref"]: f for f in G["footprints"]}
    for f in G["footprints"]:
        if f["ref"].startswith("H") or f["ref"] == "A1":
            continue
        name, col = CAT_OF.get(GROUP.get(f["ref"], ""), ("Sonstiges", (150, 150, 160)))
        x0, y0, x1, y1 = f["box"]
        c.rect(x0, y0, x1, y1, fill=col + (150,), outline=col + (255,), width=2)
    for f in G["footprints"]:
        if f["ref"].startswith("H"):
            c.circle(f["x"], f["y"], 1.6, fill=(255, 255, 255), outline=EDGE, width=3)
    a = fps["A1"]["box"]
    c.d.rectangle([c.P(a[0], a[1]), c.P(a[2], a[3])], outline=(70, 120, 220, 255), width=5)
    c.text((a[0] + a[2]) / 2, a[1] + 3.2, "Teensy 4.1 (steckt darüber)", 11, (40, 80, 170), True)
    for i, (ref, short, _) in enumerate(CALLOUTS, 1):
        f = fps[ref]
        x, y = (f["box"][0] + f["box"][2]) / 2, (f["box"][1] + f["box"][3]) / 2
        if ref == "A1":
            y = a[1] + 7.0
        c.circle(x, y, 1.45, fill=(25, 25, 35), outline=(255, 255, 255), width=3)
        c.text(x, y, str(i), 9, (255, 255, 255), True, halo=False)
    c.text((X0 + X1) / 2, Y0 - 0.0 + 0.0 - 0.3, "", 1)
    return c.save("map.png")


def fig_map_legend():
    w, h = 900, 64 + 34 * len(CATS) // 3 * 1
    img = Image.new("RGB", (1500, 120), BG)
    d = ImageDraw.Draw(img)
    f = font(26)
    x, y = 10, 14
    for i, (name, col, _) in enumerate(CATS):
        if i == 5:
            x, y = 10, 70
        d.rectangle([x, y, x + 34, y + 34], fill=col, outline=(60, 60, 60))
        d.text((x + 44, y + 17), name, font=f, fill=(20, 20, 20), anchor="lm")
        x += 50 + d.textlength(name, font=f) + 30
    img = img.crop((0, 0, 1500, 115))
    img.save(OUT / "map_legend.png")
    return OUT / "map_legend.png"


# ------------------------------------------------------------------ 2. stackup cross section
def fig_stack():
    W, H = 1500, 800
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    left, right = 60, 900
    layers = [  # name, thickness in um, kind
        ("Lötstopplack oben", 10, "mask"), ("F.Cu  (35 µm Kupfer)", 35, "cu", "F.Cu"),
        ("Prepreg 0,21 mm", 210, "pp"), ("In1.Cu (15 µm Kupfer)", 15, "cu", "In1.Cu"),
        ("Kern 1,07 mm", 1065, "core"), ("In2.Cu (15 µm Kupfer)", 15, "cu", "In2.Cu"),
        ("Prepreg 0,21 mm", 210, "pp"), ("B.Cu  (35 µm Kupfer)", 35, "cu", "B.Cu"), ("Lötstopplack unten", 10, "mask")]
    role = {"F.Cu": "Bauteile, Signale, Strompfade als Flächen", "In1.Cu": "durchgehende GND-Fläche",
            "In2.Cu": "zweite Signallage, Rest GND", "B.Cu": "Versorgungsflächen GND_PWR und 5V_SYS"}
    # draw with exaggerated copper: copper fixed 34 px, dielectric scaled
    y = 40
    rows = []
    for L in layers:
        if L[2] == "cu":
            h = 60
            col = LAYER_COL[L[3]]
        elif L[2] == "mask":
            h = 30
            col = (60, 80, 200)
        else:
            h = 200 if L[2] == "core" else 70
            col = (214, 196, 140) if L[2] == "core" else (230, 214, 165)
        rows.append((y, h, L, col))
        y += h
    for y0, h, L, col in rows:
        if L[2] == "cu" and L[3] in ("In1.Cu", "B.Cu"):
            d.rectangle([left, y0, right, y0 + h], fill=col)
        elif L[2] == "cu":
            for a, b in ((left, 240), (300, 420), (470, 520), (580, 760), (820, right)):
                d.rectangle([a, y0, b, y0 + h], fill=col)
        else:
            d.rectangle([left, y0, right, y0 + h], fill=col)
        if L[2] == "cu":
            d.text((right + 30, y0 + 18), L[0], font=font(26, True), fill=(20, 20, 20), anchor="lm")
            d.text((right + 30, y0 + 46), role[L[3]], font=font(22), fill=(80, 80, 80), anchor="lm")
        else:
            d.text((right + 30, y0 + h / 2), L[0], font=font(22), fill=(70, 70, 70), anchor="lm")
    top, bot = rows[1][0], rows[7][0] + rows[7][1]
    # through via
    vx = 545
    d.rectangle([vx - 22, top, vx + 22, bot], fill=(190, 150, 60))
    d.rectangle([vx - 12, top, vx + 12, bot], fill=(255, 255, 255))
    for yy in (rows[1][0], rows[3][0], rows[5][0], rows[7][0]):
        d.rectangle([vx - 34, yy, vx + 34, yy + 60], fill=(190, 150, 60))
    d.rectangle([vx - 12, top, vx + 12, bot], fill=(255, 255, 255))
    d.text((vx, bot + 78), "Via: Bohrung 0,3 mm,", font=font(24), fill=(20, 20, 20), anchor="mm")
    d.text((vx, bot + 108), "innen verkupfert", font=font(24), fill=(20, 20, 20), anchor="mm")
    d.text((left, bot + 78), "gesamt etwa 1,6 mm", font=font(24, True), fill=(20, 20, 20), anchor="lm")
    d.text((left, bot + 108), "(Höhen nicht maßstäblich)", font=font(22), fill=(110, 110, 110), anchor="lm")
    img.save(OUT / "stack.png")
    return OUT / "stack.png"


# ------------------------------------------------------------------ 3. the four layers side by side
def fig_layers():
    names = [("layer_F_Cu.png", "F.Cu (oben)"), ("layer_In1_Cu.png", "In1.Cu: GND"),
             ("layer_In2_Cu.png", "In2.Cu: Signale"), ("layer_B_Cu.png", "B.Cu: Versorgung")]
    ims = [Image.open(HERE / "img" / n).convert("RGB") for n, _ in names]
    w, h = ims[0].size
    sc = 0.62
    tw, th = int(w * sc), int(h * sc)
    out = Image.new("RGB", (4 * tw + 5 * 20, th + 70), BG)
    d = ImageDraw.Draw(out)
    for i, (im, (_, title)) in enumerate(zip(ims, names)):
        out.paste(im.resize((tw, th), Image.LANCZOS), (20 + i * (tw + 20), 60))
        d.text((20 + i * (tw + 20) + tw / 2, 30), title, font=font(28, True), fill=(20, 20, 20), anchor="mm")
    out.save(OUT / "layers4.png")
    return OUT / "layers4.png"


# ------------------------------------------------------------------ 4. current paths
POWER = [("VBAT2_RAW", (230, 60, 60)), ("VBAT2_REV", (240, 110, 60)), ("VBAT2_F", (245, 150, 50)),
         ("VBAT_PROT", (200, 40, 120)), ("VBAT_ARMED", (150, 40, 170)), ("VSERVO", (40, 150, 210)),
         ("PYRO1_NEG", (120, 80, 40)), ("PYRO2_NEG", (120, 80, 40)), ("PYRO3_NEG", (120, 80, 40)),
         ("PYRO4_NEG", (120, 80, 40)), ("VSYS_IN", (60, 170, 80))]


def faint_copper(c, layer="F.Cu", col=(175, 180, 190)):
    for t in G["tracks"]:
        if t["layer"] == layer:
            c.line(t["x1"], t["y1"], t["x2"], t["y2"], t["w"], col + (255,))
    for f in G["footprints"]:
        for p in f["pads"]:
            if layer in p["layers"]:
                c.pad(p, (160, 165, 175, 255))


def fig_power():
    c = Canvas(X0, Y0, X1, Y1, 12)
    c.board()
    faint_copper(c)
    for net, col in POWER:
        for z in G["zones"]:
            if z["net"] == net and z["layer"] == "F.Cu" and z["name"].endswith("Strompfad"):
                c.fills(z["fill"], col + (235,))
        for t in G["tracks"]:
            if t["net"] == net and t["layer"] == "F.Cu":
                c.line(t["x1"], t["y1"], t["x2"], t["y2"], t["w"], col + (255,))
    lab = [(142.0, 158.6, "VBAT2_RAW (XT30)"), (133.0, 147.2, "VBAT2_REV / F"), (147.0, 142.6, "VBAT_PROT"),
           (147.6, 118.0, "VBAT_PROT"), (151.0, 104.0, "VSERVO"), (124.0, 140.0, "VSERVO-Bus"),
           (118.0, 164.0, "VSERVO zu den Servos"), (127.0, 55.2, "VBAT_ARMED"), (111.0, 61.5, "PYRO_NEG"),
           (108.5, 133.5, "VSYS_IN")]
    for x, y, s in lab:
        c.text(x, y, s, 10, (20, 20, 20), True)
    return c.save("power.png")


def fig_planes():
    imgs = []
    for layer, parts, title in (("In1.Cu", [("GND In1.Cu", (150, 150, 160))], "In1.Cu: GND"),
                                ("B.Cu", [("GND_PWR B.Cu", (30, 150, 85)), ("5V_SYS B.Cu", (240, 150, 40))],
                                 "B.Cu: GND_PWR und 5V_SYS")):
        c = Canvas(X0, Y0, X1, Y1, 7)
        c.board()
        for name, col in parts:
            for z in zone(name):
                c.fills(z["fill"], col + (255,))
        for v in G["vias"]:
            c.circle(v["x"], v["y"], 0.3, fill=(255, 255, 255, 255))
        imgs.append((c.save(f"plane_{layer[:3]}.png"), title))
    ims = [Image.open(p) for p, _ in imgs]
    w, h = ims[0].size
    out = Image.new("RGB", (2 * w + 60, h + 60), BG)
    d = ImageDraw.Draw(out)
    for i, (im, (_, t)) in enumerate(zip(ims, imgs)):
        out.paste(im, (20 + i * (w + 20), 50))
        d.text((20 + i * (w + 20) + w / 2, 25), t, font=font(24, True), fill=(20, 20, 20), anchor="mm")
    # labels on B.Cu half
    def lbl(x, y, s):
        px = 20 + w + 20 + (x - X0) * 7 + 8
        py = 50 + (y - Y0) * 7 + 8
        d.text((px, py), s, font=font(20, True), fill=(20, 20, 20), anchor="mm", stroke_width=3, stroke_fill=(255, 255, 255))
    lbl(127, 165, "GND_PWR"), lbl(147, 100, "GND_PWR"), lbl(127, 55, "GND_PWR"), lbl(110, 120, "5V_SYS"), lbl(127, 125, "5V_SYS")
    out.save(OUT / "planes.png")
    return OUT / "planes.png"


# ------------------------------------------------------------------ 5. zooms: layer changes
def zoom(name, x0, y0, x1, y1, s, layers, hl, labels=(), show_rules=False, circles=()):
    c = Canvas(x0, y0, x1, y1, s, margin=4)
    c.d.rectangle([0, 0, c.w, c.h], fill=BOARD)
    order = ["B.Cu", "In2.Cu", "F.Cu"]
    for layer in order:
        if layer not in layers:
            continue
        col = LAYER_COL[layer]
        faded = tuple(int(v * 0.35 + 255 * 0.65) for v in col)
        for z in G["zones"]:
            if z["layer"] == layer and z["name"].endswith("Strompfad"):
                c.fills(z["fill"], faded + (255,))
        for t in G["tracks"]:
            if t["layer"] == layer:
                strong = t["net"] in hl
                c.line(t["x1"], t["y1"], t["x2"], t["y2"], t["w"], (col if strong else faded) + (255,))
        if layer == "F.Cu":
            for f in G["footprints"]:
                for p in f["pads"]:
                    if "F.Cu" in p["layers"]:
                        c.pad(p, ((205, 160, 60) if p["net"] in hl else (215, 200, 170)) + (255,))
    for v in G["vias"]:
        strong = v["net"] in hl
        c.circle(v["x"], v["y"], v["d"] / 2, fill=(VIA if strong else (225, 215, 185)) + (255,),
                 outline=(90, 70, 20, 255) if strong else (170, 160, 140, 255), width=2)
        c.circle(v["x"], v["y"], v["drill"] / 2, fill=(255, 255, 255, 255))
    if show_rules:
        for r in G["rules"]:
            for ring, holes in r["poly"]:
                pts = [c.P(x, y) for x, y in ring]
                c.d.line(pts + pts[:1], fill=(200, 0, 200, 255), width=3)
    for cx, cy, r, col, lab in circles:
        c.circle(cx, cy, r, outline=col + (255,), width=4)
    for x, y, s_, sz in labels:
        c.text(x, y, s_, sz, (15, 15, 15), True)
    return c.save(name)


def fig_zooms():
    out = {}
    out["pyro3"] = zoom("zoom_pyro3.png", 127.5, 61.5, 138.5, 76.0, 46, ["F.Cu", "In2.Cu"],
                        {"PYRO3_NEG", "PYRO3_SENSE"},
                        [(130.2, 63.2, "Q8 (FET)", 9), (133.35, 70.4, "D5", 9), (136.6, 65.6, "R40", 9),
                         (134.5, 69.9, "", 9)])
    out["drv"] = zoom("zoom_drv.png", 135.5, 111.0, 150.0, 123.0, 42, ["F.Cu", "In2.Cu", "B.Cu"],
                      {"MOT_A", "MOT_B"},
                      [(143.5, 111.8, "U7 DRV8833", 10), (139.4, 122.6, "J8.1", 9), (141.9, 122.6, "J8.2", 9)])
    ix, iy = [(f["x"], f["y"]) for f in G["footprints"] if f["ref"] == "U4"][0]
    out["imu"] = zoom("zoom_imu.png", ix - 6.5, iy - 6.5, ix + 6.5, iy + 6.5, 40, ["F.Cu", "In2.Cu"],
                      {"GND", "SPI1_SCK", "SPI1_MOSI", "SPI1_MISO", "CS_IMU", "IMU_INT"},
                      [(ix, iy - 5.6, "5 mm: keine fremden Vias, kein In2", 9)],
                      circles=[(ix, iy, 5.0, (200, 0, 200), ""), (ix, iy, 2.6, (230, 120, 0), "")])
    return out


# ------------------------------------------------------------------ 6. the process
def fig_pipeline():
    steps = [("circuit.py", "Schaltung als Code:\nBauteile, Pins, Netze"),
             ("gen_schematic.py", "Schaltplan erzeugen,\nERC, Netzliste prüfen"),
             ("gen_pcb.py place", "Bauteile setzen, Strompfade\nals Flächen, Sperrflächen"),
             ("Freerouting", "Autorouter verlegt\ndie Signale (≈ 17 min)"),
             ("merge, patch", "Ergebnis übernehmen,\nkleine Lücken schließen"),
             ("DRC", "KiCad prüft Abstände,\nVerbindungen, Schaltplan"),
             ("Nacharbeit", "Rest von Hand und mit\neigenem Gitter-Router"),
             ("silk, img", "Bestückungsdruck,\nBilder, Prüfskript")]
    W, H = 1600, 520
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    bw, bh, gap = 340, 170, 50
    for i, (t, s) in enumerate(steps):
        row, col = divmod(i, 4)
        if row == 1:
            col = 3 - col
        x = 30 + col * (bw + gap)
        y = 30 + row * (bh + 120)
        fill = (225, 235, 250) if i not in (5,) else (230, 245, 230)
        d.rounded_rectangle([x, y, x + bw, y + bh], radius=18, fill=fill, outline=(70, 100, 160), width=3)
        d.text((x + bw / 2, y + 40), t, font=font(30, True), fill=(20, 40, 90), anchor="mm")
        d.multiline_text((x + bw / 2, y + 108), s, font=font(24), fill=(40, 40, 40), anchor="mm", align="center")
        if i < len(steps) - 1:
            if i == 3:
                d.line([(x + bw / 2, y + bh), (x + bw / 2, y + bh + 120)], fill=(70, 100, 160), width=5)
                d.polygon([(x + bw / 2 - 14, y + bh + 100), (x + bw / 2 + 14, y + bh + 100), (x + bw / 2, y + bh + 120)], fill=(70, 100, 160))
            elif row == 0:
                d.line([(x + bw, y + bh / 2), (x + bw + gap, y + bh / 2)], fill=(70, 100, 160), width=5)
                d.polygon([(x + bw + gap - 18, y + bh / 2 - 12), (x + bw + gap - 18, y + bh / 2 + 12), (x + bw + gap, y + bh / 2)], fill=(70, 100, 160))
            else:
                d.line([(x, y + bh / 2), (x - gap, y + bh / 2)], fill=(70, 100, 160), width=5)
                d.polygon([(x - gap + 18, y + bh / 2 - 12), (x - gap + 18, y + bh / 2 + 12), (x - gap, y + bh / 2)], fill=(70, 100, 160))
    img.save(OUT / "pipeline.png")
    return OUT / "pipeline.png"


def build_all():
    return {"map": fig_map(), "legend": fig_map_legend(), "stack": fig_stack(), "layers": fig_layers(),
            "power": fig_power(), "planes": fig_planes(), "pipeline": fig_pipeline(), **fig_zooms()}


if __name__ == "__main__":
    for k, v in build_all().items():
        print(k, v)
