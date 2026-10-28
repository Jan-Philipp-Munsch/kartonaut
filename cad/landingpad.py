"""Startrampe für die gebaute Rakete (Modulbauweise Kartonaut 1, Stand 2d; Rampe vom 22.10.2026, umgestellt am 27.10.2026).
Anforderungen: docs/Schnittstellen_Bodensystem_2026-10-22.md, S1; Zündung an Bord nach docs/Plan_Bordzuendung_2026-10-27.md.
Abweichungen stehen in cad/README.md.

    python cad/landingpad.py              Rampe bauen, prüfen, export/landingpad.step, Bilder docs/img/cad/landingpad*.png
    python cad/landingpad.py --no-render  ohne Blender

Aufbau (Maße unten, jede Zahl mit Quelle wie in params.py):
  Platte:      Siebdruckplatte 600 × 600 × 18 (Baumarkt-Zuschnitt) mit Loch Ø 130 in der Mitte; der Strahl geht durch das
               Loch in die Erde. Um das Loch ein Stahlblech 250 × 250 × 1 als Brandschutz. Dosenlibelle eingelassen.
  Beine:       drei Gewindestangen M10 × 330 in Einschlagmuttern, je mit Kontermutter, unten Karosseriescheibe Ø 30 zwischen
               zwei Muttern (auf weichem Boden ohne Scheibe 3 cm eingesteckt). Jedes Bein einzeln verstellbar: Platte 80 … 270 mm
               über dem Boden, damit lässt sich die Rampe auf geneigtem oder unebenem Boden waagerecht stellen.
  Startstützen: drei Stützen bei 45°, 135°, 250° (Rakete: Radialschrauben bei 0/90/180/270°, Servofenster bei 207°/336°,
               Luken bei 90°/270° über der Führung): Alu-Vierkantrohr 20 × 20 × 1,5 als Führung (2 mm Luft zum Rohr, mehr
               als die 1,65 mm hohen Linsenköpfe der M3-Schrauben, 160 mm über der Rohrunterkante), Auflage-Klotz unter der
               Rohrunterkante, Schrägstrebe aus demselben Rohr zur Fußplatte (Alu 40 × 5, zwei M6 in Langlöchern) und ein
               Knotenblech. Die Führung endet 10 mm unter der Rohrunterkante; im Strahl steht nichts.
  Zündung:     an Bord über Pyro 1 (Plan Bordzündung, Jan 27.10.2026). Kein Zündkasten, keine Zündleitung, kein Shunt an
               der Rampe; die Anzünderleitung kommt von innen aus der Düse und hängt nach dem Start lose.
Koordinaten wie die Rakete der Modulbauweise: z = 0 Düsenebene = Rohrunterkante (der Motor steht bündig); Winkel ab der
Längslinie 0° (Kardanschraube), wie in modular_params.py. Die Oberkante des Stahlblechs liegt bei z = DECK_Z.
Die spätere Landung (Konfiguration voll, Füße auf r ≈ 320) braucht eine eigene Fläche, die hier nicht enthalten ist.
"""
import json, math, os, sys, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
os.environ.setdefault("MS_CONFIG", "erstflug")
import cadquery as cq
from cadquery import exporters
import params as P
import build
import modular as MD
import modular_params as M
from common import Parts, tube, cyl, cyl_between, box_from, rot_z

