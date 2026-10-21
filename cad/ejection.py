"""Kolben-Ausstoß nach BPS: Kolben aus einem Stück Kuppler mit Platte, darüber der Fallschirm als Platzhalter.
Der feste Spant mit der Ladungsschale ist die obere Endplatte des Flugcomputer-Moduls (avionics.py)."""
import cadquery as cq
import params as P
from common import Parts, tube, cyl, box_from


def piston():
    z0 = P.PISTON_Z0
    p = tube(P.COUPLER_OD, P.COUPLER_ID, z0, z0 + P.PISTON_L)
    plate = cyl(P.COUPLER_ID + 0.2, z0, z0 + P.PISTON_PLATE_T)
    eye = (cq.Workplane("YZ").center(0, z0 + P.PISTON_PLATE_T + 4).circle(P.SHOCK_CORD_EYE_D / 2 + 1.5)
           .circle(P.SHOCK_CORD_EYE_D / 2).extrude(1.5, both=True))
    return p.union(plate).union(eye)


def parachute():
    z0 = P.CHUTE_Z0
    c = cyl(P.CHUTE_D, z0, z0 + P.CHUTE_L)
    return c.edges().fillet(8.0)


def build(parts: Parts):
    parts.add("Kolben (Kuppler-Stück mit Platte)", piston(), "coupler", "recovery")
    parts.add("Fallschirm 125 cm (gepackt, Platzhalter)", parachute(), "chute", "recovery")
