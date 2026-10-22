# Druckteile erstflug (aus `cad/build.py --config erstflug --print`)

Jede Datei liegt mittig auf der Druckplatte (z ab 0), in Einbaulage; im Slicer drehen, wo es sich besser druckt.
Geschätzte Masse = Volumen × 1.24 g/cm³ (PLA) × 0.45 (3 Wände, 20 % Füllung). Nach dem Druck wiegen
und die Masse in `cad/params.py` eintragen; `python cad/mass_model.py` rechnet Schwerpunkt und Trägheit neu.

| Teil | Datei | Außenmaß [mm] | Volumen massiv | geschätzt | im Massenmodell | Abweichung |
|---|---|---|---|---|---|---|
| Spitze Spant mit Öse | `nose_spant.stl` | 70.0 × 70.1 × 12.5 | 15.5 cm³ | 9 g | 3.0 g | +6 g |
| Außenrahmen | `tvc_aussenrahmen.stl` | 72.4 × 72.4 × 47.6 | 25.1 cm³ | 14 g | 22.0 g | -8 g |
| Motorrohr | `tvc_motorrohr.stl` | 38.3 × 33.6 × 58.1 | 13.4 cm³ | 7 g | 12.0 g | -5 g |
| Adapter 29→24 | `tvc_adapter_29_24.stl` | 29.0 × 29.0 × 85.1 | 16.5 cm³ | 9 g | 15.0 g | -6 g |
| Innenrahmen | `tvc_innenrahmen.stl` | 54.0 × 57.0 × 48.5 | 17.3 cm³ | 10 g | 16.0 g | -6 g |
| Endring unten | `fc_endring_unten.stl` | 69.0 × 69.1 × 6.1 | 13.6 cm³ | 8 g | 7.5 g | +0 g |
| Endplatte oben (Spant, Ladungsschale) | `fc_endplatte_oben.stl` | 69.0 × 69.1 × 14.5 | 22.7 cm³ | 13 g | 17.5 g | -5 g |
| Träger (gedruckt) | `fc_traeger.stl` | 54.0 × 13.7 × 139.0 | 23.5 cm³ | 13 g | 15.0 g | -2 g |
| Schalterbrett (Luke B) | `fc_schalterbrett.stl` | 11.0 × 18.6 × 59.5 | 1.9 cm³ | 1 g | – |  |
| Schlüsselschalter-Kragen | `fc_schluesselschalter_kragen.stl` | 72.5 × 72.5 × 18.2 | 40.1 cm³ | 22 g | 8.0 g | +14 g |

Summe: geschätzt 106 g, im Massenmodell 116 g (-10 g).

Auffällig (22.10.2026): Der Schlüsselschalter-Kragen ist ein massiver Ring (Ø 72,4 außen, 18 mm hoch) und
wiegt gedruckt etwa 22 g statt der 8 g im Massenmodell. Ein dünnerer Ring mit einem Auge nur um die
Schalterbohrung spart etwa 15 g; ein Arming-Stecker statt des Schlüsselschalters (siehe
`cad/weight_levers.md`) macht den Kragen ganz überflüssig.
