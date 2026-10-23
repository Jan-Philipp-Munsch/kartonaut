#pragma once
// Proto.h – maschinenlesbares Zeilenformat der Testkonsole (USB-Serial, 115200 Bd)
//
// Jede Zeile beginnt mit einem Schlüsselwort; tools/bench_test.py wertet sie aus:
//   READY                          Konsole bereit, wartet auf Befehle
//   # <text>                       Kommentar für Menschen (Menü, Hinweise)
//   INFO <text>                    Zwischenwert oder Hinweis, nicht bewertet
//   TEST <name> OK|FEHL|SKIP <detail>
//   CAL <name> <wert> [<wert> ...]  Kalibrierwert(e), Leerzeichen-getrennt, Punkt als Dezimalzeichen
//   ASK <text>                     Firmware wartet auf eine Zahl (leere Zeile = abbrechen)
//   WAIT <text>                    Firmware wartet auf Enter/"j" (weiter), "n" (nein), "q" (abbrechen)
//   CONFIRM <text>                 Firmware wartet auf das Wort JA (alles andere = abbrechen)
//   END <befehl> OK|FEHL|SKIP      Befehl beendet, Gesamtergebnis
//
// Namen sind ASCII ohne Leerzeichen. Alles, was nicht so beginnt, ist
// freier Text und wird vom Werkzeug nur protokolliert.
#include <Arduino.h>

enum class Res : uint8_t { OK, FEHL, SKIP };

namespace proto {

const char* name(Res r);
Res worst(Res a, Res b);       // FEHL schlägt SKIP schlägt OK

void ready();
void comment(const char* fmt, ...);
void info(const char* fmt, ...);
void test(const char* name, Res r, const char* fmt = "", ...);
void test(const char* name, bool ok, const char* fmt = "", ...);
void cal(const char* name, const char* fmt, ...);
void end(const char* cmd, Res r);

// Eine Zeile von der Konsole lesen (ohne Zeilenende), mit Zeitlimit in ms (0 = ohne).
// false bei Zeitablauf. Führende/abschließende Leerzeichen werden entfernt.
bool readLine(char* buf, size_t n, uint32_t timeout_ms = 0);
void flushInput();

// Geführte Schritte; -1 = abgebrochen (q oder leer bei ASK)
int  wait(const char* fmt, ...);                 // 1 = weiter/ja, 0 = nein, -1 = abbrechen
bool ask(float& value, const char* fmt, ...);    // false = abgebrochen
bool confirm(const char* fmt, ...);              // true nur bei "JA"

// Während langer Messungen: true, wenn der Nutzer "q" geschickt hat
bool abortRequested();

}  // namespace proto
