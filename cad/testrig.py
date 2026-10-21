"""TVC-Prüfstand: die Rakete hängt in einem zweiachsigen Gestell mit Drehpunkt im Schwerpunkt, an Stelle
des E12 liefert ein Brushless-Motor mit Propeller den Schub (Idee Jan, 21.10.2026; Teile docs/BUILD.md §1.5).

Aufbau (alle Maße in params.py, Abschnitt Prüfstand):
  Gestell:    Sperrholz-Grundplatte, zwei Alu-Stützen 40 × 40 bei x = ±RIG_UPRIGHT_X mit Kugellager 608 in
              Höhe des Drehpunkts, zwei Achsstummel Ø 8 (x-Achse), die Rakete steht dazwischen.
  Rahmen:     Rechteck aus Alu-Profil 20 × 20, auf der Welle festgeklemmt, nickt mit der Rakete um x.
              Auf den y-Stäben zwei gedruckte Lagerböcke mit 608-Lagern.
  Kragen:     zweiteiliger gedruckter Klemmkragen um das Rohr in Höhe RIG_PIVOT_Z (Schwerpunkt), zwei Zapfen
              Ø 8 auf der y-Achse in die Lagerböcke: die Rakete giert um y. Rollen ist durch den Kragen gesperrt.
  Antrieb:    Adapter mit Ø-29-Zapfen im Motorrohr (Klemmschraube wie beim E12-Adapter) und Flansch unter dem
              Motorrohr, daran der BR2814 mit Welle nach unten, Propeller unterhalb der Rohrunterkante.
              Der Schubvektor geht durch den Kardanpunkt, der Kardan lenkt ihn wie im Flug.
  Schutz:     Käfig aus zwei Ringen mit Stäben und vier Speichen zu einem Klemmring am Rohrende; er sitzt an
              der Rakete und schwenkt mit ihr, die Propellerspitze hat 8 mm Luft bei ±7° Kardanauslenkung.
Nicht modelliert: Kabel, Anschläge (Gurt zwischen Rohr und Rahmen bei ±RIG_TILT_MAX_DEG), Schrauben.

Koordinaten: die Rakete behält ihr System (z ab Düse); der Boden liegt bei RIG_FLOOR_Z.
"""
import math
import cadquery as cq
import params as P
from common import Parts, tube, cyl, cyl_between, box, box_from, rot_about


# ----------------------------------------------------------------------------- Antrieb (bewegt sich mit dem Kardan)
def prop_adapter():
    """Zapfen im Motorrohr + Flansch unter dem Motorrohr mit Motor-Lochbild. Absolute z."""
    z_fl0, z_fl1 = P.PM_FLANGE_Z
    spigot = tube(P.PM_SPIGOT_D, 12.0, z_fl1, z_fl1 + P.PM_SPIGOT_L)
    for i in range(3):   # Schlitze wie beim E12-Adapter
        spigot = spigot.cut(box_from(-0.8, 0.8, 0, P.PM_SPIGOT_D, z_fl1 + P.PM_SPIGOT_L * 0.4, z_fl1 + P.PM_SPIGOT_L + 1)
                            .rotate((0, 0, 0), (0, 0, 1), 120 * i))
    flange = cyl(P.PM_FLANGE_D, z_fl0, z_fl1)
    a, b = P.PM_MOUNT_CROSS
    for (x, y) in ((a / 2, 0), (-a / 2, 0), (0, b / 2), (0, -b / 2)):
        flange = flange.cut(cyl(3.2, z_fl0 - 1, z_fl1 + 1, x, y))
    flange = flange.cut(cyl(10.0, z_fl0 - 1, z_fl1 + 1))   # Wellen-/Kabeldurchlass
    return spigot.union(flange)


def prop_motor():
    z0, z1 = P.PM_CAN_Z
    can = cyl(P.PM_CAN_D, z0, z1)
    can = can.cut(tube(P.PM_CAN_D + 1, P.PM_CAN_D - 6, z0 + 2, z1 - 6))   # Lüftungsnut angedeutet
    shaft = cyl(P.PM_SHAFT_D, P.PROP_Z - P.PROP_T / 2 - 6, z0 + 1)
    return can.union(shaft)


def propeller():
    """Zweiblatt als flache Platte mit Nabe, Blätter um 15° angestellt."""
    R = P.PROP_DIA / 2
    hub = cyl(P.PROP_HUB_D, P.PROP_Z - P.PROP_T / 2, P.PROP_Z + P.PROP_T / 2)
    blade = box_from(6.0, R, -P.PROP_CHORD / 2, P.PROP_CHORD / 2, -1.2, 1.2)
    blade = blade.edges("|Z").fillet(5.0)
    blade = blade.rotate((0, 0, 0), (1, 0, 0), 15).translate((0, 0, P.PROP_Z))
    return hub.union(blade).union(blade.rotate((0, 0, 0), (0, 0, 1), 180))


