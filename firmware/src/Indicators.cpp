#include "Indicators.h"
#include <Arduino.h>

#ifdef BOARD_REVB
static CRGB leds[2];
#else
static CRGB led1, led2;
#endif

static void setAll(const CRGB& c) {
#ifdef BOARD_REVB
  leds[0] = c; leds[1] = c;
#else
  led1 = c; led2 = c;
#endif
  if (!DARK) FastLED.show();
}

void Indicators_setup(){
  pinMode(PIN_BEEPER, OUTPUT);
#ifdef BOARD_REVB
  FastLED.addLeds<WS2812B, PIN_LED_DATA, GRB>(leds, 2);
#else
  FastLED.addLeds<WS2812B, PIN_LED1, GRB>(&led1, 1);
  FastLED.addLeds<WS2812B, PIN_LED2, GRB>(&led2, 1);
#endif
  FastLED.clear(true);
}

void Indicate_color(uint8_t r, uint8_t g, uint8_t b){ setAll(CRGB(r, g, b)); }

void Indicate_beep(uint16_t ms){
  if (SILENT) return;
  digitalWrite(PIN_BEEPER, HIGH);
  delay(ms);
  digitalWrite(PIN_BEEPER, LOW);
}

void Indicate_success(){
  for (int i=0; i<3; ++i){
    if (!SILENT) digitalWrite(PIN_BEEPER, HIGH);
    setAll(CRGB::Green);
    delay(50);
    digitalWrite(PIN_BEEPER, LOW);
    FastLED.clear(true);
    delay(50);
  }
}

void Indicate_waiting(){
  if (!SILENT) digitalWrite(PIN_BEEPER, HIGH);
  setAll(CRGB::Orange);
}

void Indicate_warn(){
  for (int i=0; i<40; ++i){
    digitalWrite(PIN_BEEPER, LOW);
    FastLED.clear(true);
    delay(250);
    if (i==39) break;
    if (!SILENT) digitalWrite(PIN_BEEPER, HIGH);
    setAll(CRGB::Red);
    delay(250);
  }
  digitalWrite(PIN_BEEPER, LOW);
  FastLED.clear(true);
}