# --------------------------------------------------------------------------- Maße
TUBE_BOTTOM_Z = M.TUBE_A[0]   # Modulbauweise: Rohrunterkante = Düsenebene = 0 (Motor bündig)
PIVOT_Z = M.GIMBAL_BASE_Z + P.PIVOT_H   # Kardanpunkt der gebauten Druckdatei, 69,5 mm
PAD_NOZZLE_H = 100.0      # [Annahme] Düse über dem Stahlblech; S1 fordert ≥ 80
DECK_Z = -PAD_NOZZLE_H    # Oberkante Stahlblech
SHEET = (250.0, 1.0)      # [Annahme] Stahlblech 250 × 250 × 1 (Baumarkt-Tafel 250 × 500 halbiert), um das Loch
PLATE = (600.0, 18.0)     # [Annahme] Siebdruckplatte 600 × 600 × 18, Baumarkt-Zuschnitt
PLATE_Z = (DECK_Z - SHEET[1] - PLATE[1], DECK_Z - SHEET[1])
HOLE_D = 130.0            # [Annahme] Loch für den Strahl; Strahlkegel bei Kardan 7° an der Platte r ≤ 46
JET_HALF_DEG = 15.0       # [Annahme] halber Öffnungswinkel des Strahls; dazu GIMBAL_MAX_DEG
JET_EXIT_R = 5.0          # [Annahme] Düsenaustritt E12 etwa Ø 10
LEG_R = 265.0             # [Annahme] Beine auf r = 265 bei 90°, 210°, 330° (drei Punkte, kippelt nicht)
LEG_PHI = (90.0, 210.0, 330.0)
LEG_ROD = (10.0, 330.0)   # [Annahme] Gewindestange M10, 1 m in drei Stücke à 330
LEG_TOP = 20.0            # Überstand über der Platte: Kontermutter + Mutter zum Drehen
LEG_FOOT = (30.0, 1.5, 8.0)   # [Annahme] Karosseriescheibe M10 × 30 × 1,5 zwischen zwei Muttern (8 hoch)
LEG_CLEAR = (80.0, LEG_ROD[1] - LEG_TOP - PLATE[1] - SHEET[1] - 2 * LEG_FOOT[2] - LEG_FOOT[1])   # Platte über Boden min/max (271)
GROUND_CLEAR = 170.0      # [Annahme] Darstellung: Plattenunterkante 170 mm über dem Boden in der Mitte
GROUND_SLOPE_DEG = 6.0    # [Annahme] Darstellung: Boden um 6° geneigt (steigt nach +x)
WIND_N, WIND_Z = 5.0, 550.0   # [Annahme] Wind 10 m/s auf die Rakete: 0,5 × 1,2 × 10² × 0,95 × 0,075 ≈ 4,3 N, Angriff 550 über der Platte

STAND_PHI = (45.0, 135.0, 250.0)   # Modulbauweise (Befund 17): zwischen den Radialschrauben 0/90/180/270° und den Servofenstern 207°/336°
GUIDE_GAP = 2.0           # [Vorgabe S1] 1 … 2 mm Luft; 2 mm, damit die Linsenköpfe M3 (ISO 7380, 1,65 hoch) bei jeder Rolllage durchgehen
SCREW_HEAD = (5.7, 1.65)  # [ISO 7380] M3-Linsenkopf: Ø, Höhe über dem Rohr
GUIDE_PROFILE = (20.0, 1.5)   # [Annahme] Alu-Vierkantrohr 20 × 20 × 1,5
GUIDE_H = 160.0           # [Vorgabe S1] ≥ 150 mm Führung über der Rohrunterkante
GUIDE_R0 = P.TUBE_OD / 2 + GUIDE_GAP          # Innenfläche der Führung (39,0)
REST_R = (34.0, GUIDE_R0)  # Auflage unter der Ringfläche r = 36,3 … 37,5; innen 4 mm außerhalb des Kardan-Freiraums
REST_H = 10.0             # [Annahme] Auflage-Klotz Alu 20 × 5 × 10 unter der Rohrunterkante
POST_Z0 = TUBE_BOTTOM_Z - REST_H   # Führung endet unten auf Höhe der Auflage (z = 10), über der Düse
GIMBAL_FREE_R = 30.0      # [Vorgabe S1] unter der Rohrunterkante kein Teil innerhalb r = 30
STAND_FOOT = (40.0, 5.0)  # [Annahme] Alu-Flachstange 40 × 5
STAND_FOOT_R = (150.0, 250.0)   # radial; beginnt außerhalb des Stahlblechs (bei 60° endet es auf r = 144)
STAND_BOLTS_R = (170.0, 232.0)  # M6 in Einschlagmuttern, Langloch 6,5 × 16
STRUT_TOP = (GUIDE_R0 + 20.0, POST_Z0 + 10.0)   # Strebe: von der Außenseite der Führung unten …
STRUT_FOOT_R = 180.0      # … zur Fußplatte
GUSSET_T = 3.0            # [Annahme] Knotenblech Alu 3 mm, beidseitig
LEVEL_POS = (200.0, 0.0)  # Dosenlibelle bei 0°, r = 200
LEVEL_D, LEVEL_H = 40.0, 12.0  # [Annahme] Dosenlibelle mit Gehäuse

