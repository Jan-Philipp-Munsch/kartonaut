#pragma once
// Tests.h – ein Befehl je Funktion; jeder gibt TEST-Zeilen aus und das Gesamtergebnis zurück
#include "Proto.h"

Res testMux();
Res testImu();
Res testBaro();
Res testMag();
Res testSht();
Res testAdxl();
Res testIna();
Res testInaLoad();          // Strom unter Last, geführt
Res testLeds();             // rot, grün, blau, weiß, Nutzer bestätigt
Res testBuzzer();
Res testCam();
Res testServo(int i, const char* mode);   // mode: center | min | max | sweep | us <wert>
Res testMotor();            // kurze Pulse in beide Richtungen, nFAULT
Res testPyro(int ch, int pulse_ms);       // nur mit Lämpchen, nach CONFIRM
Res testLora();             // Parameter lesen, Ping zur Bodenstation
Res testGps();
Res testSd();
Res testTiming();
Res testWatchdog(bool fire);
