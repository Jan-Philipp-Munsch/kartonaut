"""Start- und Landepad für die Rakete (22.10.2026). Anforderungen: docs/Schnittstellen_Bodensystem_2026-10-22.md, S1 und S2.

    python cad/landingpad.py              Pad bauen, prüfen, export/landingpad.step, Bilder docs/img/cad/landingpad*.png
    python cad/landingpad.py --no-render  ohne Blender

Aufbau (Maße unten, jede Zahl mit Quelle wie in params.py):
  Deck:        Achteck 1250 mm über die Flächen aus Siebdruckplatte 18 mm, zwei Hälften (Teilung y = 0), oben verzinktes
               Stahlblech 0,75 mm als nicht brennbare Lande- und Startfläche. Unten zwei Kanthölzer 45 × 70 quer zur Teilung,
               mit M8 in Einschlagmuttern: sie verbinden die Hälften. Drei Fußklötze mit Stellfüßen M10 (drei Punkte, kippelt nicht),
               eine Dosenlibelle bündig eingelassen.
  Strahlplatte: Einsatz in einer Aussparung 320 × 320 in der Mitte: Stahl 2 mm auf Zementfaserplatte 16 mm, darunter eine
               Trägerplatte 400 × 400 × 12 (Zementfaser), von unten mit 4 × M6 an beiden Hälften. Oberkante 0,75 mm unter dem Deck.
               Der Strahl trifft senkrecht auf und läuft flach nach allen Seiten ab (zwischen den drei Stützen frei).
  Startstützen: drei abnehmbare Stützen bei 60°, 180°, 300° (frei von Schlüsselschalter +x und Luken ±y): Fußplatte Alu 50 × 5
               mit zwei M6 in Langlöchern (radial einstellbar), Vierkantrohr 20 × 20 × 1,5 als Führung (1,5 mm Luft zum Rohr,
               160 mm über der Rohrunterkante), Auflage-Klotz unter der Rohrunterkante, Knotenblech.
  Zündkasten:  auf der Fußplatte der Stütze bei 180° (geht mit ihr ab): Abzweigkasten mit XT30-Buchse für die Zündleitung (S2),
               zweiter XT30-Buchse für den Shunt-Stecker (parallel zum Anzünder), zwei Polklemmen für das 30-cm-Kabel mit
               Krokoklemmen, Hitzeschild aus Stahlblech zur Düse hin.
Koordinaten wie die Rakete: z = 0 Düsenebene; das Deck liegt bei z = DECK_Z, die Achse des Pads ist die Raketenachse.
"""
import json, math, os, sys, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cadquery as cq
from cadquery import exporters
import params as P
import build
from common import Parts, tube, cyl, cyl_between, box_from, rot_z

# --------------------------------------------------------------------------- Maße
PAD_NOZZLE_H = 100.0      # [Annahme] Düse über der Deckfläche; S1 fordert ≥ 80 über der Strahlplatte (hier 100,75)
DECK_Z = -PAD_NOZZLE_H    # Oberkante Deckblech
DECK_AF = 1250.0          # [Annahme] Achteck über die Flächen; S1 fordert Ø ≥ 1200 (Inkreis 1250)
COVER_T = 0.75            # [Annahme] verzinktes Stahlblech, Baumarkt/Metallhandel
PLY_T = 18.0              # [Annahme] Siebdruckplatte (Birke) 18 mm
SEAM_GAP = 1.0            # [Annahme] Fuge zwischen den Hälften
PLY_Z = (DECK_Z - COVER_T - PLY_T, DECK_Z - COVER_T)
BATTEN = (70.0, 45.0)     # [Annahme] Kantholz 45 × 70, flach (Breite × Höhe)
BATTEN_X = 250.0          # [Annahme] zwei Latten bei x = ±250 längs y, verbinden die Hälften
BATTEN_Y = 580.0          # halbe Länge (Deck bei x = 250 bis y = 625)
FOOT_R = 540.0            # [Annahme] Stellfüße auf r = 540 bei 90°, 210°, 330°
FOOT_PHI = (90.0, 210.0, 330.0)
FOOT_BLOCK = (120.0, 45.0)   # [Annahme] Fußklotz 120 × 120 × 45 aus Kantholz-Resten, geleimt und geschraubt
FOOT_EXT = 40.0           # [Annahme] Stellfuß M10 ragt 40 mm unter den Klotz (Verstellbereich etwa 25 … 60)
FOOT_PLATE = (50.0, 10.0) # [Annahme] Gelenkteller Ø 50
GROUND_Z = PLY_Z[0] - FOOT_BLOCK[1] - FOOT_EXT

