"""Testvektoren für die nativen Firmware-Tests (firmware/test/data/) aus der Simulation erzeugen.

    python scripts/export_firmware_vectors.py

* ``sil_controller_ki0.csv`` / ``sil_controller_ki1.csv``: Eingänge und Ausgänge von
  ``tvcsim.controller.FirmwareController`` (Winkel, Drehraten, gefiltertes |a|, Momente,
  Servo-Grad) über einen Nominalflug, einmal mit Ki = 0 (Config.h) und einmal mit Ki = 1.
  ``firmware/src/ControlLaw.cpp`` muss dieselben Zahlen liefern (test_controllaw.cpp).
* ``flight_profile_tvcsim.csv``: |spezifische Kraft|, axiale spezifische Kraft, Höhe,
  Steiggeschwindigkeit und Barometerhöhe über den Flug (Fahrzeug ``preload``, Boden an,
  2 s Pad davor, 5 s Ruhe nach der Landung) für den Zustandsautomaten (test_flightstate.cpp).

Die Dateien liegen im Repo, damit die Tests ohne Python laufen; nach Änderungen an der
Simulation oder an Config.h neu erzeugen.
"""
import csv
from pathlib import Path

import numpy as np

import _path  # noqa: F401
from tvcsim.controller import FirmwareController
from tvcsim.params import FirmwareParams, NoiseParams, REPO_DIR, SimParams, VehicleParams
from tvcsim.sim import simulate

OUT = REPO_DIR / "firmware" / "test" / "data"


def export_sil(res, ki: float, name: str) -> None:
    fw = FirmwareParams(PY_KI=ki, quantize_servo=False, MASS_KG=0.761, MOMENT_ARM_M=0.242)
    fc = FirmwareController(fw, 0.01)
    rows = []
    for k in range(len(res.t)):
        w_sim = res.w_dps[k]
        a_norm = float(abs(res.T[k] / res.m[k]))      # spezifische Kraft entlang der Achse
        fc.step(float(res.t[k]), w_sim, None, float(res.T_est[k]), a_norm=a_norm)
        omega_fw = fc.sim_to_fw(w_sim)
        rows.append([f"{res.t[k]:.3f}", "0.01", f"{fc.rot_deg[0]:.6f}", f"{fc.rot_deg[1]:.6f}",
                     f"{omega_fw[0]:.6f}", f"{omega_fw[1]:.6f}", f"{fc.a_norm_filt:.6f}",
                     f"{fc.last['u'][1]:.8f}", f"{fc.last['u'][2]:.8f}",
                     f"{fc.last['yaw_servo_deg']:.5f}", f"{fc.last['pitch_servo_deg']:.5f}"])
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["t_s", "dt_s", "angle_x_deg", "angle_y_deg", "omega_x_dps", "omega_y_dps", "a_norm_filt",
                    "yaw_moment_nm", "pitch_moment_nm", "yaw_servo_deg", "pitch_servo_deg"])
        w.writerows(rows)
    print(f"{OUT / name}: {len(rows)} Zeilen")


def export_flight_profile(res) -> None:
    from scipy.spatial.transform import Rotation as R
    t = res.t
    g = 9.81
    # spezifische Kraft inertial: rdd - g_vec (x = Hoehe nach oben)
    f_in = res.rdd.copy()
    f_in[:, 0] += g
    q = res.q  # Skalar zuerst, Koerper -> inertial
    rot = R.from_quat(np.column_stack([q[:, 1], q[:, 2], q[:, 3], q[:, 0]]))
    f_body = rot.inv().apply(f_in)
    a_norm = np.linalg.norm(f_body, axis=1)
    a_axial = f_body[:, 0]
    alt = res.r[:, 0]
    vz = res.rd[:, 0]
    rng = np.random.default_rng(0)
    baro = alt + rng.normal(0, 0.3, len(alt))
    rows = []
    for k in range(200):                               # 2 s Pad
        rows.append([k * 0.01, g, g, 0.0, 0.0, float(rng.normal(0, 0.3))])
    for k in range(len(t)):
        rows.append([2.0 + t[k], a_norm[k], a_axial[k], alt[k], vz[k], baro[k]])
    t_end = 2.0 + t[-1]
    for k in range(1, 501):                            # 5 s Ruhe nach der Landung
        rows.append([t_end + k * 0.01, g, g, 0.0, 0.0, float(rng.normal(0, 0.3))])
    with open(OUT / "flight_profile_tvcsim.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["t_s", "a_norm_ms2", "a_axial_ms2", "alt_m", "vz_ms", "baro_alt_m"])
        for r in rows:
            w.writerow([f"{r[0]:.3f}"] + [f"{v:.4f}" for v in r[1:]])
    print(f"{OUT / 'flight_profile_tvcsim.csv'}: {len(rows)} Zeilen, Gipfel {alt.max():.1f} m, Landung {t[-1]:.2f} s")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    p = SimParams(vehicle=VehicleParams.preload(), controller="firmware",
                  noise=NoiseParams(accel_model="specific_force"), t_end=12.0, seed=0)
    p.firmware.MASS_KG = 0.761
    p.firmware.MOMENT_ARM_M = 0.242
    res = simulate(p)
    export_sil(res, 0.0, "sil_controller_ki0.csv")
    export_sil(res, 1.0, "sil_controller_ki1.csv")
    export_flight_profile(res)


if __name__ == "__main__":
    main()
