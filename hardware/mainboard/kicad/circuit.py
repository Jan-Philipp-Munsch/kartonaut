"""The circuit of mainboard rev B1 as data: parts, values, footprints, nets.

Single source for the schematic (gen_schematic.py), the board (gen_pcb.py) and the checks
(check_design.py). Rev B1 is rev B (hardware/mainboard/README.md) plus the changes decided on
21/22 Oct 2026: review A1-A8 (review_kicad_2026-10-21.md) and decisions E1-E10
(Komponenten_2026-10-22.md, datasheet MS-MB-B section "Beschlossene Aenderungen"). Where this file had
to decide something those documents leave open, the comment says so and kicad/README.md section 6 lists it.

Net names follow the spec. GND is the logic ground (1S minus, Teensy, sensors); GND_PWR is the
return of everything fed from the 2S pack (servos, motor driver, pyro). They meet in exactly one
point, the net tie NT1 next to the 2S minus at J1 (spec section 3: star point).
"""
from dataclasses import dataclass, field

from build_lib import teensy_pad

SHEETS = [  # (file stem, sheet title, page title shown on the sheet)
    ("power", "Versorgung", "Versorgung: 1S-Pfad (Elektronik, Lader) und 2S-Pfad (Aktoren, Pyro), Lastschalter"),
    ("mcu", "Teensy", "Teensy 4.1, CS-Decoder und Analogmux, Stapelstecker J_STACK"),
    ("sensors", "Sensorik", "IMU ICM-42688-P und zwei BMP390 an SPI1, Qwiic an I2C"),
    ("radio", "Funk", "LoRa E22-400T22S an Serial8, GPS an Serial1"),
    ("actuators", "Aktoren", "Vier Servos und Rollmotor DRV8833 am 2S-Akku"),
    ("pyro", "Pyro", "Vier Pyro-Kanaele low-side (3 und 4 DNP), Arming, Durchgangspruefung"),
    ("signal", "Signal", "WS2812B-Kette mit Pegelwandler, Summer, Kamera-Trigger"),
]


@dataclass
class Part:
    ref: str
    lib: str                      # "Library:Symbol"
    value: str
    fp: str                       # "Library:Footprint"
    sheet: str
    pins: dict                    # pin number (str) -> net name, or None for no-connect
    lcsc: str = ""
    func: str = ""                # name used in README.md (J_BAT2, U_TEENSY ...)
    descr: str = ""
    dnp: bool = False
    fields: dict = field(default_factory=dict)
    group: str = ""               # functional block on the schematic sheet


PARTS: list = []
_group = [""]


def group(title):
    """All parts added after this call belong to the block 'title' on their sheet."""
    _group[0] = title


def add(ref, lib, value, fp, sheet, pins, **kw):
    PARTS.append(Part(ref, lib, value, fp, sheet, {str(k): v for k, v in pins.items()}, group=_group[0], **kw))


# ---------------------------------------------------------------- footprints and helpers
R0603 = "Resistor_SMD:R_0603_1608Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"
C1210 = "Capacitor_SMD:C_1210_3225Metric"
CP7343 = "Capacitor_Tantalum_SMD:CP_EIA-7343-31_Kemet-D"     # polymer, 3.1 mm high (review B3)
L5040 = "Inductor_SMD:L_Changjiang_FNR5040S"
SOT23 = "Package_TO_SOT_SMD:SOT-23"
SOT235 = "Package_TO_SOT_SMD:SOT-23-5"
TSSOP16 = "Package_SO:TSSOP-16_4.4x5mm_P0.65mm"
TP = "TestPoint:TestPoint_Pad_D1.5mm"
SJ = "Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm"
JST = "Connector_JST:"
XH2_SIDE = JST + "JST_XH_S2B-XH-A_1x02_P2.50mm_Horizontal"
XH2_TOP = JST + "JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical"
XH3_SIDE = JST + "JST_XH_S3B-XH-A_1x03_P2.50mm_Horizontal"
XH3_TOP = JST + "JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical"

_n = {"R": 0, "C": 0, "TP": 0}


def _next(prefix):
    _n[prefix] += 1
    return f"{prefix}{_n[prefix]}"


def R(value, a, b, sheet, fp=R0603, **kw):
    ref = _next("R")
    add(ref, "Device:R", value, fp, sheet, {1: a, 2: b}, **kw)
    return ref


def C(value, a, b, sheet, fp=C0603, **kw):
    ref = _next("C")
    add(ref, "Device:C", value, fp, sheet, {1: a, 2: b}, **kw)
    return ref


def CP(value, plus, minus, sheet, fp, **kw):
    ref = _next("C")
    add(ref, "Device:C_Polarized", value, fp, sheet, {1: plus, 2: minus}, **kw)
    return ref


def testpoint(net, sheet):
    ref = _next("TP")
    add(ref, "Connector:TestPoint", net, TP, sheet, {1: net}, descr=f"Testpunkt {net}")
    return ref


def divider(top, node, sheet, low_group=None, **kw):
    """100 k / 33 k to GND with 100 nF: full scale 13.3 V at 3.3 V (spec section 4).

    low_group: put the 33 k and the 100 nF into that block (at the analog mux), the 100 k stays at the
    measured node. Same divider, the filter capacitor sits at the mux input."""
    R("100k", top, node, sheet, **kw)
    if low_group:
        here = _group[0]
        group(low_group)
        R("33k", node, "GND", sheet, **kw)
        C("100n", node, "GND", sheet, **kw)
        group(here)
    else:
        R("33k", node, "GND", sheet, **kw)
        C("100n", node, "GND", sheet, **kw)


