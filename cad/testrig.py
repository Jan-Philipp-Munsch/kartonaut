"""TVC-Prüfstand für die gebaute Rakete (Modulbauweise Kartonaut 1, Stand 2d). Idee Jan 21.10.2026, Teile docs/BUILD.md
§1.5; am 27.10.2026 von der alten Konfiguration (tvc.py, Rohr 20 mm über der Düse) auf die gebaute Rakete umgestellt.

    python cad/testrig.py              bauen, prüfen, export/testrig.step + testrig.stl, Druckteile export/testrig/*.stl,
                                       Bilder docs/img/cad/testrig*.png
    python cad/testrig.py --no-render  ohne Blender

Die Rakete hängt in einem zweiachsigen Gestell, Drehpunkt im Schwerpunkt; an Stelle des E12 liefert ein Brushless-Motor
mit Propeller den Schub, und der gebaute Kardan lenkt ihn wie im Flug.
  Antrieb:    Adapter mit Zapfen im gebauten Motorrohr (MotorTube.003, Unterkante z = 34) statt des 29→24-Adapters und des
              E12; darunter der BR2814 mit Welle nach unten, Propeller 12 × 6 knapp unter der Rohrunterkante. Der Schub
              geht durch den Kardanpunkt (z = 69,5).
  Schutz:     Käfig aus zwei Alu-Ringen Ø 8 mit Stäben und vier Speichen zu einem gedruckten Klemmring an Rohr A
              (z = 6 … 26, unter den Kardanschrauben bei z = 44).
  Kragen:     zweiteiliger gedruckter Klemmkragen um Rohr B in Höhe des Schwerpunkts, Ohren mit Zapfen Ø 8 bei 0°/180°
              der Rakete; Fenster lassen Luke B (Hauptschalter, Laden), den Schraubschalter und Luke A1 frei.
  Gestell:    Sperrholzplatte, zwei Alu-Stützen 40 × 40 mit Lager 608 auf Drehpunkthöhe, Achsstummel Ø 8, Rahmen aus
              Alu 20 × 20, der um x nickt, mit zwei gedruckten Lagerböcken für die Zapfen (Gieren um y).
Rig-Achsen: Achsstummel = x (Nicken), Zapfen = y (Gieren). Die Rakete ist im Gestell um RIG_ROLL_DEG gedreht: ihre
Längslinie 0° (Kardanschraube) zeigt nach +y, Luke B (270°) nach +x.
Koordinaten: z wie die Rakete (Düsenebene = Rohrunterkante = 0); der Boden liegt bei RIG_FLOOR_Z.
Nicht modelliert: Kabel, Gurt-Anschläge bei ±RIG_TILT_MAX_DEG, Schrauben.
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
import modular as MD
import modular_params as M
from common import Parts, tube, cyl, cyl_between, box_from, rot_about

PRINT_DIR = HERE / "export" / "testrig"
RHO_PETG = 1.27e-3        # g/mm³
PRINT_FILL = 0.75         # [Annahme] wie masses.json der Modulbauweise: 75 % des CAD-Volumens

# --------------------------------------------------------------------------- gebauter Kardan (Lage aus modular.py)
GIMBAL_PIVOT_Z = M.GIMBAL_BASE_Z + P.PIVOT_H     # 69,5: Kardanpunkt der gebauten Druckdatei
GIMBAL_FRAME_Z0 = M.GIMBAL_BASE_Z                 # 38: Grundfläche von Außen- und Innenrahmen
MOTOR_TUBE_Z0 = 34.0      # [STL] Unterkante MotorTube.003 in Lage (Bounding Box), Oberkante 92,6
MOTOR_TUBE_BORE = 28.6    # [Blender] Bohrung des gedruckten Motorrohrs; vor dem Druck des Adapters nachmessen
TUBE_R_IN = P.TUBE_ID / 2

# --------------------------------------------------------------------------- Antrieb (Racerstar BR2814 1000 KV [BUILD])
PM_CAN_D, PM_CAN_L, PM_SHAFT_D = 35.0, 36.0, 4.0   # [Annahme] typischer 2814-Außenläufer, am Teil nachmessen
PM_MOUNT_CROSS = (16.0, 19.0)                       # [Annahme] Kreuz-Lochbild M3
PM_M = 75.0                                         # [Annahme] g
PM_FLANGE_D, PM_FLANGE_T = 34.0, 5.0                # Adapterflansch so groß wie das Motorrohr (Ø 33,5): kippt mit ihm unter den Rahmen durch
PM_SPIGOT_D = MOTOR_TUBE_BORE - 0.2                 # Zapfen im Motorrohr, Sitz wie der 29→24-Adapter
PM_SPIGOT_ID = 12.0
PM_SPIGOT_L = 50.0                                  # 34 … 84, Motorrohr endet bei 92,6
PM_FLANGE_Z = (MOTOR_TUBE_Z0 - PM_FLANGE_T, MOTOR_TUBE_Z0)
PM_CAN_Z = (PM_FLANGE_Z[0] - PM_CAN_L, PM_FLANGE_Z[0])   # Glocke −7 … 29, Welle nach unten
PROP_DIA, PROP_CHORD, PROP_T, PROP_HUB_D = 305.0, 28.0, 8.0, 16.0   # [BUILD] 12 × 6; Blatt und Nabe [Annahme]
PROP_M = 15.0
PROP_Z = PM_CAN_Z[0] - 3.0 - PROP_T / 2             # Propellerebene ≈ −14, 14 mm unter der Rohrunterkante

# --------------------------------------------------------------------------- Propellerschutz
GUARD_R = PROP_DIA / 2 + 16.0     # Mitte des Ringrohrs: 12 mm radiales Spiel zur Propellerspitze
GUARD_TUBE_D = 8.0
GUARD_RING_Z = (PROP_Z - 32.0, 40.0)
GUARD_BARS, GUARD_SPOKES = 12, 4
GUARD_COLLAR_Z = (6.0, 26.0)      # Klemmring an Rohr A unter den Kardanschrauben (z 44, Köpfe 41 … 47)
GUARD_COLLAR_OD = 102.0           # Wand 13 mm für die Speichenbuchsen Ø 8,2
GUARD_COLLAR_ID = P.TUBE_OD + 0.2
GUARD_EAR = (12.0, 14.0)          # Ohren an der Teilung (radiale Länge, Höhe = Ringhöhe): je Seite eine M4
GUARD_M = 90.0                    # [Annahme] g, Alu-Rohr 8 mm (ohne den gedruckten Klemmring)

# --------------------------------------------------------------------------- Gestell
RIG_ROLL_DEG = 90.0               # Rakete gedreht: Längslinie 0° → +y (Zapfen), Luke B 270° → +x
RIG_PIVOT_ABOVE_FLOOR = 600.0     # [Annahme] Propeller dann ≈ 360 mm über dem Boden (mehr als ein Durchmesser)
RIG_TILT_MAX_DEG = 20.0           # [Annahme] Auslenkung je Achse, Begrenzung per Gurt zwischen Rohr und Rahmen
RIG_BASE = (820.0, 500.0, 18.0)   # [Annahme] Sperrholz-Grundplatte x × y × Dicke
RIG_UPRIGHT_X = 350.0
RIG_PROFILE = 40.0
RIG_BEARING = (22.0, 8.0, 7.0)    # Kugellager 608
RIG_AXLE_D = 8.0
RIG_FRAME_X = (60.0, 80.0)        # Innen-/Außenkante der x-Stäbe; Kragen r 47,5 und 32 mm über dem Drehpunkt
RIG_FRAME_Y = (67.5, 87.5)
RIG_FRAME_H = 20.0
RIG_BEARING_BLOCK = (30.0, 20.0, 30.0)
RIG_COLLAR_OD = 95.0
RIG_COLLAR_ID = P.TUBE_OD + 0.2
RIG_COLLAR_DZ = (-15.0, 50.0)     # Kragen vom Drehpunkt aus: 15 mm darunter, 50 darüber (über dem Fenster für Luke B und den
#   Schraubschalter bleibt ein Rand, damit jede Hälfte ein Stück ist; Luke A2 beginnt erst darüber)
RIG_COLLAR_FLANGE = (14.0, 16.0)  # Ohren: radiale Länge, Breite; je Seite 2 × M4 bei ±13 um den Zapfen
RIG_STUD_D = 8.0
RIG_ESC_BOX = (75.0, 35.0, 25.0)  # [Annahme] ESC + 4S-Akku als Klotz auf dem Rahmen (−y)
# Fenster im Kragen, in Winkeln der Rakete: Luke B mit Schraubschalter (282°, z 237) und Luke A1 (oben bis z 207)
HATCH_B_Z = (M.v_to_z(M.HATCH_B["v"][0]), M.v_to_z(M.HATCH_B["v"][1]))
HATCH_A1_Z = (M.v_to_z(M.HATCH_A1["v"][0]), M.v_to_z(M.HATCH_A1["v"][1]))
ARM_Z = M.v_to_z(M.ARM_SCREW_SWITCH["v"])
ARM_PHI = M.ARM_SCREW_SWITCH["phi"] + 12.0       # so gebohrt in modular.tube_b()
COLLAR_WINDOWS = [(249.0, 292.0, None, ARM_Z + 4.0), (73.0, 107.0, None, HATCH_A1_Z[1] + 2.0)]

P.COLORS.update({"alu": (0.75, 0.76, 0.78), "wood": (0.82, 0.70, 0.50), "prop": (0.20, 0.20, 0.22)})


def polar(r, phi, z):
    a = math.radians(phi)
    return (r * math.cos(a), r * math.sin(a), z)


def print_mass(shape):
    return shape.Volume() * RHO_PETG * PRINT_FILL


# --------------------------------------------------------------------------- Antrieb
def prop_adapter():
    z_fl0, z_fl1 = PM_FLANGE_Z
    spigot = tube(PM_SPIGOT_D, PM_SPIGOT_ID, z_fl1, z_fl1 + PM_SPIGOT_L)
    for i in range(3):   # Schlitze, damit der Zapfen im Motorrohr klemmt
        spigot = spigot.cut(box_from(-0.8, 0.8, 0, PM_SPIGOT_D, z_fl1 + PM_SPIGOT_L * 0.4, z_fl1 + PM_SPIGOT_L + 1)
                            .rotate((0, 0, 0), (0, 0, 1), 120 * i))
    flange = cyl(PM_FLANGE_D, z_fl0, z_fl1)
    a, b = PM_MOUNT_CROSS
    for (x, y) in ((a / 2, 0), (-a / 2, 0), (0, b / 2), (0, -b / 2)):
        flange = flange.cut(cyl(3.2, z_fl0 - 1, z_fl1 + 1, x, y))
    flange = flange.cut(cyl(10.0, z_fl0 - 1, z_fl1 + 1))   # Wellen- und Kabeldurchlass
    return spigot.union(flange)


def prop_motor():
    z0, z1 = PM_CAN_Z
    can = cyl(PM_CAN_D, z0, z1).cut(tube(PM_CAN_D + 1, PM_CAN_D - 6, z0 + 2, z1 - 6))
    return can.union(cyl(PM_SHAFT_D, PROP_Z - PROP_T / 2 - 6, z0 + 1))


def propeller():
    R = PROP_DIA / 2
    hub = cyl(PROP_HUB_D, PROP_Z - PROP_T / 2, PROP_Z + PROP_T / 2)
    blade = box_from(6.0, R, -PROP_CHORD / 2, PROP_CHORD / 2, -1.2, 1.2).edges("|Z").fillet(5.0)
    blade = blade.rotate((0, 0, 0), (1, 0, 0), 15).translate((0, 0, PROP_Z))
    return hub.union(blade).union(blade.rotate((0, 0, 0), (0, 0, 1), 180))


def drive_parts():
    return [("Prop-Adapter (gedruckt)", prop_adapter(), "printed2"), ("Motor BR2814", prop_motor(), "servo"),
            ("Propeller 12x6", propeller(), "prop")]


# --------------------------------------------------------------------------- Propellerschutz
def guard():
    R, d = GUARD_R, GUARD_TUBE_D
    zl, zu = GUARD_RING_Z
    cage = tube(2 * R + d, 2 * R - d, zl - d / 2, zl + d / 2).union(tube(2 * R + d, 2 * R - d, zu - d / 2, zu + d / 2))
    for i in range(GUARD_BARS):
        cage = cage.union(cyl(d * 0.75, zl, zu, *polar(R, 360.0 * i / GUARD_BARS, 0)[:2]))
    z0, z1 = GUARD_COLLAR_Z
    zc = (z0 + z1) / 2
    ring = tube(GUARD_COLLAR_OD, GUARD_COLLAR_ID, z0, z1)
    el, eh = GUARD_EAR
    ro = GUARD_COLLAR_OD / 2
    for sx in (-1, 1):   # Ohren an der Teilung y = 0, je eine M4 quer
        ring = ring.union(box_from(*sorted((sx * (ro - 3), sx * (ro + el))), -eh / 2, eh / 2, z0, z1))
        ring = ring.cut(cyl_between(4.4, (sx * (ro + el / 2), -eh, zc), (sx * (ro + el / 2), eh, zc)))
    ring = ring.cut(box_from(-ro - el - 1, ro + el + 1, -0.6, 0.6, z0 - 1, z1 + 1))   # Teilung y = 0
    spokes = None
    for i in range(GUARD_SPOKES):
        phi = 360.0 * i / GUARD_SPOKES + 45.0
        p0, p1 = polar(GUARD_COLLAR_OD / 2 - 5.0, phi, zc), polar(R, phi, zu)
        s = cyl_between(d, p0, p1)
        spokes = s if spokes is None else spokes.union(s)
        sock = cyl_between(d + 0.2, p0, p1).cut(cyl(GUARD_COLLAR_ID + 4.0, z0 - 20, z1 + 40))   # Buchse bis 2 mm vor das Rohr
        ring = ring.cut(sock)
    return [("Propellerschutz Käfig", cage.union(spokes), "alu"), ("Propellerschutz Klemmring", ring, "printed")]


# --------------------------------------------------------------------------- Kragen, Gestell, Rahmen
def rig_cg():
    """Schwerpunkt der Rakete im Prüfstand aus mass_stand2b.json (ohne Motor) mit den getauschten Teilen."""
    d = json.loads((HERE / "mass_stand2b.json").read_text(encoding="utf-8"))["configurations"]["no_motor"]
    m, mz = d["mass_kg"] * 1000, d["mass_kg"] * 1000 * d["cg_from_nozzle_m"] * 1000
    gz = sum(GUARD_RING_Z) / 2
    items = [(-P.ADAPTER_M, (8.0 + M.MOTOR_L) / 2),                    # 29→24-Adapter kommt raus
             (PM_M, sum(PM_CAN_Z) / 2), (PROP_M, PROP_Z),
             (print_mass(prop_adapter().val()), MOTOR_TUBE_Z0 + 5.0),
             (GUARD_M, gz), (print_mass(guard()[1][1].val()), sum(GUARD_COLLAR_Z) / 2)]
    for dm, z in items:
        m += dm
        mz += dm * z
    return m, mz / m


RIG_MASS_G, RIG_CG_Z = rig_cg()
RIG_PIVOT_Z = round(RIG_CG_Z)     # [cad] nach dem Auswiegen am Gerät setzen
RIG_FLOOR_Z = RIG_PIVOT_Z - RIG_PIVOT_ABOVE_FLOOR
RIG_UPRIGHT_TOP = RIG_PIVOT_Z + 60.0
RIG_COLLAR_Z = (RIG_PIVOT_Z + RIG_COLLAR_DZ[0], RIG_PIVOT_Z + RIG_COLLAR_DZ[1])


def collar():
    """Zweiteiliger Klemmkragen in Rig-Koordinaten (vor den Rig-Drehungen). Teilung in der Ebene x = 0, Ohren an ±y mit
    je zwei M4 über und unter dem Zapfen; der Zapfen Ø 8 liegt in der Teilung. Fenster in Winkeln der Rakete + RIG_ROLL."""
    z = RIG_PIVOT_Z
    z0, z1 = RIG_COLLAR_Z
    c = tube(RIG_COLLAR_OD, RIG_COLLAR_ID, z0, z1)
    fl_l, fl_w = RIG_COLLAR_FLANGE
    ro = RIG_COLLAR_OD / 2
    for sy in (-1, 1):
        c = c.union(box_from(-fl_w / 2, fl_w / 2, *sorted((sy * (ro - 3), sy * (ro + fl_l))), z0, z1))
        for zz in (z - 13, z + 13):
            c = c.cut(cyl_between(4.4, (-fl_w, sy * (ro + fl_l / 2 + 1.5), zz), (fl_w, sy * (ro + fl_l / 2 + 1.5), zz)))
    for a, b, wz0, wz1 in COLLAR_WINDOWS:
        a, b = a + RIG_ROLL_DEG, b + RIG_ROLL_DEG
        wz0 = z0 - 1 if wz0 is None else wz0
        wedge = (cq.Workplane("XY").workplane(offset=wz0)
                 .polyline([(0, 0)] + [polar(80.0, a + (b - a) * i / 8, 0)[:2] for i in range(9)]).close().extrude(wz1 - wz0))
        c = c.cut(wedge)
    c = c.cut(box_from(-0.6, 0.6, -ro - fl_l - 1, ro + fl_l + 1, z0 - 1, z1 + 1))     # Teilung x = 0
    c = c.cut(cyl_between(RIG_STUD_D + 0.2, (0, -ro - fl_l - 2, z), (0, ro + fl_l + 2, z)))
    y_stud = RIG_FRAME_Y[1] + 4
    stud = cyl_between(RIG_STUD_D, (0, ro - 6, z), (0, y_stud, z))
    head = cyl_between(RIG_STUD_D + 6, (0, y_stud, z), (0, y_stud + 3, z))
    studs = stud.union(head).union(stud.mirror("XZ")).union(head.mirror("XZ"))
    return [("Klemmkragen (gedruckt, 2-teilig)", c, "printed2"), ("Zapfen Ø 8", studs, "steel")]


def stand():
    bx, by, bt = RIG_BASE
    zf = RIG_FLOOR_Z
    parts = [("Grundplatte Sperrholz", box_from(-bx / 2, bx / 2, -by / 2, by / 2, zf, zf + bt), "wood")]
    pr = RIG_PROFILE
    zb = zf + bt
    for sx in (-1, 1):
        x = sx * RIG_UPRIGHT_X
        lbl = "links" if sx < 0 else "rechts"
        up = box_from(x - pr / 2, x + pr / 2, -pr / 2, pr / 2, zb, RIG_UPRIGHT_TOP)
        up = up.cut(cyl_between(RIG_BEARING[0], (x - pr, 0, RIG_PIVOT_Z), (x + pr, 0, RIG_PIVOT_Z)))
        parts.append((f"Stütze {lbl} 40x40", up, "alu"))
        h_br = 0.45 * (RIG_PIVOT_Z - zb)
        braces = (cyl_between(pr * 0.6, (x - sx * 10, 0, zb + 40), (x - sx * 220, 0, zb + 3)),
                  cyl_between(pr * 0.6, (x, -20, zb + h_br), (x, -200, zb + 3)),
                  cyl_between(pr * 0.6, (x, 20, zb + h_br), (x, 200, zb + 3)))
        for j, b in enumerate(braces):
            parts.append((f"Strebe {lbl} {j + 1}", b, "alu"))
        bearing = tube(RIG_BEARING[0], RIG_BEARING[1], 0, RIG_BEARING[2]).rotate((0, 0, 0), (0, 1, 0), 90)
        parts.append((f"Lager 608 Stütze {lbl}", bearing.translate((x - RIG_BEARING[2] / 2, 0, RIG_PIVOT_Z)), "steel"))
    L = RIG_UPRIGHT_X + pr / 2 + 15
    x_in = RIG_FRAME_X[0] + 2
    for sx, lbl in ((-1, "links"), (1, "rechts")):
        parts.append((f"Achsstummel Ø 8 {lbl}", cyl_between(RIG_AXLE_D, (sx * x_in, 0, RIG_PIVOT_Z), (sx * L, 0, RIG_PIVOT_Z)), "steel"))
    return parts


def bearing_block():
    bw, bd, bh = RIG_BEARING_BLOCK
    z = RIG_PIVOT_Z
    yc = sum(RIG_FRAME_Y) / 2
    blk = box_from(-bw / 2, bw / 2, yc - bd / 2 - 2, yc + bd / 2 + 2, z - bh / 2, z + bh / 2)
    blk = blk.cut(cyl_between(RIG_BEARING[0], (0, yc - 20, z), (0, yc + 20, z)))
    return blk.cut(box_from(-bw, bw, RIG_FRAME_Y[0], RIG_FRAME_Y[1], z - RIG_FRAME_H / 2, z + RIG_FRAME_H / 2))   # sitzt auf dem Stab


def frame():
    x0, x1 = RIG_FRAME_X
    y0, y1 = RIG_FRAME_Y
    h = RIG_FRAME_H
    z = RIG_PIVOT_Z
    bars = (box_from(x0, x1, -y1, y1, z - h / 2, z + h / 2).union(box_from(-x1, -x0, -y1, y1, z - h / 2, z + h / 2))
            .union(box_from(-x1, x1, y0, y1, z - h / 2, z + h / 2)).union(box_from(-x1, x1, -y1, -y0, z - h / 2, z + h / 2)))
    boss = cyl_between(20.0, (x0, 0, z), (x1 + 6, 0, z))
    bars = bars.union(boss).union(boss.mirror("YZ"))
    bars = bars.cut(cyl_between(RIG_AXLE_D + 0.2, (-x1 - 10, 0, z), (x1 + 10, 0, z)))
    out = [("Rahmen 20x20", bars, "alu")]
    yc = (y0 + y1) / 2
    for sy in (-1, 1):
        blk = bearing_block() if sy > 0 else bearing_block().mirror("XZ")
        out.append((f"Lagerbock {'−y' if sy < 0 else '+y'}", blk, "printed"))
        bearing = tube(RIG_BEARING[0], RIG_BEARING[1], 0, RIG_BEARING[2]).rotate((0, 0, 0), (1, 0, 0), -90)
        out.append((f"Lager 608 Rahmen {'−y' if sy < 0 else '+y'}", bearing.translate((0, sy * yc - RIG_BEARING[2] / 2, z)), "steel"))
    ex, ey, ez = RIG_ESC_BOX
    out.append(("ESC + Akku 4S", box_from(-ex / 2, ex / 2, -y1 - ey, -y1, z - ez / 2, z + ez / 2), "battery"))
    return out


# --------------------------------------------------------------------------- Zusammenbau
_ROCKET = None


def rocket_base():
    """Gebaute Rakete ohne E12 und ohne den Kardan-Hüllkörper (der reicht bis z = 3 und steht für Motor und Adapter);
    der Kardan selbst wird über die Lage des Antriebs geprüft (check_drive)."""
    global _ROCKET
    if _ROCKET is None:
        _ROCKET = [(n, s, c, g) for n, s, c, g in MD.build_all() if not n.startswith(("Motor TSP", "Kardan (gebaut"))]
    return _ROCKET


def build(gimbal_pitch=0.0, gimbal_yaw=0.0, rig_pitch=0.0, rig_yaw=0.0):
    """Rakete im Prüfstand: Antrieb um den Kardanpunkt geneigt, Rakete um RIG_ROLL gedreht, dann Gieren um y und Nicken
    um x im Drehpunkt; Gestell fest, Rahmen nickt mit."""
    parts = Parts()
    kp = (0, 0, GIMBAL_PIVOT_Z)
    rp = (0, 0, RIG_PIVOT_Z)
    moving = [(n, s, c, g) for n, s, c, g in rocket_base()]
    for n, s, c in drive_parts():
        s = rot_about(s, kp, (1, 0, 0), gimbal_pitch)
        s = rot_about(s, kp, (0, 1, 0), gimbal_yaw)
        moving.append((n, s, c, "antrieb"))
    moving += [(n, s, c, "testrig") for n, s, c in guard()]
    rolled = []
    for n, s, c, g in moving:
        w = s if isinstance(s, cq.Workplane) else cq.Workplane().add(s)
        rolled.append((n, w.rotate((0, 0, 0), (0, 0, 1), RIG_ROLL_DEG), c, g))
    rolled += [(n, s if isinstance(s, cq.Workplane) else cq.Workplane().add(s), c, "testrig") for n, s, c in collar()]
    for n, w, c, g in rolled:
        w = rot_about(w, rp, (0, 1, 0), rig_yaw)
        w = rot_about(w, rp, (1, 0, 0), rig_pitch)
        parts.add(n, w, c, g)
    for n, s, c in frame():
        parts.add(n, rot_about(s, rp, (1, 0, 0), rig_pitch), c, "testrig")
    for n, s, c in stand():
        parts.add(n, s, c, "testrig")
    return parts


# --------------------------------------------------------------------------- Prüfungen
def _vol(a, b):
    ba, bb = a.BoundingBox(), b.BoundingBox()
    if ba.xmax < bb.xmin or bb.xmax < ba.xmin or ba.ymax < bb.ymin or bb.ymax < ba.ymin or ba.zmax < bb.zmin or bb.zmax < ba.zmin:
        return 0.0
    r = cq.Workplane().add(a).intersect(cq.Workplane().add(b))
    return sum(s.Volume() for s in r.vals()) if r.vals() else 0.0


FIXED = ("Stütze", "Strebe", "Grundplatte", "Achsstummel", "Lager 608 Stütze", "Rahmen", "Lagerbock", "Lager 608 Rahmen", "ESC")


def check_drive():
    """Antrieb gegen den gebauten Kardan und das Rohr: Flansch unter den Rahmen, Glocke und Flansch im Rohr, Propeller
    unter dem Rohr und im Käfig, bei Kardan ±7° in beiden Achsen."""
    g = P.GIMBAL_MAX_DEG
    out = []
    a = math.radians(g * math.sqrt(2))   # Kippwinkel bei ±7°/±7°
    dz = GIMBAL_PIVOT_Z - PM_FLANGE_Z[1]
    top = GIMBAL_PIVOT_Z - dz * math.cos(a) + PM_FLANGE_D / 2 * math.sin(a)
    out.append((f"Adapterflansch bei {math.degrees(a):.1f}° Kippung bis z = {top:.1f}, Kardanrahmen ab z = {GIMBAL_FRAME_Z0:.0f}",
                [] if top < GIMBAL_FRAME_Z0 - 0.3 else ["zu hoch"]))
    worst = 0.0
    for r, z in ((PM_FLANGE_D / 2, PM_FLANGE_Z[0]), (PM_CAN_D / 2, PM_CAN_Z[0])):
        worst = max(worst, r * math.cos(a) + (GIMBAL_PIVOT_Z - z) * math.sin(a))
    out.append((f"Flansch und Glocke bei voller Kippung bis r = {worst:.1f}, Rohr innen r = {TUBE_R_IN:.1f}",
                [] if worst < TUBE_R_IN - 1.0 else ["zu weit außen"]))
    bad = []
    for gp, gy in ((0, 0), (g, g), (g, -g), (-g, g), (-g, -g), (g, 0), (0, g)):
        by = {n: s for n, s, _, _ in build(gp, gy)}
        for x, y in (("Propeller 12x6", "Propellerschutz Käfig"), ("Propeller 12x6", "Propellerschutz Klemmring"),
                     ("Propeller 12x6", "Rohr A 125 (Kardan, gebaut)"), ("Motor BR2814", "Rohr A 125 (Kardan, gebaut)"),
                     ("Prop-Adapter (gedruckt)", "Rohr A 125 (Kardan, gebaut)"), ("Propellerschutz Klemmring", "Rohr A 125 (Kardan, gebaut)")):
            v = _vol(by[x], by[y])
            if v > 0.5:
                bad.append(f"Kardan {gp:+.0f}/{gy:+.0f}: {x} / {y}: {v:.0f} mm³")
    out.append(("Propeller, Glocke, Adapter und Käfig-Klemmring gegen Rohr A und Käfig, Kardan 0° und ±7°", bad))
    return out


def check_rig():
    g, t = P.GIMBAL_MAX_DEG, RIG_TILT_MAX_DEG
    cases = [(0, 0, t, 0), (0, 0, -t, 0), (0, 0, 0, t), (0, 0, 0, -t), (g, g, t, t), (-g, -g, -t, -t), (g, -g, t, -t), (-g, g, -t, t)]
    bad = []
    for gp, gy, rp, ry in cases:
        parts = build(gp, gy, rp, ry)
        fixed = [(n, s) for n, s, _, g_ in parts if n.startswith(FIXED)]
        moving = [(n, s) for n, s, _, g_ in parts if not n.startswith(FIXED)]
        for mn, ms in moving:
            for fn, fs in fixed:
                if fn.startswith(("Rahmen", "Lagerbock", "Lager 608 Rahmen", "ESC")) and mn.startswith(("Zapfen", "Klemmkragen")):
                    continue   # Zapfen läuft im Lagerbock, Kragen hängt am Rahmen: gewollt
                v = _vol(ms, fs)
                if v > 0.5:
                    bad.append(f"Kardan {gp:+.0f}/{gy:+.0f}, Rig {rp:+.0f}/{ry:+.0f}: {mn} / {fn}: {v:.0f} mm³")
        # Kragen gegen den Rahmen extra: er darf ihn nur über die Zapfen berühren
        by = {n: s for n, s, _, _ in parts}
        v = _vol(by["Klemmkragen (gedruckt, 2-teilig)"], by["Rahmen 20x20"])
        if v > 0.5:
            bad.append(f"Rig {rp:+.0f}/{ry:+.0f}: Klemmkragen / Rahmen: {v:.0f} mm³")
    return [(f"Rakete, Antrieb, Käfig und Kragen gegen Gestell und Rahmen, Rig ±{t:.0f}° je Achse, Kardan ±{g:.0f}°", bad)]


def check_collar():
    """Kragen lässt Luke B, den Schraubschalter und Luke A1 frei und trifft keine Schraubenköpfe."""
    c = collar()[0][1].val()
    bad = []
    r0, r1 = P.TUBE_OD / 2 - 0.5, RIG_COLLAR_OD / 2 + 1
    probes = [("Luke B", M.HATCH_B["phi"], M.HATCH_B.get("w", M.HATCH_W), HATCH_B_Z),
              ("Luke A1", M.HATCH_A1["phi"], M.HATCH_W, HATCH_A1_Z),
              ("Schraubschalter", ARM_PHI, 6.0, (ARM_Z - 3.0, ARM_Z + 3.0))]
    for name, phi, w, (za, zb) in probes:
        prism = box_from(-w / 2, w / 2, r0, r1, za, zb).rotate((0, 0, 0), (0, 0, 1), phi + RIG_ROLL_DEG - 90.0).val()
        v = _vol(c, prism)
        if v > 0.5:
            bad.append(f"{name}: {v:.0f} mm³ verdeckt")
    for z in (M.OLD_HOLES_B_Z, M.SPIGOT_B_SCREW_Z):
        if RIG_COLLAR_Z[0] - 4 < z < RIG_COLLAR_Z[1] + 4:
            bad.append(f"Schraubenebene z = {z:.0f} unter dem Kragen")
    big = 300.0
    for side, sx in (("+x (Luke B)", 1), ("−x (Luke A1)", -1)):
        half = c.intersect(box_from(min(0, sx * big), max(0, sx * big), -big, big, -big, 2 * big).val())
        n = len(half.Solids())
        if n != 1:
            bad.append(f"Kragenhälfte {side} zerfällt in {n} Stücke")
        else:
            rim = RIG_COLLAR_Z[1] - max(w[3] for w in COLLAR_WINDOWS)
            if rim < 6.0:
                bad.append(f"Rand über den Fenstern nur {rim:.1f} mm")
    for z in (M.v_to_z(M.HATCH_A2["v"][0]),):
        if z < RIG_COLLAR_Z[1] + 1:
            bad.append(f"Luke A2 ab z = {z:.0f} unter dem Kragen")
    return [(f"Kragen z {RIG_COLLAR_Z[0]:.0f} … {RIG_COLLAR_Z[1]:.0f} lässt Luke B, Schraubschalter und Luke A1 frei, "
             f"Luke A2 und Schraubenebenen außerhalb", bad)]


# --------------------------------------------------------------------------- Druckteile
def printed_parts():
    """(Datei, Stückzahl, Form) liegend fürs Druckbett: Kragenhälften mit der Teilung nach unten, Klemmring-Hälften
    ebenso, Lagerbock auf der Grundfläche, Adapter mit dem Flansch nach unten."""
    def bed(shape):
        bb = shape.BoundingBox()
        return shape.translate(cq.Vector(-(bb.xmin + bb.xmax) / 2, -(bb.ymin + bb.ymax) / 2, -bb.zmin))
    col = collar()[0][1].val()
    big = 300.0
    zc = RIG_PIVOT_Z
    half_b = col.intersect(box_from(0, big, -big, big, -big, 2 * big).val())    # +x: Fenster Luke B
    half_a = col.intersect(box_from(-big, 0, -big, big, -big, 2 * big).val())   # −x: Fenster Luke A1
    half_b = half_b.rotate(cq.Vector(0, 0, zc), cq.Vector(0, 1, zc), -90)     # Teilfläche nach unten
    half_a = half_a.rotate(cq.Vector(0, 0, zc), cq.Vector(0, 1, zc), 90)
    ring = guard()[1][1].val()
    gz = sum(GUARD_COLLAR_Z) / 2
    ring_half = ring.intersect(box_from(-big, big, 0, big, -big, big).val()).rotate(cq.Vector(0, 0, gz), cq.Vector(1, 0, gz), 90)
    return [("Klemmkragen_Haelfte_LukeB.stl", 1, bed(half_b)), ("Klemmkragen_Haelfte_LukeA.stl", 1, bed(half_a)),
            ("Lagerbock_608.stl", 2, bed(bearing_block().val())), ("Prop_Adapter.stl", 1, bed(prop_adapter().val())),
            ("Kaefig_Klemmring_Haelfte.stl", 2, bed(ring_half))]


def export_printed():
    PRINT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for fn, n, s in printed_parts():
        exporters.export(cq.Workplane().add(s), str(PRINT_DIR / fn), tolerance=0.05, angularTolerance=0.2)
        bb = s.BoundingBox()
        rows.append(dict(datei=f"cad/export/testrig/{fn}", stueck=n, cm3=round(s.Volume() / 1000, 1),
                         g=round(print_mass(s), 1), mm=[round(bb.xlen), round(bb.ylen), round(bb.zlen)]))
        print(f"  cad/export/testrig/{fn:32s} × {n}  {s.Volume() / 1000:5.1f} cm³  ≈ {print_mass(s):4.0f} g  "
              f"{bb.xlen:.0f} × {bb.ylen:.0f} × {bb.zlen:.0f} mm")
    (PRINT_DIR / "druckteile.json").write_text(json.dumps(dict(
        quelle="cad/testrig.py", material="PETG, 3 Wände, 25 % Gyroid (wie die Modulbauweise)",
        masse_regel=f"{PRINT_FILL:.0%} des CAD-Volumens × 1,27 g/cm³", teile=rows), indent=1, ensure_ascii=False), encoding="utf-8")


def main():
    t0 = time.time()
    no_render = "--no-render" in sys.argv
    print(f"Prüfstand: Rakete {RIG_MASS_G:.0f} g mit Propellerantrieb, Schwerpunkt z = {RIG_CG_Z:.1f} → Drehpunkt {RIG_PIVOT_Z:.0f} "
          f"(Kragen z {RIG_COLLAR_Z[0]:.0f} … {RIG_COLLAR_Z[1]:.0f}), Boden z = {RIG_FLOOR_Z:.0f}, "
          f"Propeller {PROP_Z - RIG_FLOOR_Z:.0f} mm über dem Boden")
    results = check_drive() + check_collar() + check_rig()
    ok = True
    for label, bad in results:
        print(f"  {label}: " + ("frei" if not bad else "FEHLER"))
        for x in bad:
            print("    " + x)
        ok &= not bad
    parts = build(4.0, 3.0, 12.0, 8.0)
    (HERE / "export").mkdir(exist_ok=True)
    import build as B
    B.assembly(parts).export(str(HERE / "export" / "testrig.step"))
    shapes = [s for n, s, _, _ in parts if n.startswith(FIXED)]
    exporters.export(cq.Workplane().add(cq.Compound.makeCompound(shapes)), str(HERE / "export" / "testrig.stl"),
                     tolerance=0.05, angularTolerance=0.2)
    print("  cad/export/testrig.step (Prüfstand mit Rakete, 12°/8° ausgelenkt) und testrig.stl (Gestell und Rahmen)")
    print("Druckteile:")
    export_printed()
    if not no_render:
        B.IMG.mkdir(parents=True, exist_ok=True)
        print("Render ...")
        d = B.write_render_manifest(parts, "testrig")
        B.render(d, B.IMG / "testrig.png", "testrig")
        drive = build(5.0, 4.0)
        d = B.write_render_manifest(drive, "testrig_drive", only_groups={"antrieb"},
                                    include=("Propellerschutz", "Rohr A"), cut=(-400, 400, -400, -2, 2, 2000))
        B.render(d, B.IMG / "testrig_drive.png", "testrig_drive")
    print(f"{'alles frei' if ok else 'PRÜFUNG FEHLGESCHLAGEN'}, fertig in {time.time() - t0:.0f} s")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