# Dichten in g/mm³ für die Massen aus dem Volumen; [Annahme] Richtwerte
RHO = {"ply": 0.68e-3, "steel": 7.85e-3, "alu": 2.70e-3}
# Teile mit fester Masse (hohl, gekauft): g [Annahme]
FIXED_M = {"Dosenlibelle": 20.0}

P.COLORS.update({"deck": (0.70, 0.72, 0.74), "ply": (0.55, 0.38, 0.22), "ground": (0.45, 0.55, 0.30),
                 "box": (0.85, 0.85, 0.82), "red": (0.85, 0.12, 0.10), "xt30": (0.95, 0.75, 0.10),
                 "black": (0.08, 0.08, 0.08), "level": (0.35, 0.80, 0.45)})

# Stückliste, Preise grob (B1/OBI, Oktober 2026) [Annahme]; XT30 gibt es nur im Modellbau-Handel
BOM = [
    ("Siebdruckplatte 18 mm, Zuschnitt 600 × 600 (Loch Ø 130 mit Lochsäge/Stichsäge)", 1, 13.0),
    ("Stahlblech 1 mm, 250 × 250 (Brandschutz um das Loch; Baumarkt-Tafel 250 × 500 halbiert)", 1, 9.0),
    ("Gewindestange M10, 1 m verzinkt (drei Beine à 330)", 1, 3.0),
    ("Einschlagmuttern M10 (3) und M6 (6), Muttern M10 (9), Karosseriescheiben M10 × 30 (3)", 1, 7.0),
    ("Alu-Vierkantrohr 20 × 20 × 1,5, 2 × 1 m (Führungen 170, Streben 200)", 2, 8.0),
    ("Alu-Flachstange 40 × 5, 1 m (Fußplatten, Auflagen); Alu-Flach 3 mm Rest (Knotenbleche)", 1, 10.0),
    ("Schrauben M6 × 20 mit Unterlegscheiben (6), M5 × 30 mit Mutter (9)", 1, 5.0),
    ("Dosenlibelle Ø 40", 1, 4.0),
    ("Druckteil PETG: Einstellring Ø 79 als Lehre (Rohr + 2 × 2 mm Luft), ca. 20 g", 1, 1.0),
]


def use_config(cfg):
    """Schaltet params zur Laufzeit auf eine Konfiguration (die Module lesen P.* erst beim Bauen)."""
    P.__dict__.update(P.layout(cfg))


def square_bar(p0, p1, w, t):
    """Vierkantrohr w × w × t von p0 nach p1 in der x-z-Ebene (lokal, y = 0)."""
    dx, dz = p1[0] - p0[0], p1[2] - p0[2]
    L = math.hypot(dx, dz)
    b = box_from(0, L, -w / 2, w / 2, -w / 2, w / 2).cut(box_from(-1, L + 1, -w / 2 + t, w / 2 - t, -w / 2 + t, w / 2 - t))
    return b.rotate((0, 0, 0), (0, 1, 0), math.degrees(math.atan2(-dz, dx))).translate(p0)


def ground_z(x, y):
    return PLATE_Z[0] - GROUND_CLEAR + x * math.tan(math.radians(GROUND_SLOPE_DEG))


# --------------------------------------------------------------------------- Platte und Beine
def plate():
    out = []
    a = PLATE[0] / 2
    ply = box_from(-a, a, -a, a, *PLATE_Z).cut(cyl(HOLE_D, PLATE_Z[0] - 1, PLATE_Z[1] + 1))
    ply = ply.cut(cyl(LEVEL_D + 1, PLATE_Z[1] - LEVEL_H, PLATE_Z[1] + 1, *LEVEL_POS))
    for phi in LEG_PHI:
        x, y = LEG_R * math.cos(math.radians(phi)), LEG_R * math.sin(math.radians(phi))
        ply = ply.cut(cyl(LEG_ROD[0] + 2, PLATE_Z[0] - 1, PLATE_Z[1] + 1, x, y))
    out.append(("Platte Siebdruck 600x600x18", ply, "ply", "ply"))
    s = SHEET[0] / 2
    sh = box_from(-s, s, -s, s, PLATE_Z[1], DECK_Z).cut(cyl(HOLE_D, PLATE_Z[1] - 1, DECK_Z + 1))
    out.append(("Stahlblech 250x250x1", sh, "deck", "steel"))
    out.append(("Dosenlibelle", cyl(LEVEL_D, PLATE_Z[1] - LEVEL_H, PLATE_Z[1] - 0.3, *LEVEL_POS), "level", None))
    for i, phi in enumerate(LEG_PHI):
        x, y = LEG_R * math.cos(math.radians(phi)), LEG_R * math.sin(math.radians(phi))
        zg = ground_z(x, y)
        d, ft, nh = LEG_FOOT
        rod = cyl(LEG_ROD[0], zg + ft, PLATE_Z[1] + SHEET[1] + LEG_TOP, x, y)
        nuts = (cyl(17.0, PLATE_Z[1], PLATE_Z[1] + 8, x, y).union(cyl(17.0, PLATE_Z[1] + 8, PLATE_Z[1] + 16, x, y))
                .union(cyl(17.0, zg + ft, zg + ft + nh, x, y)).union(cyl(17.0, zg + ft + nh, zg + ft + 2 * nh, x, y)))
        out.append((f"Bein {i + 1} Gewindestange M10", rod, "steel", "steel"))
        out.append((f"Bein {i + 1} Muttern und Scheibe", nuts.union(cyl(d, zg, zg + ft, x, y)), "steel", "steel"))
    return out


