# Mainboard rev B – JLCPCB-Angebot (Test)

Stand 2026-10-23. Erstes echtes Angebot mit den Fertigungsdaten aus `kicad/`, nur zur Kostenabschätzung,
**nicht bestellt**. Ergänzt `Fertiger_2026-10-21.md` (dort Schätzungen aus Preisseiten) und `ORDER.md`.
Alle Preise in USD, ohne Zoll und Einfuhrumsatzsteuer.

> **Achtung, falscher Stand:** Dieses Angebot beruht auf dem Layout in `main` (INA219, 2 × 74AHCT1G125,
> THT-Elkos). Das aktuelle, fertig geroutete Board **rev B1** liegt auf dem Branch `claude/rev-b1` mit
> eigenen Bestelldateien in `kicad/fab/` (132 SMD-Bauteile, INA239, 74HC138, LIS3MDL, SHT40). Für eine
> Bestellung das Angebot mit diesen Dateien wiederholen. Größenordnung und Schlüsse unten bleiben gültig.

## Dateien

| Datei | Inhalt |
|---|---|
| `kicad/mainboard-jlcpcb.zip` | Gerber (4 Lagen) + Bohrdateien, Export vom 23.10. 14:40 |
| `kicad/jlcpcb/mainboard-BOM.csv` | 43 Zeilen, alle mit LCSC-Nummer |
| `kicad/jlcpcb/mainboard-CPL.csv` | 102 SMD-Bauteile, alle oben |

BOM und CPL sind per Skript aus `*.kicad_sch` und `mainboard.kicad_pcb` erzeugt (kein `kicad-cli` installiert).
THT-Teile (A1, BZ1, C3, C11, C19, J1–J10, J15), Testpunkte, Lötjumper, NetTie und Montagelöcher sind nicht
enthalten. Die Drehwinkel kommen ungeändert aus KiCad; in der JLCPCB-Vorschau saßen die Teile auf den Pads,
Pin-1-Lagen von ICs und LEDs vor einer echten Bestellung trotzdem einzeln prüfen.

### Ergänzte LCSC-Nummern

Im Schaltplan hatten nur 14 Bauteiltypen eine LCSC-Nummer. Ergänzt (Lager und Typ am 23.10. in der
JLCPCB-Teilesuche geprüft):

| Wert | Footprint | LCSC | Typ |
|---|---|---|---|
| 100n / 10n / 1u / 2.2u | 0603 | C14663 / C57112 / C15849 / C23630 | Basic |
| 10u/25V, 22u/10V | 0805 | C15850, C45783 (25 V) | Basic |
| 100u/6.3V | 1210 | C426103 (Murata GRM32EE70J107ME15L) | Extended |
| 10k / 100k / 4.7k / 1k / 100 / 220 / 330 / 33k / 56k / 330k | 0603 | C25804 / C25803 / C23162 / C21190 / C22775 / C22962 / C23138 / C4216 / C23206 / C23137 | Basic |
| 130k / 680k | 0603 | C22795 / C25822 | Extended |
| 20 mΩ 1 W | 2512 | C159174 (RTT25R020FTE) | Extended |
| SMBJ12CA | SMB | C353397 | Extended |
| 3 A hold | 1812 | C883162 (BSMD1812-300-16V; 16 V, die 6–8-V-Typen reichen für 2S nicht) | Extended |
| 2.2 µH / 1.5 µH | FNR5040S | C167957 / C167955 | Extended |
| J_GPS / J_CAM, J_LED / J_QWIIC | JST GH / SH | C161692 / C161691 / C160390 | Extended |
| WS2812B-2020 | 2020 | C52917434 (V6; C965555 ausverkauft) | Extended, nur Standard-PCBA |

## Angebot

Platine: 5 Stück, 4 Lagen, 120 × 54 × 1,6 mm, FR4 TG135, 1 oz außen / 0,5 oz innen, Vias 0,3 mm.

| Variante | Platine |
|---|---|
| blau, ENIG (wie in KiCad) | $51.30 |
| **grün, LeadFree HASL (gewählt)** | **$34.20** |