BLAST_CUT = 320.0         # Aussparung in Deck und Blech (quadratisch, mittig, über der Teilung)
BLAST_PLATE = (316.0, 2.0)   # [Vorgabe S1] Stahl 2 mm; 2 mm Spiel in der Aussparung
BLAST_TOP_Z = DECK_Z - COVER_T   # Strahlplatte bündig mit der Sperrholzoberkante, 0,75 mm unter dem Deckblech
BLAST_BED_T = PLY_T - BLAST_PLATE[1]   # [Annahme] Zementfaserplatte 16 mm (z. B. Duripanel) unter dem Stahl
BLAST_CARRIER = (400.0, 12.0)  # [Annahme] Trägerplatte Zementfaser 400 × 400 × 12 unter dem Deck

STAND_PHI = (60.0, 180.0, 300.0)   # Schlüsselschalter bei +x (0°), Luken A/B bei ±y (90°/270°): Stützen dazwischen
GUIDE_GAP = 1.5           # [Vorgabe S1] 1 … 2 mm Luft zum Rohr
GUIDE_PROFILE = (20.0, 1.5)   # [Annahme] Alu-Vierkantrohr 20 × 20 × 1,5
GUIDE_H = 160.0           # [Vorgabe S1] ≥ 150 mm Führung über der Rohrunterkante
GUIDE_R0 = P.TUBE_OD / 2 + GUIDE_GAP          # Innenfläche der Führung (39,0)
REST_R = (34.0, GUIDE_R0)  # Auflage unter der Ringfläche r = 36,3 … 37,5; innen 4 mm außerhalb des Kardan-Freiraums
REST_H = 10.0             # [Annahme] Auflage-Klotz (Alu 20 × 10, oder PETG) unter der Rohrunterkante
GIMBAL_FREE_R = 30.0      # [Vorgabe S1] unter der Rohrunterkante kein Teil innerhalb r = 30
STAND_FOOT = (50.0, 5.0)  # [Annahme] Alu-Flachstange 50 × 5
STAND_FOOT_R = (40.0, 250.0)   # radial; die Stütze mit Zündkasten reicht bis 345
STAND_FOOT_R_BOX = 345.0
STAND_BOLTS_R = (205.0, 235.0)   # M6 in Einschlagmuttern; bei 60°/300° liegt r = 205 bei |y| = 178, außerhalb der Aussparung
STAND_BOLTS_R_BOX = (205.0, 335.0)
GUSSET = (70.0, 90.0, 5.0)   # [Annahme] Knotenblech Alu 5 mm, radial × hoch
BOX = (216.0, 316.0, 100.0, 55.0)   # [Annahme] Abzweigkasten 100 × 100 × 55 (IP54), radial von 216 bis 316
SHIELD = (212.0, 1.0, 120.0, 70.0)  # [Annahme] Hitzeschild Stahlblech 1 mm: r, Dicke, Breite, Höhe über der Fußplatte
LEVEL_POS = (-340.0, 340.0)   # Dosenlibelle Ø 40 bei 135°, r = 480
LEVEL_D, LEVEL_H = 40.0, 12.0  # [Annahme] Dosenlibelle mit Gehäuse

# Dichten in g/mm³ für die Massen aus dem Volumen; [Annahme] Richtwerte
RHO = {"ply": 0.68e-3, "steel": 7.85e-3, "alu": 2.70e-3, "cement": 1.35e-3, "wood": 0.45e-3, "petg": 0.6e-3}
# Teile mit fester Masse (hohl, gekauft): g [Annahme]
FIXED_M = {"Zündkasten (Abzweigkasten)": 180.0, "Polklemme": 10.0, "XT30-Buchse": 4.0, "XT30-Stecker": 4.0,
           "Shunt-Stecker": 8.0, "Dosenlibelle": 20.0, "Stellfuß": 120.0, "Anzünderkabel": 15.0, "Zündleitung": 0.0}

