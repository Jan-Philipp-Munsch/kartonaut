#include "Sensors.h"

#ifdef USE_WIRE1_FOR_IMU
  #define WIRE_IMU Wire1
#else
  #define WIRE_IMU Wire
#endif

// --- Geräteinstanzen ---
static Adafruit_BMP280 bmp;         // Barometer
static ICM_20948_I2C   imu;         // IMU (DMP/FIFO)
static INA219_WE       ina219(0x40);// Power-Monitor

// --- Stati & Kalibrierung ---
float gndps_hPa = 1013.25f;         // für BMP280.readAltitude()
static float calib_temp = 20.0f;

static bool imu_ok=false, bmp_ok=false, ina_ok=false;

// Body-Frame Bias (m/s^2), von Accel_calibrate_body() gesetzt
Vec3 g_acc_bias_body_ms2 = {0.0f, 0.0f, 0.0f};

void Sensors_setup(){
  // I2C
  Wire.begin();
  Wire.setClock(I2C_MAIN_SPEED_HZ);

#ifdef USE_WIRE1_FOR_IMU
  WIRE_IMU.begin();
  WIRE_IMU.setClock(I2C_IMU_SPEED_HZ);
#endif

  // --- BMP280 ---
  bmp_ok = bmp.begin(0x76);
  if (bmp_ok){
    bmp.setSampling(Adafruit_BMP280::MODE_NORMAL,
                    Adafruit_BMP280::SAMPLING_X1,
                    Adafruit_BMP280::SAMPLING_X4,
                    Adafruit_BMP280::FILTER_X4,
                    Adafruit_BMP280::STANDBY_MS_1);
  }

  // --- ICM-20948 ---
  imu.begin(WIRE_IMU, 0);
  imu_ok = (imu.status == ICM_20948_Stat_Ok);
  if (imu_ok){
    bool ok = true;
    ok &= (imu.initializeDMP() == ICM_20948_Stat_Ok);
    ok &= (imu.enableDMPSensor(INV_ICM20948_SENSOR_ORIENTATION) == ICM_20948_Stat_Ok);
    ok &= (imu.enableDMPSensor(INV_ICM20948_SENSOR_ACCELEROMETER) == ICM_20948_Stat_Ok);
    ok &= (imu.enableDMPSensor(INV_ICM20948_SENSOR_GYROSCOPE) == ICM_20948_Stat_Ok);
    ok &= (imu.setDMPODRrate(DMP_ODR_Reg_Quat9, 0) == ICM_20948_Stat_Ok);
    ok &= (imu.setDMPODRrate(DMP_ODR_Reg_Accel, 0) == ICM_20948_Stat_Ok);
    ok &= (imu.setDMPODRrate(DMP_ODR_Reg_Gyro, 0) == ICM_20948_Stat_Ok);
    ok &= (imu.setDMPODRrate(DMP_ODR_Reg_Gyro_Calibr, 0) == ICM_20948_Stat_Ok);
    ok &= (imu.enableFIFO() == ICM_20948_Stat_Ok);
    ok &= (imu.enableDMP() == ICM_20948_Stat_Ok);
    ok &= (imu.resetDMP() == ICM_20948_Stat_Ok);
    ok &= (imu.resetFIFO() == ICM_20948_Stat_Ok);
    imu_ok = ok;
  }

  // --- INA219 ---
  ina_ok = ina219.init();

  if (bmp_ok) BMP_calibrate_ground();
}

void BMP_calibrate_ground(){
  if (!bmp_ok) return;
  gndps_hPa = 0.f; calib_temp = 0.f;
  for (int i=0;i<100;i++){
    gndps_hPa  += bmp.readPressure()   / 100.0f; // Pa → hPa
    calib_temp += bmp.readTemperature();
    delay(5);
  }
  gndps_hPa  /= 100.0f;
  calib_temp /= 100.0f;

  if (VERBOSE){
    Serial.print("BMP ground cal: p[hPa]="); Serial.print(gndps_hPa,1);
    Serial.print(", T[C]="); Serial.println(calib_temp,1);
  }
}

