#!/usr/bin/env python3
"""Startet die Werkbank (grafische Oberfläche für das Mainboard rev B1), egal aus welchem Ordner.

    python firmware/tools/werkbank.py            # Teensy suchen, Oberfläche im Browser öffnen
    python firmware/tools/werkbank.py --sim      # ohne Hardware: simulierte Platine
    python firmware/tools/werkbank.py --port COM7

Dasselbe wie `python -m bench_gui` im Ordner firmware/tools. Beschreibung: bench_gui/README.md
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bench_gui.__main__ import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
