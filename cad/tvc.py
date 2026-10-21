"""TVC-Kardan nach dem BPS-Scout-F-Prinzip (dual_tvc / *_dual_TVC vom Juni 2025) mit FrSky W5652H.

Aufbau von außen nach innen, alle z relativ zur Rahmen-Grundfläche TVC_RING_Z:
  Außenrahmen: Flanschring (im Rohr, 4 × M3 radial), Servotasche bei -y, Lagerohr bei +y.
               Servowelle und Lagerbolzen liegen auf der y-Achse in Höhe PIVOT_H -> Innenrahmen kippt um y.
  Innenrahmen: Ring, Servotasche bei +x, Lagerohr bei -x, Lagerzapfen bei ±y.
               Welle und Bolzen auf der x-Achse -> Motorrohr kippt um x.
  Motorrohr:   Ø 33,5, Lagerzapfen bei ±x, darin Adapter 29→24 und der E12.
Das Servo liegt flach in der Rahmenwand, die Abtriebswelle zeigt radial nach innen und treibt das
nächstinnere Teil direkt über eine Hebelscheibe (keine Schubstange). Die Blender-Fassung vom 12.06.2025
hat dieses Prinzip mit einem "5600"-Servo, aber ohne das Lagerohr am Außenrahmen; es ist hier ergänzt.
Die Servowelle liegt genau auf der Rahmenachse; das Servogehäuse ist deshalb um SERVO_SHAFT_OFFSET
tangential versetzt (Taschen und Gehäuse wandern mit).
"""
import cadquery as cq
import params as P
from common import Parts, tube, cyl, cyl_between, box, box_from, rot_about, radial_holes

OFF = -P.SERVO_SHAFT_OFFSET          # tangentialer Versatz des Servogehäuses, Welle auf der Achse


def servo_local():
    """W5652H: Gehäuse bei y = -r, Welle auf der y-Achse (x = 0) nach +y (innen). Rückgabe (servo, hebel) vor Verschiebung."""
    L, H, T = P.SERVO_L, P.SERVO_H, P.SERVO_T
    body = box(L, T, H).translate((OFF, 0, 0))
    tabs = box(L + 2 * P.SERVO_TAB_L, 1.5, H * 0.7).translate((OFF, T / 2 - 0.75, 0))
    shaft = cyl_between(P.SERVO_SHAFT_D, (0, T / 2 - 0.1, 0), (0, T / 2 + P.SERVO_SHAFT_L, 0))
    horn = cyl_between(P.HORN_D, (0, T / 2 + P.SERVO_SHAFT_L, 0), (0, T / 2 + P.SERVO_SHAFT_L + P.HORN_T, 0))
    return body.union(tabs).union(shaft), horn


def servo(axis):
    """Servo montiert: axis "y" = Außenrahmen (bei -y), axis "x" = Innenrahmen (bei +x)."""
    s, h = servo_local()
    r = P.SERVO_OUTER_R if axis == "y" else P.SERVO_INNER_R
    s = s.translate((0, -r, P.PIVOT_H)); h = h.translate((0, -r, P.PIVOT_H))
    if axis == "x":
        s = s.rotate((0, 0, 0), (0, 0, 1), 90); h = h.rotate((0, 0, 0), (0, 0, 1), 90)
    return s, h


def pocket_cutters(r_servo, z):
    """Tasche (nach außen offen) für Servo + Laschen bei y = -r_servo, Welle bei x = 0, plus Wellenloch."""
    c = P.POCKET_CLEAR
    L, H, T = P.SERVO_L, P.SERVO_H, P.SERVO_T
    body = box_from(OFF - L / 2 - c, OFF + L / 2 + c, -r_servo - T / 2 - c - 20, -r_servo + T / 2 + c,
                    z - H / 2 - c, z + H / 2 + c)
    tabs = box_from(OFF - L / 2 - P.SERVO_TAB_L - c, OFF + L / 2 + P.SERVO_TAB_L + c, -r_servo - T / 2 - 20,
                    -r_servo + T / 2 - 1.5 + c, z - H * 0.35 - c, z + H * 0.35 + c)
    shaft = cyl_between(P.SERVO_SHAFT_D + 1.0, (0, -r_servo, z), (0, -r_servo + T / 2 + P.POCKET_WALL_IN + 1, z))
    return body.union(tabs).union(shaft)


def housing_box(r_in, r_out, z0, z1):
    hx = P.SERVO_L / 2 + 3.0 + P.SERVO_TAB_L
    return box_from(OFF - hx, OFF + hx, -r_out, -r_in, z0, z1)


