# Review-Brief Mainboard rev B1 (23.10.2026)

Für das Review vor der Platinenbestellung. Alles Nötige liegt im Branch `claude/rev-b1`
(Pull Request auf GitHub, Repo `Jan-Philipp-Munsch/kartonaut`). Rückmeldungen am liebsten als
Kommentare im Pull Request, Zeile oder Datei genügt.

## 1. Das Projekt in einem Absatz

**Kartonaut** ist eine Modellrakete mit Schubvektorsteuerung nach dem Vorbild der „Scout F“ von
BPS.space: Rumpf aus Klima-Papprohr Ø 75 mm, Motor TSP E12 in einem Kardan mit zwei Servos, Rollmotor,
Fallschirm mit pyrotechnischem Kolbenausstoß. An Bord ein Teensy 4.1 auf einem eigenen Mainboard mit
IMU (ICM-42688-P), Barometer (BMP390), Strommonitor (INA239), microSD und LoRa-Funk zur Bodenstation.
Firmware (PlatformIO), 6DOF-Simulation (Python) und CAD (CadQuery) liegen im selben Repo. Der Erstflug
*Kartonaut 1* fliegt ohne Landesystem, Ziel unter 750 g. Übersicht: `README.de.md` im Repo-Wurzelverzeichnis.

## 2. Die Platine in Zahlen

| | |
|---|---|
| Format | 54 × 120 mm Längsschlitten im Kuppler, 4 Lagen (F.Cu Signale, In1 GND, In2 Signale, B.Cu GND_PWR / 5V_SYS), 1,6 mm, ENIG, JLC04161H-7628 |
| Versorgung | zwei Akkus: 1S für die Elektronik über TPS63070 (Buck-Boost, 5 V), 2S für Servos, Rollmotor und Pyro; Lastschalter über FETs (E1), Polyfuse je Akku (A4), Laden in der Rakete (E2) |
| Sensorik | ICM-42688-P auf der Rollachse unter dem Teensy, BMP390 (zweites DNP), INA239 mit Kelvin-Shunt 20 mΩ (A5), alles an SPI1 über einen 74HC138-CS-Decoder, Analogmux 74HC4051 für die Messteiler |
| Aktoren | 4 Servoausgänge direkt am 2S, DRV8833 für den Rollmotor, 4 Pyro-Kanäle low-side (3 und 4 DNP), Arming über Schlüsselschalter |
| Schnittstellen | E22-400T22S LoRa, GPS, Kamera, WS2812-LEDs, Qwiic, Stapelstecker J_STACK (20-polig) für eine Zusatzplatine |
| Stand | 166 Bauteile, 113 Netze; ERC 0/0, DRC 0 Fehler, 0 offene Verbindungen, Schaltplan-Parität 0; Prüfskript: kein 2S-Netz auf In2, IMU-Umfeld sauber, Sense-Netze nur am Shunt |

## 3. Was sich seit dem Review vom 21.10. geändert hat

Alle acht A-Punkte und die Entscheidungen E1 bis E10 sind eingearbeitet (`kicad/README.md` §6 listet jede
Abweichung von der Spezifikation mit Grund):

- A1 Ausgangskapazität des TPS63070 auf 470 µF, der 1000-µF-Elko hinter D1 an TEENSY_VIN.
- A2 Unterspannungsschwelle des 1S-Akkus auf 3,1 V ein / 2,7 V aus.
- A3 Hauptschalter schaltet FET-Gates (AO3401A), nicht den Strompfad.
- A4 Polyfuse je Akku. A5 Kelvin-Abgriff am Shunt (eigener Footprint `R_2512_Kelvin`).
- A6 2S-Netze nur auf den Außenlagen; A7 VSYS_IN mindestens 0,6 mm; A8 keine 0,15-mm-Stücke in der Servoversorgung.
- B13 Der 2S-Pfad, die Pyro-Ausgänge und VSYS_IN sind Kupferflächen auf F.Cu (`CORRIDORS` in `gen_pcb.py`), keine Autorouter-Bahnen.
- E3 BMP390 und INA239 an SPI1 (INA239 statt INA219), E5 alle Servos am 2S, E9 Rollmotor direkt am 2S, E10 J_STACK und Pin-Bilanz mit Decoder und Mux.
- **Neu am 23.10.:** Magnetometer LIS3MDL und Feuchte/Temperatur SHT40 bestückt, ADXL375 (±200 g) als
  DNP-Footprint; alle drei an I²C und 3V3, nicht an SPI1/3V3_SENS (`kicad/README.md` §6). Außerdem die
  schmalen Versorgungsstücke nach dem Handrouting verbreitert (VSYS_IN 0,6 mm, A7).

