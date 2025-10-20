/*
// ===== Sender: sendet 1x/Sek. eine BEACON-Zeile über HC-12 =====
#include <Arduino.h>

// Teensy 4.1: HC-12 am Serial8 (Pin 34=RX8, 35=TX8)
// Bei Uno/MEGA/etc. ggf. Serial1/2/3 verwenden.
HardwareSerial& HC12 = Serial8; 

const uint32_t HC12_BAUD = 9600;       // Werksdefault HC-12
const uint32_t PERIOD_MS = 1000;       // 1 Hz
uint32_t next_ms = 0;
uint32_t seq     = 0;

void setup() {
  Serial.begin(115200);
  uint32_t t0 = millis();
  while (!Serial && (millis() - t0) < 2000) {} // optional

  HC12.begin(HC12_BAUD);

  Serial.println("\n[TX] HC-12 Beacon sender started.");
  Serial.printf("[TX] Baud=%lu, period=%lums\n", (unsigned long)HC12_BAUD, (unsigned long)PERIOD_MS);

  next_ms = millis() + PERIOD_MS;
}

void loop() {
  uint32_t now = millis();
  if ((int32_t)(now - next_ms) >= 0) {
    // Paket im einfachen Zeilenformat:  BEACON,<seq>,<millis>\n
    HC12.print("BEACON,");
    HC12.print(seq++);
    HC12.print(",");
    HC12.print(now);
    HC12.print("\n");

    // Debug auf USB:
    Serial.print("[TX] sent: BEACON,");
    Serial.print(seq - 1);
    Serial.print(",");
    Serial.println(now);

    next_ms += PERIOD_MS;
  }
}
*/