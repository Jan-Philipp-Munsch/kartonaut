#pragma once
// StateStore.h – Ablage des SavedState in nicht gelöschtem RAM (DMAMEM) und Rückgabe nach
// einem Neustart. Reine Teile (Packen, CRC) in StateMemory.h.
#include "StateMemory.h"

void  StateStore_begin();                         // einmal nach dem Start
bool  StateStore_restore(SavedState& out);        // true, wenn ein gültiger Block vorlag
void  StateStore_save(const SavedState& s);       // CRC wird gesetzt
void  StateStore_clear();                         // nach LANDED / beim Scharfschalten auf dem Pad
