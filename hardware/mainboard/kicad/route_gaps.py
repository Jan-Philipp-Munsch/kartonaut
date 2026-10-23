"""Grid router for the open connections of out/geom.json (close_gaps.py dump) -> out/routes.json.

System Python (numpy, scipy, PIL). A* on a 0.1 mm grid over F.Cu and In2.Cu (B.Cu only for the nets
that own a plane there, F.Cu only for the class Strom), vias where a 0.6 mm via keeps clear of every
other net on all four layers. An endpoint is the whole piece of copper it belongs to (pad, stubs, vias),
so the router reaches it from free space. Clearance: the net class of the routed net, 0.2 mm against
the current-carrying classes. The GND pours on F.Cu and In2.Cu are no obstacle (they are filled around
the new copper afterwards); the current paths on F.Cu and the planes on B.Cu are. Rule areas of the
board and the 5 mm IMU zone (no foreign vias) are respected, 0.6 mm to the board edge.

Where a pin is boxed in, signal tracks (never pads, zones or the current classes) that hem in the
endpoint are ripped up, the connection is routed, and the ripped nets are routed again; if that does
not work out, everything is put back.

    python route_gaps.py [n ...]        route all gaps, or only the numbered ones
    python route_gaps.py debug n ...    pictures out/route_debug_<n>_<layer>.png and counts
"""
import heapq
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

HERE = Path(__file__).resolve().parent
G = json.loads((HERE / "out" / "geom.json").read_text(encoding="utf-8"))
RES = G["res"]
K = 0.1 / RES            # cell counts below were set for 0.1 mm cells
X0, Y0, X1, Y1 = G["board"]
NX, NY = int(round((X1 - X0) / RES)) + 1, int(round((Y1 - Y0) / RES)) + 1
LAYERS = G["layers"]                      # F.Cu In1.Cu In2.Cu B.Cu
NETS = {int(k): v for k, v in G["nets"].items()}
HI = {n for n, v in NETS.items() if v["clearance"] >= 0.2}     # classes with 0.2 mm clearance
NO_RIP = {n for n, v in NETS.items() if v["class"] in ("Strom", "Rueckstrom")}
PLANE_NET = {"GND": "In1.Cu", "GND_PWR": "B.Cu", "5V_SYS": "B.Cu"}
VIA_R, VIA_COST = 0.3, 25 * K
EDGE_TRACK, EDGE_VIA = 0.6, 1.0
MARGIN = 0.06            # raster: copper edges lie up to 0.05 mm (0.7 cells) outside the painted cell centres
MAX_RIP_NETS, MAX_RIP_TRACKS, RIP_ROUNDS = 30, 160, 3
RIP_DEPTH = 1            # a ripped net may itself rip up others once
VERBOSE = "-v" in sys.argv

TRACKS = [dict(t, id=i, removed=False) for i, t in enumerate(G["tracks"])]
VIAS = [dict(v, id=i, removed=False) for i, v in enumerate(G["vias"])]
occ = {l: np.full((NY, NX), -1, np.int32) for l in LAYERS}        # net of the copper in a cell
solid = {l: np.full((NY, NX), -1, np.int32) for l in LAYERS}      # the same without zone fills
tid = {l: np.full((NY, NX), -1, np.int32) for l in LAYERS}        # track id in a cell
vid = np.full((NY, NX), -1, np.int32)                             # via id in a cell
no_track = {l: np.zeros((NY, NX), bool) for l in LAYERS}
no_via = np.zeros((NY, NX), bool)
JJ, II = np.mgrid[0:NY, 0:NX]
XX, YY = X0 + II * RES, Y0 + JJ * RES
RING3 = np.ones((3, 3), bool)


def cell(x, y):
    return int(round((y - Y0) / RES)), int(round((x - X0) / RES))


def window(x, y, r):
    j0, i0 = cell(x - r, y - r)
    j1, i1 = cell(x + r, y + r)
    return slice(max(j0, 0), min(j1 + 1, NY)), slice(max(i0, 0), min(i1 + 1, NX))


def seg_mask(x1, y1, x2, y2, w):
    def f(X, Y):
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        t = np.clip(((X - x1) * dx + (Y - y1) * dy) / L2, 0, 1) if L2 > 0 else 0
        return np.hypot(X - (x1 + t * dx), Y - (y1 + t * dy)) <= w / 2 + 1e-6
    return f


def rect_mask(x, y, sx, sy, rot, circle):
    def f(X, Y):
        if circle:
            return np.hypot(X - x, Y - y) <= sx / 2 + 1e-6
        a = math.radians(-rot)
        dx, dy = X - x, Y - y
        u = dx * math.cos(a) - dy * math.sin(a)
        v = dx * math.sin(a) + dy * math.cos(a)
        return (np.abs(u) <= sx / 2 + 1e-6) & (np.abs(v) <= sy / 2 + 1e-6)
    return f


def polygon_mask(ring, holes=()):
    img = Image.new("1", (NX, NY), 0)
    d = ImageDraw.Draw(img)
    d.polygon([((x - X0) / RES, (y - Y0) / RES) for x, y in ring], fill=1)
    for h in holes:
        d.polygon([((x - X0) / RES, (y - Y0) / RES) for x, y in h], fill=0)
    return np.array(img, bool)


def track_geom(t):
    r = max(abs(t["x2"] - t["x1"]), abs(t["y2"] - t["y1"])) / 2 + t["w"] / 2 + RES
    return seg_mask(t["x1"], t["y1"], t["x2"], t["y2"], t["w"]), (t["x1"] + t["x2"]) / 2, (t["y1"] + t["y2"]) / 2, r


def paint(mask_fn, x, y, r, layers, net, track_id=-1, via_id=-1):
    win = window(x, y, r)
    m = mask_fn(XX[win], YY[win])
    for l in layers:
        occ[l][win][m] = net
        solid[l][win][m] = net
        if track_id >= 0:
            tid[l][win][m] = track_id
    if via_id >= 0:
        vid[win][m] = via_id


