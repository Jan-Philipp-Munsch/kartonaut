"""Gehäuse der Bodenstations-Funkbrücke: Raspberry Pi Pico + E22-400T22S mit senkrechtem Halbwellen-Dipol (27.10.2026).
Hintergrund: docs/Plan_Bordzuendung_2026-10-27.md §5 (Bodenstation = Laptop + Pico + drittes E22, Entscheidung Jan 27.10.).

    python cad/groundbridge.py              bauen, prüfen, Druckteile export/groundbridge/*.stl, Bild docs/img/cad/groundbridge.png
    python cad/groundbridge.py --no-render  ohne Blender

Aufbau (Koordinaten: x quer, z senkrecht nach oben, y von der Rückwand y = 0 zum Deckel):
  Unterteil: flacher Kasten, Rückwand und Seitenwände 2 mm. Innen links oben das E22 in einem Rahmen (mit
             Schaumklebeband auf die Rückwand), darunter der Pico auf vier Domen (M2 × 5, schneiden ihr Gewinde selbst),
             USB-Buchse des Pico in einer Öffnung der rechten Wand. Rechts oben ein Dom mit eingelegter 1/4"-Stativmutter
             (Kamerastativ an der Rückseite). Vier Dome für den Deckel (M3 × 10, Gewinde schneidet sich ins Ø-2,6-Loch,
             wie die Druckteile der Modulbauweise).
  Dipol:     senkrecht an der linken Außenseite in einer Leiste mit Drahtkanal Ø 2,2. In der Mitte ein Fenster: dort
             biegen beide Arme rechtwinklig durch zwei Löcher in der linken Wand zu den Pads des E22 (oberer Arm an ANT,
             unterer an GND). Jeder Arm ist ab seiner Lötstelle DIPOL_ARM lang (Kupferdraht 1,5 mm², z. B. aus NYM).
             Polarisation senkrecht wie die Wendel in der Rakete. Die Elektronik liegt neben dem Dipol, nicht in seiner Achse.
  Deckel:    2-mm-Platte, vier Schrauben, Fenster über der Pico-LED.
Druck: PETG, 3 Wände, 25 %, Unterteil mit der Rückwand auf dem Bett, Deckel mit der Außenseite auf dem Bett, ohne Stützen.
"""
import json, math, sys, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cadquery as cq
from cadquery import exporters
import params as P

PRINT_DIR = HERE / "export" / "groundbridge"
RHO_PETG, PRINT_FILL = 1.27, 0.75   # [Annahme] wie die Modulbauweise (modular_params.PRINT_RHO, PRINT_FILL)

# --------------------------------------------------------------------------- Maße
PICO_L, PICO_W, PICO_T = 51.0, 21.0, 1.0      # [Raspberry Pi Pico Datenblatt] Platine 51 × 21 × 1
PICO_HOLE_DX, PICO_HOLE_DZ = 47.0, 11.4       # [Pico Datenblatt] Lochabstand längs / quer, Löcher Ø 2,1
E22_W, E22_H, E22_T = 16.0, 26.0, 2.8         # [Ebyte] E22-400T22S 16 × 26 mm; Höhe mit Schirm [Annahme]
FREQ_MHZ = 433.125                            # [Config.h] Kanal der Rakete, Mitte des 433-MHz-Bands
VEL = 0.95                                    # [Annahme] Verkürzung für blanken Draht 1,4 mm
DIPOL_ARM = round(299.792 / FREQ_MHZ / 4 * VEL * 1000)   # mm je Arm ab der Lötstelle, ≈ 164

