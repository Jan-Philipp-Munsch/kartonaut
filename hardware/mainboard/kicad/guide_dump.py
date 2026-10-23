"""Board geometry for make_guide.py (KiCad Python, read-only).

    "%LOCALAPPDATA%/Programs/KiCad/10.0/bin/python.exe" guide_dump.py   ->  out/guide/board.json

Footprints (reference, value, courtyard box, pads), tracks, vias, zone fills, rule areas and the outline,
all in KiCad mm (x right, y down)."""
import json
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
OUT = HERE / "out" / "guide"
OUT.mkdir(parents=True, exist_ok=True)
b = pcbnew.LoadBoard(str(HERE / "mainboard.kicad_pcb"))
mm = pcbnew.ToMM
CU = {pcbnew.F_Cu: "F.Cu", pcbnew.In1_Cu: "In1.Cu", pcbnew.In2_Cu: "In2.Cu", pcbnew.B_Cu: "B.Cu"}


def polys(ps):
    out = []
    for i in range(ps.OutlineCount()):
        o = ps.COutline(i)
        ring = [(round(mm(o.CPoint(k).x), 3), round(mm(o.CPoint(k).y), 3)) for k in range(o.PointCount())]
        holes = []
        for h in range(ps.HoleCount(i)):
            c = ps.CHole(i, h)
            holes.append([(round(mm(c.CPoint(k).x), 3), round(mm(c.CPoint(k).y), 3)) for k in range(c.PointCount())])
        out.append([ring, holes])
    return out


g = {"outline": None, "footprints": [], "tracks": [], "vias": [], "zones": [], "rules": []}
bb = b.GetBoardEdgesBoundingBox()
g["outline"] = [mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom())]
for fp in b.GetFootprints():
    c = fp.GetCourtyard(pcbnew.F_CrtYd)
    box = c.BBox() if c.OutlineCount() else fp.GetBoundingBox(False)
    pads = []
    for p in fp.Pads():
        s = p.GetSize()
        pads.append({"num": p.GetNumber(), "net": p.GetNetname(), "x": mm(p.GetPosition().x), "y": mm(p.GetPosition().y),
                     "sx": mm(s.x), "sy": mm(s.y), "rot": p.GetOrientation().AsDegrees(),
                     "round": p.GetShape() in (pcbnew.PAD_SHAPE_CIRCLE, pcbnew.PAD_SHAPE_OVAL),
                     "pth": p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH, "drill": mm(p.GetDrillSize().x),
                     "layers": [n for l, n in CU.items() if p.IsOnLayer(l)]})
    g["footprints"].append({"ref": fp.GetReference(), "value": fp.GetValue(), "x": mm(fp.GetPosition().x),
                            "y": mm(fp.GetPosition().y), "rot": fp.GetOrientation().AsDegrees(),
                            "box": [mm(box.GetLeft()), mm(box.GetTop()), mm(box.GetRight()), mm(box.GetBottom())],
                            "pads": pads})
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        g["vias"].append({"x": mm(t.GetPosition().x), "y": mm(t.GetPosition().y), "d": mm(t.GetWidth(pcbnew.F_Cu)),
                          "drill": mm(t.GetDrillValue()), "net": t.GetNetname()})
    else:
        g["tracks"].append({"x1": mm(t.GetStart().x), "y1": mm(t.GetStart().y), "x2": mm(t.GetEnd().x),
                            "y2": mm(t.GetEnd().y), "w": mm(t.GetWidth()), "layer": b.GetLayerName(t.GetLayer()),
                            "net": t.GetNetname()})
for z in b.Zones():
    if z.GetIsRuleArea():
        g["rules"].append({"name": z.GetZoneName(), "layers": [n for l, n in CU.items() if z.IsOnLayer(l)],
                           "poly": polys(z.Outline())})
        continue
    for l, n in CU.items():
        if z.IsOnLayer(l):
            g["zones"].append({"name": z.GetZoneName(), "net": z.GetNetname(), "layer": n,
                               "fill": polys(z.GetFilledPolysList(l))})
(OUT / "board.json").write_text(json.dumps(g), encoding="utf-8")
print(f"{len(g['footprints'])} footprints, {len(g['tracks'])} tracks, {len(g['vias'])} vias, {len(g['zones'])} zone layers")
