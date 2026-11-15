#pragma once
// Board.h – Bausteine des Mainboards rev B1 für die Testkonsole
#include <Arduino.h>
#include <FastLED.h>
#include "BoardRevB.h"
#include "BusRevB.h"
#include "Imu.h"
#include "ImuAuto.h"
#include "FitRevB.h"
#include "BMP390.h"
#include "INA239.h"
#include "LIS3MDL.h"
#include "SHT40.h"
#include "ADXL375.h"
#include "CalStore.h"
#include "I2cRevB.h"

namespace rb = revb;

namespace board {

extern BusRevB    bus;
extern ImuDriver& imu;          // ImuAuto: LSM6DSV16X (rev B1) oder ICM-42688-P, nach WHO_AM_I
extern BMP390     baro;
extern BMP390     baro2;
extern INA239     ina;
extern LIS3MDL    mag;
extern SHT40      sht;
extern ADXL375    adxl;
extern CRGB       leds[rb::LED_COUNT_ONBOARD];
extern cal::CalData calib;      // geladene Kalibrierung (oder Standardwerte)
extern cal::Check   calib_check;

struct Status {
  bool imu = false, baro = false, baro2 = false, ina = false, mag = false, sht = false, adxl = false;
};
extern Status st;
extern rb::Fit fit;             // Bestückungsliste (FitRevB.h), zur Laufzeit mit "fit" änderbar

void safeOutputs();             // Pyro tief, DRV8833 schlafend, Servos ohne Puls, alle CS hoch
void begin();                   // Busse starten, bestückte Bausteine erkennen (keine Bewegung, kein Pyro)
void beginParts();              // nur die Bausteine laut fit neu erkennen (st), LoRa-Pins in Ruhe

float vbat1();                  // Spannungen über die Mux, kalibriert (adc_gain)
float vbat2();
float armV();
float pyroV(int ch);            // 0..3
float muxInputV(rb::Mux ch);
bool  have2S();                 // 2S-Zweig versorgt (VBAT2 > 6 V)
bool  armed();                  // ARM_SENSE scharf (> 5 V)

void setLeds(CRGB c);           // beide LEDs setzen und anzeigen
void beep(uint16_t ms);

// Servos: Pulsgrenzen je Kanal (Config.h-Fenster und Kalibrierung), Puls setzen, loslassen
void servoLimitsUs(int i, int& lo, int& hi);
void servoWriteUs(int i, int us);   // klemmt auf servoLimitsUs
void servoRelease(int i);
void servoReleaseAll();

}  // namespace board
