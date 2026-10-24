#pragma once
// Watchdog.h – WDOG3 (RTWDOG) des i.MX RT1062 und die Ursache des letzten Neustarts
#include <Arduino.h>

enum class ResetCause { POWER_ON, WATCHDOG, SOFTWARE, OTHER };

ResetCause  wdResetCause();            // liest SRC_SRSR einmal und löscht es
const char* wdResetCauseName(ResetCause c);
void        wdBegin(uint32_t timeout_ms);   // scharf; danach regelmäßig wdFeed()
void        wdFeed();
void        wdEnd();                       // wieder aus (möglich, weil UPDATE gesetzt ist)