# ================================================================ Versorgung (spec 3, E1, E2, A1-A5)
S = "power"
group("2S: Akku, Verpolschutz, Sicherung, Lastschalter")
# 2S path: XT30 -> reverse protection Q1 -> polyfuse F1 (A4) -> P-FET load switch Q6 (E1) -> VBAT_PROT.
# Q6 sits source to source with Q1 (fuse between them): its body diode blocks when it is off. The
# main switch on the switch board only pulls Q6's gate to ground; J3 carries microamps (E1).
add("J1", "Connector_Generic:Conn_01x02", "XT30PW-M", "Connector_AMASS:AMASS_XT30PW-M_1x02_P2.50mm_Horizontal", S,
    {1: "VBAT2_RAW", 2: "GND_PWR"}, func="J_BAT2", descr="2S-LiPo 6,0-8,4 V, Pin 1 = Plus")
add("J18", "Connector_Generic:Conn_01x02", "J_CHG2", JST + "JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical", S,
    {1: "VBAT2_RAW", 2: "GND_PWR"}, func="J_CHG2",
    descr="2S-Ladeanschluss parallel zu J_BAT2 (<= 1 A), Kabel zur XT30-Ladebuchse am Schalterbrett (E2)")
add("Q1", "Transistor_FET:AO3401A", "AO3401A", SOT23, S, {1: "Q1_G", 2: "VBAT2_REV", 3: "VBAT2_RAW"},
    lcsc="C15127", descr="Verpolschutz 2S")
R("10k", "Q1_G", "GND_PWR", S)
add("F1", "Device:Polyfuse", "3A hold 6A trip", "Fuse:Fuse_1812_4532Metric", S, {1: "VBAT2_REV", 2: "VBAT2_F"},
    func="F_BAT2", descr="Polyfuse 2S direkt hinter dem Verpolschutz, 1812 (Review A4)")
add("Q6", "Transistor_FET:AO3401A", "AO3401A", SOT23, S, {1: "Q6_G", 2: "VBAT2_F", 3: "VBAT_PROT"},
    lcsc="C15127", func="Q_SW2", descr="Lastschalter 2S, Gate ueber J_SW auf GND_PWR = ein (E1)")
R("100k", "Q6_G", "VBAT2_F", S, descr="haelt Q6 ohne Schalter aus")
R("1k", "Q6_G", "SW2_G", S, descr="Schutz des Gates gegen das Schalterkabel")
add("J3", "Connector_Generic:Conn_01x04", "J_SW", JST + "JST_PH_B4B-PH-K_1x04_P2.00mm_Vertical", S,
    {1: "SW1_G", 2: "GND", 3: "SW2_G", 4: "GND_PWR"}, func="J_SW",
    descr="zweipoliger Hauptschalter: 1-2 schaltet den 1S-Pfad, 3-4 den 2S-Pfad (nur Gates, Mikroampere)")
add("JP1", "Jumper:SolderJumper_2_Open", "SJ 1S", SJ, S, {1: "SW1_G", 2: "GND"},
    descr="ersetzt den Schalter 1S auf dem Tisch")
add("JP2", "Jumper:SolderJumper_2_Open", "SJ 2S", SJ, S, {1: "SW2_G", 2: "GND_PWR"},
    descr="ersetzt den Schalter 2S auf dem Tisch")
group("2S: Spannungsmessung, Shunt und INA239")
divider("VBAT2_F", "VBAT2_SENSE", S, low_group="Messteiler am Analogmux")       # before the load switch: readable with the rocket off (E2)
# Shunt with split Kelvin lands (A5): pads 1/4 carry the current, 2/3 are the sense taps
add("R_SH1", "Device:R_Shunt", "20m 1% 1W", "mainboard:R_2512_Kelvin", S,
    {1: "VBAT_PROT", 2: "ISENS_P", 3: "ISENS_N", 4: "VSERVO"}, func="R_SHUNT",
    descr="Shunt 2S-Pfad, 2512, Kelvin-Abgriff ueber geteilte Pads")
R("10", "ISENS_P", "INA_INP", S, descr="Eingangsfilter INA239")
R("10", "ISENS_N", "INA_INN", S, descr="Eingangsfilter INA239")
C("100n", "INA_INP", "INA_INN", S, descr="Differenzfilter gegen Servo-PWM (A5)")
add("U6", "mainboard:INA239", "INA239AIDGSR", "Package_SO:MSOP-10_3x3mm_P0.5mm", S,
    {1: "CS_INA", 2: "SPI1_MOSI", 3: None, 4: "SPI1_MISO", 5: "SPI1_SCK", 6: "3V3", 7: "GND", 8: "ISENS_N",
     9: "INA_INN", 10: "INA_INP"},
    descr="Strom/Spannung 2S an SPI1 (E3); VBUS am Kelvin-Abgriff (8 uA); Bezug DigiKey, Handloetung")
