#pragma once
// Secrets.example.h – Vorlage für den Startschlüssel (Plan Bordzündung 27.10.2026, §3.3)
//
// Kopieren nach src/Secrets.h (steht in .gitignore) und 16 eigene Zufallsbytes eintragen, z. B. mit
//   python tools/ground/launch.py --new-key
// Derselbe Schlüssel gehört hexadezimal in tools/ground/secrets.json ("key"). Ein Schlüssel aus
// lauter Nullen gilt als fehlend: die Rakete verweigert ARM.
#include <stdint.h>

constexpr uint8_t LAUNCH_KEY[16] = {
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
};
