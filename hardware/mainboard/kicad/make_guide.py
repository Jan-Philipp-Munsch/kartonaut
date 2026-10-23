"""Rundgang durch die Platine als PDF: RUNDGANG_PLATINE.pdf (system Python with Pillow and reportlab).

    "%LOCALAPPDATA%/Programs/KiCad/10.0/bin/python.exe" guide_dump.py     # board geometry -> out/guide/board.json
    python make_guide.py                                                  # pictures and PDF

Uses the renders in img/ (./make.sh img) and draws its own pictures from the board (guide_figures.py)."""
import json
from pathlib import Path

from PIL import Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image as RLImage, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

import guide_figures as gf

HERE = Path(__file__).resolve().parent
OUT = HERE / "RUNDGANG_PLATINE.pdf"
pdfmetrics.registerFont(TTFont("Arial", "C:/Windows/Fonts/arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", "C:/Windows/Fonts/arialbd.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Italic", "C:/Windows/Fonts/ariali.ttf"))
from reportlab.pdfbase.pdfmetrics import registerFontFamily
registerFontFamily("Arial", normal="Arial", bold="Arial-Bold", italic="Arial-Italic", boldItalic="Arial-Bold")

BLUE = colors.HexColor("#1f3d7a")
ST = {
    "title": ParagraphStyle("title", fontName="Arial-Bold", fontSize=24, leading=29, textColor=BLUE, spaceAfter=6),
    "sub": ParagraphStyle("sub", fontName="Arial", fontSize=12, leading=16, textColor=colors.HexColor("#444444")),
    "h1": ParagraphStyle("h1", fontName="Arial-Bold", fontSize=16, leading=20, textColor=BLUE, spaceBefore=4, spaceAfter=6),
    "h2": ParagraphStyle("h2", fontName="Arial-Bold", fontSize=11.5, leading=15, textColor=BLUE, spaceBefore=8, spaceAfter=3),
    "p": ParagraphStyle("p", fontName="Arial", fontSize=9.6, leading=13.4, spaceAfter=5),
    "li": ParagraphStyle("li", fontName="Arial", fontSize=9.6, leading=13.2, leftIndent=12, bulletIndent=2, spaceAfter=2.5),
    "cap": ParagraphStyle("cap", fontName="Arial-Italic", fontSize=8.4, leading=11, textColor=colors.HexColor("#555555"),
                          alignment=TA_CENTER, spaceBefore=3, spaceAfter=8),
    "cell": ParagraphStyle("cell", fontName="Arial", fontSize=8.2, leading=10.2),
    "cellb": ParagraphStyle("cellb", fontName="Arial-Bold", fontSize=8.2, leading=10.2),
    "box": ParagraphStyle("box", fontName="Arial", fontSize=9.2, leading=12.8),
}


def P(t, s="p"):
    return Paragraph(t, ST[s])


def bullets(items):
    return [Paragraph(t, ST["li"], bulletText="•") for t in items]


def img(path, width_cm, cap=None):
    w, h = Image.open(path).size
    flow = [RLImage(str(path), width=width_cm * cm, height=width_cm * cm * h / w)]
    if cap:
        flow.append(P(cap, "cap"))
    return KeepTogether(flow)


def table(rows, widths, head=True, font=8.2):
    data = [[Paragraph(str(c), ST["cellb" if (head and i == 0) else "cell"]) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=[w * cm for w in widths], repeatRows=1 if head else 0)
    style = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b8c2d6")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
             ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]
    if head:
        style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e3eaf6")))
    t.setStyle(TableStyle(style))
    return t