def outer_gimbal():
    ro, ri = P.OUTER_RING_OD / 2, P.OUTER_RING_ID / 2
    g = tube(P.OUTER_RING_OD, P.OUTER_RING_ID, 0, P.OUTER_FLANGE_H)
    g = radial_holes(g, P.OUTER_SCREW_D, ro, P.OUTER_FLANGE_H / 2, n=4, phi0=45, depth=ro - ri + 1)
    r_in = P.SERVO_OUTER_R - P.SERVO_T / 2 - P.POCKET_WALL_IN
    housing = housing_box(r_in, ro + 1, P.OUTER_FLANGE_H - 1, P.OUTER_H).intersect(cyl(P.OUTER_RING_OD, 0, P.OUTER_H))
    g = g.union(housing).cut(pocket_cutters(P.SERVO_OUTER_R, P.PIVOT_H))
    # Lagerohr bei +y mit Bohrung für den M3-Bolzen
    ear = box_from(-8.0, 8.0, ro - P.OUTER_WALL_T, ro, P.OUTER_FLANGE_H - 1, P.OUTER_H).intersect(cyl(P.OUTER_RING_OD, 0, P.OUTER_H))
    ear = ear.edges("|Y").fillet(3.0)
    g = g.union(ear).cut(cyl_between(P.PIVOT_PIN_D + 0.2, (0, ro + 1, P.PIVOT_H), (0, ro - P.OUTER_WALL_T - 1, P.PIVOT_H)))
    return g


def boss_with_recess(r0, r1, along, d=None):
    """Lagerzapfen von Radius r0 bis r1 entlang +along ("x"/"y"/"-x"/"-y") in Höhe PIVOT_H mit Hebel-Vertiefung außen."""
    d = d or P.PIVOT_BOSS_D + 6
    sgn = -1 if along.startswith("-") else 1
    ax = along[-1]
    def pt(r):
        return (sgn * r, 0, P.PIVOT_H) if ax == "x" else (0, sgn * r, P.PIVOT_H)
    b = cyl_between(d, pt(r0), pt(r1))
    b = b.cut(cyl_between(P.HORN_D + 0.6, pt(r1 + 1), pt(r1 - P.HORN_T - 0.5)))
    b = b.cut(cyl_between(P.SERVO_SHAFT_D + 0.4, pt(r1 + 1), pt(r0 - 1)))
    return b


def pin_boss(r0, r1, along):
    """Lagerzapfen mit Kernloch für den M3-Bolzen."""
    sgn = -1 if along.startswith("-") else 1
    ax = along[-1]
    def pt(r):
        return (sgn * r, 0, P.PIVOT_H) if ax == "x" else (0, sgn * r, P.PIVOT_H)
    b = cyl_between(P.PIVOT_BOSS_D, pt(r0), pt(r1))
    return b.cut(cyl_between(P.PIVOT_PIN_D - 0.4, pt(r1 + 1), pt(r1 - 10)))


def inner_gimbal():
    ro, ri = P.INNER_RING_OD / 2, P.INNER_RING_ID / 2
    g = tube(P.INNER_RING_OD, P.INNER_RING_ID, 0, P.INNER_FLANGE_H)
    # Servogehäuse bei +x (gebaut bei -y, dann um +90° gedreht), beginnt über dem Außenflansch
    r_in = P.SERVO_INNER_R - P.SERVO_T / 2 - P.POCKET_WALL_IN
    r_out = P.SERVO_INNER_R + P.SERVO_T / 2 + 1.6
    housing = housing_box(r_in, r_out, P.INNER_HOUSING_Z0, P.INNER_H)
    strut = housing_box(ri - 1, r_out, P.INNER_FLANGE_H - 1, P.INNER_HOUSING_Z0 + 1).intersect(cyl(P.INNER_RING_OD, 0, P.INNER_H))
    hs = housing.union(strut).cut(pocket_cutters(P.SERVO_INNER_R, P.PIVOT_H)).rotate((0, 0, 0), (0, 0, 1), 90)
    hs = hs.intersect(cyl(2 * P.INNER_ENVELOPE_R, 0, P.INNER_H))   # Ecken des Gehäuses bleiben innerhalb des Rohrs
    g = g.union(hs)
    # Lagerohr bei -x
    ear = box_from(-ro, -ro + P.INNER_WALL_T, -8.0, 8.0, P.INNER_FLANGE_H - 1, P.INNER_H).intersect(cyl(P.INNER_RING_OD, 0, P.INNER_H))
    ear = ear.edges("|X").fillet(3.0)
    g = g.union(ear).cut(cyl_between(P.PIVOT_PIN_D + 0.2, (-ro - 1, 0, P.PIVOT_H), (-ro + P.INNER_WALL_T + 1, 0, P.PIVOT_H)))
    # Lagerzapfen zum Außenrahmen: +y Bolzen ins Lagerohr, -y Hebelscheibe des Außenservos
    r_ear_in = P.OUTER_RING_OD / 2 - P.OUTER_WALL_T
    web = box_from(-6, 6, ri - 1, ro - 0.5, P.INNER_FLANGE_H - 1, P.PIVOT_H)
    g = g.union(web).union(web.mirror("XZ"))
    g = g.union(pin_boss(ri + 0.5, r_ear_in - 0.5, "y"))
    r_horn_out = P.SERVO_OUTER_R - P.SERVO_T / 2 - P.POCKET_WALL_IN - 0.5     # Innenfläche der Außentasche minus Spiel
    g = g.union(boss_with_recess(ri + 0.5, r_horn_out, "-y"))
    return g