P.COLORS.update({"deck": (0.70, 0.72, 0.74), "ply": (0.55, 0.38, 0.22), "cement": (0.62, 0.62, 0.58),
                 "blast": (0.30, 0.30, 0.32), "box": (0.85, 0.85, 0.82), "red": (0.85, 0.12, 0.10),
                 "xt30": (0.95, 0.75, 0.10), "black": (0.08, 0.08, 0.08), "level": (0.35, 0.80, 0.45)})

# Stückliste der Kaufteile, Preise grob (Baumarkt/Online, Oktober 2026) [Annahme]
BOM = [
    ("Siebdruckplatte 18 mm, Zuschnitt 1250 × 1250", 1, 45.0),
    ("Stahlblech verzinkt 0,75 mm, 2 × 1250 × 625 (Zuschnitt Metallhandel)", 1, 50.0),
    ("Kantholz 45 × 70, 3 m (Latten 2 × 1160, Fußklötze)", 1, 9.0),
    ("Stellfuß M10 mit Gelenkteller Ø 50", 3, 4.0),
    ("Einschlagmuttern M10 / M8 / M6, Schrauben M8 × 70, M6 × 30 mit Rändelkopf, Senkschrauben", 1, 15.0),
    ("Zementfaserplatte 16 mm und 12 mm, Reste (z. B. Duripanel)", 1, 25.0),
    ("Stahlblech 2 mm, 316 × 316 (Strahlplatte)", 1, 10.0),
    ("Alu-Vierkantrohr 20 × 20 × 1,5, 1 m", 1, 9.0),
    ("Alu-Flachstange 50 × 5, 1 m (Fußplatten, Knotenbleche)", 1, 14.0),
    ("Alu-Flachstange 20 × 10, 0,1 m (Auflagen)", 1, 3.0),
    ("Dosenlibelle Ø 40", 1, 5.0),
    ("Abzweigkasten 100 × 100 × 55, IP54", 1, 6.0),
    ("XT30-Buchsen (2) und Stecker (2, einer als Shunt gebrückt), Litze 1,5 mm²", 1, 8.0),
    ("Polklemmen 4 mm (2), Krokoklemmen-Kabel 30 cm", 1, 7.0),
    ("Fahne REMOVE BEFORE FLIGHT, Stahlblech 1 mm für den Hitzeschild", 1, 6.0),
    ("Druckteile PETG: Einstellring Ø 78 (Lehre), XT30-Halter, Libellenfassung, ca. 60 g", 1, 3.0),
]


def use_config(cfg):
    """Schaltet params zur Laufzeit auf eine Konfiguration (die Module lesen P.* erst beim Bauen)."""
    P.__dict__.update(P.layout(cfg))


def octagon(af, z0, z1):
    return cq.Workplane("XY").workplane(offset=z0).polygon(8, af / math.cos(math.radians(22.5))).extrude(z1 - z0) \
        .rotate((0, 0, 0), (0, 0, 1), 22.5)