T = 2.0                                       # [Vorgabe] Wandstärke
IN_X = (-29.0, 29.0)                          # Innenraum
IN_Z = (0.0, 66.0)
IN_Y = (T, T + 12.0)                          # Innentiefe 12: Pico auf 3-mm-Domen, Bauteile bis ~9, Lötstellen
OUT_X = (IN_X[0] - T, IN_X[1] + T)
OUT_Z = (IN_Z[0] - T, IN_Z[1] + T)
LID_T = 2.0
PICO_C = (3.0, 18.5)                          # Mitte Pico (x, z): USB-Ende bei x = 28,5, 0,5 mm vor der rechten Wand
PICO_POST_H = 3.0
E22_C = (-12.0, 46.0)                         # Mitte E22, links oben
LID_BOSS = [(-25.5, 3.5), (25.5, 3.5), (-25.5, 62.5), (25.5, 62.5)]
TRIPOD_C = (14.0, 46.0)                       # 1/4"-20-Mutter: SW 11,1, Höhe 5,5 [DIN/ISO-Tabelle]
SPINE_X = (OUT_X[0] - 8.0, OUT_X[0])          # Leiste links, 8 breit, 10 tief
SPINE_Y = (0.0, 10.0)
SPINE_Z = (OUT_Z[0] - 15.0, OUT_Z[1] + 15.0)
WIRE_X, WIRE_Y = (SPINE_X[0] + SPINE_X[1]) / 2, 5.0
FEED_Z = (47.0, 55.0)                         # Fenster in der Leiste, Höhe des E22
LEAD_Z = (53.0, 49.0)                         # Durchführungen: oben ANT, unten GND


def solid(wp):
    return wp.val() if hasattr(wp, "val") else wp


def bx(x0, x1, y0, y1, z0, z1):
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0))


def cyl(d, origin, axis, length):
    return cq.Solid.makeCylinder(d / 2, length, cq.Vector(*origin), cq.Vector(*axis))


def hex_prism(af, origin, axis, length):
    pl = cq.Plane(origin=origin, xDir=(1, 0, 0) if axis != (1, 0, 0) else (0, 1, 0), normal=axis)
    return cq.Workplane(pl).polygon(6, af / math.cos(math.radians(30))).extrude(length).val()


def base():
    b = bx(OUT_X[0], OUT_X[1], 0, IN_Y[1], OUT_Z[0], OUT_Z[1])
    b = b.cut(bx(IN_X[0], IN_X[1], IN_Y[0], IN_Y[1] + 1, IN_Z[0], IN_Z[1]))
    # Deckeldome
    for x, z in LID_BOSS:
        b = b.fuse(cyl(6.5, (x, IN_Y[0], z), (0, 1, 0), IN_Y[1] - IN_Y[0]))
    # Pico-Dome
    holes = [(PICO_C[0] + sx * PICO_HOLE_DX / 2, PICO_C[1] + sz * PICO_HOLE_DZ / 2) for sx in (-1, 1) for sz in (-1, 1)]
    for x, z in holes:
        b = b.fuse(cyl(4.5, (x, IN_Y[0], z), (0, 1, 0), PICO_POST_H))
    # E22-Rahmen (1 mm Steg, 1,5 hoch, 0,3 Luft)
    ex0, ex1 = E22_C[0] - E22_W / 2 - 0.3, E22_C[0] + E22_W / 2 + 0.3
    ez0, ez1 = E22_C[1] - E22_H / 2 - 0.3, E22_C[1] + E22_H / 2 + 0.3
    frame = bx(ex0 - 1, ex1 + 1, IN_Y[0], IN_Y[0] + 1.5, ez0 - 1, ez1 + 1).cut(bx(ex0, ex1, IN_Y[0], IN_Y[0] + 2, ez0, ez1))
    frame = frame.cut(bx(ex0 - 1.5, ex0 + 0.5, IN_Y[0], IN_Y[0] + 2, ez0 + 4, ez1 - 4))   # Lücke links für die Drähte
    b = b.fuse(frame)
    # Stativdom
    tx, tz = TRIPOD_C
    b = b.fuse(cyl(18.0, (tx, IN_Y[0], tz), (0, 1, 0), 7.0))
    # Leiste links mit Drahtkanal
    b = b.fuse(bx(SPINE_X[0], SPINE_X[1] + 0.01, SPINE_Y[0], SPINE_Y[1], SPINE_Z[0], SPINE_Z[1]))
    # --- Bohrungen
    for x, z in LID_BOSS:
        b = b.cut(cyl(2.6, (x, IN_Y[0] + 2.0, z), (0, 1, 0), 20))
    for x, z in holes:
        b = b.cut(cyl(1.8, (x, IN_Y[0] + 0.8, z), (0, 1, 0), 10))
    # USB-Öffnung rechts (Stecker-Umspritzung ~11 × 7)
    b = b.cut(bx(IN_X[1] - 0.5, OUT_X[1] + 0.5, IN_Y[0] + 0.8, IN_Y[0] + 9.8, PICO_C[1] - 6.0, PICO_C[1] + 6.0))
    # Stativ: Durchgang Ø 6,6 durch die Rückwand, Sechskanttasche von innen
    b = b.cut(cyl(6.6, (tx, -1, tz), (0, 1, 0), IN_Y[0] + 3))
    b = b.cut(hex_prism(11.1 + 0.3, (tx, IN_Y[0] + 1.4, tz), (0, 1, 0), 10))
    # Drahtkanal, Fenster, Durchführungen
    b = b.cut(cyl(2.2, (WIRE_X, WIRE_Y, SPINE_Z[0] - 1), (0, 0, 1), SPINE_Z[1] - SPINE_Z[0] + 2))
    b = b.cut(bx(SPINE_X[0] + 1.0, SPINE_X[1] + 0.5, 2.0, SPINE_Y[1] + 1, FEED_Z[0], FEED_Z[1]))
    for z in LEAD_Z:
        b = b.cut(cyl(2.2, (SPINE_X[1] - 1, WIRE_Y, z), (1, 0, 0), T + 2))
    # Kabelbinderschlitz unten in der Leiste (Dipol am Stab befestigen, falls kein Stativ)
    for z in (SPINE_Z[0] + 6, SPINE_Z[1] - 6):
        b = b.cut(bx(SPINE_X[0] - 1, SPINE_X[1] + 1, 7.0, 9.0, z - 2.5, z + 2.5))
    return b.clean()


