"""Schubdrossel als Schlitzscheibe (Konzept vom 16.11.2026, nicht gebaut). Löst den Entwurf throttle.py vom 15.11. ab.

    python cad/throttle_plate.py              bauen, prüfen, export/throttle_plate.step, Bilder docs/img/cad/throttle_plate*.png
    python cad/throttle_plate.py --no-render  ohne Blender (das Übersichtsbild entsteht trotzdem)

Anlass (Jan, 16.11.2026): Der Schub muss gleichmäßig abgeblockt werden, die Bauform soll Fehler verzeihen, der Abstand
zur Düse ist frei wählbar, und sie muss mit dem Motorwechsel im Magazin funktionieren (die leere Hülse fällt nach unten
heraus). Daraus:

  Scheibe:  EIN Blech (Edelstahl 1,5 mm) 15 mm unter der Düse, drehbar um eine Welle neben dem Motor. Darin ein Schlitz
            entlang eines Kreisbogens um die Welle: am einen Ende ein Loch Ø 27 (Strahl frei, und die Hülse Ø 24 fällt
            hindurch), von dort keilförmig schmaler bis 2 mm. Drehen der Scheibe schiebt eine andere Schlitzbreite unter
            die Düse. Beide Kanten des Schlitzes sind im selben Teil; Spiel im Gestänge ändert nur die Stärke.
  Abstand:  15 mm = 1,5 Düsendurchmesser, damit die Scheibe auf den freien Strahl wirkt und nicht in die Düse zurückstaut.
  Welle:    M3, läuft in einer 15,6 mm langen Messingbuchse im Träger (über der Düsenebene, im Rohr) und ragt nach unten
            zur Scheibe. Die Strahlkraft auf die Scheibe trägt die Welle (Biegung) und das Lager, nicht das Servo.
  Antrieb:  Kurbel (7 mm) oben auf der Welle, Stange, Servohebel (6 mm), Mikroservo am Motoradapter. Das ganze Gestänge
            liegt über der Düsenebene im Rohr, weg vom Abgas.
  Träger:   Klemmring auf dem Adapter (später auf dem Magazinrohr), alles schwenkt mit dem Kardan.

Koordinaten wie throttle.py: z = 0 Düsenebene = Rohrunterkante, +z zur Spitze; x, y sind die Achsen des Kardans, die Welle
steht bei (R | 0). Drehwinkel theta der Scheibe: 0 = Loch unter der Düse (offen, Auswurf), THETA_MAX = schmalstes Ende.
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
import throttle as T
from common import Parts, tube, cyl, cyl_between, box_from
from throttle import e, _bar, _vol, _tilt, max_radius, manifest, TUBE_R, PIVOT_Z, JET_R, JET_HALF_DEG, ADAPTER_OD, RHO

# --------------------------------------------------------------------------- Maße
GAP = 15.0                                   # [Jan 16.11.: frei wählbar] Abstand Düsenebene – Scheibe, 1,5 Düsendurchmesser
PLATE_T = 1.5                                # Edelstahlblech
PLATE_Z = (-GAP - PLATE_T, -GAP)
R = 24.0                                     # Welle bei (24 | 0); der Schlitz liegt auf dem Kreis mit Radius R um die Welle
THETA_MAX = 80.0                             # Drehwinkel vom Loch bis zum schmalen Ende
CASE_D = P.MOTOR_D                           # 24, leere Hülse beim Motorwechsel
HW0, HW1 = 13.5, 1.0                         # halbe Schlitzbreite am Loch (Ø 27) und am schmalen Ende (2 mm)
RIM, LAND = 5.0, 12.0                        # Rand um das Loch; Blech neben dem Schlitz (deckt den Strahl mit Zugabe)
JET_R_PLATE = JET_R + GAP * math.tan(math.radians(JET_HALF_DEG))   # 9,0 mm Strahlradius an der Scheibe [Annahme 15°]
SHAFT_D, BUSH = 3.0, dict(od=4.0, id=3.1, z=(2.0, 17.6))            # M3-Welle, Messingrohr 4 × 0,45
LUG = dict(x=(14.2, 27.5), w=8.0)
RING = dict(od=33.0, id=ADAPTER_OD + 0.2, z=(0.5, 10.0))
SERVO = dict(T.SERVO)                        # dasselbe Mikroservo wie in throttle.py (4,3 g, [Annahme])
SERVO_Z0 = 1.5                               # Unterkante Servokörper, Welle nach OBEN
SERVO_AZ, SERVO_SGN = 300.0, 1               # aus einer Suche über Lage und Hebelrichtungen (Übertragungswinkel ≥ 41°)
SERVO_R = ADAPTER_OD / 2 + 0.55 + SERVO["w"] / 2
CRANK_R, HORN_R = 7.0, 6.0
KAPPA_MID, PSI_MID = 180.0, 0.0              # Richtung von Kurbel und Servohebel in der Mitte des Wegs (theta = 40°)
LEVER_Z = (20.5, 21.7)                       # Ebene von Kurbel und Servohebel
LINK_Z = 22.7
ENVELOPE_R = 25.6
FIXED_M = {"Servohebel": 0.3, "Servo": SERVO["m"] + 1.5, "Welle": 3.6, "Buchse": 0.6, "Kurbel": 0.5, "Stange": 0.2,
           "Klemmschraube": 0.4}             # Welle: M3 × 45 (2,2 g) mit vier Muttern und zwei Scheiben

S = (R, 0.0)
_er, _et = e(SERVO_AZ), e(SERVO_AZ + 90.0)
SERVO_C = (SERVO_R * _er[0], SERVO_R * _er[1])
SERVO_AX = (SERVO_C[0] + SERVO_SGN * SERVO["shaft_off"] * _et[0], SERVO_C[1] + SERVO_SGN * SERVO["shaft_off"] * _et[1])


def crank_pin(theta):
    u = e(KAPPA_MID + THETA_MAX / 2 - theta)
    return S[0] + CRANK_R * u[0], S[1] + CRANK_R * u[1]


_k, _h = crank_pin(THETA_MAX / 2), (SERVO_AX[0] + HORN_R * e(PSI_MID)[0], SERVO_AX[1] + HORN_R * e(PSI_MID)[1])
LINK_L = math.hypot(_k[0] - _h[0], _k[1] - _h[1])


def servo_angle(theta):
    """Winkel des Servohebels (Grad um die Mitte) zum Drehwinkel der Scheibe; die Lösung wird von der Mitte aus verfolgt."""
    psi = PSI_MID
    n = max(1, int(abs(theta - THETA_MAX / 2) / 2.0))
    for i in range(1, n + 1):
        th = THETA_MAX / 2 + (theta - THETA_MAX / 2) * i / n
        kx, ky = crank_pin(th)
        dx, dy = kx - SERVO_AX[0], ky - SERVO_AX[1]
        d = math.hypot(dx, dy)
        c = max(-1.0, min(1.0, (d * d + HORN_R ** 2 - LINK_L ** 2) / (2 * d * HORN_R)))
        base, off = math.degrees(math.atan2(dy, dx)), math.degrees(math.acos(c))
        psi = min((base + off, base - off), key=lambda q: abs((q - psi + 180) % 360 - 180))
        psi = PSI_MID + (psi - PSI_MID + 180) % 360 - 180
    return psi


def half_width(a):
    return HW0 + (HW1 - HW0) * min(max(a, 0.0), THETA_MAX) / THETA_MAX


def in_slot(x, y, theta):
    """Liegt der Punkt (Raketenkoordinaten, Scheibenebene) im Schlitz, wenn die Scheibe um theta gedreht ist?"""
    px, py = x - S[0], y - S[1]
    rot = math.radians(-(180.0 - theta))
    qx, qy = px * math.cos(rot) - py * math.sin(rot), px * math.sin(rot) + py * math.cos(rot)
    rho, a = math.hypot(qx, qy), math.degrees(math.atan2(qy, qx))
    if 0.0 <= a <= THETA_MAX and abs(rho - R) <= half_width(a):
        return True
    ex, ey = R * e(THETA_MAX)[0], R * e(THETA_MAX)[1]
    return math.hypot(qx - R, qy) <= HW0 or math.hypot(qx - ex, qy - ey) <= HW1


def jet_stats(theta, core=False, n=41):
    """(abgedeckter Anteil des Strahlimpulses, Versatz des durchgelassenen Rests in mm) für Drehwinkel theta.
    core=False: Impuls gleichmäßig über den Strahlquerschnitt; core=True: zur Mitte konzentriert (Gauß, σ = halber Radius)."""
    rj = JET_R_PLATE
    tot = pas = mx = my = 0.0
    for i in range(n):
        for j in range(n):
            x, y = -rj + 2 * rj * (i + 0.5) / n, -rj + 2 * rj * (j + 0.5) / n
            r2 = x * x + y * y
            if r2 > rj * rj:
                continue
            w = math.exp(-r2 / (2 * (rj / 2) ** 2)) if core else 1.0
            tot += w
            if in_slot(x, y, theta):
                pas += w; mx += w * x; my += w * y
    return 1.0 - pas / tot, (math.hypot(mx, my) / pas if pas > 0 else 0.0)


# --------------------------------------------------------------------------- Teile
def plate_outline_pts(n=60):
    pts = [(0.0, 0.0)]
    for i in range(n + 1):
        a = (THETA_MAX + 14.0) * i / n
        rho = R + max(half_width(a) + RIM, LAND)
        pts.append((rho * e(a)[0], rho * e(a)[1]))
    return pts


def slot_pts(n=60):
    out = [((R + half_width(THETA_MAX * i / n)) * e(THETA_MAX * i / n)[0], (R + half_width(THETA_MAX * i / n)) * e(THETA_MAX * i / n)[1]) for i in range(n + 1)]
    inn = [((R - half_width(THETA_MAX * i / n)) * e(THETA_MAX * i / n)[0], (R - half_width(THETA_MAX * i / n)) * e(THETA_MAX * i / n)[1]) for i in range(n, -1, -1)]
    return out + inn


def plate_local():
    """Scheibe im eigenen Bezugssystem: Welle im Ursprung, Loch bei (R | 0), Schlitz gegen den Uhrzeigersinn."""
    z0, z1 = PLATE_Z
    h = z1 - z0
    s = cq.Workplane("XY").workplane(offset=z0).polyline(plate_outline_pts()).close().extrude(h)
    s = s.union(cyl(2 * (HW0 + RIM), z0, z1, R, 0)).union(cyl(16.0, z0, z1))
    slot = cq.Workplane("XY").workplane(offset=z0 - 1).polyline(slot_pts()).close().extrude(h + 2)
    ex, ey = R * e(THETA_MAX)[0], R * e(THETA_MAX)[1]
    slot = slot.union(cyl(2 * HW0, z0 - 1, z1 + 1, R, 0)).union(cyl(2 * HW1, z0 - 1, z1 + 1, ex, ey))
    return s.cut(slot).cut(cyl(SHAFT_D + 0.2, z0 - 1, z1 + 1))


_PLATE = None


def plate(theta):
    global _PLATE
    if _PLATE is None:
        _PLATE = plate_local()
    return _PLATE.rotate((0, 0, 0), (0, 0, 1), 180.0 - theta).translate((S[0], S[1], 0))


def servo_body_box(grow=0.0):
    ang = SERVO_AZ - 90.0
    b = box_from(-SERVO["l"] / 2 - grow, SERVO["l"] / 2 + grow, -SERVO["w"] / 2 - grow, SERVO["w"] / 2 + grow,
                 SERVO_Z0, SERVO_Z0 + SERVO["h"])
    return b.rotate((0, 0, 0), (0, 0, 1), ang).translate((SERVO_C[0], SERVO_C[1], 0))


def servo():
    ang = SERVO_AZ - 90.0
    zt = SERVO_Z0 + SERVO["h"] - SERVO["tab_h"] - SERVO["tab_t"]
    tabs = box_from(-SERVO["tab_l"] / 2, SERVO["tab_l"] / 2, -SERVO["w"] / 2, SERVO["w"] / 2, zt, zt + SERVO["tab_t"])
    tabs = tabs.rotate((0, 0, 0), (0, 0, 1), ang).translate((SERVO_C[0], SERVO_C[1], 0)).intersect(cyl(2 * ENVELOPE_R, -5, 40))
    boss = cyl(SERVO["boss_d"], SERVO_Z0 + SERVO["h"], LEVER_Z[0], *SERVO_AX)
    return servo_body_box().union(tabs).union(boss)


def carrier():
    z0, z1 = RING["z"]
    ring = tube(RING["od"], 0, z0, z1)
    lug = box_from(LUG["x"][0], LUG["x"][1], -LUG["w"] / 2, LUG["w"] / 2, BUSH["z"][0], BUSH["z"][1]).union(
        box_from(LUG["x"][0], LUG["x"][1] - 5.0, -LUG["w"] / 2, LUG["w"] / 2, z0, BUSH["z"][0]))
    ang = SERVO_AZ - 90.0
    zt = SERVO_Z0 + SERVO["h"] - SERVO["tab_h"] - SERVO["tab_t"]
    cons = box_from(-SERVO["l"] / 2 - 1.0, SERVO["l"] / 2 + 1.0, -SERVO["w"] / 2 - 3.0, SERVO["w"] / 2, z0, SERVO_Z0)
    for sx in (-1, 1):
        px = sx * (SERVO["l"] / 2 + 2.2)
        cons = cons.union(box_from(px - 1.8, px + 1.8, -SERVO["w"] / 2 - 3.0, SERVO["w"] / 2, z0, zt))
    cons = cons.rotate((0, 0, 0), (0, 0, 1), ang).translate((SERVO_C[0], SERVO_C[1], 0)).intersect(cyl(2 * ENVELOPE_R, -5, 40))
    ears = box_from(15.5, 22.0, -3.5, 3.5, z0 + 1.5, z1 - 1.5).rotate((0, 0, 0), (0, 0, 1), 135.0)
    slit = box_from(13.0, 23.0, -0.5, 0.5, z0 - 1, z1 + 1).rotate((0, 0, 0), (0, 0, 1), 135.0)
    s = ring.union(lug).union(cons).union(ears).cut(slit).cut(cyl(RING["id"], -5, 40))
    s = s.cut(cyl(BUSH["od"], -5, 40, *S)).cut(servo_body_box(0.15)).cut(servo())
    t = e(225)
    ear_c = (18.7 * e(135)[0], 18.7 * e(135)[1])
    screw = cyl_between(2.0, (ear_c[0] - 4.5 * t[0], ear_c[1] - 4.5 * t[1], 5.2), (ear_c[0] + 4.5 * t[0], ear_c[1] + 4.5 * t[1], 5.2))
    return s.cut(screw), screw


def shaft():
    zb = BUSH["z"][1]
    s = cyl(SHAFT_D, PLATE_Z[0] - 3.0, LEVER_Z[1] + 2.4, *S)
    for z0, z1, d in ((PLATE_Z[1], PLATE_Z[1] + 1.8, 6.0),            # flache Mutter über der Scheibe
                      (PLATE_Z[0] - 0.5, PLATE_Z[0], 9.0), (PLATE_Z[0] - 2.9, PLATE_Z[0] - 0.5, 6.0),   # Scheibe und Mutter darunter
                      (zb, zb + 0.5, 7.0), (zb + 0.5, LEVER_Z[0], 6.0),  # Anlaufscheibe und Mutter über dem Lager
                      (LEVER_Z[1], LEVER_Z[1] + 2.4, 6.0)):              # Mutter über der Kurbel
        s = s.union(cyl(d, z0, z1, *S))
    return s


def crank(theta):
    k = crank_pin(theta)
    return _bar(S, k, 4.0, *LEVER_Z).union(cyl(6.0, *LEVER_Z, *S)).cut(cyl(SHAFT_D, 0, 40, *S)).cut(cyl(1.8, 0, 40, *k)), k


def horn(theta):
    psi = servo_angle(theta)
    h = (SERVO_AX[0] + HORN_R * e(psi)[0], SERVO_AX[1] + HORN_R * e(psi)[1])
    return _bar(SERVO_AX, h, 4.0, *LEVER_Z).union(cyl(6.0, *LEVER_Z, *SERVO_AX)).cut(cyl(1.8, 0, 40, *h)), h


def link(theta):
    k, h = crank(theta)[1], horn(theta)[1]
    wire = cyl_between(1.0, (h[0], h[1], LINK_Z), (k[0], k[1], LINK_Z))
    return wire.union(cyl(1.6, LEVER_Z[0], LINK_Z + 0.5, *h)).union(cyl(1.6, LEVER_Z[0], LINK_Z + 0.5, *k))


def build_throttle(theta=0.0, context=True, case_z=None):
    parts = Parts()
    c, screw = carrier()
    parts.add("Drosselträger (Druckteil)", c, "printed", "drossel")
    parts.add("Servo 4,3 g", servo(), "servo", "drossel")
    parts.add("Servohebel", horn(theta)[0], "nose", "drossel")
    parts.add("Stange Servo–Kurbel", link(theta), "steel", "drossel")
    parts.add("Kurbel auf der Welle", crank(theta)[0], "alu", "drossel")
    parts.add("Welle M3 mit Muttern", shaft(), "steel", "drossel")
    parts.add("Buchse Messing 4 × 0,45", tube(BUSH["od"], BUSH["id"], *BUSH["z"], *S), "battery", "drossel")
    parts.add("Schlitzscheibe (Edelstahl 1,5 mm)", plate(theta), "leg", "drossel")
    parts.add("Klemmschraube M2", screw, "steel", "drossel")
    if context:
        parts.add("Motor TSP E12-0", cyl(P.MOTOR_D, 0.0, M.MOTOR_L).cut(cyl(2 * JET_R, -1, 6)), "motor", "antrieb")
        parts.add("Adapter 29→24", tube(ADAPTER_OD, P.ADAPTER_ID, 0.5, M.MOTOR_L), "coupler", "antrieb")
    if case_z is not None:
        parts.add("leere Hülse (Motorwechsel)", tube(CASE_D, 18.0, case_z, case_z + P.MOTOR_L), "motor", "auswurf")
    return parts


# --------------------------------------------------------------------------- Prüfungen
def envelope_below(theta):
    """Größter Abstand der Scheibe von der Rohrachse (unter dem Rohr)."""
    r = 0.0
    for ed in plate(theta).val().Edges():
        for k in range(0, 9):
            p = ed.positionAt(k / 8)
            r = max(r, math.hypot(p.x, p.y))
    return r


def check_all():
    out = []
    thetas = (0.0, 20.0, 40.0, 60.0, THETA_MAX)
    bad = []
    for th in thetas:
        parts = build_throttle(th)
        for i in range(len(parts)):
            for j in range(i + 1, len(parts)):
                v = _vol(parts[i][1], parts[j][1])
                if v > 0.05:
                    bad.append(f"theta {th:.0f}°: {parts[i][0]} / {parts[j][0]}: {v:.2f} mm³")
    out.append(("Teile gegeneinander, Drehwinkel 0 … 80° in fünf Schritten", bad))
    # Auswurf: Zylinder Ø 25 (Hülse 24 + 0,5 Luft je Seite) von der Düsenebene 60 mm nach unten
    path = cyl(CASE_D + 1.0, -60.0, -0.1).val()
    parts = build_throttle(0.0, context=False)
    bad = [f"{n}: {_vol(path, s):.1f} mm³" for n, s, _, _ in parts if _vol(path, s) > 0.01]
    out.append((f"Auswurf der Hülse Ø {CASE_D:.0f} durch das Loch Ø {2 * HW0:.0f} bei theta = 0 (Luft {HW0 - CASE_D / 2:.1f} mm ringsum)", bad))
    L = 40.0
    cone = cq.Solid.makeCone(JET_R, JET_R + L * math.tan(math.radians(JET_HALF_DEG)), L, cq.Vector(0, 0, 0), cq.Vector(0, 0, -1))
    bad = [f"{n}: {_vol(cone, s):.1f} mm³" for n, s, _, _ in parts if _vol(cone, s) > 0.01]
    out.append((f"Strahlkegel ±{JET_HALF_DEG:.0f}° frei bei theta = 0 (Strahlradius an der Scheibe {JET_R_PLATE:.1f}, Loch {HW0:.1f})", bad))
    tube_a = MD.tube_a().val()
    clear = {}
    for g in (5.0, 7.0):
        for label, tilts in ((f"±{g:.0f}° in einer Achse", ((g, 0), (-g, 0), (0, g), (0, -g))),
                             (f"±{g:.0f}° in beiden Achsen", ((g, g), (g, -g), (-g, g), (-g, -g)))):
            bad, rmax = [], 0.0
            for th in (0.0, 40.0, THETA_MAX):
                comp = cq.Compound.makeCompound([s for _, s, _, _ in build_throttle(th, context=False)])
                for pitch, yaw in tilts:
                    t = _tilt(comp, pitch, yaw)
                    rmax = max(rmax, max_radius(t))
                    v = _vol(t, tube_a)
                    if v > 0.05:
                        bad.append(f"theta {th:.0f}°, Kardan {pitch:+.0f}/{yaw:+.0f}: {v:.1f} mm³ im Rohr")
            clear[label] = TUBE_R - rmax
            out.append((f"Kardan {label}: Luft zur Rohrwand {TUBE_R - rmax:.1f} mm", bad))
    return out, clear


def masses(parts):
    rows = []
    for n, s, col, g in parts:
        if g != "drossel":
            continue
        fixed = next((m for k, m in FIXED_M.items() if n.startswith(k)), None)
        rows.append((n, fixed if fixed is not None else s.Volume() * (RHO["print"] if "Druckteil" in n else RHO["steel"])))
    return rows


def servo_load(f_block):
    """Servomoment für eine abgeblockte Schubkraft f_block (N): Die Kraft greift an der Düsenachse an, R neben der Welle.
    Das Kippmoment tragen zwei Lagerkräfte im Abstand der Buchsenlänge; Reibung am Wellenradius, dazu die Anlaufscheibe."""
    mu = 0.3
    lb = (BUSH["z"][1] - BUSH["z"][0]) * 1e-3
    m_tilt = f_block * R * 1e-3
    m_fric = mu * 2 * (m_tilt / lb) * (SHAFT_D / 2) * 1e-3 + mu * f_block * 0.0025
    d = 2.0
    ratio = abs(servo_angle(THETA_MAX / 2 + d) - servo_angle(THETA_MAX / 2 - d)) / (2 * d)
    sigma = 32 * m_tilt / (math.pi * (SHAFT_D * 1e-3) ** 3) / 1e6
    return dict(m_tilt=m_tilt, m_fric=m_fric, ratio=ratio, m_servo=m_fric / ratio, reserve=SERVO["torque_nm"] / (m_fric / ratio), sigma=sigma)


# --------------------------------------------------------------------------- Übersichtsbild (matplotlib)
def figure(path, clear, mass_total, env):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Polygon, Rectangle
    import numpy as np

    def place(pts, theta):
        a = math.radians(180.0 - theta)
        return [(S[0] + x * math.cos(a) - y * math.sin(a), S[1] + x * math.sin(a) + y * math.cos(a)) for x, y in pts]

    def circ(c, r, n=40):
        return [(c[0] + r * math.cos(2 * math.pi * k / n), c[1] + r * math.sin(2 * math.pi * k / n)) for k in range(n)]

    fig = plt.figure(figsize=(15, 9.6), layout="constrained")
    gs = fig.add_gridspec(2, 3, height_ratios=[1.2, 1.0])
    ex = (R * e(THETA_MAX)[0], R * e(THETA_MAX)[1])
    views = ((0.0, "0°: Loch unter der Düse\nStrahl frei, Hülse fällt durch"), (40.0, "40°: halber Weg"), (THETA_MAX, "80°: schmalstes Ende (2 mm)"))
    for k, (th, title) in enumerate(views):
        ax = fig.add_subplot(gs[0, k])
        ax.add_patch(Circle((0, 0), TUBE_R, fill=False, ec="#9aa5b1", lw=1.2, ls="--"))
        ax.add_patch(Circle((0, 0), JET_R_PLATE, fc="#f4a259", ec="#e76f51", lw=1.2, alpha=0.9, zorder=1))
        # Scheibe: Außenkontur, darüber die Schlitzfläche wieder in Hintergrundfarbe mit Strahl sichtbar
        for poly in (plate_outline_pts(), circ((R, 0), HW0 + RIM), circ((0, 0), 8.0)):
            ax.add_patch(Polygon(place(poly, th), fc="#7d8590", ec="none", zorder=2))
        for poly in (slot_pts(), circ((R, 0), HW0), circ(ex, HW1)):
            ax.add_patch(Polygon(place(poly, th), fc="w", ec="none", zorder=3))
        ax.add_patch(Circle((0, 0), JET_R_PLATE, fc="#f4a259", ec="none", alpha=0.35, zorder=4))
        tt = np.linspace(0, 2 * np.pi, 400)
        vis = [(JET_R_PLATE * math.cos(t), JET_R_PLATE * math.sin(t)) for t in tt]
        ax.plot([p[0] for p in vis], [p[1] for p in vis], color="#e76f51", lw=1.0, ls=":", zorder=5)
        ax.add_patch(Circle((0, 0), P.MOTOR_D / 2, fill=False, ec="#8d6e4a", lw=1.0, ls="-", zorder=5))
        # Servo, Kurbel, Stange (liegen über der Düsenebene)
        ang = math.radians(SERVO_AZ - 90.0)
        body = [(SERVO_C[0] + x * math.cos(ang) - y * math.sin(ang), SERVO_C[1] + x * math.sin(ang) + y * math.cos(ang))
                for x, y in ((-10, -4.25), (10, -4.25), (10, 4.25), (-10, 4.25))]
        ax.add_patch(Polygon(body, fc="#333", ec="k", lw=0.8, alpha=0.8, zorder=6))
        kp, psi = crank_pin(th), servo_angle(th)
        hp = (SERVO_AX[0] + HORN_R * e(psi)[0], SERVO_AX[1] + HORN_R * e(psi)[1])
        ax.plot([S[0], kp[0]], [S[1], kp[1]], color="k", lw=3, zorder=7)
        ax.plot([SERVO_AX[0], hp[0]], [SERVO_AX[1], hp[1]], color="w", lw=3.5, zorder=7); ax.plot([SERVO_AX[0], hp[0]], [SERVO_AX[1], hp[1]], color="k", lw=1, zorder=7)
        ax.plot([kp[0], hp[0]], [kp[1], hp[1]], color="#2a6f97", lw=1.8, zorder=7)
        ax.plot(*S, "o", color="k", ms=7, zorder=8)
        b_u, off = jet_stats(th)
        b_c, _ = jet_stats(th, core=True)
        ax.set_title(f"{title}\nabgedeckt {100 * b_u:.0f} % (Kern betont: {100 * b_c:.0f} %), Servo {psi:+.0f}°", fontsize=10)
        ax.set_xlim(-52, 62); ax.set_ylim(-57, 57); ax.set_aspect("equal"); ax.axis("off")
        if k == 0:
            ax.annotate("Welle", S, (40, -12), fontsize=8, arrowprops=dict(arrowstyle="-", lw=0.6))
            ax.annotate("Hülse Ø 24", (-8.5, 8.5), (-48, 30), fontsize=8, arrowprops=dict(arrowstyle="-", lw=0.6))
            ax.annotate("Rohr innen", (-25.6, 25.6), (-50, 44), fontsize=8, arrowprops=dict(arrowstyle="-", lw=0.6))
            ax.text(5, -56, "Draufsicht. Orange: Strahl an der Scheibe (Ø 18).", fontsize=8, ha="center")
    # Kennlinie
    ax = fig.add_subplot(gs[1, 0])
    th = np.linspace(0, THETA_MAX, 41)
    st = [jet_stats(t) for t in th]; sc = [jet_stats(t, core=True) for t in th]
    sv = [servo_angle(t) for t in th]
    ax.plot(sv, [100 * s[0] for s in st], color="#bc4749", lw=2, label="Impuls gleichmäßig im Strahl")
    ax.plot(sv, [100 * s[0] for s in sc], color="#e9a23b", lw=2, label="Impuls zur Mitte konzentriert")
    ax.axhline(65, color="k", lw=0.8, ls="--"); ax.text(sv[2], 67, "nötig für Schubfaktor 0,35", fontsize=8)
    ax.set_xlabel("Winkel des Servohebels (°)"); ax.set_ylabel("abgedeckter Anteil des Strahls (%)")
    ax.set_title("Geometrische Kennlinie (der Schub selbst kommt aus E05)", fontsize=10); ax.grid(alpha=0.3); ax.legend(fontsize=8, loc="upper left")
    # Seitenansicht (schematisch, Schnitt durch Düse und Welle)
    ax = fig.add_subplot(gs[1, 1])
    ax.add_patch(Rectangle((-TUBE_R - 1.25, 0), 1.25, 34, fc="#e8e0cc", ec="k", lw=0.6)); ax.add_patch(Rectangle((TUBE_R, 0), 1.25, 34, fc="#e8e0cc", ec="k", lw=0.6))
    ax.add_patch(Rectangle((-14.5, 0.5), 29, 33.5, fc="#eadfce", ec="#8d6e4a", lw=0.8)); ax.add_patch(Rectangle((-12, 0), 24, 34, fc="#d8b98a", ec="k", lw=0.8))
    ax.add_patch(Polygon([(-JET_R, 0), (JET_R, 0), (JET_R_PLATE + 4, -30), (-JET_R_PLATE - 4, -30)], fc="#f4a259", ec="none", alpha=0.6))
    ax.add_patch(Rectangle((LUG["x"][0], BUSH["z"][0]), LUG["x"][1] - LUG["x"][0], BUSH["z"][1] - BUSH["z"][0], fc="#3d6fb5", ec="k", lw=0.6))
    ax.add_patch(Rectangle((R - 1.5, PLATE_Z[0] - 3), 3, LEVER_Z[1] + 2.4 - PLATE_Z[0] + 3, fc="#555", ec="k", lw=0.6))
    ax.add_patch(Rectangle((R - 7, LEVER_Z[0]), 8.5, 1.2, fc="#bbb", ec="k", lw=0.6))
    ax.add_patch(Rectangle((-HW0 - RIM, PLATE_Z[0]), RIM, PLATE_T, fc="#444", ec="k", lw=0.6)); ax.add_patch(Rectangle((HW0, PLATE_Z[0]), R - HW0 + 8, PLATE_T, fc="#444", ec="k", lw=0.6))
    ax.add_patch(Rectangle((-12, -62), 24, 30, fc="#d8b98a", ec="k", lw=0.8, alpha=0.55, ls="--"))
    ax.annotate("", (-22, 0), (-22, -GAP), arrowprops=dict(arrowstyle="<->", lw=1)); ax.text(-24, -GAP / 2, f"{GAP:.0f} mm", ha="right", va="center", fontsize=9)
    ax.text(0, 20, "Motor", ha="center", fontsize=9); ax.text(0, -48, "leere Hülse", ha="center", fontsize=9)
    ax.text(R + 5, 9, "Lager im\nTräger", fontsize=8, va="center"); ax.text(R + 3, 23, "Kurbel", fontsize=8); ax.text(R + 10, -15.5, "Schlitzscheibe", fontsize=8, va="center")
    ax.text(R + 3, -6, "Welle M3", fontsize=8); ax.text(-TUBE_R - 3, 28, "Rohr", fontsize=8, ha="right")
    ax.set_xlim(-58, 62); ax.set_ylim(-66, 38); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("Schnitt durch Düse und Welle bei 0°: Loch unter der Düse", fontsize=10)
    # Luft zur Rohrwand
    ax = fig.add_subplot(gs[1, 2])
    labels = list(clear); vals = [clear[k] for k in labels]
    ax.barh(range(len(vals)), vals, color=["#2a9d8f" if v > 0.5 else "#bc4749" for v in vals])
    for i, v in enumerate(vals):
        ax.text(max(v, 0) + 0.15, i, f"{v:+.1f} mm", va="center", fontsize=9)
    ax.set_yticks(range(len(vals)), ["Kardan " + s for s in labels], fontsize=8); ax.invert_yaxis()
    ax.axvline(0, color="k", lw=0.8); ax.set_xlim(min(min(vals), 0) - 1.5, max(vals) + 3)
    ax.set_xlabel("Luft zwischen Drossel und Rohrwand (mm)"); ax.grid(axis="x", alpha=0.3)
    ax.set_title(f"Masse {mass_total:.0f} g; Scheibe bis r = {env:.0f} mm", fontsize=10)
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main():
    t0 = time.time()
    no_render = "--no-render" in sys.argv
    parts = build_throttle(0.0)
    rows = masses(parts)
    total = sum(m for _, m in rows)
    print(f"Schlitzscheibe: {len(rows)} Teile, Abstand zur Düse {GAP:.0f} mm, Stange {LINK_L:.1f} mm")
    for n, m in rows:
        print(f"  {n:36s} {m:5.1f} g")
    print(f"  {'gesamt':36s} {total:5.1f} g")
    env = max(envelope_below(t) for t in (0.0, 20.0, 40.0, 60.0, THETA_MAX))
    print(f"Die Scheibe reicht bis r = {env:.1f} mm von der Rohrachse (Rohr außen 37,5), {GAP + PLATE_T + 3:.0f} mm unter die Rohrunterkante")
    print(f"Servo {servo_angle(0):+.0f}° … {servo_angle(THETA_MAX):+.0f}° für 0 … {THETA_MAX:.0f}° an der Scheibe")
    print("Kennlinie (abgedeckter Anteil gleichmäßig / Kern betont, Versatz des Reststrahls):")
    kenn = []
    for th in (0, 10, 20, 30, 40, 50, 60, 70, 80):
        b, off = jet_stats(th); bc, offc = jet_stats(th, core=True)
        kenn.append((th, b, bc, off))
        print(f"  theta {th:2d}°: Schlitz {2 * half_width(th):4.1f} mm, abgedeckt {100 * b:3.0f} % / {100 * bc:3.0f} %, Versatz {off:.2f} mm")
    for label, f in (("Plateau, tiefste Drosselung", 11.4 * 0.65), ("Schubspitze, tiefste Drosselung", 28.3 * 0.65)):
        sl = servo_load(f)
        print(f"Servo, {label} ({f:.1f} N auf der Scheibe): Kippmoment {1000 * sl['m_tilt']:.0f} mN·m, Reibmoment {1000 * sl['m_fric']:.0f} mN·m, "
              f"am Servo {1000 * sl['m_servo']:.0f} von {1000 * SERVO['torque_nm']:.0f} mN·m (Reserve {sl['reserve']:.1f}-fach), Biegespannung Welle {sl['sigma']:.0f} MPa")
    print("Prüfungen ...")
    results, clear = check_all()
    ok = True
    for label, bad in results:
        print(f"  {label}: " + ("frei" if not bad else "FEHLER"))
        for x in bad[:6]:
            print("    " + x)
        if "7°" not in label:
            ok &= not bad
    exp = HERE / "export"
    exp.mkdir(parents=True, exist_ok=True)
    build.assembly(parts).export(str(exp / "throttle_plate.step"))
    out = exp / "throttle_plate"
    out.mkdir(exist_ok=True)
    exporters.export(cq.Workplane().add(parts[0][1]), str(out / "Drosseltraeger_Schlitzscheibe.stl"), tolerance=0.02, angularTolerance=0.1)
    exporters.export(plate_local(), str(out / "Schlitzscheibe_Blech_1.5mm.step"))
    try:
        exporters.export(plate_local().faces("<Z"), str(out / "Schlitzscheibe_Blech_1.5mm.dxf"))
    except Exception as ex_:
        print(f"  DXF nicht geschrieben: {ex_}")
    sl = servo_load(28.3 * 0.65)
    (out / "throttle_plate.json").write_text(json.dumps(dict(
        mass_g=round(total, 1), parts={n: round(m, 2) for n, m in rows}, gap_mm=GAP, envelope_r_mm=round(env, 1),
        servo_range_deg=[round(servo_angle(0), 1), round(servo_angle(THETA_MAX), 1)],
        clearance_mm={k: round(v, 2) for k, v in clear.items()}, servo_reserve_peak=round(sl["reserve"], 2),
        kennlinie=[dict(theta=t, blocked_uniform=round(b, 3), blocked_core=round(bc, 3), offset_mm=round(o, 2)) for t, b, bc, o in kenn]),
        indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"  cad/export/throttle_plate.step, Teile in cad/export/throttle_plate/")
    build.IMG.mkdir(parents=True, exist_ok=True)
    figure(build.IMG / "throttle_plate_uebersicht.png", clear, total, env)
    print("  ok docs/img/cad/throttle_plate_uebersicht.png")
    if not no_render:
        print("Render ...")

        def short(parts, z=30.0):
            return [(n, cq.Workplane().add(s).intersect(box_from(-80, 80, -80, 80, -80, z)).val() if g == "antrieb" else s, c, g)
                    for n, s, c, g in parts]
        build.render(manifest(short(build_throttle(0.0, case_z=-75.0)), "throttle_plate_open"), build.IMG / "throttle_plate_auswurf.png", "throttle")
        build.render(manifest(short(build_throttle(60.0)), "throttle_plate_60"), build.IMG / "throttle_plate_gedrosselt.png", "throttle")
        tube_a = cq.Workplane().add(MD.tube_a().val()).intersect(box_from(-60, 60, -60, 60, -1, 45)).cut(box_from(-60, 60, -60, 0, -5, 60)).val()
        tilted = [(n, _tilt(s, 5.0, 5.0), c, g) for n, s, c, g in short(build_throttle(60.0), 44.0)]
        build.render(manifest(tilted + [("Rohr A (aufgeschnitten)", tube_a, "tube", "rumpf")], "throttle_plate_tube"),
                     build.IMG / "throttle_plate_in_tube.png", "throttle_side")
    print(f"{'alles frei' if ok else 'PRÜFUNG FEHLGESCHLAGEN'}, fertig in {time.time() - t0:.0f} s")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
