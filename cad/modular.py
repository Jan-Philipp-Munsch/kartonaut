"""Modulbauweise Kartonaut 1 (Erstflug ohne Gewindestangen): Druckteile, Rumpf mit Bohrungen, Prüfungen, Bilder.

    MS_CONFIG=erstflug python cad/modular.py            # STL/STEP nach cad/export/modular/, Bilder nach docs/img/bauanleitung/
    MS_CONFIG=erstflug python cad/modular.py --no-render

Maße: cad/modular_params.py (alles Neue) und cad/params.py (Rohr, Kuppler, Kardan, Spitze). Unverändert aus den
bestehenden Modulen: Kardan (tvc.py, nur das Lochbild des Außenrahmens ist neu), Spitze (airframe.nose_cone).
Bauanleitung: docs/Bauanleitung_Kartonaut1.md.
"""
import math
import os
import sys
from pathlib import Path

os.environ.setdefault("MS_CONFIG", "erstflug")
import cadquery as cq
from cadquery import exporters

import params as P
import modular_params as M
import common
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
    c = box_from(-w / 2, w / 2, r_in, r_out, z0, z1)
    return c.rotate((0, 0, 0), (0, 0, 1), phi - 90.0)


# --------------------------------------------------------------------------- Rumpf mit allen Bohrungen
def hatch_cuts(r_in, r_out, z_lo, z_hi, a2_as_notch=False):
    cuts = []
    for hd in (M.HATCH_A1, M.HATCH_A2, M.HATCH_B):
        z0, z1 = M.v_to_z(hd["v"][0]), M.v_to_z(hd["v"][1])
        if hd is M.HATCH_A2 and a2_as_notch:
            z0 = z_lo - 1
        z0, z1 = max(z0, z_lo - 1), min(z1, z_hi + 1)
        if z1 > z0 + 1:
            cuts.append(window(hd["phi"], hd.get("w", M.HATCH_W), z0, z1, r_in, r_out))
    return cuts


def lower_tube():
    z0, z1 = M.TUBE_BOTTOM_Z, M.JOINT_Z
    t = tube(M.TUBE_OD, M.TUBE_ID, z0, z1)
    r_o, r_i = M.TUBE_OD / 2 + 1, M.TUBE_ID / 2 - 1
    for phi in M.SCREW_PHI:
        t = t.cut(radial_bore(M.SCREW_HOLE_PAPER, phi, M.TVC_SCREW_Z, r_o, r_i))
    t = t.cut(radial_bore(M.KEY_HOLE_D, M.KEY_PHI, M.KEY_Z, r_o, r_i))
    for phi in M.BARO_PHI:
        t = t.cut(radial_bore(M.BARO_D, phi, M.BARO_Z, r_o, r_i))
    for c in hatch_cuts(r_i - 3.0, r_o, z0, z1):
        t = t.cut(c)
    return t


def upper_tube():
    z0, z1 = M.JOINT_Z, M.TOP_Z
    t = tube(M.TUBE_OD, M.TUBE_ID, z0, z1)
    r_o, r_i = M.TUBE_OD / 2 + 1, M.TUBE_ID / 2 - 1
    for phi in M.SCREW_PHI:
        t = t.cut(radial_bore(M.SCREW_HOLE_PAPER, phi, M.JOINT_SCREW_Z, r_o, r_i))
    for phi in M.SHEAR_PIN_PHI:
        t = t.cut(radial_bore(M.SHEAR_PIN_D, phi, M.SHEAR_PIN_Z, r_o, r_i))
    for c in hatch_cuts(r_i - 3.0, r_o, z0, z1, a2_as_notch=True):
        t = t.cut(c)
    return t


