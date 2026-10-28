"""Modulbauweise Kartonaut 1 (Erstflug), Stand 2: Druckteile, Rumpf mit Bohrungen, Prüfungen, Masse, Bilder.

    MS_CONFIG=erstflug python cad/modular.py            # STL nach cad/export/modular/, Bilder nach docs/img/bauanleitung/
    MS_CONFIG=erstflug python cad/modular.py --no-render

Maße: cad/modular_params.py (nach Jans gebautem Kardan, 22.10.2026) und cad/params.py (Rohr, Kuppler, Platine, Spitze).
Der Kardan ist gebaut und hier nur als Hüllkörper dabei (Schubstangen-Kardan, nicht der aus tvc.py).
Bauanleitung: docs/Bauanleitung_Kartonaut1.md.
"""
import json
import math
import os
import sys
from pathlib import Path

os.environ.setdefault("MS_CONFIG", "erstflug")
import cadquery as cq
from cadquery import exporters

import params as P
import modular_params as M
from common import Parts, tube, cyl, box_from, cyl_between

HERE = Path(__file__).resolve().parent
EXPORT = HERE / "export" / "modular"
IMG = HERE.parent / "docs" / "img" / "bauanleitung"


def polar(r, phi_deg, z):
    a = math.radians(phi_deg)
    return (r * math.cos(a), r * math.sin(a), z)


def radial_bore(d, phi, z, r_out, r_in):
    return cyl_between(d, polar(r_out, phi, z), polar(r_in, phi, z))


def window(phi, w, z0, z1, r_in, r_out):
    """Fenster der Breite w (tangential) bei phi zwischen z0 und z1, schneidet r_in … r_out."""
    return box_from(-w / 2, w / 2, r_in, r_out, z0, z1).rotate((0, 0, 0), (0, 0, 1), phi - 90.0)


# --------------------------------------------------------------------------- Rumpf
def tube_with_holes(z0, z1, od, id_, holes, windows=()):
    t = tube(od, id_, z0, z1)
    ro, ri = od / 2 + 1, id_ / 2 - 3
    for d, phi, z in holes:
        if z0 < z < z1:
            t = t.cut(radial_bore(d, phi, z, ro, ri))
    for phi, w, a, b in windows:
        a, b = max(a, z0 - 1), min(b, z1 + 1)
        if b > a:
            t = t.cut(window(phi, w, a, b, ri, ro))
    return t


def hatch_windows():
    return [(hd["phi"], hd.get("w", M.HATCH_W), M.v_to_z(hd["v"][0]), M.v_to_z(hd["v"][1]))
            for hd in (M.HATCH_A1, M.HATCH_A2, M.HATCH_B)]


def tube_a():
    holes = [(M.SCREW_HOLE_PAPER, p, M.GIMBAL_SCREW_Z) for p in M.SCREW_PHI]
    holes += [(M.SCREW_HOLE_PAPER, p, M.J1_SCREW_Z) for p in M.SCREW_PHI]
    wins = [(phi, M.GIMBAL_WINDOW["w"], z0, z1) for phi, z0, z1 in servo_windows()]
    return tube_with_holes(*M.TUBE_A, M.TUBE_OD, M.TUBE_ID, holes, wins)


def tube_b():
    holes = [(M.SCREW_HOLE_PAPER, p, M.OLD_HOLES_B_Z) for p in M.SCREW_PHI]
    holes += [(M.SCREW_HOLE_PAPER, p, M.SPIGOT_B_SCREW_Z) for p in M.SCREW_PHI]
    sw = M.ARM_SCREW_SWITCH
    holes += [(sw["d"], sw["phi"] + 12.0, M.v_to_z(sw["v"]))]
    return tube_with_holes(*M.TUBE_B, M.TUBE_OD, M.TUBE_ID, holes, hatch_windows())


def tube_c():
    holes = [(M.SCREW_HOLE_PAPER, p, M.SPIGOT_C_SCREW_Z) for p in M.SPIGOT_C_PHI]
    holes += [(M.SHEAR_PIN_D, p, M.SHEAR_PIN_Z) for p in M.SHEAR_PIN_PHI]
    return tube_with_holes(*M.TUBE_C, M.TUBE_OD, M.TUBE_ID, holes)


def coupler_j1():
    holes = [(M.SCREW_HOLE_PAPER, p, M.J1_SCREW_Z) for p in M.SCREW_PHI]
    return tube_with_holes(*M.J1_COUPLER, P.COUPLER_OD, P.COUPLER_ID, holes)


