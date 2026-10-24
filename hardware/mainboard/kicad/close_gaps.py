"""Close the connections Freerouting left open, in the board file (KiCad Python).

    python.exe close_gaps.py dump     board geometry and the open connections of out/drc.json -> out/geom.json
    python  route_gaps.py             (system Python with numpy/scipy) routes them -> out/routes.json
    python.exe close_gaps.py apply    adds those tracks and vias to the board, refills the zones

Then `./make.sh drc`. Repeat while the DRC still lists open connections.
"""
import json
import sys
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
PCB = HERE / "mainboard.kicad_pcb"
mm = pcbnew.ToMM
MM = pcbnew.FromMM
COPPER = ("F.Cu", "In1.Cu", "In2.Cu", "B.Cu")


def poly_list(polys):
    """[[outline, [hole, ...]], ...] in mm for a SHAPE_POLY_SET."""
    out = []
    for i in range(polys.OutlineCount()):
        o = polys.COutline(i)
        ring = [(mm(o.CPoint(k).x), mm(o.CPoint(k).y)) for k in range(o.PointCount())]
        holes = []
        for h in range(polys.HoleCount(i)):
            c = polys.CHole(i, h)
            holes.append([(mm(c.CPoint(k).x), mm(c.CPoint(k).y)) for k in range(c.PointCount())])
        out.append([ring, holes])
    return out


def dump():
    board = pcbnew.LoadBoard(str(PCB))
    lname = {l: board.GetLayerName(l) for l in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)}
    layer_id = {v: k for k, v in lname.items()}
    g = {"res": 0.05, "layers": list(COPPER), "tracks": [], "vias": [], "pads": [], "zones": [], "rules": [],
         "nets": {}, "gaps": []}
    bb = board.GetBoardEdgesBoundingBox()
    g["board"] = [mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom())]
    # net classes (circuit.py): clearance and width per net; the DRC takes the larger clearance of a pair
    sys.path.insert(0, str(HERE))
    import circuit
    by_net = {n: (name, c[1], c[0]) for name, c in circuit.NETCLASSES.items() for n in c[4]}
    for code, net in board.GetNetInfo().NetsByNetcode().items():
        name, clearance, width = by_net.get(net.GetNetname(), ("Default", 0.15, 0.2))
        g["nets"][code] = {"name": net.GetNetname(), "class": name, "clearance": clearance, "width": width}
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            g["vias"].append({"x": mm(t.GetPosition().x), "y": mm(t.GetPosition().y),
                              "d": mm(t.GetWidth(pcbnew.F_Cu)), "net": t.GetNetCode()})
        elif t.GetClass() == "PCB_TRACK":
            g["tracks"].append({"x1": mm(t.GetStart().x), "y1": mm(t.GetStart().y), "x2": mm(t.GetEnd().x),
                                "y2": mm(t.GetEnd().y), "w": mm(t.GetWidth()), "layer": lname.get(t.GetLayer(), "?"),
                                "net": t.GetNetCode()})
    for fp in board.GetFootprints():
        for p in fp.Pads():
            layers = [lname[l] for l in lname if p.IsOnLayer(l)]
            if not layers:
                continue
            g["pads"].append({"ref": f"{fp.GetReference()}-{p.GetNumber()}", "x": mm(p.GetPosition().x),
                              "y": mm(p.GetPosition().y), "sx": mm(p.GetSize().x), "sy": mm(p.GetSize().y),
                              "rot": p.GetOrientationDegrees(), "circle": p.GetShape() == pcbnew.PAD_SHAPE_CIRCLE,
                              "layers": layers, "pth": p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH,
                              "drill": mm(p.GetDrillSize().x), "net": p.GetNetCode()})
    for z in board.Zones():
        layers = [lname[l] for l in lname if z.IsOnLayer(l)]
        if z.GetIsRuleArea():
            o = z.Outline().COutline(0)
            g["rules"].append({"name": z.GetZoneName(), "layers": layers, "tracks": z.GetDoNotAllowTracks(),
                               "vias": z.GetDoNotAllowVias(),
                               "poly": [(mm(o.CPoint(k).x), mm(o.CPoint(k).y)) for k in range(o.PointCount())]})
            continue
        for layer in layers:
            g["zones"].append({"name": z.GetZoneName(), "layer": layer, "net": z.GetNetCode(),
                               "islands": poly_list(z.GetFilledPolysList(layer_id[layer]))})
    d = json.loads((HERE / "out" / "drc.json").read_text(encoding="utf-8"))
    for n, u in enumerate(d["unconnected_items"], 1):
        items = []
        for i in u["items"]:
            it = board.ResolveItem(pcbnew.KIID(i["uuid"]))
            if it is None:
                break
            it = it.Cast()
            cls = it.GetClass()
            if cls == "PAD":
                items.append({"type": "pad", "ref": f"{it.GetParentFootprint().GetReference()}-{it.GetNumber()}",
                              "x": mm(it.GetPosition().x), "y": mm(it.GetPosition().y),
                              "layers": [lname[l] for l in lname if it.IsOnLayer(l)]})
            elif cls == "PCB_TRACK":
                items.append({"type": "track", "x1": mm(it.GetStart().x), "y1": mm(it.GetStart().y),
                              "x2": mm(it.GetEnd().x), "y2": mm(it.GetEnd().y), "layer": lname[it.GetLayer()]})
            elif cls == "PCB_VIA":
                items.append({"type": "via", "x": mm(it.GetPosition().x), "y": mm(it.GetPosition().y)})
            elif cls == "ZONE":
                layer = next(lname[l] for l in lname if it.IsOnLayer(l))
                items.append({"type": "zone", "name": it.GetZoneName(), "layer": layer,
                              "islands": poly_list(it.GetFilledPolysList(layer_id[layer]))})
            else:
                items.append({"type": cls})
        if len(items) == 2:
            net = board.ResolveItem(pcbnew.KIID(u["items"][0]["uuid"])).Cast().GetNetCode()
            g["gaps"].append({"n": n, "net": net, "items": items})
    (HERE / "out" / "geom.json").write_text(json.dumps(g), encoding="utf-8")
    print(f"geom.json: {len(g['tracks'])} tracks, {len(g['vias'])} vias, {len(g['pads'])} pads, "
          f"{len(g['zones'])} zone layers, {len(g['rules'])} rule areas, {len(g['gaps'])} gaps")