def paint_track(t):
    f, x, y, r = track_geom(t)
    paint(f, x, y, r, [t["layer"]], t["net"], track_id=t["id"])


def paint_via(v):
    paint(rect_mask(v["x"], v["y"], v["d"], v["d"], 0, True), v["x"], v["y"], v["d"] / 2 + RES, LAYERS, v["net"],
          via_id=v["id"])


def paint_zone(z):
    for ring, holes in z["islands"]:
        m = polygon_mask(ring, holes)
        tgt = occ[z["layer"]]
        tgt[m & (tgt == -1)] = z["net"]


def unpaint(item, layers):
    """Take an item out of the grids and paint everything else of its net in that window again."""
    if "layer" in item:
        f, x, y, r = track_geom(item)
    else:
        f, x, y, r = rect_mask(item["x"], item["y"], item["d"], item["d"], 0, True), item["x"], item["y"], item["d"] / 2 + RES
    win = window(x, y, r)
    m = f(XX[win], YY[win])
    for l in layers:
        for grid in (occ[l], solid[l], tid[l]):
            grid[win][m] = -1
    vid[win][m] = -1
    xa, xb, ya, yb = x - r, x + r, y - r, y + r
    net = item["net"]
    for t in TRACKS:
        if t["net"] == net and not t["removed"] and t is not item and \
                min(t["x1"], t["x2"]) - t["w"] <= xb and max(t["x1"], t["x2"]) + t["w"] >= xa and \
                min(t["y1"], t["y2"]) - t["w"] <= yb and max(t["y1"], t["y2"]) + t["w"] >= ya:
            paint_track(t)
    for v in VIAS:
        if v["net"] == net and not v["removed"] and v is not item and xa <= v["x"] <= xb and ya <= v["y"] <= yb:
            paint_via(v)
    for p in G["pads"]:
        if p["net"] == net and abs(p["x"] - x) <= r + 2 and abs(p["y"] - y) <= r + 2:
            paint(rect_mask(p["x"], p["y"], p["sx"], p["sy"], p["rot"], p["circle"]), p["x"], p["y"],
                  max(p["sx"], p["sy"]) / 2 + RES, p["layers"], p["net"])
    for z in G["zones"]:
        if z["net"] == net and z["name"] not in ("GND F.Cu", "GND In2.Cu", "GND In1.Cu"):
            paint_zone(z)


def build():
    for t in TRACKS:
        paint_track(t)
    for v in VIAS:
        paint_via(v)
    for p in G["pads"]:
        paint(rect_mask(p["x"], p["y"], p["sx"], p["sy"], p["rot"], p["circle"]), p["x"], p["y"],
              max(p["sx"], p["sy"]) / 2 + RES, p["layers"], p["net"])
    for z in G["zones"]:
        if z["name"] not in ("GND F.Cu", "GND In2.Cu", "GND In1.Cu"):
            paint_zone(z)
    for r in G["rules"]:
        m = polygon_mask(r["poly"])
        for l in r["layers"]:
            if r["tracks"]:
                no_track[l] |= m
        if r["vias"]:
            no_via[:] |= m
        if r["name"] == "IMU ruhige Masse":             # 5 mm zone: no foreign vias (spec 8 / B16)
            cx, cy = np.mean([p[0] for p in r["poly"]]), np.mean([p[1] for p in r["poly"]])
            no_via[:] |= np.hypot(XX - cx, YY - cy) <= 5.0
    return np.minimum(np.minimum(XX - X0, X1 - XX), np.minimum(YY - Y0, Y1 - YY))


EDGE = build()
PADS_F = ndimage.binary_dilation(np.isin(solid["F.Cu"], [p["net"] for p in G["pads"]]) & (solid["F.Cu"] != -1),
                                 iterations=int(round(VIA_R / RES)))   # no via in or at a pad


def snapshot():
    return ({l: occ[l].copy() for l in LAYERS}, {l: solid[l].copy() for l in LAYERS},
            {l: tid[l].copy() for l in LAYERS}, vid.copy(), [t["removed"] for t in TRACKS], [v["removed"] for v in VIAS])


def restore(s):
    o, so, ti, vi, tr, vr = s
    for l in LAYERS:
        occ[l][:] = o[l]
        solid[l][:] = so[l]
        tid[l][:] = ti[l]
    vid[:] = vi
    for t, f in zip(TRACKS, tr):
        t["removed"] = f
    for v, f in zip(VIAS, vr):
        v["removed"] = f


def edt(mask):
    """Distance (mm) from every cell to the nearest True cell."""
    if not mask.any():
        return np.full(mask.shape, 1e9)
    return ndimage.distance_transform_edt(~mask) * RES


class Net:
    """Passability grids for one net at one track width."""

    def __init__(self, net, width, layers):
        self.net, self.w, self.layers = net, width, layers
        c = NETS[net]["clearance"]
        self.ok = {}
        for l in layers:
            other = (occ[l] != -1) & (occ[l] != net)
            hi = other & np.isin(occ[l], list(HI))
            keep_out = ndimage.binary_dilation(no_track[l], iterations=int(round((width / 2 + 0.05) / RES)))
            self.ok[l] = ((edt(hi) >= 0.2 + width / 2 + MARGIN) & (edt(other) >= c + width / 2 + MARGIN)
                          & ~keep_out & (EDGE >= EDGE_TRACK))
        via = ~no_via & (EDGE >= EDGE_VIA)
        for l in LAYERS:
            src = occ[l] if l in ("F.Cu", "In2.Cu") else solid[l]
            other = (src != -1) & (src != net)
            via &= edt(other) >= 0.2 + VIA_R + MARGIN
        self.via = via


