#include "Persist.h"
#include "Crc16.h"
#include <string.h>

namespace {
constexpr uint32_t MAGIC = 0x4B415254;   // "KART"

struct Block {
  uint32_t     magic;
  uint32_t     boot_count;
  PersistState state;
  uint16_t     crc;
  uint16_t     _pad;
};

// DMAMEM liegt im OCRAM und wird vom Startcode nicht initialisiert
DMAMEM Block block;
bool     wdt_reset = false;
uint16_t reset_reason = 0;

uint16_t blockCrc(const Block& b) {
  return crc16_ccitt(reinterpret_cast<const uint8_t*>(&b.state), sizeof b.state,
                     crc16_ccitt(reinterpret_cast<const uint8_t*>(&b.boot_count), sizeof b.boot_count));
}
}  // namespace

bool Persist_begin(PersistState& out) {
#if defined(__IMXRT1062__)
  reset_reason = uint16_t(SRC_SRSR);
  // Bit 4: WDOG1-Reset, Bit 3: IPP_USER (Reset-Pin), Bit 0: Einschalten (IPP_RESET_B)
  wdt_reset = (reset_reason & (1u << 4)) != 0;
  SRC_SRSR = reset_reason;   // Bits werden durch Schreiben einer 1 gelöscht
#endif
  const bool valid = block.magic == MAGIC && block.crc == blockCrc(block);
  if (valid) {
    block.boot_count++;
    out = block.state;
  } else {
    memset(&block, 0, sizeof block);
    block.magic = MAGIC;
    block.state.q[0] = 1.0f;
  }
  block.crc = blockCrc(block);
  return valid;
}

void Persist_save(const PersistState& s) {
  block.magic = MAGIC;
  block.state = s;
  block.crc = blockCrc(block);
}

void Persist_clear() {
  const uint32_t boots = block.boot_count;
  memset(&block, 0, sizeof block);
  block.magic = MAGIC;
  block.boot_count = boots;
  block.state.q[0] = 1.0f;
  block.crc = blockCrc(block);
}

uint32_t Persist_bootCount() { return block.boot_count; }
bool     Persist_wasWatchdogReset() { return wdt_reset; }
uint16_t Persist_resetReason() { return reset_reason; }

void Watchdog_begin(float timeout_s) {
#if defined(__IMXRT1062__)
  // WT in 0,5-s-Stufen: Zeit = (WT + 1) · 0,5 s, 0..255
  int wt = int(timeout_s * 2.0f + 0.5f) - 1;
  if (wt < 0) wt = 0;
  if (wt > 255) wt = 255;
  WDOG1_WMCR = 0;                         // Power-Down-Zähler aus (nur einmal schreibbar)
  WDOG1_WCR = WDOG_WCR_WT(wt) | WDOG_WCR_WDE | WDOG_WCR_SRS | WDOG_WCR_WDA | WDOG_WCR_WDZST;
  Watchdog_feed();
#else
  (void)timeout_s;
#endif
}

void Watchdog_feed() {
#if defined(__IMXRT1062__)
  WDOG1_WSR = 0x5555;
  WDOG1_WSR = 0xAAAA;
#endif
}