// Stationäre Accel-Kalibrierung (Body-Frame)
void Accel_calibrate_body(int samples, uint16_t sample_delay_ms){
  if (!imu_ok) return;

  Vec3 sum_meas = {0,0,0};
  Quaternion q(1,0,0,0);
  int collected = 0;

  while (collected < samples){
    if (!imu.dataReady()) { delay(sample_delay_ms); continue; }
    icm_20948_DMP_data_t d;
    imu.readDMPdataFromFIFO(&d);
    if (imu.status != ICM_20948_Stat_Ok && imu.status != ICM_20948_Stat_FIFOMoreDataAvail){ delay(sample_delay_ms); continue; }

    bool gotQuat=false, gotAcc=false;
    Vec3 a_body_ms2;

    if ((d.header & DMP_header_bitmap_Quat9) > 0){
      float q1 = (float)d.Quat9.Data.Q1 / 1073741824.0f;
      float q2 = (float)d.Quat9.Data.Q2 / 1073741824.0f;
      float q3 = (float)d.Quat9.Data.Q3 / 1073741824.0f;
      float t  = 1.0f - (q1*q1 + q2*q2 + q3*q3);
      if (t < 0.f) t = 0.f;
      float q0 = sqrtf(t);
      q = Quaternion(q0,q1,q2,q3);
      q.normalize();
      gotQuat = true;
    }

    if ((d.header & DMP_header_bitmap_Accel) > 0){
      a_body_ms2 = {
        (float)d.Raw_Accel.Data.X / ACC_LSB_PER_G * G_MS2,
        (float)d.Raw_Accel.Data.Y / ACC_LSB_PER_G * G_MS2,
        (float)d.Raw_Accel.Data.Z / ACC_LSB_PER_G * G_MS2
      };
      gotAcc = true;
    }

    if (!(gotQuat && gotAcc)) { delay(sample_delay_ms); continue; }

    sum_meas += a_body_ms2;
    ++collected;
    delay(sample_delay_ms);
  }

  const Vec3 avg_meas = sum_meas * (1.0f / max(1, samples));

  // Erwartete a_body im Stillstand: -R^T * g
  const Vec3 gravity_nav = {0,0,-G_MS2};
  const Quaternion q_conj = q.conjugate();
  const Vec3 Rt_g = rotateVector(q_conj, gravity_nav);   // R^T * g
  const Vec3 expected = Vec3(-Rt_g.x, -Rt_g.y, -Rt_g.z); // -R^T * g

  g_acc_bias_body_ms2 = avg_meas - expected;

  if (VERBOSE){
    Serial.print("Accel bias body [m/s^2]: ");
    Serial.print(g_acc_bias_body_ms2.x,3); Serial.print(", ");
    Serial.print(g_acc_bias_body_ms2.y,3); Serial.print(", ");
    Serial.println(g_acc_bias_body_ms2.z,3);
  }
}

