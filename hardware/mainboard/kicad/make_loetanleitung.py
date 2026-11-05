"""Löt- und Messanleitung für die Handlötteile als PDF: ../LOETANLEITUNG_revB1.pdf (system Python, Pillow, reportlab).

    "%LOCALAPPDATA%/Programs/KiCad/10.0/bin/python.exe" guide_dump.py     # board geometry -> out/guide/board.json
    python make_loetanleitung.py                                          # pictures and PDF

Lage, Drehung und Pad 1 jedes Teils kommen aus out/guide/board.json (also aus mainboard.kicad_pcb), Netze aus
circuit.py. Teilenummern wie im DigiKey-Auftrag 102484398 (Beschaffung_2026-10-26.md §6)."""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from PIL import Image as PILImage
from reportlab.platypus import CondPageBreak, Image as RLImage, PageBreak, SimpleDocTemplate, Spacer, Table, TableStyle

import circuit
import guide_figures as gf
from make_guide import P, ST, bullets, img, note, table

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "LOETANLEITUNG_revB1.pdf"
FIG = gf.OUT
FPS = {f["ref"]: f for f in gf.G["footprints"]}
NETS = {p.ref: p.pins for p in circuit.PARTS}

STAGE_COL = [(220, 70, 60), (235, 150, 40), (60, 150, 220), (40, 160, 90), (150, 90, 200), (120, 120, 130)]

# Stufen: (Titel, Farbe, [(Ref, Teil laut Auftrag, DigiKey-Nr., Gehäuse, Hinweis zur Ausrichtung)])
STAGES = [
    ("1S-Eingang und 5-V-Wandler", [
        ("F2", "Polyfuse 2 A/16 V", "F11449CT-ND", "1812", "ungepolt"),
        ("R17", "115 kΩ 1 % (Yageo RC0603FR-07115KL)", "311-115KHRCT-ND", "0603", "ungepolt; EN-Teiler von U2"),
        ("R14", "680 kΩ 1 % (Panasonic ERJ-3EKF6803V)", "P680KHCT-ND", "0603", "ungepolt; oberer FB-Widerstand"),
        ("R15", "130 kΩ 1 % (Yageo RC0603FR-07130KL)", "311-130KHRCT-ND", "0603",
         "ungepolt; unterer FB-Widerstand. <b>Pflicht vor dem ersten Einschalten</b>"),
        ("L2", "1,5 µH, Isat ≥ 4 A (Taiyo Yuden NRS5040T1R5NMGJ)", "587-NRS5040T1R5NMGJCT-ND", "5040", "ungepolt"),
        ("J2", "JST B2B-PH-K-S (J_BAT1, 1S-Akku)", "455-1704-ND", "THT 2 mm", "Rastnase wie im Bestückungsdruck"),
        ("J3", "JST B4B-PH-K-S (J_SW, Hauptschalter)", "455-1706-ND", "THT 2 mm", "Rastnase wie im Bestückungsdruck"),
    ]),
    ("3,3-V-Regler für Funk und Erweiterung", [
        ("U3", "AP2112K-3.3TRG1 (LDO 3V3_RF)", "AP2112K-3.3TRG1DICT-ND", "SOT-23-5", ""),
        ("U14", "AP2112K-3.3TRG1 (LDO 3V3_EXP)", "AP2112K-3.3TRG1DICT-ND", "SOT-23-5", ""),
        ("C20", "100 µF/6,3 V X7S (Murata GRM32EC70J107ME15L)", "490-10530-1-ND", "1210", "ungepolt (Keramik)"),
    ]),
    ("Logik, Sensorinsel und Teensy-Sockel", [
        ("FB1", "Ferrit 600 Ω bei 100 MHz (Murata BLM18KG601SN1D)", "490-5258-1-ND", "0603",
         "ungepolt; versorgt IMU und Barometer (3V3_SENS)"),
        ("U12", "74HC138PW (Nexperia), CS-Decoder", "1727-4065-1-ND", "TSSOP-16", ""),
        ("U13", "CD74HC4051PWR (TI), Analogmux", "296-13031-1-ND", "TSSOP-16", "TI statt Nexperia, pinkompatibel"),
        ("A1", "2 × Buchsenleiste 1×24, 8,5 mm (Sullins)", "S7022-ND", "THT 2,54 mm",
         "mit gestecktem Teensy als Lehre löten"),
        ("J15", "Stiftleiste 2×10 (J_STACK), optional", "35-PRPC010DAAN-RC-ND", "THT 2,54 mm", "erst wenn gebraucht"),
    ]),
    ("2S-Pfad: Sicherung, Schutzdioden, Puffer, Stecker", [
        ("F1", "Polyfuse 3 A/24 V (Littelfuse 1812L300/24SLER)", "18-1812L300/24SLERCT-ND", "1812", "ungepolt"),
        ("D2", "TVS SMAJ12CA (bidirektional)", "SMAJ12CALFCT-ND", "SMA", "bidirektional: Richtung egal"),
        ("D3", "TVS SMAJ12CA (bidirektional)", "SMAJ12CALFCT-ND", "SMA", "bidirektional: Richtung egal"),
        ("C4", "330 µF/16 V Polymer-Tantal (Kyocera AVX TCJE337M016R0050E)", "478-13307-1-ND", "7343",
         "<b>gepolt</b>: Balken am Gehäuse = Plus = Pad 1"),
        ("C5", "330 µF/16 V Polymer-Tantal (Kyocera AVX TCJE337M016R0050E)", "478-13307-1-ND", "7343",
         "<b>gepolt</b>: Balken am Gehäuse = Plus = Pad 1"),
        ("J1", "AMASS XT30PW-M (2S-Akku), falls vorhanden", "nicht bei DigiKey", "THT", "Pin 1 = Plus"),
        ("J4", "JST B2B-XH-A (J_ARM, Schlüsselschalter)", "455-B2B-XH-A-ND", "THT 2,5 mm", ""),
        ("J18", "JST B2B-PH-K-S (2S-Ladeanschluss)", "455-1704-ND", "THT 2 mm", ""),
    ]),
    ("Stecker, LEDs, Summer, Lader", [
        ("J5", "JST B3B-XH-A stehend (Servo Yaw)", "455-2248-ND", "THT 2,5 mm",
         "stehend statt liegend S3B: Löcher passen, Kabel geht nach oben"),
        ("J6", "JST B3B-XH-A stehend (Servo Pitch)", "455-2248-ND", "THT 2,5 mm", "wie J5"),
        ("J7", "JST B3B-XH-A (Servo Fallschirm)", "455-2248-ND", "THT 2,5 mm", ""),
        ("J16", "JST B3B-XH-A (Servo Beine)", "455-2248-ND", "THT 2,5 mm", ""),
        ("J8", "JST B2B-XH-A (Rollmotor)", "455-B2B-XH-A-ND", "THT 2,5 mm", ""),
        ("J9", "JST S2B-XH-A liegend (Pyro 1)", "455-S2B-XH-A-ND", "THT 2,5 mm", "Öffnung zur Platinenkante"),
        ("J10", "JST S2B-XH-A liegend (Pyro 2)", "455-S2B-XH-A-ND", "THT 2,5 mm", "Öffnung zur Platinenkante"),
        ("J17", "JST B3B-PH-K-S (Kabel zum Schalterbrett)", "455-1705-ND", "THT 2 mm", ""),
        ("J12", "JST BM04B-SRSS-TB (Qwiic)", "455-BM04B-SRSS-TBCT-ND", "SMD 1,0 mm", "Haltelaschen zuerst"),
        ("J13", "JST BM03B-GHS-TBT (Kamera)", "455-BM03B-GHS-TBTCT-ND", "SMD 1,25 mm", "Haltelaschen zuerst"),
        ("J14", "JST BM03B-GHS-TBT (externe LEDs)", "455-BM03B-GHS-TBTCT-ND", "SMD 1,25 mm", "Haltelaschen zuerst"),
        ("U8", "SN74LV1T34DBVR (Pegel 3,3 → 5 V für die LEDs)", "296-37176-1-ND", "SOT-23-5", ""),
        ("LED1", "WS2812B-2020 (Adafruit 4684)", "1528-4684-ND", "2,0 × 2,0 mm", "Pin-1-Ecke am Gehäuse markiert"),
        ("LED2", "WS2812B-2020 (Adafruit 4684)", "1528-4684-ND", "2,0 × 2,0 mm", "Pin-1-Ecke am Gehäuse markiert"),
        ("BZ1", "aktiver Summer 5 V, 12 mm (AI-1223-TWT-5V-R)", "668-1019-ND", "THT RM 7,6",
         "<b>gepolt</b>: „+“ am Summer = Pad 1"),
        ("U11", "MCP73831T-2ACI/OT (1S-Lader)", "MCP73831T-2ACI/OTCT-ND", "SOT-23-5", ""),
    ]),
    ("Nachzügler (Teile noch unterwegs)", [
        ("U6", "INA239AIDGSR (Strom/Spannung 2S)", "296-INA239AIDGSRCT-ND", "VSSOP-10",
         "kommt mit der 2. DigiKey-Sendung (ab 9.11.)"),
        ("J11", "JST BM04B-GHS-TBT (GPS)", "455-BM04B-GHS-TBTCT-ND", "SMD 1,25 mm", "kommt mit der 2. DigiKey-Sendung"),
        ("U10", "Ebyte E22-400T22S (LoRa)", "AliExpress", "SMD-Modul, 26 Randpads", "Antenne an die IPEX-Buchse"),
    ]),
]
STAGE_OF = {ref: i for i, (_, parts) in enumerate(STAGES) for ref, *_ in parts}


