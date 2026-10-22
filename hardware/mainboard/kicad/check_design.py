"""Gate 1 of ORDER.md: the netlist against the pin table of the spec (README.md §4, rev B1).

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

# Teensy pin -> list of (ref, pin) it must reach: spec README.md section 4 with the rev B1 changes
# (Komponenten_2026-10-22.md section 5, 8, 9; kicad/README.md section 7)
SPI_DEVICES = [("U4", "14", "13", "1"), ("U5", "4", "2", "5"), ("U15", "4", "2", "5"), ("U6", "2", "5", "4"),
               ("J15", "8", "7", "9")]                           # (ref, MOSI, SCK, MISO)
EXPECT = {
    "0": [("J11", "3")], "1": [("J11", "4")],                          # GPS TX -> RX1, RX <- TX1
    "2": [("U7", "16"), ("U7", "9")], "3": [("U7", "15"), ("U7", "10")],   # DRV8833 AIN1=BIN1, AIN2=BIN2
    "4": [("U4", "4")],                                                # IMU INT1
    "5": [("U8", "2")],                                                # LED chain level shifter (B8)
    "6": [("U10", "1")],                                               # LoRa NRST (B9)
    "7": [("J13", "2")],                                               # camera via 1 k
    "8": [("U7", "8")],                                                # nFAULT
    "9": [("J7", "1")], "10": [("J16", "1")],                          # chute servo, landing-leg servo (E5)
    "11": [("U7", "1")],                                               # DRV8833 nSLEEP (C1)
    "12": [("Q8", "1")], "14": [("Q9", "1")],                          # pyro 3/4 fire (E5)
    "13": [("J15", "18")], "15": [("J15", "20")], "17": [("J15", "13")],   # J_STACK PWM, nRST, IRQ
    "18": [("J12", "3"), ("J15", "14")], "19": [("J12", "4"), ("J15", "15")],   # I2C: Qwiic and J_STACK only (E3)
    "20": [("J15", "17")], "21": [("J15", "16")],                      # Serial5 TX/RX to J_STACK
    "22": [("Q4", "1")], "23": [("Q3", "1")],                          # pyro 2/1 fire: gate via 100
    "24": [("U13", "3")],                                              # analog mux output
    "38": [("U12", "1"), ("U13", "11")], "25": [("U12", "2"), ("U13", "10")], "30": [("U12", "3"), ("U13", "9")],
    "31": [("U12", "4")],                                              # decoder enable (active low)
    "26": [(r, m) for r, m, _, _ in SPI_DEVICES], "27": [(r, k) for r, _, k, _ in SPI_DEVICES],
    "39": [(r, i) for r, _, _, i in SPI_DEVICES],                      # SPI1 to every device (E3)
    "28": [("J5", "1")], "29": [("J6", "1")],                          # TVC servos via 220
    "32": [("U10", "21")], "33": [("U10", "20")],                      # LoRa M1, M0
    "34": [("U10", "23")], "35": [("U10", "22")], "36": [("U10", "24")],   # RX8 <- TXD, TX8 -> RXD, AUX
    "37": [("Q5", "1")],                                               # buzzer FET gate via 100 (B7)
}
SPARE = ["16", "40", "41"]
# decoder output -> chip select pin, mux input -> what it measures (through one divider resistor)
CHIP_SELECTS = {("U12", "15"): ("U4", "12"), ("U12", "14"): ("U5", "6"), ("U12", "13"): ("U15", "6"),
                ("U12", "12"): ("U6", "1"), ("U12", "11"): ("J15", "10"), ("U12", "10"): ("J15", "11"),
                ("U12", "9"): ("J15", "12")}
MUX = {("U13", "13"): ("Q3", "3"), ("U13", "14"): ("Q4", "3"), ("U13", "15"): ("Q8", "3"),
       ("U13", "12"): ("Q9", "3"), ("U13", "1"): ("F2", "2"), ("U13", "5"): ("F1", "2"), ("U13", "2"): ("J4", "2")}

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
    for (u, pin), target in list(CHIP_SELECTS.items()) + list(MUX.items()):
        net = pin_net.get((u, pin))
        if net is None or target not in reach(net, nets, pin_net):
            errors.append(f"{u}.{pin} ({net}): erreicht {target[0]}.{target[1]} nicht")
    for tpin in SPARE:
        if pin_net.get(("A1", teensy_pad(tpin))) not in (None, ""):
            net = pin_net.get(("A1", teensy_pad(tpin)))
            if not net.startswith("unconnected"):
                errors.append(f"Teensy {tpin}: als Reserve gedacht, haengt an {net}")
    used = set(EXPECT) | set(SPARE)
    unused = [str(i) for i in range(42) if str(i) not in used]
    if unused:
        errors.append(f"Teensy-Pins ohne Ziel in der Pruefung: {unused}")
    # power rails and their sources
    rails = {"TEENSY_VIN": [("A1", teensy_pad("VIN")), ("D1", "1")], "3V3_RF": [("U3", "5"), ("U10", "25"), ("J11", "1")],
             "5V_SYS": [("U2", "7"), ("D1", "2"), ("U3", "1"), ("U14", "1"), ("J15", "4")],
             "VSYS_IN": [("Q7", "3"), ("U2", "1"), ("U2", "12")], "VBAT_PROT": [("Q6", "3"), ("R_SH1", "1"), ("J4", "1")],
             "VSERVO": [("R_SH1", "4"), ("J5", "2"), ("J6", "2"), ("J7", "2"), ("J16", "2"), ("U7", "12"), ("J15", "5")],
             "VBAT_ARMED": [("J4", "2"), ("J9", "1"), ("J10", "1"), ("J19", "1"), ("J20", "1")],
             "3V3_SENS": [("FB1", "2"), ("U4", "5"), ("U4", "8"), ("U5", "10"), ("U15", "10")],
             "3V3_EXP": [("U14", "5"), ("J15", "3")], "VBAT1_F": [("F2", "2"), ("Q7", "2"), ("U11", "3")],
             "VBAT2_RAW": [("J1", "1"), ("J18", "1"), ("Q1", "3")]}
    # Kelvin (A5): the sense nets reach the shunt only at its sense pads
    for net, pad in (("ISENS_P", ("R_SH1", "2")), ("ISENS_N", ("R_SH1", "3"))):
        if [n for n in nets.get(net, []) if n[0] == "R_SH1"] != [pad]:  # VBUS of U6 on ISENS_N is fine
            errors.append(f"{net}: Kelvin-Abgriff nicht nur am Sense-Pad {pad[1]}")
    for rail, nodes in rails.items():
        for node in nodes:
            if node not in nets.get(rail, []):
                errors.append(f"{rail}: {node[0]}.{node[1]} fehlt")
    if values.get("R_SH1") != "20m 1% 1W":
        errors.append("Shunt ist nicht 20 mOhm")
    print(f"{len(EXPECT)} Teensy-Pins, {len(CHIP_SELECTS)} Chip-Selects, {len(MUX)} Mux-Kanaele und {len(rails)} Schienen geprueft")
    for e in errors:
        print("FEHLER:", e)
    print("OK: Netzliste entspricht README.md §4 mit den B1-Aenderungen" if not errors else f"{len(errors)} Abweichungen")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
