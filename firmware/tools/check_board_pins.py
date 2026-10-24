"""Vergleicht firmware/lib/mainboard_revb/BoardRevB.h mit der Schaltung in circuit.py.

Geprüft werden die Teensy-Pins (TEENSY), die Ausgänge des CS-Decoders U12 (74HC138)
und die Kanäle der Analogmux U13 (74HC4051) samt Select-Leitungen. circuit.py wird
nur geparst, nicht ausgeführt.

    python firmware/tools/check_board_pins.py [pfad/zu/circuit.py]

Ohne Argument: hardware/mainboard/kicad/circuit.py im selben Repo. Exit-Code 1 bei
Abweichungen, 2 wenn circuit.py noch keinen CS-Decoder hat (Stand vor E10, dann gibt es
nichts zu vergleichen; die CI meldet das als Warnung).
"""
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HEADER = ROOT / "firmware/lib/mainboard_revb/BoardRevB.h"

# Bauteilpin -> Ausgang/Kanal (Datenblätter NXP 74HC138, 74HC4051)
HC138_Y = {15: 0, 14: 1, 13: 2, 12: 3, 11: 4, 10: 5, 9: 6, 7: 7}
HC138_SEL = {1: "SEL0", 2: "SEL1", 3: "SEL2", 4: "CS_EN"}
HC4051_Y = {13: 0, 14: 1, 15: 2, 12: 3, 1: 4, 5: 5, 2: 6, 4: 7}
HC4051_SEL = {11: "SEL0", 10: "SEL1", 9: "SEL2", 3: "MUX_OUT"}


def parse_circuit(path):
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    teensy, parts = None, {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "TEENSY" for t in node.targets):
            teensy = {int(k): v for k, v in ast.literal_eval(node.value).items()}
        if (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "add" and node.args
                and isinstance(node.args[0], ast.Constant) and node.args[0].value in ("U12", "U13")):
            parts[node.args[0].value] = ast.literal_eval(node.args[5])
    if teensy is None:
        sys.exit(f"{path}: TEENSY nicht gefunden")
    if set(parts) != {"U12", "U13"}:
        print(f"{path}: kein CS-Decoder U12 / keine Mux U13, Stand vor E10; nichts zu vergleichen")
        sys.exit(2)
    return teensy, parts


def parse_header():
    text = HEADER.read_text(encoding="utf-8")
    pins = {int(n): net for n, net in re.findall(r"constexpr uint8_t PIN_\w+\s*=\s*(\d+);\s*//\s*(\w+)", text)}

    def enum(name):
        body = re.search(r"enum class %s[^{]*\{(.*?)\};" % name, text, re.S).group(1)
        return {int(v): net for v, net in re.findall(r"\w+\s*=\s*(\d+),\s*//\s*(\w+)", body)}

    return pins, enum("Cs"), enum("Mux")


def main():
    circuit = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "hardware/mainboard/kicad/circuit.py"
    teensy, parts = parse_circuit(circuit)
    pins, cs, mux = parse_header()
    errors = []

    for pin in sorted(set(teensy) | set(pins)):
        want, have = teensy.get(pin), pins.get(pin)
        if want != have:
            errors.append(f"Teensy-Pin {pin}: circuit.py {want!r}, BoardRevB.h {have!r}")

    for ref, ymap, selmap, enum_, what in (("U12", HC138_Y, HC138_SEL, cs, "Cs"),
                                            ("U13", HC4051_Y, HC4051_SEL, mux, "Mux")):
        conn = parts[ref]
        for pad, net in selmap.items():
            if conn.get(pad) != net:
                errors.append(f"{ref} Pin {pad}: erwartet {net}, circuit.py {conn.get(pad)!r}")
        for pad, y in ymap.items():
            want = conn.get(pad)
            have = enum_.get(y)
            if want is None and have and have.startswith("Y"):
                continue                       # offener Ausgang, im Header als "Y7 offen"
            if want != have:
                errors.append(f"{ref} Y{y}: circuit.py {want!r}, BoardRevB.h {what} {have!r}")

    print(f"circuit.py: {circuit}")
    if errors:
        print("\n".join("  " + e for e in errors))
        print(f"{len(errors)} Abweichung(en)")
        return 1
    print(f"OK: {len(teensy)} Teensy-Pins, 8 Chip-Selects, 8 Analogkanäle stimmen überein")
    return 0


if __name__ == "__main__":
    sys.exit(main())
