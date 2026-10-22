#pragma once
// Persist.h – Watchdog und Zustandsspeicher über einen Neustart hinweg (Plan §2 B5)
//
// Watchdog: WDOG1 des i.MX RT1062, Zeitüberschreitung in 0,5-s-Stufen. Einmal
// eingeschaltet lässt er sich nicht mehr abschalten; die Schleife füttert ihn
// einmal je Durchlauf. Hängt der Teensy (I²C-Blockade, Endlosschleife), startet
// er neu statt mit Servos auf Anschlag zu fallen.
//
// Zustandsspeicher: ein Block im DMAMEM (OCRAM), den der Startcode des Teensy
// nicht löscht. Beim Start prüft Persist_begin() Magic und CRC; passt beides und
// war der Neustart ein Watchdog-Reset, übernimmt main.cpp Flugzustand, Lage,
// Gyro-Bias, Bodendruck und gezündete Pyro-Kanäle statt wieder in SAFE zu
// beginnen. Ein Kaltstart (Hauptschalter) löscht den Block.
#include <Arduino.h>
#include "MathTypes.h"

// Trivialer Typ ohne Initialisierer: ein globales Objekt mit Konstruktor würde
// beim Start den DMAMEM-Block überschreiben. Lokale Instanzen mit {} anlegen
// und q[0] = 1 setzen.
struct PersistState {
  uint8_t  phase;                // KnPhase
  uint8_t  pyro_fired;           // Bitmaske
  uint8_t  calibrated;
  uint8_t  _pad;
  uint32_t t_since_liftoff_ms;   // 0 = nicht gestartet
  uint32_t t_saved_ms;           // millis() beim Speichern
  float    q[4];
  float    gyro_bias_dps[3];
  float    ground_pressure_pa;
  float    alt_offset_m;
  float    max_alt_m;
};

// true, wenn ein gültiger Block aus dem vorigen Lauf vorliegt (dann steht er in out)
bool     Persist_begin(PersistState& out);
void     Persist_save(const PersistState& s);
void     Persist_clear();
uint32_t Persist_bootCount();          // Neustarts seit dem Kaltstart
bool     Persist_wasWatchdogReset();   // Grund des letzten Neustarts
uint16_t Persist_resetReason();        // SRC_SRSR roh

void Watchdog_begin(float timeout_s);
void Watchdog_feed();