C("100n", "3V3", "GND", S)
group("2S: Servo-Schiene VSERVO")
CP("330u/16V polymer", "VSERVO", "GND_PWR", S, CP7343, descr="Puffer VSERVO, 7343 (B3)")
CP("330u/16V polymer", "VSERVO", "GND_PWR", S, CP7343, descr="Puffer VSERVO, 7343 (B3)")
C("10u/25V", "VSERVO", "GND_PWR", S, fp=C0805)
group("1S: Akku, Verpolschutz, Sicherung, Lastschalter")
# 1S path: JST-PH -> reverse protection Q2 -> polyfuse F2 -> P-FET load switch Q7 -> VSYS_IN
add("J2", "Connector_Generic:Conn_01x02", "J_BAT1", JST + "JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical", S,
    {1: "VBAT1_RAW", 2: "GND"}, func="J_BAT1", descr="1S-LiPo 3,0-4,2 V, Pin 1 = Plus")
add("Q2", "Transistor_FET:AO3401A", "AO3401A", SOT23, S, {1: "Q2_G", 2: "VBAT1_REV", 3: "VBAT1_RAW"},
    lcsc="C15127", descr="Verpolschutz 1S")
R("10k", "Q2_G", "GND", S)
add("F2", "Device:Polyfuse", "2A hold", "Fuse:Fuse_1812_4532Metric", S, {1: "VBAT1_REV", 2: "VBAT1_F"},
    func="F_BAT1", descr="Polyfuse 1S direkt hinter dem Verpolschutz, 1812 (Review A4)")
add("Q7", "Transistor_FET:AO3401A", "AO3401A", SOT23, S, {1: "Q7_G", 2: "VBAT1_F", 3: "VSYS_IN"},
    lcsc="C15127", func="Q_SW1", descr="Lastschalter 1S, Gate ueber J_SW auf GND = ein (E1)")
R("100k", "Q7_G", "VBAT1_F", S, descr="haelt Q7 ohne Schalter aus")
R("1k", "Q7_G", "SW1_G", S, descr="Schutz des Gates gegen das Schalterkabel")
divider("VBAT1_F", "VBAT1_SENSE", S, low_group="Messteiler am Analogmux")
group("1S: Lader MCP73831")
# E2: the 1S cell is charged in the rocket from USB-C on the switch board; charge LED there too.
# Charger output on VBAT1_F, before the load switch: charges with the rocket switched off.
add("J17", "Connector_Generic:Conn_01x03", "J_CHG1", JST + "JST_PH_B3B-PH-K_1x03_P2.00mm_Vertical", S,
    {1: "VBUS_CHG", 2: "GND", 3: "CHG_STAT"}, func="J_CHG1",
    descr="Kabel zum Schalterbrett: USB-C VBUS, GND, Lade-LED (Kathode)")
add("U11", "Battery_Management:MCP73831-2-OT", "MCP73831T-2ACI/OT", SOT235, S,
    {1: "CHG_STAT", 2: "GND", 3: "VBAT1_F", 4: "VBUS_CHG", 5: "CHG_PROG"}, lcsc="C424093",
    descr="1S-Lader 4,2 V, 500 mA")
R("2k", "CHG_PROG", "GND", S, descr="Ladestrom 1000 V / 2 k = 500 mA")
C("4.7u", "VBUS_CHG", "GND", S, fp=C0805)
C("4.7u", "VBAT1_F", "GND", S, fp=C0805)
group("1S: Buck-Boost U2 -> 5V_SYS, Teensy-VIN")
# U2 TPS63070 buck-boost: 5V_SYS from 1S. Vout = 0.8 V (1 + 680k/130k) = 4.98 V (TI table 4).
# EN divider 330k/115k (A2): on above 3.1 V, off below 2.7 V (EN 0.8/0.7 V). FB2 open (B2).
add("U2", "lcsc:TPS63070RNMR", "TPS63070RNMR", "lcsc:VQFN-15_L3.0-W2.5-P0.50-BL", S,
    {1: "VSYS_IN", 2: None, 3: "U2_VAUX", 4: "GND", 5: "U2_FB", 6: None, 7: "5V_SYS", 9: "U2_L2",
     10: "GND", 11: "U2_L1", 12: "VSYS_IN", 14: "U2_EN", 15: "GND"}, lcsc="C109322",
    descr="Buck-Boost 5V_SYS aus 1S, 2-16 V ein; PS/SYNC hoch = Stromsparbetrieb bei Teillast")
C("10u/25V", "VSYS_IN", "GND", S, fp=C0805)
C("10u/25V", "VSYS_IN", "GND", S, fp=C0805)
C("100n", "U2_VAUX", "GND", S)
add("L2", "Device:L", "1.5u Isat>=4A", L5040, S, {1: "U2_L1", 2: "U2_L2"}, descr="5040, Isat >= 4 A")
R("680k", "5V_SYS", "U2_FB", S)
R("130k", "U2_FB", "GND", S)
R("330k", "VSYS_IN", "U2_EN", S)
R("115k", "U2_EN", "GND", S, descr="EN-Schwelle: an ab 3,1 V, aus unter 2,7 V (A2)")
for _ in range(3):
    C("22u/10V", "5V_SYS", "GND", S, fp=C0805)    # 66 uF at VOUT, datasheet limit 470 uF (A1)
add("D1", "Diode:SS14", "SS14", "Diode_SMD:D_SMA", S, {1: "TEENSY_VIN", 2: "5V_SYS"}, lcsc="C2480",
    descr="5V_SYS -> Teensy VIN, USB darf gleichzeitig stecken (VIN-VUSB-Bruecke nicht trennen, B11)")
