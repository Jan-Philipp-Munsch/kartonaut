"""Fabrication data for JLCPCB (KiCad Python), called by `./make.sh fab` after kicad-cli wrote the Gerbers,
the drill files and the KiCad position file:

    fab/mainboard_gerber.zip   Gerber + Excellon (what the order form takes)
    fab/mainboard_bom.csv      Comment, Designator, Footprint, LCSC Part #   (SMD, not DNP, grouped)
    fab/mainboard_cpl.csv      Designator, Mid X, Mid Y, Layer, Rotation      (from the KiCad position file)
    fab/FAB.md                 what is in the files, what still has no LCSC number, what is soldered by hand

Rotation corrections for JLC's part library are made in the order form (ORDER.md section 3.2), not here.
"""
import csv
import zipfile
from collections import OrderedDict
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
FAB = HERE / "fab"


def field(fp, name):
    for f in fp.GetFields():
        if f.GetName() == name:
            return f.GetText().strip()
    return ""


def main():
    board = pcbnew.LoadBoard(str(HERE / "mainboard.kicad_pcb"))
    fps = sorted(board.GetFootprints(), key=lambda f: (f.GetReference().rstrip("0123456789"),
                                                       int("".join(c for c in f.GetReference() if c.isdigit()) or 0)))
    smd, tht, dnp = [], [], []
    for fp in fps:
        if fp.IsDNP():
            dnp.append(fp)
        elif fp.GetAttributes() & pcbnew.FP_SMD and fp.GetLayer() == pcbnew.F_Cu:
            smd.append(fp)
        else:
            tht.append(fp)
    # BOM: one line per value + footprint + LCSC
    groups = OrderedDict()
    for fp in smd:
        key = (fp.GetValue(), fp.GetFPID().GetLibItemName().wx_str(), field(fp, "LCSC"))
        groups.setdefault(key, []).append(fp.GetReference())
    with open(FAB / "mainboard_bom.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (value, footprint, lcsc), refs in groups.items():
            w.writerow([value, ",".join(refs), footprint, lcsc])
    # CPL from KiCad's position file (its coordinate convention is what JLC expects from KiCad users)
    pos = list(csv.DictReader(open(HERE / "fab" / "pos_kicad.csv", newline="", encoding="utf-8")))
    with open(FAB / "mainboard_cpl.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for r in pos:
            w.writerow([r["Ref"], f"{float(r['PosX']):.4f}mm", f"{float(r['PosY']):.4f}mm",
                        "Top" if r["Side"] == "top" else "Bottom", f"{float(r['Rot']):.1f}"])
    # Gerber zip
    gerber = FAB / "gerber"
    with zipfile.ZipFile(FAB / "mainboard_gerber.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(gerber.iterdir()):
            z.write(p, p.name)
    # summary
    no_lcsc = [(v, refs) for (v, fpn, l), refs in groups.items() if not l]
    with_lcsc = sum(len(refs) for (v, fpn, l), refs in groups.items() if l)
    lines = [
        "# Fertigungsdaten Mainboard rev B1 (JLCPCB)", "",
        f"Erzeugt mit `./make.sh fab` aus `mainboard.kicad_pcb`. Parameter nach `../ORDER.md` §3.1: 4 Lagen,",
        "54 × 120 mm, 1,6 mm, ENIG, Stackup JLC04161H-7628, Economic PCBA nur Oberseite.", "",
        "| Datei | Inhalt |", "|---|---|",
        "| `mainboard_gerber.zip` | F/In1/In2/B.Cu, F.Paste, F/B.Silkscreen, F/B.Mask, Edge.Cuts (Protel-Endungen, ohne X2), Excellon PTH+NPTH in einer Datei, Bohrplan |",
        f"| `mainboard_bom.csv` | {len(groups)} Zeilen, {len(smd)} bestückte SMD-Bauteile, {with_lcsc} davon mit LCSC-Nummer |",
        f"| `mainboard_cpl.csv` | {len(pos)} Bauteile, Oberseite, Drehung wie KiCad (im Bestellformular prüfen) |", "",
        f"**Ohne LCSC-Nummer ({sum(len(r) for v, r in no_lcsc)} Bauteile, im JLC-Teileprogramm zuordnen):**", "",
    ]
    for v, refs in no_lcsc:
        lines.append(f"- {v}: {', '.join(refs)}")
    solder = [fp for fp in tht if not fp.GetReference().startswith(("H", "NT", "TP", "JP"))]
    nothing = [fp for fp in tht if fp not in solder]
    lines += ["", f"**Von Hand zu löten ({len(solder)} THT-Teile, nicht in BOM und CPL):** "
              + ", ".join(f"{fp.GetReference()} ({fp.GetValue()})" for fp in solder), "",
              f"**Kein Bauteil (Löcher, Netzbrücke, Testpunkte, Lötjumper):** " + ", ".join(fp.GetReference() for fp in nothing), "",
              f"**DNP ({len(dnp)}):** " + ", ".join(f"{fp.GetReference()} ({fp.GetValue()})" for fp in dnp), ""]
    (FAB / "FAB.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"fab/: {len(groups)} BOM lines for {len(smd)} SMD parts ({with_lcsc} with LCSC), "
          f"{len(pos)} CPL rows, {len(tht)} by hand, {len(dnp)} DNP, "
          f"{sum(len(r) for v, r in no_lcsc)} without LCSC")


if __name__ == "__main__":
    main()
