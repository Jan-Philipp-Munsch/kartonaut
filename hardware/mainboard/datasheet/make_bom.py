"""Write the bill of materials of the datasheet from kicad/circuit.py (the single source).

Reads PARTS from ../kicad/circuit.py without touching the KiCad project, groups identical
passives (same value and footprint) and writes bom_generated.tex, a longtable body that
MS-MB-B.tex includes. Also writes bom_summary.tex with the counts used in the text.

Run:  python hardware/mainboard/datasheet/make_bom.py
"""
import re
import sys
from collections import OrderedDict
from pathlib import Path

HERE = Path(__file__).resolve().parent
KICAD = HERE.parent / "kicad"
sys.path.insert(0, str(KICAD))
import circuit  # noqa: E402  (executes the part list; no KiCad needed)

SHEET_TITLE = {s[0]: s[1] for s in circuit.SHEETS}
SHEET_ORDER = [s[0] for s in circuit.SHEETS]


def tex(s):
    s = str(s)
    for a, b in [("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("#", r"\#"), ("_", r"\_"),
                 ("µ", r"\textmu{}"), ("Ω", r"\textohm{}"), ("°", r"\textdegree{}"), ("≥", r"$\geq$"),
                 ("<", r"$<$"), (">", r"$>$"), ("±", r"$\pm$"), ("×", r"$\times$")]:
        s = s.replace(a, b)
    return s


def package(fp):
    name = fp.split(":")[-1]
    m = re.match(r"JST_(\w+)_[\w-]+_1x(\d+)(-1MP)?_P[\d.]+mm_(Vertical|Horizontal)", name)
    if m:
        return f"JST-{m.group(1)} {int(m.group(2))} {'liegend' if m.group(4) == 'Horizontal' else 'stehend'}"
    if name.startswith("AMASS_XT30"):
        return "XT30PW-M liegend"
    if name.startswith("SolderJumper"):
        return "Lötbrücke"
    if name.startswith("CP_Radial"):
        return "Elko radial Ø" + re.search(r"D([\d.]+)mm", name).group(1).rstrip("0").rstrip(".") + " mm"
    if name.startswith("PinHeader"):
        return "Stiftleiste " + re.search(r"_(\dx\d+)_", name).group(1)
    if name.startswith("Teensy41"):
        return "Buchsenleisten 2 × 1×24"
    if name.startswith("NetTie"):
        return "Netzbrücke"
    if name.startswith("Buzzer"):
        return "THT Ø 12 mm"
    if name.startswith("TestPoint"):
        return "Testpunkt"
    if name.startswith("WIRELM"):
        return "SMD-Modul 16 × 26 mm"
    if name.startswith("L_Changjiang"):
        return "5040"
    name = re.sub(r"_\d+\.?\d*x\d+\.?\d*mm.*$", "", name)      # Package_SO:SOIC-8_3.9x4.9mm_P1.27mm
    name = re.sub(r"_L\d.*$", "", name)                         # lcsc:LGA-14_L3.0-W2.5-P0.50-TL
    name = re.sub(r"_\d{4}Metric$", "", name)                   # R_0603_1608Metric
    name = name.replace("_", " ")
    for a, b in [("R 0603", "0603"), ("C 0603", "0603"), ("C 0805", "0805"), ("C 1210", "1210"),
                 ("Fuse 1812", "1812"), ("D SMA", "SMA"), ("D SMB", "SMB"), ("D SOD-123", "SOD-123"),
                 ("L Changjiang FNR5040S", "5040"), ("Package TO SOT SMD:", "")]:
        name = name.replace(a, b)
    return name


def refprefix(ref):
    return re.match(r"[A-Za-z_]+", ref).group(0)


def main():
    rows = OrderedDict()          # (sheet, group, value, fp, descr) -> [refs]
    for p in circuit.PARTS:
        passive = refprefix(p.ref) in ("R", "C", "TP")
        key = (p.sheet, p.group, p.value, p.fp, p.descr if not passive else "", p.lcsc, p.dnp)
        rows.setdefault(key, []).append(p.ref)

    head = (r"\textbf{Ref} & \textbf{n} & \textbf{Wert} & \textbf{Gehäuse} & \textbf{Funktion} & \textbf{LCSC}\\")
    out = [r"\begin{longtable}{L{24mm} r L{26mm} L{30mm} L{52mm} L{14mm}}",
           r"\toprule", head, r"\midrule", r"\endfirsthead",
           r"\toprule", head, r"\midrule", r"\endhead",
           r"\midrule\multicolumn{6}{r}{\scriptsize Fortsetzung nächste Seite}\\", r"\endfoot",
           r"\bottomrule", r"\endlastfoot"]
    current_sheet = None
    n_parts = n_lines = 0
    for key in sorted(rows, key=lambda k: (SHEET_ORDER.index(k[0]), )):
        sheet, group, value, fp, descr, lcsc, dnp = key
        refs = rows[key]
        if sheet != current_sheet:
            if current_sheet is not None:
                out.append(r"\midrule")
            out.append(r"\multicolumn{6}{l}{\bfseries " + tex(SHEET_TITLE[sheet]) + r"}\\*\midrule")
            current_sheet = sheet
        refs_s = ", ".join(refs) if len(refs) <= 6 else f"{refs[0]} … {refs[-1]} ({len(refs)}×)"
        descr = descr or group
        if dnp:
            descr = "DNP, " + descr
        out.append(" & ".join([tex(refs_s), str(len(refs)), tex(value), tex(package(fp)), tex(descr),
                               r"\texttt{" + tex(lcsc) + "}" if lcsc else "–"]) + r"\\")
        n_parts += len(refs)
        n_lines += 1
    out.append(r"\end{longtable}")
    (HERE / "bom_generated.tex").write_text("\n".join(out) + "\n", encoding="utf-8")
    (HERE / "bom_summary.tex").write_text(
        f"\\newcommand{{\\bomParts}}{{{n_parts}}}\n\\newcommand{{\\bomLines}}{{{n_lines}}}\n"
        f"\\newcommand{{\\bomNets}}{{{len(circuit.nets())}}}\n", encoding="utf-8")
    print(f"{n_parts} parts, {n_lines} BOM lines, {len(circuit.nets())} nets")


if __name__ == "__main__":
    main()