def j1_ring():
    """Schraubring im Kuppler J1 (dort verklebt): 4 Augen mit Einschmelzmuttern für die Schrauben durch Rohr A."""
    z0, z1 = M.J1_RING["z"]
    r = tube(M.J1_RING["od"], M.J1_RING["id"], z0, z1)
    for phi in M.SCREW_PHI:
        r = r.union(cyl_between(9.0, polar(M.J1_RING["id"] / 2 - 2.5, phi, M.J1_SCREW_Z), polar(M.J1_RING["od"] / 2 - 0.5, phi, M.J1_SCREW_Z))
                    .intersect(cyl(M.J1_RING["od"], z0, z1)))
        r = r.cut(radial_bore(3.3, phi, M.J1_SCREW_Z, M.J1_RING["od"] / 2 + 1, M.J1_RING["id"] / 2 - 4))
        r = r.cut(nut_pocket(phi, M.J1_SCREW_Z, M.J1_RING["id"] / 2 - 2.5))
    return r


# --------------------------------------------------------------------------- Schlitten mit Spant (ein Druckteil)
def bosses(shape, z, r_in, r_out, z_top, d=M.BOSS_D, phis=M.SCREW_PHI):
    for phi in phis:
        b = cyl_between(d, polar(r_in, phi, z), polar(r_out, phi, z))
        b = b.union(box_from(-d / 2, d / 2, r_in, r_out, min(z, z_top), max(z, z_top)).rotate((0, 0, 0), (0, 0, 1), phi - 90))
        shape = shape.union(b)
        shape = shape.cut(radial_bore(3.3, phi, z, r_out + 1, r_in - 1))
        shape = shape.cut(nut_pocket(phi, z, r_in))
    return shape


def nut_pocket(phi, z, r_in):
    """Sechskant-Tasche für eine M3-Mutter am inneren Ende einer Radialbohrung, offen nach innen (Mutter von innen eindrücken)."""
    n = M.NUT
    across = (n["sw"] + n["clear"]) / math.cos(math.pi / 6)
    pocket = (cq.Workplane("YZ").workplane(offset=r_in - 1.0).polygon(6, across).extrude(n["h"] + 1.2))
    return pocket.translate((0, 0, z)).rotate((0, 0, 0), (0, 0, 1), phi)