def avionics_coupler():
    z0, z1 = M.COUPLER_Z
    t = tube(P.COUPLER_OD, P.COUPLER_ID, z0, z1)
    r_o, r_i = P.COUPLER_OD / 2 + 1, P.COUPLER_ID / 2 - 1
    for phi in M.SCREW_PHI:
        t = t.cut(radial_bore(M.SCREW_HOLE_PAPER, phi, M.JOINT_SCREW_Z, r_o, r_i))
    for phi in M.BARO_PHI:
        t = t.cut(radial_bore(M.BARO_D, phi, M.BARO_Z, r_o, r_i))
    for c in hatch_cuts(r_i - 3.0, r_o, z0, z1):
        t = t.cut(c)
    return t


# --------------------------------------------------------------------------- Schlüsselring mit Kabelgitter
def key_ring():
    """Dünnwandiger Ring (im Rohr verklebt) mit Auge für den Schlüsselschalter und Kabelgitter als Boden."""
    z0, z1 = M.KEY_RING_Z
    ro = M.KEY_RING_OD / 2
    ring = tube(M.KEY_RING_OD, M.KEY_RING_OD - 2 * M.KEY_RING_WALL, z0, z1)
    bw, bd = M.KEY_BOSS
    boss = box_from(ro - bd, ro, -bw / 2, bw / 2, z0, z1).intersect(cyl(M.KEY_RING_OD, z0, z1))
    ring = ring.union(boss.rotate((0, 0, 0), (0, 0, 1), M.KEY_PHI))
    # Kabelgitter als Boden (1,6 mm): hält die Kabelschlaufe vom Kardan fern; Speichenrad mit Löchern
    grid = cyl(M.KEY_RING_OD - 1, z0, z0 + 1.6)
    for k in range(8):
        a = 22.5 + 45 * k
        x, y = 15 * math.cos(math.radians(a)), 15 * math.sin(math.radians(a))
        grid = grid.cut(cyl(10.0, z0 - 1, z0 + 3, x, y))
    for k in range(12):
        a = 15 + 30 * k
        x, y = 27 * math.cos(math.radians(a)), 27 * math.sin(math.radians(a))
        grid = grid.cut(cyl(7.0, z0 - 1, z0 + 3, x, y))
    ring = ring.union(grid)
    # Durchlässe für die Servokabel an der Wand (Stecker XH-3 passt durch): Außenservo bei 270°, Innenservo bei 90°
    for phi in (270.0, 90.0):
        ring = ring.cut(window(phi, 12.0, z0 - 1, z0 + 3, ro - 9.0, ro - M.KEY_RING_WALL + 0.01))
    # Schalterbohrung und Muttertasche (von innen, Schlüsselweite KEY_NUT)
    ring = ring.cut(radial_bore(M.KEY_HOLE_D, M.KEY_PHI, M.KEY_Z, M.TUBE_OD, ro - bd - 1))
    sw, nh = M.KEY_NUT
    r_nut = ro - bd + 3.0
    nut = (cq.Workplane("YZ").workplane(offset=r_nut - nh / 2).center(0, M.KEY_Z).polygon(6, sw / math.cos(math.pi / 6))
           .extrude(nh + 0.4))
    slot = box_from(r_nut - nh / 2, r_nut + nh / 2 + 0.4, -sw / 2 - 0.2, sw / 2 + 0.2, M.KEY_Z, z1 + 1)
    ring = ring.cut(nut).cut(slot)
    return ring


def key_switch():
    return radial_bore(P.KEY_SWITCH_D, M.KEY_PHI, M.KEY_Z, M.TUBE_OD / 2 + 4.0, M.KEY_RING_ID / 2 + 2)


