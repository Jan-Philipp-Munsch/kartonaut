"""Figures for the mainboard rev B design guide (docs/DesignGuide_Mainboard_revB.md).

Writes SVGs into hardware/mainboard/img/. No dependencies; the placement plan and the
cross-section come from outline.py, this script draws everything else:

  system_blocks.svg      block diagram of the electronics
  power_tree.svg         both battery paths, converters, rails and loads
  pyro_channel.svg       one pyro channel with arming, FET, TVS and continuity sense
  teensy_pinmap.svg      Teensy 4.1 pin assignment of rev B
  installation_side.svg  side view of the sled inside the coupler (batteries, antenna, hatch)
  order_flow.svg         the way from the specification to the commissioned board

Run:  python hardware/mainboard/figures.py
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
IMG = HERE / "img"
FONT = 'font-family="Helvetica,Arial,sans-serif"'

# palette: one colour per domain, used identically in all figures
C_PWR1 = "#f4d6a0"   # 1S path / 5V_SYS (electronics)
C_PWR2 = "#f6c4c4"   # 2S path / actuators / pyro
C_SENS = "#c9e4c5"   # sensors
C_RF = "#cfe0f5"     # radio / GPS
C_MCU = "#9fc0e0"    # Teensy
C_SIG = "#e3d9f2"    # indicators / signals
C_LINE = "#333"
C_GREY = "#888"


class SVG:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" {FONT}>',
                    '<defs><marker id="arr" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">'
                    f'<path d="M0,0 L8,4 L0,8 z" fill="{C_LINE}"/></marker>'
                    '<marker id="arrg" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">'
                    f'<path d="M0,0 L8,4 L0,8 z" fill="{C_GREY}"/></marker></defs>',
                    '<rect width="100%" height="100%" fill="white"/>']

    def box(self, x, y, w, h, title, lines=(), fill="#eee", stroke=C_LINE, title_size=12, size=10, rx=4, bold=True):
        self.out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>')
        cx = x + w / 2
        n = len(lines)
        total = title_size + 4 + n * (size + 3)
        ty = y + (h - total) / 2 + title_size
        fw = ' font-weight="bold"' if bold else ''
        self.out.append(f'<text x="{cx}" y="{ty:.1f}" font-size="{title_size}"{fw} text-anchor="middle">{esc(title)}</text>')
        for i, ln in enumerate(lines):
            self.out.append(f'<text x="{cx}" y="{ty + title_size - 2 + (i + 1) * (size + 3) - size + 2:.1f}" font-size="{size}" '
                            f'text-anchor="middle" fill="#222">{esc(ln)}</text>')

    def text(self, x, y, s, size=10, anchor="start", bold=False, fill="#222", rotate=None, italic=False):
        fw = ' font-weight="bold"' if bold else ''
        fi = ' font-style="italic"' if italic else ''
        tr = f' transform="rotate({rotate} {x} {y})"' if rotate is not None else ''
        self.out.append(f'<text x="{x}" y="{y}" font-size="{size}"{fw}{fi} text-anchor="{anchor}" fill="{fill}"{tr}>{esc(s)}</text>')

    def line(self, pts, arrow=False, stroke=C_LINE, width=1.4, dash=None, grey=False):
        d = "M" + " L".join(f"{x},{y}" for x, y in pts)
        m = ' marker-end="url(#arrg)"' if (arrow and grey) else (' marker-end="url(#arr)"' if arrow else '')
        ds = f' stroke-dasharray="{dash}"' if dash else ''
        self.out.append(f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{width}"{m}{ds}/>')

    def label(self, x, y, s, size=9, anchor="middle", fill="#444"):
        self.text(x, y, s, size=size, anchor=anchor, fill=fill)

    def rect(self, x, y, w, h, fill="none", stroke=C_LINE, width=1, rx=0, dash=None, opacity=None):
        ds = f' stroke-dasharray="{dash}"' if dash else ''
        op = f' fill-opacity="{opacity}"' if opacity is not None else ''
        self.out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"{ds}{op}/>')

    def circle(self, x, y, r, fill="white", stroke=C_LINE, width=1):
        self.out.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')

    def raw(self, s):
        self.out.append(s)

    def save(self, name):
        self.out.append("</svg>")
        (IMG / name).write_text("\n".join(self.out), encoding="utf-8")


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ----------------------------------------------------------------------------------------------
def system_blocks():
    g = SVG(940, 560)
    g.text(20, 26, "Mainboard rev B: Blockschaltbild", 15, bold=True)
    g.text(20, 44, "Alles auf einer Platine 54 × 120 mm; extern nur Akkus, Schalter, Servos, Motor, E-Matches, GPS und Antenne.", 10, fill="#555")

    # Teensy in the centre
    tx, ty, tw, th = 360, 190, 220, 180
    g.box(tx, ty, tw, th, "Teensy 4.1", ["i.MX RT1062, 600 MHz", "microSD (SDIO), USB", "W25Q128 Flash (LittleFS)",
                                          "100-Hz-Flugschleife", "Watchdog, Zustandsspeicher"], fill=C_MCU, title_size=14)

    # left column: power
    g.box(30, 80, 150, 70, "1S LiPo", ["3,0–4,2 V, 450–600 mAh", "JST-PH"], fill=C_PWR1)
    g.box(30, 170, 150, 70, "2S LiPo", ["6,0–8,4 V, 450–850 mAh", "XT30"], fill=C_PWR2)
    g.box(30, 270, 150, 60, "Hauptschalter", ["zweipolig, J_SW", "JP1/JP2 am Tisch"], fill="#eee")
    g.box(30, 350, 150, 60, "Arming", ["Schalter J_ARM", "ARM_SENSE → Pin 24"], fill=C_PWR2)

    g.box(210, 80, 120, 70, "TPS63070", ["Buck-Boost 5 V / 2 A", "5V_SYS"], fill=C_PWR1)
    g.box(210, 170, 120, 70, "INA219 + 20 mΩ", ["Strom, Spannung 2S", "I²C 0x40"], fill=C_PWR2)
    g.box(210, 260, 120, 60, "TPS563201", ["Buck 5 V / 3 A", "5V_SERVO"], fill=C_PWR2)
    g.box(210, 340, 120, 60, "AP2112K", ["LDO 3,3 V / 0,6 A", "3V3_RF"], fill=C_PWR1)

    # power arrows
    g.line([(180, 115), (210, 115)], arrow=True)
    g.line([(180, 205), (210, 205)], arrow=True)
    g.line([(270, 150), (270, 160)], arrow=False, grey=True, stroke=C_GREY)
    g.line([(330, 115), (360, 115), (360, 190)], arrow=True)          # 5V_SYS -> VIN
    g.label(345, 108, "5V_SYS → VIN", anchor="start")
    g.line([(270, 240), (270, 260)], arrow=True)
    g.line([(330, 290), (348, 290), (348, 470), (380, 470)], arrow=True)   # 5V_SERVO -> actuators
    g.line([(330, 205), (348, 205), (348, 290)], arrow=False)             # VSERVO
    g.label(300, 332, "VSERVO (Akku direkt)", anchor="start", size=8)
    g.line([(270, 150), (195, 150), (195, 370), (210, 370)], arrow=True, grey=True, stroke=C_GREY)

    # right column: sensors and radio
    g.box(640, 80, 150, 70, "ICM-42688-P", ["IMU auf der Rollachse", "SPI1 7 MHz, INT Pin 4"], fill=C_SENS)
    g.box(640, 170, 150, 60, "BMP390", ["Barometer, I²C 0x77", "unter Schaum"], fill=C_SENS)
    g.box(640, 250, 150, 60, "Qwiic / J_EXP", ["I²C-Erweiterung", "11 freie Pins"], fill=C_SENS)
    g.line([(580, 115), (640, 115)], arrow=True)
    g.label(610, 108, "SPI1", size=8)
    g.line([(580, 200), (640, 200)], arrow=True)
    g.label(610, 193, "I²C0", size=8)
    g.line([(610, 200), (610, 280), (640, 280)], arrow=True)

    g.box(640, 395, 150, 70, "LoRa E22-400T22S", ["SX1268, 433 MHz, 22 dBm", "Serial8, M0/M1/AUX, 3V3_RF", "IPEX → Antenne in der Spitze"], fill=C_RF)
    g.box(820, 395, 100, 70, "GPS-Modul", ["u-blox M9/M10, 3V3_RF", "in der Spitze", "Serial1, J_GPS"], fill=C_RF)
    g.line([(560, 370), (560, 430), (640, 430)], arrow=True)
    g.label(600, 423, "UART8", size=8)
    g.line([(560, 430), (560, 500), (870, 500), (870, 465)], arrow=True)
    g.label(715, 494, "UART1 über J_GPS", size=8)

    # bottom: actuators and pyro
    g.box(380, 440, 110, 60, "2× W5652H", ["TVC-Servos", "an VSERVO (8,4 V)"], fill=C_PWR2)
    g.box(500, 440, 110, 60, "DRV8833", ["Rollmotor", "an 5V_SERVO"], fill=C_PWR2)
    g.line([(420, 370), (420, 440)], arrow=True)
    g.label(432, 410, "PWM 28/29", size=8, anchor="start")
    g.line([(540, 370), (540, 440)], arrow=True)
    g.label(548, 410, "PWM 2/3", size=8, anchor="start")

    g.box(640, 320, 150, 60, "2× Pyro-Kanal", ["AO3400A low-side, TVS", "Durchgang → ADC 20/21"], fill=C_PWR2)
    g.line([(580, 340), (640, 340)], arrow=True)
    g.label(610, 333, "22 / 23", size=8)
    g.line([(180, 380), (195, 380), (195, 520), (715, 520), (715, 380)], arrow=True, stroke="#b03a2e")
    g.label(455, 514, "VBAT_ARMED nur mit Arming-Schalter", size=8, fill="#b03a2e")

    # indicators
    g.box(820, 80, 100, 70, "Signale", ["2× WS2812B", "Summer", "Reset-Taster"], fill=C_SIG)
    g.line([(470, 190), (470, 60), (870, 60), (870, 80)], arrow=True, grey=True, stroke=C_GREY)
    g.label(680, 54, "Pins 5, 6, 13", size=8, fill=C_GREY)
    g.box(820, 250, 100, 60, "J_CAM, J_LED", ["Kamera-Auslöser", "externe LEDs"], fill=C_SIG)

    # legend
    lx, ly = 30, 440
    g.text(lx, ly - 8, "Farben", 10, bold=True)
    for i, (c, t) in enumerate([(C_PWR1, "1S-Pfad: Elektronik"), (C_PWR2, "2S-Pfad: Aktoren, Pyro"), (C_SENS, "Sensorik"),
                                (C_RF, "Funk, GPS"), (C_SIG, "Anzeige, Erweiterung")]):
        g.rect(lx, ly + i * 18, 14, 12, fill=c, stroke="#777")
        g.text(lx + 20, ly + 10 + i * 18, t, 9)
    g.save("system_blocks.svg")


# ----------------------------------------------------------------------------------------------
def power_tree():
    g = SVG(1160, 600)
    g.text(20, 26, "Stromversorgung: zwei Akkus, vier Schienen", 15, bold=True)
    g.text(20, 44, "Der 1S-Pfad sieht keine Servo- und Pyro-Spitzen. Beide Massen treffen sich an einem Sternpunkt am 2S-Minus neben dem Shunt.", 10, fill="#555")

    # --- 1S path (top)
    y1 = 90
    g.rect(20, y1 - 25, 1120, 190, fill=C_PWR1, stroke="none", opacity=0.35, rx=8)
    g.text(30, y1 - 8, "1S-Pfad: Elektronik", 12, bold=True)
    chain1 = [("1S LiPo", ["3,0–4,2 V", "JST-PH"]), ("Q2 AO3401A", ["Verpolschutz"]), ("SW1a", ["Hauptschalter", "oder JP1"]),
              ("TPS63070", ["Buck-Boost", "2–16 V → 5 V / 2 A", "1,5 µH"]), ("5V_SYS", ["1000 µF Polymer", "Testpunkt"])]
    x = 30
    for i, (t, ls) in enumerate(chain1):
        w = 120 if i == 3 else 100
        g.box(x, y1, w, 60, t, ls, fill="white" if i else C_PWR1)
        if i < len(chain1) - 1:
            g.line([(x + w, y1 + 30), (x + w + 18, y1 + 30)], arrow=True)
        x += w + 18
    xr = x - 18  # right end of the 5V_SYS box
    loads1 = [("Teensy VIN", "über D1 SS14; USB darf stecken"), ("2× WS2812B, Summer", "74AHCT1G125, AO3400A"),
              ("AP2112K-3.3 → 3V3_RF", "100 µF: LoRa E22, GPS")]
    for i, (t, s) in enumerate(loads1):
        yy = y1 + 5 + i * 50 - 10
        g.line([(xr, y1 + 30), (xr + 20, y1 + 30), (xr + 20, yy + 15), (xr + 40, yy + 15)], arrow=True)
        g.box(xr + 40, yy, 230, 32, t, [s], fill="white", title_size=11, size=9)
    g.text(30, y1 + 85, "Teensy 3V3 (≤ 250 mA) → ICM-42688-P, BMP390, INA219, I²C-Pull-ups", 9, fill="#444")
    g.text(30, y1 + 100, "Teiler 100 k / 33 k von VSYS_IN → Pin 41 (VBAT1_SENSE)", 9, fill="#444")
    g.text(30, y1 + 125, "Dauer 0,4 A an 5 V (0,6 A aus dem Akku), Spitze 0,8 A beim LoRa-Sendepuls", 9, fill="#444", italic=True)

    # --- 2S path (bottom)
    y2 = 310
    g.rect(20, y2 - 25, 1120, 290, fill=C_PWR2, stroke="none", opacity=0.35, rx=8)
    g.text(30, y2 - 8, "2S-Pfad: Servos, Rollmotor, Pyro", 12, bold=True)
    chain2 = [("2S LiPo", ["6,0–8,4 V", "XT30"]), ("Q1 AO3401A", ["Verpolschutz"]), ("SW1b", ["Hauptschalter", "oder JP2"]),
              ("VBAT_PROT", ["Teiler → Pin 40"])]
    x = 30
    for i, (t, ls) in enumerate(chain2):
        w = 100
        g.box(x, y2, w, 60, t, ls, fill="white" if i else C_PWR2)
        if i < len(chain2) - 1:
            g.line([(x + w, y2 + 30), (x + w + 18, y2 + 30)], arrow=True)
        x += w + 18
    xp = x - 18
    # arming branch (up)
    g.line([(xp, y2 + 30), (xp + 20, y2 + 30), (xp + 20, y2 - 5), (xp + 40, y2 - 5)], arrow=True, stroke="#b03a2e")
    g.box(xp + 40, y2 - 20, 100, 32, "J_ARM", ["Arming-Schalter"], fill="white", title_size=11, size=9, stroke="#b03a2e")
    g.line([(xp + 140, y2 - 4), (xp + 160, y2 - 4)], arrow=True, stroke="#b03a2e")
    g.box(xp + 160, y2 - 20, 150, 32, "VBAT_ARMED", ["Pyro 1 / 2 (+), SMBJ12A"], fill="white", title_size=11, size=9, stroke="#b03a2e")
    g.text(xp + 320, y2 - 2, "Teiler → Pin 24 (ARM_SENSE); Zündstrom läuft nicht durch den Shunt", 9, fill="#b03a2e")
    # shunt branch (down)
    g.line([(xp + 20, y2 + 30), (xp + 20, y2 + 80), (xp + 40, y2 + 80)], arrow=True)
    g.box(xp + 40, y2 + 60, 110, 40, "R_SHUNT 20 mΩ", ["2512, Kelvin, INA219"], fill="white", title_size=11, size=9)
    g.line([(xp + 150, y2 + 80), (xp + 170, y2 + 80)], arrow=True)
    g.box(xp + 170, y2 + 60, 90, 40, "VBAT_MEAS", [], fill="white", title_size=11)
    xm = xp + 260
    g.line([(xm, y2 + 80), (xm + 20, y2 + 80), (xm + 20, y2 + 60), (xm + 40, y2 + 60)], arrow=True)
    g.box(xm + 40, y2 + 40, 110, 40, "F1 Polyfuse 3 A", ["→ VSERVO"], fill="white", title_size=11, size=9)
    g.line([(xm + 150, y2 + 60), (xm + 170, y2 + 60)], arrow=True)
    g.box(xm + 170, y2 + 40, 200, 40, "VSERVO = Akku direkt", ["1000 µF Low-ESR: 2× W5652H (TVC)"], fill="white", title_size=11, size=9)
    g.line([(xm + 20, y2 + 80), (xm + 20, y2 + 130), (xm + 40, y2 + 130)], arrow=True)
    g.box(xm + 40, y2 + 110, 110, 40, "TPS563201", ["Buck 5 V / 3 A, 2,2 µH"], fill="white", title_size=11, size=9)
    g.line([(xm + 150, y2 + 130), (xm + 170, y2 + 130)], arrow=True)
    g.box(xm + 170, y2 + 110, 200, 40, "5V_SERVO", ["470 µF: J_SERVO3 (Reserve), DRV8833"], fill="white", title_size=11, size=9)
    # budget table
    g.text(30, y2 + 130, "Strombudget 2S", 10, bold=True)
    rows = [("VSERVO", "2× W5652H, Blockierstrom je ~1 A", "0,2 A", "2 A"),
            ("5V_SERVO", "Fallschirm-Servo 0,65 A, Rollmotor ~1 A", "0,3 A", "1,7 A"),
            ("Pyro", "E-Match 3–5 A für 20 ms", "–", "5 A")]
    g.text(30, y2 + 148, "Schiene", 9, bold=True); g.text(100, y2 + 148, "Verbraucher", 9, bold=True)
    g.text(330, y2 + 148, "Dauer", 9, bold=True); g.text(380, y2 + 148, "Spitze", 9, bold=True)
    for i, r in enumerate(rows):
        yy = y2 + 164 + i * 15
        g.text(30, yy, r[0], 9); g.text(100, yy, r[1], 9); g.text(330, yy, r[2], 9); g.text(380, yy, r[3], 9)
    g.text(30, y2 + 235, "Firmware: beide Akkuspannungen per ADC, 2S-Strom per INA219 (bis 16 A, 2 mA Auflösung).", 9, fill="#444")
    g.text(30, y2 + 250, "Warnton bei 1S < 3,5 V oder 2S < 6,6 V; keine Startfreigabe ohne beide Akkus.", 9, fill="#444")
    # star point
    g.circle(xp + 20, y2 + 80, 4, fill="black")
    g.text(xp + 12, y2 + 98, "Sternpunkt GND", 8, fill="#444", anchor="end")
    g.save("power_tree.svg")


# ----------------------------------------------------------------------------------------------
def pyro_channel():
    g = SVG(760, 420)
    g.text(20, 26, "Ein Pyro-Kanal: vier Hürden vor der Zündung", 15, bold=True)
    g.text(20, 44, "Arming-Schalter (Hardware), Flugzustand und Puls ≤ 1 s (Firmware), Pull-down am Gate (Boot), TVS am Ausgang.", 10, fill="#555")

    # rails
    g.line([(60, 100), (640, 100)], stroke=C_LINE, width=1.6)
    g.text(60, 92, "VBAT_PROT (2S, 6–8,4 V)", 10, bold=True)
    # arming switch
    g.circle(250, 100, 4, fill="white"); g.circle(330, 100, 4, fill="white")
    g.line([(253, 99), (322, 78)], width=1.8, stroke="#b03a2e")
    g.text(290, 70, "J_ARM (extern)", 9, anchor="middle", fill="#b03a2e")
    g.rect(254, 96, 72, 8, fill="white", stroke="none")  # hide the rail under the open switch
    g.line([(334, 100), (640, 100)], width=1.6)
    g.text(400, 92, "VBAT_ARMED", 10, bold=True, fill="#b03a2e")
    # ARM_SENSE divider
    g.line([(560, 100), (560, 130)], width=1.2)
    g.rect(552, 130, 16, 30, fill="white"); g.text(575, 150, "100 k", 9)
    g.line([(560, 160), (560, 175)], width=1.2)
    g.rect(552, 175, 16, 30, fill="white"); g.text(575, 195, "33 k", 9)
    g.line([(560, 205), (560, 225)], width=1.2)
    g.text(560, 240, "GND", 9, anchor="middle")
    g.line([(560, 168), (610, 168)], arrow=True); g.text(615, 172, "Pin 24 ARM_SENSE", 9)

    # e-match
    g.line([(400, 100), (400, 140)], width=1.6)
    g.rect(380, 140, 40, 24, fill="#ffe", stroke=C_LINE, rx=3)
    g.text(400, 156, "E-Match", 9, anchor="middle")
    g.text(430, 156, "J_PYRO (JST-XH 2)", 9)
    g.line([(400, 164), (400, 220)], width=1.6)
    # TVS parallel to the output
    g.line([(400, 120), (340, 120), (340, 170)], width=1.2)
    g.raw('<path d="M332,186 L348,186 L340,170 z" fill="white" stroke="#333" stroke-width="1.2"/>')
    g.line([(332, 170), (348, 170)], width=1.4)
    g.line([(340, 186), (340, 220), (400, 220)], width=1.2)
    g.text(300, 182, "SMBJ12A", 9, anchor="end")
    # continuity divider from drain
    g.line([(400, 220), (470, 220), (470, 235)], width=1.2)
    g.rect(462, 235, 16, 28, fill="white"); g.text(485, 253, "100 k", 9)
    g.line([(470, 263), (470, 278)], width=1.2)
    g.rect(462, 278, 16, 28, fill="white"); g.text(485, 296, "33 k", 9)
    g.line([(470, 306), (470, 330)], width=1.2)
    g.line([(470, 270), (520, 270)], arrow=True); g.text(525, 274, "Pin 20/21 PYRO_SENSE", 9)
    # MOSFET
    g.line([(400, 220), (400, 250)], width=1.6)
    g.line([(400, 250), (400, 300)], width=2.2)        # channel
    g.line([(400, 300), (400, 330)], width=1.6)
    g.line([(386, 255), (386, 295)], width=2.2)        # gate plate
    g.line([(386, 275), (340, 275)], width=1.4)        # gate lead
    g.rect(300, 267, 40, 16, fill="white"); g.text(320, 279, "100 Ω", 9, anchor="middle")
    g.line([(300, 275), (250, 275)], width=1.4)
    g.text(245, 279, "Pin 22/23 PYRO_FIRE", 9, anchor="end")
    g.rect(270, 290, 16, 28, fill="white"); g.text(292, 308, "100 k", 9)
    g.line([(278, 275), (278, 290)], width=1.2); g.line([(278, 318), (278, 330)], width=1.2)
    g.text(380, 258, "AO3400A (30 V, 5,7 A)", 9, anchor="end")
    # ground
    g.line([(200, 330), (640, 330)], width=1.6)
    g.text(640, 345, "GND (Sternpunkt)", 9, anchor="end")
    for x in (278, 400, 470, 560):
        g.circle(x, 330 if x != 560 else 225, 3, fill="black")
    g.line([(560, 225), (560, 330)], width=1.2)

    # rules box
    g.rect(40, 360, 680, 48, fill="#f7f7f7", stroke="#bbb", rx=4)
    g.text(50, 377, "Firmware: Zünden nur in den Zuständen Apogäum oder Landung, Puls ≤ 1 s, jeder Kanal höchstens einmal,", 9.5)
    g.text(50, 391, "ohne ARM_SENSE keine Freigabe. Durchgang (PYRO_SENSE auf VBAT) wird vor dem Start per Summer gemeldet.", 9.5)
    g.text(50, 404, "Tischtest nur mit Glühlämpchen oder 2-Ω-Widerstand, nie mit Ladung.", 9.5, bold=True)
    g.save("pyro_channel.svg")


# ----------------------------------------------------------------------------------------------
PINS = {  # pin: (signal, target, domain colour, new?)
    0: ("RX1", "GPS TX (J_GPS)", C_RF, True), 1: ("TX1", "GPS RX (J_GPS)", C_RF, True),
    2: ("MOT_IN1", "DRV8833 AIN1 = BIN1", C_PWR2, False), 3: ("MOT_IN2", "DRV8833 AIN2 = BIN2", C_PWR2, False),
    4: ("IMU_INT", "ICM-42688-P INT1", C_SENS, True),
    5: ("LED1", "74AHCT1G125 → WS2812B", C_SIG, False), 6: ("LED2", "74AHCT1G125 → WS2812B, J_LED", C_SIG, False),
    7: ("CAM_TRIG", "1 kΩ → J_CAM", C_SIG, True), 8: ("frei", "J_EXP", "#eee", False),
    9: ("SERVO_CHUTE", "J_SERVO3 (5V_SERVO)", C_PWR2, False),
    10: ("frei", "J_EXP", "#eee", False), 11: ("frei", "J_EXP", "#eee", False), 12: ("frei", "J_EXP", "#eee", False),
    13: ("BUZZER", "AO3400A → Summer", C_SIG, False),
    14: ("frei", "J_EXP", "#eee", False), 15: ("frei", "J_EXP", "#eee", False), 16: ("frei", "J_EXP", "#eee", False), 17: ("frei", "J_EXP", "#eee", False),
    18: ("SDA0", "BMP390, INA219, J_QWIIC", C_SENS, False), 19: ("SCL0", "BMP390, INA219, J_QWIIC", C_SENS, False),
    20: ("PYRO1_SENSE", "Teiler Drain Pyro 1 (A6)", C_PWR2, True), 21: ("PYRO2_SENSE", "Teiler Drain Pyro 2 (A7)", C_PWR2, True),
    22: ("PYRO2_FIRE", "Gate Q_P2", C_PWR2, True), 23: ("PYRO1_FIRE", "Gate Q_P1", C_PWR2, False),
    24: ("ARM_SENSE", "Teiler VBAT_ARMED (A10)", C_PWR2, True), 25: ("frei", "J_EXP", "#eee", False),
    26: ("MOSI1", "ICM-42688-P SDI", C_SENS, True), 27: ("SCK1", "ICM-42688-P SCLK", C_SENS, True),
    28: ("SERVO_YAW", "J_SERVO1 (VSERVO)", C_PWR2, False), 29: ("SERVO_PITCH", "J_SERVO2 (VSERVO)", C_PWR2, False),
    30: ("frei", "J_EXP", "#eee", False), 31: ("frei", "J_EXP", "#eee", False),
    32: ("LORA_M1", "E22 M1", C_RF, True), 33: ("LORA_M0", "E22 M0", C_RF, True),
    34: ("RX8", "E22 TXD", C_RF, False), 35: ("TX8", "E22 RXD", C_RF, False),
    36: ("LORA_AUX", "E22 AUX", C_RF, True), 37: ("frei", "J_EXP", "#eee", False),
    38: ("CS1", "ICM-42688-P CS", C_SENS, True), 39: ("MISO1", "ICM-42688-P SDO", C_SENS, True),
    40: ("VBAT2_SENSE", "Teiler VBAT_PROT 2S (A16)", C_PWR2, True), 41: ("VBAT1_SENSE", "Teiler VSYS_IN 1S (A17)", C_PWR1, True),
}
# Teensy 4.1 header order (top view, USB up): left row GND,0..12,3V3,24..33 ; right row VIN,GND,3V3,23..14,A12?,...
LEFT = ["GND", 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, "3V3", 24, 25, 26, 27, 28, 29, 30, 31, 32]
RIGHT = ["VIN", "GND", "3V3", 23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, "GND", 41, 40, 39, 38, 37, 36, 35, 34, 33]


def teensy_pinmap():
    g = SVG(940, 700)
    g.text(20, 26, "Teensy 4.1: Pinbelegung rev B (Draufsicht, USB oben)", 15, bold=True)
    g.text(20, 44, "★ neu gegenüber Config.h. Alle bisher genutzten Pins bleiben, wo sie sind. Freie Pins liegen auf J_EXP (2×7).", 10, fill="#555")
    bx, by, bw, bh = 400, 70, 140, 600
    g.rect(bx, by, bw, bh, fill="#2e7d4f", stroke="#1b4d30", rx=6)
    g.rect(bx + 45, by - 8, 50, 22, fill="#bbb", stroke="#777", rx=2)
    g.text(bx + 70, by + 7, "USB", 9, anchor="middle")
    g.rect(bx + 40, by + bh - 30, 60, 26, fill="#444", stroke="#222", rx=2)
    g.text(bx + 70, by + bh - 13, "microSD", 9, anchor="middle", fill="white")
    g.text(bx + 70, by + 300, "Teensy 4.1", 14, anchor="middle", bold=True, fill="white", rotate=-90)
    g.text(bx + 90, by + 300, "(Buchsenleisten 2× 1×24)", 9, anchor="middle", fill="#dfe", rotate=-90)
    pitch = 24.0
    for i, (lp, rp) in enumerate(zip(LEFT, RIGHT)):
        y = by + 20 + i * pitch
        for side, p in (("L", lp), ("R", rp)):
            px = bx + 10 if side == "L" else bx + bw - 10
            g.circle(px, y, 4, fill="#ddd", stroke="#333")
            if isinstance(p, int):
                sig, tgt, col, new = PINS[p]
                star = " ★" if new else ""
                if side == "L":
                    g.rect(60, y - 10, 320, 20, fill=col, stroke="#999", rx=3)
                    g.text(70, y + 4, f"{p}", 10, bold=True)
                    g.text(95, y + 4, sig + star, 10, bold=(sig != "frei"))
                    g.text(200, y + 4, tgt, 9, fill="#333")
                    g.line([(380, y), (px - 5, y)], width=0.8, stroke="#777")
                else:
                    g.rect(560, y - 10, 350, 20, fill=col, stroke="#999", rx=3)
                    g.text(570, y + 4, f"{p}", 10, bold=True)
                    g.text(595, y + 4, sig + star, 10, bold=(sig != "frei"))
                    g.text(720, y + 4, tgt, 9, fill="#333")
                    g.line([(px + 5, y), (560, y)], width=0.8, stroke="#777")
            else:
                if side == "L":
                    g.text(bx - 8, y + 4, p, 9, anchor="end", fill="#555")
                else:
                    g.text(bx + bw + 8, y + 4, p, 9, fill="#555")
    g.text(60, by + bh + 14, "SPI1: MISO liegt auf Pin 39 (SPI1.setMISO(39)), weil Pin 1 das GPS braucht. Rückseite des Teensy: W25Q128 (SOIC-8) für LittleFS.", 9, fill="#444")
    g.save("teensy_pinmap.svg")


# ----------------------------------------------------------------------------------------------
def installation_side():
    g = SVG(940, 470)
    g.text(20, 26, "Einbau: Längsschnitt durch die Avionik-Sektion (Kuppler 150 mm, innen 70,2 mm)", 15, bold=True)
    g.text(20, 44, "Blick von der Seite, Platinenebene senkrecht zur Zeichenebene. Links TVC-Ende (v = 0), rechts Spitze. Maße in mm.", 10, fill="#555")
    s = 4.2                     # px per mm
    x0, yc = 130, 255           # v = 0 at x0, roll axis at yc
    def X(v): return x0 + v * s
    def Y(y): return yc - y * s
    Rin = 70.2 / 2
    # body tube (continues beyond the coupler) and coupler walls
    g.rect(X(-25), Y(36.3 + 1.2), 175 * s, 1.2 * s, fill="#e9e1d2", stroke="#bbb")
    g.rect(X(-25), Y(-36.3), 175 * s, 1.2 * s, fill="#e9e1d2", stroke="#bbb")
    g.text(X(125), Y(39.5), "Rohr 75 / 72,6", 9, fill="#999")
    g.rect(X(-15), Y(Rin + 1.1), 150 * s, 1.1 * s, fill="#c8b89a", stroke="#8a7a5a")
    g.rect(X(-15), Y(-Rin), 150 * s, 1.1 * s, fill="#c8b89a", stroke="#8a7a5a")
    g.text(X(5), Y(-Rin - 5), "Kuppler 72,4 / 70,2 × 150", 9, fill="#6a5a3a")
    # end rings and rods
    for v0 in (-15, 120):
        g.rect(X(v0), Y(34.5), 15 * s, 69 * s, fill="#d9d9d9", stroke="#777")
        g.text(X(v0 + 7.5), Y(-15), "Endring", 8, anchor="middle", rotate=-90, fill="#444")
    for yy in (29.5, 7, -7, -29.5):
        g.line([(X(-15), Y(yy)), (X(135), Y(yy))], stroke="#222", width=2)
    g.text(X(118), Y(31.5), "8× M2-Stange", 8, anchor="end", fill="#222")
    # board, carrier, batteries
    g.rect(X(0), Y(0.8), 120 * s, 1.6 * s, fill="#2f6b3a", stroke="#1d4a26")
    g.text(X(60), Y(-3.2), "Platine 54 × 120 × 1,6", 9, anchor="middle", fill="#1d4a26")
    g.rect(X(2), Y(-3.5), 116 * s, 10 * s, fill="#eee", stroke="#999", dash="3 2")
    g.text(X(60), Y(-16), "gedruckter Träger, zwei Fächer mit Klettband, 4× M3 zur Platine", 8, anchor="middle", fill="#777")
    g.rect(X(8), Y(-4.5), 56 * s, 8 * s, fill=C_PWR2, stroke="#a55")
    g.text(X(36), Y(-9), "2S LiPo 56 × 25,5 × 8", 8, anchor="middle")
    g.rect(X(68), Y(-4.5), 50 * s, 7 * s, fill=C_PWR1, stroke="#a85")
    g.text(X(93), Y(-8.5), "1S LiPo ca. 50 × 30 × 7", 8, anchor="middle")
    # Teensy, IMU
    g.rect(X(30), Y(13.5), 61 * s, 12.7 * s, fill=C_MCU, stroke="#1d3d63")
    g.text(X(44), Y(10), "Teensy 4.1", 9, anchor="middle", bold=True)
    g.text(X(44), Y(7.5), "auf Buchsenleisten", 8, anchor="middle")
    g.text(X(77), Y(10), "USB →", 8, anchor="middle"); g.text(X(34), Y(3), "SD", 8, anchor="middle")
    g.rect(X(60.5) - 6, Y(3.8), 12, 6, fill="#c0392b")
    g.text(X(60.5), Y(17), "IMU auf der Rollachse, v = 60,5", 8, anchor="middle", fill="#c0392b")
    g.line([(X(60.5), Y(15.5)), (X(60.5), Y(5))], stroke="#c0392b", width=0.8, dash="2 2")
    # LoRa, connectors
    g.rect(X(95), Y(4.5), 24 * s, 3.7 * s, fill=C_RF, stroke="#36c")
    g.text(X(107), Y(1.8), "LoRa E22", 8, anchor="middle")
    g.rect(X(1), Y(7), 20 * s, 6.2 * s, fill="#ddd", stroke="#777")
    g.text(X(11), Y(3.5), "XT30, Servos", 8, anchor="middle")
    g.text(X(11), Y(9.5), "Stecker axial", 8, anchor="middle", fill="#555")
    # antenna pigtail to the nose
    g.line([(X(119), Y(3.5)), (X(140), Y(3.5)), (X(165), Y(12))], stroke="#36c", width=1.6, arrow=True)
    g.text(X(121), Y(-6.5), "Pigtail 10 cm → λ/4-Antenne (17 cm) in der Spitze", 8, fill="#36c")
    # barometer (right strip, drawn in projection) with foam, holes
    g.rect(X(76), Y(4), 10 * s, 3 * s, fill="#fff2a8", stroke="#c9a800", dash="2 2")
    g.text(X(81), Y(21), "BMP390 (rechter Streifen) unter Schaum", 8, anchor="middle", fill="#8a7000")
    g.line([(X(81), Y(19.5)), (X(81), Y(4))], stroke="#c9a800", width=0.8, dash="2 2")
    g.circle(X(81), Y(Rin + 0.5), 3, fill="white", stroke="#c9a800", width=1.5)
    g.circle(X(81), Y(-Rin - 0.5), 3, fill="white", stroke="#c9a800", width=1.5)
    g.text(X(81), Y(-Rin - 7), "3–4 Druckausgleichsbohrungen Ø 2 mm auf dieser Höhe", 8, anchor="middle", fill="#8a7000")
    # hatch
    g.line([(X(25), Y(Rin + 3.5)), (X(100), Y(Rin + 3.5))], stroke="#c0392b", width=3)
    g.text(X(62), Y(Rin + 6.5), "Luke in Kuppler und Rohr (USB, SD, Reset), v ≈ 25 bis 100", 8, anchor="middle", fill="#c0392b")
    # direction labels
    g.text(X(-20), yc + 4, "TVC", 9, anchor="end", bold=True)
    g.text(X(139), yc + 4, "Spitze", 9, bold=True)
    g.text(20, 455, "Die Avionik-Sektion ist gegen den Fallschirmraum dicht (Ausstoßdruck). Alles sitzt steif: keine Gummipuffer, Vibration wird digital gefiltert.", 9, fill="#444")
    g.save("installation_side.svg")


# ----------------------------------------------------------------------------------------------
def order_flow():
    g = SVG(940, 330)
    g.text(20, 26, "Weg zur Platine: fünf Tore bis zur Inbetriebnahme", 15, bold=True)
    steps = [("0  Jetzt", ["Vorab bestellen:", "ICM-42688-Breakout,", "1S-Akku, LoRa DIP,", "Stecker, Pigtail"], "#eee"),
             ("1  Schaltplan", ["KiCad 9 installieren", "Schaltplan nach README", "ERC, Review (Kollege)"], C_SENS),
             ("2  Layout", ["Edge.Cuts aus DXF", "Zonen nach Plan", "DRC (JLC-Regeln), 3D", "1:1-Ausdruck im Kuppler"], C_SENS),
             ("3  Bestellung", ["Gerber, BOM, CPL", "JLCPCB 4 Lagen, ENIG", "5 Stück, 2 bestückt", "Teile-Check am Tag"], C_PWR1),
             ("4  Aufbau", ["THT selbst löten", "Sichtprüfung, Kurzschluss", "Firmware rev B flashen"], C_PWR1),
             ("5  Inbetrieb.", ["Testplan §9:", "Labornetzteil, I²C/SPI,", "Servos ohne Neustart,", "Pyro mit Lämpchen, LoRa"], C_PWR2)]
    x = 20
    w, gap = 140, 12
    for i, (t, ls, col) in enumerate(steps):
        g.box(x, 60, w, 110, t, ls, fill=col, title_size=12, size=9.5)
        if i < len(steps) - 1:
            g.line([(x + w, 115), (x + w + gap, 115)], arrow=True)
        x += w + gap
    g.text(20, 200, "Tore (nicht weiter ohne):", 10, bold=True)
    gates = ["1 → 2: Schaltplan ohne ERC-Fehler, jede Schiene mit Testpunkt und Sicherung, Review-Punkte des Kollegen eingearbeitet.",
             "2 → 3: DRC sauber, alle Hüllen in outline.py, Papierausdruck passt in den Kuppler, Teile-Verfügbarkeit bei JLC am Bestelltag geprüft.",
             "3 → 4: Lieferung geprüft (Lagen, Maße, Bohrungen, Bestückungsfotos), keine Brücken unter LGA-Gehäusen.",
             "4 → 5: Beide Versorgungen am Labornetzteil mit Strombegrenzung, erst dann Teensy stecken.",
             "Dauer: Schaltplan und Layout je nach Abenden 2 bis 4 Wochen, JLCPCB mit Bestückung und Versand 2 bis 3 Wochen."]
    for i, s in enumerate(gates):
        g.text(20, 220 + i * 18, s, 9.5, fill="#333")
    g.save("order_flow.svg")


if __name__ == "__main__":
    IMG.mkdir(exist_ok=True)
    for f in (system_blocks, power_tree, pyro_channel, teensy_pinmap, installation_side, order_flow):
        f()
        print("wrote", IMG / (f.__name__ + ".svg"))