# --------------------------------------------------------------------------- Deck (bleibt für die Landung)
def deck():
    out = []
    hole = box_from(-BLAST_CUT / 2, BLAST_CUT / 2, -BLAST_CUT / 2, BLAST_CUT / 2, PLY_Z[0] - 1, DECK_Z + 1)
    level = cyl(LEVEL_D + 1, DECK_Z - LEVEL_H, DECK_Z + 1, *LEVEL_POS)
    for sy, lbl in ((1, "+y"), (-1, "−y")):
        half = box_from(-DECK_AF, DECK_AF, *sorted((sy * SEAM_GAP / 2, sy * DECK_AF)), -1000, 1000)
        ply = octagon(DECK_AF, *PLY_Z).intersect(half).cut(hole).cut(level)
        cov = octagon(DECK_AF, PLY_Z[1], DECK_Z).intersect(half).cut(hole).cut(level)
        out.append((f"Deckhälfte {lbl} Siebdruck 18", ply, "ply", "ply"))
        out.append((f"Deckblech {lbl} 0,75", cov, "deck", "steel"))
    for sx in (-1, 1):
        x = sx * BATTEN_X
        bt = box_from(x - BATTEN[0] / 2, x + BATTEN[0] / 2, -BATTEN_Y, BATTEN_Y, PLY_Z[0] - BATTEN[1], PLY_Z[0])
        out.append((f"Latte {'links' if sx < 0 else 'rechts'} 45x70", bt, "wood", "wood"))
    for i, phi in enumerate(FOOT_PHI):
        x, y = FOOT_R * math.cos(math.radians(phi)), FOOT_R * math.sin(math.radians(phi))
        b = FOOT_BLOCK[0] / 2
        blk = box_from(x - b, x + b, y - b, y + b, PLY_Z[0] - FOOT_BLOCK[1], PLY_Z[0])
        out.append((f"Fußklotz {i + 1}", blk, "wood", "wood"))
        z_top = PLY_Z[0] - FOOT_BLOCK[1]
        foot = cyl(10.0, GROUND_Z + FOOT_PLATE[1], z_top + 25, x, y).union(cyl(FOOT_PLATE[0], GROUND_Z, GROUND_Z + FOOT_PLATE[1], x, y))
        out.append((f"Stellfuß {i + 1}", foot, "steel", None))
    # Strahlplatten-Einsatz
    s = BLAST_PLATE[0] / 2
    out.append(("Strahlplatte Stahl 2", box_from(-s, s, -s, s, BLAST_TOP_Z - BLAST_PLATE[1], BLAST_TOP_Z), "blast", "steel"))
    out.append(("Strahlplatten-Bett Zementfaser 16", box_from(-s, s, -s, s, PLY_Z[0], BLAST_TOP_Z - BLAST_PLATE[1]), "cement", "cement"))
    c = BLAST_CARRIER[0] / 2
    out.append(("Trägerplatte Zementfaser 12", box_from(-c, c, -c, c, PLY_Z[0] - BLAST_CARRIER[1], PLY_Z[0]), "cement", "cement"))
    out.append(("Dosenlibelle", cyl(LEVEL_D, DECK_Z - LEVEL_H, DECK_Z - 0.3, *LEVEL_POS), "level", None))
    return out


# --------------------------------------------------------------------------- Startstützen (abnehmbar)
def stand(phi, with_box=False):
    """Eine Stütze im lokalen System (x radial nach außen), dann um z gedreht."""
    z0 = DECK_Z
    zf = z0 + STAND_FOOT[1]
    w, t = GUIDE_PROFILE
    r_out = STAND_FOOT_R_BOX if with_box else STAND_FOOT_R[1]
    foot = box_from(STAND_FOOT_R[0], r_out, -STAND_FOOT[0] / 2, STAND_FOOT[0] / 2, z0, zf)
    for r in (STAND_BOLTS_R_BOX if with_box else STAND_BOLTS_R):   # Langloch 6,5 × 16 radial
        foot = foot.cut(cq.Workplane("XY").workplane(offset=z0 - 1).center(r, 0).slot2D(16.0, 6.5, 0).extrude(STAND_FOOT[1] + 2))
    z_top = P.TUBE_BOTTOM_Z + GUIDE_H
    r0 = GUIDE_R0
    post = box_from(r0, r0 + w, -w / 2, w / 2, zf, z_top).cut(box_from(r0 + t, r0 + w - t, -w / 2 + t, w / 2 - t, zf - 1, z_top + 1))
    post = post.faces(">Z").edges("<X").chamfer(1.4)   # Einführschräge innen oben
    rest = box_from(REST_R[0], REST_R[1], -w / 2, w / 2, P.TUBE_BOTTOM_Z - REST_H, P.TUBE_BOTTOM_Z)
    gl, gh, gt = GUSSET
    gus = (cq.Workplane("XZ").polyline([(r0 + w, zf), (r0 + w + gl, zf), (r0 + w, zf + gh)]).close()
           .extrude(gt / 2, both=True))
    tag = f"{phi:.0f}°"
    out = [(f"Stütze {tag} Fußplatte Alu 50x5", foot, "alu", "alu"),
           (f"Stütze {tag} Führung Alu 20x20", post, "alu", "alu"),
           (f"Stütze {tag} Auflage", rest, "printed", "alu"),
           (f"Stütze {tag} Knotenblech", gus, "alu", "alu")]
    if with_box:
        out += ignition_box(zf)
    return [(n, rot_z(s, phi), c, m) for n, s, c, m in out]