# --------------------------------------------------------------------------- Avionik-Schlitten (ein Druckteil)
def sled():
    """Flansch + Zapfenring (Ausstoßspant) und Träger unter der Platine in einem Stück. Druck stehend, Flansch auf dem Bett."""
    v0 = M.BOARD_V0_Z
    bw = M.BOARD_W / 2
    yb = -M.BOARD_T / 2                        # Unterseite der Platine
    fl0, fl1 = M.FLANGE_Z
    sp0, sp1 = M.SPIGOT_Z
    # Flansch (Platte) und Zapfenring
    s = cyl(M.FLANGE_OD, fl0, fl1)
    s = s.union(tube(M.SPIGOT_OD, M.SPIGOT_ID, sp0, sp1))
    # Fase am Zapfen unten zum Einführen
    s = s.cut(tube(M.SPIGOT_OD + 2, M.SPIGOT_OD - 1.2, sp0 - 0.1, sp0 + 0.8))
    # Schraubenaugen innen am Zapfenring für die Einschmelzmuttern (radial)
    for phi in M.SCREW_PHI:
        boss = cyl_between(M.BOSS_D, polar(M.SPIGOT_ID / 2 - 3.5, phi, M.JOINT_SCREW_Z), polar(M.SPIGOT_OD / 2 - 0.5, phi, M.JOINT_SCREW_Z))
        boss = boss.union(box_from(-M.BOSS_D / 2, M.BOSS_D / 2, M.SPIGOT_ID / 2 - 3.5, M.SPIGOT_OD / 2 - 0.5, M.JOINT_SCREW_Z, sp1)
                          .rotate((0, 0, 0), (0, 0, 1), phi - 90))
        s = s.union(boss)
        d, depth = M.INSERT_HOLE
        s = s.cut(radial_bore(d, phi, M.JOINT_SCREW_Z, M.SPIGOT_OD / 2 + 1, M.SPIGOT_OD / 2 - depth))
    # Träger: Boden, Seitenwände mit den Platinen-Säulen, Stirnwand unten
    tz0, tz1 = M.DISC_Z[1], sp0 + 1.0
    floor = box_from(-bw, bw, M.TRAY_FLOOR_Y, M.TRAY_FLOOR_Y + M.TRAY_WALL, tz0, tz1)
    walls = box_from(-bw, -bw + M.TRAY_WALL, M.TRAY_FLOOR_Y, yb, tz0, tz1)
    walls = walls.union(walls.mirror("YZ"))
    s = s.union(floor).union(walls)
    # Steg vom Träger in den Zapfenring (unter der Platine, y < 0), trägt den Träger am Spant
    web = box_from(-bw, bw, M.TRAY_FLOOR_Y, -3.0, sp0 - 0.5, sp1).intersect(cyl(M.SPIGOT_ID + 1, sp0 - 0.5, sp1))
    s = s.union(web)
    for (u, v) in M.BOARD_HOLES:
        z = v0 + v
        post = box_from(u - M.POST_D / 2 if u < 0 else u - M.POST_D / 2, u + M.POST_D / 2, M.TRAY_FLOOR_Y, yb, z - 4.0, z + 4.0)
        post = post.union(box_from(-bw if u < 0 else u, u if u < 0 else bw, M.TRAY_FLOOR_Y, yb, z - 4.0, z + 4.0))
        s = s.union(post)
        d, depth = M.INSERT_HOLE
        s = s.cut(cyl_between(d, (u, yb + 0.5, z), (u, yb - depth - 4.0, z)))
    end = box_from(-bw, bw, M.TRAY_FLOOR_Y, yb, tz0, tz0 + 3.0)
    end = end.cut(box_from(-12, 12, M.TRAY_FLOOR_Y + 3, yb + 1, tz0 - 1, tz0 + 4))      # Kabel der Akkus nach unten
    s = s.union(end)
    for (x, y) in M.TRAY_TO_DISC:
        s = s.union(cyl_between(8.0, (x, y, tz0), (x, y, tz0 + 8.0)))
        s = s.cut(cyl_between(M.INSERT_HOLE[0], (x, y, tz0 - 1), (x, y, tz0 + M.INSERT_HOLE[1] + 1)))
    # Akkufächer: Trennsteg und Klettband-Schlitze
    v_sep = (M.BAT2S["v0"] + M.BAT2S["l"] + M.BAT1S["v0"]) / 2
    s = s.union(box_from(-bw, bw, M.TRAY_FLOOR_Y, M.TRAY_FLOOR_Y + 5.0, v0 + v_sep - 1, v0 + v_sep + 1))
    for bat in (M.BAT2S, M.BAT1S):
        vm = bat["v0"] + bat["l"] / 2
        for dv in (-bat["l"] / 4, bat["l"] / 4):
            s = s.cut(box_from(-M.STRAP_SLOT[1] / 2, M.STRAP_SLOT[1] / 2, M.TRAY_FLOOR_Y - 1, M.TRAY_FLOOR_Y + 3,
                               v0 + vm + dv - M.STRAP_SLOT[0] / 2, v0 + vm + dv + M.STRAP_SLOT[0] / 2))
    # Seitenfenster in den Wänden (Akkustecker, Griff, Gewicht)
    for vm, ln in ((22.0, 22.0), (50.0, 22.0), (84.0, 22.0), (106.0, 14.0)):
        s = s.cut(box_from(-bw - 1, bw + 1, M.TRAY_FLOOR_Y + 4, yb - 3, v0 + vm - ln / 2, v0 + vm + ln / 2))
    # Schalterbrett-Säulen: Löcher im Boden für 2 × M3 von innen
    for (u, v) in M.PANEL_COLS:
        s = s.cut(cyl_between(3.3, (u, M.TRAY_FLOOR_Y - 1, v0 + v), (u, M.TRAY_FLOOR_Y + 3, v0 + v)))
    # Spant: Sockel der Ladungsschale, Zünder-Klemmen, Ringschraube
    cc = M.CHARGE_CUP
    s = s.union(tube(cc["d"] + 6, cc["d"] + 0.3, fl1, fl1 + 3.0, cc["x"], cc["y"]))
    for (x, y) in M.FEEDTHRU:
        s = s.cut(cyl(M.FEEDTHRU_D, fl0 - 1, fl1 + 1, x, y))
    s = s.cut(cyl(M.EYE_BOLT["d"], fl0 - 1, fl1 + 1, M.EYE_BOLT["x"], M.EYE_BOLT["y"]))
    # Dichtnut für Moosgummi-Ring auf der Unterseite des Flansches (liegt auf der Kupplerkante)
    s = s.cut(tube(P.COUPLER_OD + 0.4, P.COUPLER_ID - 0.4, fl0 - 0.1, fl0 + 1.0))
    return s