class Components:
    """Connected copper of one net: 8-connected cells per layer, joined across layers by its vias and
    through-hole pads."""

    def __init__(self, net):
        self.labs = {l: ndimage.label(occ[l] == net, structure=RING3)[0] for l in LAYERS}
        self.parent = {}
        for v in [v for v in VIAS if not v["removed"]] + [p for p in G["pads"] if p["pth"]]:
            if v["net"] != net:
                continue
            j, i = cell(v["x"], v["y"])
            ids = [(l, int(self.labs[l][j, i])) for l in LAYERS if self.labs[l][j, i] > 0]
            for b in ids[1:]:
                self.union(ids[0], b)
        self.members = {}
        for l in LAYERS:
            for lab in range(1, int(self.labs[l].max()) + 1):
                self.members.setdefault(self.find((l, lab)), []).append((l, lab))

    def find(self, a):
        while self.parent.get(a, a) != a:
            a = self.parent[a]
        return a

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra

    def roots(self, seeds):
        return {self.find((l, int(self.labs[l][j, i]))) for l, j, i in seeds if self.labs[l][j, i] > 0}

    def root_mask(self, root, layers):
        out = {l: np.zeros((NY, NX), bool) for l in layers}
        for l, lab in self.members.get(root, []):
            if l in out:
                out[l] |= self.labs[l] == lab
        return out

    def masks(self, seeds, layers):
        """{layer: mask} of every cell connected to the seed cells [(layer, j, i)]."""
        out = {l: np.zeros((NY, NX), bool) for l in layers}
        for r in self.roots(seeds):
            for l, lab in self.members.get(r, []):
                if l in out:
                    out[l] |= self.labs[l] == lab
        for l, j, i in seeds:
            if l in out:
                out[l][j, i] = True
        return out


def island_cells(islands):
    m = np.zeros((NY, NX), bool)
    for ring, holes in islands:
        m |= polygon_mask(ring, holes)
    return m


def seeds_of(item):
    if item["type"] == "pad":
        j, i = cell(item["x"], item["y"])
        return [(l, j, i) for l in LAYERS if l in item["layers"]]
    if item["type"] == "track":
        return [(item["layer"], *cell(x, y)) for x, y in ((item["x1"], item["y1"]), (item["x2"], item["y2"]))]
    if item["type"] == "via":
        j, i = cell(item["x"], item["y"])
        return [(l, j, i) for l in LAYERS]
    return []


def endpoint(item, net, layers, comp):
    """(exact point(s) or None, {layer: bool mask of the copper piece the item belongs to})."""
    if item["type"] == "zone":                         # the island itself, no expansion (a stub next to it
        m = island_cells(item["islands"])              # touches it in the raster but not on the board)
        out = {l: np.zeros((NY, NX), bool) for l in layers}
        if item["layer"] in out:
            out[item["layer"]] = m
        return None, out
    if item["type"] == "track":
        pts = [(item["x1"], item["y1"]), (item["x2"], item["y2"])]
    else:
        pts = (item["x"], item["y"])
    return pts, comp.masks(seeds_of(item), layers)


def reach(n, starts):
    """Cells reachable from the start cells layer by layer (no vias): the pocket an endpoint sits in."""
    out = {}
    for l in n.layers:
        passable = n.ok[l] | starts[l]
        lab, k = ndimage.label(passable, structure=RING3)
        ids = np.unique(lab[starts[l]])
        out[l] = np.isin(lab, ids[ids > 0])
    return out


def blockers(n, pocket, net, other=None):
    """Tracks and vias of other nets (not of the current classes) that hem the pocket in; with
    `other` (a second pocket) only those in the wall between the two."""
    tracks, vias = set(), set()
    for l in n.layers:
        rim = ndimage.binary_dilation(pocket[l], RING3, iterations=int(6 * K)) & ~pocket[l]
        if other is not None:
            rim &= ndimage.binary_dilation(other[l], RING3, iterations=int(6 * K)) & ~other[l]
        for t in np.unique(tid[l][rim]):
            if t >= 0 and TRACKS[t]["net"] not in NO_RIP | {net} and not TRACKS[t]["removed"]:
                tracks.add(int(t))
        for v in np.unique(vid[rim]):
            if v >= 0 and VIAS[v]["net"] not in NO_RIP | {net} and not VIAS[v]["removed"]:
                vias.add(int(v))
    return tracks, vias


def astar(n, starts, goals, drop=None):
    """Cheapest path from any start cell to any goal cell (or a via-drop cell). Cells are (layer, j, i)."""
    layers = n.layers
    goal_any = np.zeros((NY, NX), bool)
    for l in layers:
        goal_any |= goals[l]
    if drop is not None:
        goal_any |= drop
    if not goal_any.any() or not any(starts[l].any() for l in layers):
        return None
    h = edt(goal_any) / RES
    js, is_ = np.nonzero(sum(starts[l] for l in layers))
    jg, ig = np.nonzero(goal_any)
    margin = int(150 * K)
    j0, j1 = max(min(js.min(), jg.min()) - margin, 0), min(max(js.max(), jg.max()) + margin, NY - 1)
    i0, i1 = max(min(is_.min(), ig.min()) - margin, 0), min(max(is_.max(), ig.max()) + margin, NX - 1)
    passable = {l: n.ok[l] | starts[l] | goals[l] for l in layers}
    via_ok = n.via
    dist, prev, heap = {}, {}, []
    for l in layers:
        for j, i in zip(*np.nonzero(starts[l])):
            dist[(l, j, i)] = 0.0
            heapq.heappush(heap, (h[j, i], 0.0, l, int(j), int(i)))
    steps = [(0, 1, 1.0), (0, -1, 1.0), (1, 0, 1.0), (-1, 0, 1.0),
             (1, 1, math.sqrt(2)), (1, -1, math.sqrt(2)), (-1, 1, math.sqrt(2)), (-1, -1, math.sqrt(2))]
    expanded = 0
    while heap:
        f, d, l, j, i = heapq.heappop(heap)
        if d > dist.get((l, j, i), 1e18):
            continue
        expanded += 1
        if goals[l][j, i] or (drop is not None and drop[j, i] and via_ok[j, i] and not starts[l][j, i]):
            path = [(l, j, i)]
            while path[-1] in prev:
                path.append(prev[path[-1]])
            path.reverse()
            return path, not goals[l][j, i]
        if expanded > 2_500_000 * K * K:
            return None
        for dj, di, c in steps:
            nj, ni = j + dj, i + di
            if nj < j0 or nj > j1 or ni < i0 or ni > i1 or not passable[l][nj, ni]:
                continue
            if dj and di and not (passable[l][j, ni] and passable[l][nj, i]):
                continue                                   # no squeezing diagonally between obstacles
            nd = d + c
            if nd < dist.get((l, nj, ni), 1e18):
                dist[(l, nj, ni)] = nd
                prev[(l, nj, ni)] = (l, j, i)
                heapq.heappush(heap, (nd + h[nj, ni], nd, l, nj, ni))
        if via_ok[j, i]:
            for l2 in layers:
                if l2 == l or not passable[l2][j, i]:
                    continue
                nd = d + VIA_COST
                if nd < dist.get((l2, j, i), 1e18):
                    dist[(l2, j, i)] = nd
                    prev[(l2, j, i)] = (l, j, i)
                    heapq.heappush(heap, (nd + h[j, i], nd, l2, j, i))
    return None