def ignition_box(zf):
    """Zündkasten auf der Fußplatte, lokales System der Stütze (x radial nach außen)."""
    x0, x1, wb, hb = BOX
    zt = zf + hb
    box_s = box_from(x0, x1, -wb / 2, wb / 2, zf, zt).edges("|Z").fillet(4.0)
    out = [("Zündkasten (Abzweigkasten)", box_s, "box", None)]
    sr, st, sw, sh = SHIELD
    out.append(("Hitzeschild Stahl 1", box_from(sr, sr + st, -sw / 2, sw / 2, zf, zf + sh), "steel", "steel"))
    for sy in (-1, 1):   # Polklemmen für das Anzünderkabel, nahe der Düsenseite
        out.append((f"Polklemme {'rot' if sy > 0 else 'schwarz'}", cyl(10.0, zt, zt + 18, x0 + 16, sy * 18),
                    "red" if sy > 0 else "black", None))
    # XT30 an der Außenseite: Buchse "LEITUNG" (−y) mit eingestecktem Stecker der Zündleitung, Buchse "SHUNT" (+y) mit Shunt-Stecker
    zc = zf + hb / 2
    for sy, lbl in ((-1, "LEITUNG"), (1, "SHUNT")):
        yc = sy * 18
        out.append((f"XT30-Buchse {lbl}", box_from(x1, x1 + 6, yc - 8, yc + 8, zc - 4, zc + 4), "xt30", None))
    out.append(("XT30-Stecker Zündleitung", box_from(x1 + 6, x1 + 18, -26, -10, zc - 4.5, zc + 4.5), "xt30", None))
    out.append(("Zündleitung 2x0,75 (15 m, Anfang)", cyl_between(6.0, (x1 + 18, -18, zc), (x1 + 120, -18, zc)).union(
        cyl_between(6.0, (x1 + 120, -18, zc), (x1 + 220, -18, zf - STAND_FOOT[1]))), "black", None))
    out.append(("Shunt-Stecker", box_from(x1 + 6, x1 + 18, 10, 26, zc - 4.5, zc + 4.5), "red", None))
    out.append(("Shunt-Fahne REMOVE BEFORE FLIGHT", box_from(x1 + 18, x1 + 19, 12, 24, zc - 60, zc), "red", None))
    # Anzünderkabel 30 cm mit Krokoklemmen: von der roten Polklemme über den Hitzeschild zur Düse (biegsam, reißt beim Start ab)
    pts = [(x0 + 16, 18, zt + 18), (sr - 4, 26, zf + sh + 8), (62, 26, -4), (16, 8, -6)]
    lead = cyl_between(3.0, pts[0], pts[1])
    for a, b in zip(pts[1:], pts[2:]):
        lead = lead.union(cyl_between(3.0, a, b))
    out.append(("Anzünderkabel 30 cm", lead, "red", None))
    return out


def build_pad(start=True):
    """Liste (name, shape, color, group) und Materialtabelle {name: Werkstoff oder None}. start=False: Landekonfiguration."""
    parts = Parts()
    mats = {}
    for n, s, c, m in deck():
        parts.add(n, s, c, "pad")
        mats[n] = m
    if start:
        for phi in STAND_PHI:
            for n, s, c, m in stand(phi, with_box=(phi == 180.0)):
                parts.add(n, s, c, "padstart")
                mats[n] = m
    return parts, mats