CP("470u/6.3V polymer", "TEENSY_VIN", "GND", S, CP7343, descr="Hold-up hinter D1 (A1), 7343")
CP("470u/6.3V polymer", "TEENSY_VIN", "GND", S, CP7343, descr="Hold-up hinter D1 (A1), 7343")
group("LDOs 3V3_RF und 3V3_EXP, Sensorinsel, Sternpunkt")
# U3 AP2112K-3.3: 3V3_RF for LoRa and GPS
add("U3", "Regulator_Linear:AP2112K-3.3", "AP2112K-3.3TRG1", SOT235, S,
    {1: "5V_SYS", 2: "GND", 3: "5V_SYS", 4: None, 5: "3V3_RF"}, lcsc="C51118", descr="LDO 3V3_RF, 600 mA")
C("1u", "5V_SYS", "GND", S)
C("1u", "3V3_RF", "GND", S)
C("100u/6.3V", "3V3_RF", "GND", S, fp=C1210, descr="Puffer fuer den LoRa-Sendepuls")
# U14 AP2112K-3.3: 3V3_EXP for boards on J_STACK, not the 250 mA of the Teensy LDO (E10)
add("U14", "Regulator_Linear:AP2112K-3.3", "AP2112K-3.3TRG1", SOT235, S,
    {1: "5V_SYS", 2: "GND", 3: "5V_SYS", 4: None, 5: "3V3_EXP"}, lcsc="C51118", descr="LDO 3V3_EXP, 600 mA")
C("1u", "5V_SYS", "GND", S)
C("1u", "3V3_EXP", "GND", S)
# 3V3_SENS (B4): IMU and barometers behind a ferrite, away from the ripple of the Teensy CPU
add("FB1", "Device:FerriteBead", "600R@100MHz", "Inductor_SMD:L_0603_1608Metric", S, {1: "3V3", 2: "3V3_SENS"},
    descr="Ferrit 0603, 600 Ohm bei 100 MHz, >= 500 mA")
C("10u", "3V3_SENS", "GND", S, fp=C0805)
add("NT1", "Device:NetTie_2", "NetTie", "NetTie:NetTie-2_SMD_Pad0.5mm", S, {1: "GND_PWR", 2: "GND"},
    descr="Sternpunkt: einzige Verbindung der beiden Massen, direkt am 2S-Minus")
for net in ["VBAT_PROT", "VSYS_IN", "5V_SYS", "VSERVO", "3V3_RF", "3V3_EXP", "GND"]:
    testpoint(net, S)

# ================================================================ Teensy (spec 4, Komponenten 5, 8, 9)
S = "mcu"
group("Teensy 4.1")
TEENSY = {  # Teensy pin -> net
    "0": "GPS_TX", "1": "GPS_RX", "2": "MOT_IN1", "3": "MOT_IN2", "4": "IMU_INT", "5": "LED_DATA",
    "6": "LORA_NRST", "7": "CAM_TRIG", "8": "MOT_FAULT", "9": "SERVO_CHUTE", "10": "SERVO_LEGS",
    "11": "MOT_NSLEEP", "12": "PYRO3_FIRE", "13": "PWM_EXT", "14": "PYRO4_FIRE", "15": "NRST_EXT",
    "17": "IRQ_EXT", "18": "SDA", "19": "SCL", "20": "EXT_TX", "21": "EXT_RX", "22": "PYRO2_FIRE",
    "23": "PYRO1_FIRE", "24": "MUX_OUT", "25": "SEL1", "26": "SPI1_MOSI", "27": "SPI1_SCK",
    "28": "SERVO_YAW", "29": "SERVO_PITCH", "30": "SEL2", "31": "CS_EN", "32": "LORA_M1", "33": "LORA_M0",
    "34": "LORA_TXD", "35": "LORA_RXD", "36": "LORA_AUX", "37": "BUZZER", "38": "SEL0", "39": "SPI1_MISO",
}
SPARE_PINS = ["16", "40", "41"]          # free after the decoder and the mux (Komponenten 9)
_tp = {teensy_pad(k): v for k, v in TEENSY.items()}
for p in SPARE_PINS:
    _tp[teensy_pad(p)] = None
for num, name in __import__("build_lib").TEENSY_PINS.items():
    if name == "GND":
        _tp[str(num)] = "GND"
    elif name == "3V3":
        _tp[str(num)] = "3V3"
    elif name == "VIN":
        _tp[str(num)] = "TEENSY_VIN"
add("A1", "mainboard:Teensy4.1_Socket", "Teensy 4.1", "mainboard:Teensy41_Socket", S, _tp, func="U_TEENSY",
    descr="2x Buchsenleiste 1x24, 2,54 mm, 8,5 mm hoch (THT, selbst loeten)")
group("CS-Decoder und Analogmux")
# Komponenten 9: three select lines address both the 74HC138 (SPI chip selects) and the 74HC4051
# (slow analog inputs). CS_EN (decoder enable, active low) is pulled high: during boot and between
# transfers every chip select is high. The mux is always on; the firmware reads a channel while CS_EN
# is high, so no SPI device is selected.
add("U12", "74xx:74HC138", "74HC138PW", TSSOP16, S,
    {1: "SEL0", 2: "SEL1", 3: "SEL2", 4: "CS_EN", 5: "GND", 6: "3V3", 7: None, 8: "GND", 9: "CS_EXT2",
     10: "CS_EXT1", 11: "CS_EXT0", 12: "CS_INA", 13: "CS_BARO2", 14: "CS_BARO", 15: "CS_IMU", 16: "3V3"},
    descr="SPI-CS-Decoder: Y0 IMU, Y1 Baro, Y2 Baro 2, Y3 INA239, Y4-Y6 J_STACK, Y7 frei")
