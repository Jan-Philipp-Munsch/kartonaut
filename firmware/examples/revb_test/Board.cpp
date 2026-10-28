#include "Board.h"
#include <Servo.h>
#include "Config.h"      // Servo-Grenzen der Flug-Firmware (SERVO_*)

namespace board {

BusRevB    bus;
static LSM6DSV16X lsm(bus);
ImuDriver& imu = lsm;
BMP390     baro(bus, rb::Cs::BARO);
BMP390     baro2(bus, rb::Cs::BARO2);
INA239     ina(bus, rb::INA_SHUNT_OHM, rb::INA_MAX_CURRENT_A);
LIS3MDL    mag(rb::I2C_ADDR_LIS3MDL);
SHT40      sht(rb::I2C_ADDR_SHT40);
ADXL375    adxl(rb::I2C_ADDR_ADXL375);
CRGB       leds[rb::LED_COUNT_ONBOARD];
cal::CalData calib;
cal::Check   calib_check = cal::Check::EMPTY;
Status st;

static const uint8_t SERVO_PINS[4] = {rb::PIN_SERVO_YAW, rb::PIN_SERVO_PITCH, rb::PIN_SERVO_CHUTE, rb::PIN_SERVO_LEGS};
static Servo servos[4];

void safeOutputs() {
  for (uint8_t p : rb::PYRO_FIRE_PINS) { digitalWrite(p, LOW); pinMode(p, OUTPUT); }
  digitalWrite(rb::PIN_MOT_NSLEEP, LOW); pinMode(rb::PIN_MOT_NSLEEP, OUTPUT);
  digitalWrite(rb::PIN_MOT_IN1, LOW);    pinMode(rb::PIN_MOT_IN1, OUTPUT);
  digitalWrite(rb::PIN_MOT_IN2, LOW);    pinMode(rb::PIN_MOT_IN2, OUTPUT);
  for (uint8_t p : SERVO_PINS) { digitalWrite(p, LOW); pinMode(p, OUTPUT); }
  digitalWrite(rb::PIN_BUZZER, LOW);     pinMode(rb::PIN_BUZZER, OUTPUT);
  digitalWrite(rb::PIN_CAM_TRIG, LOW);   pinMode(rb::PIN_CAM_TRIG, OUTPUT);
  pinMode(rb::PIN_MOT_FAULT, INPUT_PULLUP);
  pinMode(rb::PIN_IMU_INT, INPUT);
  pinMode(rb::PIN_LORA_NRST, INPUT);     // Open-Drain: loslassen = Pull-up hält hoch
  pinMode(rb::PIN_LORA_AUX, INPUT);
  // CS_EN hält der Pull-up hoch; bus.begin() setzt ihn als Ausgang hoch
}

void begin() {
  bus.begin();
  revb_i2c::begin(rb::I2C_SPEED_HZ);
  FastLED.addLeds<WS2812B, rb::PIN_LED_DATA, GRB>(leds, rb::LED_COUNT_ONBOARD);
  calib_check = cal::load(calib);

  st.imu   = imu.begin();
  st.baro  = baro.begin();
  st.baro2 = baro2.begin();
  st.ina   = ina.begin();
  st.mag   = mag.begin();
  st.sht   = sht.begin();
  st.adxl  = adxl.begin();
}

float muxInputV(rb::Mux ch) {
  return bus.readMuxInputV(ch) * calib.adc_gain[uint8_t(ch)];
}
float vbat1() { return muxInputV(rb::Mux::VBAT1); }
float vbat2() { return muxInputV(rb::Mux::VBAT2); }
float armV()  { return muxInputV(rb::Mux::ARM); }
float pyroV(int ch) { return muxInputV(rb::Mux(uint8_t(rb::Mux::PYRO1) + ch)); }
bool  have2S() { return vbat2() > 6.0f; }
bool  armed()  { return armV() > 5.0f; }

void setLeds(CRGB c) {
  fill_solid(leds, rb::LED_COUNT_ONBOARD, c);
  FastLED.show();
}

void beep(uint16_t ms) {
  digitalWrite(rb::PIN_BUZZER, HIGH);
  delay(ms);
  digitalWrite(rb::PIN_BUZZER, LOW);
}

// Fenster aus Config.h: Pulsbereich SERVO_PULSE_MIN/MAX_US, für Yaw/Pitch
// zusätzlich das mechanische Fenster des Kardans in Servo-Grad (0..180 auf den Pulsbereich).
static int degToUs(float deg) {
  return int(SERVO_PULSE_MIN_US + deg / 180.0f * (SERVO_PULSE_MAX_US - SERVO_PULSE_MIN_US) + 0.5f);
}

void servoLimitsUs(int i, int& lo, int& hi) {
  lo = SERVO_PULSE_MIN_US;
  hi = SERVO_PULSE_MAX_US;
  if (i == 0) { lo = degToUs(SERVO_YAW_MIN_DEG);   hi = degToUs(SERVO_YAW_MAX_DEG); }
  if (i == 1) { lo = degToUs(SERVO_PITCH_MIN_DEG); hi = degToUs(SERVO_PITCH_MAX_DEG); }
}

void servoWriteUs(int i, int us) {
  if (i < 0 || i > 3) return;
  int lo, hi;
  servoLimitsUs(i, lo, hi);
  us = constrain(us, lo, hi);
  if (!servos[i].attached()) servos[i].attach(SERVO_PINS[i], SERVO_PULSE_MIN_US, SERVO_PULSE_MAX_US);
  servos[i].writeMicroseconds(us);
}

void servoRelease(int i) {
  if (i < 0 || i > 3) return;
  if (servos[i].attached()) servos[i].detach();
  digitalWrite(SERVO_PINS[i], LOW);
  pinMode(SERVO_PINS[i], OUTPUT);
}

void servoReleaseAll() { for (int i = 0; i < 4; ++i) servoRelease(i); }

}  // namespace board