def part_mass(name, shape, mat):
    if mat:
        return shape.Volume() * RHO[mat]
    for k, m in FIXED_M.items():
        if name.startswith(k):
            return m
    return 0.0


# --------------------------------------------------------------------------- Prüfungen
def _vol(a, b):
    ba, bb = a.BoundingBox(), b.BoundingBox()
    if ba.xmax < bb.xmin or bb.xmax < ba.xmin or ba.ymax < bb.ymin or bb.ymax < ba.ymin or ba.zmax < bb.zmin or bb.zmax < ba.zmin:
        return 0.0
    try:
        return cq.Workplane().add(a).intersect(cq.Workplane().add(b)).val().Volume()
    except Exception:
        return 0.0


def _shift(parts, dx=0.0, dy=0.0, dz=0.0):
    return [(n, s.translate(cq.Vector(dx, dy, dz)), c, g) for n, s, c, g in parts]


def collisions(rocket, pad, skip=()):
    bad = []
    for rn, rs, _, _ in rocket:
        for pn, ps, _, _ in pad:
            if any(pn.startswith(k) for k in skip):
                continue
            v = _vol(rs, ps)
            if v > 0.5:
                bad.append(f"{rn} / {pn}: {v:.0f} mm³")
    return bad


def check_all():
    """Alle Prüfungen; liefert [(Text, [Befunde])], leer = frei."""
    out = []
    g = P.GIMBAL_MAX_DEG
    pad, _ = build_pad(start=True)
    by = {n: s for n, s, _, _ in pad}
    use_config("erstflug")
    rocket0 = build.build_all()
    # 1 Rakete (Erstflug) mit Kardan 0° und ±7° in beiden Achsen gegen alle Padteile
    bad = []
    nozzle_min = 1e9
    for pitch, yaw in ((0, 0), (g, g), (g, -g), (-g, g), (-g, -g)):
        rk = rocket0 if (pitch, yaw) == (0, 0) else build.build_all(pitch=pitch, yaw=yaw)
        bad += [f"Kardan {pitch:+.0f}/{yaw:+.0f}: {x}" for x in collisions(rk, pad)]
        nozzle_min = min(nozzle_min, min(s.BoundingBox().zmin for n, s, _, _ in rk if n.startswith("Motor")))
    out.append(("Rakete Erstflug auf dem Pad, Kardan 0° und ±7°/±7°, gegen alle Padteile", bad))
    gap = nozzle_min - BLAST_TOP_Z
    out.append((f"Düse über der Strahlplatte: min. {gap:.1f} mm (Kardan ±7°), gefordert ≥ 80", [] if gap >= 80 else ["zu tief"]))
    # 2 Kardan-Freiraum: Zylinder r = 30 von der Strahlplatte bis zur Rohrunterkante; das Anzünderkabel ist biegsam und ausgenommen
    free = cyl(2 * GIMBAL_FREE_R, BLAST_TOP_Z + 0.01, P.TUBE_BOTTOM_Z).val()
    bad = [f"{n}: {_vol(free, s):.0f} mm³" for n, s in by.items() if not n.startswith("Anzünderkabel") and _vol(free, s) > 0.01]
    out.append((f"Kardan-Freiraum r < {GIMBAL_FREE_R:.0f} unter der Rohrunterkante leer (ohne Anzünderkabel)", bad))
    # 3 Auflagen: Oberkante = Rohrunterkante, tragen die Ringfläche; Führungen: Luft und Höhe
    bad = []
    tube_low = [s for n, s, _, _ in rocket0 if n.startswith("Rohr unten")][0]
    for phi in STAND_PHI:
        rest = by[f"Stütze {phi:.0f}° Auflage"]
        bb = rest.BoundingBox()
        if abs(bb.zmax - P.TUBE_BOTTOM_Z) > 0.01:
            bad.append(f"Auflage {phi:.0f}°: Oberkante {bb.zmax:.2f} statt {P.TUBE_BOTTOM_Z}")
        if not (REST_R[0] <= P.TUBE_ID / 2 and REST_R[1] >= P.TUBE_OD / 2):
            bad.append(f"Auflage {phi:.0f}° deckt die Ringfläche nicht")
        guide = by[f"Stütze {phi:.0f}° Führung Alu 20x20"]
        d = tube_low.distance(guide)
        h = guide.BoundingBox().zmax - P.TUBE_BOTTOM_Z
        if not (1.0 <= d <= 2.0):
            bad.append(f"Führung {phi:.0f}°: Luft {d:.2f} mm")
        if h < 150:
            bad.append(f"Führung {phi:.0f}°: nur {h:.0f} mm hoch")
    out.append((f"Auflagen auf z = {P.TUBE_BOTTOM_Z:.0f} unter r = {P.TUBE_ID / 2:.1f} … {P.TUBE_OD / 2:.1f}, "
                f"Führungen {GUIDE_H:.0f} mm hoch, Luft {tube_low.distance(by['Stütze 60° Führung Alu 20x20']):.2f} mm", bad))
    # 4 Abheben: die Rakete steigt durch die Führungen, nichts darf hängen bleiben (Schlüsselschalter +x, Luken ±y)
    bad = []
    guides = [p for p in pad if p[0].startswith("Stütze")]
    for dz in (1.0, 40.0, 80.0, 120.0, 160.0, 200.0):
        bad += [f"dz {dz:.0f}: {x}" for x in collisions(_shift(rocket0, dz=dz), guides)]
    out.append(("Abheben bis 200 mm durch die Führungen frei", bad))
    # 5 Landung (voll, Beine ausgefahren) ohne Stützen: Füße auf dem Deck, nichts steht über die Fläche
    use_config("voll")
    rv = build.build_all(legs_deployed=True)
    sole = min(s.BoundingBox().zmin for n, s, _, _ in rv if n.endswith("Fuß"))
    land, _ = build_pad(start=False)
    bad = []
    for dx, dy in ((0, 0), (150, 0), (0, -150), (-150, 150)):
        rk = _shift(rv, dx, dy, DECK_Z - sole)
        bad += [f"Versatz {dx}/{dy}: {x}" for x in collisions(rk, land)]
    above = [f"{n}: z {s.BoundingBox().zmax:.2f}" for n, s, _, _ in land if s.BoundingBox().zmax > DECK_Z + 1e-6]
    r_foot = max(math.hypot(x, y) for n, s, _, _ in rv if n.endswith("Fuß")
                 for x, y in ((s.BoundingBox().xmax, s.BoundingBox().ymax), (s.BoundingBox().xmin, s.BoundingBox().ymin),
                              (s.BoundingBox().xmax, s.BoundingBox().ymin), (s.BoundingBox().xmin, s.BoundingBox().ymax)))
    nozzle_land = DECK_Z - sole
    out.append((f"Landung voll, Fußsohle auf dem Deck (Düse {PAD_NOZZLE_H + nozzle_land:.0f} mm darüber), "
                f"Versatz bis 150 mm, gegen Deck/Strahlplatte/Libelle", bad))
    out.append(("Landefläche: nichts über dem Deckblech", above))
    margin = DECK_AF / 2 - r_foot
    out.append((f"Füße bis r = {r_foot:.0f}, Inkreis des Decks {DECK_AF / 2:.0f}: {margin:.0f} mm Landeversatz möglich "
                f"(Ø 1200: {600 - r_foot:.0f} mm)", [] if margin > 0 else ["Füße außerhalb"]))
    use_config("erstflug")
    return out, rocket0