def motor_tube():
    ro, ri = P.MOTOR_TUBE_OD / 2, P.MOTOR_TUBE_ID / 2
    t = tube(P.MOTOR_TUBE_OD, P.MOTOR_TUBE_ID, 0, P.MOTOR_TUBE_L)
    r_ear_in = P.INNER_RING_OD / 2 - P.INNER_WALL_T
    web = box_from(ri - 0.5, ro + 0.5, -6, 6, P.PIVOT_H - 12, P.PIVOT_H + 12)
    t = t.union(web).union(web.mirror("YZ"))
    t = t.union(pin_boss(ri + 0.5, r_ear_in - 0.5, "-x"))
    r_horn_out = P.SERVO_INNER_R - P.SERVO_T / 2 - P.POCKET_WALL_IN - 0.5
    t = t.union(boss_with_recess(ri + 0.5, r_horn_out, "x"))
    # Klemmschraube für den Adapter, Anschlagring oben
    t = t.cut(cyl_between(P.MOTOR_CLAMP_SCREW_D, (0, -ro - 1, P.MOTOR_TUBE_L - 8), (0, 0, P.MOTOR_TUBE_L - 8)))
    lip = tube(P.MOTOR_TUBE_ID + 0.2, P.MOTOR_D + 1.0, P.MOTOR_TUBE_L - 2, P.MOTOR_TUBE_L)
    return t.union(lip)


def adapter():
    a = tube(P.ADAPTER_OD, P.ADAPTER_ID, 0, P.ADAPTER_L)
    for i in range(3):   # Schlitze zum Klemmen
        a = a.cut(box_from(-0.8, 0.8, 0, P.ADAPTER_OD, P.ADAPTER_L * 0.4, P.ADAPTER_L + 1).rotate((0, 0, 0), (0, 0, 1), 120 * i))
    return a


def motor():
    m = cyl(P.MOTOR_D, 0, P.MOTOR_L)
    nozzle = cq.Workplane("XY").circle(4.0).workplane(offset=6).circle(9.0).loft()
    return m.cut(nozzle)


def build(parts: Parts, pitch_deg=0.0, yaw_deg=0.0):
    """Kardan montiert; pitch_deg kippt das Motorrohr um x, yaw_deg den Innenrahmen um y (Darstellung)."""
    zr = P.TVC_RING_Z
    up = (0, 0, zr)
    piv = (0, 0, P.PIVOT_H)

    parts.add("Außenrahmen", outer_gimbal().translate(up), "printed", "tvc")
    s_out, h_out = servo("y")
    parts.add("Servo Außenrahmen W5652H", s_out.translate(up), "servo", "tvc")
    s_in, h_in = servo("x")

    inner_group = [("Innenrahmen", inner_gimbal(), "printed2"),
                   ("Servo Innenrahmen W5652H", s_in, "servo"),
                   ("Servohebel außen", h_out, "steel")]
    motor_group = [("Motorrohr", motor_tube(), "printed"),
                   ("Adapter 29→24", adapter().translate((0, 0, P.ADAPTER_Z[0] - zr)), "printed2"),
                   ("Motor TSP E12-0", motor().translate((0, 0, -zr)), "motor"),
                   ("Servohebel innen", h_in, "steel")]
    for name, shp, col in motor_group:
        shp = rot_about(shp, piv, (1, 0, 0), pitch_deg)
        shp = rot_about(shp, piv, (0, 1, 0), yaw_deg)
        parts.add(name, shp.translate(up), col, "tvc")
    for name, shp, col in inner_group:
        shp = rot_about(shp, piv, (0, 1, 0), yaw_deg)
        parts.add(name, shp.translate(up), col, "tvc")
