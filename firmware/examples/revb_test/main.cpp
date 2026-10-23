// revb_test – Testkonsole und Kalibrierung des Mainboards rev B1
//
// Befehlsmenü über USB-Serial (115200 Bd). Jede Prüfung meldet eine Zeile
// "TEST <name> OK|FEHL|SKIP <detail>", jeder Kalibrierwert "CAL <name> <werte>",
// jeder Befehl endet mit "END <befehl> <ergebnis>" (Format: Proto.h).
// tools/bench_test.py stößt die Befehle nacheinander an und schreibt den Bericht.
//
// Versorgung: VIN des Teensy ist vom USB getrennt. Ohne 1S (J_BAT1 plus JP1
// oder Schalter an J_SW) läuft nichts; ohne 2S (XT30 plus JP2 oder Schalter)
// melden Servos, Motor, Pyro und INA239 "SKIP" statt zu scheitern.
//
// Sicherheit: Beim Start zuerst safeOutputs() (Pyro tief, DRV8833 schlafend,
// Servos ohne Puls, alle Chip-Selects hoch). Pyro nur nach "CONFIRM ... JA",
// nur bei scharfem ARM_SENSE, Puls höchstens 1 s, danach sofort tief.
// Servos nur im Fenster aus Config.h, Motor nur kurze Pulse mit nFAULT-Überwachung.
#include <Arduino.h>
// Direkt eingebunden, damit der PlatformIO-Dependency-Finder lib/mainboard_revb und
// lib/calstore findet: Header im Beispielordner (Board.h) löst er nicht auf.
#include "BoardRevB.h"
#include "CalStore.h"
#include "Board.h"
#include "Proto.h"
#include "Tests.h"
#include "Calib.h"
#include "Watchdog.h"
#include "Tvc.h"

using namespace board;

static void help() {
  proto::comment("Befehle (q bricht laufende Messungen ab):");
  proto::comment("  all            alle Prüfungen ohne Bewegung: mux imu baro mag sht adxl ina timing");
  proto::comment("  all full       dazu led buzzer cam servo 1..4 motor lora gps sd (mit Rückfragen)");
  proto::comment("  mux | imu | baro | mag | sht | adxl | ina | ina load");
  proto::comment("  led | buzzer | cam");
  proto::comment("  servo <1..4> [center|min|max|sweep|us <wert>]   (1 Yaw, 2 Pitch, 3 Chute, 4 Legs)");
  proto::comment("  motor          zwei kurze Pulse, nFAULT");
  proto::comment("  pyro <1..4> [ms]   NUR mit Lämpchen, fragt CONFIRM, höchstens 1000 ms");
  proto::comment("  lora | gps | sd | timing | watchdog | watchdog fire (Neustart!)");
  proto::comment("  cal gyro [s] | cal acc | cal mag [s] | cal axes | cal baro [s]");
  proto::comment("  cal adc [kanal] | cal ina | cal servo <1..4>");
  proto::comment("  cal show | cal save | cal load | cal defaults | cal erase");
  proto::comment("  tvc ...        Versuch E02 Servo -> Kardan (tvc help)");
  proto::comment("  status | help");
}

static void status() {
  proto::info("Bausteine: IMU %d Baro %d Baro2 %d INA %d Mag %d SHT %d ADXL %d", st.imu, st.baro, st.baro2, st.ina, st.mag, st.sht, st.adxl);
  proto::info("1S %.2f V, 2S %.2f V, ARM %.2f V, nFAULT %s, Kalibrierung %s, gültig 0x%02lX",
              vbat1(), vbat2(), armV(), digitalRead(rb::PIN_MOT_FAULT) ? "hoch" : "TIEF", cal::checkName(calib_check), (unsigned long)calib.valid);
}

static int argInt(const char* s, int def) { return (s && *s) ? atoi(s) : def; }
static float argFloat(const char* s, float def) { return (s && *s) ? strtof(s, nullptr) : def; }

static Res runAll(bool full) {
  Res r = Res::OK;
  r = proto::worst(r, testMux());
  r = proto::worst(r, testImu());
  r = proto::worst(r, testBaro());
  r = proto::worst(r, testMag());
  r = proto::worst(r, testSht());
  r = proto::worst(r, testAdxl());
  r = proto::worst(r, testIna());
  r = proto::worst(r, testTiming());
  if (!full) return r;
  r = proto::worst(r, testLeds());
  r = proto::worst(r, testBuzzer());
  r = proto::worst(r, testCam());
  for (int i = 0; i < 4; ++i) r = proto::worst(r, testServo(i, "center"));
  r = proto::worst(r, testMotor());
  r = proto::worst(r, testLora());
  r = proto::worst(r, testGps());
  r = proto::worst(r, testSd());
  return r;
}