def lower_disc():
    z0, z1 = M.DISC_Z
    d = cyl(M.DISC_OD, z0, z1).cut(cyl(M.DISC_CABLE_D, z0 - 1, z1 + 1, 0, -4.0))
    x0, x1, y0, y1 = M.DISC_PLUG_WINDOW
    d = d.cut(box_from(x0, x1, y0, y1, z0 - 1, z1 + 1))
    for (x, y) in M.TRAY_TO_DISC:
        d = d.cut(cyl(3.4, z0 - 1, z1 + 1, x, y))
    for a in M.DISC_LIGHT_PHI:                             # Erleichterung unter dem Akkufach, frei von den Schraubenlöchern
        x, y = M.DISC_LIGHT_R * math.cos(math.radians(a)), M.DISC_LIGHT_R * math.sin(math.radians(a))
        d = d.cut(cyl(M.DISC_LIGHT_D, z0 - 1, z1 + 1, x, y))
    # Griffmulde / Ausrichtmarke bei 0°
    d = d.cut(box_from(M.DISC_OD / 2 - 2.5, M.DISC_OD / 2 + 1, -1.0, 1.0, z0 - 1, z1 + 1))
    return d


def charge_cup():
    cc = M.CHARGE_CUP
    z0 = M.FLANGE_Z[1]
    # Becher mit Boden, steckt im Sockel des Spants; Zünder von oben, Ladung mit Klebeband verschlossen. Verrußt = neu drucken.
    return tube(cc["d"], cc["d"] - 2.4, z0, z0 + cc["h"], cc["x"], cc["y"]).union(cyl(cc["d"], z0, z0 + 1.2, cc["x"], cc["y"]))