def sled():
    v0 = M.BOARD_V0_Z
    bw = M.BOARD_W / 2
    yb = -M.BOARD_T / 2
    b0, b1 = M.BAND_Z
    sb, sc = M.SPIGOT_B, M.SPIGOT_C
    # Band: außen ein 5 mm hoher Rand (sichtbar, liegt auf Rohr B), innen die Spantplatte M.PLATE_T oben auf der Druckseite.
    # Zapfen nach unten in B, Zapfen nach oben in C (Wand M.SPIGOT_WALL)
    p0 = b1 - M.PLATE_T
    s = tube(M.BAND_OD, sb["id"], b0, b1).union(cyl(sb["id"] + 0.2, p0, b1))
    s = s.union(tube(sb["od"], sb["id"], *sb["z"])).union(tube(sc["od"], sc["id"], *sc["z"]))
    s = s.cut(tube(sb["od"] + 2, sb["od"] - 1.2, sb["z"][0] - 0.1, sb["z"][0] + 0.8))      # Einführfasen
    s = s.cut(tube(sc["od"] + 2, sc["od"] - 1.2, sc["z"][1] - 0.8, sc["z"][1] + 0.1))
    s = bosses(s, M.SPIGOT_B_SCREW_Z, sb["id"] / 2 - 4.5, sb["od"] / 2 - 0.5, b0)     # Stand 2c: Augen nach innen, 
    s = bosses(s, M.SPIGOT_C_SCREW_Z, sc["id"] / 2 - 4.0, sc["od"] / 2 - 0.5, b1, phis=M.SPIGOT_C_PHI)   # ≥ 2,9 mm hinter der Mutter
    # Ringschraube M4 (Schockschnur) und Kabelverschraubung für das Servo der CO₂-Auslösung
    s = s.cut(cyl(4.3, b0 - 1, b1 + 1, 0, -16))
    s = s.cut(cyl(6.0, b0 - 1, b1 + 1, *M.SERVO_GLAND))
    # Träger: U-Profil (Boden + zwei Wände) bis unter die Spantplatte; im Zapfen läuft der Boden als Sehne bis an die
    # Zapfenwand (statt des vollen Klotzes von Stand 2b, 11,5 cm³)
    tz0, tz1 = M.DISC_Z[1], p0
    s = s.union(box_from(-bw, bw, M.TRAY_FLOOR_Y, M.TRAY_FLOOR_Y + M.TRAY_WALL, tz0, tz1))
    walls = box_from(-bw, -bw + M.TRAY_WALL, M.TRAY_FLOOR_Y, yb, tz0, tz1)
    s = s.union(walls).union(walls.mirror("YZ"))
    s = s.union(box_from(-sb["id"] / 2, sb["id"] / 2, M.TRAY_FLOOR_Y, M.TRAY_FLOOR_Y + M.TRAY_WALL, sb["z"][0], p0)
                .intersect(cyl(sb["id"] + 1, sb["z"][0], p0)))
    for (u, v) in M.BOARD_HOLES:
        z = v0 + v
        s = s.union(box_from(u - M.POST_D / 2, u + M.POST_D / 2, M.TRAY_FLOOR_Y, yb, z - 4.0, z + 4.0))
        s = s.union(box_from(-bw if u < 0 else u, u if u < 0 else bw, M.TRAY_FLOOR_Y, yb, z - 4.0, z + 4.0))
        s = s.cut(cyl_between(M.TAP_HOLE, (u, yb + 0.5, z), (u, yb - 9.0, z)))
    end = box_from(-bw, bw, M.TRAY_FLOOR_Y, yb, tz0, tz0 + 3.0).cut(box_from(-12, 12, M.TRAY_FLOOR_Y + 3, yb + 1, tz0 - 1, tz0 + 4))
    s = s.union(end)
    for (x, y) in M.TRAY_TO_DISC:
        s = s.union(cyl_between(8.0, (x, y, tz0), (x, y, tz0 + 8.0)))
        s = s.cut(cyl_between(M.TAP_HOLE, (x, y, tz0 - 1), (x, y, tz0 + 7.0)))
    v_sep = (M.BAT2S["v0"] + M.BAT2S["l"] + M.BAT1S["v0"]) / 2
    s = s.union(box_from(-bw, bw, M.TRAY_FLOOR_Y, M.TRAY_FLOOR_Y + 5.0, v0 + v_sep - 1, v0 + v_sep + 1))
    for bat in (M.BAT2S, M.BAT1S):
        vm = bat["v0"] + bat["l"] / 2
        for dv in (-bat["l"] / 4, bat["l"] / 4):
            s = s.cut(box_from(-M.STRAP_SLOT[1] / 2, M.STRAP_SLOT[1] / 2, M.TRAY_FLOOR_Y - 1, M.TRAY_FLOOR_Y + 3,
                               v0 + vm + dv - M.STRAP_SLOT[0] / 2, v0 + vm + dv + M.STRAP_SLOT[0] / 2))
    for vm, ln in ((22.0, 22.0), (50.0, 22.0), (84.0, 22.0), (106.0, 14.0)):
        s = s.cut(box_from(-bw - 1, bw + 1, M.TRAY_FLOOR_Y + 4, yb - 3, v0 + vm - ln / 2, v0 + vm + ln / 2))
    for (u, v) in M.PANEL_COLS:
        s = s.cut(cyl_between(3.3, (u, M.TRAY_FLOOR_Y - 1, v0 + v), (u, M.TRAY_FLOOR_Y + 3, v0 + v)))
    # Stand 2c: Fenster im Boden unter den Akkus, zwischen den Klettschlitzen und Fachenden
    for v_a, v_b in floor_windows():
        s = s.cut(box_from(-M.FLOOR_WINDOW_W / 2, M.FLOOR_WINDOW_W / 2, M.TRAY_FLOOR_Y - 1, M.TRAY_FLOOR_Y + M.TRAY_WALL + 0.5,
                           v0 + v_a, v0 + v_b))
    for (u, v) in M.PANEL_COLS:      # Auflage der Schalterbrett-Säulen bleibt voll
        s = s.union(cyl_between(M.PANEL_COL_D + 3.0, (u, M.TRAY_FLOOR_Y, v0 + v), (u, M.TRAY_FLOOR_Y + M.TRAY_WALL, v0 + v)))
        s = s.cut(cyl_between(3.3, (u, M.TRAY_FLOOR_Y - 1, v0 + v), (u, M.TRAY_FLOOR_Y + 3, v0 + v)))
    # Stand 2d: Fenster im Zapfen B zwischen den Augen, Bodenfenster neben den Akkus
    for w, sp in ((M.SPIGOT_B_WINDOWS, sb), (M.SPIGOT_C_WINDOWS, sc)):
        for a, b in w["phi"]:
            wedge = (cq.Workplane("XY").workplane(offset=w["z"][0])
                     .polyline([(0, 0)] + [polar(45.0, a + (b - a) * i / 8, 0)[:2] for i in range(9)]).close()
                     .extrude(w["z"][1] - w["z"][0]))
            s = s.cut(wedge.cut(cyl(sp["id"] - 0.4, w["z"][0] - 1, w["z"][1] + 1)))
    sw = M.SIDE_WINDOWS
    for va, vb in sw["v"]:
        for x0, x1 in ((sw["x"][0], sw["x"][1]), (-sw["x"][1], -sw["x"][0])):
            s = s.cut(box_from(x0, x1, M.TRAY_FLOOR_Y - 1, M.TRAY_FLOOR_Y + M.TRAY_WALL + 0.5, v0 + va, v0 + vb))
    # GPS-Halter (Stand 2d): zwei Leisten quer an den y-Enden des Stapels, je mit Auflagekante unter der Modulplatine
    g, r = M.GPS, M.GPS_RAIL
    zb = g["z_top"] - g["h"]
    for y0, y1, ly0, ly1 in ((g["y"][0] - r["t"], g["y"][0], g["y"][0], g["y"][0] + r["lip"]),
                             (g["y"][1], g["y"][1] + r["t"], g["y"][1] - r["lip"], g["y"][1])):
        s = s.union(box_from(-r["x"], r["x"], y0, y1, zb - r["lip_t"], p0))
        s = s.union(box_from(-r["x"], r["x"], ly0, ly1, zb - r["lip_t"], zb))
    return s