def to_segments(path, width, p_start, p_end):
    """Cells -> straight segments per layer (collinear runs merged) and vias at layer changes."""
    def xy(c):
        return X0 + c[2] * RES, Y0 + c[1] * RES
    segs, vias = [], []
    run_start, prev_dir = path[0], None
    for a, b in zip(path, path[1:]):
        if a[0] != b[0]:                                    # layer change: via
            if run_start != a:
                segs.append((*xy(run_start), *xy(a), a[0], width))
            vias.append(xy(a))
            run_start, prev_dir = b, None
            continue
        d = (b[1] - a[1], b[2] - a[2])
        if prev_dir is not None and d != prev_dir:
            segs.append((*xy(run_start), *xy(a), a[0], width))
            run_start = a
        prev_dir = d
    if run_start != path[-1]:
        segs.append((*xy(run_start), *xy(path[-1]), path[-1][0], width))

    def snap(p, c, at_start):                               # exact pad centre / track end instead of the cell
        if p is None:
            return
        pts = p if isinstance(p, list) else [p]
        x, y = xy(c)
        px, py = min(pts, key=lambda q: math.hypot(q[0] - x, q[1] - y))
        if 1e-6 < math.hypot(px - x, py - y) <= 0.15:
            segs.insert(0 if at_start else len(segs), (px, py, x, y, c[0], width))
    snap(p_start, path[0], True)
    snap(p_end, path[-1], False)
    return segs, vias


def add_copper(net, segs, vias):
    """New copper joins the item lists and the grids (an obstacle for what follows)."""
    for x1, y1, x2, y2, l, w in segs:
        t = {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "w": w, "layer": l, "net": net, "id": len(TRACKS), "removed": False}
        TRACKS.append(t)
        paint_track(t)
    for x, y in vias:
        v = {"x": x, "y": y, "d": 2 * VIA_R, "net": net, "id": len(VIAS), "removed": False}
        VIAS.append(v)
        paint_via(v)


def widths_for(net):
    cls = NETS[net]["class"]
    return [0.5, 0.3, 0.2] if cls in ("Strom", "Rueckstrom", "Versorgung") else [0.2, 0.15]


def layers_for(net):
    name, cls = NETS[net]["name"], NETS[net]["class"]
    if cls == "Strom":
        return ["F.Cu"]
    if name in ("GND_PWR", "5V_SYS"):
        return ["F.Cu", "In2.Cu", "B.Cu"]
    return ["F.Cu", "In2.Cu"]


def drop_cells(net):
    """Cells where a via would land on this net's own plane."""
    name = NETS[net]["name"]
    if name not in PLANE_NET:
        return None
    if name == "GND":
        return ~PADS_F
    own = occ["B.Cu"] == net
    k = int(round((VIA_R + 0.25) / RES))
    return ndimage.minimum_filter(own, size=2 * k + 1) & ~PADS_F


def max_width(item):
    """A track into an SMD pad must not be wider than the pad's narrow side."""
    if item["type"] != "pad":
        return 9
    pad = next(p for p in G["pads"] if p["ref"] == item["ref"])
    return 9 if pad["pth"] else min(pad["sx"], pad["sy"]) + 0.05


def try_route(net, a, b, label, log):
    """One attempt over the widths. Returns (route dict, note) or (None, reason)."""
    layers = layers_for(net)
    for w in widths_for(net):
        if w > min(max_width(a), max_width(b)):
            continue
        n = Net(net, w, layers)
        comp = Components(net)
        pa, sa = endpoint(a, net, layers, comp)
        pb, sb = endpoint(b, net, layers, comp)
        if any((sa[l] & sb[l]).any() for l in layers):
            return None, "already one piece of copper in the raster"
        drop = drop_cells(net) if a["type"] != "zone" and b["type"] != "zone" else None
        if drop is not None:
            drop = drop & n.via
        res = astar(n, sa, sb, drop)
        if res is None:
            continue
        path, dropped = res
        segs, vias = to_segments(path, w, pa, None if dropped else pb)
        if dropped:
            vias.append((X0 + path[-1][2] * RES, Y0 + path[-1][1] * RES))
        add_copper(net, segs, vias)
        length = sum(math.hypot(x2 - x1, y2 - y1) for x1, y1, x2, y2, l, w_ in segs)
        log.append(f"{NETS[net]['name']:12s} {label:34s} ok  w={w} len={length:5.1f} vias={len(vias)}"
                   + ("  (via onto the plane)" if dropped else ""))
        return {"net": net, "segments": [list(s) for s in segs], "vias": [list(v) for v in vias]}, "ok"
    return None, "no route"