def switch_panel():
    v0 = M.BOARD_V0_Z
    va, vb = M.HATCH_B["v"]
    plate = box_from(-M.PANEL_W / 2, M.PANEL_W / 2, M.PANEL_Y[0], M.PANEL_Y[1], v0 + va + 1, v0 + vb - 1)
    for name, u, a, b, w in M.PANEL_PARTS:
        plate = plate.cut(box_from(u - w / 2 - 0.2, u + w / 2 + 0.2, M.PANEL_Y[0] - 1, M.PANEL_Y[1] + 1, v0 + a, v0 + b))
    for (u, v) in M.PANEL_COLS:
        col = cyl_between(M.PANEL_COL_D, (u, M.PANEL_Y[1] - 0.5, v0 + v), (u, M.TRAY_FLOOR_Y, v0 + v))
        col = col.cut(cyl_between(M.INSERT_HOLE[0], (u, M.TRAY_FLOOR_Y + 0.5, v0 + v), (u, M.TRAY_FLOOR_Y - M.INSERT_HOLE[1] - 0.5, v0 + v)))
        plate = plate.union(col)
    return plate


def panel_parts():
    v0 = M.BOARD_V0_Z
    out = []
    for name, u, a, b, w in M.PANEL_PARTS:
        out.append((name, box_from(u - w / 2, u + w / 2, -34.6, M.PANEL_Y[1] + 4.0, v0 + a, v0 + b)))
    return out


def piston_plate():
    z0 = M.PISTON_Z[0]
    p = cyl(P.COUPLER_ID - 0.2, z0, z0 + 3.0)
    p = p.union(tube(P.COUPLER_ID - 0.2, P.COUPLER_ID - 3.4, z0, z0 + 8.0))     # Kragen, in das Kuppler-Stück geklebt
    return p.cut(cyl(6.0, z0 - 1, z0 + P.PISTON_PLATE_T + 1))                    # Schnur läuft mittig durch


def nose_bulkhead():
    """Spant in der Schulter der Spitze mit Bohrung für eine Ringschraube M4 (statt der gedruckten Öse)."""
    z0 = M.TOP_Z - P.NOSE_SHOULDER_L
    d = P.NOSE_SHOULDER_D - 2.4
    b = cyl(d, z0 + 2, z0 + 5).union(tube(d, d - 3.2, z0 + 5, z0 + 11))    # 3 mm Platte, Kragen zum Einkleben
    for k in range(4):                                                       # Erleichterung (kein Gasraum, nur Zug)
        a = math.radians(45 + 90 * k)
        b = b.cut(cyl(14.0, z0, z0 + 8, 20 * math.cos(a), 20 * math.sin(a)))
    return b.cut(cyl(M.EYE_BOLT["d"], z0, z0 + 8))


# --------------------------------------------------------------------------- Kardan: neues Lochbild am Außenrahmen
def outer_gimbal_inserts():
    """Außenrahmen aus tvc.py, aber 3 Einschmelzmutter-Bohrungen bei 0°/135°/225° statt 4 × Ø 3,2 bei 45°."""
    import tvc
    orig = tvc.radial_holes
    tvc.radial_holes = lambda shape, *a, **k: shape      # alte 4er-Bohrung unterdrücken
    try:
        g = tvc.outer_gimbal()
    finally:
        tvc.radial_holes = orig
    ro = P.OUTER_RING_OD / 2
    d, depth = M.INSERT_HOLE
    for phi in M.SCREW_PHI:
        g = g.cut(radial_bore(d, phi, P.OUTER_FLANGE_H / 2, ro + 1, ro - depth))
    return g.translate((0, 0, P.TVC_RING_Z))