def note(text):
    t = Table([[Paragraph(text, ST["box"])]], colWidths=[17 * cm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff6dd")),
                           ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#e0b84a")),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return t


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Arial", 8)
    canvas.setFillColor(colors.HexColor("#777777"))
    canvas.drawString(2 * cm, 1.2 * cm, "Kartonaut Mainboard rev B1 · Rundgang durch die Platine")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Seite {doc.page}")
    canvas.restoreState()


def build():
    f = gf.build_all()
    g = gf.G
    n_tracks, n_vias = len(g["tracks"]), len(g["vias"])
    s = []

    # ---------------------------------------------------------------- title
    s += [P("Rundgang durch die Platine", "title"),
          P("Kartonaut Mainboard rev B1 · 54 × 120 mm · vier Kupferlagen · Stand 23.10.2026", "sub"),
          Spacer(1, 10), img(HERE / "img" / "render_iso.png", 16.5,
                             "3D-Ansicht aus KiCad, mit dem Teensy auf seinen Buchsenleisten und dem LoRa-Modul daneben."),
          P("Diese Anleitung erklärt, wo die Bauteile sitzen, wie Leitungen und Vias funktionieren, warum die Platine vier "
            "Lagen hat, wie sie entstanden ist und was KiCad dabei prüft. Alle Bilder sind aus der aktuellen Platinendatei "
            "gezeichnet. Bei den Draufsichten liegt die <b>Spitze der Rakete oben</b> und das <b>Heck mit dem Triebwerk "
            "unten</b>, genau wie im KiCad-Leiterplatteneditor."),
          table([["Kennzahl", "Wert"],
                 ["Bauteile", "166, davon 9 unbestückt (Pyro 3 und 4, zweites Barometer)"],
                 ["Netze (elektrisch getrennte Verbindungen)", "113"],
                 ["Leiterbahn-Segmente", str(n_tracks)],
                 ["Vias (Durchkontaktierungen)", str(n_vias)],
                 ["Design Rule Check", "0 Fehler, 0 offene Verbindungen, 0 Abweichungen vom Schaltplan"]], [7.5, 9.5]),
          PageBreak()]

    # ---------------------------------------------------------------- 1 orientation
    s += [P("1  Orientierung", "h1"),
          img(HERE / "img" / "render_top.png", 17,
              "Draufsicht, hier quer gelegt: links die Spitze mit den vier Pyro-Steckern, rechts das Heck mit dem XT30-Akkustecker "
              "(gelb). In der Mitte die Buchsenleisten für den Teensy, darunter das LoRa-Funkmodul."),
          P("Eine Platine ist ein Stapel aus Glasfaser-Epoxid (FR4) mit Kupferschichten dazwischen und außen. Die Bauteile "
            "sitzen alle auf der <b>Oberseite</b>. Grün oder hier blau ist der <b>Lötstopplack</b>: er deckt das Kupfer ab, "
            "nur die Lötflächen (Pads) bleiben frei. Weiß ist der <b>Bestückungsdruck</b> mit Namen und Markierungen."),
          P("In KiCad gibt es ein Koordinatensystem in Millimetern: <b>x nach rechts, y nach unten</b>. Unsere Platine "
            "liegt zwischen x 100 und 154 und zwischen y 50 (Spitze) und 170 (Heck). Die Statusleiste unten in KiCad zeigt "
            "die Position des Mauszeigers. Die Positionsangaben in dieser Anleitung beziehen sich darauf."),
          img(HERE / "img" / "render_bottom.png", 13, "Unterseite: keine Bauteile, nur die Versorgungsfläche, Bohrungen und Testpunkte."),
          PageBreak()]

    # ---------------------------------------------------------------- 2 parts
    rows = [["Nr", "Bauteil", "Aufgabe"]] + [[str(i), f"<b>{short}</b> ({ref})", fn]
                                            for i, (ref, short, fn) in enumerate(gf.CALLOUTS, 1)]
    t = Table([[RLImage(str(f["map"]), width=7.6 * cm, height=7.6 * cm * Image.open(f["map"]).size[1] / Image.open(f["map"]).size[0]),
                table(rows, [0.7, 3.9, 4.6])]], colWidths=[8.0 * cm, 9.4 * cm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    s += [P("2  Wo die Bauteile sitzen", "h1"),
          P("Jedes Rechteck ist der Platzbedarf eines Bauteils (sein „Courtyard“), eingefärbt nach Aufgabe. Der Teensy steckt "
            "auf Buchsenleisten 8,5 mm über der Platine. Darunter ist Platz für flache Bauteile, deshalb sitzen IMU, "
            "CS-Decoder und Analogmux unter ihm."),
          img(f["legend"], 17), t, PageBreak()]
    s += [P("Die Aufteilung folgt den Strömen", "h2"),
          *bullets([
              "<b>Heck (unten):</b> Hier kommt die Energie an. Rechts der 2S-Akku über den XT30-Stecker J1, dann die Kette "
              "Verpolschutz Q1, Sicherung F1, Lastschalter Q6 und der Shunt R_SH1 zur Strommessung. Links die 1S-Seite: Akku J2, "
              "Schalter J3, Lader und der Wandler U2, der daraus 5 V macht. Ganz unten die zwei TVC-Servos, damit ihr Strom kurz bleibt.",
              "<b>Mitte:</b> der Teensy als Rechner. Die IMU U4 sitzt auf der Rollachse, also genau in der Mitte. Decoder U12 und "
              "Mux U13 liegen direkt an den Teensy-Pins, die sie bedienen.",
              "<b>Rechter Streifen:</b> alles, was Kraft braucht: Servos J7 und J16, Rollmotor J8 mit Treiber U7, dann Stapelstecker "
              "J15 und Arming-Stecker J4. Am Rand laufen die breiten Strompfade.",
              "<b>Linker Streifen:</b> Funk und Peripherie: LoRa-Modul U10, GPS, Kamera, LEDs.",
              "<b>Spitze (oben):</b> die vier Pyro-Ausgänge. Unter jedem Stecker eine Spalte aus Schutzdiode und Schalt-FET, damit "
              "der Zündstrom auf kürzestem Weg fließt."]),
          note("<b>Faustregel für die Platzierung:</b> Erst kommen die Bauteile, die mechanisch festliegen: Stecker am Rand, "
               "Teensy, Bohrungen. Dann die, durch die viel Strom fließt, möglichst kurz hintereinander. Kleinteile wie "
               "Kondensatoren gehören direkt an den Pin, den sie versorgen. Erst danach wird verlegt. Fast alle Probleme beim "
               "Verlegen haben ihre Ursache in der Platzierung."),
          PageBreak()]

    # ---------------------------------------------------------------- 3 layers
    s += [P("3  Warum vier Lagen?", "h1"),
          img(f["stack"], 16.5, "Querschnitt durch die Platine. Kupfer ist farbig, Isolierstoff beige. Ein Via ist eine verkupferte "
                                "Bohrung, die alle Lagen an einer Stelle verbinden kann."),
          P("Eine einfache Platine hat zwei Lagen: oben und unten. Unsere hat zwei weitere im Inneren. Jede hat eine feste Aufgabe:"),
          table([["Lage", "Aufgabe", "Warum"],
                 ["F.Cu (oben)", "Bauteile, die meisten Signale, Strompfade als Flächen", "Hier sitzen die Pads, also beginnt und endet hier fast jede Leitung."],
                 ["In1.Cu", "eine durchgehende GND-Fläche", "Jede Leitung braucht einen Rückweg für ihren Strom. Liegt direkt unter ihr eine "
                  "geschlossene Massefläche, fließt der Rückstrom genau darunter zurück. Das hält Störungen klein und die Messwerte ruhig."],
                 ["In2.Cu", "zweite Signallage, Lücken mit GND gefüllt", "Mit 166 Bauteilen auf 54 × 120 mm passen nicht alle Leitungen auf eine Lage. "
                  "Wo sich zwei kreuzen müssen, geht eine über ein Via nach In2."],
                 ["B.Cu (unten)", "Versorgungsflächen GND_PWR und 5V_SYS", "Breite Kupferflächen verteilen Strom mit wenig Widerstand, ohne dass "
                  "dafür Leitungen gezogen werden müssen."]], [2.6, 5.0, 9.4]),
          Spacer(1, 6),
          P("Mit nur zwei Lagen müsste die Massefläche zwischen den Leitungen zerstückelt werden. Rückströme liefen dann Umwege, und genau "
            "diese Umwege strahlen und stören. Für die IMU, die feine Drehraten misst, und den Funk ist das kritisch. Bei JLCPCB kostet "
            "die vierlagige Platine nur wenig mehr als die zweilagige."),
          PageBreak(),
          img(f["layers"], 17, "Die vier Kupferlagen einzeln, jede in ihrer KiCad-Farbe: F.Cu rot, In1 grün, In2 orange, B.Cu blau. "
                               "Weiß ist kupferfrei. In1 ist fast geschlossen, die weißen Punkte sind Vias anderer Netze, die hindurchgehen."),
          P("Auf F.Cu sieht man die feinen Leitungen zwischen den Pads, auf In2 die längeren Wege quer über die Platine. In1 ist eine "
            "einzige Fläche. Auf B.Cu erkennt man die Teilung in zwei Flächen, mehr dazu auf der nächsten Seite."),
          PageBreak()]

    # ---------------------------------------------------------------- 4 planes
    s += [P("4  Die Flächen: Masse und Versorgung", "h1"),
          img(f["planes"], 14.5, "Links In1 (GND, durchgehend), rechts B.Cu: grün GND_PWR, orange 5V_SYS. Weiße Punkte sind Vias, "
                                  "weiße Linien kurze Signalstücke, die auf B.Cu laufen."),
          *bullets([
              "<b>GND</b> ist die Masse der Elektronik: Rechner, Sensoren, Funk. Sie liegt als ganze Lage auf In1. Jedes GND-Pad "
              "bekommt direkt daneben ein eigenes Via dorthin.",
              "<b>GND_PWR</b> ist die Masse der Leistung: Servos, Motor, Pyro und der 2S-Akku. Diese Ströme sind groß und springen "
              "beim Anlaufen eines Servos. Sie sollen nicht durch die empfindliche Masse fließen.",
              "Beide Massen sind an genau einer Stelle verbunden, am <b>Sternpunkt NT1</b> direkt am Minuspol des XT30. So können "
              "die Leistungsströme nicht durch die Elektronikmasse zurückfließen.",
              "<b>5V_SYS</b> ist die 5-V-Versorgung aus dem Wandler U2. Sie liegt als Fläche unter der 1S-Seite und unter dem Teensy."]),
          note("<b>Warum die Flächen nicht zerschnitten werden sollen:</b> Ein Schlitz in einer Fläche zwingt den Strom zu einem Umweg. "
               "Deshalb liegen auf B.Cu nur wenige kurze Signalstücke, und die Strom-Netze nie. Wo ein Signal doch durch "
               "die Fläche musste, ist das in README §5.5 mit Länge aufgeführt."),
          PageBreak()]

    # ---------------------------------------------------------------- 5 power paths
    pw, ph = Image.open(f["power"]).size
    left = [RLImage(str(f["power"]), width=7.4 * cm, height=7.4 * cm * ph / pw),
            P("Strompfade auf F.Cu, farbig hervorgehoben. Grau sind alle anderen Leitungen und Pads der Oberseite.", "cap")]
    right = [P("Durch einige Netze fließen mehrere Ampere: der 2S-Akkustrom, die Servo-Versorgung VSERVO und beim Zünden kurz "
               "bis zu 5 A durch einen Pyro-Kanal. Dafür reichen normale Leiterbahnen nicht. Diese Netze sind <b>breite "
               "Kupferflächen</b> auf der Oberseite, im Generator „Korridore“ genannt:"),
             *bullets([
                 "<b>2S-Kette:</b> XT30 J1 → VBAT2_RAW → Verpolschutz Q1 → VBAT2_REV → Sicherung F1 → VBAT2_F → "
                 "Lastschalter Q6 → VBAT_PROT.",
                 "<b>VBAT_PROT</b> geht von Q6 nach links über F1 zum Shunt und nach rechts an den Rand, dort hoch zum "
                 "Arming-Stecker J4.",
                 "<b>VBAT_ARMED</b> kommt aus J4 zurück und läuft als Band hinter den vier Pyro-Steckern entlang.",
                 "<b>VSERVO</b> kommt aus dem Shunt, läuft als Bus unter dem Teensy quer zu den TVC-Servos und als Schiene "
                 "am rechten Rand zu Servo 3 und 4, zum Motortreiber und zum Stapelstecker.",
                 "<b>PYRO_NEG:</b> vom Schalt-FET jedes Kanals senkrecht zum Stecker."]),
             P("Strom-Netze bleiben ausschließlich auf der Oberseite und haben kein Via. Ein Via verträgt nur etwa 1 A, und die "
               "Innenlagen haben dünneres Kupfer (15 statt 35 µm). Außerdem soll die 2S-Spannung nicht neben empfindlichen "
               "Innenlagen-Signalen liegen."),
             P("Damit kein Autorouter eine fremde Leitung quer durch einen Strompfad legt, hat jeder Korridor eine 0,2 mm schmale "
               "Sperre auf seiner Mittellinie. Sie gilt nur während des Routens und wird danach gelöscht.")]
    t5 = Table([[left, right]], colWidths=[7.8 * cm, 9.2 * cm])
    t5.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    s += [P("5  Die Strompfade", "h1"), t5, PageBreak()]

    # ---------------------------------------------------------------- 6 tracks and vias
    s += [P("6  Leitungen und Vias", "h1"),
          P("Eine Leiterbahn verbindet zwei Pads desselben Netzes. Zwei Größen bestimmen sie: die <b>Breite</b> und der <b>Abstand</b> "
            "zu fremdem Kupfer. Beides ist über <b>Netzklassen</b> festgelegt:"),
          table([["Netzklasse", "Breite", "Abstand", "Beispiele"],
                 ["Strom", "1,0 mm (Fläche)", "0,2 mm", "VBAT2_*, VBAT_PROT, VSERVO, VBAT_ARMED, PYRO*_NEG"],
                 ["Rückstrom", "0,8 mm", "0,2 mm", "GND_PWR, wo es nicht über die Fläche geht"],
                 ["Versorgung", "0,6 mm", "0,2 mm", "5V_SYS, 3V3_RF, VSYS_IN, MOT_A/B"],
                 ["Wandler", "0,4 mm", "0,15 mm", "U2_L1, U2_L2 (Spule des Wandlers)"],
                 ["Default", "0,2 mm", "0,15 mm", "alle Signale wie SPI, I2C, UART, Chip-Selects"]], [2.8, 2.6, 2.0, 9.6]),
          Spacer(1, 4),
          P("Die Breite richtet sich nach dem Strom: Eine 0,2-mm-Bahn auf der Oberseite trägt etwa 0,5 A, eine 1-mm-Bahn etwa 2,5 A. "
            "Der Abstand verhindert Kurzschlüsse bei der Fertigung. JLCPCB fertigt sicher ab 0,127 mm Abstand und 0,09 mm Breite."),
          P("Wann braucht man ein Via?", "h2"),
          P("Zwei Leitungen auf derselben Lage dürfen sich nicht kreuzen. Muss eine Leitung über eine andere hinweg, wechselt sie "
            "über ein Via auf eine andere Lage und kommt danach mit einem zweiten Via zurück. Das Beispiel zeigt Pyro-Kanal 3:"),
          img(f["pyro3"], 9.5, "Pyro 3. Rot: Oberseite, blau: In2, gelbe Kreise: Vias. Hervorgehoben sind PYRO3_NEG und PYRO3_SENSE, "
                               "alles andere ist blass."),
          *bullets([
              "Die breite rote Bahn ist <b>PYRO3_NEG</b>: Zündstrom vom FET Q8 zur Schutzdiode D5, als Strom-Netz nur oben.",
              "Die Messleitung <b>PYRO3_SENSE</b> von R40 musste diese Bahn kreuzen. Sie taucht über ein Via auf In2 ab, läuft unter der "
              "Zündbahn durch und kommt über das zweite Via wieder hoch.",
              "Die anderen Leitungen weichen in Abstand aus, die zwei Wege berühren sich nirgends."]),
          PageBreak(),
          P("Ein schwieriges Beispiel: der Motortreiber", "h2"),
          img(f["drv"], 10.0, "DRV8833 (U7). Rot: Oberseite, blau: In2, grün: B.Cu. Hervorgehoben MOT_A und MOT_B zum Motorstecker J8."),
          P("Der DRV8833 hat seine Ausgänge abwechselnd an den Pins: MOT_A an Pin 2 und 7, MOT_B an Pin 4 und 5 dazwischen. Auf "
            "einer Lage kann man nicht beide Paare zum Stecker J8 führen, ohne dass sich eine Bahn einschließt. Gelöst ist es so: "
            "Jeder Ausgang bekommt ein Via direkt am Pin und läuft auf B.Cu (grün) zu seinem Steckerpin. J8 ist ein bedrahteter "
            "Stecker, sein Pin geht durch alle Lagen und lässt sich deshalb auch von unten erreichen."),
          note("<b>Warum manche Bahnen ihre Breite wechseln:</b> Eine Bahn kann nicht breiter sein als das Pad, in das sie läuft. Der "
               "Autorouter verjüngt sie deshalb kurz vor kleinen Pads, etwa von 0,6 auf 0,4 mm. Das ist normal. Elektrisch zählt "
               "die engste Stelle, und die ist nur ein kurzes Stück. Die feinen Treppen aus 0,05-mm-Stufen, die beim Nacharbeiten "
               "entstanden waren, sind inzwischen zu geraden Stücken zusammengefasst. Keine Bahn ist schmaler als 0,15 mm."),
          P("Sonderzonen", "h2"),
          img(f["imu"], 5.6, "IMU U4: violett der 5-mm-Kreis, orange der 2,6-mm-Kreis direkt unter dem Chip."),
          *bullets([
              "<b>IMU:</b> Im Kreis von 5 mm um den Chip liegen nur seine eigenen fünf GND-Vias und keine Leitungen auf In2. "
              "Die Masse unter dem Sensor bleibt so ungestört.",
              "<b>LoRa-Modul:</b> Unter dem Modul liegen keine Leitungen auf F.Cu und In2. Das Funkmodul braucht eine ruhige Massefläche "
              "unter sich. Die Pins sitzen an seinem Rand, die Leitungen gehen außen herum."]),
          PageBreak()]

    # ---------------------------------------------------------------- 7 process
    s += [P("7  Wie die Platine entstanden ist", "h1"),
          img(f["pipeline"], 17, "Die Kette aus Skripten, mit der Schaltplan und Platine erzeugt werden."),
          P("Die Platine ist nicht von Hand gezeichnet, sondern aus Code erzeugt. Das hat einen Vorteil: Jede Entscheidung steht "
            "nachvollziehbar in einer Datei und lässt sich wiederholen."),
          *bullets([
              "<b>circuit.py</b> beschreibt die Schaltung: jedes Bauteil mit Gehäuse und welcher Pin an welchem Netz hängt.",
              "<b>gen_schematic.py</b> zeichnet daraus den Schaltplan. Der ERC prüft ihn, etwa auf offene Eingänge oder zwei Ausgänge an "
              "einem Netz. <b>check_design.py</b> vergleicht die Netzliste mit der Spezifikation.",
              "<b>gen_pcb.py place</b> setzt die Bauteile: feste Positionen für Stecker, Teensy und Leistungsteile, die Kleinteile "
              "sucht ein Platzierer neben ihrem IC. Dann zeichnet es die Strompfade als Flächen, legt Sperrflächen an und setzt die "
              "Vias der GND- und Versorgungs-Pads.",
              "<b>Freerouting</b> ist ein Autorouter. Er bekommt die Platine als Datei, verlegt in etwa 17 Minuten die Signale und gibt "
              "das Ergebnis zurück. Zwei kurze Nachläufe versuchen die Reste.",
              "Der <b>DRC</b> in KiCad prüft das Ergebnis."]),
          P("Was am 23.10. passiert ist", "h2"),
          *bullets([
              "Nach Freerouting blieben 21 Verbindungen offen. Sieben davon gingen von Hand in KiCad und per Skript zu.",
              "Die anderen 14 lagen an der Platzierung. Ein Beispiel: Der Strompfad VBAT_PROT war im Generator vorgesehen, aber "
              "Freerouting legte Signalleitungen quer hindurch, weil die Sperrfläche bei schmalen Pfaden zu nichts schrumpfte. "
              "Außerdem saßen zwei Kondensatoren des Motortreibers 8 bis 14 mm von ihm entfernt.",
              "Also wurde der Generator korrigiert: Jeder Strompfad hat jetzt eine schmale Sperre auf seiner Mittellinie. Die "
              "Kondensatoren haben feste Plätze am Treiber, Q6, R2 und R4 sind neu angeordnet, und J18 und J15 bekommen eigene Strompfade.",
              "Neuer Lauf: 18 offene Stellen, aber andere und leichtere. Die gingen mit einem eigenen Gitter-Router und "
              "Einzelkorrekturen zu. Am Ende wurden die Treppenwege begradigt."]),
          note("<b>Wichtig:</b> Ab jetzt ist die Platinendatei die Quelle. Ein neuer Lauf von <b>./make.sh pcb</b> würde eine andere "
               "Platine erzeugen und die Nacharbeit löschen. Kleine Änderungen macht man ab hier direkt in KiCad."),
          PageBreak()]

    # ---------------------------------------------------------------- 8 checks
    s += [P("8  Was KiCad prüft und was nicht", "h1"),
          P("Der <b>Design Rule Check (DRC)</b> vergleicht jede Bahn, jedes Pad und jedes Via mit den Regeln aus dem Projekt. Er "
            "unterscheidet <b>Fehler</b>, die behoben werden müssen, und <b>Warnungen</b>, die man bewerten kann."),
          table([["KiCad prüft", "Beispiel auf unserer Platine"],
                 ["Abstand zwischen Kupfer verschiedener Netze", "mindestens 0,127 mm, Strom- und Versorgungsklassen 0,2 mm"],
                 ["Mindestbreite von Bahnen", "0,09 mm (Fertigungsgrenze), tatsächlich ab 0,15 mm"],
                 ["Vias und Bohrungen", "Via 0,6/0,3 mm, Restring, Abstand Loch zu Loch"],
                 ["Abstand zum Platinenrand", "0,2 mm"],
                 ["Offene Verbindungen", "jedes Pad eines Netzes muss mit den anderen verbunden sein"],
                 ["Kurzschlüsse", "zwei Netze, die sich berühren"],
                 ["Sperrflächen", "unter dem LoRa-Modul, um die IMU"],
                 ["Bestückungsdruck", "Text über Pads oder über dem Rand: bei uns nur Warnungen"],
                 ["Übereinstimmung mit dem Schaltplan", "jedes Bauteil und jedes Netz wie im Schaltplan"]], [7.2, 9.8]),
          Spacer(1, 8),
          table([["KiCad prüft nicht", "Wer es stattdessen prüft"],
                 ["ob eine Bahn breit genug für ihren Strom ist", "Netzklassen und Strompfade im Generator; Liste im Prüfskript"],
                 ["„Strom-Netze nur oben, ohne Via“", "review_check_layout.py"],
                 ["„keine fremden Vias und kein In2 nahe der IMU“", "teils Sperrflächen, sonst review_check_layout.py"],
                 ["Schlitze in den Flächen, Rückstromwege, EMV", "Review mit dem Kollegen anhand der Lagenbilder"],
                 ["Wärme, z. B. am Motortreiber", "Datenblatt, Wärmepad mit Vias zur GND_PWR-Fläche"],
                 ["ob die Schaltung richtig ist", "ERC, check_design.py, Review"],
                 ["ob alles mechanisch passt", "1:1-Ausdruck in den Kuppler halten"]], [7.2, 9.8]),
          Spacer(1, 8),
          P("Ein bestandener DRC heißt also: Die Platine ist <b>fertigbar und richtig verbunden</b>. Ob sie gut ist, zeigt erst der Blick "
            "eines Menschen. Deshalb steht als Nächstes das Review mit dem Kollegen an."),
          PageBreak()]

    # ---------------------------------------------------------------- 9 KiCad tips and glossary
    s += [P("9  Selbst in KiCad nachsehen", "h1"),
          table([["Was", "Wie im Leiterplatteneditor"],
                 ["Ein Netz hervorheben", "Mauszeiger auf eine Bahn oder ein Pad, Taste <b>`</b> (Gravis, links neben der 1). Noch einmal drücken hebt es wieder auf."],
                 ["Eine Lage allein ansehen", "Rechts im Panel „Darstellung“ auf das Auge neben einer Lage klicken; Bild hoch und Bild runter wechseln die aktive Lage."],
                 ["Nur die aktive Lage kräftig zeigen", "Menü <b>Ansicht → Hochkontrastmodus</b>"],
                 ["Eigenschaften einer Bahn", "Bahn anklicken: links stehen Netz, Breite und Lage."],
                 ["Messen", "Menü <b>Inspektion → Messwerkzeug</b>, dann zwei Punkte anklicken"],
                 ["3D-Ansicht", "Menü <b>Ansicht → 3D-Betrachter</b>"],
                 ["DRC laufen lassen", "Menü <b>Inspektion → Designregeln überprüfen</b>, dann „DRC starten“"]], [5.0, 12.0]),
          Spacer(1, 10),
          P("Kleines Glossar", "h1"),
          table([["Begriff", "Bedeutung"],
                 ["Pad", "Lötfläche eines Bauteils"],
                 ["Leiterbahn (Track)", "Kupferstreifen zwischen zwei Punkten auf einer Lage"],
                 ["Via", "verkupferte Bohrung, verbindet Lagen an einer Stelle"],
                 ["Netz", "alles, was elektrisch zusammengehört, z. B. GND oder SPI1_SCK"],
                 ["Netzklasse", "Gruppe von Netzen mit gleicher Breite und gleichem Abstand"],
                 ["Zone, Fläche", "Kupferfläche, die KiCad selbst ausfüllt und um fremdes Kupfer herum ausspart"],
                 ["Sperrfläche (Keepout)", "Bereich, in dem keine Bahnen oder Vias liegen dürfen"],
                 ["Courtyard", "Platzbedarf eines Bauteils; zwei Courtyards dürfen sich nicht überlappen"],
                 ["DRC / ERC", "Regelprüfung der Platine / des Schaltplans"],
                 ["Autorouter", "Programm, das Leitungen selbst verlegt; hier Freerouting"],
                 ["Schiebe-Router", "KiCads Werkzeug, das beim Verlegen fremde Bahnen beiseiteschiebt"],
                 ["Shunt", "kleiner, genauer Widerstand, an dem man den Strom misst"],
                 ["Sternpunkt", "die eine Stelle, an der zwei Massen verbunden sind"],
                 ["THT / SMD", "Bauteil mit Drahtbeinen durch die Platine / Bauteil zum Auflöten auf die Oberfläche"]], [4.2, 12.8])]

    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm,
                            bottomMargin=1.8 * cm, title="Rundgang durch die Platine", author="Kartonaut")
    doc.build(s, onFirstPage=footer, onLaterPages=footer)
    print(OUT)


if __name__ == "__main__":
    build()