// Befehlszeile ausführen; gibt END aus
static void execute(char* line) {
  if (line[0] == 0) return;
  char cmdcopy[64];
  strncpy(cmdcopy, line, sizeof cmdcopy - 1);
  cmdcopy[sizeof cmdcopy - 1] = 0;
  char* a0 = strtok(line, " ");
  char* a1 = strtok(nullptr, " ");
  char* a2 = strtok(nullptr, " ");
  Res r = Res::OK;

  if (!strcmp(a0, "help") || !strcmp(a0, "?")) { help(); return; }
  else if (!strcmp(a0, "tvc") && a1 && !strcmp(a1, "help")) { tvcHelp(); return; }
  else if (!strcmp(a0, "status"))  { status(); return; }
  else if (!strcmp(a0, "all"))     r = runAll(a1 && !strcmp(a1, "full"));
  else if (!strcmp(a0, "mux"))     r = testMux();
  else if (!strcmp(a0, "imu"))     r = testImu();
  else if (!strcmp(a0, "baro"))    r = testBaro();
  else if (!strcmp(a0, "mag"))     r = testMag();
  else if (!strcmp(a0, "sht"))     r = testSht();
  else if (!strcmp(a0, "adxl"))    r = testAdxl();
  else if (!strcmp(a0, "ina"))     r = (a1 && !strcmp(a1, "load")) ? testInaLoad() : testIna();
  else if (!strcmp(a0, "led"))     r = testLeds();
  else if (!strcmp(a0, "buzzer"))  r = testBuzzer();
  else if (!strcmp(a0, "cam"))     r = testCam();
  else if (!strcmp(a0, "servo")) {
    char mode[16] = "center";
    if (a1 && !strcmp(a1, "all")) {
      for (int i = 0; i < 4; ++i) r = proto::worst(r, testServo(i, a2 ? a2 : "center"));
    } else {
      if (a2) { if (!strcmp(a2, "us")) snprintf(mode, sizeof mode, "us%d", argInt(strtok(nullptr, " "), 1500)); else strncpy(mode, a2, sizeof mode - 1); }
      r = testServo(argInt(a1, 0) - 1, mode);
    }
  }
  else if (!strcmp(a0, "motor"))   r = testMotor();
  else if (!strcmp(a0, "pyro"))    r = testPyro(argInt(a1, 0) - 1, argInt(a2, 500));
  else if (!strcmp(a0, "lora"))    r = testLora();
  else if (!strcmp(a0, "gps"))     r = testGps();
  else if (!strcmp(a0, "sd"))      r = testSd();
  else if (!strcmp(a0, "timing"))  r = testTiming();
  else if (!strcmp(a0, "watchdog")) r = testWatchdog(a1 && !strcmp(a1, "fire"));
  else if (!strcmp(a0, "tvc")) {
    // Rest der Zeile hinter dem Unterbefehl, aus der unzerlegten Kopie (center/window/note brauchen mehrere Wörter)
    const char* rest = cmdcopy + 3;
    while (*rest == ' ') ++rest;
    while (*rest && *rest != ' ') ++rest;
    while (*rest == ' ') ++rest;
    r = tvcCommand(a1, a2, rest);
  }
  else if (!strcmp(a0, "cal")) {
    if (!a1)                          { calShow(); return; }
    else if (!strcmp(a1, "gyro"))     r = calGyro(argFloat(a2, 10.0f));
    else if (!strcmp(a1, "acc"))      r = calAcc();
    else if (!strcmp(a1, "mag"))      r = calMag(argFloat(a2, 40.0f));
    else if (!strcmp(a1, "axes"))     r = calAxes();
    else if (!strcmp(a1, "baro"))     r = calBaro(argFloat(a2, 20.0f));
    else if (!strcmp(a1, "adc"))      r = calAdc(argInt(a2, -1));
    else if (!strcmp(a1, "ina"))      r = calIna();
    else if (!strcmp(a1, "servo"))    r = calServo(argInt(a2, 0) - 1);
    else if (!strcmp(a1, "show"))     { calShow(); return; }
    else if (!strcmp(a1, "save"))     r = calSave();
    else if (!strcmp(a1, "load"))     r = calLoad();
    else if (!strcmp(a1, "defaults")) r = calDefaults();
    else if (!strcmp(a1, "erase"))    r = calErase();
    else { proto::info("unbekannt: cal %s", a1); r = Res::FEHL; }
  }
  else { proto::info("unbekannter Befehl: %s (help)", a0); r = Res::FEHL; }

  // nach jedem Befehl: sichere Ausgänge (Servos loslassen, Motor schlafend, Pyro tief)
  servoReleaseAll();
  digitalWrite(rb::PIN_MOT_NSLEEP, LOW);
  for (uint8_t p : rb::PYRO_FIRE_PINS) digitalWrite(p, LOW);
  proto::end(cmdcopy, r);
}

void setup() {
  safeOutputs();
  const ResetCause rc = wdResetCause();
  board::begin();
  setLeds(CRGB(0, 0, 30));

  Serial.begin(115200);
  const uint32_t t0 = millis();
  while (!Serial && millis() - t0 < 4000) {}

  Serial.println();
  proto::comment("Kartonaut Mainboard rev B1: Testkonsole (revb_test)");
  proto::info("reset_cause %s", wdResetCauseName(rc));
  if (rc == ResetCause::WATCHDOG) proto::test("watchdog_reset", true, "Neustart durch den Watchdog erkannt");
  proto::info("kalibrierung %s%s", cal::checkName(calib_check), calib_check == cal::Check::OK ? "" : " -> Standardwerte");
  if (calib_check != cal::Check::OK && calib_check != cal::Check::EMPTY) proto::info("WARNUNG: Kalibrierblock unbrauchbar (%s)", cal::checkName(calib_check));
  status();
  help();
  setLeds(st.imu && st.baro ? CRGB(0, 30, 0) : CRGB(30, 10, 0));
  proto::ready();
}

void loop() {
  static char line[96];
  if (!proto::readLine(line, sizeof line, 50)) return;
  if (line[0] == 0) { proto::ready(); return; }
  execute(line);
  proto::ready();
}
