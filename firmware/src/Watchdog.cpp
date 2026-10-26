#include "Watchdog.h"
#include <Arduino.h>

static ResetCause cause = ResetCause::OTHER;
static bool cause_read = false;

ResetCause Watchdog_resetCause() {
  if (!cause_read) {
    const uint32_t srsr = SRC_SRSR;
    if (srsr & (SRC_SRSR_WDOG3_RST_B | SRC_SRSR_WDOG_RST_B)) cause = ResetCause::WATCHDOG;
    else if (srsr & SRC_SRSR_IPP_RESET_B)                    cause = ResetCause::POWER_ON;
    else if (srsr & (SRC_SRSR_JTAG_SW_RST | SRC_SRSR_LOCKUP_SYSRESETREQ)) cause = ResetCause::SOFTWARE;
    else cause = ResetCause::OTHER;
    SRC_SRSR = srsr;        // write-1-to-clear
    cause_read = true;
  }
  return cause;
}

const char* resetCauseName(ResetCause c) {
  switch (c) {
    case ResetCause::POWER_ON: return "Einschalten";
    case ResetCause::WATCHDOG: return "Watchdog";
    case ResetCause::SOFTWARE: return "Software";
    default: return "andere";
  }
}

void Watchdog_begin(uint32_t timeout_ms) {
  Watchdog_resetCause();
  uint32_t ticks = (timeout_ms * 128UL + 999UL) / 1000UL;   // 128 Hz
  if (ticks < 2) ticks = 2;
  if (ticks > 0xFFFF) ticks = 0xFFFF;
  __disable_irq();
  WDOG3_CNT = 0xD928C520;                 // Entsperren (innerhalb von 255 Bustakten konfigurieren)
  WDOG3_TOVAL = ticks;
  WDOG3_CS = WDOG_CS_EN | WDOG_CS_CLK(1) | WDOG_CS_PRES | WDOG_CS_CMD32EN | WDOG_CS_UPDATE;
  __enable_irq();
}

void Watchdog_feed() {
  __disable_irq();
  WDOG3_CNT = 0xB480A602;                 // Refresh-Sequenz (CMD32EN)
  __enable_irq();
}