def ground():
    """Nur zur Darstellung: geneigter Boden unter der Rampe."""
    g = cyl(1000.0, -40.0, 0.0).rotate((0, 0, 0), (0, 1, 0), -GROUND_SLOPE_DEG).translate((0, 0, ground_z(0, 0)))
    return [("Boden (Darstellung)", g, "ground", None)]


# --------------------------------------------------------------------------- Startstützen (abnehmbar)
def stand(phi):
    """Eine Stütze im lokalen System (x radial nach außen), dann um z gedreht."""
    z0 = PLATE_Z[1]
    zf = z0 + STAND_FOOT[1]
    w, t = GUIDE_PROFILE
    foot = box_from(STAND_FOOT_R[0], STAND_FOOT_R[1], -STAND_FOOT[0] / 2, STAND_FOOT[0] / 2, z0, zf)
    for r in STAND_BOLTS_R:   # Langloch 6,5 × 16 radial
        foot = foot.cut(cq.Workplane("XY").workplane(offset=z0 - 1).center(r, 0).slot2D(16.0, 6.5, 0).extrude(STAND_FOOT[1] + 2))
    z_top = TUBE_BOTTOM_Z + GUIDE_H
    r0 = GUIDE_R0
    post = box_from(r0, r0 + w, -w / 2, w / 2, POST_Z0, z_top).cut(box_from(r0 + t, r0 + w - t, -w / 2 + t, w / 2 - t, POST_Z0 - 1, z_top + 1))
    post = post.faces(">Z").edges("<X").chamfer(1.4)   # Einführschräge innen oben
    rest = box_from(REST_R[0], REST_R[1], -w / 2, w / 2, TUBE_BOTTOM_Z - REST_H, TUBE_BOTTOM_Z)
    p0 = (STRUT_TOP[0] + w / 2 - 4, 0, STRUT_TOP[1])
    p1 = (STRUT_FOOT_R, 0, zf + w / 2 - 3)
    strut = square_bar(p0, p1, w, t)
    # Knotenbleche beidseitig: Führung (unten) – Strebe – Fußplatte
    pts = [(r0, POST_Z0), (r0 + w, POST_Z0 + 70), (STRUT_FOOT_R + 30, zf), (STRUT_FOOT_R - 25, zf)]
    gus = None
    for sy in (-1, 1):
        g = (cq.Workplane("XZ").polyline(pts).close().extrude(GUSSET_T / 2, both=True)
             .translate((0, sy * (w / 2 + GUSSET_T / 2), 0)))
        gus = g if gus is None else gus.union(g)
    tag = f"{phi:.0f}°"
    out = [(f"Stütze {tag} Fußplatte Alu 40x5", foot, "alu", "alu"),
           (f"Stütze {tag} Führung Alu 20x20", post, "alu", "alu"),
           (f"Stütze {tag} Auflage", rest, "printed", "alu"),
           (f"Stütze {tag} Strebe Alu 20x20", strut, "alu", "alu"),
           (f"Stütze {tag} Knotenbleche Alu 3", gus, "alu", "alu")]
    return [(n, rot_z(s, phi), c, m) for n, s, c, m in out]