def lid():
    l = bx(OUT_X[0], OUT_X[1], IN_Y[1], IN_Y[1] + LID_T, OUT_Z[0], OUT_Z[1])
    for x, z in LID_BOSS:
        l = l.cut(cyl(3.4, (x, IN_Y[1] - 1, z), (0, 1, 0), LID_T + 2))
    # Fenster über der LED (Pico-LED am USB-Ende); großzügig, Lage am Teil prüfen
    l = l.cut(bx(PICO_C[0] + PICO_L / 2 - 12, PICO_C[0] + PICO_L / 2 - 2, IN_Y[1] - 1, IN_Y[1] + LID_T + 1,
                 PICO_C[1] - 6, PICO_C[1] + 6))
    return l.clean()


def dummies():
    """Pico, E22, Dipol nur fürs Bild und die Prüfung."""
    py0 = IN_Y[0] + PICO_POST_H
    pico = bx(PICO_C[0] - PICO_L / 2, PICO_C[0] + PICO_L / 2, py0, py0 + PICO_T, PICO_C[1] - PICO_W / 2, PICO_C[1] + PICO_W / 2)
    pico = pico.fuse(bx(PICO_C[0] + PICO_L / 2 - 5.5, PICO_C[0] + PICO_L / 2 + 1.0, py0 + PICO_T, py0 + PICO_T + 2.6,
                        PICO_C[1] - 4, PICO_C[1] + 4))                     # Micro-USB
    pico = pico.fuse(bx(PICO_C[0] - 4, PICO_C[0] + 3, py0 + PICO_T, py0 + PICO_T + 1.0, PICO_C[1] - 3.5, PICO_C[1] + 3.5))
    e22 = bx(E22_C[0] - E22_W / 2, E22_C[0] + E22_W / 2, IN_Y[0] + 1.0, IN_Y[0] + 1.0 + E22_T,
             E22_C[1] - E22_H / 2, E22_C[1] + E22_H / 2)
    w = 1.4
    lead_up = (E22_C[0] - E22_W / 2) - WIRE_X               # waagerechte Länge bis zum Pad
    arm_up = cyl(w, (WIRE_X, WIRE_Y, LEAD_Z[0]), (0, 0, 1), DIPOL_ARM - lead_up)
    arm_up = arm_up.fuse(cyl(w, (WIRE_X, WIRE_Y, LEAD_Z[0]), (1, 0, 0), lead_up))
    arm_dn = cyl(w, (WIRE_X, WIRE_Y, LEAD_Z[1]), (0, 0, -1), DIPOL_ARM - lead_up)
    arm_dn = arm_dn.fuse(cyl(w, (WIRE_X, WIRE_Y, LEAD_Z[1]), (1, 0, 0), lead_up))
    return pico, e22, arm_up, arm_dn


