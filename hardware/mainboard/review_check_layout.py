"""Layout checks of the rev B review (review_kicad_2026-10-21.md, section 5), updated for rev B1. Read-only.

Run with KiCad's Python on a COPY of the board (the .kicad_pro must lie next to the copy):

    "%LOCALAPPDATA%/Programs/KiCad/10.0/bin/python.exe" review_check_layout.py <copy>/mainboard.kicad_pcb

Prints: width, length, layers and vias of every power net (tracks) and the copper zones per net and layer;
2S tracks on In2 (A6: none); the Kelvin taps of the INA239; vias, tracks and parts within 5 mm of the IMU; parts at the edge (|u| > 25), under the
Teensy and over the outline; zones; silkscreen references.
"""
import math
import sys
from collections import defaultdict

import pcbnew

PCB = sys.argv[1]
board = pcbnew.LoadBoard(PCB)
MM = pcbnew.ToMM
X0, Y0, W, L = 100.0, 50.0, 54.0, 120.0


def UV(x, y):
    return x - X0 - W / 2, Y0 + L - y


def uv_of(item):
    p = item.GetPosition()
    return UV(MM(p.x), MM(p.y))


fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
tracks = [t for t in board.GetTracks() if t.GetClass() in ("PCB_TRACK", "PCB_ARC")]
vias = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
print(f"board: {len(fps)} footprints, {len(tracks)} track segments, {len(vias)} vias, {len(list(board.Zones()))} zones")

# 1. widths and vias per net (power nets)
STROM = ["VBAT2_RAW", "VBAT2_REV", "VBAT2_F", "VBAT_PROT", "VSERVO", "VBAT_ARMED", "PYRO1_NEG", "PYRO2_NEG",
         "PYRO3_NEG", "PYRO4_NEG"]
NETS = STROM + ["GND_PWR", "VBAT1_RAW", "VBAT1_REV", "VBAT1_F", "VSYS_IN", "U2_L1", "U2_L2", "5V_SYS", "3V3_RF",
                "3V3_EXP", "TEENSY_VIN", "MOT_A", "MOT_B", "VBUS_CHG", "3V3", "3V3_SENS", "GND"]
bynet = defaultdict(list)
for t in tracks:
    bynet[t.GetNetname()].append(t)
vbynet = defaultdict(list)
for v in vias:
    vbynet[v.GetNetname()].append(v)
print("\n== Stromnetze: Breite min/max [mm], Laenge [mm], Lagen, Vias (Durchmesser/Bohrung)")
for n in NETS:
    ts = bynet.get(n, [])
    if not ts and not vbynet.get(n):
        print(f"  {n:12s} keine Bahnen")
        continue
    ws = [MM(t.GetWidth()) for t in ts]
    ln = sum(MM(t.GetLength()) for t in ts)
    layers = sorted({board.GetLayerName(t.GetLayer()) for t in ts})
    vs = vbynet.get(n, [])
    vd = sorted({(round(MM(v.GetWidth(pcbnew.F_Cu)), 2), round(MM(v.GetDrill()), 2)) for v in vs})
    narrow = [t for t in ts if MM(t.GetWidth()) < 0.45]
    print(f"  {n:12s} w {min(ws) if ws else 0:.2f}-{max(ws) if ws else 0:.2f}  L {ln:6.1f}  {','.join(layers):18s}  vias {len(vs):3d} {vd}"
          + (f"  <0.45mm: {len(narrow)} seg, {sum(MM(t.GetLength()) for t in narrow):.1f} mm" if narrow else ""))

print("\n== 2S-Netze auf In2 (A6: keine)")
in2 = board.GetLayerID("In2.Cu")
bad = {n: round(sum(MM(t.GetLength()) for t in bynet.get(n, []) if t.GetLayer() == in2), 1) for n in STROM}
print("  " + (", ".join(f"{n} {v} mm" for n, v in bad.items() if v) or "keine"))
print("\n== Kupferflaechen der Stromnetze auf F.Cu (gefuellt, mm2)")
area = defaultdict(float)
for z in board.Zones():
    if z.GetIsRuleArea() or z.GetNetname() not in STROM + ["VSYS_IN"]:
        continue
    area[z.GetNetname()] += z.GetFilledArea() / 1e12 if hasattr(z, "GetFilledArea") else 0
for n, a in sorted(area.items()):
    print(f"  {n:12s} {a:7.1f}")

# 2. Kelvin: where do the INA sense pins reach the shunt? BFS over tracks of the net.
def pad(ref, num):
    for p in fps[ref].Pads():
        if p.GetNumber() == num:
            return p
    raise KeyError((ref, num))