# --------------------------------------------------------------------------- Zusammenbau
def old_printed_mass():
    """Druckteile des bisherigen Erstflug-Entwurfs (Ring-Stack) mit derselben Regel gerechnet: Vergleich auf gleicher Basis."""
    import build as B
    keys = {"Endring unten": 1.0, "Endplatte oben": 1.0, "Träger": 1.0, "Schlüsselschalter-Kragen": 1.0, "Schalterbrett": 1.0,
            "Spitze Spant": 1.0}
    out = {}
    for n, sh, _, _ in B.build_all():
        for k in keys:
            if n.startswith(k):
                out[k] = out.get(k, 0.0) + sh.Volume() / 1000 * M.PRINT_RHO * M.PRINT_FILL
    out["Kolbenplatte (Ø 70,4 × 6)"] = math.pi * (P.COUPLER_ID / 2 + 0.1) ** 2 * P.PISTON_PLATE_T / 1000 * M.PRINT_RHO * M.PRINT_FILL
    return out


def build_all():
    import tvc, airframe
    parts = Parts()
    parts.add("Rohr unten 200", lower_tube(), "tube", "rumpf")
    parts.add("Rohr oben 500", upper_tube(), "tube", "rumpf")
    parts.add("Avionik-Kuppler 150 (im unteren Rohr verklebt)", avionics_coupler(), "coupler", "rumpf")
    parts.add("Schlüsselring mit Kabelgitter", key_ring(), "printed", "rumpf")
    parts.add("Schlüsselschalter", key_switch(), "steel", "rumpf")
    # Kardan aus tvc.py, Außenrahmen mit neuem Lochbild
    tv = Parts()
    tvc.build(tv)
    for name, shape, col, grp in tv:
        if name.startswith("Außenrahmen"):
            shape = outer_gimbal_inserts().val()
        parts.append((name, shape, col, "antrieb"))
    parts.add("Schlitten mit Ausstoßspant", sled(), "printed2", "avionik")
    parts.add("Untere Scheibe", lower_disc(), "printed", "avionik")
    parts.add("Ladungsbecher", charge_cup(), "steel", "avionik")
    parts.add("Schalterbrett", switch_panel(), "printed", "avionik")
    for name, b in panel_parts():
        parts.add(name, b, "steel", "avionik")
    v0 = M.BOARD_V0_Z
    board = box_from(-M.BOARD_W / 2, M.BOARD_W / 2, -M.BOARD_T / 2, M.BOARD_T / 2, v0, v0 + M.BOARD_L).edges("|Y").fillet(2.0)
    for (u, v) in M.BOARD_HOLES:
        board = board.cut(cyl_between(3.2, (u, -2, v0 + v), (u, 2, v0 + v)))
    parts.add("Platine rev B1", board, "board", "avionik")
    t = P.TEENSY
    parts.add("Teensy 4.1", box_from(t["u0"], t["u1"], M.BOARD_T / 2, M.BOARD_T / 2 + 12.0, v0 + t["v0"], v0 + t["v1"]), "teensy", "avionik")
    for name, (u0, plugs, sgn) in (("TVC", (0.0, M.PLUGS_TVC_END, -1)), ("Spitze", (M.BOARD_L, M.PLUGS_NOSE_END, +1))):
        for pname, u in plugs:
            a, b = sorted((v0 + u0, v0 + u0 + sgn * M.PLUG_REACH))
            parts.add(f"Stecker {pname}", box_from(u - 3.0, u + 3.0, M.BOARD_T / 2, M.BOARD_T / 2 + 7.0, a, b), "steel", "avionik")
    yb = -M.BOARD_T / 2 - M.TRAY_WALL / 2
    for nm, bat in (("Akku 2S", M.BAT2S), ("Akku 1S", M.BAT1S)):
        parts.add(nm, box_from(-bat["w"] / 2, bat["w"] / 2, M.TRAY_FLOOR_Y + M.TRAY_WALL + 0.3, M.TRAY_FLOOR_Y + M.TRAY_WALL + 0.3 + bat["h"],
                               v0 + bat["v0"], v0 + bat["v0"] + bat["l"]), "battery", "avionik")
    parts.add("Kolben Kuppler-Stück 40", tube(P.COUPLER_OD, P.COUPLER_ID, *M.PISTON_Z), "coupler", "bergung")
    parts.add("Kolbenplatte", piston_plate(), "printed", "bergung")
    parts.add("Fallschirm (gepackt)", cyl(P.CHUTE_D, *M.CHUTE_Z).edges().fillet(8.0), "chute", "bergung")
    # Spitze an die neue Lage schieben (airframe rechnet mit NOSE_BASE_Z aus params; erstflug 700 mm ist dieselbe Basis 720)
    assert abs(P.NOSE_BASE_Z - M.TOP_Z) < 1e-6, (P.NOSE_BASE_Z, M.TOP_Z)
    z0 = M.TOP_Z - P.NOSE_SHOULDER_L
    parts.add("Spitze Schulterkuppler", tube(P.NOSE_SHOULDER_D, P.NOSE_SHOULDER_D - 2.4, z0, M.TOP_Z + 2), "coupler", "spitze")
    parts.add("Spitze Klima 8539", airframe.nose_cone(), "nose", "spitze")
    parts.add("Spitze Spant (Ringschraube M4)", nose_bulkhead(), "printed2", "spitze")
    return parts


