#include "CalStore.h"
#include <Arduino.h>
#include <EEPROM.h>

namespace cal {

Check load(CalData& out) {
  CalData d;
  EEPROM.get(EEPROM_OFFSET, d);
  const Check c = check(d);
  out = c == Check::OK ? d : defaults();
  return c;
}

bool save(CalData& d) {
  d.saved_count++;
  seal(d);
  EEPROM.put(EEPROM_OFFSET, d);          // schreibt nur geänderte Bytes
  CalData back;
  EEPROM.get(EEPROM_OFFSET, back);
  return memcmp(&back, &d, sizeof d) == 0;
}

void erase() {
  const uint32_t zero = 0;
  EEPROM.put(EEPROM_OFFSET + int(offsetof(CalData, magic)), zero);
}

}  // namespace cal