def build_pad(with_ground=False):
    """Liste (name, shape, color, group) und Materialtabelle {name: Werkstoff oder None}."""
    parts = Parts()
    mats = {}
    items = plate() + [x for phi in STAND_PHI for x in stand(phi)] + (ground() if with_ground else [])
    for n, s, c, m in items:
        parts.add(n, s, c, "pad")
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


def screw_heads():
    """Linsenköpfe der Radialschrauben am Rohr (in modular.py nur als Löcher): Kardan z 44 und Stoß J1 z 110 liegen in
    der Führungshöhe, T2/T3 darüber."""
    d, h = SCREW_HEAD
    r0 = P.TUBE_OD / 2
    out = []
    for z in (M.GIMBAL_SCREW_Z, M.J1_SCREW_Z, M.SPIGOT_B_SCREW_Z):
        for phi in M.SCREW_PHI:
            a = math.radians(phi)
            out.append((f"Schraubenkopf M3 {phi:.0f}° z {z:.0f}",
                        cyl_between(d, (r0 * math.cos(a) - 0.3 * math.cos(a), r0 * math.sin(a) - 0.3 * math.sin(a), z),
                                    ((r0 + h) * math.cos(a), (r0 + h) * math.sin(a), z)).val(), "steel", "rumpf"))
    for phi in M.SPIGOT_C_PHI:
        a = math.radians(phi)
        z = M.SPIGOT_C_SCREW_Z
        out.append((f"Schraubenkopf M3 {phi:.0f}° z {z:.0f}",
                    cyl_between(d, ((r0 - 0.3) * math.cos(a), (r0 - 0.3) * math.sin(a), z),
                                ((r0 + h) * math.cos(a), (r0 + h) * math.sin(a), z)).val(), "steel", "rumpf"))
    return out


def rocket_modular(pitch=0.0, yaw=0.0, base=None):
    """Gebaute Rakete aus modular.build_all() mit Schraubenköpfen; der Motor kippt um den Kardanpunkt (Nicken um x,
    Gieren um y). Der Kardan selbst ist dort nur ein Hüllkörper im Rohr A und kommt der Rampe nicht nahe."""
    base = base if base is not None else [(n, (s.val() if hasattr(s, "val") else s), c, g) for n, s, c, g in MD.build_all()] + screw_heads()
    if pitch == 0 and yaw == 0:
        return base
    out = []
    for n, s, c, g in base:
        if n.startswith("Motor"):
            s = s.rotate(cq.Vector(0, 0, PIVOT_Z), cq.Vector(1, 0, PIVOT_Z), pitch)
            s = s.rotate(cq.Vector(0, 0, PIVOT_Z), cq.Vector(0, 1, PIVOT_Z), yaw)
        out.append((n, s, c, g))
    return out


def leg_points():
    return [(LEG_R * math.cos(math.radians(p)), LEG_R * math.sin(math.radians(p))) for p in LEG_PHI]