# --------------------------------------------------------------------------- Export und Bilder
def manifest(parts, name, keep=None, remove=None):
    """Wie build.write_render_manifest, aber mit keep (nur dieser Quader bleibt) und remove (dieser Quader fällt weg)."""
    d = build.EXPORT / "render" / name
    d.mkdir(parents=True, exist_ok=True)
    for f in d.glob("*.stl"):
        f.unlink()
    items = []
    for i, (pname, shape, col, group) in enumerate(parts):
        shp = cq.Workplane().add(shape)
        try:
            if keep:
                shp = shp.intersect(box_from(*keep))
                if not shp.vals() or shp.val().Volume() < 1e-3:
                    continue
                shp = cq.Workplane().add(shp.val())   # sonst greift cut() bei leerer Schnittmenge auf das Ausgangsteil zurück
            if remove:
                shp = shp.cut(box_from(*remove))
            if not shp.vals() or shp.val().Volume() < 1e-3:
                continue
            f = d / f"{i:03d}.stl"
            exporters.export(shp, str(f), tolerance=0.1, angularTolerance=0.2)
        except Exception as e:
            print(f"  ! {pname}: {e}")
            continue
        items.append({"file": f.name, "name": pname, "color": P.COLORS[col], "group": group})
    (d / "manifest.json").write_text(json.dumps(items, indent=1, ensure_ascii=False), encoding="utf-8")
    return d


