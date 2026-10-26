# Abschlussprüfung Mainboard rev B1 vor der Bestellung (26.10.2026)

Maschinelle Prüfung der Fertigungsdaten in `kicad/fab/` (Export 24.10. 11:22, Platinendatei 24.10. 11:21) gegen
die Spezifikation `README.md` und die veröffentlichten Fertigungsgrenzen von JLCPCB (Seite „PCB Capabilities“,
abgerufen 26.10.2026). Ergänzt das Review-Paket vom selben Tag. **Ergebnis: keine Verletzung einer JLCPCB-Grenze,
keine Abweichung von der Spezifikation; alle 17 KiCad-Warnungen betreffen nur den Bestückungsdruck.**

## 1. Fertigungsdaten (Gerber-ZIP, Bohrdatei, BOM, CPL)

| Prüfung | Befund |
|---|---|
| Lagen im ZIP | F/In1/In2/B.Cu, F.Paste, F/B.Silkscreen, F/B.Mask, Edge.Cuts, Bohrplan, Job-Datei (Protel-Endungen) – vollständig für 4 Lagen, Bestückung nur oben |
| Umriss | geschlossen: Rechteck 54 × 120 mm (x 100–154, y 50–170) mit vier Bögen r = 2 mm; Job-Datei meldet 54,1 × 120,1 (Linienbreite) |
| Bohrdatei | eine Excellon-Datei, metrisch, PTH und NPTH mit Attributen: 0,2 mm (12 Thermovias DRV8833), 0,3 mm (Vias), 0,75 / 0,95 / 1,0 mm (JST, Teensy), 1,9 mm (2), 3,2 mm NPTH (5, davon 4 Befestigungslöcher) |
| BOM ↔ CPL | 132 Referenzen in beiden, keine Dubletten, alle `Top`, Drehungen 0/90/180/−90, alle LCSC-Nummern im Format `C\d+` |
| BOM | 53 Zeilen, 21 Teile mit LCSC-Nummer (14 Typen), 111 ohne (Passive, Stecker, Polyfuses, Elkos, INA239, SN74LV1T34, 74HC138/4051) |
| ERC / DRC | ERC 0/0; DRC 0 Fehler, 0 offen, Schaltplan-Parität 0, 17 Warnungen (Bestückungsdruck) |

## 2. JLCPCB-Grenzen (4 Lagen, 1 oz außen) gegen die Platine

Gemessen mit einem zweiten DRC-Lauf auf einer Kopie, Regeln auf die JLCPCB-Werte gesetzt, und mit der KiCad-API.

| Grenze JLCPCB | Platine | |
|---|---|---|
| Bahn / Abstand ≥ 0,09 mm | min 0,127 mm (Regel), Netzklasse 0,15 mm | ✓ |
| Via-Loch ≥ 0,15, Durchmesser ≥ 0,25; Aufpreis nur bei Loch 0,2/0,25 **und** Durchmesser < 0,45 | Vias 0,3 / 0,6 mm; 12 Thermovias 0,2 / 0,5 mm (Durchmesser ≥ 0,45, kein Aufpreis; im Formular die Via-Option wählen, die 0,2 mm einschließt) | ✓ |
| Restring PTH ≥ 0,15 (empfohlen 0,2) | Vias 0,15; Teensy-Pads 0,35; JST 0,225 | ✓ |
| Loch zu Loch: Via 0,2, Pad 0,45 | kleinster Abstand 0,45 mm (12 Via-Paare zwischen 0,45 und 0,50) | ✓ |
| Kupfer zum gefrästen Rand ≥ 0,2 mm | 0,2 mm (Zonen), an den Ecken ebenfalls 0,2 | ✓ |
| NPTH ≥ 0,5 mm; NPTH zu Kupfer ≥ 0,2 | 3,2 mm; Zonen halten 0,25 mm zum Lochrand auf allen vier Lagen | ✓ |
| Via-Loch zu Innenlagen-Kupfer ≥ 0,2; PTH-Loch ≥ 0,3 | Via 0,30; Teensy 0,50; JST 0,375 (Restring + Netzklasse) | ✓ |
| Lötstoppsteg ≥ 0,10 mm (blau, 1 oz) | engste Pads 0,5-mm-Raster (VQFN, LGA, HTSSOP, TSSOP): Steg ≈ 0,2 mm | ✓ |
| Bestückungsdruck Linie ≥ 0,15, Schrift ≥ 1,0 mm | alle Texte 0,15 / 0,2 mm Strich, 1,0 mm hoch; Footprint-Grafik teils 0,06–0,12 mm (wird blass oder fehlt, nur Umrisse) | ✓ (kosmetisch) |