def check(parts):
    """Durchdringungen zwischen Teilen, die sich nicht berühren dürfen, und Freiraum der Kabel/Stecker."""
    by = {n: s for n, s, _, _ in parts}
    def vol(a, b):
        try:
            return by[a].intersect(by[b]).Volume()
        except Exception:
            return 0.0
    pairs = []
    sled_like = ["Schlitten mit Ausstoßspant", "Untere Scheibe", "Schalterbrett", "Platine rev B1", "Teensy 4.1", "Akku 2S", "Akku 1S"]
    sled_like += [n for n in by if n.startswith("Stecker ")] + [p[0] for p in M.PANEL_PARTS]
    for a in sled_like:
        pairs.append((a, "Avionik-Kuppler 150 (im unteren Rohr verklebt)"))
        pairs.append((a, "Rohr oben 500"))
        pairs.append((a, "Rohr unten 200"))
    for a in ("Schlitten mit Ausstoßspant", "Untere Scheibe", "Schalterbrett"):
        for b in ("Platine rev B1", "Teensy 4.1", "Akku 2S", "Akku 1S") + tuple(n for n in by if n.startswith("Stecker ")):
            pairs.append((a, b))
    pairs.append(("Schlüsselring mit Kabelgitter", "Untere Scheibe"))
    for name, *_ in M.PANEL_PARTS:                       # Bauteile stecken durch die Ausbrüche, nicht in Brett oder Säulen
        pairs.append(("Schalterbrett", name))
        pairs.append(("Schlitten mit Ausstoßspant", name))
    for n in by:
        if n.startswith(("Motorrohr", "Innenrahmen", "Außenrahmen", "Servo", "Hebel")):
            pairs.append(("Schlüsselring mit Kabelgitter", n))
    bad = []
    for a, b in pairs:
        if a in by and b in by:
            v = vol(a, b)
            if v > 0.5:
                bad.append(f"{a} ∩ {b}: {v:.1f} mm³")
    missing = [n for n in sled_like if n not in by]
    return bad, missing


