#include "Indicators.h"
#include <FastLED.h>

static CRGB leds[LED_COUNT];

static void show() { if (!DARK) FastLED.show(); }
static void beep(bool on) { digitalWrite(PIN_BEEPER, (on && !SILENT) ? HIGH : LOW); }

void Indicators_setup() {
  pinMode(PIN_BEEPER, OUTPUT);
  beep(false);
#ifdef BOARD_REVB
  FastLED.addLeds<WS2812B, PIN_LED_DATA, GRB>(leds, LED_COUNT);
#else
  FastLED.addLeds<WS2812B, PIN_LED1, GRB>(&leds[0], 1);
  FastLED.addLeds<WS2812B, PIN_LED2, GRB>(&leds[1], 1);
#endif
  FastLED.clear(true);
}

void Indicators_off() {
  beep(false);
  FastLED.clear(true);
}

void Indicate_success() {
  for (int i = 0; i < 4; ++i) {
    beep(false);
    FastLED.clear(true);
    delay(50);
    if (i == 3) break;
    beep(true);
    fill_solid(leds, LED_COUNT, CRGB::Green);
    show();
    delay(50);
  }
  Indicators_off();
}

void Indicate_waiting() {
  beep(true);
  fill_solid(leds, LED_COUNT, CRGB::Orange);
  show();
}

void Indicate_warn() {
  for (int i = 0; i < 40; ++i) {
    beep(false);
    FastLED.clear(true);
    delay(250);
    if (i == 39) break;
    beep(true);
    fill_solid(leds, LED_COUNT, CRGB::Red);
    show();
    delay(250);
  }
  Indicators_off();
}

void Indicators_update(const IndicatorInputs& in, uint32_t now_ms) {
  static uint32_t last_ms = 0;
  if (now_ms - last_ms < 20) return;     // 50 Hz reicht, FastLED.show() kostet ca. 60 µs je Pixel
  last_ms = now_ms;

  const uint32_t ph = now_ms % 1000;
  CRGB c = CRGB::Black;
  bool b = false;

  switch (in.phase) {
    case FlightPhase::SAFE: {
      const uint8_t v = uint8_t(40 + 40 * (1.0f + sinf(now_ms * 0.003f)));
      c = in.calibrated ? CRGB(0, 0, v) : CRGB(v / 2, 0, v);
      b = in.battery_low && (now_ms % 2000) < 60;
      break;
    }
    case FlightPhase::PAD_READY:
      c = in.continuity ? CRGB(0, 80, 0) : CRGB(60, 60, 0);
      b = ph < 30;
      break;
    case FlightPhase::BOOST:
    case FlightPhase::COAST:
      c = CRGB(80, 80, 80);
      break;
    case FlightPhase::APOGEE:
    case FlightPhase::DESCENT:
      c = CRGB(80, 0, 80);
      break;
    case FlightPhase::LANDED:
      c = ph < 500 ? CRGB(80, 60, 0) : CRGB::Black;
      b = ph < 100;
      break;
    case FlightPhase::ABORT:
      c = (now_ms % 200) < 100 ? CRGB(120, 0, 0) : CRGB::Black;
      b = (now_ms % 200) < 100;
      break;
  }
  fill_solid(leds, LED_COUNT, c);
  show();
  beep(b);
}
