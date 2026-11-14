#pragma once
// Calib.h – geführte Kalibrierungen; Ergebnis als CAL-Zeilen und in board::calib (RAM).
// "cal save" schreibt den Block mit Version und CRC ins EEPROM-Emulat.
#include "Proto.h"

Res calGyro(float seconds);
Res calAcc();
Res calMag(float seconds);
Res calAxes();
Res calBaro(float seconds);
Res calAdc(int channel);        // 0..7, -1 = alle sinnvollen (VBAT1, VBAT2, ARM)
Res calIna();
Res calServo(int i);
Res calSet(const char* args);   // "<name> <werte...>": Feld im RAM setzen (Werte vom PC), geprüft
void calShow();
Res calSave();
Res calLoad();
Res calDefaults();
Res calErase();