def floor_windows():
    """v-Bereiche der Bodenfenster: je Akkufach die Stücke zwischen Fachende und den beiden Klettschlitzen."""
    out, g, half = [], M.FLOOR_WINDOW_GAP, M.STRAP_SLOT[0] / 2
    for bat in (M.BAT2S, M.BAT1S):
        vm = bat["v0"] + bat["l"] / 2
        cuts = [bat["v0"] + g, vm - bat["l"] / 4 - half - g, vm - bat["l"] / 4 + half + g, vm + bat["l"] / 4 - half - g,
                vm + bat["l"] / 4 + half + g, bat["v0"] + bat["l"] - g]
        for a, b in zip(cuts[0::2], cuts[1::2]):
            if b - a > 4.0:
                out.append((a, b))
    return out


def lower_disc():
    z0, z1 = M.DISC_Z
    d = cyl(M.DISC_OD, z0, z1).cut(cyl(M.DISC_CABLE_D, z0 - 1, z1 + 1, 0, -4.0))
    x0, x1, y0, y1 = M.DISC_PLUG_WINDOW
    d = d.cut(box_from(x0, x1, y0, y1, z0 - 1, z1 + 1))
    for a in M.DISC_LIGHT_PHI:
        d = d.cut(cyl(M.DISC_LIGHT_D, z0 - 1, z1 + 1, M.DISC_LIGHT_R * math.cos(math.radians(a)), M.DISC_LIGHT_R * math.sin(math.radians(a))))
    for (x, y) in M.TRAY_TO_DISC:
        d = d.cut(cyl(3.4, z0 - 1, z1 + 1, x, y))
    return d.cut(box_from(M.DISC_OD / 2 - 2.5, M.DISC_OD / 2 + 1, -1.0, 1.0, z0 - 1, z1 + 1))   # Marke 0°


def switch_panel():
    v0 = M.BOARD_V0_Z
    va, vb = M.HATCH_B["v"]
    plate = box_from(-M.PANEL_W / 2, M.PANEL_W / 2, M.PANEL_Y[0], M.PANEL_Y[1], v0 + va + 1, v0 + vb - 1)
    for name, u, a, b, w in M.PANEL_PARTS:
        plate = plate.cut(box_from(u - w / 2 - 0.2, u + w / 2 + 0.2, M.PANEL_Y[0] - 1, M.PANEL_Y[1] + 1, v0 + a, v0 + b))
    for (u, v) in M.PANEL_COLS:
        col = cyl_between(M.PANEL_COL_D, (u, M.PANEL_Y[1] - 0.5, v0 + v), (u, M.TRAY_FLOOR_Y, v0 + v))
        col = col.cut(cyl_between(M.TAP_HOLE, (u, M.TRAY_FLOOR_Y + 0.5, v0 + v), (u, M.TRAY_FLOOR_Y - 7.0, v0 + v)))
        plate = plate.union(col)
    return plate


def _gimbal_loc():
    return cq.Location(cq.Vector(0, 0, M.GIMBAL_BASE_Z), cq.Vector(0, 0, 1), M.GIMBAL_ROT_DEG)