def route_or_rip(net, a, b, label, log, depth):
    """try_route, and on 'no route' a rip-up of its own while depth allows. Returns (routes, why)."""
    r, why = try_route(net, a, b, label, log)
    if r is not None:
        return [r], "ok"
    if why != "no route" or depth <= 0:
        return None, why
    out, note = route_with_ripup(0, net, a, b, label, depth - 1)
    if out is None:
        return None, note
    log.append(note)
    return out, "ok"


def clear_segment(t):
    """Does a track keep its clearance from every other net where it is?"""
    f, x, y, r = track_geom(t)
    win = window(x, y, r + 0.5)
    m = f(XX[win], YY[win])
    other = (occ[t["layer"]][win] != -1) & (occ[t["layer"]][win] != t["net"])
    if not other.any():
        return True
    d = ndimage.distance_transform_edt(~other) * RES
    c = max(NETS[t["net"]]["clearance"], 0.2 if np.isin(occ[t["layer"]][win][other], list(HI)).any() else 0)
    return bool((d[m] >= c + t["w"] / 2 + MARGIN).all())


def reroute_ripped(removed_tracks, removed_vias, log, depth):
    """After a rip-up: join what the removed items held together. Yields routes; None on a failure."""
    for t in removed_tracks:
        ends = [{"type": "track", "x1": x, "y1": y, "x2": x, "y2": y, "layer": t["layer"]}
                for x, y in ((t["x1"], t["y1"]), (t["x2"], t["y2"]))]
        # a supply net gets no rip-up of its own, and no re-route may become a long detour
        d = 0 if t["net"] in HI else depth
        rs, why = route_or_rip(t["net"], ends[0], ends[1], f"re-route {NETS[t['net']]['name']}", log, d)
        r = None
        if rs is not None:
            was = math.hypot(t["x2"] - t["x1"], t["y2"] - t["y1"])
            if route_length(rs[-1]) > 3 * was + 6.0:
                log.append(f"{NETS[t['net']]['name']:12s} re-route failed: detour {route_length(rs[-1]):.1f} mm for {was:.1f} mm")
                yield None
                return
            for r in rs[:-1]:
                yield r
            r = rs[-1]
        if r is None and why.startswith("already"):
            # one piece in the raster, but the raster joins copper 0.1 mm apart that KiCad does not:
            # a short piece goes back as it was, a long one is trusted to be joined elsewhere
            length = math.hypot(t["x2"] - t["x1"], t["y2"] - t["y1"])
            if length <= 1.5 and clear_segment(t):
                seg = (t["x1"], t["y1"], t["x2"], t["y2"], t["layer"], t["w"])
                add_copper(t["net"], [seg], [])
                r = {"net": t["net"], "segments": [list(seg)], "vias": []}
            elif length <= 1.5:
                log.append(f"{NETS[t['net']]['name']:12s} re-route failed: its old place is taken")
                yield None
                return
            else:
                continue
        if r is None:
            log.append(f"{NETS[t['net']]['name']:12s} re-route failed: {why}")
            yield None
            return
        yield r
    for v in removed_vias:
        comp = Components(v["net"])
        j, i = cell(v["x"], v["y"])
        pieces = {}
        for l in ("F.Cu", "In2.Cu"):
            for r_ in comp.roots([(l, j, i)]):
                pieces.setdefault(r_, l)
        if len(pieces) < 2:
            continue
        la, lb = list(pieces.values())[:2]
        ends = [{"type": "track", "x1": v["x"], "y1": v["y"], "x2": v["x"], "y2": v["y"], "layer": l} for l in (la, lb)]
        rs, why = route_or_rip(v["net"], ends[0], ends[1], f"re-route {NETS[v['net']]['name']} (via)", log, depth)
        if rs is None:
            log.append(f"{NETS[v['net']]['name']:12s} re-route failed: {why}")
            yield None
            return
        yield from rs


def route_length(r):
    return sum(math.hypot(x2 - x1, y2 - y1) for x1, y1, x2, y2, l, w in r["segments"]) + 2.0 * len(r["vias"])


def straight(a, b):
    def pt(i):
        if i["type"] == "track":
            return (i["x1"] + i["x2"]) / 2, (i["y1"] + i["y2"]) / 2
        if i["type"] == "zone":
            ring = i["islands"][0][0]
            return sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring)
        return i["x"], i["y"]
    (xa, ya), (xb, yb) = pt(a), pt(b)
    return math.hypot(xa - xb, ya - yb)


