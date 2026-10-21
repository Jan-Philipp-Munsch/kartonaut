"""Flugcomputer-Modul im Kuppler: Endringe mit Gewindestangen, gedruckter Träger, Schlitten-Platine
54 × 120 mit Teensy, Akkus 2S und 1S unter der Platine. Die obere Endplatte ist zugleich der feste
Spant des Kolben-Ausstoßes (Ladungsschale, E-Match-Bohrungen, Schockschnur-Öse).

Das Modul ist eine Einheit: Kuppler lösen (4 × M2 oben), oberes Rohr abziehen, Modul am oberen
Ring herausziehen. Die Akkus liegen im Träger unter der Platine und sind nach dem Herausziehen frei.
"""
import math
import cadquery as cq
import params as P
from common import Parts, tube, cyl, box, box_from, cyl_between


def end_ring(z0, closed):
    r = P.FC_RING_D / 2
    ring = cyl(P.FC_RING_D, z0, z0 + P.FC_RING_T)
    for (x, y) in P.FC_RODS:
        ring = ring.cut(cyl(P.FC_ROD_D + 0.3, z0 - 1, z0 + P.FC_RING_T + 1, x, y))
    if not closed:
        ring = ring.cut(cyl(36.0, z0 - 1, z0 + P.FC_RING_T + 1))            # Kabel zum TVC
        ring = ring.cut(box_from(-27.5, 27.5, -16.0, 1.5, z0 - 1, z0 + P.FC_RING_T + 1))   # Träger/Platine stecken durch
    return ring


def charge_bulkhead():
    """Obere Endplatte mit Ladungsschale, 2 E-Match-Bohrungen und Öse."""
    z0 = P.FC_COUPLER_Z[1] - P.FC_RING_T
    plate = end_ring(z0, closed=True)
    top = z0 + P.FC_RING_T
    well = tube(P.CHARGE_WELL_D + 4, P.CHARGE_WELL_D, top, top + P.CHARGE_WELL_H, 0, 14)
    plate = plate.union(well)
    plate = plate.cut(cyl(P.CHARGE_WELL_D, top - 3, top + P.CHARGE_WELL_H + 1, 0, 14))
    for x in (-3, 3):
        plate = plate.cut(cyl(P.EMATCH_HOLE_D, z0 - 1, top + 1, x, 14))
    eye = (cq.Workplane("YZ").workplane(offset=0).center(-14, top + 4).circle(P.SHOCK_CORD_EYE_D / 2 + 1.5)
           .circle(P.SHOCK_CORD_EYE_D / 2).extrude(1.5, both=True))
    eye = eye.union(box_from(-1.5, 1.5, -18, -10, top - 0.5, top + 1.5))
    return plate.union(eye)


def carrier(z0, z1):
    """Wanne unter der Platine: Boden, zwei Längswände, Stirnwände mit Schraubflanschen zu den Endringen."""
    w, d, t = P.BOARD_W, P.CARRIER_DEPTH, P.CARRIER_WALL
    L = z1 - z0
    tray = box_from(-w / 2, w / 2, -d, -P.BOARD_T / 2, z0, z1)
    cav = box_from(-w / 2 + t, w / 2 - t, -d + t, 0, z0 + t, z1 - t)
    tray = tray.cut(cav)
    # Ausschnitt in den Längswänden für Akkustecker und Griff
    tray = tray.cut(box_from(-w, w, -d + t + 2, -P.BOARD_T / 2 - 2, z0 + 0.35 * L, z0 + 0.65 * L))
    # Flansche an den Stirnseiten (zu den Endringen) mit Schraubenbohrung
    for zf, dz in ((z0, -1), (z1, +1)):
        fl = box_from(-w / 2, w / 2, -d, -d + 6, zf - 0.5 + (0 if dz < 0 else 0), zf + 0.5)
        tray = tray.union(fl)
    # Gewindeaufnahmen für die Platine (M3, Positionen HOLES)
    for (u, v) in P.BOARD_HOLES:
        post = cyl(6.0, -d + t, -P.BOARD_T / 2, u, 0).translate((0, 0, 0))
        post = cyl_between(6.0, (u, -d + t, P.BOARD_V0_Z + v), (u, -P.BOARD_T / 2, P.BOARD_V0_Z + v))
        tray = tray.union(post).cut(cyl_between(2.5, (u, -d, P.BOARD_V0_Z + v), (u, 1, P.BOARD_V0_Z + v)))
    return tray


def board():
    v0 = P.BOARD_V0_Z
    b = box_from(-P.BOARD_W / 2, P.BOARD_W / 2, -P.BOARD_T / 2, P.BOARD_T / 2, v0, v0 + P.BOARD_L)
    b = b.edges("|Y").fillet(2.0)
    for (u, v) in P.BOARD_HOLES:
        b = b.cut(cyl_between(3.2, (u, -2, v0 + v), (u, 2, v0 + v)))
    return b


def teensy():
    t = P.TEENSY
    v0 = P.BOARD_V0_Z
    body = box_from(t["u0"], t["u1"], P.BOARD_T / 2 + 8.5, P.BOARD_T / 2 + 8.5 + 1.6, v0 + t["v0"], v0 + t["v1"])
    pins = box_from(t["u0"] + 0.5, t["u0"] + 3.0, P.BOARD_T / 2, P.BOARD_T / 2 + 8.5, v0 + t["v0"], v0 + t["v1"])
    pins2 = pins.translate((t["u1"] - t["u0"] - 3.5, 0, 0))
    usb = box_from(-4.0, 4.0, P.BOARD_T / 2 + 10.1, P.BOARD_T / 2 + 10.1 + 3.0, v0 + t["v1"] - 6, v0 + t["v1"] + 1.5)
    sd = box_from(-6.0, 6.0, P.BOARD_T / 2 + 10.1, P.BOARD_T / 2 + 10.1 + 2.0, v0 + t["v0"] - 1, v0 + t["v0"] + 12)
    return body.union(pins).union(pins2).union(usb).union(sd)


def battery(spec):
    v0 = P.BOARD_V0_Z
    y1 = -P.BOARD_T / 2 - 2.0
    b = box_from(-spec["w"] / 2, spec["w"] / 2, y1 - spec["h"], y1, v0 + spec["v0"], v0 + spec["v0"] + spec["l"])
    return b.edges("|Z").fillet(1.5)


def build(parts: Parts, hatch):
    z0, z1 = P.FC_COUPLER_Z
    coupler = tube(P.COUPLER_OD, P.COUPLER_ID, z0, z1).cut(hatch)
    parts.add("Kuppler Flugcomputer 150", coupler, "coupler", "avionics")
    parts.add("Endring unten", end_ring(z0, closed=False), "printed", "avionics")
    parts.add("Endplatte oben (Spant, Ladungsschale)", charge_bulkhead(), "printed", "avionics")
    for i, (x, y) in enumerate(P.FC_RODS):
        parts.add(f"Gewindestange M2 {i + 1}", cyl(P.FC_ROD_D, z0 - 2, z1 + 2, x, y), "steel", "avionics")
    parts.add("Träger (gedruckt)", carrier(z0 + P.FC_RING_T, z1 - P.FC_RING_T), "printed2", "avionics")
    parts.add("Platine 54x120", board(), "board", "avionics")
    parts.add("Teensy 4.1", teensy(), "teensy", "avionics")
    parts.add("Akku 2S", battery(P.BAT2S), "battery", "avionics")
    parts.add("Akku 1S", battery(P.BAT1S), "battery", "avionics")