def servo_geometry():
    """Je Servo: Körper, Hebel, Draht (nach Jans Fotos) im Bezugssystem der Druckdatei, dazu die Lage der Welle."""
    out = []
    L, H, T = M.SERVO_BODY
    for name, (cx, cy, cz), (rx, ry), s_tan, phi_t, r_t in M.SERVOS:
        tx, ty = -ry, rx
        rad = math.hypot(cx, cy)
        ang = math.degrees(math.atan2(ry, rx)) - 90.0
        body = cq.Workplane("XY").box(L, T, H).rotate((0, 0, 0), (0, 0, 1), ang).translate((cx, cy, cz))
        r_face = rad + T / 2
        sx, sy = rx * r_face + tx * s_tan, ry * r_face + ty * s_tan
        z0 = M.SERVO_SHAFT_Z
        p0, p1 = (sx, sy, z0), (sx + rx * 2.5, sy + ry * 2.5, z0)
        hub = cyl_between(6.0, p0, p1)
        hm = (p0[0] + rx * 1.25, p0[1] + ry * 1.25)
        arm = cyl_between(4.5, (hm[0], hm[1], z0), (hm[0], hm[1], z0 + M.HORN_R))
        tip = (hm[0] - rx * 1.5, hm[1] - ry * 1.5, z0 + M.HORN_R)      # Draht steckt von innen im oberen Hebelloch
        # Bogen innen an der Wand vom Hebel zum Zielwinkel, dann senkrecht hinunter, dann radial zum Stift
        a0 = math.degrees(math.atan2(tip[1], tip[0])) % 360
        a1 = phi_t % 360
        da = ((a1 - a0 + 180) % 360) - 180
        R = M.WIRE_ARC_R
        pts = [tip, (R * math.cos(math.radians(a0)), R * math.sin(math.radians(a0)), tip[2])]
        n = 10
        for k in range(1, n + 1):
            a = math.radians(a0 + da * k / n)
            pts.append((R * math.cos(a), R * math.sin(a), tip[2]))
        a = math.radians(a1)
        pts.append((R * math.cos(a), R * math.sin(a), M.WIRE_PIN_Z))
        pin_in = ((r_t - 2.0) * math.cos(a), (r_t - 2.0) * math.sin(a), M.WIRE_PIN_Z)
        pts.append(pin_in)
        wire = None
        for q0, q1 in zip(pts[:-1], pts[1:]):
            seg = cyl_between(M.WIRE_D, q0, q1).union(cq.Workplane("XY").sphere(M.WIRE_D / 2).translate(q1))
            wire = seg if wire is None else wire.union(seg)
        washer = cyl_between(6.0, ((r_t + 2.5) * math.cos(a), (r_t + 2.5) * math.sin(a), M.WIRE_PIN_Z),
                             ((r_t + 0.5) * math.cos(a), (r_t + 0.5) * math.sin(a), M.WIRE_PIN_Z))
        out.append(dict(name=name, body=body, horn=hub.union(arm), wire=wire.union(washer), shaft=(sx, sy, z0)))
    return out


def servo_linkage():
    loc = _gimbal_loc()
    out = []
    for g in servo_geometry():
        out.append((f"Servo {g['name']}", g["body"].val().moved(loc), "servo"))
        out.append((f"Servohebel {g['name']}", g["horn"].val().moved(loc), "printed2"))
        out.append((f"Drahtbügel {g['name']}", g["wire"].val().moved(loc), "steel"))
    return out


def servo_windows():
    """Lage der Servofenster im Rohr A aus der Wellenlage: (phi in Rohrwinkeln, z0, z1)."""
    out = []
    for g in servo_geometry():
        sx, sy, sz = g["shaft"]
        phi = (math.degrees(math.atan2(sy, sx)) + M.GIMBAL_ROT_DEG) % 360
        out.append((phi, M.GIMBAL_WINDOW["z"][0], M.GIMBAL_WINDOW["z"][1]))
    return out