def bfs_path(start_pad, target_pad, net):
    """Length of copper path from start pad to target pad using tracks/vias of the net (endpoint graph)."""
    pts = defaultdict(list)   # (x,y,layerkey) -> [(other, length)]
    def key(p, layer):
        return (p.x, p.y)
    for t in bynet.get(net, []):
        a, b = t.GetStart(), t.GetEnd()
        ln = MM(t.GetLength())
        pts[(a.x, a.y)].append(((b.x, b.y), ln))
        pts[(b.x, b.y)].append(((a.x, a.y), ln))
    # pads: connect every endpoint inside a pad bbox to the pad centre
    def pad_nodes(p):
        bb = p.GetBoundingBox()
        return [k for k in pts if bb.Contains(pcbnew.VECTOR2I(k[0], k[1]))]
    import heapq
    s_nodes = pad_nodes(start_pad)
    t_nodes = set(pad_nodes(target_pad))
    if not s_nodes:
        return None, "Startpad ohne Bahn"
    if not t_nodes:
        return None, "Zielpad ohne Bahn"
    dist = {k: 0.0 for k in s_nodes}
    heap = [(0.0, k) for k in s_nodes]
    while heap:
        d, k = heapq.heappop(heap)
        if k in t_nodes:
            return d, "ok"
        if d > dist.get(k, 1e9):
            continue
        for nb, ln in pts[k]:
            nd = d + ln
            if nd < dist.get(nb, 1e9):
                dist[nb] = nd
                heapq.heappush(heap, (nd, nb))
    # zones may connect; report unreachable via tracks
    return None, "nur ueber Flaeche/Pad verbunden"


print("\n== Kelvin-Abgriff: Sense-Netze des Shunts R_SH1 (Pad 2 = ISENS_P, Pad 3 = ISENS_N)")
for net in ("ISENS_P", "ISENS_N"):
    pads_ = [f"{r}.{q.GetNumber()}" for r, fp in fps.items() for q in fp.Pads() if q.GetNetname() == net]
    print(f"  {net}: Pads {pads_} - nur Sense-Pad und Filterwiderstand, Kelvin durch die Netzliste")

# 3. IMU surroundings
IMU = (0.0, 60.5)
print("\n== Umfeld der IMU (U4) im Radius 5 mm")
imu_vias = [(round(math.hypot(*(a - b for a, b in zip(uv_of(v), IMU))), 1), v.GetNetname(), ) for v in vias
            if math.hypot(*(a - b for a, b in zip(uv_of(v), IMU))) < 5.0]
print(f"  Vias < 5 mm: {len(imu_vias)}", sorted(imu_vias)[:12])
for layer in ("In2.Cu", "B.Cu", "F.Cu", "In1.Cu"):
    lid = board.GetLayerID(layer)
    hits = defaultdict(float)
    for t in tracks:
        if t.GetLayer() != lid:
            continue
        for p in (t.GetStart(), t.GetEnd()):
            u, v = UV(MM(p.x), MM(p.y))
            if math.hypot(u - IMU[0], v - IMU[1]) < 5.0:
                hits[t.GetNetname()] += MM(t.GetLength())
                break
    print(f"  Bahnen auf {layer} mit Endpunkt < 5 mm: " + ", ".join(f"{k} {v:.1f}mm" for k, v in sorted(hits.items(), key=lambda kv: -kv[1])[:10]))
parts_near = []
for ref, fp in fps.items():
    u, v = uv_of(fp)
    d = math.hypot(u - IMU[0], v - IMU[1])
    if d < 8 and ref != "U4":
        parts_near.append((round(d, 1), ref, fp.GetValue()))
print("  Bauteile < 8 mm:", sorted(parts_near))

# 4. heights at the edge and under the Teensy, parts outside the board
print("\n== Lage der Bauteile: Rand (|u|>25), unter dem Teensy, ausserhalb")
edge, under, outside = [], [], []
for ref, fp in fps.items():
    if ref.startswith("H"):
        continue
    poly = fp.GetCourtyard(pcbnew.F_CrtYd)
    bb = poly.BBox() if poly.OutlineCount() else fp.GetBoundingBox(False)
    (u0, v1), (u1, v0) = UV(MM(bb.GetLeft()), MM(bb.GetTop())), UV(MM(bb.GetRight()), MM(bb.GetBottom()))
    tht = fp.GetAttributes() & pcbnew.FP_THROUGH_HOLE
    if u0 < -25 or u1 > 25:
        edge.append((ref, fp.GetValue(), "THT" if tht else "SMD", round(min(u0, -u1), 1)))
    if -6.1 < (u0 + u1) / 2 < 6.1 and 30 < (v0 + v1) / 2 < 91:
        under.append((ref, fp.GetValue(), "THT" if tht else "SMD"))
    if u0 < -27.3 or u1 > 27.3 or v0 < -0.3 or v1 > 120.3:
        outside.append((ref, round(u0, 1), round(u1, 1), round(v0, 1), round(v1, 1)))
print("  am Rand:", edge)
print("  unter dem Teensy:", under)
print("  ueber den Rand:", outside)

# 5. zones
print("\n== Zonen")
for z in board.Zones():
    print(f"  {z.GetZoneName():22s} net={z.GetNetname():10s} layers={[board.GetLayerName(l) for l in z.GetLayerSet().Seq()]} "
          f"rule={z.GetIsRuleArea()} filled={z.IsFilled()}")

# 6. silkscreen reference presence for connectors and ICs
print("\n== Bestueckungsdruck: Referenzen auf F.SilkS")
silk = [ref for ref, fp in fps.items() if fp.Reference().GetLayer() == pcbnew.F_SilkS and fp.Reference().IsVisible()]
print("  sichtbar:", len(silk), "von", len(fps))
texts = [t.GetText() for t in board.Drawings() if isinstance(t, pcbnew.PCB_TEXT) and t.GetLayer() == pcbnew.F_SilkS]
print("  freie Texte:", texts)
