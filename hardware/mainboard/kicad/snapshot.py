"""Quick look at the board: courtyards, fab layer and copper as PNG (out/snapshot_<name>.png)."""
import subprocess, sys, os
from pathlib import Path
import pymupdf
HERE = Path(__file__).resolve().parent
CLI = Path(os.environ["LOCALAPPDATA"]) / "Programs/KiCad/10.0/bin/kicad-cli.exe"
name = sys.argv[1] if len(sys.argv) > 1 else "place"
layers = sys.argv[2] if len(sys.argv) > 2 else "Edge.Cuts,F.CrtYd,F.Fab,F.SilkS"
pdf = HERE / "out" / f"snapshot_{name}.pdf"
subprocess.run([str(CLI), "pcb", "export", "pdf", "--layers", layers, "--mode-single", "--include-border-title",
                "-o", str(pdf), str(HERE / "mainboard.kicad_pcb")], check=True, capture_output=True)
d = pymupdf.open(pdf)
page = d[0]
clip = pymupdf.Rect(95 / 25.4 * 72, 45 / 25.4 * 72, 159 / 25.4 * 72, 175 / 25.4 * 72)
page.get_pixmap(dpi=int(sys.argv[3]) if len(sys.argv) > 3 else 220, clip=clip).save(HERE / "out" / f"snapshot_{name}.png")
print(HERE / "out" / f"snapshot_{name}.png")
