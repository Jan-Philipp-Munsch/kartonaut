#include "StateMemory.h"
#include "Crc16.h"
#include <string.h>

void savedStateSeal(SavedState& s) {
  s.magic = SAVED_MAGIC;
  s.version = SAVED_VERSION;
  s.crc = crc16_ccitt(reinterpret_cast<const uint8_t*>(&s), sizeof(SavedState) - sizeof(uint16_t));
}

bool savedStateValid(const SavedState& s) {
  if (s.magic != SAVED_MAGIC || s.version != SAVED_VERSION) return false;
  return s.crc == crc16_ccitt(reinterpret_cast<const uint8_t*>(&s), sizeof(SavedState) - sizeof(uint16_t));
}