// -----------------------------
//  IMU-Read mit FIFO-Drain
// -----------------------------
bool Read_IMU(ImuData& out, float& a_norm_filt){
  if (!imu_ok) return false;

  // Statische Merker (bleiben auch ohne neue Frames erhalten)
  static Quaternion last_q(1,0,0,0);
  static Vec3 last_omega_dps = {0,0,0};
  static Vec3 gyro_filt = {0,0,0};

  constexpr float GYRO_ALPHA = 0.25f; // 0..1 (höher = glatter)
  const uint32_t t_start = micros();

  // Default: gebe die letzten Werte aus; markiere Flags als "nicht frisch"
  out.q         = last_q;
  out.omega_dps = last_omega_dps;
  out.hasQuat   = false;
  out.hasAccel  = false;
  out.hasGyro   = false;
  out.stamp_us  = t_start;

  // Wir versuchen die FIFO zu lesen, auch wenn dataReady() false sagt.
  // Beenden, wenn kein "MoreDataAvail" kommt oder wir unser Cap erreichen.
  bool got_any = false;
  const int READ_CAP = 24;     // Sicherheitsgrenze
  for (int i=0; i<READ_CAP; ++i){
    icm_20948_DMP_data_t d;
    imu.readDMPdataFromFIFO(&d);

    // Wenn der Status irgendetwas anderes ist als OK oder MoreDataAvail,
    // ist die FIFO leer oder ein Fehler aufgetreten -> raus aus der Schleife.
    if (!(imu.status == ICM_20948_Stat_Ok || imu.status == ICM_20948_Stat_FIFOMoreDataAvail)) {
      break;
    }

    got_any = true; // wir haben zumindest einen Frame gesehen

    // --- Quat ---
    if ((d.header & DMP_header_bitmap_Quat9) > 0){
      float q1 = (float)d.Quat9.Data.Q1 / 1073741824.0f;
      float q2 = (float)d.Quat9.Data.Q2 / 1073741824.0f;
      float q3 = (float)d.Quat9.Data.Q3 / 1073741824.0f;
      float t  = 1.0f - (q1*q1 + q2*q2 + q3*q3);
      if (t < 0.f) t = 0.f;
      float q0 = sqrtf(t);
      out.q = Quaternion(q0,q1,q2,q3);
      out.q.normalize();
      last_q   = out.q;
      out.hasQuat = true;
    }

    // --- Accel ---
    if ((d.header & DMP_header_bitmap_Accel) > 0){
      Vec3 a_body_ms2 = {
        (float)d.Raw_Accel.Data.X / ACC_LSB_PER_G * G_MS2,
        (float)d.Raw_Accel.Data.Y / ACC_LSB_PER_G * G_MS2,
        (float)d.Raw_Accel.Data.Z / ACC_LSB_PER_G * G_MS2
      };
      // Bias abziehen
      a_body_ms2 = a_body_ms2 - g_acc_bias_body_ms2;
      out.a_body = a_body_ms2;

      const Vec3 gravity_nav(0,0,-G_MS2);
      const Quaternion& q_use = out.hasQuat ? out.q : last_q; // konsistent rotieren
      out.a_nav = rotateVector(q_use, a_body_ms2) + gravity_nav;

      // |a| leicht glätten
      const float aN = norm(a_body_ms2);
      a_norm_filt += (aN - a_norm_filt) * A_NORM_ALPHA;

      out.hasAccel = true;
    }

    // --- Gyro ---
    if ((d.header & DMP_header_bitmap_Gyro_Calibr) > 0){
      Vec3 omega = {
        (float)(d.Raw_Gyro.Data.X + 12.1f) / GYRO_LSB_PER_DPS,
        (float)(d.Raw_Gyro.Data.Y - 7.96f) / GYRO_LSB_PER_DPS,
        (float)(d.Raw_Gyro.Data.Z + 2.44f) / GYRO_LSB_PER_DPS
      };
      // IIR-Glättung
      gyro_filt.x += (omega.x - gyro_filt.x) * GYRO_ALPHA;
      gyro_filt.y += (omega.y - gyro_filt.y) * GYRO_ALPHA;
      gyro_filt.z += (omega.z - gyro_filt.z) * GYRO_ALPHA;

      out.omega_dps   = gyro_filt;
      last_omega_dps  = out.omega_dps;
      out.hasGyro     = true;
    }

    // Wenn keine weiteren Daten verfügbar sind, verlassen wir die Schleife
    if (imu.status != ICM_20948_Stat_FIFOMoreDataAvail) break;
  }

  // Wenn in diesem Loop kein Frame kam, geben wir die letzten Werte zurück.
  // Returnwert signalisiert dem Aufrufer, ob etwas Neues verarbeitet wurde.
  return got_any;
}


bool Read_Baro(BaroData& out){
  if (!bmp_ok) return false;
  out.alt_m = bmp.readAltitude(gndps_hPa);
  return true;
}

bool Read_Power(PowerData& out){
  if (!ina_ok) return false;
  out.shunt_mV   = ina219.getShuntVoltage_mV();
  out.bus_V      = ina219.getBusVoltage_V();
  out.current_mA = ina219.getCurrent_mA();
  out.power_mW   = ina219.getBusPower();
  out.load_V     = out.bus_V + out.shunt_mV/1000.0f;
  out.overflow   = ina219.getOverflow();
  return true;
}