# --------------------------------------------------------------------------- Zusammenbau
def build_all():
    import airframe
    parts = Parts()
    parts.add("Rohr A 125 (Kardan, gebaut)", tube_a(), "tube", "rumpf")
    parts.add("Rohr B 176 (Avionik)", tube_b(), "tube", "rumpf")
    parts.add("Rohr C (Bergung)", tube_c(), "tube", "rumpf")
    parts.add("Kuppler J1 75 (in B verklebt)", coupler_j1(), "coupler", "rumpf")
    parts.add("Schraubring J1", j1_ring(), "printed", "rumpf")
    parts.add("Kardan (gebaut, Hüllkörper)", cyl(P.COUPLER_ID - 2, 3.0, M.GIMBAL_TOP_Z).cut(cyl(24.0, 2.0, M.GIMBAL_TOP_Z + 1)), "printed2", "antrieb")
    parts.add("Motor TSP E12-0", cyl(P.MOTOR_D, 0.0, M.MOTOR_L), "motor", "antrieb")
    for name, shape, col in servo_linkage():
        parts.add(name + " (schematisch)", shape, col, "antrieb")
    parts.add("Schlitten mit Spant", sled(), "printed2", "avionik")
    parts.add("Untere Scheibe", lower_disc(), "printed", "avionik")
    parts.add("Schalterbrett", switch_panel(), "printed", "avionik")
    v0 = M.BOARD_V0_Z
    for name, u, a, b, w in M.PANEL_PARTS:
        parts.add(name, box_from(u - w / 2, u + w / 2, -34.6, M.PANEL_Y[1] + 4.0, v0 + a, v0 + b), "steel", "avionik")
    board = box_from(-M.BOARD_W / 2, M.BOARD_W / 2, -M.BOARD_T / 2, M.BOARD_T / 2, v0, v0 + M.BOARD_L).edges("|Y").fillet(2.0)
    parts.add("Platine rev B1", board, "board", "avionik")
    t = P.TEENSY
    parts.add("Teensy 4.1", box_from(t["u0"], t["u1"], M.BOARD_T / 2, M.BOARD_T / 2 + 12.0, v0 + t["v0"], v0 + t["v1"]), "teensy", "avionik")
    for pname, u in M.PLUGS_TVC_END:
        parts.add(f"Stecker {pname}", box_from(u - 3.0, u + 3.0, M.BOARD_T / 2, M.BOARD_T / 2 + 7.0, v0 - M.PLUG_REACH, v0), "steel", "avionik")
    for nm, bat in (("Akku 2S", M.BAT2S), ("Akku 1S", M.BAT1S)):
        y0 = M.TRAY_FLOOR_Y + M.TRAY_WALL + 0.3
        parts.add(nm, box_from(-bat["w"] / 2, bat["w"] / 2, y0, y0 + bat["h"], v0 + bat["v0"], v0 + bat["v0"] + bat["l"]), "battery", "avionik")
    g = M.GPS
    gb, gp = M.GPS_BOARD, M.GPS_PATCH
    zb, ym = g["z_top"] - g["h"], sum(g["y"]) / 2
    gps = box_from(-gb["w"] / 2, gb["w"] / 2, g["y"][0], g["y"][1], zb, zb + gb["h"])
    gps = gps.union(box_from(-gp["w"] / 2, gp["w"] / 2, ym - gp["l"] / 2, ym + gp["l"] / 2, zb + gb["h"], g["z_top"]))
    parts.add("GPS-Modul (Patch nach oben)", gps, "teensy", "avionik")
    lh = M.LORA_HELIX
    parts.add("LoRa-Wendel 433 MHz", cyl(lh["d"], lh["z_top"] - lh["l"], lh["z_top"], lh["x"], lh["y"]), "steel", "avionik")
    c = M.CO2
    z0 = M.CO2_Z0
    co2 = cyl_between(c["d"], (-c["l"] / 2, 4.0, z0 + c["d"] / 2), (c["l"] / 2, 4.0, z0 + c["d"] / 2))
    co2 = co2.union(box_from(-12, 12, -24, -6, z0, z0 + 22))      # Servo und Anstechdorn [Annahme]
    parts.add("CO₂-Modul (Kapsel quer, Servo-Auslösung)", co2, "steel", "bergung")
    parts.add("Fallschirm (gepackt 100 × Ø 70)", cyl(M.CHUTE["d"], *M.CHUTE_Z).edges().fillet(8.0), "chute", "bergung")
    zs = M.NOSE_SHOULDER_Z0
    parts.add("Spitze Schulter (Klima)", tube(P.COUPLER_OD, P.COUPLER_ID, *M.NOSE_COUPLER_Z), "coupler", "spitze")
    parts.add("Spitze Holzplatte mit Haken (Klima)", cyl(M.TUBE_ID - 1.0, M.NOSE_COUPLER_Z[1], M.NOSE_COUPLER_Z[1] + 4), "coupler", "spitze")
    assert abs(P.NOSE_BASE_Z - M.TOP_Z) >= 0       # airframe.nose_cone() setzt bei P.NOSE_BASE_Z an, hier verschoben
    parts.add("Spitze Klima 8539", airframe.nose_cone().translate((0, 0, M.TOP_Z - P.NOSE_BASE_Z)), "nose", "spitze")
    return parts