R("10k", "3V3", "CS_EN", S, descr="Decoder aus waehrend des Boots: alle CS hoch")
C("100n", "3V3", "GND", S)
add("U13", "74xx:74HC4051", "74HC4051PW", TSSOP16, S,
    {1: "VBAT1_SENSE", 2: "ARM_SENSE", 3: "MUX_OUT", 4: "GND", 5: "VBAT2_SENSE", 6: "GND", 7: "GND", 8: "GND",
     9: "SEL2", 10: "SEL1", 11: "SEL0", 12: "PYRO4_SENSE", 13: "PYRO1_SENSE", 14: "PYRO2_SENSE",
     15: "PYRO3_SENSE", 16: "3V3"},
    descr="Analogmux: 0-3 Pyro 1-4, 4 1S, 5 2S, 6 ARM, 7 GND (Nullpunkt)")
C("100n", "3V3", "GND", S)
group("Stapelstecker J_STACK, Befestigung, Testpunkte")
# E10 / Komponenten 8: 2x10, 2.54 mm, flat cable to a board in the ring stack.
# Deviation: pin 2 is GND_PWR (return of VSERVO on pins 5/6) instead of a second GND, so servo
# current of an extension board does not flow through the logic ground. Do not join them there.
add("J15", "Connector_Generic:Conn_02x10_Odd_Even", "J_STACK", "Connector_PinHeader_2.54mm:PinHeader_2x10_P2.54mm_Vertical",
    S, {1: "GND", 2: "GND_PWR", 3: "3V3_EXP", 4: "5V_SYS", 5: "VSERVO", 6: "VSERVO", 7: "SPI1_SCK",
        8: "SPI1_MOSI", 9: "SPI1_MISO", 10: "CS_EXT0", 11: "CS_EXT1", 12: "CS_EXT2", 13: "IRQ_EXT",
        14: "SDA", 15: "SCL", 16: "EXT_RX", 17: "EXT_TX", 18: "PWM_EXT", 19: "ARM_EXT", 20: "NRST_EXT"},
    func="J_STACK", descr="Stapelstecker fuer Zusatzplatinen (Flachband)")
R("10k", "ARM_SENSE", "ARM_EXT", S, descr="ARM-Pegel (0-2,1 V) zur Zusatzplatine, entkoppelt")
for i in range(1, 5):
    add(f"H{i}", "Mechanical:MountingHole", "M3", "MountingHole:MountingHole_3.2mm_M3", S, {},
        descr="M3 zum gedruckten Traeger")

# ================================================================ Sensorik (spec 6, E3, B4, C2)
S = "sensors"
group("IMU ICM-42688-P, SPI1")
add("U4", "lcsc:ICM-42688-P", "ICM-42688-P", "lcsc:LGA-14_L3.0-W2.5-P0.50-TL", S,
    {1: "SPI1_MISO", 2: "GND", 3: "GND", 4: "IMU_INT", 5: "3V3_SENS", 6: "GND", 7: "GND", 8: "3V3_SENS",
     9: "GND", 10: "GND", 11: "GND", 12: "CS_IMU", 13: "SPI1_SCK", 14: "SPI1_MOSI"}, lcsc="C1850418",
    descr="IMU auf der Rollachse; RESV und FSYNC an GND (DS-000347 Tab. 9)")
C("100n", "3V3_SENS", "GND", S, descr="VDD")
C("2.2u", "3V3_SENS", "GND", S, descr="VDD")
C("10n", "3V3_SENS", "GND", S, descr="VDDIO")
group("Barometer BMP390, SPI1")
# E3 / B6: 4-wire SPI (SDO = MISO, SDI = MOSI, CSB from the decoder). U15 is the second barometer (C2), DNP.
for ref, cs, dnp in (("U5", "CS_BARO", False), ("U15", "CS_BARO2", True)):
    add(ref, "lcsc:BMP390_C5124834", "BMP390", "lcsc:LGA-10_L2.0-W2.0-P0.50-BL", S,
        {1: "3V3_SENS", 2: "SPI1_SCK", 3: "GND", 4: "SPI1_MOSI", 5: "SPI1_MISO", 6: cs, 7: None, 8: "GND",
         9: "GND", 10: "3V3_SENS"},
        lcsc="C5124834", dnp=dnp, descr="SPI 4-Draht; Rueckfall BMP388 C779278, pinkompatibel"
        + (" - zweites Barometer, DNP (C2)" if dnp else ""))
    C("100n", "3V3_SENS", "GND", S, descr="VDD", dnp=dnp)
    C("100n", "3V3_SENS", "GND", S, descr="VDDIO", dnp=dnp)
group("Qwiic, I2C")
R("4.7k", "3V3", "SDA", S)
R("4.7k", "3V3", "SCL", S)
add("J12", "Connector_Generic:Conn_01x04", "J_QWIIC", JST + "JST_SH_BM04B-SRSS-TB_1x04-1MP_P1.00mm_Vertical", S,
    {1: "GND", 2: "3V3", 3: "SDA", 4: "SCL"}, func="J_QWIIC", descr="Qwiic-Belegung; nur Zubehoer (E3)")