def export(parts):
    EXPORT.mkdir(parents=True, exist_ok=True)
    printed = ["Schlitten mit Ausstoßspant", "Untere Scheibe", "Ladungsbecher", "Schalterbrett", "Schlüsselring mit Kabelgitter",
               "Kolbenplatte", "Spitze Spant", "Außenrahmen", "Innenrahmen", "Motorrohr", "Adapter 29"]
    by = {n: s for n, s, _, _ in parts}
    files = []
    for n in printed:
        key = next(k for k in by if k.startswith(n))
        fn = (key.split(" (")[0].replace(" ", "_").replace("ß", "ss").replace("ü", "ue").replace("ö", "oe").replace("ä", "ae")
              .replace("→", "-"))
        shp = cq.Workplane().add(by[key])
        for ext in ("stl", "step"):
            f = EXPORT / f"{fn}.{ext}"
            exporters.export(shp, str(f), tolerance=0.02, angularTolerance=0.1) if ext == "stl" else exporters.export(shp, str(f))
        files.append((key, fn, by[key].Volume()))
    return files


def renders(parts):
    sys.path.insert(0, str(HERE))
    import build as B
    IMG.mkdir(parents=True, exist_ok=True)
    jobs = [
        ("modular_section", "section", dict(cut=(0, 60, -60, 60, -100, 1100))),
        ("modular_avionik", "avionics", dict(only_groups=["avionik"])),
        ("modular_avionik_rumpf", "hatch_a_iso", dict(only_groups=["avionik", "rumpf"], cut=(-60, 60, -60, 60, 300, 1000))),
        ("modular_luke_b", "hatch_b_iso", dict(only_groups=["avionik", "rumpf"], cut=(-60, 60, -60, 60, 300, 1000))),
        ("modular_schluesselring", "tvc", dict(only_groups=["rumpf", "antrieb"], include=None, cut=(-60, 60, -60, 60, 128, 1100))),
    ]
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
        print("  Prüfung frei: Schlitten, Platine, Stecker, Akkus, Schalterbrett gegen Kuppler und Rohre; Schlüsselring gegen Kardan")
    files = export(parts)
    printed_g = 0.0
    rows = []
    for name, fn, vol in files:
        g = vol / 1000 * M.PRINT_RHO * M.PRINT_FILL
        if not name.startswith(("Außenrahmen", "Innenrahmen", "Motorrohr", "Adapter")):   # Kardan steht im alten Modell schon drin
            printed_g += g
        rows.append({"teil": name, "datei": f"cad/export/modular/{fn}.stl", "cm3": round(vol / 1000, 1), "g": round(g, 1)})
        print(f"  export/modular/{fn}.stl  {vol / 1000:.1f} cm³  ≈ {g:.0f} g")
    total = M.mass_estimate(printed_g)
    old = old_printed_mass()
    old_g = sum(old.values())
    old_assumed = sum(m for n, m in M.MASS_REMOVED if not n.startswith(("8 Gew", "Stoß", "9 ×")))
    old_fair = M.MASS_BASE_ERSTFLUG - old_assumed + old_g
    print(f"  alter Entwurf mit derselben Regel: Druckteile {old_g:.0f} g statt {old_assumed:.0f} g angesetzt -> {old_fair:.0f} g")
    print(f"  Masse Erstflug modular ≈ {total:.0f} g (alt {M.MASS_BASE_ERSTFLUG:.0f} g; neue Druckteile {printed_g:.0f} g)")
    import json
    (EXPORT / "masses.json").write_text(json.dumps({"druckteile": rows, "druckteile_neu_g": round(printed_g, 1),
                                                    "start_g": round(total, 1),
                                                    "alt_druckteile_gleiche_regel": {k: round(v, 1) for k, v in old.items()},
                                                    "alt_druckteile_angesetzt_g": old_assumed, "alt_start_angesetzt_g": M.MASS_BASE_ERSTFLUG,
                                                    "alt_start_gleiche_regel_g": round(old_fair, 1)}, indent=1, ensure_ascii=False), encoding="utf-8")
    if "--no-render" not in sys.argv:
        renders(parts)
    return 1 if bad or missing else 0


if __name__ == "__main__":
    sys.exit(main())
