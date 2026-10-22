#pragma once
// Watchdog.h – RTWDOG (WDOG3) des i.MX RT1062 (Plan 22.10.2026, B5)
//
// Startet den Teensy neu, wenn die Schleife WDT_TIMEOUT_MS lang nicht Watchdog_feed()
// aufruft. Takt LPO 32,768 kHz / 256 = 128 Hz, also 7,8 ms Auflösung. Dazu die
// Reset-Ursache aus SRC_SRSR, damit main.cpp einen Neustart im Flug erkennt und den
// Zustandsspeicher benutzt.
#include <stdint.h>

enum class ResetCause : uint8_t { POWER_ON = 0, WATCHDOG = 1, SOFTWARE = 2, OTHER = 3 };

void       Watchdog_begin(uint32_t timeout_ms);
void       Watchdog_feed();
ResetCause Watchdog_resetCause();      // einmal nach dem Start lesen (löscht das Register)
const char* resetCauseName(ResetCause c);