def check(parts):
    by = {n: s for n, s, _, _ in parts}

    def vol(a, b):
        try:
            return by[a].intersect(by[b]).Volume()
        except Exception:
            return 0.0
    inner = ["Schlitten mit Spant", "Untere Scheibe", "Schalterbrett", "Platine rev B1", "Teensy 4.1", "Akku 2S", "Akku 1S",
             "GPS-Modul (Patch nach oben)", "LoRa-Wendel 433 MHz", "Schraubring J1", "CO₂-Modul (Kapsel quer, Servo-Auslösung)",
             "Fallschirm (gepackt 100 × Ø 70)"] + [n for n in by if n.startswith("Stecker ")] + [p[0] for p in M.PANEL_PARTS]
    shells = ["Rohr A 125 (Kardan, gebaut)", "Rohr B 176 (Avionik)", "Rohr C (Bergung)", "Kuppler J1 75 (in B verklebt)"]
    pairs = [(a, b) for a in inner for b in shells if not (a == "Schraubring J1" and b.startswith("Kuppler"))]
    loose = ["Platine rev B1", "Teensy 4.1", "Akku 2S", "Akku 1S", "GPS-Modul (Patch nach oben)", "LoRa-Wendel 433 MHz"] + \
            [n for n in by if n.startswith("Stecker ")] + [p[0] for p in M.PANEL_PARTS]
    pairs += [(a, b) for a in ("Schlitten mit Spant", "Untere Scheibe", "Schalterbrett") for b in loose]
    pairs += [("GPS-Modul (Patch nach oben)", n) for n in by if n.startswith("Stecker ") or n in ("Platine rev B1", "Teensy 4.1")]
    for n in by:
        if n.startswith(("Servo W5652H", "Servohebel")):        # Drahtbügel nur schematisch, Führung am echten Teil anders
            pairs += [(n, "Rohr A 125 (Kardan, gebaut)"), (n, "Kuppler J1 75 (in B verklebt)"), (n, "Schraubring J1"), (n, "Motor TSP E12-0")]
    pairs += [("Schraubring J1", "Kardan (gebaut, Hüllkörper)"), ("Untere Scheibe", "Kardan (gebaut, Hüllkörper)"),
              ("CO₂-Modul (Kapsel quer, Servo-Auslösung)", "Schlitten mit Spant"),
              ("Fallschirm (gepackt 100 × Ø 70)", "CO₂-Modul (Kapsel quer, Servo-Auslösung)"),
              ("Fallschirm (gepackt 100 × Ø 70)", "Spitze Schulter (Klima)")]
    bad = [f"{a} ∩ {b}: {v:.1f} mm³" for a, b in pairs if a in by and b in by and (v := vol(a, b)) > 0.5]
    return bad, [n for n in inner if n not in by]


def export(parts):
    EXPORT.mkdir(parents=True, exist_ok=True)
    for f in EXPORT.glob("*.st*"):
        if not f.name.startswith("Kartonaut1"):
            f.unlink()
    by = {n: s for n, s, _, _ in parts}
    rows = []
    for key, fn in (("Schlitten mit Spant", "Schlitten_mit_Spant"), ("Untere Scheibe", "Untere_Scheibe"),
                    ("Schalterbrett", "Schalterbrett"), ("Schraubring J1", "Schraubring_J1")):
        shp = cq.Workplane().add(by[key])
        exporters.export(shp, str(EXPORT / f"{fn}.stl"), tolerance=0.02, angularTolerance=0.1)
        exporters.export(shp, str(EXPORT / f"{fn}.step"))
        v = by[key].Volume() / 1000
        shell = min(v, by[key].Area() / 100 * M.PRINT_SHELL / 10)     # cm² × cm
        g_sl = M.PRINT_RHO * (shell + M.PRINT_INFILL * (v - shell))
        rows.append({"teil": key, "datei": f"cad/export/modular/{fn}.stl", "cm3": round(v, 1),
                     "g_75": round(v * M.PRINT_RHO * M.PRINT_FILL, 1), "g": round(g_sl, 1)})
    return rows


def asbuilt_gimbal():
    """Die gedruckten Kardanteile (Dreiecksnetze aus den Blender-Dateien) an ihrer Lage im Rohr A. Nur Netz: für Bild und GLB."""
    from OCP.RWStl import RWStl
    from OCP.BRep import BRep_Builder
    from OCP.TopoDS import TopoDS_Face
    from OCP.Message import Message_ProgressRange
    out = []
    loc = cq.Location(cq.Vector(0, 0, M.GIMBAL_BASE_Z), cq.Vector(0, 0, 1), M.GIMBAL_ROT_DEG)
    for fn, col in zip(M.GIMBAL_STL, ((0.45, 0.6, 0.35), (0.6, 0.45, 0.4), (0.35, 0.45, 0.75))):
        f = HERE / "export" / "asbuilt" / fn
        if not f.exists():
            continue
        tri = RWStl.ReadFile_s(str(f), Message_ProgressRange())
        face = TopoDS_Face()
        BRep_Builder().MakeFace(face, tri)
        out.append((f"Kardan gedruckt: {fn[:-4]}", cq.Shape.cast(face).moved(loc), col))
    return out