def main():
    t0 = time.time()
    no_render = "--no-render" in sys.argv
    pad, mats = build_pad(start=True)
    print(f"Pad: {len(pad)} Teile, Deck Achteck {DECK_AF:.0f} mm, Deckblech z = {DECK_Z:.0f}, Boden z = {GROUND_Z:.1f}")
    # Massen
    total = 0.0
    groups = {}
    for n, s, _, g in pad:
        m = part_mass(n, s, mats[n])
        key = ("Deck je Hälfte (Sperrholz + Blech)" if n.startswith(("Deckhälfte", "Deckblech")) else
               "Latten, Fußklötze, Stellfüße" if n.startswith(("Latte", "Fußklotz", "Stellfuß")) else
               "Strahlplatten-Einsatz" if n.startswith(("Strahlplatte", "Träger")) else
               "Stützen ohne Zündkasten" if n.startswith("Stütze") else
               "Zündkasten mit Steckern und Schild" if g == "padstart" else "Libelle")
        groups[key] = groups.get(key, 0.0) + m
        total += m
    print("Massen (aus dem Volumen, Dichten [Annahme]):")
    for k, m in groups.items():
        print(f"  {k:40s} {m / 1000 / (2 if k.startswith('Deck je') else 1):6.2f} kg")
    print(f"  {'gesamt':40s} {total / 1000:6.2f} kg")
    cost = sum(q * p for _, q, p in BOM)
    print(f"Kaufteile grob: {cost:.0f} €")
    print("Prüfungen ...")
    results, rocket = check_all()
    ok = True
    for label, bad in results:
        print(f"  {label}: " + ("frei" if not bad else "FEHLER"))
        for x in bad:
            print("    " + x)
        ok &= not bad
    # STEP: Pad in Startkonfiguration mit der Erstflug-Rakete (wie testrig.step)
    build.EXPORT.mkdir(parents=True, exist_ok=True)
    step = build.EXPORT / "landingpad.step"
    build.assembly(Parts(list(pad) + list(rocket))).export(str(step))
    print(f"  {step.relative_to(HERE.parent)} (Pad mit Rakete Erstflug)")
    if not no_render:
        build.IMG.mkdir(parents=True, exist_ok=True)
        print("Render ...")
        both = list(pad) + list(rocket)
        d = manifest(both, "pad")
        build.render(d, build.IMG / "landingpad.png", "pad")
        d = manifest(both, "pad_detail", keep=(-420, 420, -420, 420, GROUND_Z - 1, 260))
        build.render(d, build.IMG / "landingpad_detail.png", "pad_detail")
        d = manifest(both, "pad_section", keep=(-420, 420, -420, 420, GROUND_Z - 1, 260), remove=(-500, 500, -500, 0, -500, 500))
        build.render(d, build.IMG / "landingpad_section.png", "pad_section")
        use_config("voll")
        rv = build.build_all(legs_deployed=True)
        sole = min(s.BoundingBox().zmin for n, s, _, _ in rv if n.endswith("Fuß"))
        land, _ = build_pad(start=False)
        d = manifest(list(land) + _shift(rv, dz=DECK_Z - sole), "pad_landing")
        build.render(d, build.IMG / "landingpad_landing.png", "pad_landing")
        use_config("erstflug")
    print(f"{'alles frei' if ok else 'PRÜFUNG FEHLGESCHLAGEN'}, fertig in {time.time() - t0:.0f} s")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