Das Routing: Freerouting aus dem Generator, danach ein eigener Gitter-Router für die Reste und zum Schluss
Handarbeit in KiCad (23.10.). Die Platinendatei ist seitdem die Quelle, der Generator erzeugt sie nicht mehr neu.

## 4. Worauf das Review schauen sollte

Die Punkte, die ich selbst nicht entscheiden kann oder die beim Handrouting entstanden sind:

1. **Strompfade:** Breite und Lage der F.Cu-Flächen (`img/layer_F_Cu.png`): XT30 → Q1 → F1 → Q6 → Shunt →
   VSERVO-Bus → Servostecker, und VBAT_PROT / VBAT_ARMED entlang der rechten Kante zu den Pyro-FETs.
   Die Pyro-Spitze (5 A, 20 ms) liegt bei 1,0 mm Breite.
2. **GND_PWR-Stück 0,15 mm × 1,9 mm an DRV8833 Pin 13** (x 144,5 / y 114,9): kein Platz für mehr, der
   Rückstrom der Brücke läuft über das Wärmepad mit Vias. Reicht das für den Rollmotor (≤ 1 A)?
3. **MOT_A / MOT_B über zwei Vias auf B.Cu** zum Motorstecker J8: schneidet die GND_PWR-Fläche unter den
   Aktoren an. Vertretbar oder umlegen?
4. **Masseführung um den Sternpunkt NT1** am XT30-Minus: GND_PWR (B.Cu) gegen GND (In1), nur dort verbunden.
5. **Anlauf des TPS63070** mit 940 µF hinter D1 (Hold-up gegen Neustart im Flug): Inrush und Softstart.
6. **Abstand LoRa-Modul ↔ IMU** und die Sperrflächen unter dem Modul.
7. **Lastschalter im 1S-Pfad:** AO3401A bei −3 V Gate knapp (B5); am Bestelltag einen Typ mit −2,5 V-Spezifikation prüfen.
8. **Zusatzsensoren:** Magnetometer in der linken Spitzenecke 12 mm von J_PYRO1 und den Pyro-FETs, SHT40 neben
   J_QWIIC, ADXL375 hinter dem USB-Ende des Teensy; alle an 3V3 statt 3V3_SENS. Störung im Flug ist eingeplant.
9. **Bestückung:** 108 Bauteile ohne LCSC-Nummer (Passive, Polyfuses, Polymer-Elkos, JST-Buchsen, INA239,
   SN74LV1T34, 74HC138/4051) werden am Bestelltag im JLC-Teileprogramm zugeordnet (`kicad/fab/FAB.md`);
   BMP390 war bei LCSC zuletzt nicht lieferbar, Rückfall BMP388 pinkompatibel.

## 5. Unterlagen

| Was | Datei |
|---|---|
| Schaltplan (7 Blätter) | `kicad/out/mainboard_schematic.pdf` |
| Lagenbilder und Renders | `kicad/img/layers.pdf`, `kicad/img/render_top.png`, `render_bottom.png` |
| Spezifikation rev B | `README.md` (dieses Verzeichnis) |
| Design Guide mit Abbildungen | `../../docs/DesignGuide_Mainboard_revB.md` (+ PDF) |
| Datenblatt (noch rev B, Stückliste aus `circuit.py`) | `datasheet/MS-MB-B.pdf` |
| Entscheidungen und Abweichungen | `kicad/README.md` §5 und §6, `Komponenten_2026-10-22.md` |
| Review vom 21.10. und Netzlistenprüfung | `review_kicad_2026-10-21.md`, `review_netlist_2026-10-21.md` |
| Bestellplan, Fertiger | `ORDER.md`, `Fertiger_2026-10-21.md` |
| Bestelldateien | `kicad/fab/` (Gerber-ZIP, BOM, CPL, FAB.md) |
| Prüfungen selbst laufen lassen | im Ordner `kicad/`: `./make.sh drc`, `python review_check_layout.py` mit KiCads Python |

Die KiCad-Dateien öffnen sich normal in KiCad 10 (`kicad/mainboard.kicad_pro`). Zum Nachsehen von Netzen
im Layout hilft die Netzliste `kicad/out/mainboard.net`; die Netznamen sind auf Schaltplan, Platine und in
der Spezifikation dieselben.

## 6. Was nach dem Review passiert

Rückmeldungen einarbeiten (Schaltung über `circuit.py` und „Leiterplatte aus Schaltplan aktualisieren“,
Layout direkt in KiCad), DRC und Prüfskript, Papierausdruck 1:1 in den Kuppler, dann Bestellung bei JLCPCB
(Economic PCBA, 5 Platinen, 2 bestückt) nach `ORDER.md` §3. Bestellt wird erst nach deiner Durchsicht.