def where(dx, dy, tol=0.25):
    v = "oben" if dy < -tol else "unten" if dy > tol else ""
    h = "links" if dx < -tol else "rechts" if dx > tol else ""
    return (v + " " + h).strip() or "Mitte"


def pad1_text(ref):
    """Wo Pad 1 liegt, in der Draufsicht (oben = Spitze, Pyro-Stecker)."""
    f = FPS[ref]
    pads = f["pads"]
    p1 = [p for p in pads if p["num"] == "1"]
    if not p1:
        return "–"
    p1 = p1[0]
    cx = sum(p["x"] for p in pads) / len(pads)  # Mitte der Pads; bei THT liegt der Ursprung auf Pad 1
    cy = sum(p["y"] for p in pads) / len(pads)
    dx, dy = p1["x"] - cx, p1["y"] - cy
    num = [p for p in pads if p["num"].isdigit()]
    net = p1["net"] if not p1["net"].startswith("unconnected") else "frei"
    if len(num) == 2:
        return f"Pad 1 {where(dx, dy)} ({net})"
    if len(num) == 5:  # SOT-23-5: Pins 1-3 auf einer Seite, 1,14 mm neben der Mitte
        three = where(dx, 0) if abs(abs(dx) - 1.14) < 0.1 else where(0, dy)
        return f"Seite mit drei Beinen {three}, Pin 1 {where(dx, dy)} ({net})"
    return f"Pin 1 {where(dx, dy)} ({net})"


