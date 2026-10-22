"""The open connections of the board, from out/drc.json: what, where, how far apart, what is in between.

    python.exe gaps.py            list
    python.exe gaps.py png        plus a picture per cluster in out/gap_<n>_{top,inner}.png (F.Cu; In2 + B.Cu)
"""
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
PCB = HERE / "mainboard.kicad_pcb"
mm = pcbnew.ToMM


def reach(it):
    """Connectable points of an item: (x, y, layer name)."""
    b = it.GetBoard()
    cls = it.GetClass()
    if cls in ("PCB_TRACK", "PCB_ARC"):
        return [(mm(it.GetStart().x), mm(it.GetStart().y), b.GetLayerName(it.GetLayer())),
                (mm(it.GetEnd().x), mm(it.GetEnd().y), b.GetLayerName(it.GetLayer()))]
    if cls == "PCB_VIA":
        p = it.GetPosition()
        return [(mm(p.x), mm(p.y), "via")]
    if cls == "PAD":
        p = it.GetPosition()
        return [(mm(p.x), mm(p.y), "pth" if it.GetAttribute() == pcbnew.PAD_ATTRIB_PTH else b.GetLayerName(it.GetLayer()))]
    if cls == "ZONE":
        bb = it.GetBoundingBox()
        return [(mm(bb.GetCenter().x), mm(bb.GetCenter().y), "zone " + "/".join(b.GetLayerName(l) for l in it.GetLayerSet().Seq()))]
    return []


def describe(it):
    cls = it.GetClass()
    if cls in ("PCB_TRACK", "PCB_ARC"):
        return f"track {mm(it.GetWidth()):.2f} on {it.GetBoard().GetLayerName(it.GetLayer())} ({mm(it.GetStart().x):.2f},{mm(it.GetStart().y):.2f})-({mm(it.GetEnd().x):.2f},{mm(it.GetEnd().y):.2f})"
    if cls == "PCB_VIA":
        p = it.GetPosition()
        return f"via ({mm(p.x):.2f},{mm(p.y):.2f})"
    if cls == "PAD":
        p = it.GetPosition()
        bb = it.GetBoundingBox()
        return f"pad {it.GetParentFootprint().GetReference()}-{it.GetNumber()} ({mm(p.x):.2f},{mm(p.y):.2f}) {mm(bb.GetWidth()):.2f}x{mm(bb.GetHeight()):.2f} {'PTH' if it.GetAttribute() == pcbnew.PAD_ATTRIB_PTH else 'SMD'}"
    if cls == "ZONE":
        return f"zone '{it.GetZoneName()}' {it.GetBoard().GetLayerName(it.GetFirstLayer())} fills={it.GetFilledPolysList(it.GetFirstLayer()).OutlineCount()}"
    return cls


def main():
    board = pcbnew.LoadBoard(str(PCB))
    d = json.loads((HERE / "out" / "drc.json").read_text(encoding="utf-8"))
    gaps = []
    for n, u in enumerate(d["unconnected_items"], 1):
        items = [board.ResolveItem(pcbnew.KIID(i["uuid"])) for i in u["items"]]
        items = [i.Cast() for i in items if i is not None]
        net = items[0].GetNetname()
        pts = [(a, b, math.hypot(a[0] - b[0], a[1] - b[1])) for a in reach(items[0]) for b in reach(items[1])]
        a, b, dist = min(pts, key=lambda t: t[2])
        print(f"{n:2d} {net:12s} d={dist:5.2f}  {describe(items[0])}  <->  {describe(items[1])}")
        gaps.append((n, net, a, b, items))
    if "png" not in sys.argv:
        return
    # pictures: kicad-cli exports the layers as PDF, crop.py (system Python with pymupdf) cuts the windows
    cli = Path(os.environ["LOCALAPPDATA"]) / "Programs/KiCad/10.0/bin/kicad-cli.exe"
    for name, layers in (("top", "F.Cu,F.Fab,Edge.Cuts"), ("inner", "In2.Cu,B.Cu,Edge.Cuts")):
        subprocess.run([str(cli), "pcb", "export", "pdf", "--layers", layers, "--mode-single", "--include-border-title",
                        "-o", str(HERE / "out" / f"gaps_{name}.pdf"), str(PCB)], check=True, capture_output=True)
    # clusters: gaps within 7 mm of each other share a picture
    centers = []
    for n, net, a, b, items in gaps:
        cx, cy = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        for c in centers:
            if math.hypot(c["x"] - cx, c["y"] - cy) < 7:
                c["ids"].append(n)
                break
        else:
            centers.append({"x": cx, "y": cy, "ids": [n]})
    windows = []
    for k, c in enumerate(centers, 1):
        xs = [p[0] for n, net, a, b, items in gaps if n in c["ids"] for p in (a, b)]
        ys = [p[1] for n, net, a, b, items in gaps if n in c["ids"] for p in (a, b)]
        x0, x1, y0, y1 = min(xs) - 5, max(xs) + 5, min(ys) - 5, max(ys) + 5
        windows.append({"k": k, "ids": c["ids"], "x0": x0, "x1": x1, "y0": y0, "y1": y1})
        print(f"cluster {k}: gaps {c['ids']}  window x {x0:.1f}..{x1:.1f} y {y0:.1f}..{y1:.1f}  (u {x0-127:.1f}..{x1-127:.1f}, v {170-y1:.1f}..{170-y0:.1f})")
    (HERE / "out" / "gaps_windows.json").write_text(json.dumps(windows), encoding="utf-8")


if __name__ == "__main__":
    main()
