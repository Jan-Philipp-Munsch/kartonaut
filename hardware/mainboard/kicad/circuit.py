"""The circuit of mainboard rev B as data: parts, values, footprints, nets.

Single source for the schematic (gen_schematic.py), the board (gen_pcb.py) and the checks
(check_design.py). Everything here follows hardware/mainboard/README.md (rev B); where this file
had to decide something the spec leaves open, the comment says so and README.md §12 lists it.

Net names follow the spec. GND is the logic ground (1S minus, Teensy, sensors); GND_PWR is the
return of everything fed from the 2S pack (servos, buck, motor driver, pyro). They meet in exactly
one point, the net tie NT1 next to the 2S minus at J1 (spec §3: star point).
"""
from dataclasses import dataclass, field

from build_lib import teensy_pad

SHEETS = [  # (file stem, sheet title, page title shown on the sheet)
    ("power", "Versorgung", "Versorgung: 1S-Pfad (Elektronik) und 2S-Pfad (Aktoren, Pyro)"),
    ("mcu", "Teensy", "Teensy 4.1 auf Buchsenleisten, Erweiterungsleiste, Befestigung"),
    ("sensors", "Sensorik", "IMU ICM-42688-P an SPI1, Barometer BMP390 und Qwiic an I2C"),
    ("radio", "Funk", "LoRa E22-400T22S an Serial8, GPS an Serial1"),
    ("actuators", "Aktoren", "TVC-Servos am 2S-Akku, Fallschirm-Servo, Rollmotor DRV8833"),
    ("pyro", "Pyro", "Zwei Pyro-Kanaele low-side, Arming, Durchgangspruefung"),
    ("signal", "Signal", "WS2812B mit Pegelwandler, Summer, Kamera-Trigger"),
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
L5040 = "Inductor_SMD:L_Changjiang_FNR5040S"
SOT23 = "Package_TO_SOT_SMD:SOT-23"
SOT235 = "Package_TO_SOT_SMD:SOT-23-5"
TP = "TestPoint:TestPoint_Pad_D1.5mm"
SJ = "Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm"
JST = "Connector_JST:"

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


# ================================================================ Versorgung (spec §3)
S = "power"
group("2S: Akku, Verpolschutz, Hauptschalter")
# 2S path: XT30 -> reverse protection -> main switch pole b -> VBAT_PROT -> shunt -> VBAT_MEAS
add("J1", "Connector_Generic:Conn_01x02", "XT30PW-M", "Connector_AMASS:AMASS_XT30PW-M_1x02_P2.50mm_Horizontal", S,
    {1: "VBAT2_RAW", 2: "GND_PWR"}, func="J_BAT2", descr="2S-LiPo 6,0-8,4 V, Pin 1 = Plus")
add("Q1", "Transistor_FET:AO3401A", "AO3401A", SOT23, S, {1: "Q1_G", 2: "VBAT2_REV", 3: "VBAT2_RAW"},
    lcsc="C15127", descr="Verpolschutz 2S")
R("10k", "Q1_G", "GND_PWR", S)
add("J3", "Connector_Generic:Conn_01x04", "J_SW", JST + "JST_PH_B4B-PH-K_1x04_P2.00mm_Vertical", S,
    {1: "VBAT1_PROT", 2: "VSYS_IN", 3: "VBAT2_REV", 4: "VBAT_PROT"}, func="J_SW",
    descr="zweipoliger Hauptschalter: 1-2 schaltet den 1S-Pfad, 3-4 den 2S-Pfad")
add("JP1", "Jumper:SolderJumper_2_Open", "SJ 1S", SJ, S, {1: "VBAT1_PROT", 2: "VSYS_IN"},
    descr="ueberbrueckt SW1a auf dem Tisch")
add("JP2", "Jumper:SolderJumper_2_Open", "SJ 2S", SJ, S, {1: "VBAT2_REV", 2: "VBAT_PROT"},
    descr="ueberbrueckt SW1b auf dem Tisch")
group("2S: Spannungsmessung und Strommessung INA219")
R("100k", "VBAT_PROT", "VBAT2_SENSE", S)
R("33k", "VBAT2_SENSE", "GND", S)
C("100n", "VBAT2_SENSE", "GND", S)
add("R_SH1", "Device:R", "20m 1% 1W", "Resistor_SMD:R_2512_6332Metric", S, {1: "VBAT_PROT", 2: "VBAT_MEAS"},
    func="R_SHUNT", descr="Shunt 2S-Pfad, Kelvin-Abgriff zum INA219")
add("U6", "Sensor_Energy:INA219AxD", "INA219AIDR", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", S,
    {1: "GND", 2: "GND", 3: "SDA", 4: "SCL", 5: "3V3", 6: "GND", 7: "VBAT_MEAS", 8: "VBAT_PROT"},
    lcsc="C138706", descr="Strom/Spannung 2S, I2C 0x40")
C("100n", "3V3", "GND", S)
group("2S: Servo-Schiene VSERVO")
add("F1", "Device:Polyfuse", "3A hold", "Fuse:Fuse_1812_4532Metric", S, {1: "VBAT_MEAS", 2: "VSERVO"},
    descr="Polyfuse Servo-Schiene, 1812, 3 A Halte-, 6 A Ausloesestrom")
CP("1000u/16V low-ESR", "VSERVO", "GND_PWR", S, "Capacitor_THT:CP_Radial_D10.0mm_P5.00mm",
   descr="Puffer VSERVO, stehend <= 12,5 mm")
C("10u/25V", "VSERVO", "GND_PWR", S, fp=C0805)
group("2S: Buck U1 -> 5V_SERVO")
# U1 TPS563201: 5V_SERVO (3 A) from the 2S pack. Vout = 0.768 V (1 + 56k/10k) = 5.07 V
add("U1", "Regulator_Switching:TPS563201", "TPS563201DDCR", "Package_TO_SOT_SMD:SOT-23-6", S,
    {1: "GND_PWR", 2: "U1_SW", 3: "VBAT_MEAS", 4: "U1_FB", 5: "U1_EN", 6: "U1_BST"}, lcsc="C116592",
    descr="Buck 5V_SERVO, 3 A")
R("100k", "VBAT_MEAS", "U1_EN", S)
C("10u/25V", "VBAT_MEAS", "GND_PWR", S, fp=C0805)
C("10u/25V", "VBAT_MEAS", "GND_PWR", S, fp=C0805)
C("100n", "VBAT_MEAS", "GND_PWR", S)
C("100n", "U1_BST", "U1_SW", S)
add("L1", "Device:L", "2.2u Isat>=4A", L5040, S, {1: "U1_SW", 2: "5V_SERVO"}, descr="5040, Isat >= 4 A")
R("56k", "5V_SERVO", "U1_FB", S)
R("10k", "U1_FB", "GND_PWR", S)
C("22u/10V", "5V_SERVO", "GND_PWR", S, fp=C0805)
C("22u/10V", "5V_SERVO", "GND_PWR", S, fp=C0805)
CP("470u/10V", "5V_SERVO", "GND_PWR", S, "Capacitor_THT:CP_Radial_D8.0mm_P3.50mm", descr="Puffer 5V_SERVO")
group("1S: Akku, Verpolschutz, Spannungsmessung")
# 1S path: JST-PH -> reverse protection -> main switch pole a -> VSYS_IN
add("J2", "Connector_Generic:Conn_01x02", "J_BAT1", JST + "JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical", S,
    {1: "VBAT1_RAW", 2: "GND"}, func="J_BAT1", descr="1S-LiPo 3,0-4,2 V, Pin 1 = Plus")
add("Q2", "Transistor_FET:AO3401A", "AO3401A", SOT23, S, {1: "Q2_G", 2: "VBAT1_PROT", 3: "VBAT1_RAW"},
    lcsc="C15127", descr="Verpolschutz 1S")
R("10k", "Q2_G", "GND", S)
R("100k", "VSYS_IN", "VBAT1_SENSE", S)
R("33k", "VBAT1_SENSE", "GND", S)
C("100n", "VBAT1_SENSE", "GND", S)
group("1S: Buck-Boost U2 -> 5V_SYS, Teensy-VIN")
# U2 TPS63070 buck-boost: 5V_SYS from 1S. Vout = 0.8 V (1 + 680k/130k) = 4.98 V (TI table 4).
# EN divider 330k/100k: on above 3.44 V, off below 3.01 V (EN 0.8/0.7 V) - protects the 1S cell.
add("U2", "lcsc:TPS63070RNMR", "TPS63070RNMR", "lcsc:VQFN-15_L3.0-W2.5-P0.50-BL", S,
    {1: "VSYS_IN", 2: None, 3: "U2_VAUX", 4: "GND", 5: "U2_FB", 6: "GND", 7: "5V_SYS", 9: "U2_L2",
     10: "GND", 11: "U2_L1", 12: "VSYS_IN", 14: "U2_EN", 15: "GND"}, lcsc="C109322",
    descr="Buck-Boost 5V_SYS aus 1S, 2-16 V ein; PS/SYNC hoch = Stromsparbetrieb bei Teillast")
C("10u/25V", "VSYS_IN", "GND", S, fp=C0805)
C("10u/25V", "VSYS_IN", "GND", S, fp=C0805)
C("100n", "U2_VAUX", "GND", S)
add("L2", "Device:L", "1.5u Isat>=4A", L5040, S, {1: "U2_L1", 2: "U2_L2"}, descr="5040, Isat >= 4 A")
R("680k", "5V_SYS", "U2_FB", S)
R("130k", "U2_FB", "GND", S)
R("330k", "VSYS_IN", "U2_EN", S)
R("100k", "U2_EN", "GND", S)
for _ in range(3):
    C("22u/10V", "5V_SYS", "GND", S, fp=C0805)
CP("1000u/10V polymer", "5V_SYS", "GND", S, "Capacitor_THT:CP_Radial_D8.0mm_P3.50mm",
   descr="Puffer 5V_SYS (Polymer, <= 12 mm hoch)")
add("D1", "Diode:SS14", "SS14", "Diode_SMD:D_SMA", S, {1: "TEENSY_VIN", 2: "5V_SYS"}, lcsc="C2480",
    descr="5V_SYS -> Teensy VIN, USB darf gleichzeitig stecken")
group("LDO U3 -> 3V3_RF, Sternpunkt, Testpunkte")
# U3 AP2112K-3.3: 3V3_RF for LoRa and GPS
add("U3", "Regulator_Linear:AP2112K-3.3", "AP2112K-3.3TRG1", SOT235, S,
    {1: "5V_SYS", 2: "GND", 3: "5V_SYS", 4: None, 5: "3V3_RF"}, lcsc="C51118", descr="LDO 3V3_RF, 600 mA")
C("1u", "5V_SYS", "GND", S)
C("1u", "3V3_RF", "GND", S)
C("100u/6.3V", "3V3_RF", "GND", S, fp=C1210, descr="Puffer fuer den LoRa-Sendepuls")
add("NT1", "Device:NetTie_2", "NetTie", "NetTie:NetTie-2_SMD_Pad2.0mm", S, {1: "GND_PWR", 2: "GND"},
    descr="Sternpunkt: einzige Verbindung der beiden Massen, direkt am 2S-Minus")
for net in ["VBAT_PROT", "VSYS_IN", "5V_SYS", "VSERVO", "5V_SERVO", "3V3_RF", "GND"]:
    testpoint(net, S)

# ================================================================ Teensy (spec §4)
S = "mcu"
group("Teensy 4.1")
TEENSY = {  # Teensy pin -> net
    "0": "GPS_TX", "1": "GPS_RX", "2": "MOT_IN1", "3": "MOT_IN2", "4": "IMU_INT", "5": "LED1_DATA",
    "6": "LED2_DATA", "7": "CAM_TRIG", "8": "MOT_FAULT", "9": "SERVO_CHUTE", "13": "BUZZER",
    "18": "SDA", "19": "SCL", "20": "PYRO1_SENSE", "21": "PYRO2_SENSE", "22": "PYRO2_FIRE",
    "23": "PYRO1_FIRE", "24": "ARM_SENSE", "26": "IMU_MOSI", "27": "IMU_SCK", "28": "SERVO_YAW",
    "29": "SERVO_PITCH", "32": "LORA_M1", "33": "LORA_M0", "34": "LORA_TXD", "35": "LORA_RXD",
    "36": "LORA_AUX", "38": "IMU_CS", "39": "IMU_MISO", "40": "VBAT2_SENSE", "41": "VBAT1_SENSE",
}
EXP_PINS = ["10", "11", "12", "14", "15", "16", "17", "25", "30", "31", "37"]
for p in EXP_PINS:
    TEENSY[p] = f"EXP_D{p}"
_tp = {teensy_pad(k): v for k, v in TEENSY.items()}
for num, name in __import__("build_lib").TEENSY_PINS.items():
    if name == "GND":
        _tp[str(num)] = "GND"
    elif name == "3V3":
        _tp[str(num)] = "3V3"
    elif name == "VIN":
        _tp[str(num)] = "TEENSY_VIN"
add("A1", "mainboard:Teensy4.1_Socket", "Teensy 4.1", "mainboard:Teensy41_Socket", S, _tp, func="U_TEENSY",
    descr="2x Buchsenleiste 1x24, 2,54 mm, 8,5 mm hoch (THT, selbst loeten)")
group("Erweiterung, Befestigung, Testpunkte")
exp = {1: "3V3", 2: "GND", 14: "5V_SYS"}
for i, p in enumerate(EXP_PINS):
    exp[3 + i] = f"EXP_D{p}"
add("J15", "Connector_Generic:Conn_02x07_Odd_Even", "J_EXP", "Connector_PinHeader_2.54mm:PinHeader_2x07_P2.54mm_Vertical",
    S, exp, func="J_EXP", descr="freie Teensy-Pins 10, 11, 12, 14-17, 25, 30, 31, 37")
for i in range(1, 5):
    add(f"H{i}", "Mechanical:MountingHole", "M3", "MountingHole:MountingHole_3.2mm_M3", S, {},
        descr="M3 zum gedruckten Traeger")
testpoint("SDA", S)
testpoint("SCL", S)

# ================================================================ Sensorik (spec §6)
S = "sensors"
group("IMU ICM-42688-P, SPI1")
add("U4", "lcsc:ICM-42688-P", "ICM-42688-P", "lcsc:LGA-14_L3.0-W2.5-P0.50-TL", S,
    {1: "IMU_MISO", 2: "GND", 3: "GND", 4: "IMU_INT", 5: "3V3", 6: "GND", 7: "GND", 8: "3V3",
     9: "GND", 10: "GND", 11: "GND", 12: "IMU_CS", 13: "IMU_SCK", 14: "IMU_MOSI"}, lcsc="C1850418",
    descr="IMU auf der Rollachse; RESV und FSYNC an GND (DS-000347 Tab. 9)")
C("100n", "3V3", "GND", S, descr="VDD")
C("2.2u", "3V3", "GND", S, descr="VDD")
C("10n", "3V3", "GND", S, descr="VDDIO")
R("10k", "3V3", "IMU_CS", S, descr="CS hoch waehrend des Boots")
group("Barometer BMP390 und I2C")
add("U5", "lcsc:BMP390_C5124834", "BMP390", "lcsc:LGA-10_L2.0-W2.0-P0.50-BL", S,
    {1: "3V3", 2: "SCL", 3: "GND", 4: "SDA", 5: "3V3", 6: "3V3", 7: None, 8: "GND", 9: "GND", 10: "3V3"},
    lcsc="C5124834", descr="I2C 0x77 (SDO an VDDIO); Rueckfall BMP388 C779278, pinkompatibel")
C("100n", "3V3", "GND", S, descr="VDD")
C("100n", "3V3", "GND", S, descr="VDDIO")
R("4.7k", "3V3", "SDA", S)
R("4.7k", "3V3", "SCL", S)
add("J12", "Connector_Generic:Conn_01x04", "J_QWIIC", JST + "JST_SH_BM04B-SRSS-TB_1x04-1MP_P1.00mm_Vertical", S,
    {1: "GND", 2: "3V3", 3: "SDA", 4: "SCL"}, func="J_QWIIC", descr="Qwiic-Belegung")

# ================================================================ Funk (spec §6)
S = "radio"
group("LoRa E22-400T22S, Serial8")
add("U10", "lcsc:E22-400T22S_C2903765", "E22-400T22S", "lcsc:WIRELM-SMD_E22-400T22S_1", S,
    {1: None, 2: "GND", 3: None, 4: None, 5: None, 6: None, 7: None, 8: "GND", 11: "GND", 12: None,
     13: "GND", 14: "GND", 15: "GND", 16: "GND", 19: "GND", 20: "LORA_M0", 21: "LORA_M1", 22: "LORA_RXD",
     23: "LORA_TXD", 24: "LORA_AUX", 25: "3V3_RF", 26: "GND"}, lcsc="C2903765",
    descr="Antenne ueber die IPEX-Buchse des Moduls, ANT-Pad offen")
C("10u", "3V3_RF", "GND", S, fp=C0805)
C("100n", "3V3_RF", "GND", S)
group("GPS, Serial1")
add("J11", "Connector_Generic:Conn_01x04", "J_GPS", JST + "JST_GH_BM04B-GHS-TBT_1x04-1MP_P1.25mm_Vertical", S,
    {1: "3V3_RF", 2: "GND", 3: "GPS_TX", 4: "GPS_RX"}, func="J_GPS",
    descr="u-blox-Modul in der Spitze: 3V3_RF, GND, TX (vom GPS), RX (zum GPS)")

# ================================================================ Aktoren (spec §3, §7)
S = "actuators"
group("Servos")
for ref, func, sig, rail, pin in [("J5", "J_SERVO1", "SERVO_YAW", "VSERVO", "JST_XH_S3B-XH-A_1x03_P2.50mm_Horizontal"),
                                  ("J6", "J_SERVO2", "SERVO_PITCH", "VSERVO", "JST_XH_S3B-XH-A_1x03_P2.50mm_Horizontal"),
                                  ("J7", "J_SERVO3", "SERVO_CHUTE", "5V_SERVO", "JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical")]:
    R("220", sig, sig + "_S", S, descr="Schutzwiderstand Servo-Signal")
    add(ref, "Connector_Generic:Conn_01x03", func, JST + pin, S, {1: sig + "_S", 2: rail, 3: "GND_PWR"},
        func=func, descr=f"S / + / -, {rail}")
group("Rollmotor DRV8833")
add("U7", "Driver_Motor:DRV8833PWP", "DRV8833PWPR",
    "Package_SO:HTSSOP-16-1EP_4.4x5mm_P0.65mm_EP3.4x5mm_Mask2.46x2.31mm_ThermalVias", S,
    {1: "U7_SLEEP", 2: "MOT_A", 3: "GND_PWR", 4: "MOT_B", 5: "MOT_B", 6: "GND_PWR", 7: "MOT_A", 8: "MOT_FAULT",
     9: "MOT_IN1", 10: "MOT_IN2", 11: "U7_VCP", 12: "5V_SERVO", 13: "GND_PWR", 14: "U7_VINT", 15: "MOT_IN2",
     16: "MOT_IN1", 17: "GND_PWR"}, lcsc="C50506", descr="beide Bruecken parallel, 2x 1,5 A")
R("10k", "5V_SERVO", "U7_SLEEP", S)
R("10k", "3V3", "MOT_FAULT", S, descr="nFAULT -> Teensy Pin 8")
C("10u/25V", "5V_SERVO", "GND_PWR", S, fp=C0805)
C("100n", "5V_SERVO", "GND_PWR", S)
C("10n", "U7_VCP", "5V_SERVO", S)
C("2.2u", "U7_VINT", "GND_PWR", S)
add("J8", "Connector_Generic:Conn_01x02", "J_MOT", JST + "JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical", S,
    {1: "MOT_A", 2: "MOT_B"}, func="J_MOT", descr="Rollmotor")

# ================================================================ Pyro (spec §5)
S = "pyro"
group("Arming")
add("J4", "Connector_Generic:Conn_01x02", "J_ARM", JST + "JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal", S,
    {1: "VBAT_PROT", 2: "VBAT_ARMED"}, func="J_ARM", descr="externer Arming-Schalter")
R("100k", "VBAT_ARMED", "ARM_SENSE", S)
R("33k", "ARM_SENSE", "GND", S)
C("100n", "ARM_SENSE", "GND", S)
for ch, (jref, qref, dref) in enumerate([("J9", "Q3", "D2"), ("J10", "Q4", "D3")], start=1):
    neg, gate = f"PYRO{ch}_NEG", f"PYRO{ch}_G"
    group(f"Pyro-Kanal {ch}")
    add(jref, "Connector_Generic:Conn_01x02", f"J_PYRO{ch}", JST + "JST_XH_S2B-XH-A_1x02_P2.50mm_Horizontal", S,
        {1: "VBAT_ARMED", 2: neg}, func=f"J_PYRO{ch}", descr="E-Match, 1 = Plus (VBAT_ARMED)")
    add(qref, "Transistor_FET:AO3400A", "AO3400A", SOT23, S, {1: gate, 2: "GND_PWR", 3: neg}, lcsc="C20917",
        descr=f"Pyro {ch} low-side")
    R("100", f"PYRO{ch}_FIRE", gate, S)
    R("100k", gate, "GND_PWR", S, descr="haelt den FET beim Booten aus")
    add(dref, "Device:D_TVS", "SMBJ12CA", "Diode_SMD:D_SMB", S, {1: "VBAT_ARMED", 2: neg},
        descr="TVS ueber dem Ausgang (bidirektional, spart die Polaritaetsfrage)")
    R("100k", neg, f"PYRO{ch}_SENSE", S, descr="Durchgangspruefung")
    R("33k", f"PYRO{ch}_SENSE", "GND", S)
    C("100n", f"PYRO{ch}_SENSE", "GND", S)

# ================================================================ Signal (spec §4: LEDs, Summer, Kamera)
S = "signal"
group("Status-LEDs")
for i, (u, led) in enumerate([("U8", "LED1"), ("U9", "LED2")], start=1):
    add(u, "74xGxx:74AHCT1G125", "74AHCT1G125", SOT235, S,
        {1: "GND", 2: f"LED{i}_DATA", 3: "GND", 4: f"LED{i}_5V", 5: "5V_SYS"}, lcsc="C2870384",
        descr="Pegel 3,3 -> 5 V")
    C("100n", "5V_SYS", "GND", S)
    R("330", f"LED{i}_5V", f"LED{i}_DIN", S)
    add(led, "LED:WS2812B-2020", "WS2812B-2020", "LED_SMD:LED_WS2812B-2020_PLCC4_2.0x2.0mm", S,
        {1: "LED_EXT_DATA" if i == 1 else None, 2: "GND", 3: f"LED{i}_DIN", 4: "5V_SYS"}, lcsc="C965555")
    C("100n", "5V_SYS", "GND", S)
add("J14", "Connector_Generic:Conn_01x03", "J_LED", JST + "JST_GH_BM03B-GHS-TBT_1x03-1MP_P1.25mm_Vertical", S,
    {1: "5V_SYS", 2: "LED_EXT_DATA", 3: "GND"}, func="J_LED", descr="externe WS2812B, Kette hinter LED1")
group("Summer")
add("BZ1", "Device:Buzzer", "aktiv 5V 12mm", "Buzzer_Beeper:Buzzer_12x9.5RM7.6", S, {1: "5V_SYS", 2: "BZ_NEG"},
    descr="aktiver Summer, THT")
add("D4", "Device:D", "1N4148W", "Diode_SMD:D_SOD-123", S, {1: "5V_SYS", 2: "BZ_NEG"}, lcsc="C81598")
add("Q5", "Transistor_FET:AO3400A", "AO3400A", SOT23, S, {1: "BZ_G", 2: "GND", 3: "BZ_NEG"}, lcsc="C20917",
    descr="Summer")
R("100", "BUZZER", "BZ_G", S)
R("100k", "BZ_G", "GND", S)
group("Kamera")
R("1k", "CAM_TRIG", "CAM_TRIG_OUT", S)
add("J13", "Connector_Generic:Conn_01x03", "J_CAM", JST + "JST_GH_BM03B-GHS-TBT_1x03-1MP_P1.25mm_Vertical", S,
    {1: "5V_SYS", 2: "CAM_TRIG_OUT", 3: "GND"}, func="J_CAM", descr="Kamera-Ausloeser (3,3-V-Pegel ueber 1 k)")

# ---------------------------------------------------------------- power flags for ERC
# Nets fed only through connectors, fuses or diodes carry a PWR_FLAG so ERC knows they are driven.
PWR_FLAGS = {"power": ["GND", "GND_PWR", "VBAT_MEAS", "VSYS_IN", "TEENSY_VIN", "5V_SERVO"],
             "actuators": ["U7_VINT"]}   # DRV8833 VINT is its own regulator output, typed power_in in the library

# ERC findings that are intended, written into the project as exclusions with the reason.
# Items are (ref, pin); "#FLG:<net>" names the power flag of that net.
ERC_EXCLUSIONS = [
    ("pin_to_pin", ("U7", "2"), ("U7", "7"), "DRV8833: Bruecken A und B bewusst parallel (Datenblatt 8.3.6)"),
    ("pin_to_pin", ("U7", "4"), ("U7", "5"), "DRV8833: Bruecken A und B bewusst parallel (Datenblatt 8.3.6)"),
    ("pin_to_pin", ("U7", "3"), ("#FLG:GND_PWR", "1"), "AISEN ohne Strommessung direkt an GND_PWR"),
    ("pin_to_pin", ("U7", "6"), ("#FLG:GND_PWR", "1"), "BISEN ohne Strommessung direkt an GND_PWR"),
]

# ---------------------------------------------------------------- net classes (spec §8)
NETCLASSES = {
    # name: (track width, clearance, via diameter, via drill, nets)
    "Strom": (1.2, 0.25, 0.8, 0.4, ["VBAT2_RAW", "VBAT2_REV", "VBAT_PROT", "VBAT_MEAS", "VSERVO", "VBAT_ARMED",
                                    "PYRO1_NEG", "PYRO2_NEG", "GND_PWR"]),
    "Versorgung": (0.6, 0.2, 0.6, 0.3, ["VBAT1_RAW", "VBAT1_PROT", "VSYS_IN", "5V_SYS", "5V_SERVO", "3V3",
                                        "3V3_RF", "TEENSY_VIN", "MOT_A", "MOT_B", "U1_SW", "U2_L1", "U2_L2", "GND"]),
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


check()

if __name__ == "__main__":
    n = nets()
    print(f"{len(PARTS)} parts, {len(n)} nets")
    for s, title, _ in SHEETS:
        print(f"  {title:12s} {sum(p.sheet == s for p in PARTS):3d} parts")