# ================================================================ Funk (spec 6)
S = "radio"
group("LoRa E22-400T22S, Serial8")
add("U10", "lcsc:E22-400T22S_C2903765", "E22-400T22S", "lcsc:WIRELM-SMD_E22-400T22S_1", S,
    {1: "LORA_NRST", 2: "GND", 3: None, 4: None, 5: None, 6: None, 7: None, 8: "GND", 11: "GND", 12: None,
     13: "GND", 14: "GND", 15: "GND", 16: "GND", 19: "GND", 20: "LORA_M0", 21: "LORA_M1", 22: "LORA_RXD",
     23: "LORA_TXD", 24: "LORA_AUX", 25: "3V3_RF", 26: "GND"}, lcsc="C2903765",
    descr="Antenne ueber die IPEX-Buchse des Moduls, ANT-Pad offen; NRST an Teensy 6 (B9)")
R("10k", "3V3_RF", "LORA_NRST", S, descr="NRST hoch; Teensy zieht im Open-Drain-Betrieb")
C("10u", "3V3_RF", "GND", S, fp=C0805)
C("100n", "3V3_RF", "GND", S)
group("GPS, Serial1")
add("J11", "Connector_Generic:Conn_01x04", "J_GPS", JST + "JST_GH_BM04B-GHS-TBT_1x04-1MP_P1.25mm_Vertical", S,
    {1: "3V3_RF", 2: "GND", 3: "GPS_TX", 4: "GPS_RX"}, func="J_GPS",
    descr="u-blox-Modul in der Spitze: 3V3_RF, GND, TX (vom GPS), RX (zum GPS)")

# ================================================================ Aktoren (spec 3, 7, E4, E5, E9)
S = "actuators"
group("Servos")
# E4: every servo connector on VSERVO (2S direct); J16 is the fourth (landing legs, E5)
for ref, func, sig, fp in [("J5", "J_SERVO1", "SERVO_YAW", XH3_SIDE), ("J6", "J_SERVO2", "SERVO_PITCH", XH3_SIDE),
                           ("J7", "J_SERVO3", "SERVO_CHUTE", XH3_TOP), ("J16", "J_SERVO4", "SERVO_LEGS", XH3_TOP)]:
    R("220", sig, sig + "_S", S, descr="Schutzwiderstand Servo-Signal")
    add(ref, "Connector_Generic:Conn_01x03", func, fp, S, {1: sig + "_S", 2: "VSERVO", 3: "GND_PWR"},
        func=func, descr="S / + / -, VSERVO")
group("Rollmotor DRV8833")
# E9: motor driver straight on VSERVO (DRV8833: 2.7-10.8 V); the firmware limits the PWM duty
# (ROLL_PWM_MAX about 60 %). nSLEEP from Teensy 11 (C1): the internal pull-down keeps it asleep at boot.
add("U7", "Driver_Motor:DRV8833PWP", "DRV8833PWPR",
    "Package_SO:HTSSOP-16-1EP_4.4x5mm_P0.65mm_EP3.4x5mm_Mask2.46x2.31mm_ThermalVias", S,
    {1: "MOT_NSLEEP", 2: "MOT_A", 3: "GND_PWR", 4: "MOT_B", 5: "MOT_B", 6: "GND_PWR", 7: "MOT_A", 8: "MOT_FAULT",
     9: "MOT_IN1", 10: "MOT_IN2", 11: "U7_VCP", 12: "VSERVO", 13: "GND_PWR", 14: "U7_VINT", 15: "MOT_IN2",
     16: "MOT_IN1", 17: "GND_PWR"}, lcsc="C50506", descr="beide Bruecken parallel, 2x 1,5 A")
R("10k", "3V3", "MOT_FAULT", S, descr="nFAULT -> Teensy Pin 8")
C("10u/25V", "VSERVO", "GND_PWR", S, fp=C0805)
C("100n", "VSERVO", "GND_PWR", S)
C("10n", "U7_VCP", "VSERVO", S)
C("2.2u", "U7_VINT", "GND_PWR", S)
add("J8", "Connector_Generic:Conn_01x02", "J_MOT", XH2_TOP, S,
    {1: "MOT_A", 2: "MOT_B"}, func="J_MOT", descr="Rollmotor, XH wegen Blockierstrom (A3)")

# ================================================================ Pyro (spec 5, A3, A4, E5)
S = "pyro"
group("Arming")
add("J4", "Connector_Generic:Conn_01x02", "J_ARM", XH2_TOP, S,
    {1: "VBAT_PROT", 2: "VBAT_ARMED"}, func="J_ARM", descr="Schluesselschalter >= 5 A, JST-XH (A3)")
divider("VBAT_ARMED", "ARM_SENSE", S, low_group="Messteiler am Analogmux")
PYRO = [  # channel, connector, FET, TVS, populated
    (1, "J9", "Q3", "D2", True), (2, "J10", "Q4", "D3", True),
    (3, "J19", "Q8", "D5", False), (4, "J20", "Q9", "D6", False),
]
for ch, jref, qref, dref, fit in PYRO:
    neg, gate = f"PYRO{ch}_NEG", f"PYRO{ch}_G"
    group(f"Pyro-Kanal {ch}")
    note = "" if fit else ", DNP (E5)"
    add(jref, "Connector_Generic:Conn_01x02", f"J_PYRO{ch}", XH2_SIDE, S,
        {1: "VBAT_ARMED", 2: neg}, func=f"J_PYRO{ch}", dnp=not fit, descr="E-Match, 1 = Plus (VBAT_ARMED)" + note)
    add(qref, "Transistor_FET:AO3400A", "AO3400A", SOT23, S, {1: gate, 2: "GND_PWR", 3: neg}, lcsc="C20917",
        dnp=not fit, descr=f"Pyro {ch} low-side; Puls 50-100 ms (A4)" + note)
    R("100", f"PYRO{ch}_FIRE", gate, S)
    R("100k", gate, "GND_PWR", S, descr="haelt den FET beim Booten aus")
    add(dref, "Device:D_TVS", "SMAJ12CA", "Diode_SMD:D_SMA", S, {1: "VBAT_ARMED", 2: neg}, dnp=not fit,
        descr="TVS ueber dem Ausgang (bidirektional, 400 W; SMA statt SMB aus Platzgruenden)" + note)
    divider(neg, f"PYRO{ch}_SENSE", S, low_group="Messteiler am Analogmux",
            descr="Durchgangspruefung, ueber den Analogmux")

