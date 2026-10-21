"""Rumpf: zwei Klima-Rohre 75 mm, Luke für den USB-Stecker, Klima-Spitze 8539 mit Schulterkuppler."""
import cadquery as cq
import params as P
from common import Parts, tube, cyl, box_from, radial_holes


def hatch_cutter():
    """Fenster in Rohr und Kuppler auf der Bestückungsseite (+y) über dem USB-Stecker des Teensy."""
    z0 = P.BOARD_V0_Z + P.HATCH_V[0]
    z1 = P.BOARD_V0_Z + P.HATCH_V[1]
    c = box_from(-P.HATCH_W / 2, P.HATCH_W / 2, 0, P.TUBE_OD, z0, z1)
    if P.HATCH_SD:
        c = c.union(box_from(-P.HATCH_W / 2, P.HATCH_W / 2, 0, P.TUBE_OD,
                             P.BOARD_V0_Z + P.SD_V[0] - 2, P.BOARD_V0_Z + P.SD_V[1] + 2))
    if P.HATCH_SIDE_Y < 0:
        c = c.mirror("XZ")
    return c


def nose_profile():
    """Ogiven-ähnliches Profil (r, z-Offset über der Basis) der Klima-Spitze; die echte Kontur nachmessen."""
    R, L = P.TUBE_OD / 2, P.NOSE_L
    return [(R, 0.0), (R * 0.985, 0.18 * L), (R * 0.88, 0.42 * L), (R * 0.66, 0.66 * L),
            (R * 0.36, 0.86 * L), (R * 0.12, 0.97 * L), (0.0, L)]


def nose_cone():
    pts = nose_profile()
    outer = (cq.Workplane("XZ").moveTo(0, 0).lineTo(pts[0][0], 0).spline(pts[1:], includeCurrent=True)
             .close().revolve(360, (0, 0, 0), (0, 1, 0)))
    t = P.NOSE_WALL
    inner_pts = [(max(r - t, 0.0), z) for r, z in pts if r - t > 0.5] + [(0.0, P.NOSE_L - 2 * t)]
    inner = (cq.Workplane("XZ").moveTo(0, -1).lineTo(inner_pts[0][0], -1).lineTo(inner_pts[0][0], 0)
             .spline(inner_pts[1:], includeCurrent=True).close().revolve(360, (0, 0, 0), (0, 1, 0)))
    cone = outer.cut(inner)
    # Stützrippen innen (Spritzguss hat welche), nur angedeutet
    for i in range(4):
        rib = box_from(0, P.TUBE_OD / 2 - 1, -1.0, 1.0, 0, P.NOSE_L * 0.75).rotate((0, 0, 0), (0, 0, 1), 45 + 90 * i)
        cone = cone.union(rib.intersect(outer))
    return cone.translate((0, 0, P.NOSE_BASE_Z))


def build(parts: Parts):
    hatch = hatch_cutter()
    lower = tube(P.TUBE_OD, P.TUBE_ID, *P.LOWER_TUBE_Z)
    lower = radial_holes(lower, P.OUTER_SCREW_D, P.TUBE_OD / 2, P.TVC_RING_Z + P.OUTER_FLANGE_H / 2, n=4, phi0=45,
                         depth=3)
    parts.add("Rohr unten 75x500", lower, "tube", "airframe")
    upper = tube(P.TUBE_OD, P.TUBE_ID, *P.UPPER_TUBE_Z).cut(hatch)
    # vier Schrauben Rohr–Kuppler oben und unten (M2 radial)
    upper = radial_holes(upper, 2.2, P.TUBE_OD / 2, P.JOINT_Z + P.COUPLER_INTO_UPPER / 2, n=4, phi0=45, depth=3)
    parts.add("Rohr oben 75x500 (mit Luke)", upper, "tube", "airframe")
    z0 = P.NOSE_BASE_Z - P.NOSE_SHOULDER_L
    shoulder = tube(P.NOSE_SHOULDER_D, P.NOSE_SHOULDER_D - 2.4, z0, P.NOSE_BASE_Z + 2)
    parts.add("Spitze Schulterkuppler", shoulder, "coupler", "nose")
    bulk = cyl(P.NOSE_SHOULDER_D - 2.4, z0 + 2, z0 + 6)
    eye = (cq.Workplane("XZ").workplane(offset=0).center(0, z0 - 2).circle(P.SHOCK_CORD_EYE_D / 2 + 1.5)
           .circle(P.SHOCK_CORD_EYE_D / 2).extrude(1.5, both=True))
    parts.add("Spitze Spant mit Öse", bulk.union(eye), "printed2", "nose")
    parts.add("Spitze Klima 8539", nose_cone(), "nose", "nose")
    return hatch