Bestückung Economic PCBA, Oberseite, 5 Stück, ohne BMP390, E22 und WS2812 (siehe unten):

| Posten | 5 bestückt | 2 bestückt (hochgerechnet) |
|---|---|---|
| Platine | $34.20 | $34.20 |
| Setup, Schablone, X-Ray | $18.04 | ~$18 |
| Extended-Gebühr (fix je Typ) | $46.35 | $46.35 |
| Bauteile | $159.38 | ~$65–70 |
| Bestückung | $2.35 | ~$1 |
| **Summe** | **$260.32** | **~$165** |

Versand DHL ca. $31 (Platine allein; bestückt 586 g, eher mehr). Mindestmenge bei JLCPCB-Bestückung ist 2.
Die Fixkosten (~$100) fallen unabhängig von der Stückzahl an: pro fertiger Platine ~$52 bei 5, ~$82 bei 2.

## Auffälligkeiten

- **BMP390 (U5):** bei JLCPCB 0 auf Lager. Global Sourcing (ca. $27 für 5) oder selbst einlöten.
- **E22-400T22S (U10):** nur 3 Stück auf Lager. Großes Modul, von Hand gut lötbar.
- **WS2812B-2020:** nur mit Standard-PCBA ($25 Setup statt $8, plus Randstreifen 70 × 120 mm). Selbst löten.
- **ICM-42688-P (U4):** $21.52/Stück bei JLCPCB (Lagerzuschlag, 453 Stück), bei Distributoren geschätzt ~$5
  (nicht geprüft). Macht $107 von $159 Bauteilkosten bei 5 Stück.
- **INA219 vs. INA239:** Im Schaltplan sitzt U6 = INA219AIDR (I²C), die Firmware rev B ist für den INA239
  (SPI) geschrieben. Vor der Bestellung klären.

## IMU-Frage

Der ICM-42688-P misst nur bis **±16 g**. Modellraketenmotoren erreichen beim Brennen oft 10–20 g, dann
sättigt der Sensor. Alternativen (Preise JLCPCB, 23.10.):

| Sensor | Bereich | Preis | Bemerkung |
|---|---|---|---|
| ICM-42688-P (jetzt) | ±16 g | $21.52 | |
| **LSM6DSO32** | **±32 g** | **$6.44** | gleiches Gehäuse LGA-14 2,5 × 3, andere Pinbelegung, neuer Treiber |
| BMI088 | ±24 g | $6.63 | anderes Gehäuse |
| ASM330LHH | ±16 g | $5.46 | gleicher Bereich wie jetzt |

Offen: Spitzenbeschleunigung aus Schubkurve und Startmasse abschätzen. Liegt sie sicher unter ~12 g,
bleibt der ICM; sonst Wechsel auf LSM6DSO32 (spart bei 2 Platinen ~$30).

## Selbst bestücken?

Eine Heißluftstation ist vorhanden. Damit gut machbar: 0603/0805, SOT-23, SOIC, HTSSOP-Wärmepad, E22,
WS2812, Nacharbeit. Riskant bleiben die Teile mit verdeckten Pads (ICM LGA-14, BMP390 LGA-10,
TPS63070 VQFN-15): ohne Röntgen keine Kontrolle, der TPS63070 versorgt das ganze Board.

Selbst bestückt kosten 2 Platinen ~$100 (Platine, Schablone ~$8, Bauteile ~$40–50 von Mouser/LCSC,
Versand ~$15) statt ~$165, also ~$60 Ersparnis für mehrere Stunden Arbeit und Ausfallrisiko. Überteuert ist
nur der ICM; der Aufpreis beträgt bei 2 Platinen ~$33.

## Entscheidung (Empfehlung)

1. **2 Platinen bei JLCPCB bestücken lassen**, Platine grün / LeadFree HASL.
2. JLCPCB bestückt alle SMD-Teile außer E22, WS2812 und ggf. BMP390.
3. Selbst gelötet: THT-Teile, E22, 2 × WS2812, ggf. BMP390 (von Mouser, mit Heißluft; vorher auf einer
   Reserveplatine üben).
4. Vorher klären: IMU (Beschleunigung) und INA219/INA239.