# ------------------------------------------------------------------ pictures
def draw_parts(c, refs, col, label=True, label_size=10):
    for ref in refs:
        f = FPS[ref]
        x0, y0, x1, y1 = f["box"]
        c.rect(x0, y0, x1, y1, fill=col + (60,), outline=col + (255,), width=3)
        for p in f["pads"]:
            c.pad(p, (205, 160, 60, 255))
        p1 = [p for p in f["pads"] if p["num"] == "1"]
        if p1 and len(f["pads"]) > 1:
            c.circle(p1[0]["x"], p1[0]["y"], max(0.45, min(p1[0]["sx"], p1[0]["sy"]) * 0.75), outline=(220, 0, 0, 255),
                     width=5)
        if label:
            c.text((x0 + x1) / 2, y0 - 0.3 - label_size * 0.6 / (c.s / 2), ref, label_size, col, True)


def faint_pads(c):
    for f in gf.G["footprints"]:
        for p in f["pads"]:
            if "F.Cu" in p["layers"]:
                c.pad(p, (210, 205, 195, 255))


def fig_overview():
    c = gf.Canvas(gf.X0, gf.Y0, gf.X1, gf.Y1, 11)
    c.board()
    faint_pads(c)
    for i, (_, parts) in enumerate(STAGES):
        draw_parts(c, [r for r, *_ in parts], STAGE_COL[i], label=True, label_size=15)
    return c.save("loet_overview.png")


def fig_stage_board(i):
    c = gf.Canvas(gf.X0, gf.Y0, gf.X1, gf.Y1, 6)
    c.board()
    faint_pads(c)
    draw_parts(c, [r for r, *_ in STAGES[i][1]], STAGE_COL[i], label=True, label_size=13)
    return c.save(f"loet_stage{i + 1}_board.png")


def fig_zoom(name, refs, col, margin=3.0, s=26, extra=()):
    boxes = [FPS[r]["box"] for r in refs] + [FPS[r]["box"] for r in extra]
    x0 = min(b[0] for b in boxes) - margin
    y0 = min(b[1] for b in boxes) - margin - 1.5
    x1 = max(b[2] for b in boxes) + margin
    y1 = max(b[3] for b in boxes) + margin
    c = gf.Canvas(x0, y0, x1, y1, s, margin=4)
    c.d.rectangle([0, 0, c.w, c.h], fill=gf.BOARD)
    faint_pads(c)
    for r in extra:  # Nachbarn zur Orientierung, grau beschriftet
        f = FPS[r]
        c.text((f["box"][0] + f["box"][2]) / 2, (f["box"][1] + f["box"][3]) / 2, r, 22, (110, 110, 120), True)
    draw_parts(c, refs, col, label=True, label_size=28)
    return c.save(name)


def fig_testpoints():
    c = gf.Canvas(gf.X0, gf.Y0, gf.X1, gf.Y1, 7)
    c.board()
    faint_pads(c)
    for f in gf.G["footprints"]:
        if f["ref"].startswith("TP"):
            c.circle(f["x"], f["y"], 1.4, fill=(220, 0, 0, 255), outline=(255, 255, 255, 255), width=3)
            c.text(f["x"], f["y"] - 2.8, f["value"], 15, (150, 0, 0), True)
    for ref, lab in (("C16", "TEENSY_VIN (+ von C16)"), ("J2", "J_BAT1"), ("J1", "J_BAT2 (XT30)"), ("JP1", "JP1"),
                     ("JP2", "JP2"), ("J3", "J_SW")):
        f = FPS[ref]
        c.rect(*f["box"], outline=(40, 80, 170, 255), width=3)
        c.text((f["box"][0] + f["box"][2]) / 2, f["box"][3] + 1.8, lab, 13, (40, 80, 170), True)
    return c.save("loet_testpoints.png")


ZOOMS = {  # Stufe -> [(Datei, Teile, Nachbarn)]
    0: [("loet_z1.png", ["F2", "R17", "R15", "R14", "L2", "J2", "J3"], ["U2", "JP1", "TP2", "TP7"])],
    1: [("loet_z2a.png", ["U3", "C20"], ["TP5", "TP3"]), ("loet_z2b.png", ["U14"], ["TP6"])],
    2: [("loet_z3.png", ["FB1", "U12", "U13"], ["U4", "U5"])],
    3: [("loet_z4a.png", ["F1", "C4", "C5", "J1", "J18"], ["R_SH1", "Q1", "Q6"]), ("loet_z4b.png", ["D2", "D3"], ["J9", "J10"])],
    4: [("loet_z5a.png", ["U8", "LED1", "LED2", "J13", "J14"], []), ("loet_z5b.png", ["U11", "J17"], [])],
    5: [("loet_z6a.png", ["U6"], ["R_SH1"]), ("loet_z6b.png", ["U10", "J11"], [])],
}


# ------------------------------------------------------------------ text
def parts_table(i):
    rows = [["Ref", "Teil (wie bestellt)", "DigiKey-Nr.", "Gehäuse", "Ausrichtung (Draufsicht)"]]
    for ref, part, dk, pkg, hint in STAGES[i][1]:
        o = pad1_text(ref)
        if hint:
            o += "; " + hint
        rows.append([f"<b>{ref}</b>", part, dk, pkg, o])
    return table(rows, [1.2, 5.0, 3.4, 1.9, 5.5])


def pic(path, w_cm, max_h_cm):
    w, h = PILImage.open(path).size
    w_cm = min(w_cm, max_h_cm * w / h)
    return RLImage(str(path), width=w_cm * cm, height=w_cm * cm * h / w)


