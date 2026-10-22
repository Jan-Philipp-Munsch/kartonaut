# Kartonaut: Abzeichen

| Datei | Inhalt |
|---|---|
| `kartonaut_patch.svg` | Abzeichen „KARTONAUT · TVC · Ø 75 MM“, farbig |
| `kartonaut_1.svg` | Missionsabzeichen des Erstflugs „KARTONAUT 1 · ERSTFLUG“ |
| `kartonaut_patch_mono.svg` | einfarbig schwarz, für Aufkleber, Laser, Stempel |

Die Dateien kommen aus `hardware/mainboard/kicad/logo.py`, derselben Geometrie, die auch im
Bestückungsdruck der Platine steht. Die Schrift ist KiCads Strichschrift als Polygone, die SVGs
brauchen also keine Schriftart. Neu erzeugen (KiCad-Python):

```bash
"$LOCALAPPDATA/Programs/KiCad/10.0/bin/python.exe" hardware/mainboard/kicad/logo.py
```

Farben: Tinte `#0f1c2e`, Flamme `#e8542a`. Für einen weiteren Flug `write_svg(..., "KARTONAUT 2", "...")`.
Spitzname für eine spätere eigene Nutzlast: Papputnik.
