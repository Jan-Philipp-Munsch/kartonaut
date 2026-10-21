"""Gate 1 of ORDER.md: the netlist against the pin table of the spec (README.md §4).

For every Teensy pin in the table the check follows its net to the part the spec names, allowing
one series resistor (servo, gate, camera and divider resistors). It reads the netlist that KiCad
exports from the schematic, so it checks the drawn schematic, not circuit.py.

Run:  python check_design.py        (exports out/mainboard.net with kicad-cli first)
"""
import os
import subprocess
import sys
from pathlib import Path

from build_lib import teensy_pad
from sexpr import find, findall, parse

HERE = Path(__file__).resolve().parent
CLI = Path(os.environ["LOCALAPPDATA"]) / "Programs/KiCad/10.0/bin/kicad-cli.exe"

# Teensy pin -> list of (ref, pin) the spec says it must reach (README.md §4)
EXPECT = {
    "0": [("J11", "3")], "1": [("J11", "4")],                          # GPS TX -> RX1, RX <- TX1
    "2": [("U7", "16"), ("U7", "9")], "3": [("U7", "15"), ("U7", "10")],   # DRV8833 AIN1=BIN1, AIN2=BIN2
    "4": [("U4", "4")],                                                # IMU INT1
    "5": [("U8", "2")], "6": [("U9", "2")],                            # LED level shifters
    "7": [("J13", "2")],                                               # camera via 1 k
    "8": [("U7", "8")],                                                # nFAULT (not in the spec, see README §4)
    "9": [("J7", "1")],                                                # chute servo via 220
    "13": [("Q5", "1")],                                               # buzzer FET gate via 100
    "18": [("U5", "4"), ("U6", "3"), ("J12", "3")],                    # SDA: BMP390, INA219, Qwiic
    "19": [("U5", "2"), ("U6", "4"), ("J12", "4")],                    # SCL
    "20": [("Q3", "3")], "21": [("Q4", "3")],                          # pyro sense: drain via divider
    "22": [("Q4", "1")], "23": [("Q3", "1")],                          # pyro fire: gate via 100
    "24": [("J4", "2")],                                               # ARM_SENSE from VBAT_ARMED
    "26": [("U4", "14")], "27": [("U4", "13")], "39": [("U4", "1")], "38": [("U4", "12")],   # SPI1
    "28": [("J5", "1")], "29": [("J6", "1")],                          # TVC servos via 220
    "32": [("U10", "21")], "33": [("U10", "20")],                      # LoRa M1, M0
    "34": [("U10", "23")], "35": [("U10", "22")], "36": [("U10", "24")],   # RX8 <- TXD, TX8 -> RXD, AUX
    "40": [("J3", "4")],                                               # VBAT2_SENSE from VBAT_PROT
    "41": [("J3", "2")],                                               # VBAT1_SENSE from VSYS_IN
}
EXP_PINS = ["10", "11", "12", "14", "15", "16", "17", "25", "30", "31", "37"]


def netlist():
    out = HERE / "out" / "mainboard.net"
    subprocess.run([str(CLI), "sch", "export", "netlist", "--format", "kicadsexpr", "-o", str(out),
                    str(HERE / "mainboard.kicad_sch")], check=True, capture_output=True)
    tree = parse(out.read_text(encoding="utf-8"))
    nets, pin_net, values = {}, {}, {}
    for comp in findall(find(tree, "components"), "comp"):
        values[str(find(comp, "ref")[1])] = str(find(comp, "value")[1])
    for n in findall(find(tree, "nets"), "net"):
        name = str(find(n, "name")[1]).split("/")[-1]
        nodes = [(str(find(x, "ref")[1]), str(find(x, "pin")[1])) for x in findall(n, "node")]
        nets[name] = nodes
        for node in nodes:
            pin_net[node] = name
    return nets, pin_net, values


def reach(start_net, nets, pin_net, hops=1):
    """All (ref, pin) on start_net and, through up to `hops` resistors, on the nets beyond."""
    seen, frontier, found = {start_net}, [start_net], set()
    for depth in range(hops + 1):
        nxt = []
        for net in frontier:
            for ref, pin in nets[net]:
                found.add((ref, pin))
                if depth < hops and ref.startswith("R") and not ref.startswith("R_SH"):
                    other = pin_net.get((ref, "2" if pin == "1" else "1"))
                    if other and other not in seen and other not in ("GND", "GND_PWR"):
                        seen.add(other)
                        nxt.append(other)
        frontier = nxt
    return found


def main():
    nets, pin_net, values = netlist()
    errors = []
    for tpin, targets in EXPECT.items():
        net = pin_net.get(("A1", teensy_pad(tpin)))
        if net is None:
            errors.append(f"Teensy {tpin}: nicht angeschlossen")
            continue
        got = reach(net, nets, pin_net)
        for t in targets:
            if t not in got:
                errors.append(f"Teensy {tpin} ({net}): erreicht {t[0]}.{t[1]} nicht")
    for i, tpin in enumerate(EXP_PINS):
        net = pin_net.get(("A1", teensy_pad(tpin)))
        if ("J15", str(3 + i)) not in nets.get(net, []):
            errors.append(f"Teensy {tpin}: nicht auf J_EXP Pin {3 + i}")
    used = set(EXPECT) | set(EXP_PINS)
    unused = [str(i) for i in range(42) if str(i) not in used]
    if unused:
        errors.append(f"Teensy-Pins ohne Ziel in der Pruefung: {unused}")
    # power rails and their sources
    rails = {"TEENSY_VIN": [("A1", teensy_pad("VIN")), ("D1", "1")], "3V3_RF": [("U3", "5"), ("U10", "25"), ("J11", "1")],
             "5V_SYS": [("U2", "7"), ("D1", "2"), ("U3", "1")], "VSERVO": [("F1", "2"), ("J5", "2"), ("J6", "2")],
             "5V_SERVO": [("L1", "2"), ("J7", "2"), ("U7", "12")], "VBAT_ARMED": [("J4", "2"), ("J9", "1"), ("J10", "1")]}
    for rail, nodes in rails.items():
        for node in nodes:
            if node not in nets.get(rail, []):
                errors.append(f"{rail}: {node[0]}.{node[1]} fehlt")
    if values.get("R_SH1") != "20m 1% 1W":
        errors.append("Shunt ist nicht 20 mOhm")
    print(f"{len(EXPECT) + len(EXP_PINS)} Teensy-Pins und {len(rails)} Schienen geprueft")
    for e in errors:
        print("FEHLER:", e)
    print("OK: Netzliste entspricht README.md §4" if not errors else f"{len(errors)} Abweichungen")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