# ================================================================ Signal (spec 4: LEDs, Summer, Kamera)
S = "signal"
group("Status-LEDs")
# B8: one chain LED1 -> LED2 -> J_LED behind one level shifter
add("U8", "Logic_LevelTranslator:SN74LV1T34DBV", "SN74LV1T34DBVR", SOT235, S,
    {1: None, 2: "LED_DATA", 3: "GND", 4: "LED_5V", 5: "5V_SYS"}, descr="Pegel 3,3 -> 5 V (B8)")
C("100n", "5V_SYS", "GND", S)
R("330", "LED_5V", "LED1_DIN", S)
add("LED1", "LED:WS2812B-2020", "WS2812B-2020", "LED_SMD:LED_WS2812B-2020_PLCC4_2.0x2.0mm", S,
    {1: "LED2_DIN", 2: "GND", 3: "LED1_DIN", 4: "5V_SYS"}, lcsc="C965555")
C("100n", "5V_SYS", "GND", S)
add("LED2", "LED:WS2812B-2020", "WS2812B-2020", "LED_SMD:LED_WS2812B-2020_PLCC4_2.0x2.0mm", S,
    {1: "LED_EXT_DATA", 2: "GND", 3: "LED2_DIN", 4: "5V_SYS"}, lcsc="C965555")
C("100n", "5V_SYS", "GND", S)
add("J14", "Connector_Generic:Conn_01x03", "J_LED", JST + "JST_GH_BM03B-GHS-TBT_1x03-1MP_P1.25mm_Vertical", S,
    {1: "5V_SYS", 2: "LED_EXT_DATA", 3: "GND"}, func="J_LED", descr="externe WS2812B, Kette hinter LED2")
group("Summer")
add("BZ1", "Device:Buzzer", "aktiv 5V 12mm", "Buzzer_Beeper:Buzzer_12x9.5RM7.6", S, {1: "5V_SYS", 2: "BZ_NEG"},
    descr="aktiver Summer, THT")
add("D4", "Device:D", "1N4148W", "Diode_SMD:D_SOD-123", S, {1: "5V_SYS", 2: "BZ_NEG"}, lcsc="C81598")
add("Q5", "Transistor_FET:AO3400A", "AO3400A", SOT23, S, {1: "BZ_G", 2: "GND", 3: "BZ_NEG"}, lcsc="C20917",
    descr="Summer, Teensy 37 (B7)")
R("100", "BUZZER", "BZ_G", S)
R("100k", "BZ_G", "GND", S)
group("Kamera")
R("1k", "CAM_TRIG", "CAM_TRIG_OUT", S)
add("J13", "Connector_Generic:Conn_01x03", "J_CAM", JST + "JST_GH_BM03B-GHS-TBT_1x03-1MP_P1.25mm_Vertical", S,
    {1: "5V_SYS", 2: "CAM_TRIG_OUT", 3: "GND"}, func="J_CAM", descr="Kamera-Ausloeser (3,3-V-Pegel ueber 1 k)")

# ---------------------------------------------------------------- power flags for ERC
# Nets fed only through connectors, fuses or diodes carry a PWR_FLAG so ERC knows they are driven.
PWR_FLAGS = {"power": ["GND", "GND_PWR", "VSYS_IN", "TEENSY_VIN", "VSERVO", "VBUS_CHG", "3V3_SENS"],
             "actuators": ["U7_VINT"]}   # DRV8833 VINT is its own regulator output, typed power_in in the library

# ERC findings that are intended, written into the project as exclusions with the reason.
# Items are (ref, pin); "#FLG:<net>" names the power flag of that net.
ERC_EXCLUSIONS = [
    ("pin_to_pin", ("U7", "2"), ("U7", "7"), "DRV8833: Bruecken A und B bewusst parallel (Datenblatt 8.3.6)"),
    ("pin_to_pin", ("U7", "4"), ("U7", "5"), "DRV8833: Bruecken A und B bewusst parallel (Datenblatt 8.3.6)"),
    ("pin_to_pin", ("U7", "3"), ("#FLG:GND_PWR", "1"), "AISEN ohne Strommessung direkt an GND_PWR"),
    ("pin_to_pin", ("U7", "6"), ("#FLG:GND_PWR", "1"), "BISEN ohne Strommessung direkt an GND_PWR"),
]