def check_all(pad_mass):
    """Alle Prüfungen; liefert [(Text, [Befunde])], leer = frei."""
    out = []
    g = P.GIMBAL_MAX_DEG
    pad, _ = build_pad()
    by = {n: s for n, s, _, _ in pad}
    rocket0 = rocket_modular()
    # 1 Rakete (Modulbauweise, mit Schraubenköpfen) mit Kardan 0° und ±7° in beiden Achsen gegen alle Teile der Rampe
    bad = []
    nozzle_min = 1e9
    for pitch, yaw in ((0, 0), (g, g), (g, -g), (-g, g), (-g, -g)):
        rk = rocket_modular(pitch, yaw, base=rocket0)
        bad += [f"Kardan {pitch:+.0f}/{yaw:+.0f}: {x}" for x in collisions(rk, pad)]
        nozzle_min = min(nozzle_min, min(s.BoundingBox().zmin for n, s, _, _ in rk if n.startswith("Motor")))
    out.append(("Rakete (Modulbauweise) auf der Rampe, Kardan 0° und ±7°/±7°, gegen alle Teile", bad))
    gap = nozzle_min - DECK_Z
    out.append((f"Düse über dem Stahlblech: min. {gap:.1f} mm (Kardan ±7°), gefordert ≥ 80", [] if gap >= 80 else ["zu tief"]))
    # 2 Strahlkegel (halber Winkel JET_HALF_DEG + Kardan) von der Düse bis 400 mm darunter: nur das Loch, kein Teil
    L = 400.0
    ang = math.radians(JET_HALF_DEG + g)
    jet = cq.Solid.makeCone(JET_EXIT_R, JET_EXIT_R + L * math.tan(ang), L, cq.Vector(0, 0, 0), cq.Vector(0, 0, -1))
    r_plate = JET_EXIT_R + (-PLATE_Z[0]) * math.tan(ang)
    bad = [f"{n}: {_vol(jet, s):.0f} mm³" for n, s in by.items() if _vol(jet, s) > 0.01]
    out.append((f"Strahlkegel ±{JET_HALF_DEG + g:.0f}° frei bis {L:.0f} mm unter der Düse (r an der Plattenunterkante "
                f"{r_plate:.0f}, Loch r {HOLE_D / 2:.0f})", bad))
    # 3 Kardan-Freiraum: Zylinder r = 30 von 400 mm unter der Düse bis zur Rohrunterkante
    free = cyl(2 * GIMBAL_FREE_R, -L, TUBE_BOTTOM_Z).val()
    bad = [f"{n}: {_vol(free, s):.0f} mm³" for n, s in by.items() if _vol(free, s) > 0.01]
    out.append((f"Kardan-Freiraum r < {GIMBAL_FREE_R:.0f} unter der Rohrunterkante leer", bad))
    # 4 Auflagen: Oberkante = Rohrunterkante, tragen die Ringfläche; Führungen: Luft und Höhe
    bad = []
    tube_low = [s for n, s, _, _ in rocket0 if n.startswith("Rohr A")][0]
    for phi in STAND_PHI:
        bb = by[f"Stütze {phi:.0f}° Auflage"].BoundingBox()
        if abs(bb.zmax - TUBE_BOTTOM_Z) > 0.01:
            bad.append(f"Auflage {phi:.0f}°: Oberkante {bb.zmax:.2f} statt {TUBE_BOTTOM_Z}")
        if not (REST_R[0] <= P.TUBE_ID / 2 and REST_R[1] >= P.TUBE_OD / 2):
            bad.append(f"Auflage {phi:.0f}° deckt die Ringfläche nicht")
        guide = by[f"Stütze {phi:.0f}° Führung Alu 20x20"]
        d = tube_low.distance(guide)
        h = guide.BoundingBox().zmax - TUBE_BOTTOM_Z
        if not (1.0 <= d <= 2.05):
            bad.append(f"Führung {phi:.0f}°: Luft {d:.2f} mm")
        if h < 150:
            bad.append(f"Führung {phi:.0f}°: nur {h:.0f} mm hoch")
    out.append((f"Auflagen auf z = {TUBE_BOTTOM_Z:.0f} unter r = {P.TUBE_ID / 2:.1f} … {P.TUBE_OD / 2:.1f}, "
                f"Führungen {GUIDE_H:.0f} mm hoch, Luft {tube_low.distance(by[f'Stütze {STAND_PHI[0]:.0f}° Führung Alu 20x20']):.2f} mm", bad))
    # 4b Schraubenköpfe bei jeder Rolllage: Kopfoberkante unter der Führungsinnenfläche
    head_r = P.TUBE_OD / 2 + SCREW_HEAD[1]
    out.append((f"Linsenköpfe M3 bis r = {head_r:.2f}, Führung innen bei r = {GUIDE_R0:.2f}: gehen bei jeder Rolllage durch",
                [] if head_r < GUIDE_R0 - 0.2 else [f"nur {GUIDE_R0 - head_r:.2f} mm"]))
    # 5 Abheben: die Rakete steigt durch die Führungen, nichts darf hängen bleiben (Schraubenköpfe, Luken, Servofenster)
    bad = []
    stands = [p for p in pad if p[0].startswith("Stütze")]
    for dz in (1.0, 40.0, 80.0, 120.0, 160.0, 200.0):
        bad += [f"dz {dz:.0f}: {x}" for x in collisions(_shift(rocket0, dz=dz), stands)]
    out.append(("Abheben bis 200 mm durch die Führungen frei", bad))
    # 6 Ausrichten: Verstellbereich der Beine und größte ausgleichbare Neigung
    pts = leg_points()
    clear = [PLATE_Z[0] - ground_z(x, y) for x, y in pts]
    bad = [f"Bein {i + 1}: {c:.0f} mm außerhalb {LEG_CLEAR[0]:.0f} … {LEG_CLEAR[1]:.0f}" for i, c in enumerate(clear)
           if not LEG_CLEAR[0] <= c <= LEG_CLEAR[1]]
    span = max(max(x * math.cos(a) + y * math.sin(a) for x, y in pts) - min(x * math.cos(a) + y * math.sin(a) for x, y in pts)
               for a in [math.radians(k) for k in range(0, 360, 5)])
    slope_max = math.degrees(math.atan((LEG_CLEAR[1] - LEG_CLEAR[0]) / span))
    out.append((f"Beine bei {GROUND_SLOPE_DEG:.0f}° Bodenneigung {min(clear):.0f} … {max(clear):.0f} mm (Bereich "
                f"{LEG_CLEAR[0]:.0f} … {LEG_CLEAR[1]:.0f}); ausgleichbar bis {slope_max:.0f}° in jeder Richtung", bad))
    # 7 Kippen im Wind: Rückstellmoment (Rampe + Rakete über der Kippkante) gegen Windmoment auf die Rakete
    edge = LEG_R * math.sin(math.radians(30))   # Abstand der Mitte zur Kante des Beindreiecks
    m_rocket = json.loads((HERE / "mass_stand2b.json").read_text(encoding="utf-8"))["configurations"]["liftoff"]["mass_kg"] * 1000   # [cad] 705 g
    h_wind = WIND_Z + (TUBE_BOTTOM_Z - DECK_Z) + (PLATE_Z[0] - min(ground_z(x, y) for x, y in pts))
    ratio = (pad_mass + m_rocket) * 9.81e-3 * edge / (WIND_N * h_wind)
    out.append((f"Kippsicherheit im Wind {WIND_N:.0f} N in {h_wind:.0f} mm Höhe: Faktor {ratio:.1f} (Kante {edge:.0f} mm)",
                [] if ratio >= 1.5 else ["unter 1,5: Heringe setzen"]))
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
    pad, mats = build_pad()
    print(f"Startrampe: {len(pad)} Teile, Platte {PLATE[0]:.0f} × {PLATE[0]:.0f}, Stahlblech z = {DECK_Z:.0f}, Loch Ø {HOLE_D:.0f}")
    total = 0.0
    groups = {}
    for n, s, _, g in pad:
        m = part_mass(n, s, mats[n])
        key = ("Platte mit Stahlblech und Libelle" if n.startswith(("Platte", "Stahlblech", "Dosenlibelle")) else
               "drei Beine" if n.startswith("Bein") else "drei Stützen")
        groups[key] = groups.get(key, 0.0) + m
        total += m
    print("Massen (aus dem Volumen, Dichten [Annahme]):")
    for k, m in groups.items():
        print(f"  {k:36s} {m / 1000:5.2f} kg")
    print(f"  {'gesamt':36s} {total / 1000:5.2f} kg")
    print(f"Kaufteile grob: {sum(q * p for _, q, p in BOM):.0f} €")
    print("Prüfungen ...")
    results, rocket = check_all(total)
    ok = True
    for label, bad in results:
        print(f"  {label}: " + ("frei" if not bad else "FEHLER"))
        for x in bad:
            print("    " + x)
        ok &= not bad
    # STEP: Rampe mit der gebauten Rakete (Modulbauweise), ohne Boden
    step = HERE / "export" / "landingpad.step"
    build.assembly(Parts(list(pad) + list(rocket))).export(str(step))
    print(f"  {step.relative_to(HERE.parent)} (Rampe mit Rakete, Modulbauweise)")
    if not no_render:
        build.IMG.mkdir(parents=True, exist_ok=True)
        print("Render ...")
        both = list(build_pad(with_ground=True)[0]) + list(rocket)
        d = manifest(both, "pad")
        build.render(d, build.IMG / "landingpad.png", "pad")
        d = manifest(both, "pad_detail", keep=(-330, 330, -330, 330, -500, 260))
        build.render(d, build.IMG / "landingpad_detail.png", "pad_detail")
        d = manifest(both, "pad_section", keep=(-330, 330, -330, 330, -500, 260), remove=(-500, 500, -500, 0, -600, 500))
        build.render(d, build.IMG / "landingpad_section.png", "pad_section")
    print(f"{'alles frei' if ok else 'PRÜFUNG FEHLGESCHLAGEN'}, fertig in {time.time() - t0:.0f} s")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