def apply():
    board = pcbnew.LoadBoard(str(PCB))
    layer_id = {board.GetLayerName(l): l for l in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)}
    r = json.loads((HERE / "out" / "routes.json").read_text(encoding="utf-8"))
    # ripped-up items: the router names them by their index in the dump, which enumerated the board in order
    tracks = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"]
    vias = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
    for i in r.get("removed_tracks", []):
        board.Delete(tracks[i])
    for i in r.get("removed_vias", []):
        board.Delete(vias[i])
    n_seg = n_via = 0
    for gap in r["gaps"]:
        net = board.GetNetInfo().GetNetItem(gap["net"])
        for x1, y1, x2, y2, layer, w in gap["segments"]:
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pcbnew.VECTOR2I(MM(x1), MM(y1)))
            t.SetEnd(pcbnew.VECTOR2I(MM(x2), MM(y2)))
            t.SetLayer(layer_id[layer])
            t.SetWidth(MM(w))
            t.SetNet(net)
            board.Add(t)
            n_seg += 1
        for x, y in gap["vias"]:
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
            v.SetWidth(MM(0.6))
            v.SetDrill(MM(0.3))
            v.SetNet(net)
            board.Add(v)
            n_via += 1
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(str(PCB), board, True)
    print(f"{n_seg} segments and {n_via} vias added for {len(r['gaps'])} connections, "
          f"{len(r.get('removed_tracks', []))} tracks and {len(r.get('removed_vias', []))} vias removed")


if __name__ == "__main__":
    {"dump": dump, "apply": apply}[sys.argv[1]]()
