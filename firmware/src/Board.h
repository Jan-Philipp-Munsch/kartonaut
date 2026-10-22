#pragma once
// Board.h – Welche Hardware trägt die Flug-Firmware?
//
// Zwei Rückenden, gewählt über die Build-Variable BOARD_REVB (platformio.ini):
//
//   (ohne)       Breakouts am Teensy 4.1 mit Dupont-Kabeln: ICM-20948 (I²C, DMP),
//                BMP280, INA219, HC-12 an Serial8, zwei WS2812B an Pin 5 und 6.
//                Pins wie bisher in Config.h.
//   BOARD_REVB   Mainboard rev B: ICM-42688-P, BMP390, INA239 an SPI1 über den
//                CS-Decoder, Akkus/ARM/Pyro-Durchgang über die Analogmux, LoRa
//                E22 an Serial8, LED-Kette an Pin 5. Pins aus lib/mainboard_revb/
//                BoardRevB.h, geprüft durch firmware/tools/check_board_pins.py.
//
// Die Module (Sensors, Control, Indicators, Radio, Pyro-Ausgänge) lesen Pins
// nur von hier. Config.h hält Physik, Gewinne und Schalter, nichts Elektrisches.
#include <Arduino.h>
#include "MathTypes.h"

#ifdef BOARD_REVB
  #include "BoardRevB.h"
  #define BOARD_NAME "Mainboard rev B"

  constexpr int PIN_BEEPER      = revb::PIN_BUZZER;       // 37
  constexpr int PIN_LED_DATA    = revb::PIN_LED_DATA;     // 5, Kette LED1 -> LED2 -> J_LED
  constexpr int LED_COUNT       = revb::LED_COUNT_ONBOARD;
  constexpr int PIN_MOT_IN1     = revb::PIN_MOT_IN1;
  constexpr int PIN_MOT_IN2     = revb::PIN_MOT_IN2;
  constexpr int PIN_MOT_NSLEEP  = revb::PIN_MOT_NSLEEP;   // DRV8833, tief = Motor stromlos
  constexpr int PIN_MOT_FAULT   = revb::PIN_MOT_FAULT;
  constexpr int PIN_SERVO_YAW   = revb::PIN_SERVO_YAW;
  constexpr int PIN_SERVO_PITCH = revb::PIN_SERVO_PITCH;
  constexpr int PIN_SERVO_CHUTE = revb::PIN_SERVO_CHUTE;
  constexpr int PIN_SERVO_LEGS  = revb::PIN_SERVO_LEGS;
  constexpr int PIN_PYRO_FIRE[4] = {revb::PIN_PYRO1_FIRE, revb::PIN_PYRO2_FIRE, revb::PIN_PYRO3_FIRE, revb::PIN_PYRO4_FIRE};
  constexpr bool PYRO_FITTED[4]  = {revb::PYRO_FITTED[0], revb::PYRO_FITTED[1], revb::PYRO_FITTED[2], revb::PYRO_FITTED[3]};
  constexpr int PIN_PYRO1       = revb::PIN_PYRO1_FIRE;
  constexpr int PIN_CAM_TRIG    = revb::PIN_CAM_TRIG;
  constexpr int PIN_THROTTLE    = revb::PIN_PWM_EXT;      // ESC am Prüfstand (J_STACK PWM_EXT)
  constexpr int PIN_LORA_M0     = revb::PIN_LORA_M0;
  constexpr int PIN_LORA_M1     = revb::PIN_LORA_M1;
  constexpr int PIN_LORA_AUX    = revb::PIN_LORA_AUX;
  constexpr int PIN_LORA_NRST   = revb::PIN_LORA_NRST;
  constexpr bool HAS_ARM_SENSE   = true;    // Schlüsselschalter messbar
  constexpr bool HAS_PYRO_SENSE  = true;    // Durchgang je Kanal messbar
  constexpr bool HAS_VBAT_SENSE  = true;    // beide Akkus am ADC
  constexpr bool HAS_GPS         = true;    // J_GPS an Serial1
  constexpr bool RADIO_IS_E22    = true;

  // Drehung Chip -> Körpersystem (x, y quer, z Rollachse zur Spitze).
  // Spezifikation rev B §2: Chip X zeigt quer (+u), Chip Y zur Spitze (+v),
  // also Körper = (c.x, -c.z, c.y). TODO: nach der endgültigen Platzierung von
  // U4 (Bestückungsdruck-Pfeile) am Gerät prüfen: Spitze nach oben -> a.z ≈ +9,81.
  inline Vec3 chipToBody(const Vec3& c) { return Vec3(c.x, -c.z, c.y); }

#else
  #define BOARD_NAME "Breakouts (Teensy 4.1, I2C)"

  constexpr int PIN_BEEPER      = 13;
  constexpr int PIN_LED1        = 5;    // WS2812B, einzeln
  constexpr int PIN_LED2        = 6;
  constexpr int LED_COUNT       = 2;
  constexpr int PIN_MOT_IN1     = 2;    // Rollmotor, H-Brücke
  constexpr int PIN_MOT_IN2     = 3;
  constexpr int PIN_MOT_NSLEEP  = -1;   // nicht vorhanden
  constexpr int PIN_MOT_FAULT   = -1;
  constexpr int PIN_SERVO_YAW   = 28;   // TVC
  constexpr int PIN_SERVO_PITCH = 29;
  constexpr int PIN_SERVO_CHUTE = 9;    // Fallschirm (Servo, Reserve)
  constexpr int PIN_SERVO_LEGS  = -1;
  constexpr int PIN_PYRO_FIRE[4] = {23, 22, -1, -1};   // Low-Side-MOSFET-Modul an 23 (Pyro-Test)
  constexpr bool PYRO_FITTED[4]  = {true, false, false, false};
  constexpr int PIN_PYRO1       = 23;
  constexpr int PIN_CAM_TRIG    = -1;
  constexpr int PIN_THROTTLE    = 10;   // ESC am Prüfstand, freier PWM-Pin
  constexpr int PIN_LORA_M0     = -1;   // HC-12: SET-Pin nicht benutzt
  constexpr int PIN_LORA_M1     = -1;
  constexpr int PIN_LORA_AUX    = -1;
  constexpr int PIN_LORA_NRST   = -1;
  constexpr bool HAS_ARM_SENSE   = false;
  constexpr bool HAS_PYRO_SENSE  = false;
  constexpr bool HAS_VBAT_SENSE  = false;
  constexpr bool HAS_GPS         = false;
  constexpr bool RADIO_IS_E22    = false;

  constexpr uint32_t I2C_MAIN_SPEED_HZ = 400000;   // BMP280, INA219, ICM-20948
  // Lage des ICM-20948-Breakouts: wie bisher (Chipachsen = Körperachsen)
  inline Vec3 chipToBody(const Vec3& c) { return c; }
#endif

// Funk hängt bei beiden an Serial8 (RX8 = 34, TX8 = 35)
#define RADIO_SERIAL Serial8
#define GPS_SERIAL   Serial1
