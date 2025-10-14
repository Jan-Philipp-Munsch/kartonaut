#include <Arduino.h>
#include "Config.h"
#include "MathTypes.h"
#include "Indicators.h"
#include "Sensors.h"
#include "KalmanZ.h"
#include "Control.h"
#include "Timing.h"
#include <HardwareSerial.h>

HardwareSerial& hc12 = Serial8;

// ======= State =======
static LoopTimer loopTimer;
static KalmanZ kal;
static float a_norm_filt = G_MS2;   // LPF(|a|)
static Vec3 rot_deg = {0,0,0};      // integrierte Demo-Rotation
static float AltitudeKalman = 0.f, VelocityVerticalKalman = 0.f;

// Offset/Zeroing nach Einpendeln
static float alt_offset = 0.0f;
static bool  offset_applied = false;

void setup(){
  Serial.begin(115200);

  Indicators_setup();
  //Indicate_success();
  //Indicate_waiting();

  Motor_setup();
  Control_setup();
  Sensors_setup();


  hc12.begin(HC12_BAUD);

  // Kalman initial parametrieren
  kal.setDt(1.0f/LOOP_HZ, KALMAN_SIGMA_ACC_MS2);
  kal.setMeasStd(KALMAN_MEAS_STD_M);
  kal.setState(KALMAN_INIT_Z_M, KALMAN_INIT_VZ_MS);
  kal.setPDiag(KALMAN_INIT_PZ_VAR, KALMAN_INIT_PV_VAR);

  LoopTimer_init(loopTimer);
  //Indicate_success();
}

void loop(){
  if (!LoopTimer_tick(loopTimer)) return; // exakte Periodik
  const uint32_t t0 = micros();

  // --- Sensors ---
  BaroData baro;
  Read_Baro(baro);

  ImuData imu;
  if (Read_IMU(imu, a_norm_filt)){
    // integrierte Rotation (nur Demo wie in deinem Code)
    rot_deg += imu.omega_dps * loopTimer.dt_meas_s;
  }

  // --- Kalman (mit aktuellem dt) ---
  kal.setDt(loopTimer.dt_meas_s, KALMAN_SIGMA_ACC_MS2);
  kal.step(imu.a_nav.z, baro.alt_m, AltitudeKalman, VelocityVerticalKalman);

  // Einpendeln & Nullpunkt setzen (optional)
  if (KALMAN_ZERO_AFTER_SETTLE && !offset_applied) {
    static uint32_t t_start_ms = millis();
    if ((millis() - t_start_ms) > (uint32_t)(KALMAN_SETTLE_TIME_S * 1000.0f)) {
      alt_offset = AltitudeKalman;  // Boden als 0 setzen
      offset_applied = true;
    }
  }

  // --- Control: Servos (Grad) ---
  int yaw_deg_cmd = SERVO_DEG_CENTER, pitch_deg_cmd = SERVO_DEG_CENTER;
  AttState attOut;
  if(false){
    Control_updatePY(imu.omega_dps, rot_deg, loopTimer.dt_meas_s, a_norm_filt,
                    yaw_deg_cmd, pitch_deg_cmd, attOut);
    Apply_servos_deg(yaw_deg_cmd, pitch_deg_cmd);
  }

  // --- Control: Roll
  float roll_angle_deg, roll_rate_dps, roll_corr_angle_deg, roll_cmd_norm;
  int   roll_pwm, roll_dir;
  if(false){
    Control_updateRoll(imu.omega_dps, rot_deg, loopTimer.dt_meas_s,
                  roll_angle_deg, roll_rate_dps, roll_corr_angle_deg,
                  roll_cmd_norm, roll_pwm, roll_dir);
  }


  // --- Teleplot-Ausgaben (Konsole) ---

  if(false)  {
    Serial.print(">Kalman_Alt:");  Serial.println(AltitudeKalman - alt_offset, 3);
    Serial.print(">Kalman_Vz:");   Serial.println(VelocityVerticalKalman, 3);
    //Serial.print(">Baro_Alt:");    Serial.println(baro.alt_m - alt_offset, 3);
    //Serial.print(">dt_meas:");     Serial.println(loopTimer.dt_meas_s, 6);
  }
  if(false)  {
    // Teleplot
    Serial.print(">Roll_Angle:");       Serial.println(roll_angle_deg, 3);
    Serial.print(">Roll_Rate:");        Serial.println(roll_rate_dps, 3);
    //Serial.print(">Roll_Corr_Angle:");  Serial.println(roll_corr_angle_deg, 3);
    //Serial.print(">Roll_CMD:");         Serial.println(roll_cmd_norm, 3);
    Serial.print(">Roll_PWM:");         Serial.println(roll_pwm);
    Serial.print(">Roll_Dir:");         Serial.println(roll_dir);
  }
  if(false)  {
    PowerData p;
    if (Read_Power(p)) {
      // optional: leichte Glättung für nicer plots
      static float i_filt = 0.0f, pwr_filt = 0.0f;
      const float ALPHA = 0.2f; // 0..1 (höher = glatter)

      i_filt   += (p.current_mA - i_filt) * ALPHA;
      pwr_filt += (p.power_mW   - pwr_filt) * ALPHA;

      //Serial.print(">INA_Shunt_mV:");  Serial.println(p.shunt_mV,   3);
      Serial.print(">INA_Bus_V:");     Serial.println(p.bus_V,      3);
      //Serial.print(">INA_Load_V:");    Serial.println(p.load_V,     3);
      //Serial.print(">INA_Current_mA:");Serial.println(p.current_mA, 3);
      //Serial.print(">INA_Power_mW:");  Serial.println(p.power_mW,   3);

      // gefilterte Kurven (falls du sie getrennt sehen willst)
      Serial.print(">INA_Current_mA_f:"); Serial.println(i_filt,   3);
      Serial.print(">INA_Power_mW_f:");   Serial.println(pwr_filt, 3);
      // Overflow-Flag als 0/1
      //Serial.print(">INA_Overflow:");  Serial.println(p.overflow ? 1 : 0);
    }
  }


  LoopTimer_overrunCheck(t0);
}