def route_with_ripup(gap_n, net, a, b, label, depth=RIP_DEPTH):
    """Rip up the signal tracks that hem the endpoints in (up to RIP_ROUNDS rounds), route, route the
    ripped nets again. Returns (routes, log line) or (None, reason); the grids are left as routed."""
    layers = layers_for(net)
    removed_t, removed_v, nets_hit = [], [], set()
    r, why, log = None, "no route", []
    snap, n_tracks, n_vias = snapshot(), len(TRACKS), len(VIAS)

    def fail(reason):
        restore(snap)
        del TRACKS[n_tracks:]
        del VIAS[n_vias:]
        return None, reason

    for round_ in range(RIP_ROUNDS):
        n = Net(net, widths_for(net)[-1], layers)
        comp = Components(net)
        pa, sa = endpoint(a, net, layers, comp)
        pb, sb = endpoint(b, net, layers, comp)
        t_ids, v_ids = set(), set()
        pockets = [reach(n, m) for m in (sa, sb)]
        small = [sum(int(p[l].sum()) for l in layers) < 20000 * K * K for p in pockets]
        for p, is_small in zip(pockets, small):
            if is_small:
                t, v = blockers(n, p, net)
                t_ids |= t
                v_ids |= v
        if not any(small):                                # two open areas: what is the wall between them?
            t, v = blockers(n, pockets[0], net, pockets[1])
            t_ids |= t
            v_ids |= v
        if VERBOSE:
            print(f"     round {round_}: pockets {[sum(int(p[l].sum()) for l in layers) for p in pockets]}, "
                  f"rip {len(t_ids)} tracks / {len(v_ids)} vias of "
                  f"{sorted({NETS[TRACKS[i]['net']]['name'] for i in t_ids} | {NETS[VIAS[i]['net']]['name'] for i in v_ids})}")
            for p, m in zip(pockets, (sa, sb)):            # map of a small pocket: . passable, X other copper,
                if sum(int(p[l].sum()) for l in layers) < 2000 * K * K:   # o own copper, * pocket, ' ' clearance zone
                    l = layers[0]
                    js, is_ = np.nonzero(p[l])
                    j0, j1 = max(js.min() - 12, 0), min(js.max() + 12, NY - 1)
                    i0, i1 = max(is_.min() - 15, 0), min(is_.max() + 15, NX - 1)
                    legend = {}
                    for j in range(j0, j1 + 1):
                        row = ""
                        for i in range(i0, i1 + 1):
                            o = occ[l][j, i]
                            if p[l][j, i]:
                                row += "*"
                            elif o == net:
                                row += "o"
                            elif o != -1:
                                k = legend.setdefault(int(o), chr(ord("A") + len(legend) % 26))
                                row += k
                            else:
                                row += "." if n.ok[l][j, i] else " "
                        print("        " + row)
                    print("        " + ", ".join(f"{k}={NETS[v]['name'] if v in NETS else v}" for v, k in legend.items()))
        if not t_ids and not v_ids:
            return fail("nothing to rip up" if round_ == 0 else f"nothing more to rip up after {round_} rounds")
        nets_now = {TRACKS[i]["net"] for i in t_ids} | {VIAS[i]["net"] for i in v_ids} | nets_hit
        if len(nets_now) > MAX_RIP_NETS or len(removed_t) + len(t_ids) > MAX_RIP_TRACKS:
            names = sorted(NETS[x]["name"] for x in nets_now)
            return fail(f"{len(nets_now)} nets / {len(removed_t) + len(t_ids)} tracks hem it in, too many ({', '.join(names)})")
        for i in sorted(t_ids):
            t = TRACKS[i]
            t["removed"] = True
            unpaint(t, [t["layer"]])
            removed_t.append(t)
        for i in sorted(v_ids):
            v = VIAS[i]
            v["removed"] = True
            unpaint(v, LAYERS)
            removed_v.append(v)
        nets_hit = nets_now
        log = []
        r, why = try_route(net, a, b, label, log)
        if r is not None:
            break
    names = ", ".join(sorted(NETS[x]["name"] for x in nets_hit))
    if r is None:
        return fail(f"rip-up of {names} did not help: {why}")
    out = [dict(r, n=gap_n)]
    for m in reroute_ripped(removed_t, removed_v, log, depth):
        if m is None:
            return fail(f"rip-up of {names}: {log[-1].strip()}")
        out.append(dict(m, n=gap_n))
    note = f"{log[0]}  [ripped {len(removed_t)} tracks, {len(removed_v)} vias of {names}]"
    return out, note + "".join(f"\n     {l}" for l in log[1:])


def route_gap(gap_n, net, a, b, label):
    """Route one connection; with rip-up when there is no route, or when the plain route is a long
    detour (more than 2.5 times the straight distance plus 4 mm). Returns route dicts."""
    snap = snapshot()
    n_tracks, n_vias = len(TRACKS), len(VIAS)
    log = []
    r, why = try_route(net, a, b, label, log)
    if r is not None and route_length(r) <= 2.5 * straight(a, b) + 4.0:
        print(f"{gap_n:2d} {log[-1]}")
        return [dict(r, n=gap_n)]
    if r is None and why != "no route":
        print(f"{gap_n:2d} {NETS[net]['name']:12s} {label:34s} {why}")
        return []
    plain, plain_note = r, log[-1] if r is not None else None
    restore(snap)
    del TRACKS[n_tracks:]
    del VIAS[n_vias:]
    out, note = route_with_ripup(gap_n, net, a, b, label)
    if out is not None and (plain is None or route_length(out[0]) < route_length(plain)):
        print(f"{gap_n:2d} {note}")
        return out
    restore(snap)
    del TRACKS[n_tracks:]
    del VIAS[n_vias:]
    if plain is not None:                                   # the detour it is
        add_copper(net, [tuple(s) for s in plain["segments"]], [tuple(v) for v in plain["vias"]])
        print(f"{gap_n:2d} {plain_note}  (detour; rip-up: {note})")
        return [dict(plain, n=gap_n)]
    print(f"{gap_n:2d} {NETS[net]['name']:12s} {label:34s} NO ROUTE ({note})")
    return []