def prop_motor_parts():
    """Liste (name, shape, color) in absoluten Koordinaten, ersetzt Adapter und E12 im Kardan."""
    return [("Prop-Adapter 29 mm (gedruckt)", prop_adapter(), "printed2"),
            ("Motor BR2814", prop_motor(), "servo"),
            ("Propeller 12x6", propeller(), "prop")]


# ----------------------------------------------------------------------------- Propellerschutz (an der Rakete)
def guard():
    R, d = P.GUARD_R, P.GUARD_TUBE_D
    zl, zu = P.GUARD_RING_Z
    rings = tube(2 * R + d, 2 * R - d, zl - d / 2, zl + d / 2).union(tube(2 * R + d, 2 * R - d, zu - d / 2, zu + d / 2))
    cage = rings
    for i in range(P.GUARD_BARS):
        phi = 2 * math.pi * i / P.GUARD_BARS
        cage = cage.union(cyl(d * 0.75, zl, zu, R * math.cos(phi), R * math.sin(phi)))
    collar = tube(P.GUARD_COLLAR_OD, P.TUBE_OD + 0.2, *P.GUARD_COLLAR_Z)
    collar = collar.cut(box_from(-60, 60, -1.0, 1.0, P.GUARD_COLLAR_Z[0] - 1, P.GUARD_COLLAR_Z[1] + 1))   # zweiteilig
    zc = (P.GUARD_COLLAR_Z[0] + P.GUARD_COLLAR_Z[1]) / 2 + 3
    for i in range(P.GUARD_SPOKES):
        phi = 2 * math.pi * i / P.GUARD_SPOKES + math.pi / 4
        p0 = (P.GUARD_COLLAR_OD / 2 - 2, 0, zc)
        p1 = (R, 0, zu)
        spoke = cyl_between(d, p0, p1).rotate((0, 0, 0), (0, 0, 1), math.degrees(phi))
        cage = cage.union(spoke)
    return [("Propellerschutz Käfig", cage, "alu"), ("Propellerschutz Klemmring", collar, "printed")]


# ----------------------------------------------------------------------------- Gestell, Rahmen, Kragen
def stand():
    bx, by, bt = P.RIG_BASE
    zf = P.RIG_FLOOR_Z
    base = box_from(-bx / 2, bx / 2, -by / 2, by / 2, zf, zf + bt)
    parts = [("Grundplatte Sperrholz", base, "wood")]
    pr = P.RIG_PROFILE
    for sx in (-1, 1):
        x = sx * P.RIG_UPRIGHT_X
        up = box_from(x - pr / 2, x + pr / 2, -pr / 2, pr / 2, zf + bt, P.RIG_UPRIGHT_TOP)
        up = up.cut(cyl_between(P.RIG_BEARING[0], (x - pr, 0, P.RIG_PIVOT_Z), (x + pr, 0, P.RIG_PIVOT_Z)))
        parts.append((f"Stütze {'links' if sx < 0 else 'rechts'} 40x40", up, "alu"))
        brace = cyl_between(pr * 0.6, (x - sx * 10, 0, zf + bt + 40), (x - sx * 260, 0, zf + bt + 3))
        brace2 = cyl_between(pr * 0.6, (x, -20, zf + bt + 330), (x, -200, zf + bt + 3))
        brace3 = cyl_between(pr * 0.6, (x, 20, zf + bt + 330), (x, 200, zf + bt + 3))
        for j, b in enumerate((brace, brace2, brace3)):
            parts.append((f"Strebe {'links' if sx < 0 else 'rechts'} {j + 1}", b, "alu"))
        bearing = tube(P.RIG_BEARING[0], P.RIG_BEARING[1], 0, P.RIG_BEARING[2]).rotate((0, 0, 0), (0, 1, 0), 90)
        parts.append((f"Lager 608 Stütze {'links' if sx < 0 else 'rechts'}", bearing.translate((x - P.RIG_BEARING[2] / 2, 0, P.RIG_PIVOT_Z)), "steel"))
    L = P.RIG_UPRIGHT_X + pr / 2 + 15
    x_in = P.RIG_FRAME_X[0] + 2          # Stummel beginnt im Rahmenboss, nicht im Schwenkbereich des Kragens
    for sx, lbl in ((-1, "links"), (1, "rechts")):
        stub = cyl_between(P.RIG_AXLE_D, (sx * x_in, 0, P.RIG_PIVOT_Z), (sx * L, 0, P.RIG_PIVOT_Z))
        parts.append((f"Achsstummel Ø 8 {lbl}", stub, "steel"))
    return parts


