#pragma once
#include <Arduino.h>

// =====================================================================
//  Web – WLAN-Zugangspunkt, Webseite unter http://192.168.4.1 und
//  WebSocket /ws mit JSON (S4).
//
//  Handy -> Station:  {"cmd":"hb"}          Herzschlag, alle 250 ms
//                     {"cmd":"countdown"}   Countdown starten
//                     {"cmd":"abort"}       Abbruch (immer erlaubt)
//                     {"cmd":"calibrate"} | {"cmd":"ping"} | {"cmd":"pad_ready_query"}
//  Station -> Handy:  {"t":"st", ...}       Zustand und Telemetrie, 10 Hz
//                     {"t":"ev","msg":...}  Ereignis für das Protokollfenster
//
//  Der WebSocket läuft in einer eigenen Task (AsyncTCP). Eingehende
//  Kommandos landen deshalb in einer Warteschlange, die loop() abarbeitet.
// =====================================================================

namespace web {

void begin();
void update();                 // Kommandos abarbeiten, Zustand senden
void event(const char* msg);   // Ereignis an alle Handys
uint32_t clientCount();

} // namespace web
