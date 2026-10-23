"""Add the parts of circuit.py that are not on the board yet, at given positions (KiCad Python).

The board file is the source since the hand routing; `gen_pcb.py place` must not run again. This
script does for new parts what gen_pcb.add_footprints does for all: footprint from the library, fields,
sheet path (so the schematic parity check matches), nets on the pads, DNP flags. Then the zones are
refilled and the DRC lists the new connections; close_gaps.py / route_gaps.py route them.

    python.exe add_parts.py            adds every part in POSITIONS that the board lacks
"""
import pcbnew

import circuit
import gen_pcb
from gen_schematic import lib_symbol, prop, sym_pins, uid

HERE = gen_pcb.HERE
PCB = gen_pcb.PCB
MM = pcbnew.FromMM

# reference: (x, y, rotation) in KiCad board coordinates (mm)
POSITIONS = {
    # tip, left corner (x 101.5..108.3, y 51.5..62.3 is free): the quietest corner, 45 mm from the 2S rail
    "U16": (104.0, 60.5, 0),        # LIS3MDL magnetometer; chip X = board +x (= +u), chip Y = board -y (= +v)
    "C47": (104.0, 58.2, 0),        # 100n Vdd
    "C48": (106.6, 61.4, 0),        # 100n C1, pad 1 next to U16 pin 4
    # tip, right strip next to the Qwiic plug J12 (x 146.5..151.5, y 58.6..64.5 is free; the rails begin at x 151.9)
    "U18": (149.0, 61.5, 0),        # SHT40 humidity / temperature
    "C49": (149.0, 63.6, 0),        # 100n VDD
    # tip centre beyond the Teensy's USB end (u -9..0, v 92..97.5), flat parts only
    "U17": (122.5, 75.4, 180),      # ADXL375 high-g accelerometer (DNP); SDA/SCL pads toward the Qwiic side
    "C50": (118.9, 75.4, 90),       # 1u VS (DNP)
    "C51": (126.1, 75.4, 90),       # 100n VDD I/O (DNP)
}


def main():
    board = pcbnew.LoadBoard(str(PCB))
    present = {fp.GetReference() for fp in board.GetFootprints()}
    netinfo = {}
    for name in circuit.nets():
        n = board.FindNet(name)
        if n is None:
            n = pcbnew.NETINFO_ITEM(board, name)
            board.Add(n)
        netinfo[name] = n
    sheet_uuid = {s: str(uid("sheet", s)) for s, _, _ in circuit.SHEETS}
    titles = {s: t for s, t, _ in circuit.SHEETS}
    added = []
    for p in circuit.PARTS:
        if p.ref in present:
            continue
        if p.ref not in POSITIONS:
            print(f"  {p.ref} ({p.value}) is new but has no position: skipped")
            continue
        pins = sym_pins(lib_symbol(p.lib))
        for num, net in list(p.pins.items()):
            if net is None and num in pins:
                name = f"unconnected-({p.ref}-{pins[num][3]}-Pad{num})"
                n = pcbnew.NETINFO_ITEM(board, name)
                board.Add(n)
                netinfo[name] = n
                p.pins[num] = name
        fp = gen_pcb.load_fp(p.fp)
        fp.SetReference(p.ref)
        fp.SetValue(p.value)
        fp.SetPath(pcbnew.KIID_PATH(f"{sheet_uuid[p.sheet]}/{uid(p.sheet, p.ref)}"))
        fp.SetSheetname(titles[p.sheet])
        fp.SetSheetfile(f"{p.sheet}.kicad_sch")
        if p.lcsc:
            fp.SetField("LCSC", p.lcsc)
        if p.func:
            fp.SetField("Funktion", p.func)
        if p.descr:
            fp.SetField("Description", p.descr)
        ds = prop(lib_symbol(p.lib), "Datasheet")
        if ds and str(ds[2]):
            fp.SetField("Datasheet", str(ds[2]))
        for f in fp.GetFields():
            if not (f.IsReference() or f.IsValue()):
                f.SetVisible(False)
        attrs = fp.GetAttributes()
        if p.dnp:
            attrs |= pcbnew.FP_DNP | pcbnew.FP_EXCLUDE_FROM_POS_FILES
        fp.SetAttributes(attrs)
        for pad in fp.Pads():
            net = p.pins.get(pad.GetNumber())
            if net:
                pad.SetNet(netinfo[net])
        if gen_pcb.passive(p.ref):
            fp.Reference().SetLayer(pcbnew.F_Fab)
        fp.Value().SetLayer(pcbnew.F_Fab)
        for item in fp.GraphicalItems():
            if isinstance(item, pcbnew.PCB_TEXT) and item.GetLayer() == pcbnew.F_SilkS:
                item.SetVisible(False)
        x, y, rot = POSITIONS[p.ref]
        fp.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
        fp.SetOrientationDegrees(rot)
        board.Add(fp)
        added.append(p.ref)
        # copper of other nets under the new pads goes; the router joins those nets again
        ripped = 0
        for t in list(board.GetTracks()):
            for pad in fp.Pads():
                if t.GetNetCode() != pad.GetNetCode() and pad.IsOnLayer(t.GetLayer() if t.GetClass() != "PCB_VIA" else pcbnew.F_Cu) \
                        and t.GetEffectiveShape(t.GetLayer() if t.GetClass() != "PCB_VIA" else pcbnew.F_Cu).Collide(
                            pad.GetEffectiveShape(pcbnew.F_Cu), MM(0.2)):
                    board.Delete(t)
                    ripped += 1
                    break
        if ripped:
            print(f"  {p.ref}: {ripped} tracks/vias of other nets removed from under its pads")
    # pads of parts already on the board whose net changed in circuit.py (a pin that was open before)
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    changed = []
    for p in circuit.PARTS:
        fp = fps.get(p.ref)
        if fp is None or p.ref in added:
            continue
        for pad in fp.Pads():
            want = p.pins.get(pad.GetNumber())
            if want and not want.startswith("unconnected-") and pad.GetNetname() != want:
                pad.SetNet(netinfo[want])
                changed.append(f"{p.ref}.{pad.GetNumber()} -> {want}")
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(str(PCB), board, True)
    gen_pcb.fix_model_paths()
    print(f"added {len(added)} footprints: {', '.join(added)}" + (f"; nets set: {', '.join(changed)}" if changed else ""))


if __name__ == "__main__":
    main()