def export_assembly(parts):
    """Ganze Rakete als farbige Baugruppe: STEP (FreeCAD, Fusion) und GLB (Windows-3D-Viewer, Doppelklick). Rohre halb durchsichtig."""
    assy = cq.Assembly(name="Kartonaut1_Stand2b")
    mesh = asbuilt_gimbal()
    for ext in ("step", "glb"):
        assy = cq.Assembly(name="Kartonaut1_Stand2b")
        for i, (name, shape, col, grp) in enumerate(parts):
            if ext == "glb" and mesh and name.startswith("Kardan (gebaut"):
                continue                                   # im GLB steht der echte Kardan statt des Hüllkörpers
            r, g, b = P.COLORS.get(col, (0.7, 0.7, 0.7))
            a = 0.35 if grp == "rumpf" and name.startswith(("Rohr", "Kuppler")) else 1.0
            assy.add(shape, name=f"{i:02d} {name}".replace("/", "-"), color=cq.Color(r, g, b, a))
        if ext == "glb":
            for name, shape, (r, g, b) in mesh:
                assy.add(shape, name=name, color=cq.Color(r, g, b, 1.0))
        assy.save(str(EXPORT / f"Kartonaut1_Stand2b.{ext}"))


def renders(parts):
    sys.path.insert(0, str(HERE))
    import build as B
    IMG.mkdir(parents=True, exist_ok=True)
    for f in IMG.glob("modular_*.png"):
        f.unlink()
    jobs = [("modular_section", "section", dict(cut=(0, 60, -60, 60, -100, 1100))),
            ("modular_avionik", "avionics", dict(only_groups=["avionik"])),
            ("modular_avionik_rumpf", "hatch_a_iso", dict(only_groups=["avionik", "rumpf"], cut=(-60, 60, -60, 60, 330, 1000))),
            ("modular_luke_b", "hatch_b_iso", dict(only_groups=["avionik", "rumpf"], cut=(-60, 60, -60, 60, 330, 1000)))]
    for name, view, kw in jobs:
        d = B.write_render_manifest(parts, name, **kw)
        B.render(d, IMG / f"{name}.png", view)


def main():
    parts = build_all()
    bad, missing = check(parts)
    print(f"{len(parts)} Teile")
    for b in bad:
        print("  KOLLISION", b)
    for m in missing:
        print("  FEHLT", m)
    if not bad and not missing:
        print("  Prüfung frei: Schlitten, Platine, Stecker, Akkus, GPS, LoRa, Schalterbrett, Schraubring, CO₂-Modul, Schirm gegen Rohre, Kuppler und einander")
    for phi, z0, z1 in servo_windows():
        print(f"  Servofenster laut Druckdatei: {phi:.0f}° ab der Längslinie, z {z0:.0f} … {z1:.0f}")
    rows = export(parts)
    printed = sum(r["g"] for r in rows)
    for r in rows:
        print(f"  {r['datei']}  {r['cm3']} cm³  ≈ {r['g']:.0f} g")
    total = M.mass_estimate(printed)
    tubes = {k: round(M.tube_mass(*z), 1) for k, z in (("A", M.TUBE_A), ("B", M.TUBE_B), ("C", M.TUBE_C))}
    print(f"  Rohre {tubes}, Druckteile {printed:.0f} g (Slicer-Modell), Überschlag Start ≈ {total:.0f} g ohne LoRa, CO₂-Servo und "
          f"Schalterbrett-Bauteile (maßgeblich: python cad/mass_stand2b.py), Länge {M.NOSE_TIP_Z:.0f} mm")
    (EXPORT / "masses.json").write_text(json.dumps({"druckteile": rows, "druckteile_g": round(printed, 1), "rohre_g": tubes,
                                                    "start_g": round(total, 1), "laenge_mm": M.NOSE_TIP_Z},
                                                   indent=1, ensure_ascii=False), encoding="utf-8")
    export_assembly(parts)
    if "--no-render" not in sys.argv:
        renders(parts)
    return 1 if bad or missing else 0


if __name__ == "__main__":
    sys.exit(main())
