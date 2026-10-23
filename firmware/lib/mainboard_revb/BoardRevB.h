#pragma once
#include <Arduino.h>

// =====================================================================
//  BoardRevB.h – Pinbelegung und Bauteilwerte des Mainboards rev B1
//
//  Quelle: hardware/mainboard/kicad/circuit.py auf dem Branch claude/rev-b1
//  (TEENSY, U12 74HC138, U13 74HC4051, Teiler, Shunt, I²C-Sensoren vom
//  23.10.2026). Platine fertig geroutet, noch nicht gefertigt. Der
//  Kommentar hinter jeder Pin-Konstante ist der Netzname in circuit.py;
//  firmware/tools/check_board_pins.py vergleicht beides, bevor jemand
//  flasht. Gegenüber rev B sind die Pins unverändert; neu sind die drei
//  I²C-Bausteine (LIS3MDL, SHT40, ADXL375 als DNP) und die Schiene 3V3_EXP.
//
//  Die Flug-Firmware in src/ läuft noch auf den Breakouts (Config.h).
//  Diese Datei wird erst dort eingebunden, wenn die Platine da ist.
// =====================================================================

namespace revb {

// ===== Teensy-Pins =====
constexpr uint8_t PIN_GPS_RX      = 0;    // GPS_TX   (Serial1, Modul sendet)
constexpr uint8_t PIN_GPS_TX      = 1;    // GPS_RX
constexpr uint8_t PIN_MOT_IN1     = 2;    // MOT_IN1  DRV8833, Rollmotor
constexpr uint8_t PIN_MOT_IN2     = 3;    // MOT_IN2
constexpr uint8_t PIN_IMU_INT     = 4;    // IMU_INT  ICM-42688-P INT1, Daten bereit
constexpr uint8_t PIN_LED_DATA    = 5;    // LED_DATA WS2812B-Kette LED1 -> LED2 -> J_LED
constexpr uint8_t PIN_LORA_NRST   = 6;    // LORA_NRST Open-Drain, 10 k nach 3V3_RF
constexpr uint8_t PIN_CAM_TRIG    = 7;    // CAM_TRIG
constexpr uint8_t PIN_MOT_FAULT   = 8;    // MOT_FAULT DRV8833 nFAULT, Open-Drain
constexpr uint8_t PIN_SERVO_CHUTE = 9;    // SERVO_CHUTE J_SERVO3 an VSERVO
constexpr uint8_t PIN_SERVO_LEGS  = 10;   // SERVO_LEGS  J_SERVO4 an VSERVO
constexpr uint8_t PIN_MOT_NSLEEP  = 11;   // MOT_NSLEEP DRV8833, tief = Motor stromlos
constexpr uint8_t PIN_PYRO3_FIRE  = 12;   // PYRO3_FIRE (Kanal DNP)
constexpr uint8_t PIN_PWM_EXT     = 13;   // PWM_EXT  J_STACK
constexpr uint8_t PIN_PYRO4_FIRE  = 14;   // PYRO4_FIRE (Kanal DNP)
constexpr uint8_t PIN_NRST_EXT    = 15;   // NRST_EXT J_STACK
constexpr uint8_t PIN_IRQ_EXT     = 17;   // IRQ_EXT  J_STACK
constexpr uint8_t PIN_SDA         = 18;   // SDA      Wire: LIS3MDL, SHT40, ADXL375 (DNP), J_QWIIC
constexpr uint8_t PIN_SCL         = 19;   // SCL
constexpr uint8_t PIN_EXT_TX      = 20;   // EXT_TX   Serial5 auf J_STACK
constexpr uint8_t PIN_EXT_RX      = 21;   // EXT_RX
constexpr uint8_t PIN_PYRO2_FIRE  = 22;   // PYRO2_FIRE
constexpr uint8_t PIN_PYRO1_FIRE  = 23;   // PYRO1_FIRE
constexpr uint8_t PIN_MUX_OUT     = 24;   // MUX_OUT  74HC4051 Z an A10
constexpr uint8_t PIN_SEL1        = 25;   // SEL1     74HC138 A1, 74HC4051 S1
constexpr uint8_t PIN_SPI1_MOSI   = 26;   // SPI1_MOSI
constexpr uint8_t PIN_SPI1_SCK    = 27;   // SPI1_SCK
constexpr uint8_t PIN_SERVO_YAW   = 28;   // SERVO_YAW   J_SERVO1
constexpr uint8_t PIN_SERVO_PITCH = 29;   // SERVO_PITCH J_SERVO2
constexpr uint8_t PIN_SEL2        = 30;   // SEL2
constexpr uint8_t PIN_CS_EN       = 31;   // CS_EN    74HC138 /E1, 10 k nach 3V3 (Boot: alle CS hoch)
constexpr uint8_t PIN_LORA_M1     = 32;   // LORA_M1
constexpr uint8_t PIN_LORA_M0     = 33;   // LORA_M0
constexpr uint8_t PIN_LORA_RX     = 34;   // LORA_TXD (Serial8, Modul sendet)
constexpr uint8_t PIN_LORA_TX     = 35;   // LORA_RXD
constexpr uint8_t PIN_LORA_AUX    = 36;   // LORA_AUX
constexpr uint8_t PIN_BUZZER      = 37;   // BUZZER
constexpr uint8_t PIN_SEL0        = 38;   // SEL0
constexpr uint8_t PIN_SPI1_MISO   = 39;   // SPI1_MISO  Achtung: SPI1-MISO ist ab Werk Pin 1 (GPS)
// Frei: 16, 40, 41

constexpr uint8_t PYRO_FIRE_PINS[4] = {PIN_PYRO1_FIRE, PIN_PYRO2_FIRE, PIN_PYRO3_FIRE, PIN_PYRO4_FIRE};
constexpr bool    PYRO_FITTED[4]    = {true, true, false, false};   // 3/4 sind DNP (E5)

// ===== SPI-Chip-Selects über den 74HC138 (Y0..Y7 = SEL2..0) =====
enum class Cs : uint8_t {
  IMU   = 0,   // CS_IMU
  BARO  = 1,   // CS_BARO
  BARO2 = 2,   // CS_BARO2 (DNP)
  INA   = 3,   // CS_INA
  EXT0  = 4,   // CS_EXT0  J_STACK
  EXT1  = 5,   // CS_EXT1
  EXT2  = 6,   // CS_EXT2
  NONE  = 7,   // Y7 offen
};

// ===== Analogkanäle über den 74HC4051 (dieselben Select-Leitungen) =====
enum class Mux : uint8_t {
  PYRO1 = 0,   // PYRO1_SENSE
  PYRO2 = 1,   // PYRO2_SENSE
  PYRO3 = 2,   // PYRO3_SENSE
  PYRO4 = 3,   // PYRO4_SENSE
  VBAT1 = 4,   // VBAT1_SENSE 1S, vor dem Lastschalter
  VBAT2 = 5,   // VBAT2_SENSE 2S, vor dem Lastschalter
  ARM   = 6,   // ARM_SENSE   VBAT_ARMED hinter dem Schlüsselschalter
  GND   = 7,   // GND (Nullpunkt des ADC)
};

// ===== I²C-Bausteine an Wire (SDA 18, SCL 19, 4,7 k nach 3V3), rev B1 =====
constexpr uint8_t I2C_ADDR_LIS3MDL = 0x1E;   // U16 Magnetometer, SA1 hoch
constexpr uint8_t I2C_ADDR_SHT40   = 0x44;   // U18 Feuchte und Temperatur
constexpr uint8_t I2C_ADDR_ADXL375 = 0x53;   // U17 ±200 g, ALT ADDRESS tief; DNP
constexpr bool    ADXL375_FITTED   = false;  // Footprint vorgesehen, nicht bestückt (23.10.)
constexpr bool    BARO2_FITTED     = false;  // U15, zweites BMP390 (C2), DNP
constexpr uint32_t I2C_SPEED_HZ    = 400000;

// ===== Bauteilwerte =====
constexpr float ADC_VREF_V      = 3.3f;
constexpr float DIVIDER_RATIO   = (100.0f + 33.0f) / 33.0f;   // 100 k / 33 k, Vollausschlag 13,3 V
constexpr float INA_SHUNT_OHM   = 0.020f;                     // Kelvin-Shunt 2S-Pfad
constexpr float INA_MAX_CURRENT_A = 8.0f;                     // ±163,84 mV / 20 mΩ = 8,19 A
constexpr int   LED_COUNT_ONBOARD = 2;                        // LED1, LED2; J_LED hängt dahinter

// ===== Testpunkte rev B1 (Versorgung, gegen GND zu messen) =====
// VBAT_PROT, VSYS_IN, 5V_SYS, VSERVO, 3V3_RF, 3V3_EXP, GND. VSYS_IN und die
// 5-V-/3,3-V-Schienen stehen nur bei versorgtem 1S-Zweig (J_BAT1 plus JP1 oder
// Schalter an J_SW), VBAT_PROT und VSERVO nur bei versorgtem 2S-Zweig (XT30
// plus JP2 oder Schalter). VIN des Teensy ist vom USB getrennt: ohne 1S läuft
// der Teensy nicht, USB liefert dann nur die Daten.

}  // namespace revb
