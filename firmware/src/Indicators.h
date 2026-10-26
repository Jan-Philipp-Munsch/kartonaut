#pragma once
#include "Config.h"
#include <FastLED.h>

void Indicators_setup();
void Indicate_success();            // drei kurze grüne Blitze mit Ton (blockiert 300 ms)
void Indicate_waiting();            // orange, Dauerton an (Aufruf im Setup)
void Indicate_warn();               // 20 s rotes Blinken (blockiert)
void Indicate_color(uint8_t r, uint8_t g, uint8_t b);   // nicht blockierend, Flugzustand
void Indicate_beep(uint16_t ms);    // blockierender Piep
