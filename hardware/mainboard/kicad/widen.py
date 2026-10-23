"""Widen narrow supply segments as far as the DRC allows (KiCad Python).

    python.exe widen.py            tries each candidate at 0.6, 0.5, 0.4, 0.3 mm and keeps the widest
                                   width that adds no DRC error; writes the board, prints the result

Candidates: segments of the supply classes narrower than 0.45 mm that are not plane-via stubs.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
PCB = HERE / "mainboard.kicad_pcb"
TMP = HERE / "out" / "widen_try.kicad_pcb"
CLI = Path(os.environ["LOCALAPPDATA"]) / "Programs/KiCad/10.0/bin/kicad-cli.exe"
mm, MM = pcbnew.ToMM, pcbnew.FromMM
NETS = ("VSYS_IN", "MOT_A", "MOT_B", "GND_PWR", "5V_SYS", "VBAT1_F", "TEENSY_VIN", "3V3_EXP", "3V3_RF", "VBUS_CHG")
WIDTHS = (0.6, 0.4, 0.3)


def drc_errors(path):
    rpt = HERE / "out" / "widen_drc.json"
    subprocess.run([str(CLI), "pcb", "drc", "--format", "json", "-o", str(rpt), str(path)], capture_output=True)
    d = json.loads(rpt.read_text(encoding="utf-8"))
    return [v for v in d["violations"] if v["severity"] == "error"], len(d["unconnected_items"])


def main():
    board = pcbnew.LoadBoard(str(PCB))
    base_err, base_open = drc_errors(PCB)
    print(f"start: {len(base_err)} DRC errors, {base_open} open")
    # 0.3 mm stubs to plane vias are fine; what matters are the 0.15 mm pieces and the motor outputs
    cands = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK" and t.GetNetname() in NETS
             and (mm(t.GetWidth()) < 0.25 or (t.GetNetname() in ("MOT_A", "MOT_B") and mm(t.GetWidth()) < 0.45))]
    import shutil
    shutil.copy(HERE / "mainboard.kicad_pro", TMP.with_suffix(".kicad_pro"))   # the DRC needs the rules
    cands.sort(key=lambda t: -t.GetLength())
    print(f"{len(cands)} candidates")
    for t in cands:
        w0 = mm(t.GetWidth())
        s, e = t.GetStart(), t.GetEnd()
        label = (f"{t.GetNetname():8s} {board.GetLayerName(t.GetLayer()):6s} w={w0:.2f} L={mm(t.GetLength()):4.2f} "
                 f"({mm(s.x):.2f},{mm(s.y):.2f})-({mm(e.x):.2f},{mm(e.y):.2f})")
        kept = w0
        for w in WIDTHS:
            if w <= w0:
                break
            t.SetWidth(MM(w))
            pcbnew.ZONE_FILLER(board).Fill(board.Zones())
            pcbnew.SaveBoard(str(TMP), board, True)
            err, n_open = drc_errors(TMP)
            if len(err) <= len(base_err) and n_open <= base_open:
                kept = w
                break
        t.SetWidth(MM(kept))
        print(f"  {label}  ->  {kept:.2f}" + ("" if kept > w0 else "  (no room)"))
        sys.stdout.flush()
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(str(PCB), board, True)
    err, n_open = drc_errors(PCB)
    print(f"end: {len(err)} DRC errors, {n_open} open")
    TMP.unlink(missing_ok=True)
    TMP.with_suffix(".kicad_pro").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
