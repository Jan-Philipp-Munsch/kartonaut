"""Schubdrossel mit zwei Pads und EINEM Servo für den Hüpfer (Konzept vom 15.11.2026, nicht gebaut).

    python cad/throttle.py              bauen, prüfen, export/throttle.step, STL, Bilder docs/img/cad/throttle*.png
    python cad/throttle.py --no-render  ohne Blender (das Kinematikbild entsteht trotzdem)

Aufbau (alles hängt am Motoradapter und schwenkt mit dem Kardan, die Pads bleiben also unter der Düse):
  Träger:   gedruckter Klemmring auf dem Adapter Ø 29 direkt über der Düsenebene, zwei Augen für die Drehachsen der
            Pads bei x = ±R_PIVOT, eine Konsole für das Servo.
  Pads:     zwei Blechhebel (Stahl 1 mm) mit je einem Mörtelklotz, die sich in einer Ebene quer zum Strahl um
            senkrechte Achsen (M3) drehen wie eine Schere. Die Kraft des Strahls auf ein Pad wirkt längs der
            Drehachse und geht über die Schraube in den Träger; das Servo trägt sie nicht.
  Kopplung: Beide Hebel drehen gleichsinnig um denselben Winkel (die Anordnung ist punktsymmetrisch zur Düse).
            Eine Koppelstange (Blechbogen um die Düse herum) verbindet zwei gleich lange Kurbeln an den Hebeln:
            ein Parallelkurbelgetriebe, die Winkel sind exakt gleich.
  Servo:    ein Mikroservo (4,3 g, Welle nach unten) neben dem Adapter, dort, wohin kein Pad schwenkt. Sein Hebel
            (4 mm) zieht über eine kurze Stange am Kurbelzapfen von Hebel 1 (8 mm): Übersetzung etwa 2 : 1.

Koordinaten: z wie die Rakete (z = 0 Düsenebene = Rohrunterkante, +z zur Spitze). x und y sind hier die Achsen des
Kardans (in der Rakete um modular_params.GIMBAL_ROT_DEG gedreht; für die Prüfung gegen das runde Rohr ist das gleich).
Der Spalt zwischen den Pads liegt auf der x-Achse. Öffnungswinkel delta: 0 = Pads geschlossen, DELTA_OPEN = offen (30°).
Jede Zahl mit Quelle wie in params.py; [Annahme] heißt nicht gemessen.
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
from common import Parts, tube, cyl, cyl_between, box_from

# --------------------------------------------------------------------------- Maße
PIVOT_Z = M.GIMBAL_BASE_Z + P.PIVOT_H        # Kardanpunkt 69,5 mm über der Düse
TUBE_R = M.TUBE_ID_MEASURED / 2              # [Jan 27.10.2026] 36,25
ADAPTER_OD = P.ADAPTER_OD                    # 29; [Annahme] der Adapter reicht bis 0,5 mm über die Düsenebene
JET_R, JET_HALF_DEG = 5.0, 15.0              # [Annahme] Düsenaustritt Ø 10, halber Öffnungswinkel des freien Strahls

RING = dict(od=33.0, id=ADAPTER_OD + 0.2, z=(0.5, 10.0))      # Klemmring, Wand 1,9
R_PIVOT = 20.0                               # Drehachsen der Pads bei (±20 | 0)
LUG = dict(w=8.0, r_out=24.0, z=(-1.0, 7.0))
PIVOT_SCREW_D, PIVOT_HOLE_D, SLEEVE_OD = 3.0, 3.2, 5.0        # M3, Distanzhülse zwischen Auge und Hebel
PAD = dict(lx=18.0, ly=13.0, t=4.0)          # Mörtelklotz je Pad; geschlossen stoßen die Kanten bei y = 0 zusammen
PAD_TOP_Z = -1.5                             # 1,5 mm unter der Düsenebene
ARM_T = 1.0                                  # Stahlblech
ARM_Z = (PAD_TOP_Z - PAD["t"] - ARM_T, PAD_TOP_Z - PAD["t"])  # −6,5 … −5,5
NECK_W = 5.0
CRANK = 8.0                                  # Kurbelradius an beiden Hebeln
TH_CLOSED = 285.0                            # Richtung der Kurbel bei geschlossenen Pads (zeigt nach −y); offen 255°
DELTA_OPEN = 30.0                            # Öffnungswinkel (40° ginge am Strahl, aber das offene Pad stieße bei ausgelenktem Kardan an den Rohrrand)
ENVELOPE_R = 25.6                            # Träger und Servolaschen außen auf diesen Radius abgerundet (Laschenecken abfeilen)
PIN_D = 2.0
COUPLER_Z = (ARM_Z[0] - 2.0, ARM_Z[0] - 1.0)                  # −8,5 … −7,5, unter den Hebeln
COUPLER_R = (17.5, 22.5)                     # Bogen um die Düse, Mittelpunkt wandert mit der Kurbel
# Servo: [Annahme] Klasse 4,3 g, 20 × 8,5 × 17, z. B. EMAX ES9051 (0,8 kg·cm, 0,09 s/60° laut Datenblatt, prüfen)
SERVO = dict(l=20.0, w=8.5, h=17.0, shaft_off=5.0, tab_l=28.0, tab_t=1.2, tab_h=4.0, boss_d=5.0, m=4.3,
             torque_nm=0.078, az=300.0)
SERVO_Z0 = 3.0                               # Unterkante des Servokörpers (Abtriebsseite unten)
SERVO_R = ADAPTER_OD / 2 + 0.55 + SERVO["w"] / 2              # Körpermitte radial 19,3
HORN_R = 4.0                                 # innerstes Loch eines Servohebels
HORN_Z = (-1.4, -0.2)
LINK_Z = -2.1                                # Mitte des Stangendrahts Ø 1
RHO = dict(steel=7.85e-3, mortar=2.0e-3, print=1.27e-3)       # g/mm³; Ofenmörtel [Annahme]
FIXED_M = {"Servohebel": 0.3, "Servo": SERVO["m"] + 1.5, "Schraube M3": 1.1, "Hülse": 0.25, "Zapfen": 0.2, "Klemmschraube": 0.4, "Stange": 0.15}
OLD_MASS = 60.0                              # docs/Baustellen_2026-10-26.md: Pads mit zwei Servos


def e(deg):
    a = math.radians(deg)
    return math.cos(a), math.sin(a)


P1, P2 = (R_PIVOT, 0.0), (-R_PIVOT, 0.0)
_er, _et = e(SERVO["az"]), e(SERVO["az"] + 90.0)
SERVO_C = (SERVO_R * _er[0], SERVO_R * _er[1])                               # Körpermitte
SERVO_AX = (SERVO_C[0] + SERVO["shaft_off"] * _et[0], SERVO_C[1] + SERVO["shaft_off"] * _et[1])   # Welle


def crank_pin(pivot, delta):
    u = e(TH_CLOSED - delta)
    return pivot[0] + CRANK * u[0], pivot[1] + CRANK * u[1]


_a_mid = crank_pin(P1, DELTA_OPEN / 2)
PSI_MID = 120.0                              # Richtung des Servohebels in der Mitte des Wegs (aus einer Suche: Übertragungswinkel ≥ 60°)
_h_mid = (SERVO_AX[0] + HORN_R * e(PSI_MID)[0], SERVO_AX[1] + HORN_R * e(PSI_MID)[1])
LINK_L = math.hypot(_a_mid[0] - _h_mid[0], _a_mid[1] - _h_mid[1])


def servo_angle(delta):
    """Winkel des Servohebels (Grad, 90° = Mitte) zum Öffnungswinkel delta: Viergelenk Servohebel–Stange–Kurbel."""
    ax, ay = crank_pin(P1, delta)
    dx, dy = ax - SERVO_AX[0], ay - SERVO_AX[1]
    d = math.hypot(dx, dy)
    c = (d * d + HORN_R * HORN_R - LINK_L * LINK_L) / (2 * d * HORN_R)
    if abs(c) > 1:
        return None
    base, off = math.degrees(math.atan2(dy, dx)), math.degrees(math.acos(c))
    p = min((base + off, base - off), key=lambda q: abs((q - PSI_MID + 180) % 360 - 180))
    return PSI_MID + (p - PSI_MID + 180) % 360 - 180


def blocked_fraction(delta, z=PAD_TOP_Z):
    """Anteil des Strahlquerschnitts in der Pad-Ebene, den beide Pads abdecken (rein geometrisch, kein Schub)."""
    r = JET_R + abs(z) * math.tan(math.radians(JET_HALF_DEG))
    d = R_PIVOT * math.sin(math.radians(delta))          # Abstand der Pad-Kante von der Düsenachse
    if d >= r:
        return 0.0
    seg = r * r * math.acos(d / r) - d * math.sqrt(r * r - d * d)
    return 2 * seg / (math.pi * r * r)


# --------------------------------------------------------------------------- Teile
def _rot(shape, center, deg):
    return shape.rotate((center[0], center[1], 0), (center[0], center[1], 1), deg)


def _bar(p0, p1, w, z0, z1):
    """Flacher Steg von p0 nach p1 mit runden Enden."""
    L = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    ang = math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
    s = box_from(0, L, -w / 2, w / 2, z0, z1).union(cyl(w, z0, z1)).union(cyl(w, z0, z1, L, 0))
    return s.rotate((0, 0, 0), (0, 0, 1), ang).translate((p0[0], p0[1], 0))


def carrier():
    z0, z1 = RING["z"]
    s = tube(RING["od"], 0, z0, z1)
    for sx in (1, -1):
        lug = box_from(min(sx * 14.0, sx * LUG["r_out"]), max(sx * 14.0, sx * LUG["r_out"]), -LUG["w"] / 2, LUG["w"] / 2, *LUG["z"])
        s = s.union(lug)
    # Servokonsole: Platte unter dem Servo (Abtriebsseite), zwei Pfosten unter den Laschen
    ang = SERVO["az"] - 90.0                # lokales x = tangential, lokales y = radial nach außen
    shelf = box_from(-SERVO["l"] / 2 - 1.0, SERVO["l"] / 2 + 1.0, -SERVO["w"] / 2 - 3.0, SERVO["w"] / 2, z0, SERVO_Z0)
    posts = None
    for sx in (-1, 1):
        px = sx * (SERVO["l"] / 2 + 2.2)
        post = box_from(px - 1.8, px + 1.8, -SERVO["w"] / 2 - 3.0, SERVO["w"] / 2, z0, SERVO_Z0 + SERVO["tab_h"])
        posts = post if posts is None else posts.union(post)
    cons = shelf.union(posts).cut(cyl(SERVO["boss_d"] + 0.6, z0 - 1, SERVO_Z0 + 1, SERVO["shaft_off"], 0))
    cons = cons.rotate((0, 0, 0), (0, 0, 1), ang).translate((SERVO_C[0], SERVO_C[1], 0))
    s = s.union(cons)
    # Klemmung bei 135°: zwei Ohren, Schlitz 1 mm, Schraube M2
    ears = box_from(15.5, 22.0, -3.5, 3.5, z0 + 1.5, z1 - 1.5).rotate((0, 0, 0), (0, 0, 1), 135.0)
    slit = box_from(13.0, 23.0, -0.5, 0.5, z0 - 1, z1 + 1).rotate((0, 0, 0), (0, 0, 1), 135.0)
    s = s.union(ears).cut(slit)
    s = s.cut(cyl(RING["id"], -5, 30))
    for p in (P1, P2):
        s = s.cut(cyl(PIVOT_HOLE_D, -5, 30, *p))
    # Servokörper freistellen (liegt an der Platte an, nicht im Ring)
    return s.cut(servo_body_box(0.15)).cut(servo()).intersect(cyl(2 * ENVELOPE_R, -5, 30))


def servo_body_box(grow=0.0):
    ang = SERVO["az"] - 90.0
    b = box_from(-SERVO["l"] / 2 - grow, SERVO["l"] / 2 + grow, -SERVO["w"] / 2 - grow, SERVO["w"] / 2 + grow,
                 SERVO_Z0, SERVO_Z0 + SERVO["h"])
    return b.rotate((0, 0, 0), (0, 0, 1), ang).translate((SERVO_C[0], SERVO_C[1], 0))


def servo():
    ang = SERVO["az"] - 90.0
    tabs = box_from(-SERVO["tab_l"] / 2, SERVO["tab_l"] / 2, -SERVO["w"] / 2, SERVO["w"] / 2,
                    SERVO_Z0 + SERVO["tab_h"], SERVO_Z0 + SERVO["tab_h"] + SERVO["tab_t"])
    tabs = tabs.rotate((0, 0, 0), (0, 0, 1), ang).translate((SERVO_C[0], SERVO_C[1], 0))
    boss = cyl(SERVO["boss_d"], HORN_Z[1], SERVO_Z0, *SERVO_AX)
    return servo_body_box().union(tabs.intersect(cyl(2 * ENVELOPE_R, -5, 30))).union(boss)


def horn(delta):
    psi = servo_angle(delta)
    h = (SERVO_AX[0] + HORN_R * e(psi)[0], SERVO_AX[1] + HORN_R * e(psi)[1])
    s = _bar(SERVO_AX, h, 4.0, *HORN_Z).union(cyl(6.0, *HORN_Z, *SERVO_AX))
    return s.cut(cyl(1.8, -5, 5, *h)), h


def link(delta):
    _, h = horn(delta)
    a = crank_pin(P1, delta)
    wire = cyl_between(1.0, (h[0], h[1], LINK_Z), (a[0], a[1], LINK_Z))
    leg = cyl(1.6, LINK_Z, HORN_Z[1], *h)
    eye = tube(4.0, PIN_D + 0.2, LINK_Z - 0.5, LINK_Z + 0.5, *a)
    return wire.union(leg).union(eye).cut(cyl(PIN_D + 0.2, -5, 5, *a))


def arm(which, delta):
    """Blechhebel mit Mörtelklotz; which = 1 (Achse bei +x, Pad auf der +y-Seite) oder 2."""
    s = 1 if which == 1 else -1
    piv = P1 if which == 1 else P2
    z0, z1 = ARM_Z
    lx, ly = PAD["lx"], PAD["ly"]
    plate = box_from(-lx / 2, lx / 2, min(0, s * ly), max(0, s * ly), z0, z1)
    neck = box_from(min(s * lx / 2, s * R_PIVOT), max(s * lx / 2, s * R_PIVOT), min(0, s * NECK_W), max(0, s * NECK_W), z0, z1)
    a0 = crank_pin(piv, 0.0)
    sheet = plate.union(neck).union(cyl(9.0, z0, z1, *piv)).union(_bar(piv, a0, 6.0, z0, z1))
    sheet = sheet.cut(cyl(PIVOT_HOLE_D, -20, 5, *piv)).cut(cyl(PIN_D + 0.2, -20, 5, *a0))
    pad = box_from(-lx / 2, lx / 2, min(0, s * ly), max(0, s * ly), z1, z1 + PAD["t"])
    return _rot(sheet, piv, -delta), _rot(pad, piv, -delta)


def coupler(delta):
    z0, z1 = COUPLER_Z
    c = (CRANK * e(TH_CLOSED - delta)[0], CRANK * e(TH_CLOSED - delta)[1])
    ring = tube(2 * COUPLER_R[1], 2 * COUPLER_R[0], z0, z1).cut(box_from(-40, 40, 0, 40, z0 - 1, z1 + 1))
    s = ring
    for p in (P1, P2):
        s = s.union(cyl(6.0, z0, z1, *p))
    for p in (P1, P2):
        s = s.cut(cyl(PIN_D + 0.2, -20, 5, *p))
    return s.translate((c[0], c[1], 0))


def hardware(delta):
    out = []
    for i, p in enumerate((P1, P2), 1):
        out.append((f"Schraube M3 Drehachse {i}", cyl(PIVOT_SCREW_D, ARM_Z[0] - 2.4, LUG["z"][1] + 2.4, *p)
                    .union(cyl(5.5, LUG["z"][1], LUG["z"][1] + 2.4, *p)).union(cyl(5.5, ARM_Z[0] - 2.4, ARM_Z[0], *p)), "steel"))
        out.append((f"Hülse Drehachse {i}", tube(SLEEVE_OD, PIVOT_HOLE_D, ARM_Z[1], LUG["z"][0], *p), "steel"))
        a = crank_pin(p, delta)
        top = LINK_Z + 0.9 if i == 1 else ARM_Z[1] + 0.8
        out.append((f"Zapfen Ø 2 Kurbel {i}", cyl(PIN_D, COUPLER_Z[0] - 0.8, top, *a)
                    .union(tube(4.0, PIN_D, COUPLER_Z[1], ARM_Z[0], *a)), "steel"))
    ear_c = (18.7 * e(135)[0], 18.7 * e(135)[1])
    t = e(225)
    out.append(("Klemmschraube M2", cyl_between(2.0, (ear_c[0] - 4.5 * t[0], ear_c[1] - 4.5 * t[1], 5.2),
                                                (ear_c[0] + 4.5 * t[0], ear_c[1] + 4.5 * t[1], 5.2)), "steel"))
    return out


def build_throttle(delta=0.0, context=True):
    """Teileliste (name, shape, color, group) bei Öffnungswinkel delta."""
    parts = Parts()
    c = carrier()
    for p in hardware(delta):
        if p[0].startswith("Klemmschraube"):
            c = c.cut(p[1])
    parts.add("Drosselträger (Druckteil)", c, "printed", "drossel")
    parts.add("Servo 4,3 g", servo(), "servo", "drossel")
    parts.add("Servohebel", horn(delta)[0], "nose", "drossel")
    parts.add("Stange Servo–Kurbel", link(delta), "steel", "drossel")
    for i in (1, 2):
        sheet, pad = arm(i, delta)
        parts.add(f"Hebel {i} (Stahlblech 1 mm)", sheet, "alu", "drossel")
        parts.add(f"Pad {i} (Ofenmörtel)", pad, "foot", "drossel")
    parts.add("Koppelstange (Stahlblech 1 mm)", coupler(delta), "leg", "drossel")
    for n, s, col in hardware(delta):
        parts.add(n, s, col, "drossel")
    if context:
        parts.add("Motor TSP E12-0", cyl(P.MOTOR_D, 0.0, M.MOTOR_L).cut(cyl(2 * JET_R, -1, 6)), "motor", "antrieb")
        parts.add("Adapter 29→24", tube(ADAPTER_OD, P.ADAPTER_ID, 0.5, M.MOTOR_L), "coupler", "antrieb")
    return parts


# --------------------------------------------------------------------------- Prüfungen
def _vol(a, b):
    ba, bb = a.BoundingBox(), b.BoundingBox()
    if ba.xmax < bb.xmin or bb.xmax < ba.xmin or ba.ymax < bb.ymin or bb.ymax < ba.ymin or ba.zmax < bb.zmin or bb.zmax < ba.zmin:
        return 0.0
    try:
        return cq.Workplane().add(a).intersect(cq.Workplane().add(b)).val().Volume()
    except Exception:
        return 0.0


def _tilt(shape, pitch, yaw):
    s = shape.rotate(cq.Vector(0, 0, PIVOT_Z), cq.Vector(1, 0, PIVOT_Z), pitch)
    return s.rotate(cq.Vector(0, 0, PIVOT_Z), cq.Vector(0, 1, PIVOT_Z), yaw)


def max_radius(shape):
    """Größter Abstand eines Punkts der Teile über der Rohrunterkante (z ≥ 0) von der Rohrachse."""
    try:
        top = cq.Workplane().add(shape).intersect(box_from(-60, 60, -60, 60, 0.0, 60)).val()
    except Exception:
        return 0.0
    r = 0.0
    for v in top.Vertices():
        r = max(r, math.hypot(v.X, v.Y))
    for ed in top.Edges():
        for k in range(1, 8):
            p = ed.positionAt(k / 8)
            r = max(r, math.hypot(p.x, p.y))
    return r


def check_all():
    out = []
    # 1 Teile gegeneinander über den ganzen Stellweg
    bad = []
    for delta in (0.0, 7.5, 15.0, 22.5, DELTA_OPEN):
        parts = build_throttle(delta)
        for i in range(len(parts)):
            for j in range(i + 1, len(parts)):
                v = _vol(parts[i][1], parts[j][1])
                if v > 0.05:
                    bad.append(f"delta {delta:.0f}°: {parts[i][0]} / {parts[j][0]}: {v:.2f} mm³")
    out.append(("Teile der Drossel gegeneinander, Öffnungswinkel 0 … 30° in fünf Schritten", bad))
    # 2 Strahl frei bei offenen Pads
    L = 30.0
    cone = cq.Solid.makeCone(JET_R, JET_R + L * math.tan(math.radians(JET_HALF_DEG)), L, cq.Vector(0, 0, 0), cq.Vector(0, 0, -1))
    parts = build_throttle(DELTA_OPEN, context=False)
    bad = [f"{n}: {_vol(cone, s):.1f} mm³" for n, s, _, _ in parts if _vol(cone, s) > 0.01]
    gap = R_PIVOT * math.sin(math.radians(DELTA_OPEN)) - (JET_R + abs(ARM_Z[0]) * math.tan(math.radians(JET_HALF_DEG)))
    out.append((f"Strahlkegel ±{JET_HALF_DEG:.0f}° frei bei offenen Pads (Luft zur Pad-Kante {gap:.1f} mm)", bad))
    # 3 mit dem Kardan geschwenkt gegen das Rohr A
    tube_a = MD.tube_a().val()
    clear = {}
    for g in (5.0, 7.0):
        for label, tilts in ((f"±{g:.0f}° in einer Achse", ((g, 0), (-g, 0), (0, g), (0, -g))),
                             (f"±{g:.0f}° in beiden Achsen", ((g, g), (g, -g), (-g, g), (-g, -g)))):
            bad, rmax = [], 0.0
            for delta in (0.0, DELTA_OPEN):
                comp = cq.Compound.makeCompound([s for _, s, _, _ in build_throttle(delta, context=False)])
                for pitch, yaw in tilts:
                    t = _tilt(comp, pitch, yaw)
                    rmax = max(rmax, max_radius(t))
                    v = _vol(t, tube_a)
                    if v > 0.05:
                        bad.append(f"delta {delta:.0f}°, Kardan {pitch:+.0f}/{yaw:+.0f}: {v:.1f} mm³ im Rohr")
            clear[label] = TUBE_R - rmax
            out.append((f"Kardan {label}: Luft zur Rohrwand {TUBE_R - rmax:.1f} mm", bad))
    return out, clear


def masses(parts):
    rows = []
    for n, s, col, g in parts:
        if g != "drossel":
            continue
        fixed = next((m for k, m in FIXED_M.items() if n.startswith(k)), None)
        if fixed is not None:
            rows.append((n, fixed))
        else:
            rho = RHO["mortar"] if n.startswith("Pad") else RHO["print"] if "Druckteil" in n else RHO["steel"]
            rows.append((n, s.Volume() * rho))
    return rows


def servo_load():
    """Abschätzung des Servomoments: Reibung an den Drehachsen unter der Axiallast, dazu eine vorsichtige Querkraft."""
    f_max, f_min = 28.3, 0.35                 # Schubspitze E12, tiefster Schubfaktor
    f_ax = f_max * (1 - f_min) / 2            # je Pad, N
    mu, r_fric = 0.3, 0.004                   # Stahl auf Stahl, Reibradius der Hülse
    m_fric = 2 * f_ax * mu * r_fric           # beide Hebel, N·m
    f_lat = 0.25 * f_ax                       # [Annahme] Querkraft des Strahls auf die Pad-Kante: ein Viertel der Axialkraft
    m_lat = 2 * f_lat * R_PIVOT * 1e-3
    d = 1.0
    ratio = (servo_angle(DELTA_OPEN / 2 + d) - servo_angle(DELTA_OPEN / 2 - d)) / (2 * d)
    return dict(f_ax=f_ax, m_fric=m_fric, m_lat=m_lat, ratio=abs(ratio), m_servo=(m_fric + m_lat) / abs(ratio),
                reserve=SERVO["torque_nm"] / ((m_fric + m_lat) / abs(ratio)))


# --------------------------------------------------------------------------- Kinematikbild (matplotlib)
def figure(path, clear, mass_total):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Polygon, Rectangle
    import numpy as np

    def rotp(pts, c, deg):
        a = math.radians(deg)
        return [(c[0] + (x - c[0]) * math.cos(a) - (y - c[1]) * math.sin(a), c[1] + (x - c[0]) * math.sin(a) + (y - c[1]) * math.cos(a)) for x, y in pts]

    fig = plt.figure(figsize=(14, 9), layout="constrained")
    gs = fig.add_gridspec(2, 3, height_ratios=[1.25, 1.0])
    lx, ly = PAD["lx"], PAD["ly"]
    r_pad = JET_R + abs(PAD_TOP_Z) * math.tan(math.radians(JET_HALF_DEG))
    for k, (delta, title) in enumerate(((0.0, "geschlossen (0°)"), (10.0, "halb (10°)"), (DELTA_OPEN, "offen (30°)"))):
        ax = fig.add_subplot(gs[0, k])
        ax.add_patch(Circle((0, 0), TUBE_R, fill=False, ec="#9aa5b1", lw=1.2, ls="--"))
        ax.add_patch(Circle((0, 0), ADAPTER_OD / 2, fc="#eadfce", ec="#8d6e4a", lw=1))
        ax.add_patch(Circle((0, 0), P.MOTOR_D / 2, fc="#d8b98a", ec="k", lw=0.8))
        # Servo, Träger
        ang = SERVO["az"] - 90.0
        body = [(-10, -4.25), (10, -4.25), (10, 4.25), (-10, 4.25)]
        body = [(SERVO_C[0] + x * math.cos(math.radians(ang)) - y * math.sin(math.radians(ang)),
                 SERVO_C[1] + x * math.sin(math.radians(ang)) + y * math.cos(math.radians(ang))) for x, y in body]
        ax.add_patch(Polygon(body, fc="#444", ec="k", lw=0.8, alpha=0.85))
        for s in (1, -1):
            ax.add_patch(Rectangle((s * 14.6 if s > 0 else -24, -4), 9.4, 8, fc="#3d6fb5", ec="k", lw=0.6, alpha=0.6))
        # Koppelstange
        c = (CRANK * e(TH_CLOSED - delta)[0], CRANK * e(TH_CLOSED - delta)[1])
        th = np.radians(np.linspace(180, 360, 60))
        outer = [(c[0] + COUPLER_R[1] * math.cos(t), c[1] + COUPLER_R[1] * math.sin(t)) for t in th]
        inner = [(c[0] + COUPLER_R[0] * math.cos(t), c[1] + COUPLER_R[0] * math.sin(t)) for t in th[::-1]]
        ax.add_patch(Polygon(outer + inner, fc="#555", ec="k", lw=0.6, alpha=0.45))
        for which, piv, s, col in ((1, P1, 1, "#bc4749"), (2, P2, -1, "#e07a5f")):
            pad = [(-lx / 2, 0), (lx / 2, 0), (lx / 2, s * ly), (-lx / 2, s * ly)]
            neck = [(s * lx / 2, 0), (s * R_PIVOT, 0), (s * R_PIVOT, s * NECK_W), (s * lx / 2, s * NECK_W)]
            ax.add_patch(Polygon(rotp(neck, piv, -delta), fc="#b0b7bf", ec="k", lw=0.6))
            ax.add_patch(Polygon(rotp(pad, piv, -delta), fc=col, ec="k", lw=0.8, alpha=0.9))
            a = crank_pin(piv, delta)
            ax.plot([piv[0], a[0]], [piv[1], a[1]], color="k", lw=2.2)
            ax.plot(*piv, "o", color="k", ms=6); ax.plot(*a, "o", color="w", mec="k", ms=5)
        psi = servo_angle(delta)
        h = (SERVO_AX[0] + HORN_R * e(psi)[0], SERVO_AX[1] + HORN_R * e(psi)[1])
        a = crank_pin(P1, delta)
        ax.plot([SERVO_AX[0], h[0]], [SERVO_AX[1], h[1]], color="w", lw=3.5, solid_capstyle="round")
        ax.plot([SERVO_AX[0], h[0]], [SERVO_AX[1], h[1]], color="k", lw=1.0)
        ax.plot([h[0], a[0]], [h[1], a[1]], color="#2a6f97", lw=1.8)
        ax.add_patch(Circle((0, 0), r_pad, fc="#f4a259", ec="#e76f51", lw=1.2, alpha=0.75, zorder=1.5 if delta > 0 else 0.5))
        ax.set_title(f"{title}: {100 * blocked_fraction(delta):.0f} % des Strahls abgedeckt, Servo {psi - PSI_MID:+.0f}°", fontsize=10)
        ax.set_xlim(-40, 40); ax.set_ylim(-40, 40); ax.set_aspect("equal"); ax.axis("off")
        if k == 0:
            ax.text(0, 37, "Draufsicht (Blick von der Spitze zur Düse); gestrichelt: Rohr innen Ø 72,5", ha="center", fontsize=8)
            ax.text(0, -39, "Servo über der Pad-Ebene im Rohr, Pads und Koppelstange darunter", ha="center", fontsize=8)
            ax.annotate("Pad 1", (0, 7), ha="center", color="w", fontsize=9); ax.annotate("Pad 2", (0, -8.5), ha="center", color="w", fontsize=9)
            ax.annotate("Servo", SERVO_C, ha="center", va="center", color="w", fontsize=8, rotation=ang)
            ax.annotate("Koppelstange", (-12, -31), ha="center", fontsize=8)
            ax.annotate("Drehachse", (P1[0] + 2, 6), fontsize=8)
    # Kennlinie
    ax = fig.add_subplot(gs[1, 0])
    dl = np.linspace(0, DELTA_OPEN, 81)
    ax.plot([servo_angle(d) - PSI_MID for d in dl], [100 * blocked_fraction(d) for d in dl], color="#bc4749", lw=2)
    ax.set_xlabel("Winkel des Servohebels um die Mitte (°)"); ax.set_ylabel("abgedeckter Strahlquerschnitt (%)")
    ax.set_title("Geometrische Kennlinie (kein Schub: der kommt aus E05)", fontsize=10); ax.grid(alpha=0.3)
    ax2 = fig.add_subplot(gs[1, 1])
    ax2.plot(dl, [servo_angle(d) - PSI_MID for d in dl], color="#2a6f97", lw=2)
    ax2.set_xlabel("Öffnungswinkel der Pads (°)"); ax2.set_ylabel("Servohebel (°)")
    ax2.set_title(f"Übersetzung Servo : Pad etwa {servo_load()['ratio']:.1f} : 1", fontsize=10); ax2.grid(alpha=0.3)
    ax3 = fig.add_subplot(gs[1, 2])
    labels = list(clear)
    vals = [clear[k] for k in labels]
    ax3.barh(range(len(vals)), vals, color=["#2a9d8f" if v > 0.5 else "#bc4749" for v in vals])
    for i, v in enumerate(vals):
        ax3.text(max(v, 0) + 0.15, i, f"{v:+.1f} mm", va="center", fontsize=9)
    ax3.set_yticks(range(len(vals)), ["Kardan " + s for s in labels], fontsize=8); ax3.invert_yaxis()
    ax3.axvline(0, color="k", lw=0.8); ax3.set_xlim(min(vals) - 1.5, max(vals) + 3)
    ax3.set_xlabel("Luft zwischen Drossel und Rohrwand (mm)")
    ax3.set_title(f"Masse {mass_total:.0f} g statt {OLD_MASS:.0f} g (zwei Servos)", fontsize=10); ax3.grid(axis="x", alpha=0.3)
    fig.suptitle("Schubdrossel mit einem Servo: zwei Scheren-Pads, Koppelstange, Mikroservo am Motoradapter", fontsize=12)
    fig.savefig(path, dpi=110)
    plt.close(fig)


# --------------------------------------------------------------------------- Export
def manifest(parts, name):
    d = build.EXPORT / "render" / name
    d.mkdir(parents=True, exist_ok=True)
    for f in d.glob("*.stl"):
        f.unlink()
    items = []
    for i, (pname, shape, col, group) in enumerate(parts):
        f = d / f"{i:03d}.stl"
        exporters.export(cq.Workplane().add(shape), str(f), tolerance=0.03, angularTolerance=0.15)
        items.append({"file": f.name, "name": pname, "color": P.COLORS[col], "group": group})
    (d / "manifest.json").write_text(json.dumps(items, indent=1, ensure_ascii=False), encoding="utf-8")
    return d


def main():
    t0 = time.time()
    no_render = "--no-render" in sys.argv
    parts = build_throttle(0.0)
    print(f"Schubdrossel: {sum(1 for p in parts if p[3] == 'drossel')} Teile, Stange Servo–Kurbel {LINK_L:.1f} mm, "
          f"Servowelle bei ({SERVO_AX[0]:.1f} | {SERVO_AX[1]:.1f})")
    rows = masses(parts)
    total = sum(m for _, m in rows)
    print("Massen (Volumen × Dichte, Kaufteile fest; alles [Annahme] bis gewogen):")
    for n, m in rows:
        print(f"  {n:34s} {m:5.1f} g")
    print(f"  {'gesamt':34s} {total:5.1f} g   (bisher angenommen: {OLD_MASS:.0f} g mit zwei Servos)")
    sl = servo_load()
    print(f"Servo: Stellweg {servo_angle(0) - PSI_MID:+.0f}° … {servo_angle(DELTA_OPEN) - PSI_MID:+.0f}° für 0 … {DELTA_OPEN:.0f}° am Pad, "
          f"Übersetzung {sl['ratio']:.2f} : 1")
    print(f"  Axiallast je Pad in der Schubspitze {sl['f_ax']:.1f} N (geht in die Drehachse); Reibmoment {1000 * sl['m_fric']:.0f} mN·m, "
          f"Querkraft-Annahme {1000 * sl['m_lat']:.0f} mN·m; am Servo {1000 * sl['m_servo']:.0f} mN·m von {1000 * SERVO['torque_nm']:.0f} "
          f"(Reserve {sl['reserve']:.1f}-fach)")
    d0 = math.degrees(math.asin((JET_R + abs(PAD_TOP_Z) * math.tan(math.radians(JET_HALF_DEG))) / R_PIVOT))
    print(f"  Die Pads greifen ab {d0:.1f}° Öffnungswinkel in den Strahl; das sind {abs(servo_angle(d0) - servo_angle(0)):.0f}° am Servo")
    print("Prüfungen ...")
    results, clear = check_all()
    ok = True
    for label, bad in results:
        print(f"  {label}: " + ("frei" if not bad else "FEHLER"))
        for x in bad[:6]:
            print("    " + x)
        if "7°" not in label:
            ok &= not bad
    (HERE / "export").mkdir(parents=True, exist_ok=True)
    step = HERE / "export" / "throttle.step"
    build.assembly(parts).export(str(step))
    out = HERE / "export" / "throttle"
    out.mkdir(exist_ok=True)
    exporters.export(cq.Workplane().add(parts[0][1]), str(out / "Drosseltraeger.stl"), tolerance=0.02, angularTolerance=0.1)
    for i in (1, 2):
        exporters.export(cq.Workplane().add(arm(i, 0.0)[0]), str(out / f"Hebel_{i}_Blech_1mm.step"))
    exporters.export(cq.Workplane().add(coupler(0.0)), str(out / "Koppelstange_Blech_1mm.step"))
    (out / "throttle.json").write_text(json.dumps(dict(
        mass_g=round(total, 1), parts={n: round(m, 2) for n, m in rows}, link_mm=round(LINK_L, 2),
        servo_range_deg=[round(servo_angle(0) - PSI_MID, 1), round(servo_angle(DELTA_OPEN) - PSI_MID, 1)],
        clearance_mm={k: round(v, 2) for k, v in clear.items()}, servo_reserve=round(sl["reserve"], 2)),
        indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"  {step.relative_to(HERE.parent)}, Druckteil und Blechteile in {out.relative_to(HERE.parent)}")
    build.IMG.mkdir(parents=True, exist_ok=True)
    figure(build.IMG / "throttle_kinematik.png", clear, total)
    print(f"  ok {(build.IMG / 'throttle_kinematik.png').relative_to(HERE.parent)}")
    if not no_render:
        print("Render ...")
        def short(parts, z=30.0):      # Motor und Adapter für das Bild kürzen
            return [(n, cq.Workplane().add(s).intersect(box_from(-60, 60, -60, 60, -60, z)).val() if g == "antrieb" else s, c, g)
                    for n, s, c, g in parts]
        build.render(manifest(short(build_throttle(0.0)), "throttle_closed"), build.IMG / "throttle_closed.png", "throttle")
        build.render(manifest(short(build_throttle(DELTA_OPEN)), "throttle_open"), build.IMG / "throttle_open.png", "throttle")
        tube_a = cq.Workplane().add(MD.tube_a().val()).intersect(box_from(-60, 60, -60, 60, -1, 45)).cut(box_from(-60, 60, -60, 0, -5, 60)).val()
        tilted = [(n, _tilt(s, 5.0, 5.0), c, g) for n, s, c, g in short(build_throttle(DELTA_OPEN), 44.0)]
        build.render(manifest(tilted + [("Rohr A (aufgeschnitten)", tube_a, "tube", "rumpf")], "throttle_tube"),
                     build.IMG / "throttle_in_tube.png", "throttle_side")
    print(f"{'alles frei' if ok else 'PRÜFUNG FEHLGESCHLAGEN'}, fertig in {time.time() - t0:.0f} s")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