def frame():
    """Rahmen aus 20 × 20 um den Drehpunkt (vor der Nick-Rotation)."""
    x0, x1 = P.RIG_FRAME_X
    y0, y1 = P.RIG_FRAME_Y
    h = P.RIG_FRAME_H
    z = P.RIG_PIVOT_Z
    bars = (box_from(x0, x1, -y1, y1, z - h / 2, z + h / 2).union(box_from(-x1, -x0, -y1, y1, z - h / 2, z + h / 2))
            .union(box_from(-x1, x1, y0, y1, z - h / 2, z + h / 2)).union(box_from(-x1, x1, -y1, -y0, z - h / 2, z + h / 2)))
    # Bosse für die Welle an den x-Stäben
    boss = cyl_between(20.0, (x0, 0, z), (x1 + 6, 0, z))
    bars = bars.union(boss).union(boss.mirror("YZ"))
    bars = bars.cut(cyl_between(P.RIG_AXLE_D + 0.2, (-x1 - 10, 0, z), (x1 + 10, 0, z)))
    out = [("Rahmen 20x20", bars, "alu")]
    bw, bd, bh = P.RIG_BEARING_BLOCK
    for sy in (-1, 1):
        yc = sy * (y0 + y1) / 2
        blk = box_from(-bw / 2, bw / 2, yc - bd / 2 - 2, yc + bd / 2 + 2, z - bh / 2, z + bh / 2)
        blk = blk.cut(cyl_between(P.RIG_BEARING[0], (0, yc - 20, z), (0, yc + 20, z)))
        out.append((f"Lagerbock {'−y' if sy < 0 else '+y'}", blk, "printed"))
        bearing = tube(P.RIG_BEARING[0], P.RIG_BEARING[1], 0, P.RIG_BEARING[2]).rotate((0, 0, 0), (1, 0, 0), -90)
        out.append((f"Lager 608 Rahmen {'−y' if sy < 0 else '+y'}", bearing.translate((0, yc - P.RIG_BEARING[2] / 2, z)), "steel"))
    ex, ey, ez = P.RIG_ESC_BOX
    out.append(("ESC + Akku 4S", box_from(-ex / 2, ex / 2, -y1 - ey, -y1, z - ez / 2, z + ez / 2), "battery"))
    return out


def collar():
    """Zweiteiliger Klemmkragen, Teilung in der Ebene x = 0, Ohren an ±y mit je zwei M4 über und unter dem
    Zapfen; der Zapfen Ø 8 liegt in der Teilung und wird von den Hälften geklemmt (vor den Rotationen)."""
    z = P.RIG_PIVOT_Z
    h = P.RIG_COLLAR_H
    c = tube(P.RIG_COLLAR_OD, P.RIG_COLLAR_ID, z - h / 2, z + h / 2)
    fl_l, fl_w = P.RIG_COLLAR_FLANGE
    ro = P.RIG_COLLAR_OD / 2
    for sy in (-1, 1):
        y_a, y_b = sorted((sy * (ro - 3), sy * (ro + fl_l)))
        c = c.union(box_from(-fl_w / 2, fl_w / 2, y_a, y_b, z - h / 2, z + h / 2))
        for zz in (z - 13, z + 13):
            c = c.cut(cyl_between(4.4, (-fl_w, sy * (ro + fl_l / 2 + 1.5), zz), (fl_w, sy * (ro + fl_l / 2 + 1.5), zz)))
    c = c.cut(box_from(-0.6, 0.6, -ro - fl_l - 1, ro + fl_l + 1, z - h / 2 - 1, z + h / 2 + 1))   # Teilung x = 0
    c = c.cut(cyl_between(P.RIG_STUD_D + 0.2, (0, -ro - fl_l - 2, z), (0, ro + fl_l + 2, z)))      # Zapfenbohrung
    y_stud = P.RIG_FRAME_Y[1] + 4
    stud = cyl_between(P.RIG_STUD_D, (0, ro - 6, z), (0, y_stud, z))
    head = cyl_between(P.RIG_STUD_D + 6, (0, y_stud, z), (0, y_stud + 3, z))
    studs = stud.union(head).union(stud.mirror("XZ")).union(head.mirror("XZ"))
    return [("Klemmkragen (gedruckt, 2-teilig)", c, "printed2"), ("Zapfen Ø 8", studs, "steel")]


# ----------------------------------------------------------------------------- Zusammenbau
def build(parts: Parts, rig_pitch=0.0, rig_yaw=0.0):
    """Nimmt die schon gebauten Raketenteile in `parts`, hängt den Propellerschutz an, dreht alles um den
    Drehpunkt (Gieren um y, dann Nicken um x mit dem Rahmen) und stellt das Gestell darunter."""
    piv = (0, 0, P.RIG_PIVOT_Z)
    rocket = list(parts)
    del parts[:]
    moving = rocket + [(n, s, c, "testrig") for n, s, c in guard()] + [(n, s, c, "testrig") for n, s, c in collar()]
    for name, shp, col, group in moving:
        w = cq.Workplane().add(shp)
        w = rot_about(w, piv, (0, 1, 0), rig_yaw)
        w = rot_about(w, piv, (1, 0, 0), rig_pitch)
        parts.add(name, w, col, group)
    for name, shp, col in frame():
        parts.add(name, rot_about(shp, piv, (1, 0, 0), rig_pitch), col, "testrig")
    for name, shp, col in stand():
        parts.add(name, shp, col, "testrig")
    return parts
