"""Baut das Raketenmodell aus den Modulen, exportiert STEP/STL je Baugruppe nach cad/export/ und rendert
drei Ansichten nach docs/img/cad/ (Gesamtansicht, Schnitt, Kardan).

    python cad/build.py              alles
    python cad/build.py --no-render  nur Geometrie und Export

Benötigt cadquery (pip install --user cadquery). Für die Renderbilder wird Blender headless aufgerufen
(Pfad BLENDER unten oder Umgebungsvariable BLENDER); ohne Blender werden die Bilder übersprungen.
"""
import json, os, subprocess, sys, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
# --config erstflug [--tube-l 700]: muss vor dem Import von params stehen (params liest MS_CONFIG / MS_TUBE_L)
for _i, _a in enumerate(sys.argv):
    if _a in ("--config", "--tube-l"):
        if _i + 1 >= len(sys.argv):
            sys.exit(f"{_a} braucht einen Wert")
        os.environ["MS_CONFIG" if _a == "--config" else "MS_TUBE_L"] = sys.argv[_i + 1]
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cadquery as cq
from cadquery import exporters
import params as P
from common import Parts, box_from
import airframe, tvc, avionics, ejection, legs

EXPORT = HERE / "export" / P.CONFIG if P.CONFIG != "voll" else HERE / "export"
IMG = HERE.parent / "docs" / "img" / "cad"
BLENDER = os.environ.get("BLENDER", r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")


def build_all(pitch=0.0, yaw=0.0, legs_deployed=None):
    """Rakete der Konfiguration P.CONFIG. Der Prüfstand steht seit 27.10.2026 in testrig.py (gebaute Rakete)."""
    parts = Parts()
    hatch = airframe.build(parts)
    tvc.build(parts, pitch_deg=pitch, yaw_deg=yaw)
    avionics.build(parts, hatch)
    ejection.build(parts)
    if P.LEGS:
        legs.build(parts, deployed=legs_deployed)
    return parts


def assembly(parts, names=True):
    assy = cq.Assembly(name="rocket")
    for i, (name, shape, col, group) in enumerate(parts):
        r, g, b = P.COLORS[col]
        assy.add(shape, name=f"{group}_{i:03d}_{name}" if names else None, color=cq.Color(r, g, b))
    return assy


def export_groups(parts):
    EXPORT.mkdir(parents=True, exist_ok=True)
    groups = sorted({g for _, _, _, g in parts})
    for g in groups:
        shapes = [s for _, s, _, gg in parts if gg == g]
        comp = cq.Compound.makeCompound(shapes)
        exporters.export(cq.Workplane().add(comp), str(EXPORT / f"{g}.stl"), tolerance=0.05, angularTolerance=0.2)
        sub = Parts([p for p in parts if p[3] == g])
        assembly(sub).export(str(EXPORT / f"{g}.step"))
        print(f"  {g:10s} {len(shapes):3d} Teile -> {g}.step / {g}.stl")
    step = EXPORT.parent / "rocket_erstflug.step" if P.CONFIG == "erstflug" else EXPORT / "rocket.step"
    assembly(parts).export(str(step))
    comp = cq.Compound.makeCompound([s for _, s, _, _ in parts])
    exporters.export(cq.Workplane().add(comp), str(EXPORT / "rocket.stl"), tolerance=0.05, angularTolerance=0.2)
    print(f"  {step.name} (Gesamtmodell, im Repo) und rocket.stl")


def write_render_manifest(parts, name, cut=None, only_groups=None, exclude=(), include=None):
    """Je Teil eine STL mit Farbe für den Blender-Renderer. cut = (x0, x1, y0, y1, z0, z1) entfernt diesen Quader.
    include: Liste von Namensanfängen, die zusätzlich zu only_groups aufgenommen werden."""
    d = EXPORT / "render" / name
    d.mkdir(parents=True, exist_ok=True)
    for f in d.glob("*.stl"):
        f.unlink()
    items = []
    for i, (pname, shape, col, group) in enumerate(parts):
        if only_groups and group not in only_groups and not (include and any(pname.startswith(k) for k in include)):
            continue
        if any(e in pname for e in exclude):
            continue
        shp = cq.Workplane().add(shape)
        if cut:
            shp = shp.cut(box_from(*cut))
            if not shp.vals() or shp.val().Volume() < 1e-3:
                continue
        f = d / f"{i:03d}.stl"
        try:
            exporters.export(shp, str(f), tolerance=0.05, angularTolerance=0.2)
        except Exception as e:  # ein Teil darf das Bild nicht verhindern
            print(f"  ! {pname}: {e}")
            continue
        items.append({"file": f.name, "name": pname, "color": P.COLORS[col], "group": group})
    (d / "manifest.json").write_text(json.dumps(items, indent=1, ensure_ascii=False), encoding="utf-8")
    return d


def render(manifest_dir, out_png, view, extra=()):
    if not Path(BLENDER).exists():
        print(f"  Blender nicht gefunden ({BLENDER}), Render {out_png.name} übersprungen")
        return
    cmd = [BLENDER, "-b", "--python", str(HERE / "tools" / "render_parts.py"), "--",
           str(manifest_dir / "manifest.json"), str(out_png), view, *map(str, extra)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    ok = "RENDER_OK" in r.stdout
    print(f"  {'ok' if ok else 'FEHLER'} {out_png.relative_to(HERE.parent)}")
    if not ok:
        print(r.stdout[-2000:], r.stderr[-2000:])


def check_clearance(deg=None):
    """Durchdringungen bei voller Auslenkung beider Achsen: bewegte Gruppen gegen ihre Umgebung."""
    deg = P.GIMBAL_MAX_DEG if deg is None else deg
    parts = build_all(pitch=deg, yaw=deg, legs_deployed=False)
    by = {n: s for n, s, _, _ in parts}
    moving_motor = ["Motorrohr", "Adapter 29→24", "Motor TSP E12-0", "Servohebel innen"]
    moving_inner = ["Innenrahmen", "Servo Innenrahmen W5652H", "Servohebel außen"] + moving_motor
    fixed = ["Außenrahmen", "Servo Außenrahmen W5652H", "Rohr unten 75x500", "Endring unten"]
    fixed += [n for n in ("Beinring unten (Hülse)", "Schlüsselschalter-Kragen", "Schlüsselschalter") if n in by]
    pairs = [(a, b) for a in moving_inner for b in fixed] + [(a, b) for a in moving_motor for b in ("Innenrahmen", "Servo Innenrahmen W5652H")]
    bad = []
    for a, b in pairs:
        v = _overlap(by, a, b)
        if v > 0.5:
            bad.append((a, b, v))
    print(f"Kollisionsprüfung bei ±{deg:.0f}° Pitch und Yaw: " + ("frei" if not bad else "DURCHDRINGUNG"))
    for a, b, v in bad:
        print(f"  {a} / {b}: {v:.0f} mm³")
    return bad


def _overlap(by, a, b):
    """Schnittvolumen zweier Teile; fehlende Namen sind ein Fehler, kein "frei"."""
    return _vol(by[a], by[b])


def _vol(a, b):
    r = cq.Workplane().add(a).intersect(cq.Workplane().add(b))
    return sum(s.Volume() for s in r.vals()) if r.vals() else 0.0


def check_erstflug(parts):
    """Erstflug: Luken, Schalterbrett, Schlüsselschalter und Kolbenraum. Gibt die Befunde als Liste zurück."""
    import math
    from common import cyl_between
    by = {n: s for n, s, _, _ in parts}
    out = []
    rods = [n for n in by if n.startswith("Gewindestange")]
    sled = ["Platine 54x120", "Teensy 4.1", "Akku 2S", "Akku 1S", "Träger (gedruckt)"]
    hw = ["Schalterbrett (Luke B)", "Schlüsselschalter"] + [n for n, *_ in P.PANEL_PARTS if n in by]
    # 1 Hardware gegen Stangen, Platine, Akkus, Träger, Kuppler, Rohr
    bad = []
    for h in hw:
        for o in rods + sled + ["Kuppler Flugcomputer 150", "Rohr oben 75x500 (mit Luke)", "Rohr unten 75x500", "Endring unten",
                                "Endplatte oben (Spant, Ladungsschale)"]:
            v = _overlap(by, h, o)
            if v > 0.5:
                bad.append(f"{h} / {o}: {v:.0f} mm³")
    for o in rods + sled + ["Kuppler Flugcomputer 150", "Rohr unten 75x500", "Endring unten"]:
        v = _overlap(by, "Schlüsselschalter-Kragen", o)
        if v > 0.5:
            bad.append(f"Kragen / {o}: {v:.0f} mm³")
    out.append(("Schalterbrett, Bauteile, Schlüsselschalter gegen Stangen/Platine/Akkus/Träger/Rohre/Kuppler", bad))
    # 2 Steckerräume: Stecker/Karte/Finger (Stecker 1,5 mm größer, bis außerhalb des Rohrs) treffen weder Stangen, Platine,
    #   Akkus und Träger noch die Wand von Kuppler und Rohr (das heißt: die Luke deckt den Steckerraum ab).
    bad = []
    v0 = P.BOARD_V0_Z
    others = list(by)
    probes = []
    for name, a, b, hwid in P.PANEL_PARTS:
        hw = hwid + 1.5
        if 2 * hw > P.ROD_GAP:
            bad.append(f"{name}: {2 * hw:.1f} mm breiter als die Stangenlücke {P.ROD_GAP:.1f}")
        probes.append((f"Steckerraum {name}", box_from(-hw, hw, -P.TUBE_OD, P.PANEL_FACE_Y - 0.01, v0 + a - 1.5, v0 + b + 1.5), {name}))
    usb_w, sd_w = 11.0, 11.0   # [Annahme] Micro-USB-Stecker mit Umspritzung; microSD 11 × 15
    probes.append(("Micro-USB-Stecker (Teensy)", box_from(-usb_w / 2, usb_w / 2, 10.0, P.TUBE_OD,
                                                       v0 + P.TEENSY["v1"] - 6, v0 + P.TEENSY["v1"] + 20), {"Teensy 4.1"}))
    # microSD sitzt an der Unterseite des Teensy am USB-fernen Ende, Auswurf nach -v (12 mm über das Modulende hinaus)
    probes.append(("microSD-Karte (Teensy)", box_from(-sd_w / 2, sd_w / 2, 2.0, P.TUBE_OD,
                                                   v0 + P.TEENSY["v0"] - 12, v0 + P.TEENSY["v0"] + 8), {"Teensy 4.1"}))
    for label, probe, skip in probes:
        for n in others:
            if n in skip:
                continue
            v = _vol(probe.val(), by[n])
            if v > 0.5:
                bad.append(f"{label} / {n}: {v:.0f} mm³")
    zk = (P.KEY_COLLAR_Z[0] + P.KEY_COLLAR_Z[1]) / 2
    probe = cyl_between(P.KEY_SWITCH_D + 4, (P.TUBE_OD / 2 + 0.01, 0, zk), (P.TUBE_OD / 2 + 30, 0, zk))
    for n in by:
        if n.startswith(("Rohr", "Schl", "Spitze")):
            continue
        v = _vol(probe.val(), by[n])
        if v > 0.5:
            bad.append(f"Schlüsselschalter-Außenraum / {n}: {v:.0f} mm³")
    out.append(("Steckerräume (USB, SD, Schalterbrett, Schlüssel) frei", bad))
    # 3 Kolbenbohrung
    bad = []
    piston = [n for n in by if n.startswith("Kolben")]
    for pn in piston:
        for n in by:
            if n == pn or n.startswith(("Kolben", "Rohr oben", "Rohr unten")):
                continue
            v = _overlap(by, pn, n)
            if v > 0.5:
                bad.append(f"{pn} / {n}: {v:.0f} mm³")
    zmax = max(by[n].BoundingBox().zmax for n in by if n.startswith(("Endplatte oben", "Gewindestange", "Kuppler Flugcomputer")))
    zmin_p = min(by[n].BoundingBox().zmin for n in piston)
    out.append((f"Kolben (z {zmin_p:.0f} …) gegen Endplatte/Stangen/Kuppler, Luft zur höchsten Kante (z {zmax:.1f}): {zmin_p - zmax:.1f} mm", bad))
    # Bohrung: Innenradius des oberen Rohrs von der Kolbenunterkante bis zur Spitze frei von Einbauten
    # Kolben Ø 72,4 läuft im Rohr (ID 72,6) bis zur Spitze; der Stoßkuppler (ID 70,2) und die Spitzenschulter liegen darüber:
    #   bis zur Unterkante des Stoßkupplers muss die Bohrung Ø 72,4 frei sein, darüber Ø 70,2 (Schirm Ø 60 passt) bis zur Öse der Spitze.
    zz0 = zmin_p
    z_narrow = P.CHUTE_COUPLER_Z[0] if P.CONFIG == "erstflug" else P.NOSE_BASE_Z - P.NOSE_SHOULDER_L
    z_top = P.NOSE_BASE_Z - P.NOSE_BULKHEAD_BELOW_BASE
    bore = cyl_between(P.COUPLER_OD, (0, 0, zz0), (0, 0, z_narrow)).union(cyl_between(P.COUPLER_ID, (0, 0, z_narrow), (0, 0, z_top)))
    stuck = []
    for n in by:
        if n.startswith(("Kolben", "Fallschirm", "Rohr", "Kuppler Flugcomputer", "Stoßkuppler", "Spitze Klima", "Spitze Schulter")):
            continue
        v = _vol(bore.val(), by[n])
        if v > 0.5:
            stuck.append(f"{n}: {v:.0f} mm³")
    out.append((f"Bohrung Ø {P.COUPLER_OD} von z {zz0:.0f} bis {z_narrow:.0f}, dann Ø {P.COUPLER_ID} bis zur Öse der Spitze ({z_top:.1f}) frei von Einbauten", stuck))
    for label, bad in out:
        print(f"  {label}: " + ("frei" if not bad else "DURCHDRINGUNG"))
        for x in bad:
            print("    " + x)
    return out


def main_erstflug():
    t0 = time.time()
    no_render = "--no-render" in sys.argv
    print(f"Erstflug-Konfiguration, Rohr {P.TUBE_TOTAL:.0f} mm (Minimum {P.TUBE_MIN:.0f} mm)")
    parts = build_all()
    print(f"  {len(parts)} Teile in {time.time() - t0:.0f} s; Gesamtlänge {P.TOTAL_LENGTH:.0f} mm")
    export_groups(parts)
    check_clearance()
    print("Erstflug-Prüfungen ...")
    check_erstflug(parts)
    if no_render:
        return
    IMG.mkdir(parents=True, exist_ok=True)
    print("Render ...")
    z0, z1 = P.FC_COUPLER_Z
    cut = (0, 200, -200, 200, -200, P.TOTAL_LENGTH + 50)
    d = write_render_manifest(parts, "ef_overall")
    render(d, IMG / "rocket_erstflug_overall.png", "overall")
    d = write_render_manifest(build_all(), "ef_section", cut=cut)
    render(d, IMG / "rocket_erstflug_section.png", "section")
    # Luken: nur Kuppler-Bereich (Rohr oben, Kuppler, Modul, Kragen), geschnitten auf z = Kuppler ± ein paar mm
    zc = (P.KEY_COLLAR_Z[0] - 5, z1 + 5)
    for side, view in (("a", "hatch_a"), ("b", "hatch_b")):
        d = write_render_manifest(parts, f"ef_hatch_{side}", only_groups={"avionics", "airframe"},
                                  exclude=("Rohr oben", "Spitze", "Stoßkuppler"), cut=(-200, 200, -200, 200, zc[1], 3000))
        render(d, IMG / f"hatches_{side}.png", view)
        render(d, IMG / f"hatches_{side}_iso.png", view + "_iso")
    print(f"fertig in {time.time() - t0:.0f} s")


def main():
    t0 = time.time()
    no_render = "--no-render" in sys.argv
    print("Geometrie ...")
    parts = build_all(legs_deployed=True)
    print(f"  {len(parts)} Teile in {time.time() - t0:.0f} s")
    print("Export ...")
    export_groups(parts)
    check_clearance()
    if no_render:
        return
    IMG.mkdir(parents=True, exist_ok=True)
    print("Render ...")
    # 1 Gesamtansicht, Beine ausgefahren
    d = write_render_manifest(parts, "overall")
    render(d, IMG / "rocket_overall.png", "overall")
    # 2 Schnitt: Hälfte x > 0 entfernt, Beine eingeklappt, Spitze/Schirm sichtbar
    parts_stowed = build_all(legs_deployed=False)
    d = write_render_manifest(parts_stowed, "section", cut=(0, 200, -200, 200, -200, P.TOTAL_LENGTH + 50))
    render(d, IMG / "rocket_section.png", "section")
    # 3 Kardan mit Servos, 5° Pitch und 4° Yaw ausgelenkt, mit dem unteren Rohrende
    parts_tvc = build_all(pitch=5.0, yaw=4.0, legs_deployed=False)
    d = write_render_manifest(parts_tvc, "tvc", only_groups={"tvc"})
    render(d, IMG / "rocket_tvc.png", "tvc")
    # 4 Flugcomputer-Modul ohne Kuppler (herausgezogen)
    d = write_render_manifest(parts, "avionics", only_groups={"avionics"}, exclude=("Kuppler",))
    render(d, IMG / "rocket_avionics.png", "avionics")
    print(f"fertig in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main_erstflug() if P.CONFIG == "erstflug" else main()