## 3. Die 17 KiCad-Warnungen

| Art | Anzahl | Was | Folge |
|---|---|---|---|
| Druck über Kupfer | 14 | Teensy-Umriss (A1) über den Pads des E22-Moduls (12), JLC-Platzhalter `JLCJLCJLCJLC` über C17 (2) | JLCPCB entfernt Druck auf Pads automatisch. Der Teensy-Umriss bekommt Lücken; die Auftragsnummer wird an C17 angeschnitten (bei *Specify a location*) |
| Druck überlappt Druck | 2 | U4-Referenz über IMU-Pfeil, E22-Kreis über Teensy-Umriss | rein kosmetisch |
| Druck am Rand | 1 | Pin-Tabelle auf der Rückseite nahe der linken Kante | wird am Rand beschnitten, kosmetisch |

Keine davon betrifft Kupfer, Bohrung, Lötstopp oder Paste. JLCPCB prüft beim Hochladen und vor der Fertigung nur die
Herstellbarkeit (Umriss, Lagen, Bohrungen, Abstände unter ihren Grenzen) und meldet sich per E-Mail, wenn etwas davon
unklar ist; Schaltungsfehler, Lesbarkeit des Drucks oder KiCad-Warnungen sieht der Fertiger nicht, sie stehen nicht in
den Gerber-Dateien.

## 4. Spezifikation `README.md` gegen die Platine

| Anforderung | Befund |
|---|---|
| §2 54 × 120 × 1,6 mm, 4 Lagen, ENIG, Eckradius 2 | ✓ (Job-Datei: ENIG; im Bestellformular wählen) |
| §2 4 × M3 bei u = ±23,5, v = 3,5 / 116,5 | Löcher bei x 103,5 / 150,5, y 53,5 / 166,5 ✓ |
| §2 IMU bei u = 0, v = 60,5 unter der Teensy-Mitte | U4 bei x 127,0 / y 109,5 ✓ |
| §2 Bestückung nur oben, unten nur Lötstifte | CPL 132 × Top, keine Footprints auf B.Cu ✓ |
| §2 am Rand (\|u\| > 25 mm) höchstens 5 mm hoch | dort nur 0603, WS2812-2020, SOT-23-5, E22-Modul (≤ 2,6 mm) ✓ |
| §4 Pinbelegung | `check_design.py`: OK (42 Pins, 7 CS, 7 Mux-Kanäle, 11 Schienen) ✓ |
| §7 Stückliste | alle genannten ICs, FETs, Dioden, Polyfuses, Elkos in BOM oder FAB.md-Liste; W25Q128 gehört auf den Teensy selbst (Einkaufsliste 0.19) ✓ |
| §8 2S-Netze nur außen, IMU-Umfeld, Kelvin, LoRa-Sperrflächen | `review_check_layout.py` ohne Befund ✓ |

## 5. Vor dem Hochladen (Empfehlungen, keine Pflicht)

1. **LCSC-Spalte in `mainboard_bom.csv` vorab füllen** (Nummern aus `Angebot_JLCPCB_2026-10-23.md`), sonst sind beim
   Upload 111 Positionen von Hand zuzuordnen. LED1/LED2 (C965555, am 23.10. ausverkauft) aus der BOM nehmen, sie
   werden selbst gelötet; ebenso E22 und ggf. BMP390.
2. Im Formular: 4 Lagen, JLC04161H-7628, 1,6 mm, ENIG, Lötstopp blau (oder grün), Via-Option mit 0,2 mm Loch, Auftragsnummer
   *Specify a location* (oder entfernen lassen), Economic PCBA nur oben, 2 bestückt.
3. In der Bestückungsvorschau: Pin 1 von U2 (VQFN), U4/U5 (LGA), U7 (HTSSOP), U10 (E22), Polarität D1/D4, Drehung SOT-23-5.
4. Kosmetik, nur wenn ohnehin noch etwas geändert wird: Platzhalter `JLCJLCJLCJLC` von C17 wegrücken (x 127 / y 90).

Wird noch etwas an der Platine geändert, danach `./make.sh drc` und `./make.sh fab` erneut laufen lassen.
