#pragma once
// CalStore.h – Ablage der Kalibrierwerte im EEPROM-Emulat des Teensy 4.1
//
// Der Block liegt ab Adresse 0 (4284 Byte stehen zur Verfügung, der Block
// braucht gut 250). load() liefert immer brauchbare Werte: bei leerem oder
// beschädigtem Speicher die Standardwerte, und meldet das als Check.
#include "CalData.h"

namespace cal {

constexpr int EEPROM_OFFSET = 0;

// Liest den Block; bei Fehler Standardwerte in `out`. Rückgabe: Befund.
Check load(CalData& out);

// Versiegelt (Version, CRC, saved_count++) und schreibt den Block; liest
// zur Kontrolle zurück. false, wenn das Zurücklesen nicht stimmt.
bool save(CalData& d);

// Magic löschen: der nächste load() liefert Standardwerte (EMPTY)
void erase();

}  // namespace cal