def debug(gap_n, width=None):
    """Picture per layer of a gap's surroundings: out/route_debug_<n>_<layer>.png. White passable, light
    grey clearance zone, dark grey other copper, blue own copper, yellow reachable from the start,
    green start, red goal, magenta tint where a via may go."""
    gap = next(x for x in G["gaps"] if x["n"] == gap_n)
    net, a, b = gap["net"], gap["items"][0], gap["items"][1]
    if a["type"] == "zone":
        a, b = b, a
    w = width or widths_for(net)[-1]
    layers = layers_for(net)
    n = Net(net, w, layers)
    comp = Components(net)
    pa, sa = endpoint(a, net, layers, comp)
    pb, sb = endpoint(b, net, layers, comp)
    cells = np.zeros((NY, NX), bool)
    for l in layers:
        cells |= sa[l] | (sb[l] if sb[l].sum() < 20000 * K * K else False)
    js, is_ = np.nonzero(cells)
    m = int(40 * K)
    j0, j1, i0, i1 = max(js.min() - m, 0), min(js.max() + m, NY - 1), max(is_.min() - m, 0), min(is_.max() + m, NX - 1)
    win = (slice(j0, j1 + 1), slice(i0, i1 + 1))
    for l in layers:
        passable = n.ok[l] | sa[l] | sb[l]
        lab, k = ndimage.label(passable[win])
        rch = np.isin(lab, np.unique(lab[sa[l][win]])) & (lab > 0)
        for name, mask in (("start", sa[l]), ("goal", sb[l])):
            edge_cells = ndimage.binary_dilation(mask, RING3) & ~mask
            print(f"    {l} {name}: {int(mask.sum())} cells, {int((edge_cells & n.ok[l]).sum())} passable neighbours, "
                  f"{int((edge_cells & n.via).sum())} via spots next to it")
        img = np.full((*lab.shape, 3), 200, np.uint8)
        img[passable[win]] = (255, 255, 255)
        img[rch] = (255, 240, 150)
        other = (occ[l][win] != -1) & (occ[l][win] != net)
        img[other] = (90, 90, 90)
        img[occ[l][win] == net] = (150, 190, 255)
        img[n.via[win]] = np.minimum(img[n.via[win]].astype(int) + (40, -40, 40), 255).clip(0, 255)
        img[sb[l][win]] = (230, 40, 40)
        img[sa[l][win]] = (30, 170, 30)
        scale = max(1, min(6, 1200 // max(lab.shape)))
        out = Image.fromarray(img).resize((img.shape[1] * scale, img.shape[0] * scale), Image.NEAREST)
        out.save(HERE / "out" / f"route_debug_{gap_n}_{l.replace('.', '')}.png")
        print(f"gap {gap_n} {l}: w={w} start cells {int(sa[l].sum())} goal cells {int(sb[l].sum())} "
              f"reachable {int(rch.sum())} window x {X0 + i0 * RES:.1f}..{X0 + i1 * RES:.1f} "
              f"y {Y0 + j0 * RES:.1f}..{Y0 + j1 * RES:.1f}")


def join_net(net, log):
    """Route between the pieces of a net until it is one piece (nearest pieces first). Returns the
    routes; stops at the first piece that cannot be joined (its name goes to the log)."""
    out = []
    while True:
        comp = Components(net)
        roots = [r for r in comp.members if any(l in ("F.Cu", "In2.Cu", "B.Cu") for l, lab in comp.members[r])]
        if len(roots) < 2:
            return out, True
        cent = {}
        for r in roots:
            m = sum(comp.root_mask(r, LAYERS).values())
            js, is_ = np.nonzero(m)
            cent[r] = (is_.mean(), js.mean(), len(js))
        pairs = sorted(((math.hypot(cent[a][0] - cent[b][0], cent[a][1] - cent[b][1]), a, b)
                        for i, a in enumerate(roots) for b in roots[i + 1:]))
        joined = False
        for d, a, b in pairs[:6]:
            layers = layers_for(net)
            for w in widths_for(net):
                n = Net(net, w, layers)
                sa, sb = comp.root_mask(a, layers), comp.root_mask(b, layers)
                res = astar(n, sa, sb, None)
                if res is None:
                    continue
                path, dropped = res
                segs, vias = to_segments(path, w, None, None)
                add_copper(net, segs, vias)
                out.append({"net": net, "segments": [list(x) for x in segs], "vias": [list(v) for v in vias]})
                log.append(f"{NETS[net]['name']:12s} joined two pieces ({d * RES:.1f} mm apart)  w={w} vias={len(vias)}")
                joined = True
                break
            if joined:
                break
        if not joined:
            log.append(f"{NETS[net]['name']:12s} stays in {len(roots)} pieces")
            return out, False


def region(x0, y0, x1, y1, only):
    """Rip up every signal track and via inside the rectangle, route the gaps, then join the ripped
    nets piece by piece. Failures are reported, not undone: the DRC afterwards is the measure."""
    keep = NO_RIP | {n for n, v in NETS.items() if v["name"] in PLANE_NET}
    removed_t = [t for t in TRACKS if t["net"] not in keep and x0 <= min(t["x1"], t["x2"]) and max(t["x1"], t["x2"]) <= x1
                 and y0 <= min(t["y1"], t["y2"]) and max(t["y1"], t["y2"]) <= y1]
    removed_v = [v for v in VIAS if v["net"] not in keep and x0 <= v["x"] <= x1 and y0 <= v["y"] <= y1]
    for t in removed_t:
        t["removed"] = True
        unpaint(t, [t["layer"]])
    for v in removed_v:
        v["removed"] = True
        unpaint(v, LAYERS)
    nets_hit = sorted({t["net"] for t in removed_t} | {v["net"] for v in removed_v}, key=lambda n: NETS[n]["name"])
    print(f"region {x0}..{x1} x {y0}..{y1}: ripped {len(removed_t)} tracks and {len(removed_v)} vias of "
          f"{len(nets_hit)} nets: {', '.join(NETS[n]['name'] for n in nets_hit)}")
    def inside(item):
        if item["type"] == "track":
            return x0 <= item["x1"] <= x1 and y0 <= item["y1"] <= y1
        if item["type"] == "zone":
            return False
        return x0 <= item["x"] <= x1 and y0 <= item["y"] <= y1
    out = []
    for gap in G["gaps"]:
        net, a, b = gap["net"], gap["items"][0], gap["items"][1]
        if only and gap["n"] not in only:
            continue
        if not only and not (inside(a) or inside(b)):
            continue
        if a["type"] == "zone" and b["type"] == "zone":
            continue
        if a["type"] == "zone":
            a, b = b, a
        label = " <-> ".join(i.get("ref") or i["type"] for i in (a, b))
        out += route_gap(gap["n"], net, a, b, label)
    # the ripped nets, supply classes first, then the signals with the fewest pieces
    order = sorted(nets_hit, key=lambda n: (n not in HI, NETS[n]["name"]))
    failed = []
    for net in order:
        log = []
        routes, ok = join_net(net, log)
        out += [dict(r, n=0) for r in routes]
        for l in log:
            print(f"     {l}")
        if not ok:
            failed.append(NETS[net]["name"])
    print(f"region done; nets left in pieces: {failed if failed else 'none'}")
    removed = [t["id"] for t in TRACKS[:len(G["tracks"])] if t["removed"]]
    removed_vias = [v["id"] for v in VIAS[:len(G["vias"])] if v["removed"]]
    (HERE / "out" / "routes.json").write_text(json.dumps({"gaps": out, "removed_tracks": removed,
                                                          "removed_vias": removed_vias}), encoding="utf-8")
    print(f"routes.json: {len(out)} connections, {len(removed)} tracks and {len(removed_vias)} vias ripped")


def drop(refs):
    """`drop REF-PIN ...`: a stub and a via from that pad onto its net's plane (GND, GND_PWR, 5V_SYS)."""
    out = []
    for ref in refs:
        pad = next(p for p in G["pads"] if p["ref"] == ref)
        net = pad["net"]
        item = {"type": "pad", "ref": ref, "x": pad["x"], "y": pad["y"], "layers": pad["layers"]}
        layers = layers_for(net)
        for w in (0.3, 0.2):
            n = Net(net, w, layers)
            comp = Components(net)
            pa, sa = endpoint(item, net, layers, comp)
            cells = drop_cells(net)
            if cells is None:
                print(f"{ref}: {NETS[net]['name']} has no plane")
                break
            res = astar(n, sa, {l: np.zeros((NY, NX), bool) for l in layers}, cells & n.via)
            if res is None:
                continue
            path, dropped = res
            segs, vias = to_segments(path, w, pa, None)
            vias.append((X0 + path[-1][2] * RES, Y0 + path[-1][1] * RES))
            add_copper(net, segs, vias)
            out.append({"n": 0, "net": net, "segments": [list(s) for s in segs], "vias": [list(v) for v in vias]})
            print(f"{ref}: via onto {NETS[net]['name']} plane, stub {sum(math.hypot(x2 - x1, y2 - y1) for x1, y1, x2, y2, l, w_ in segs):.1f} mm")
            break
        else:
            print(f"{ref}: no spot for a via")
    (HERE / "out" / "routes.json").write_text(json.dumps({"gaps": out, "removed_tracks": [], "removed_vias": []}),
                                              encoding="utf-8")


def main():
    if sys.argv[1:2] == ["drop"]:
        drop(sys.argv[2:])
        return
    if sys.argv[1:2] == ["region"]:
        x0, y0, x1, y1 = (float(a) for a in sys.argv[2:6])
        region(x0, y0, x1, y1, {int(a) for a in sys.argv[6:] if a.isdigit()})
        return
    if sys.argv[1:2] == ["debug"]:
        for a in sys.argv[2:]:
            debug(int(a))
        return
    only = {int(a) for a in sys.argv[1:] if a.isdigit()}
    out = []
    for gap in G["gaps"]:
        if only and gap["n"] not in only:
            continue
        net, a, b = gap["net"], gap["items"][0], gap["items"][1]
        name = NETS[net]["name"]
        label = " <-> ".join(i.get("ref") or i["type"] for i in (a, b))
        if a["type"] == "zone" and b["type"] == "zone":
            if name == "GND":
                # pour islands of GND: a via to In1 in every island that has none yet
                n = Net(net, 0.2, ["F.Cu"])
                done = 0
                for isl in sorted(a["islands"], key=lambda isl: abs(sum(
                        x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(isl[0], isl[0][1:] + isl[0][:1]))))[:-1]:
                    cells = island_cells([isl])
                    has_via = any(not v["removed"] and v["net"] == net and cells[cell(v["x"], v["y"])] for v in VIAS)
                    if has_via:
                        continue
                    spots = cells & n.via & ~PADS_F
                    if not spots.any():
                        continue
                    js, is_ = np.nonzero(spots)
                    k = np.argmin((js - js.mean()) ** 2 + (is_ - is_.mean()) ** 2)
                    x, y = X0 + is_[k] * RES, Y0 + js[k] * RES
                    add_copper(net, [], [(x, y)])
                    out.append({"n": gap["n"], "net": net, "segments": [], "vias": [[x, y]]})
                    done += 1
                print(f"{gap['n']:2d} GND          pour islands: {done} vias to In1 added")
                continue
            islands = sorted(a["islands"], key=lambda isl: -abs(sum(
                x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(isl[0], isl[0][1:] + isl[0][:1]))))
            done = [islands[0]]
            for isl in islands[1:]:
                r = route_gap(gap["n"], net, {"type": "zone", "layer": a["layer"], "islands": [isl]},
                              {"type": "zone", "layer": a["layer"], "islands": done}, f"{name} island")
                if r:
                    out += r
                    done.append(isl)
            continue
        if a["type"] == "zone":
            a, b = b, a
        out += route_gap(gap["n"], net, a, b, label)
    removed = [t["id"] for t in TRACKS[:len(G["tracks"])] if t["removed"]]
    removed_vias = [v["id"] for v in VIAS[:len(G["vias"])] if v["removed"]]
    (HERE / "out" / "routes.json").write_text(json.dumps({"gaps": out, "removed_tracks": removed,
                                                          "removed_vias": removed_vias}), encoding="utf-8")
    print(f"routes.json: {len(out)} connections, {len(removed)} tracks and {len(removed_vias)} vias ripped")


if __name__ == "__main__":
    main()
