#include "Indicators.h"

CRGB led1;
CRGB led2;

void Indicators_setup(){
  pinMode(PIN_BEEPER, OUTPUT);
  FastLED.addLeds<WS2812B, PIN_LED1, GRB>(&led1, 1);
  FastLED.addLeds<WS2812B, PIN_LED2, GRB>(&led2, 1);
  FastLED.clear(true);
}

void Indicate_success(){
  for (int i=0; i<4; ++i){
    digitalWrite(PIN_BEEPER, LOW);
    FastLED.clear(true);
    delay(50);
    if (i==3) break;
    if(!SILENT){
      digitalWrite(PIN_BEEPER, HIGH);
    }
    led1 = CRGB::Green; led2 = CRGB::Green;
    if(!DARK){
      FastLED.show();
    }
    delay(50);
  }
  digitalWrite(PIN_BEEPER, LOW);
  FastLED.clear(true);
}

void Indicate_waiting(){
  if(!SILENT){
      digitalWrite(PIN_BEEPER, HIGH);
  }
  led1 = CRGB::Orange; led2 = CRGB::Orange;
  if(!DARK){
      FastLED.show();
  }
}

void Indicate_warn(){
    for (int i=0; i<40; ++i){
    digitalWrite(PIN_BEEPER, LOW);
    FastLED.clear(true);
    delay(250);
    if (i==39) break;
    if(!SILENT){
      digitalWrite(PIN_BEEPER, HIGH);
    }
    led1 = CRGB::Red; led2 = CRGB::Red;
    if(!DARK){
      FastLED.show();
    }
    delay(250);
  }
  digitalWrite(PIN_BEEPER, LOW);
  FastLED.clear(true);
}
