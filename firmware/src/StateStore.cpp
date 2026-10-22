#include "StateStore.h"
#include <Arduino.h>
#include <string.h>

// .dmabuffers (OCRAM) wird von startup.c nicht genullt; Inhalt überlebt den Watchdog-Reset.
DMAMEM static SavedState saved_block __attribute__((aligned(32)));
static SavedState shadow;

void StateStore_begin() {
  memcpy(&shadow, &saved_block, sizeof shadow);     // vor dem ersten Schreiben sichern
}

bool StateStore_restore(SavedState& out) {
  if (!savedStateValid(shadow)) return false;
  out = shadow;
  return true;
}

void StateStore_save(const SavedState& s) {
  SavedState tmp = s;
  savedStateSeal(tmp);
  memcpy(&saved_block, &tmp, sizeof tmp);
  arm_dcache_flush_delete(&saved_block, sizeof saved_block);
}

void StateStore_clear() {
  memset(&saved_block, 0, sizeof saved_block);
  arm_dcache_flush_delete(&saved_block, sizeof saved_block);
  memset(&shadow, 0, sizeof shadow);
}
