# Fertigungsdaten Mainboard rev B1 (JLCPCB)

Erzeugt mit `./make.sh fab` aus `mainboard.kicad_pcb`. Parameter nach `../ORDER.md` §3.1: 4 Lagen,
54 × 120 mm, 1,6 mm, ENIG, Stackup JLC04161H-7628, Economic PCBA nur Oberseite.

| Datei | Inhalt |
|---|---|
| `mainboard_gerber.zip` | F/In1/In2/B.Cu, F.Paste, F/B.Silkscreen, F/B.Mask, Edge.Cuts (Protel-Endungen, ohne X2), Excellon PTH+NPTH in einer Datei, Bohrplan |
| `mainboard_bom.csv` | 53 Zeilen, 132 bestückte SMD-Bauteile, 21 davon mit LCSC-Nummer |
| `mainboard_cpl.csv` | 132 Bauteile, Oberseite, Drehung wie KiCad (im Bestellformular prüfen) |

**Ohne LCSC-Nummer (111 Bauteile, im JLC-Teileprogramm zuordnen):**

- 100n: C1, C2, C3, C7, C12, C24, C25, C26, C29, C30, C34, C36, C39, C40, C41, C42, C43, C44, C45, C46, C47, C48, C49
- 330u/16V polymer: C4, C5
- 10u/25V: C6, C10, C11, C35
- 4.7u: C8, C9
- 22u/10V: C13, C14, C15
- 470u/6.3V polymer: C16, C17
- 1u: C18, C19, C21, C22
- 100u/6.3V: C20
- 10u: C23, C33
- 2.2u: C27, C38
- 10n: C28, C37
- SMAJ12CA: D2, D3
- 3A hold 6A trip: F1
- 2A hold: F2
- 600R@100MHz: FB1
- J_GPS: J11
- J_QWIIC: J12
- J_CAM: J13
- J_LED: J14
- 1.5u Isat>=4A: L2
- 10k: R1, R8, R18, R19, R22, R27
- 100k: R2, R4, R9, R11, R28, R31, R32, R35, R36, R39, R40, R43, R44, R48
- 1k: R3, R10, R49
- 33k: R5, R12, R29, R33, R37, R41, R45
- 10: R6, R7
- 2k: R13
- 680k: R14
- 130k: R15
- 330k: R16
- 115k: R17
- 4.7k: R20, R21
- 220: R23, R24, R25, R26
- 100: R30, R34, R38, R42, R47
- 330: R46
- 20m 1% 1W: R_SH1
- INA239AIDGSR: U6
- SN74LV1T34DBVR: U8
- 74HC138PW: U12
- 74HC4051PW: U13

**Von Hand zu löten (16 THT-Teile, nicht in BOM und CPL):** A1 (Teensy 4.1), BZ1 (aktiv 5V 12mm), J1 (XT30PW-M), J2 (J_BAT1), J3 (J_SW), J4 (J_ARM), J5 (J_SERVO1), J6 (J_SERVO2), J7 (J_SERVO3), J8 (J_MOT), J9 (J_PYRO1), J10 (J_PYRO2), J15 (J_STACK), J16 (J_SERVO4), J17 (J_CHG1), J18 (J_CHG2)

**Kein Bauteil (Löcher, Netzbrücke, Testpunkte, Lötjumper):** H1, H2, H3, H4, JP1, JP2, NT1, TP1, TP2, TP3, TP4, TP5, TP6, TP7

**DNP (12):** C31 (100n), C32 (100n), C50 (1u), C51 (100n), D5 (SMAJ12CA), D6 (SMAJ12CA), J19 (J_PYRO3), J20 (J_PYRO4), Q8 (AO3400A), Q9 (AO3400A), U15 (BMP390), U17 (ADXL375)
