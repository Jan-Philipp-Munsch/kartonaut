#pragma once
// Tvc.h – Versuch E02: Servo-Soll -> Kardanwinkel auf dem Mainboard rev B1
//
// Fährt je TVC-Achse die Anregungsfolge aus Experiment E01 (Treppe, Sprünge,
// Wechselsprünge, zwei Chirps) und zeichnet mit 500 Hz das Kommando, die externe
// IMU auf dem Motorrohr (ICM-20948-Breakout an J_QWIIC) und die Platinen-IMU
// (Rumpf) auf. CSV auf USB-Serial im Format von servo_ident, damit
// simulation/scripts/ident_servo.py die Datei auswertet; die Rumpfzeilen stehen
// als "#body,..." dazwischen. Anleitung: docs/experiments/E02_TVC_Charakterisierung_revB1.md
#include "Proto.h"

// "tvc <unterbefehl> ...", siehe tvcHelp(); liefert das Ergebnis für END
Res tvcCommand(const char* a1, const char* a2, const char* rest);
void tvcHelp();
