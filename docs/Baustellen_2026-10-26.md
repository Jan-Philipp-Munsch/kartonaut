# Baustellen am Projekt (Stand 26.10.2026)

Was nach dem Platinen-Review ansteht, nach Strängen geordnet und innerhalb jedes Strangs nach Dringlichkeit.
Stand: `main` = `github/main` auf Commit `e774e59` (26.10., alle Branches und PR #2–#7 gemergt, CI grün).
Quellen: `PROJECT.md` §6 (Stand 26.10.), `README.de.md` „Als Nächstes“, `hardware/mainboard/kicad/README.md` §8,
`firmware/Tischtest_revB1.md` §7, `docs/Bauanleitung_Kartonaut1.md` §8, `cad/README.md` „Offen“,
`simulation/README.md` „Offen“.

## 1. Platine rev B1 und Bestellung (jetzt)

| Nr. | Baustelle | Quelle |
|---|---|---|
| 1.1 | **Durchsicht nach `hardware/mainboard/REVIEW_PAKET_2026-10-26.md`**, A-Punkte einarbeiten, DRC und Prüfskript, `./make.sh fab` neu | REVIEW_PAKET, REVIEW_ANLEITUNG |
| 1.2 | 1:1-Papierausdruck in Rohr B / Kuppler, Kabelwege zu Luke B (J_SW, J_CHG1, J_CHG2) und J_ARM prüfen | `kicad/README.md` §8.4 |
| 1.3 | 111 BOM-Positionen mit LCSC-Nummern versehen (Passive aus dem Angebot vom 23.10. übernehmen; neu: INA239, SN74LV1T34, 74HC138/4051, Polymer-Elkos, Polyfuses) | `kicad/fab/FAB.md` |
| 1.4 | JLCPCB-Angebot mit den rev-B1-Dateien wiederholen (das vom 23.10. ist rev B); Oberfläche ENIG | `Angebot_JLCPCB_2026-10-23.md` |
| 1.5 | Bestand am Bestelltag: BMP390 (Rückfall BMP388), E22-400T22S, TPS63070, LSM6DSV16X, AO3401A-Alternative mit −2,5 V | `ORDER.md` §3.3 |
| 1.6 | Bestellung nach Freigabe (Meilenstein M1): 5 Platinen, 2 bestückt, Economic PCBA; E22, WS2812, ggf. BMP390 und 16 THT-Teile selbst löten | `ORDER.md` §3 |
| 1.7 | Einkauf nach `EINKAUFSLISTE_revB1.md` und Bauanleitung §3.1 (THT-Teile, Gegenstecker, Crimpzange, Akkus, Breakouts, Schrauben; Reichelt, Berrybase, Ebyte); **1S-Ladegerät fehlt** (HTRC H4AC kann kein 1S) | EINKAUFSLISTE, Bauanleitung §3.1 |
| 1.8 | ~~Datenblatt auf rev B1~~ (erledigt 26.10., Version 0.2); Design Guide `docs/DesignGuide_Mainboard_revB.md` im Text noch rev B (Abbildungen seit 26.10. rev B1) | `kicad/README.md` §8.7 |

## 2. Repo (klein, seit dem Merge vom 26.10.)

| Nr. | Baustelle | Befund |
|---|---|---|
| 2.1 | Drei uncommittete Dateien im Haupt-Checkout: `hardware/mainboard/Angebot_JLCPCB_2026-10-23.md`, `hardware/mainboard/REVIEW_PAKET_2026-10-26.md`, `docs/Baustellen_2026-10-26.md`; committen (README-Regel aus CLAUDE.md beachten, wenn der Projektstand sich ändert) | `git status` |
| 2.2 | Sechs Worktrees unter `.claude/worktrees/` (alle sauber, alle in `main` enthalten) und die zugehörigen lokalen Branches aufräumen; Remote-Branches auf GitHub ebenso | `git worktree list` |
| 2.3 | Umbenennung `groundcode` → `kartonaut-ground` auf GitHub und RWTH-GitLab und in den Remotes | PROJECT §6.9 |
| 2.4 | `hardware/mainboard/kicad/.history/` (Editor-Plugin) ist ignoriert, liegt aber noch lokal; kann weg | `.gitignore` |

## 3. Firmware

| Nr. | Baustelle | Quelle |
|---|---|---|
| 3.1 | **Treiber LSM6DSV16X** (SPI, WHO_AM_I 0x70) hinter `Imu.h`; Schnittstelle und Werksselbsttest sind vorbereitet, E12 ist entschieden | `firmware/README.md` §rev B1, Tischtest §7.5 |
| 3.2 | Kalibrierwerte aus `lib/calstore/` an den rev-B-Sensorpfad (`Sensors_revb.cpp`) anschließen | PROJECT §6.3, Tischtest §7.4 |
| 3.3 | CO₂-Auslösung aus dem Zustandsautomaten (Kartonaut 1 wirft mit CO₂ aus, nicht pyrotechnisch) | PROJECT §6.3 |
| 3.4 | `Telemetry.h` als gemeinsamen Header in `kartonaut-ground` übernehmen; LoRa-Protokoll (PING/PONG, RSSI-Byte) festlegen | PROJECT §6.3, Tischtest §7.2–7.3 |
| 3.5 | `Config.h` auf die gewogene Masse und die Gewinne Kp 2 / Ki 1 / Kd 0,45 (Befund 22); Befunde 1–4 aus PROJECT §5 vor dem ersten Flug mit aktiver Regelung | PROJECT §6.3 |
| 3.6 | Körperachse +x für `cal axes` festlegen (hängt mit CAD 4.2 zusammen) | Tischtest §7.1 |
| 3.7 | Tischtest nach `Tischtest_revB1.md` und die Versuche `Versuche_revB1.md` (E01 am alten Kardan als Prüfung der Messkette, dann E02 auf rev B1) fahren, sobald die Platine da ist | firmware/ |
| 3.8 | Später: Schubdrossel und Landebrennen (`THROTTLE_F_MIN`, `LANDING_IGNITER_DELAY_S` nach Experiment E05) | PROJECT §6.8 |

## 4. Mechanik, CAD und Bau

| Nr. | Baustelle | Quelle |
|---|---|---|
| 4.1 | **Bauanleitung umsetzen:** Druckteile Stand 2c drucken (PETG, 3 Wände, 25 %) und wiegen; Gewichtspaket P1 entscheiden (705 → 672 g); CO₂-Modul konstruieren (O6); altes GPS-Modul bestimmen (O3); Servofenster am Rohr nachsehen (O1) | PROJECT §6.2, Bauanleitung §8 |
| 4.2 | Kardan an die FrSky W5652H anpassen: Wellenlage, Laschenabstand, Schraubenmaß aus dem Datenblatt, dann `tvc.py`-Taschen am gebauten Kardan prüfen (O4) | `cad/README.md` Offen 3 |
| 4.3 | Pitch/Yaw-Zuordnung der Servos zu `Config.h` und zur Platinenlage (`chipToBody`) | `cad/README.md` Offen 1 |
| 4.4 | Rakete wiegen, Schwerpunkt auspendeln, Bifilarpendel; `mass_stand2b.py`, `Config.h`, `ServoParams` korrigieren und die Simulation neu rechnen | PROJECT §6.4 |
| 4.5 | Druckausgleichsbohrungen fürs Barometer ins CAD (die alten Löcher in Rohr B bei h = 44 übernehmen diese Rolle laut Bauanleitung) | `cad/README.md` Offen 5 |
| 4.6 | Ringspiel 4,4 mm des Innenrahmens prüfen | `cad/README.md` Offen 4 |
| 4.7 | TVC-Prüfstand bauen (`cad/testrig.py`, Drehpunkt 256 mm): Teile drucken und kaufen, BR2814 nachmessen, Gurt-Anschläge, Kabelführung, Gas-Ausgang in der Firmware | `cad/README.md` Offen 6, PROJECT §6.5 |
| 4.8 | Später: Einklappmechanismus und Flugverriegelung der Beine, Drosselmechanik (Pads, zwei Servos, ca. 60 g) | `cad/README.md` Offen 2, PROJECT §6.8 |

## 5. Simulation und Versuche

| Nr. | Baustelle | Quelle |
|---|---|---|
| 5.1 | W5652H vermessen (E01) und `ServoParams` aktualisieren; Servo-Grad je TVC-Grad (6 oder 23) und Polung messen; Ratenbegrenzung ins Modell, falls bestätigt | `simulation/README.md` Offen |
| 5.2 | `tf5` aus MATLAB exportieren und mit dem Fit vergleichen (Widerspruch zum Tuner-Ergebnis) | ebd. |
| 5.3 | Flugzustandsautomat in die Simulation (zweite Zündung bei 7,3 s trifft sonst die fallende Rakete) | ebd. |
| 5.4 | Nominallauf aus Simulink exportieren für den quantitativen Vergleich | ebd. |

## 6. Bodensysteme und Bodentests

| Nr. | Baustelle | Quelle |
|---|---|---|
| 6.1 | Bodenstation Sparvariante bauen (ca. 80 €): Messplatine löten, Module verdrahten, flashen, Zündkreis mit Lastwiderstand abgleichen | PROJECT §6.6 |
| 6.2 | Startrampe bauen (ca. 86 €, Führungen 45°/135°/250° nach Befund 17, gegen `modular.py` prüfen) | PROJECT §6.6 |
| 6.3 | Startsperre Ende zu Ende vom Handy bis zum Lämpchen (M5) | PROJECT §6.6 |
| 6.4 | Bodentests: CO₂-Ausstoß dreimal (auch kalt), Barometer-Druckausgleich, Funkreichweite und GPS-Fix bei sendendem LoRa, geschlossener Regelkreis am Prüfstand (M4) | PROJECT §6.5 |
| 6.5 | Zweiter E22-400T22D (DIP) und Antennen für Bodenstation und Tischgegenstelle bestellen | `ORDER.md` §1 (0.3–0.5) |

## 7. Reihenfolge bis zum Erstflug (Vorschlag)

1. Platinen-Review und Bestellung (1.1–1.6), parallel Einkauf (1.7) und Druckteile (4.1).
2. Während die Platine unterwegs ist (ca. 2–3 Wochen): LSM6DSV16X-Treiber (3.1), Kalibrierpfad und CO₂-Auslösung (3.2–3.3), Kardan für W5652H (4.2), Prüfstand (4.7), Bodenstation und Startrampe (6.1–6.2).
3. Platine da: THT löten, Tischtest, E01/E02, Kalibrierung (3.7).
4. Rakete bauen, wiegen, Schwerpunkt, Simulation mit Messwerten (4.4).
5. Bodentests (6.3–6.4), Checklisten, Erstflug *Kartonaut 1* ohne Landesystem (M6/M7).
