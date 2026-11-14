#include "Stream.h"
#include "Board.h"
#include <math.h>

using namespace board;

Res streamRun(float hz) {
  hz = constrain(hz, 1.0f, 200.0f);
  const uint32_t period_us = uint32_t(1e6f / hz);
  proto::info("stream %.0f Hz, q beendet. IMU und Magnetometer roh in Chip-Achsen (Format: Stream.h)", hz);
  Serial.println("HDR t_ms ax ay az gx gy gz ti mx my mz p tb v1 v2 varm py1 py2 py3 py4 ia vbus rh ts n");

  ImuSample is;
  MagSample ms;
  for (int i = 0; i < 3; ++i) { is.acc_ms2[i] = NAN; is.gyro_dps[i] = NAN; ms.mag_gauss[i] = NAN; }
  is.temp_c = NAN;
  float p = NAN, tb = NAN;
  float mux[7] = {NAN, NAN, NAN, NAN, NAN, NAN, NAN};   // v1 v2 varm py1..py4
  float ia = NAN, vbus = NAN, rh = NAN, ts = NAN;

  uint32_t next = micros();
  uint32_t t_ina = 0, t_sht = 0, lines = 0;
  int mux_i = 0;
  for (;;) {
    if (proto::abortRequested()) break;
    if (int32_t(micros() - next) < 0) continue;
    next += period_us;
    if (int32_t(micros() - next) > int32_t(4 * period_us)) next = micros();   // nach einer Pause nicht aufholen

    const int n_imu = st.imu ? imu.readAveraged(is) : 0;
    if (st.mag && mag.dataReady()) mag.read(ms);
    if (st.baro) { float pp, tt; if (baro.read(pp, tt)) { p = pp; tb = tt; } }

    // Mux reihum, eine Messung je Zeile (nie zwischen select() und deselect(): hier ist kein Chip gewählt)
    switch (mux_i) {
      case 0: mux[0] = vbat1(); break;
      case 1: mux[1] = vbat2(); break;
      case 2: mux[2] = armV(); break;
      default: mux[mux_i] = pyroV(mux_i - 3); break;
    }
    mux_i = (mux_i + 1) % 7;

    const uint32_t now = millis();
    if (st.ina && now - t_ina >= 100) {
      t_ina = now;
      PowerSample s;
      ina.read(s);
      ia = (s.current_A - calib.ina_offset_a) * calib.ina_gain;
      vbus = s.bus_V;
    }
    if (st.sht && (lines == 0 || now - t_sht >= 2000)) {   // blockiert ca. 10 ms
      t_sht = now;
      ShtSample s;
      if (sht.read(s)) { rh = s.rh_pct; ts = s.temp_c; }
    }

    Serial.printf("D %lu %.4f %.4f %.4f %.4f %.4f %.4f %.2f %.5f %.5f %.5f %.1f %.2f %.3f %.3f %.3f %.3f %.3f %.3f %.3f %.4f %.3f %.1f %.2f %d\n",
                  (unsigned long)now, is.acc_ms2[0], is.acc_ms2[1], is.acc_ms2[2], is.gyro_dps[0], is.gyro_dps[1], is.gyro_dps[2], is.temp_c,
                  ms.mag_gauss[0], ms.mag_gauss[1], ms.mag_gauss[2], p, tb,
                  mux[0], mux[1], mux[2], mux[3], mux[4], mux[5], mux[6], ia, vbus, rh, ts, n_imu);
    ++lines;
  }
  proto::test("stream", Res::OK, "%lu Zeilen", (unsigned long)lines);
  return Res::OK;
}