# ---------------------------------------------------------------- net classes (spec 8, review B12, A6-A8)
NETCLASSES = {
    # name: (track width, clearance, via diameter, via drill, nets)
    # 2S path, servo rail, pyro: up to 3 A continuous, 5 A for 20 ms. 1.0 mm outer copper carries
    # about 2.4 A at 10 K (IPC-2221); the main runs are F.Cu zones drawn by gen_pcb.py (B13), this
    # width applies to the stubs the router adds. Freerouting keeps this class off In2 (A6).
    "Strom": (1.0, 0.2, 0.8, 0.4, ["VBAT2_RAW", "VBAT2_REV", "VBAT2_F", "VBAT_PROT", "VSERVO", "VBAT_ARMED",
                                   "PYRO1_NEG", "PYRO2_NEG", "PYRO3_NEG", "PYRO4_NEG"]),
    "Rueckstrom": (0.8, 0.2, 0.8, 0.4, ["GND_PWR"]),
    # 1S input (A7: >= 0.6 mm), 5 V and 3.3 V rails, motor outputs
    "Versorgung": (0.6, 0.2, 0.6, 0.3, ["VBAT1_RAW", "VBAT1_REV", "VBAT1_F", "VSYS_IN", "5V_SYS", "3V3_RF",
                                        "3V3_EXP", "TEENSY_VIN", "MOT_A", "MOT_B", "VBUS_CHG"]),
    # inductor nets of the TPS63070 (VQFN, 0.5 mm pitch): short, the pads are wide (A7)
    "Wandler": (0.4, 0.15, 0.6, 0.3, ["U2_L1", "U2_L2"]),
    # GND and 3V3 stay in the default class: GND rides on the planes, 3V3 carries sensor currents only
}


def nets():
    """net name -> list of (ref, pin)."""
    out = {}
    for p in PARTS:
        for pin, net in p.pins.items():
            if net:
                out.setdefault(net, []).append((p.ref, pin))
    for sheet, flags in PWR_FLAGS.items():
        for net in flags:
            out.setdefault(net, []).append(("#FLG", "1"))
    return out


def check():
    refs = [p.ref for p in PARTS]
    assert len(refs) == len(set(refs)), "duplicate references"
    single = [n for n, c in nets().items() if len(c) < 2]
    assert not single, f"nets with only one connection: {single}"
    used = set(TEENSY)
    assert not used & set(SPARE_PINS)
    assert used | set(SPARE_PINS) == {str(i) for i in range(42)}, "every Teensy pin 0..41 has a role"


# ================================================================ Sensoren vom 23.10. (am Ende: die Nummern der Kondensatoren bleiben)
# All three on the I2C pair and on 3V3 (not 3V3_SENS): they sit at the tip, 45 mm from the sensor island,
# and none of them is in the flight path.
S = "sensors"
group("Magnetometer LIS3MDL, I2C (23.10.)")
# On the board the field is bent by the servo and motor currents; for the ground, quiet phases and later
# vehicles. Pins 2 and 12 reserved -> GND, C1 100 nF (DocID024204 Tab. 2); CS high = I2C, SA1 high -> 0x1E.
add("U16", "lcsc:LIS3MDLTR", "LIS3MDL", "lcsc:LGA-12_L2.0-W2.0-P0.50-BL", S,
    {1: "SCL", 2: "GND", 3: "GND", 4: "MAG_C1", 5: "3V3", 6: "3V3", 7: None, 8: None,
     9: "3V3", 10: "3V3", 11: "SDA", 12: "GND"}, lcsc="C478483",
    descr="3-Achsen-Magnetometer an I2C, Adresse 0x1E (SA1 hoch), CS hoch = I2C; Reserved an GND; im Flug gestoert")
C("100n", "3V3", "GND", S, descr="Vdd")
C("100n", "MAG_C1", "GND", S, descr="C1")
group("Feuchte und Temperatur SHT40, I2C (23.10.)")
add("U18", "lcsc:SHT40-AD1B-R3", "SHT40-AD1B", "lcsc:DFN-4_L1.5-W1.5-P0.8-TL-EP", S,
    {1: "SDA", 2: "SCL", 3: "3V3", 4: "GND", 5: None}, lcsc="C2848306",
    descr="Feuchte und Temperatur an I2C, Adresse 0x44; Die-Pad frei (Sensirion: nicht loeten)")
C("100n", "3V3", "GND", S, descr="VDD")
group("Hochbeschleunigung ADXL375, I2C, DNP (23.10.)")
# +-200 g for stronger motors and hard landings. I2C (CS high, ALT ADDRESS low -> 0x53): SPI1 stays the
# flight bus under the Teensy, and the tip is only reachable by the I2C pair. Reserved pins 3 and 11 to
# GND (datasheet: GND or open). Footprint only for now.
add("U17", "lcsc:ADXL375BCCZ", "ADXL375", "lcsc:LGA-14_L5.0-W3.0-P0.80-BL-1", S,
    {1: "3V3", 2: "GND", 3: "GND", 4: "GND", 5: "GND", 6: "3V3", 7: "3V3", 8: None, 9: None,
     10: None, 11: "GND", 12: "GND", 13: "SDA", 14: "SCL"}, lcsc="C579466", dnp=True,
    descr="Hochbeschleunigung +-200 g an I2C, Adresse 0x53 (CS hoch, ALT ADDRESS tief) - DNP, Footprint fuer spaetere Fluege")
C("1u", "3V3", "GND", S, descr="VS", dnp=True)
C("100n", "3V3", "GND", S, descr="VDD I/O", dnp=True)

check()

if __name__ == "__main__":
    n = nets()
    print(f"{len(PARTS)} parts ({sum(p.dnp for p in PARTS)} DNP), {len(n)} nets")
    for s, title, _ in SHEETS:
        print(f"  {title:12s} {sum(p.sheet == s for p in PARTS):3d} parts")
