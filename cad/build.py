"""Baut das Raketenmodell aus den Modulen, exportiert STEP/STL je Baugruppe nach cad/export/ und rendert
drei Ansichten nach docs/img/cad/ (Gesamtansicht, Schnitt, Kardan).

    python cad/build.py              alles
    python cad/build.py --no-render  nur Geometrie und Export

Benötigt cadquery (pip install --user cadquery). Für die Renderbilder wird Blender headless aufgerufen
(Pfad BLENDER unten oder Umgebungsvariable BLENDER); ohne Blender werden die Bilder übersprungen.
"""
import json, os, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cadquery as cq
from cadquery import exporters
import params as P
from common import Parts, box_from
import airframe, tvc, avionics, ejection, legs

EXPORT = HERE / "export"
IMG = HERE.parent / "docs" / "img" / "cad"
BLENDER = os.environ.get("BLENDER", r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")


def build_all(pitch=0.0, yaw=0.0, legs_deployed=None):
    parts = Parts()
    hatch = airframe.build(parts)
    tvc.build(parts, pitch_deg=pitch, yaw_deg=yaw)
    avionics.build(parts, hatch)
    ejection.build(parts)
    legs.build(parts, deployed=legs_deployed)
    return parts


def assembly(parts, names=True):
    assy = cq.Assembly(name="rocket")
    for i, (name, shape, col, group) in enumerate(parts):
        r, g, b = P.COLORS[col]
        assy.add(shape, name=f"{group}_{i:03d}_{name}" if names else None, color=cq.Color(r, g, b))
    return assy


def export_groups(parts):
    EXPORT.mkdir(exist_ok=True)
    groups = sorted({g for _, _, _, g in parts})
    for g in groups:
        shapes = [s for _, s, _, gg in parts if gg == g]
        comp = cq.Compound.makeCompound(shapes)
        exporters.export(cq.Workplane().add(comp), str(EXPORT / f"{g}.stl"), tolerance=0.05, angularTolerance=0.2)
        sub = Parts([p for p in parts if p[3] == g])
        assembly(sub).export(str(EXPORT / f"{g}.step"))
        print(f"  {g:10s} {len(shapes):3d} Teile -> {g}.step / {g}.stl")
    assembly(parts).export(str(EXPORT / "rocket.step"))
    comp = cq.Compound.makeCompound([s for _, s, _, _ in parts])
    exporters.export(cq.Workplane().add(comp), str(EXPORT / "rocket.stl"), tolerance=0.05, angularTolerance=0.2)
    print("  rocket.step (Gesamtmodell, im Repo) und rocket.stl")


def write_render_manifest(parts, name, cut=None, only_groups=None, exclude=()):
    """Je Teil eine STL mit Farbe für den Blender-Renderer. cut = (x0, x1, y0, y1, z0, z1) entfernt diesen Quader."""
    d = EXPORT / "render" / name
    d.mkdir(parents=True, exist_ok=True)
    for f in d.glob("*.stl"):
        f.unlink()
    items = []
    for i, (pname, shape, col, group) in enumerate(parts):
        if only_groups and group not in only_groups:
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
    fixed = ["Außenrahmen", "Servo Außenrahmen W5652H", "Rohr unten 75x500", "Beinring unten (Hülse)", "Endring unten"]
    pairs = [(a, b) for a in moving_inner for b in fixed] + [(a, b) for a in moving_motor for b in ("Innenrahmen", "Servo Innenrahmen W5652H")]
    bad = []
    for a, b in pairs:
        try:
            v = cq.Workplane().add(by[a]).intersect(cq.Workplane().add(by[b])).val().Volume()
        except Exception:
            v = 0.0
        if v > 0.5:
            bad.append((a, b, v))
    print(f"Kollisionsprüfung bei ±{deg:.0f}° Pitch und Yaw: " + ("frei" if not bad else "DURCHDRINGUNG"))
    for a, b, v in bad:
        print(f"  {a} / {b}: {v:.0f} mm³")
    return bad


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
    main()
