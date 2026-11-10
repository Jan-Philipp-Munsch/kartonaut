#pragma once
// FlashLog.h – Flugschreiber im QSPI-Flash unter dem Teensy (W25Q128, 16 MB), zusätzlich zum SD-Log
//
// Warum: Was im Flash steht, bleibt ohne Strom erhalten und überlebt auch eine beim Aufprall
// herausgeflogene SD-Karte. Der Flash wird seitenweise (256 Byte) beschrieben; der Loop gibt
// höchstens einen Programmierbefehl je Takt ab (µs) und wartet nie auf den Chip (QspiFlash.h).
// Beim Aufprall fehlt so höchstens die zuletzt angefangene Seite.
//
// Ablauf:
//   * Start (SAFE): Steht noch ein nicht kopierter Flug im Flash, kommt er zuerst als LOGxxxxx.BIN
//     auf die SD-Karte (blockierend, vor dem Watchdog), dann wird der benutzte Bereich gelöscht
//     (64-KB-Blöcke, im Hintergrund, nur am Boden). Ohne SD-Karte bleibt der alte Flug stehen und
//     der Flugschreiber ist aus (USB 'f' kopiert, sobald eine Karte steckt).
//   * PAD_READY: Sitzung beginnt (Kopfseite), Datensätze mit 25 Hz (lange Wartezeit am Pad füllt den
//     Flash so nicht). Ab BOOST bis APOGEE 250 Hz, ab DESCENT 50 Hz. 16 MB reichen bei 250 Hz ~8 min.
//   * LANDED: Rest schreiben, Länge in die Kopfseite. Zurück nach SAFE ohne Start: Sitzung verwerfen.
//   * Neustart im Flug (Watchdog): Ende der Daten suchen und weiterschreiben.
//
// Aufbau im Flash: Seite 0 = Kopf (FlashHeader), ab Byte 256 die Datensätze wie in der SD-Datei
// (SDLogger.h, 136 Byte, Format 2) ohne Lücken. Die Kopie auf der Karte lässt sich deshalb wie jedes
// Log mit SDLogger_exportLatestCSVx() bzw. USB 'x' als CSV ausgeben.
#include <stdint.h>
#include "SDLogger.h"

struct FlashLogStats {
  bool     present = false;      // Flash erkannt
  uint32_t jedec = 0, size = 0;
  bool     session = false;      // Sitzung läuft
  uint32_t write_pos = 0;        // nächste freie Adresse
  uint32_t erased_to = 0;        // bis hier gelöscht
  uint32_t queued_pages = 0, max_queued = 0, dropped_records = 0;
  bool     old_flight_pending = false;   // alter Flug wartet auf die Kopie zur SD
};

// Start. resume = Neustart im Flug: Ende suchen und weiterschreiben, nichts kopieren oder löschen.
void FlashLog_setup(bool resume);
// Jeden Loop: höchstens eine Seite programmieren oder (erase_ok) einen Block löschen
void FlashLog_service(bool erase_ok);
// Sitzung beginnen (PAD_READY); wird nachgeholt, sobald Block 0 gelöscht ist
void FlashLog_startSession();
// Sitzung ohne Flug verwerfen (zurück nach SAFE): Bereich wird wieder gelöscht
void FlashLog_abortSession();
// Sitzung abschließen (LANDED): Rest schreiben, Länge eintragen
void FlashLog_finish();
// Datensatz anhängen (nur in einer Sitzung)
void FlashLog_log(const SDFrame& f);
// Alten bzw. letzten Flug auf die SD-Karte kopieren (blockierend, nur am Boden)
bool FlashLog_copyToSd();
void FlashLog_getStats(FlashLogStats& out);
