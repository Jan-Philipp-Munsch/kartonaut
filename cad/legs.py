"""Landebeine nach model_rocket.blend / LegConnectors.blend: Hülse am Rohrende mit vier Gelenken,
Ring 70 mm darüber mit vier Gelenkböcken, je Bein eine Hauptstrebe (am Ring unten) und eine obere
Strebe (am Ring oben), die sich am Fuß treffen. LEG_DEPLOYED schaltet zwischen ausgefahren (Blender)
und eingeklappt (Hauptstrebe senkrecht am Rohr). Mit festen Strebenlängen klappt die obere Strebe nicht
mit ein (siehe blender_inventory.md §3.7); eingeklappt wird sie deshalb nur bis zum Fuß gezeichnet."""
import math
import cadquery as cq
import params as P
from common import Parts, tube, cyl, box, box_from, cyl_between


def leg(phi_deg, deployed):
    ang = math.radians(-P.LEG_DEPLOY_DEG if deployed else P.LEG_STOW_DEG)
    h0 = (P.LEG_HINGE_R, 0.0, P.LEG_HINGE_Z)
    foot = (P.LEG_HINGE_R + P.LEG_MAIN_L * math.cos(ang), 0.0, P.LEG_HINGE_Z + P.LEG_MAIN_L * math.sin(ang))
    t0 = (P.LEG_TOP_HINGE_R, 0.0, P.LEG_TOP_HINGE_Z)
    # Hauptstrebe: Flachprofil mit runden Enden, in der x-z-Ebene
    main = (cq.Workplane("XZ").center(0, 0).slot2D(P.LEG_MAIN_L + P.LEG_MAIN_W, P.LEG_MAIN_W, 0)
            .extrude(P.LEG_MAIN_T / 2, both=True))
    main = main.cut(cq.Workplane("XZ").center(-P.LEG_MAIN_L / 2, 0).circle(2.0).extrude(10, both=True))
    main = main.cut(cq.Workplane("XZ").center(P.LEG_MAIN_L / 2, 0).circle(2.0).extrude(10, both=True))
    main = main.translate((P.LEG_MAIN_L / 2, 0, 0)).rotate((0, 0, 0), (0, 1, 0), -math.degrees(ang)).translate(h0)
    top = cyl_between(P.LEG_TOP_D, t0, foot)
    fx, fy, fz = P.LEG_FOOT
    foot_pad = box(fx, fy, fz, foot[0], 0, foot[2] - fz / 2 + 2)
    if not deployed:
        foot_pad = box(fz, fy, fx, foot[0] + fz / 2 + 3, 0, foot[2] - fx / 2 + 3)
    # Gelenk unten (LegEnd): zwei Laschen an der Hülse
    lug = box_from(P.LEG_SLEEVE_OD / 2 - 3, P.LEG_HINGE_R + 6, -P.LEG_MAIN_T / 2 - 4, P.LEG_MAIN_T / 2 + 4,
                   P.LEG_HINGE_Z - 5, P.LEG_HINGE_Z + 5)
    lug = lug.cut(box_from(P.LEG_SLEEVE_OD / 2 - 1, P.LEG_HINGE_R + 10, -P.LEG_MAIN_T / 2 - 0.3, P.LEG_MAIN_T / 2 + 0.3,
                           P.LEG_HINGE_Z - 6, P.LEG_HINGE_Z + 6))
    lug = lug.cut(cyl_between(2.2, (P.LEG_HINGE_R, -10, P.LEG_HINGE_Z), (P.LEG_HINGE_R, 10, P.LEG_HINGE_Z)))
    # Gelenkbock oben (TopStrut Mount, 7 × 21,5 × 16)
    mount = box_from(P.LEG_UPPER_RING_OD / 2 - 6, P.LEG_TOP_HINGE_R + 8, -3.5, 3.5, P.LEG_TOP_HINGE_Z - 5, P.LEG_TOP_HINGE_Z + 11)
    mount = mount.edges("|Y").fillet(2.5)
    mount = mount.cut(cyl_between(2.2, (P.LEG_TOP_HINGE_R, -10, P.LEG_TOP_HINGE_Z), (P.LEG_TOP_HINGE_R, 10, P.LEG_TOP_HINGE_Z)))
    out = []
    for name, shp, col in (("Hauptstrebe", main, "leg"), ("obere Strebe", top, "steel"), ("Fuß", foot_pad, "foot"),
                           ("Gelenk unten", lug, "printed2"), ("Gelenkbock oben", mount, "printed2")):
        out.append((name, shp.rotate((0, 0, 0), (0, 0, 1), phi_deg), col))
    return out


def build(parts: Parts, deployed=None):
    deployed = P.LEG_DEPLOYED if deployed is None else deployed
    sleeve = tube(P.LEG_SLEEVE_OD, P.LEG_SLEEVE_ID, P.LEG_SLEEVE_Z0, P.LEG_SLEEVE_Z0 + P.LEG_SLEEVE_H)
    parts.add("Beinring unten (Hülse)", sleeve, "printed", "legs")
    ring = tube(P.LEG_UPPER_RING_OD, P.LEG_UPPER_RING_ID, *P.LEG_UPPER_RING_Z)
    for i in range(P.LEG_N):   # Aussparungen zwischen den Böcken, Ring bleibt als Kreuz mit Außenring
        ring = ring.cut(box_from(P.TUBE_OD / 2 + 3, P.LEG_UPPER_RING_OD / 2 - 4, -16, 16,
                                 P.LEG_UPPER_RING_Z[0] - 1, P.LEG_UPPER_RING_Z[1] + 1).rotate((0, 0, 0), (0, 0, 1), 45 + 90 * i))
    parts.add("Beinring oben", ring, "printed", "legs")
    for i in range(P.LEG_N):
        for name, shp, col in leg(90.0 * i, deployed):
            parts.add(f"Bein {i + 1} {name}", shp, col, "legs")