def stage_figs(i):
    zs = [fig_zoom(name, refs, STAGE_COL[i], extra=extra) for name, refs, extra in ZOOMS[i]]
    max_h = 9.0 / len(zs)
    right = Table([[pic(p, 11.5, max_h)] for p in zs], colWidths=[11.8 * cm])
    right.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    t = Table([[pic(fig_stage_board(i), 4.2, 9.5), right]], colWidths=[5.2 * cm, 11.8 * cm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    return [t, P("Links die ganze Platine (oben = Spitze mit den Pyro-Steckern), rechts vergrößert. "
                 "Roter Ring = Pad 1, graue Namen = schon bestückte Nachbarn zur Orientierung.", "cap")]


def meas(rows):
    return table([["Messung", "Wo", "Soll", "Wenn nicht"]] + rows, [3.6, 4.4, 3.4, 5.6])


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Arial", 8)
    canvas.setFillColor(colors.HexColor("#777777"))
    canvas.drawString(2 * cm, 1.2 * cm, "Kartonaut Mainboard rev B1 · Löt- und Messanleitung")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Seite {doc.page}")
    canvas.restoreState()


def build():
    s = []
    s += [P("Löt- und Messanleitung", "title"),
          P("Kartonaut Mainboard rev B1 · Handlötteile nach der JLCPCB-Bestückung · Stand 05.11.2026", "sub"),
          Spacer(1, 8),
          P("JLCPCB liefert die Platine mit 106 bestückten SMD-Teilen (Wandler U2, IMU U4, Barometer U5, Motortreiber U7, "
            "Magnetometer U16, SHT40 U18, alle FETs, D1, D4, C16, C17 und die meisten Passiven). Die übrigen Teile "
            "lötest du selbst, in <b>sechs Stufen</b>. Nach jeder Stufe wird gemessen, bevor die nächste beginnt: So "
            "bleibt ein Fehler auf wenige Teile eingegrenzt, und kein Teil bekommt Spannung, bevor seine Versorgung "
            "stimmt."),
          note("<b>Vor dem ersten Einschalten müssen R14 (680 k) und R15 (130 k) beide eingelötet sein.</b> Sie stellen "
               "die 5-V-Schiene ein. Ohne R15 regelt U2 auf etwa 0,8 V (die Platine bleibt tot). Ohne R14 ist der "
               "Regler ohne Rückführung und die Ausgangsspannung unbestimmt. Der 130 k von DigiKey kommt erst mit der "
               "zweiten Sendung (Versand ab 9.11.). Bis dahin geht jeder 130-kΩ-Widerstand mit 1 % (Werkstatt, Sortiment, "
               "auch bedrahtet mit kurz gebogenen Beinen auf den 0603-Pads) oder 120 k + 10 k in Reihe."),
          Spacer(1, 6),
          img(fig_overview(), 7.0, "Alle Handlötteile, eingefärbt nach Stufe (Farben wie in den Kapiteln). "
                                   "Oben die Spitze mit den Pyro-Steckern, unten das Heck mit XT30 und Servos."),
          PageBreak()]

    s += [P("0  Vorbereitung", "h1"),
          P("Werkzeug", "h2"),
          *bullets(["Lötkolben mit feiner Meißelspitze (1–2 mm), 330–350 °C; bleihaltiges Lot 0,5 mm oder bleifrei 0,5 mm "
                    "bei 360 °C", "Flussmittel (No-Clean-Gel), Entlötlitze, Isopropanol und Pinsel",
                    "Pinzette, Lupe oder Mikroskop (für TSSOP, 0603, WS2812B-2020)",
                    "Multimeter mit Durchgangspiepser; Labornetzteil mit Strombegrenzung (sonst: 1S-Akku über eine "
                    "1-A-Sicherung, dann aber besonders vorsichtig)",
                    "für Stufe 6: Heißluft hilft beim E22-Modul, geht aber auch mit dem Kolben (Randpads)"]),
          P("Löttechnik in Kürze", "h2"),
          *bullets(["<b>0603 und 1812:</b> ein Pad vorverzinnen, Teil mit der Pinzette anlegen, Pad nachschmelzen, dann "
                    "das zweite Pad löten.",
                    "<b>SOT-23-5:</b> ein Eckbein heften, Lage prüfen, dann die übrigen Beine.",
                    "<b>TSSOP-16 und VSSOP-10:</b> Pads dünn mit Flussmittel bestreichen, zwei diagonale Ecken heften, "
                    "Lage unter der Lupe prüfen, dann mit etwas Lot an der Spitze über die Beine ziehen (Schlepplöten). "
                    "Brücken mit Flussmittel und sauberer Spitze oder Entlötlitze abziehen.",
                    "<b>SMD-Stecker JST GH/SH:</b> zuerst die beiden Haltelaschen, dann die Signalpins.",
                    "<b>Widerstände ohne Aufdruck:</b> 0603 mit 1 % sind meist unbeschriftet. Erst messen, dann aus "
                    "dem Gurt nehmen, jeden Wert getrennt ablegen.",
                    "<b>Nach jeder Stufe:</b> Flussmittel mit Isopropanol abwaschen, unter der Lupe auf Brücken und "
                    "kalte Stellen sehen."]),
          P("Orientierung in den Bildern", "h2"),
          P("Alle Bilder sind Draufsichten auf die Bestückungsseite, gezeichnet aus <i>mainboard.kicad_pcb</i>. "
            "<b>Oben</b> ist die Spitze der Rakete (Pyro-Stecker J9/J10), <b>unten</b> das Heck (XT30, Servostecker "
            "J5/J6). Der <b>rote Ring</b> markiert Pad 1. Bei Dioden ist Pad 1 die Kathode, bei gepolten Kondensatoren "
            "der Pluspol. Bei ICs findest du Pin 1 am Punkt oder an der abgeschrägten Kante des Gehäuses; zusätzlich "
            "zeigt der Bestückungsdruck auf der Platine eine Pin-1-Marke."),
          P("Messpunkte", "h2"),
          img(fig_testpoints(), 7.5, "Testpunkte (rot) und Einspeisestellen (blau). Minus des Multimeters immer an TP GND."),
          P("Eingangsprüfung, bevor du lötest (ohne Spannung)", "h2"),
          *bullets(["Platine unter der Lupe ansehen: Brücken an U2 (QFN), U4/U5/U16 (LGA), U7; Polung von D1 und D4 "
                    "(Kathodenring wie im Bestückungsdruck), C16/C17 (Balken links).",
                    "Mit dem Ohmmeter von TP GND gegen <b>VSYS_IN, 5V_SYS, 3V3_RF, 3V3_EXP, VBAT_PROT, VSERVO</b> und "
                    "das Plus von C16 (TEENSY_VIN) messen. Kein Wert darf piepen. Bei Kondensatoren steigt die Anzeige "
                    "langsam an, das ist normal. Werte notieren: Sie sind der Vergleich für die späteren Stufen."]),
          PageBreak()]

    texts = {
        0: [P("Diese Teile bringen die 1S-Spannung auf die Platine und stellen den Buck-Boost-Wandler U2 (TPS63070, "
              "von JLCPCB bestückt) auf 5 V ein: 5V_SYS = 0,8 V × (1 + 680 k / 130 k) = 4,98 V. R17 bildet mit R16 "
              "(330 k, bestückt) die Einschaltschwelle: ein ab 3,1 V, aus unter 2,7 V."),
            P("Vor dem Einschalten (Ohmmeter, ohne Spannung)", "h2"),
            meas([["R15 im Schaltkreis", "Pads von R15", "etwa 110–130 kΩ", "unter 50 kΩ: Brücke an U2-FB; offen: Lötstelle"],
                  ["R14 im Schaltkreis", "Pads von R14", "etwa 400–680 kΩ (parallel liegt R15 + Last)", "Lötstelle prüfen"],
                  ["Kurzschluss", "TP GND gegen VSYS_IN, 5V_SYS", "kein Piepen", "nicht einschalten, Brücke suchen"]]),
            P("Erstes Einschalten (Netzteil 4,0 V, Strombegrenzung 100 mA)", "h2"),
            P("Plus an J_BAT1 Pin 1, Minus an Pin 2. Den 1S-Lastschalter schließen: Lötbrücke <b>JP1</b> („SJ 1S“) "
              "zulöten oder an J_SW Pin 1 und 2 verbinden. Teensy noch nicht stecken."),
            meas([["Strom", "Netzteilanzeige", "unter 20 mA (meist wenige mA)", "über 60 mA sofort aus: Kurzschluss, verdrehtes Teil"],
                  ["VSYS_IN", "TP VSYS_IN", "Netzteil minus < 0,1 V", "0 V: F2, Q2, Q7, JP1 prüfen"],
                  ["5V_SYS", "TP 5V_SYS", "4,85–5,15 V", "≈ 0,8 V: R15 fehlt/offen; > 5,2 V: R14/R15 vertauscht oder falscher Wert"],
                  ["TEENSY_VIN", "Plus von C16", "4,5–4,9 V (5V_SYS minus Diode D1)", "0 V: D1 verpolt oder offen"],
                  ["Spannungsfenster", "Netzteil auf 3,0 V und 4,2 V stellen", "5V_SYS bleibt 4,85–5,15 V", "U2 / L2 prüfen"],
                  ["Abschaltschwelle", "Netzteil langsam auf 2,6 V senken, dann auf 3,3 V heben", "aus unter 2,7 V, wieder an ab 3,1 V", "R17 / R16 prüfen"]])],
        1: [P("Zwei LDOs machen aus 5V_SYS je 3,3 V: <b>3V3_RF</b> für LoRa und GPS, <b>3V3_EXP</b> für Zusatzplatinen "
              "an J_STACK. C20 puffert den Sendepuls des Funkmoduls. Der Teensy hat einen eigenen 3,3-V-Regler (Netz "
              "<i>3V3</i>); diese beiden LDOs entlasten ihn."),
            P("Messen (4,0 V, 100 mA, Teensy noch nicht gesteckt)", "h2"),
            meas([["Kurzschluss vorher", "TP GND gegen TP 3V3_RF, TP 3V3_EXP", "kein Piepen", "Brücke an U3/U14 suchen"],
                  ["Strom", "Netzteil", "unter 20 mA", "über 60 mA: LDO verdreht"],
                  ["3V3_RF", "TP 3V3_RF", "3,20–3,40 V", "0 V: U3 verdreht (Pin 1 = Eingang 5V_SYS) oder EN-Pin 3 offen"],
                  ["3V3_EXP", "TP 3V3_EXP", "3,20–3,40 V", "wie oben für U14"]])],
        2: [P("<b>FB1</b> trennt die Sensorversorgung 3V3_SENS (IMU U4, Barometer U5) vom Teensy-3,3-V-Netz; ohne FB1 "
              "sind IMU und Barometer stromlos. <b>U12</b> (74HC138) erzeugt aus drei Adressleitungen die Chip-Selects "
              "für IMU, Barometer, INA239 und J_STACK; ohne U12 antwortet keiner der SPI-Sensoren. <b>U13</b> schaltet "
              "die acht Messspannungen (Akkus, Pyro-Durchgang, ARM) auf einen ADC-Pin. Dann die Teensy-Sockel."),
            P("Prüfen nach dem Löten (ohne Spannung)", "h2"),
            meas([["Nachbarpins", "jedes benachbarte Beinpaar von U12 und U13 mit dem Piepser", "kein Piepen, <b>außer U13 Pin 6–7–8</b> (alle GND, gewollt)",
                   "Brücke mit Flussmittel und Litze entfernen"],
                  ["3V3 gegen GND", "U12 Pin 16 gegen TP GND", "kein Piepen", "Brücke an U12/U13 (Pin 16 = 3V3, Pin 8 = GND)"],
                  ["FB1", "beide Pads von FB1", "Durchgang (< 1 Ω)", "Lötstelle"]]),
            P("Teensy-Sockel A1", "h2"),
            P("Beide Buchsenleisten 1×24 auf die Stifte des Teensy stecken, den Teensy samt Leisten einsetzen und die Leisten "
              "von unten verlöten, dabei den Teensy <b>nicht</b> mitlöten. Lage: <b>USB-Buchse zeigt nach oben</b> (zur "
              "Spitze, zu J9/J10); das quadratische Pad 1 oben links ist GND, so wie der GND-Pin neben Pin 0 am USB-Ende "
              "des Teensy. VIN-VUSB-Brücke auf dem Teensy <b>nicht</b> trennen (D1 verhindert Rückspeisung). "
              "Danach den ersten Test mit Teensy machen: Kapitel 7, Schritt A (Sensorerkennung)."),
            ],
        3: [P("Der 2S-Zweig versorgt Servos, Rollmotor und Pyro. F1 sitzt direkt hinter dem Verpolschutz Q1, C4/C5 puffern "
              "die Servoschiene VSERVO, D2/D3 begrenzen Spitzen am Pyro-Ausgang VBAT_ARMED. <b>C4/C5 sind gepolt:</b> "
              "beim Polymer-Tantal markiert der Balken den <b>Pluspol</b> (umgekehrt wie beim Alu-Elko)."),
            P("Messen (Netzteil Kanal 2: 7,4 V, 100 mA; 1S bleibt an)", "h2"),
            P("Plus an J_BAT2 (XT30) Pin 1. 2S-Lastschalter schließen: <b>JP2</b> („SJ 2S“) zulöten oder J_SW Pin 3–4 "
              "verbinden. ARM (J4) noch offen lassen."),
            meas([["Kurzschluss vorher", "TP GND gegen TP VBAT_PROT, TP VSERVO", "kein Piepen (Anzeige steigt langsam, C4/C5)", "C4/C5 verpolt? Brücke an F1"],
                  ["Strom 2S", "Netzteil Kanal 2", "unter 10 mA", "über 30 mA aus: C4/C5 verpolt, D2/D3 falsches Teil"],
                  ["VBAT_PROT", "TP VBAT_PROT", "Netzteil minus < 0,1 V", "0 V: F1, Q1, Q6, JP2"],
                  ["VSERVO", "TP VSERVO", "VBAT_PROT minus < 0,05 V", "Shunt R_SH1 Lötstelle"],
                  ["ARM aus", "Pad von D2 (VBAT_ARMED) gegen GND", "≈ 0 V", "ARM-Pfad prüfen"],
                  ["ARM ein", "J4 Pin 1–2 brücken, wieder D2", "≈ VBAT_PROT", "J4 Lötstellen; danach Brücke wieder ab"]])],
        4: [P("Jetzt die übrigen Stecker, die Status-LEDs mit ihrem Pegelwandler U8, der Summer und der 1S-Lader. "
              "Reihenfolge: zuerst die flachen SMD-Teile (U8, U11, LED1/LED2, J12–J14), dann die THT-Stecker, zuletzt "
              "der hohe Summer."),
            *bullets(["<b>LED1/LED2 (WS2812B-2020):</b> 2 × 2 mm, Pads unter dem Gehäuse. Pads dünn verzinnen, LED mit "
                      "Flussmittel aufsetzen, von der Seite kurz erhitzen. Nicht länger als 3 s, die LED ist hitzeempfindlich. "
                      "Pin 1 ist DOUT, Pin 3 DIN, Pin 2 GND, Pin 4 5 V.",
                      "<b>J5/J6:</b> Bestellt sind stehende B3B-XH-A statt der liegenden S3B. Das Lochbild passt; "
                      "die Rastnase so drehen, wie der Bestückungsdruck die Steckrichtung zeigt.",
                      "<b>J9/J10:</b> liegende S2B-XH-A, Steckseite zur Platinenkante.",
                      "<b>BZ1:</b> Das längere Bein bzw. „+“ auf dem Gehäuse kommt an Pad 1 (5V_SYS)."]),
            P("Messen", "h2"),
            meas([["Kurzschluss", "TP GND gegen TP 5V_SYS", "kein Piepen", "LED oder U8 verdreht"],
                  ["Strom 1S", "Netzteil, 4,0 V", "unter 30 mA ohne Teensy (LEDs aus ≈ 1 mA je LED)", "LED verdreht: Pin 4 an 5 V prüfen"],
                  ["Summer, LEDs", "über die Testfirmware (Kapitel 7, Schritt C)", "Ton; rot/grün/blau/weiß", "BZ1 verpolt; LED-Kette: U8, LED1 DIN"],
                  ["Lader", "5 V an J17 Pin 1 (VBUS), Pin 2 GND, Akku an J_BAT1", "Ladestrom ≤ 500 mA, endet bei 4,2 V", "U11 verdreht"]])],
        5: [P("Diese Teile sind noch unterwegs. Die Platine läuft ohne sie: Ohne <b>U6</b> fehlt nur die Strommessung "
              "VSERVO, ohne <b>J11</b> der GPS-Stecker (Litzen gingen auch direkt), ohne <b>U10</b> der Funk. Die "
              "Testfirmware meldet sie als nicht bestückt, bis du sie in der Bestückungsliste einschaltest (Kapitel 7)."),
            *bullets(["<b>U6 INA239</b> (VSSOP-10, 0,5 mm Raster): wie TSSOP schlepplöten. Pin 1 (Punkt) oben links. "
                      "Danach Nachbarpins mit dem Piepser prüfen; Pin 6 (3V3) darf nicht an Pin 7 (GND) hängen.",
                      "<b>J11</b>: Haltelaschen zuerst. Pin 1 = 3V3_RF, 2 = GND, 3 = TX vom GPS, 4 = RX zum GPS.",
                      "<b>U10 E22-400T22S</b>: Modul so auflegen, dass die Randpads genau über den Pads liegen; die "
                      "Pin-1-Marke auf dem Modul liegt am roten Ring. Zwei gegenüberliegende Ecken heften, dann Pad für "
                      "Pad mit viel Flussmittel. Antenne vor dem ersten Senden an die IPEX-Buchse; ohne Antenne nicht "
                      "senden."]),
            meas([["U6 eingelötet", "Strom 2S", "unter 10 mA", "Brücke an U6"],
                  ["U10 eingelötet", "3V3_RF mit Modul", "3,20–3,40 V, Strom 1S + ≈ 10 mA", "Modul verdreht: sofort aus"]])],
    }

    for i, (title, _) in enumerate(STAGES):
        s += [P(f"{i + 1}  Stufe {i + 1}: {title}", "h1")]
        s += texts[i][:1]
        s += [parts_table(i), Spacer(1, 6)]
        s += stage_figs(i)
        s += texts[i][1:]
        s += [PageBreak()]

    s += [P("7  Funktionstest mit der Testfirmware", "h1"),
          P("Die Testkonsole <i>firmware/examples/revb_test</i> prüft jeden Baustein und meldet je Zeile "
            "OK, FEHL, SKIP oder NICHT_BESTÜCKT. Ausführlich: <i>firmware/Tischtest_revB1.md</i> und "
            "<i>firmware/Versuche_revB1.md</i>."),
          *FIRMWARE,
          ]

    s += [CondPageBreak(6 * cm), P("8  Kurzfassung zum Abhaken", "h1"),
          table([["", "Schritt", "Erledigt"],
                 ["0", "Sichtprüfung, Widerstand der Schienen gegen GND notiert", "☐"],
                 ["1", "F2, R17, R14, R15, L2, J2, J3 / JP1 → 5V_SYS 4,85–5,15 V, Strom < 20 mA", "☐"],
                 ["2", "U3, U14, C20 → 3V3_RF und 3V3_EXP 3,20–3,40 V", "☐"],
                 ["3", "FB1, U12, U13, Buchsenleisten → Teensy stecken, Sensorerkennung", "☐"],
                 ["4", "F1, D2, D3, C4, C5, J1, J4, J18 / JP2 → VBAT_PROT, VSERVO, Strom 2S < 10 mA", "☐"],
                 ["5", "Stecker, U8, LED1/2, BZ1, U11 → LEDs, Summer, Servos, Motor, Pyro-Lämpchen", "☐"],
                 ["6", "U6, J11, U10 nach Lieferung → in der Bestückungsliste einschalten, Test wiederholen", "☐"]],
                [0.8, 14.0, 2.2])]

    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm,
                            bottomMargin=1.8 * cm, title="Löt- und Messanleitung Mainboard rev B1", author="Kartonaut")
    doc.build(s, onFirstPage=footer, onLaterPages=footer)
    print(OUT)


FIRMWARE = [  # Stand der Testfirmware 05.11.2026: LSM6DSV16X-Treiber, Bestückungsliste FitRevB.h
    P("Was bestückt ist, steht in einer <b>Bestückungsliste</b> (<i>lib/mainboard_revb/FitRevB.h</i>). Ab Werk: "
      "IMU (LSM6DSV16X), Barometer (BMP388), Magnetometer und SHT40 <b>ein</b>; INA239, LoRa, GPS, zweites Barometer und "
      "ADXL375 <b>aus</b>. Ein Teil auf „aus“ meldet <b>NICHT_ERKANNT</b> und zählt nicht als Fehler. Ein Teil auf "
      "„ein“, das nicht antwortet, meldet <b>FEHL</b>. Kein Teil bricht den Lauf ab. Die IMU wählt die Firmware selbst "
      "nach WHO_AM_I (0x70 = LSM6DSV16X)."),
    table([["Befehl (Konsole revb_test)", "Wirkung"],
           ["fit", "Bestückungsliste anzeigen"],
           ["fit ina on  ·  fit lora on  ·  fit gps on", "Teil einschalten, sobald es eingelötet ist"],
           ["fit baro off", "Barometer aus dem Test nehmen (falls es nicht antwortet und du erst weiterlöten willst)"],
           ["fit all on|off  ·  fit default", "alles ein/aus, zurück zur Werksliste"],
           ["python tools/bench_test.py --skip-rails --fit \"ina=on,lora=on\"", "dasselbe vom PC aus"]],
          [8.0, 9.0]),
    P("Die Liste gilt bis zum nächsten Neustart. Für <i>revb_bringup</i> (ohne Konsole) setzt man sie beim Bauen, "
      "z. B. <i>-DREVB_FIT_INA239=1</i>, <i>REVB_FIT_LORA</i>, <i>REVB_FIT_GPS</i>.", "p"),
    P("Schritt A: nach Stufe 3 (Teensy steckt, nur 1S)", "h2"),
    *bullets(["Netzteil 1S: 4,0 V, Strombegrenzung jetzt <b>300 mA</b> (der Teensy braucht etwa 100 mA). USB anstecken.",
              "Im Ordner <i>firmware</i>: <i>python tools/check_board_pins.py</i> (Pins gegen die Platine), dann "
              "<i>pio run -e revb_test -t upload</i>, dann <i>pio device monitor</i>. Es erscheint ein Banner und "
              "<i>READY</i>.",
              "<i>all</i> eingeben oder <i>python tools/bench_test.py --skip-rails</i> ausführen."]),
    P("Erwartete Ausgabe (gekürzt, INA239, LoRa und GPS noch nicht bestückt):", "p"),
    table([["Zeile", "Bedeutung"],
           ["TEST imu_whoami OK 0x70 soll 0x70 (LSM6DSV16X)", "IMU antwortet, FB1 und U12 sind in Ordnung"],
           ["TEST imu_rate OK 960 Hz", "Datenrate stimmt"],
           ["TEST imu_selftest_gyro OK … Grenzen 150..700", "Gyro-Selbsttest"],
           ["TEST imu_selftest_acc OK … Grenzen 0.050..1.700", "Beschleunigungs-Selbsttest"],
           ["TEST baro1 OK Chip-ID 0x50 (BMP388), … Pa", "Barometer; Druck um 100 000 Pa"],
           ["TEST mag … OK · TEST sht … OK", "I²C-Sensoren"],
           ["TEST baro2 / adxl_present / ina_id NICHT_ERKANNT", "nicht bestückt, kein Fehler"],
           ["END all SKIP", "SKIP kommt von den 2S-Kanälen des Mux, solange 2S fehlt"]], [8.6, 8.4]),
    note("<b>IMU meldet FEHL:</b> zuerst FB1 (3V3_SENS an Pin 5/8 von U4 messen: 3,3 V) und U12 (Nachbarpins, Pin 1 "
         "richtig?). <b>Barometer FEHL, IMU OK:</b> eher U5 selbst. <b>Alle SPI-Sensoren FEHL:</b> U12, oder SPI1 am "
         "Teensy-Sockel (Lötstellen A1). <b>Mag/SHT FEHL:</b> I²C-Leitungen SDA/SCL am Sockel."),
    P("Schritt B: Schienen mit dem PC-Werkzeug", "h2"),
    P("<i>python tools/bench_test.py --no-2s</i> fragt die Spannungen aus Stufe 1–2 ab, prüft die Sollbereiche und "
      "schreibt einen Bericht nach <i>test_reports/</i>. Nach Stufe 4 ohne <i>--no-2s</i>, dann mit VBAT_PROT und VSERVO."),
    P("Schritt C: nach Stufe 4 und 5 (mit 2S)", "h2"),
    P("<i>all full</i> bzw. <i>python tools/bench_test.py --skip-rails --full</i>: LEDs rot/grün/blau/weiß, Summer, "
      "Kamera-Trigger, Servos 1–4 (<i>servo 1 center</i>, <i>sweep</i>), Rollmotor (zwei kurze Pulse), SD-Karte. Das "
      "Werkzeug fragt bei jeder sichtbaren Prüfung nach („LED rot? j/n“)."),
    P("Schritt D: Pyro nur mit Glühlämpchen", "h2"),
    P("An J_PYRO1 ein Glühlämpchen oder 2 Ω, <b>nie einen Anzünder</b>. J_ARM brücken, dann <i>pyro 1 500</i>; die "
      "Firmware fragt nach und zündet nur nach der Eingabe <i>JA</i>. Danach J_ARM wieder öffnen."),
    P("Schritt E: Nachzügler", "h2"),
    P("Nach dem Einlöten von U6: <i>fit ina on</i>, dann <i>ina</i> (Busspannung ≈ 2S-Spannung, Strom ≈ 0 ohne Last). "
      "Nach U10 mit Antenne: <i>fit lora on</i>, dann <i>lora</i> (Parameter lesen, PING an die Bodenstation). Nach J11 "
      "mit dem NEO-6M: <i>fit gps on</i>, dann <i>gps</i> (NMEA-Sätze, draußen Fix)."),
    P("Was auf der echten Platine noch zu bestätigen ist", "h2"),
    P("Der LSM6DSV16X-Treiber ist neu und bisher nur übersetzt, nicht auf Hardware gelaufen. Beim ersten Lauf prüfen:"),
    *bullets(["<i>imu_rate</i> zeigt etwa 960 Hz (ODR-Code 0x09).",
              "<i>imu_rest</i>: Betrag der Beschleunigung ≈ 9,8 m/s²; eine Vierteldrehung von Hand ergibt etwa 90° "
              "(Messbereiche ±16 g und ±2000 °/s).",
              "Selbsttest-Grenzen (Accel 50–1700 mg, Gyro 150–700 °/s) gegen das Datenblatt DS13510 halten; schlägt "
              "der Selbsttest knapp fehl, liegt es eher an den Grenzen als am Chip.",
              "Temperatur der IMU gegen ein Raumthermometer; Achsrichtungen mit <i>cal axes</i>.",
              "Ohne E22 liegen die LoRa-Pads auf etwa 0 V (die Firmware hält M0/M1/AUX hochohmig)."]),
]

if __name__ == "__main__":
    build()
