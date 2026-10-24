"""Footprint fields (value, LCSC, Funktion, Description, Datasheet) of the board follow circuit.py, so that
the schematic parity check stays clean after a change in circuit.py without regenerating the board.
Run with KiCad's Python: python sync_fields.py"""
from pathlib import Path

import pcbnew

import circuit
from gen_pcb import lib_symbol, prop

HERE = Path(__file__).resolve().parent
PCB = HERE / "mainboard.kicad_pcb"

board = pcbnew.LoadBoard(str(PCB))
fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
changed = []
for p in circuit.PARTS:
    fp = fps.get(p.ref)
    if fp is None:
        continue
    if fp.GetValue() != p.value:
        changed.append(f"{p.ref} value {fp.GetValue()} -> {p.value}")
        fp.SetValue(p.value)
    want = {"LCSC": p.lcsc or "", "Funktion": p.func or "", "Description": p.descr or ""}
    ds = prop(lib_symbol(p.lib), "Datasheet")
    want["Datasheet"] = str(ds[2]) if ds and str(ds[2]) else ""
    for name, value in want.items():
        fields = {f.GetName(): f for f in fp.GetFields()}
        have = fields[name].GetText() if name in fields else ""
        if value and have != value:
            fp.SetField(name, value)
            {f.GetName(): f for f in fp.GetFields()}[name].SetVisible(False)
            changed.append(f"{p.ref} {name}")
pcbnew.SaveBoard(str(PCB), board, True)
print(f"{len(changed)} fields updated: {', '.join(changed)}" if changed else "fields already in sync")
