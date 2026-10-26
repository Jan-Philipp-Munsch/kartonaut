#pragma once
#include <Arduino.h>

// =====================================================================
//  Config.h – alle Zahlen, Pins und Schalter der Bodenstation
//
//  Die Module (Protocol, Radio, Igniter, Launch, Web) lesen ihre
//  Parameter ausschließlich von hier. Pinbelegung und Verdrahtung:
//  groundstation/Schaltung.md.
// =====================================================================

// ===== WLAN (S4) =====
constexpr const char* WIFI_SSID     = "MissionSpace-GS";
// WPA2 verlangt mindestens 8 Zeichen. Vor dem ersten Einsatz ändern.
constexpr const char* WIFI_PASSWORD = "scoutf-e12";
constexpr uint8_t     WIFI_CHANNEL  = 6;
constexpr uint8_t     WIFI_MAX_CLIENTS = 4;
// IP 192.168.4.1 ist der Standard des ESP32-Zugangspunkts.

// ===== Pins (ESP32-S3-DevKitC-1) =====
// ADC nur auf ADC1 (GPIO 1..10): ADC2 ist bei aktivem WLAN nicht nutzbar.
constexpr int PIN_ADC_LINE_NEG = 1;   // Zündleitung minus, Teiler 22k/6k8
constexpr int PIN_ADC_LINE_POS = 2;   // Zündleitung plus,  Teiler 22k/6k8
constexpr int PIN_ADC_VBAT     = 4;   // 3S-Akku,           Teiler 100k/27k
constexpr int PIN_KEY_SENSE    = 5;   // Schlüssel gedreht (Teiler 22k/7k5 nach dem Schlüsselschalter)
constexpr int PIN_ARM_SENSE    = 6;   // ARM ein (Teiler 22k/7k5 nach dem ARM-Schalter)
constexpr int PIN_START_BTN    = 7;   // Start-Taster gegen GND, interner Pull-up
constexpr int PIN_FIRE_GATE    = 9;   // MOSFET Zündkreis (100k Pull-down am Gate)
constexpr int PIN_BUZZER       = 10;  // Summer über NPN
constexpr int PIN_LED_CONT     = 11;  // grün: Durchgang
constexpr int PIN_LED_ARMED    = 12;  // rot: scharf / Countdown
constexpr int PIN_LED_LINK     = 13;  // blau: Telemetrie aktuell
constexpr int PIN_E22_AUX      = 14;
constexpr int PIN_E22_M0       = 15;
constexpr int PIN_E22_M1       = 16;
constexpr int PIN_E22_RXD      = 17;  // ESP-TX -> E22-RXD
constexpr int PIN_E22_TXD      = 18;  // ESP-RX <- E22-TXD

// ===== Analogmessung =====
constexpr float ADC_VREF_V       = 3.3f;   // nur zur Umrechnung, analogReadMilliVolts() ist kalibriert
constexpr float DIV_LINE         = (22.0f + 6.8f) / 6.8f;   // 4,24
constexpr float DIV_VBAT         = (100.0f + 27.0f) / 27.0f; // 4,70
// Durchgangsprüfung (Schaltung.md §3): Anzünder vorhanden -> Leitung minus
// SICHER ca. 2,0 V, SCHARF ca. Akkuspannung; offen -> 0 V.
constexpr float CONT_MIN_V       = 0.8f;   // Leitung minus darüber: Durchgang
// Leitung plus im SICHER-Zustand unter diesem Wert bei Leitung minus ~0:
// Leitung minus liegt an Masse (MOSFET durchlegiert oder Schluss nach GND).
constexpr float LINE_SHORT_V     = 0.5f;
constexpr float RELAY_CLOSED_V   = 8.0f;   // Leitung plus darüber: Relais zu
constexpr float VBAT_MIN_FIRE_V  = 10.5f;  // 3S unter 3,5 V/Zelle: kein Countdown
constexpr float VBAT_LOW_WARN_V  = 11.1f;

// ===== Funk (S3) =====
// E22-400T22S/-D, transparenter Modus. Register werden beim Start geprüft und
// nur bei Abweichung neu geschrieben (Radio.cpp).
constexpr uint32_t E22_UART_BAUD = 9600;
constexpr uint8_t  E22_ADDH      = 0x00;
constexpr uint8_t  E22_ADDL      = 0x00;
constexpr uint8_t  E22_NETID     = 0x00;
constexpr uint8_t  E22_CHANNEL   = 0x17;   // 410,125 MHz + 23 MHz = 433,125 MHz
// Luftrate: Code 0b010 = 2,4 kbit/s (S3), 0b100 = 9,6 kbit/s.
// ABWEICHUNG von S3, siehe README §6: 10 Hz × 33 Byte passen nicht in 2,4 kbit/s.
constexpr uint8_t  E22_AIR_RATE  = 0b100;
// Sendeleistung: 0b00 22 dBm, 0b01 17 dBm, 0b10 13 dBm, 0b11 10 dBm.
// 433-MHz-SRD in DE: höchstens 10 mW ERP. 10 dBm + ½λ-Antenne (2 dBi) liegt
// an der Grenze; 22 dBm nur mit Amateurfunkgenehmigung (README §6).
constexpr uint8_t  E22_POWER     = 0b11;

constexpr uint32_t CMD_RETRY_MS    = 300;  // Wiederholung, wenn keine Quittung kommt
constexpr uint8_t  CMD_RETRIES     = 4;
constexpr uint8_t  ABORT_RETRIES   = 10;
constexpr uint32_t CMD_SLOT_WAIT_MS = 150; // nach Telemetrie senden, sonst spätestens nach dieser Zeit

// ===== Startsperre und Countdown (S3, S4) =====
constexpr uint32_t TLM_MAX_AGE_MS     = 1000;  // Bedingung 3
constexpr uint32_t COUNTDOWN_MS       = 10000;
constexpr uint32_t FIRE_PULSE_MS      = 1000;  // S2: mindestens 5 A für 1 s
constexpr uint32_t HANGFIRE_WAIT_MS   = 60000; // nach Fehlzündung: 60 s nicht an das Pad
constexpr uint32_t START_BTN_HOLD_MS  = 1000;  // Taster so lange halten, bis der Countdown startet
constexpr bool     START_BTN_DEADMAN  = true;  // Loslassen während des Countdowns = Abbruch
                                               // (nur wenn der Countdown am Taster gestartet wurde)
// Handy: Herzschlag alle 250 ms. Bleibt er während des Countdowns länger aus,
// bricht die Station ab. TCP allein meldet einen WLAN-Abriss erst nach Sekunden.
constexpr uint32_t PHONE_HEARTBEAT_TIMEOUT_MS = 1500;

// ===== Takt =====
constexpr uint32_t WS_PUSH_PERIOD_MS = 100;  // 10 Hz zum Handy
constexpr uint32_t ADC_PERIOD_MS     = 20;