def check(b, l, pico, e22, arm_up, arm_dn):
    bad = []
    def vol(a, c):
        try:
            return a.intersect(c).Volume()
        except Exception:
            return 0.0
    for n, s in (("Pico", pico), ("E22", e22), ("Deckel", l)):
        v = vol(b, s)
        if v > 0.5:
            bad.append(f"{n} schneidet das Unterteil ({v:.1f} mm³)")
    if vol(l, pico) > 0.5 or vol(l, e22) > 0.5:
        bad.append("Deckel berührt Pico oder E22")
    # Abstand Dipol zur Elektronik
    d_lower = abs(WIRE_X - (PICO_C[0] - PICO_L / 2))
    if d_lower < 10:
        bad.append(f"unterer Arm nur {d_lower:.1f} mm neben dem Pico")
    return bad, d_lower


def bed(shape, flip=False):
    s = shape.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), -90 if flip else 90)
    bb = s.BoundingBox()
    return s.translate(cq.Vector(-(bb.xmin + bb.xmax) / 2, -(bb.ymin + bb.ymax) / 2, -bb.zmin))


def main():
    t0 = time.time()
    no_render = "--no-render" in sys.argv
    b, l = base(), lid()
    pico, e22, arm_up, arm_dn = dummies()
    bad, d_lower = check(b, l, pico, e22, arm_up, arm_dn)
    print(f"Funkbrücke: Kasten {OUT_X[1] - OUT_X[0]:.0f} × {IN_Y[1] + LID_T:.0f} × {OUT_Z[1] - OUT_Z[0]:.0f} mm "
          f"(ohne Leiste), Dipol 2 × {DIPOL_ARM} mm für {FREQ_MHZ} MHz, unterer Arm {d_lower:.0f} mm neben dem Pico")
    for x in bad:
        print("  FEHLER " + x)
    PRINT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for fn, s, flip in (("Funkbruecke_Unterteil.stl", b, False), ("Funkbruecke_Deckel.stl", l, True)):
        p = bed(s, flip)
        exporters.export(cq.Workplane().add(p), str(PRINT_DIR / fn), tolerance=0.05, angularTolerance=0.2)
        bb = p.BoundingBox()
        g = s.Volume() / 1000 * RHO_PETG * PRINT_FILL
        rows.append(dict(datei=f"cad/export/groundbridge/{fn}", stueck=1, cm3=round(s.Volume() / 1000, 1), g=round(g, 1),
                         mm=[round(bb.xlen), round(bb.ylen), round(bb.zlen)]))
        print(f"  cad/export/groundbridge/{fn:28s} {s.Volume() / 1000:5.1f} cm³  ≈ {g:3.0f} g  "
              f"{bb.xlen:.0f} × {bb.ylen:.0f} × {bb.zlen:.0f} mm")
    (PRINT_DIR / "druckteile.json").write_text(json.dumps(dict(
        quelle="cad/groundbridge.py", material="PETG, 3 Wände, 25 % Gyroid", dipol_arm_mm=DIPOL_ARM,
        schrauben="4 × M3 × 10 (Deckel), 4 × M2 × 5 (Pico), 1 × Mutter 1/4\"-20 (Stativ)",
        masse_regel=f"{PRINT_FILL:.0%} des CAD-Volumens × {RHO_PETG} g/cm³", teile=rows), indent=1, ensure_ascii=False),
        encoding="utf-8")
    if not no_render:
        import build as B
        P.COLORS.setdefault("copper", (0.85, 0.50, 0.22))
        lid_x = l.translate(cq.Vector(0, 30, 0))     # Deckel abgehoben
        parts = [("Unterteil", b, "printed", "gehaeuse"), ("Deckel", lid_x, "printed2", "gehaeuse"),
                 ("Pico", pico, "teensy", "elektronik"), ("E22", e22, "board", "elektronik"),
                 ("Dipol oben", arm_up, "copper", "antenne"), ("Dipol unten", arm_dn, "copper", "antenne")]
        B.IMG.mkdir(parents=True, exist_ok=True)
        d = B.write_render_manifest(parts, "groundbridge")
        B.render(d, B.IMG / "groundbridge.png", "groundbridge")
        detail = [p for p in parts if not p[0].startswith("Dipol")]
        d = B.write_render_manifest(detail, "groundbridge_detail")
        B.render(d, B.IMG / "groundbridge_detail.png", "groundbridge_detail")
    print(f"{'ok' if not bad else 'PRÜFUNG FEHLGESCHLAGEN'}, fertig in {time.time() - t0:.0f} s")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
