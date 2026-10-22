#include "Igniter.h"
#include "Config.h"

namespace igniter {

static Status st;
static uint32_t lastAdcMs = 0;
static uint32_t relayMismatchSinceMs = 0;
static bool first = true;

static float readV(int pin, float div) {
  return analogReadMilliVolts(pin) * 0.001f * div;
}

static void filt(float& y, float x) {
  y = first ? x : y + 0.3f * (x - y);   // ~60 ms Zeitkonstante bei 20 ms Takt
}

void begin() {
  // Gate zuerst festlegen; der 100k-Pull-down hält es bis hierher unten.
  digitalWrite(PIN_FIRE_GATE, LOW);
  pinMode(PIN_FIRE_GATE, OUTPUT);
  pinMode(PIN_KEY_SENSE, INPUT);
  pinMode(PIN_ARM_SENSE, INPUT);
  analogReadResolution(12);
  analogSetPinAttenuation(PIN_ADC_LINE_NEG, ADC_11db);
  analogSetPinAttenuation(PIN_ADC_LINE_POS, ADC_11db);
  analogSetPinAttenuation(PIN_ADC_VBAT, ADC_11db);
  update();
}

void setFire(bool on) {
  digitalWrite(PIN_FIRE_GATE, on ? HIGH : LOW);
  st.firing = on;
}

void update() {
  uint32_t now = millis();
  st.key = digitalRead(PIN_KEY_SENSE);
  st.arm = digitalRead(PIN_ARM_SENSE) && st.key;

  if (now - lastAdcMs < ADC_PERIOD_MS && !first) return;
  lastAdcMs = now;
  filt(st.lineNegV, readV(PIN_ADC_LINE_NEG, DIV_LINE));
  filt(st.linePosV, readV(PIN_ADC_LINE_POS, DIV_LINE));
  filt(st.vbatV,    readV(PIN_ADC_VBAT,     DIV_VBAT));
  first = false;

  st.relayClosed = st.linePosV > RELAY_CLOSED_V;

  // Durchgang: Leitung minus wird über den Anzünder hochgezogen
  // (SICHER aus 3,3 V über 1k + Diode, SCHARF aus dem Akku über das Relais).
  // Während der Zündung zieht der MOSFET sie auf 0 V; dann gilt der letzte Wert.
  if (!st.firing) st.continuity = st.lineNegV > CONT_MIN_V;

  // Fehlerbewertung
  st.fault = nullptr;
  if (st.firing) return;
  bool mismatch = st.arm != st.relayClosed;
  if (mismatch) {
    if (!relayMismatchSinceMs) relayMismatchSinceMs = now;
  } else {
    relayMismatchSinceMs = 0;
  }
  if (relayMismatchSinceMs && now - relayMismatchSinceMs > 200) {
    st.fault = st.relayClosed ? "Relais klebt oder Fremdspannung auf der Zündleitung"
                              : "Relais zieht nicht an (Sicherung, Akku, Spule)";
  } else if (!st.relayClosed && st.linePosV < LINE_SHORT_V) {
    // Ohne Relais hält die Prüfquelle Leitung plus bei 2..3 V. Liegt sie bei 0,
    // ist die Leitung nach Masse kurzgeschlossen oder der MOSFET durchlegiert:
    // beim Scharfschalten würde sofort gezündet.
    st.fault = "Zündleitung an Masse: MOSFET durchlegiert oder Kurzschluss";
  }
}

const Status& status() { return st; }

} // namespace igniter
