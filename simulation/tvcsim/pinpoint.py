"""Punktlandung mit TVC: Aufstieg, freier Fall, Landebrennen und Aufsetzen am Zielpunkt (15.11.2026).

Die bisherigen Landestudien (``landing.py``, ``throttle.py``) rechnen senkrecht in 1D. Dieses Modul rechnet
den ganzen Flug in 6DOF und fuer viele Laeufe gleichzeitig (alle Zustaende sind Felder der Form (N, ...)),
damit ein Monte-Carlo mit einigen hundert Laeufen in Sekunden durchlaeuft. Es beantwortet: Wie nah am
Zielpunkt und wie weich setzt die Rakete auf, wenn Schubkurve, Stellglieder, Wind, Sensoren und Kalibrierung
streuen, und welche Drosselspanne, Regelguete und Sensorik braucht es dafuer?

Koordinaten wie in der Firmware (``Attitude.h``): Navigationssystem x = Ost, y = Nord, z = oben, Ursprung am
Startpunkt; Koerper z = Laengsachse zur Spitze; ``q`` dreht Koerper -> Navigation (Skalar zuerst).

Wahrheit
    Starrkoerper mit Schub (zwei Motoren, Impuls und Brenndauer gestreut), Schubdrossel (Pads, PT2 mit
    Totzeit, Kennlinie f(u) = 1 - (1 - f_min) u^gamma), Kardan (PT2 mit Totzeit, Ratenbegrenzung,
    Verstaerkungs- und Nullpunktfehler), seitlichem Schwerpunktversatz, Rollmoment, Wind (Hoehenprofil plus
    Boeen als Gauss-Markov-Prozess) und Aerodynamik: Axialwiderstand, Querkraft der Spitze (Barrowman, im
    Rueckwaertsfall am Heck), Queranstroemwiderstand des Rumpfs. Die Querkraefte greifen an ihren
    Druckpunkten an und geben das Moment, das die finnenlose Rakete instabil macht.
Sensoren
    Gyro und Beschleunigung (Nullpunkt, Skalenfehler, Achsfehler, Rauschen, Vibration unter Schub),
    Barometer (Rauschen, Nullpunkt, Staudruckfehler), Magnetometer (nur Kurs auf der Rampe: Hart- und
    Weicheisenrest, Stoerfeld der Rampe, Missweisung), GPS (langsam wandernder Fehler relativ zur Einmessung
    auf der Rampe, Rauschen, Latenz, Ausfall ueber der g-Grenze), Kamera mit Zielmarke (Peilung im
    Koerpersystem: Winkelrauschen, Einbaufehler, Latenz, Sichtfeld, Reichweite), Laser-Hoehenmesser.
Schaetzung
    Lage: Gyro-Quaternion wie die Firmware, Startlage aus Beschleunigung und Magnetometer. Position und
    Geschwindigkeit: je Achse ein Kalman-Filter mit drei Zustaenden (Position, Geschwindigkeit,
    Beschleunigungsfehler), Vorhersage mit der ins Navigationssystem gedrehten Beschleunigung, Stuetzung
    durch Barometer, GPS, Kamera und Laser. Das ist ``KalmanZ`` der Firmware, auf drei Achsen erweitert.
Fuehrung und Regelung
    Lageregler wie die Firmware (PID auf den Kippfehler, D auf die Drehrate, Moment -> Kardanwinkel ueber
    den geschaetzten Schub). Landezuendung aus einer Tabelle Zuendhoehe(Sinkrate), die das schlechteste
    Aufsetzen ueber schwachen und starken Motor und kurzen und langen Zuendverzug minimiert. Senkrecht
    fuehrt die Drossel zeitbasiert auf Hoehe 0 zum Brennschluss (wie ``throttle.py``), seitlich fuehrt
    dieselbe Zero-Effort-Miss-Regel ueber den Kippwinkel auf den Zielpunkt.

Nicht modelliert: Fahrwerk und Umkippen nach dem Aufsetzen, Schwerpunktwanderung beim Abbrand, Abschattung
der Aerodynamik durch den Abgasstrahl, Hebelarm des Sensors zum Schwerpunkt, Reaktionsmoment des Kardans
(in ``rate_study.py`` als unkritisch gezeigt).
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from types import SimpleNamespace

import numpy as np

from .motors import load_thrust_curve

G = 9.81
DEG = np.pi / 180.0


@dataclass
class PinpointConfig:
    # ----- Mission und Fahrzeug (Nennwerte) -----
    curve: str = "E12"
    # Flugprofil:
    #  "fall":     Aufstieg mit Motor 1, antriebsloser Flug ueber den Gipfel, Landezuendung aus der Tabelle
    #  "handover": Motor 2 zuendet ``overlap`` vor dem Brennschluss von Motor 1 (beide im Kardan), nie ohne Schub
    #  "hop":      ein Motor: gedrosselt steigen bis ``t_hop_switch``, dann Landefuehrung auf demselben Motor
    mission: str = "fall"
    overlap: float = 0.35          # s, Zuendkommando vor dem Nenn-Brennschluss von Motor 1 ("handover")
    swap_time: float | None = None  # s, Motorwechsel im Magazin ("handover"): Zuendkommando erst, wenn Motor 1 wirklich
                                   # ausgebrannt und Motor 2 nachgerutscht ist (Nennzeit, je Lauf 0,7- bis 1,5-fach);
                                   # ersetzt ``overlap``. Die Schubluecke ist swap_time plus Zuendverzug
    swap_open_lead: float = 0.0    # s vor dem Nenn-Brennschluss von Motor 1 faehrt die Drossel ganz auf, damit die leere
                                   # Huelse durch die Schlitzscheibe faellt (nur mit swap_time); bis dahin wird gedrosselt
    t_hop_switch: float = 1.5      # s nach der Zuendung ("hop")
    m_land: float = 0.60           # kg bei der Landezuendung: voller Landemotor, leere Huelse des ersten
                                   # ("hop": Startmasse mit vollem Motor)
    fuel: float = 0.028            # kg Treibstoff je Motor
    I_t: float | None = None       # kg m^2 quer; None: 0,0211 * (m_land + fuel) / 0,704 (Stand 2b skaliert)
    I_a: float = 0.0006            # kg m^2 laengs
    lever: float = 0.20            # m, Kardanpunkt bis Schwerpunkt
    motor_offset: float = 0.0      # m, Schubachsen der beiden Motoren je so weit neben der Kardanachse
                                   # ("handover" mit zwei Motoren nebeneinander: 0,0125 bei 24-mm-Motoren)
    motor_cant: bool = False       # beide Motoren so schraeg eingebaut, dass ihre Schubachsen durch den Schwerpunkt
                                   # gehen (Winkel motor_offset / lever): kein Moment, dafuer Querkraft
    motor_ff: bool = False         # Regler stellt den Trimm fuer den Schubversatz vor (aus Nennkurve und Zuendzeit)
    z_cg: float = 0.27             # m, Schwerpunkt ueber der Duese
    target_e: float = 0.0          # m, Zielpunkt relativ zum Startpunkt
    target_n: float = 0.0
    landing: bool = True           # False: nur Aufstieg und Fall (ohne Landemotor)
    # ----- Schubdrossel -----
    f_min: float = 0.5             # kleinster Schubfaktor; 1,0 = keine Drossel
    thr_wn: float = 36.7           # rad/s, Pads als PT2 (wie der Kardan-Servo im SG90-Fit)
    thr_zeta: float = 0.6
    thr_dead: float = 0.03         # s
    throttle_ascent: bool = False  # Aufstieg drosseln: Steiggeschwindigkeit und Gipfel begrenzen
    h_apo: float = 30.0            # m
    v_asc_max: float = 8.0         # m/s
    a_dec_ascent: float = 2.0      # m/s^2, Verzoegerung, mit der der Aufstieg auf h_apo abgebremst wird
    kv_ascent: float = 2.0         # 1/s
    ascent_hold: bool = False      # im Aufstieg seitlich auf den Zielpunkt fuehren (Vorgabe: der Startpunkt)
    kp_hold: float = 2.0           # 1/s^2
    kd_hold: float = 2.4           # 1/s
    tilt_max_ascent: float = 10.0  # Grad
    # ----- Kardan -----
    gim_max: float = 5.0           # Grad
    gim_wn: float = 60.0           # rad/s (Nennwert; gestreut zwischen gim_wn_lo und gim_wn_hi)
    gim_wn_lo: float = 40.0
    gim_wn_hi: float = 80.0
    gim_zeta: float = 0.9
    gim_dead_lo: float = 0.004     # s, Totzeit gleichverteilt (W5652H-Annahme bis SG90-Fit)
    gim_dead_hi: float = 0.030
    gim_rate: float = 150.0        # Grad/s am Kardan
    gim_slew: float = 100.0        # Grad/s, Begrenzung des Kommandos (Firmware PY_SLEW_TVC_DPS)
    # ----- Lageregler (Firmware-Gewinne Kp 2 / Ki 1 / Kd 0,45 bei I = 0,021: wn 7,4 rad/s, zeta 0,83) -----
    att_wn: float = 7.4
    att_zeta: float = 0.83
    att_ki: float = 0.5            # 1/s, Ki = att_ki * Kp
    att_int_max: float = 0.15      # rad s
    d_lpf_hz: float = 30.0
    a_norm_tau: float = 0.095      # s
    # ----- Landefuehrung -----
    tilt_max_land: float = 15.0    # Grad
    tilt_max_ground: float = 6.0   # Grad, unterhalb h_upright
    h_upright: float = 3.0         # m, darunter wird der zulaessige Kippwinkel linear zurueckgenommen
    t_go_lat_min: float = 1.0      # s
    lateral: bool = True           # seitliche Fuehrung im Landebrennen (False: nur senkrecht halten)
    t_go_margin: float = 0.15      # s, Aufsetzen so viel vor dem Brennschluss planen
    t_go_min: float = 0.3
    v_final: float = 0.5           # m/s
    h_final: float = 0.8           # m
    h_cut: float = 0.25            # m, darunter Pads ganz hinein
    kv_final: float = 3.0          # 1/s
    ign_delay_assumed: float = 0.10
    ign_delay_lo: float = 0.05     # s, wahrer Zuendverzug gleichverteilt
    ign_delay_hi: float = 0.20
    ign_scales: tuple = (0.9, 1.1)         # Motoren, fuer die die Zuendtabelle das schlechteste Aufsetzen minimiert
    ign_delays: tuple = (-0.05, 0.10)      # s, Abweichung des Zuendverzugs dabei
    ign_extra_m: float = 0.0       # m, Zuendung hoeher als die Tabelle
    # ----- Umgebung -----
    wind10: float = 3.0            # m/s in 10 m Hoehe
    wind_exp: float = 0.2          # Exponent des Hoehenprofils
    gust_frac: float = 0.2         # Boeen-Standardabweichung als Anteil von wind10
    gust_tau: float = 3.0          # s
    rho: float = 1.2
    # ----- Aerodynamik (Nennwerte; Rumpf Durchmesser 75 mm, Laenge 731 mm) -----
    aero: bool = True
    a_ref: float = 0.00442         # m^2
    cd_a: float = 0.003            # m^2, Axialwiderstand Cd * A
    cna_nose: float = 2.0          # 1/rad, Spitze (Barrowman)
    z_cp_nose: float = 0.62        # m ueber der Duese
    cna_base: float = 1.0          # 1/rad, stumpfes Heck im Rueckwaertsfall (grobe Annahme)
    z_cp_base: float = 0.03
    cdc: float = 1.1               # Queranstroemwiderstand des Zylinders
    a_plan: float = 0.050          # m^2, Seitenflaeche
    z_cp_cross: float = 0.36       # m
    # ----- Streuung der Wahrheit (1 Sigma, sofern nicht anders gesagt); scatter skaliert alles -----
    scatter: float = 1.0
    sc_motor: float = 1.0          # Gruppen einzeln abschaltbar (Unsicherheitsbudget): Motoren und Zuendverzug,
    sc_act: float = 1.0            # Kardan und Drossel,
    sc_mass: float = 1.0           # Masse, Traegheit, Schwerpunkt, Rollmoment, Schiefstand,
    sc_aero: float = 1.0           # Aerodynamik
    sig_mass: float = 0.010        # kg
    sig_inertia: float = 0.05      # relativ
    sig_lever: float = 0.005       # m
    sig_cg_lat: float = 0.0015     # m je Achse
    sig_impulse: float = 0.04      # relativ, Gesamtimpuls je Motor
    sig_burntime: float = 0.04     # relativ, Brenndauer (Schub entsprechend umgekehrt)
    sig_gim_gain: float = 0.05     # relativ
    sig_gim_off: float = 0.5       # Grad je Achse (Nullstellung und Schubvektorfehler)
    sig_fmin: float = 0.05         # relativ
    gamma_lo: float = 0.7          # Kennlinie der Pads u^gamma, gleichverteilt
    gamma_hi: float = 1.4
    sig_pad_side: float = 1.0      # Grad Schubablenkung bei voll eingeschwenkten Pads
    pad_side_bias: float = 0.0     # Grad, feste (bei jedem Flug gleiche) Ablenkung bei voller Drosselung, z. B. durch den
                                   # Keilschlitz der Schlitzscheibe; pad_bias_comp = Anteil, den der Regler vorsteuert
    pad_bias_comp: float = 0.0
    sig_roll_arm: float = 1.0e-5   # m, Rollmoment je Newton Schub
    sig_aero: float = 0.15         # relativ auf cna_nose, cdc, cd_a
    sig_cp: float = 0.03           # m auf die Druckpunkte
    cna_base_lo: float = 0.3
    cna_base_hi: float = 2.0
    sig_pad_tilt: float = 0.5      # Grad, Schiefstand auf der Rampe
    # ----- Sensoren (noise skaliert alle Sensorfehler; 0 = ideale Sensoren) -----
    noise: float = 1.0
    gyro_bias: float = 0.03        # Grad/s nach dem Nullabgleich auf der Rampe
    gyro_scale: float = 0.003
    gyro_mis: float = 0.3          # Grad, Achsfehler
    gyro_noise: float = 0.05       # Grad/s je Takt
    gyro_vib: float = 0.3          # Grad/s je Takt zusaetzlich unter Schub
    acc_bias: float = 0.05         # m/s^2 nach der Sechs-Lagen-Kalibrierung
    acc_scale: float = 0.003
    acc_noise: float = 0.02        # m/s^2
    acc_vib: float = 1.0           # m/s^2 unter Schub
    mag_hard: float = 1.0          # uT Rest nach dem Ellipsoid-Fit
    mag_soft: float = 0.02
    mag_pad: float = 1.0           # uT Stoerfeld der Rampe (Stahl)
    mag_decl: float = 1.0          # Grad Fehler der Missweisung
    baro: bool = True
    baro_noise: float = 0.25       # m
    baro_off: float = 0.10         # m
    baro_kdyn: float = 0.05        # Anteil des Staudrucks, der als Hoehenfehler erscheint
    baro_hz: float = 50.0
    gps: str = "neo6m"             # "none", "neo6m", "m10", "rtk"
    gps_hz: float = 5.0
    gps_bias: float = 1.5          # m je Achse, langsam wandernd (Gauss-Markov)
    gps_bias_tau: float = 60.0     # s
    gps_white: float = 0.5         # m
    gps_vel: float = 0.10          # m/s
    gps_delay: float = 0.15        # s
    gps_g_limit: float = 4.0       # g, darueber Ausfall (u-blox "airborne < 4 g")
    gps_reacq: float = 1.0         # s
    cam: bool = False
    cam_hz: float = 20.0
    cam_noise: float = 0.4         # Grad
    cam_mis: float = 0.5           # Grad Einbaufehler (nach Kalibrierung)
    cam_delay: float = 0.06        # s
    cam_range: float = 40.0        # m
    cam_fov: float = 35.0          # Grad halber Oeffnungswinkel
    cam_blind_burn: bool = False   # True: Abgasstrahl verdeckt die Marke waehrend des Landebrennens
    lidar: bool = False
    lidar_range: float = 8.0       # m
    lidar_noise: float = 0.03      # m
    # ----- Kalman-Filter -----
    kf_sig_acc: float = 2.0        # m/s^2 (KALMAN_SIGMA_ACC_MS2)
    kf_bias_rw: float = 0.05       # m/s^2 / sqrt(s)
    kf_r_baro: float = 0.5         # m
    kf_r_gps: float = 1.0          # m
    kf_r_gps_vel: float = 0.15     # m/s
    kf_gate: float = 5.0           # Sigma
    # ----- Erfolgskriterien -----
    ok_vz: float = 3.0             # m/s
    ok_vh: float = 1.0             # m/s
    ok_tilt: float = 10.0          # Grad
    ok_radius: float = 1.0         # m
    # ----- Numerik -----
    dt: float = 0.004
    t_max: float = 30.0

    def with_(self, **kw) -> "PinpointConfig":
        return replace(self, **kw)

    @property
    def inertia_t(self) -> float:
        return self.I_t if self.I_t is not None else 0.0211 * (self.m_land + self.fuel) / 0.704


GPS_PRESETS = {
    "none": {},
    "neo6m": dict(gps_hz=5.0, gps_bias=1.5, gps_white=0.5, gps_vel=0.10, gps_delay=0.15, kf_r_gps=1.0, kf_r_gps_vel=0.15),
    "m10": dict(gps_hz=10.0, gps_bias=1.0, gps_white=0.3, gps_vel=0.05, gps_delay=0.08, kf_r_gps=0.7, kf_r_gps_vel=0.10),
    "rtk": dict(gps_hz=10.0, gps_bias=0.01, gps_white=0.01, gps_vel=0.03, gps_delay=0.08, kf_r_gps=0.03, kf_r_gps_vel=0.05),
}


def with_gps(cfg: PinpointConfig, kind: str) -> PinpointConfig:
    return replace(cfg, gps=kind, **GPS_PRESETS[kind])


def uncalibrated(cfg: PinpointConfig) -> PinpointConfig:
    """Sensorfehler ohne die Kalibrierung an der Werkbank (Datenblatt-Toleranzen, Magnetometer roh)."""
    return replace(cfg, gyro_scale=0.01, gyro_mis=1.0, acc_bias=0.3, acc_scale=0.01, mag_hard=15.0, mag_soft=0.10,
                   mag_decl=4.0, cam_mis=2.0, baro_kdyn=0.10)


# ---------------------------------------------------------------- Quaternionen (Felder der Form (N, 4))

def qmul(a, b):
    aw, ax, ay, az = a[:, 0], a[:, 1], a[:, 2], a[:, 3]
    bw, bx, by, bz = b[:, 0], b[:, 1], b[:, 2], b[:, 3]
    return np.stack([aw * bw - ax * bx - ay * by - az * bz,
                     aw * bx + ax * bw + ay * bz - az * by,
                     aw * by - ax * bz + ay * bw + az * bx,
                     aw * bz + ax * by - ay * bx + az * bw], axis=1)


def qexp(rv):
    """Drehvektor (N, 3) -> Quaternion."""
    th = np.linalg.norm(rv, axis=1)
    s = np.where(th > 1e-9, np.sin(0.5 * th) / np.maximum(th, 1e-12), 0.5)
    return np.column_stack([np.cos(0.5 * th), rv * s[:, None]])


def rotmat(q):
    """Drehmatrix Koerper -> Navigation, (N, 3, 3)."""
    w, x, y, z = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
    R = np.empty((len(q), 3, 3))
    R[:, 0, 0] = 1 - 2 * (y * y + z * z); R[:, 0, 1] = 2 * (x * y - w * z); R[:, 0, 2] = 2 * (x * z + w * y)
    R[:, 1, 0] = 2 * (x * y + w * z); R[:, 1, 1] = 1 - 2 * (x * x + z * z); R[:, 1, 2] = 2 * (y * z - w * x)
    R[:, 2, 0] = 2 * (x * z - w * y); R[:, 2, 1] = 2 * (y * z + w * x); R[:, 2, 2] = 1 - 2 * (x * x + y * y)
    return R


def quat_from_R(R):
    """Drehmatrix (N, 3, 3) -> Quaternion; der jeweils groesste Anteil bestimmt den Rechenweg."""
    m = R
    tr = m[:, 0, 0] + m[:, 1, 1] + m[:, 2, 2]
    c = np.stack([1 + tr, 1 + 2 * m[:, 0, 0] - tr, 1 + 2 * m[:, 1, 1] - tr, 1 + 2 * m[:, 2, 2] - tr], axis=1)
    k = np.argmax(c, axis=1)
    s = 2.0 * np.sqrt(np.maximum(c[np.arange(len(R)), k], 1e-12))
    q = np.empty((len(R), 4))
    w_ = np.stack([s / 4, (m[:, 2, 1] - m[:, 1, 2]) / s, (m[:, 0, 2] - m[:, 2, 0]) / s, (m[:, 1, 0] - m[:, 0, 1]) / s], axis=1)
    x_ = np.stack([(m[:, 2, 1] - m[:, 1, 2]) / s, s / 4, (m[:, 0, 1] + m[:, 1, 0]) / s, (m[:, 0, 2] + m[:, 2, 0]) / s], axis=1)
    y_ = np.stack([(m[:, 0, 2] - m[:, 2, 0]) / s, (m[:, 0, 1] + m[:, 1, 0]) / s, s / 4, (m[:, 1, 2] + m[:, 2, 1]) / s], axis=1)
    z_ = np.stack([(m[:, 1, 0] - m[:, 0, 1]) / s, (m[:, 0, 2] + m[:, 2, 0]) / s, (m[:, 1, 2] + m[:, 2, 1]) / s, s / 4], axis=1)
    for i, cand in enumerate((w_, x_, y_, z_)):
        sel = k == i
        q[sel] = cand[sel]
    return q / np.linalg.norm(q, axis=1, keepdims=True)


def _unit(a):
    return a / np.maximum(np.linalg.norm(a, axis=1, keepdims=True), 1e-12)


# ---------------------------------------------------------------- senkrechte Fuehrung und Zuendtabelle

def thrust_moments(cfg: PinpointConfig) -> SimpleNamespace:
    """Momente der Nennschubkurve vom Zeitpunkt t bis zum geplanten Aufsetzen te = Brennschluss - t_go_margin:
    M0 = int F, M1 = int tau F, M2 = int tau^2 F. Daraus rechnet ``vertical_law`` jeden Takt neu."""
    tc, fc = load_thrust_curve(cfg.curve)
    tb = float(tc[np.nonzero(fc)[0][-1] + 1])
    te = tb - cfg.t_go_margin
    tg = np.arange(0.0, te + 1e-9, 0.005)
    F = np.interp(tg, tc, fc)

    def rc(y):
        seg = 0.5 * (y[1:] + y[:-1]) * np.diff(tg)
        return np.concatenate([np.cumsum(seg[::-1])[::-1], [0.0]])

    return SimpleNamespace(t=tg, te=te, tb=tb, F=F, M0=rc(F), M1=rc(tg * F), M2=rc(tg * tg * F))


def vertical_law(cfg: PinpointConfig, mom, h, v, t_burn, scale, m, f_min, cos_tilt=1.0):
    """Geforderter Schubfaktor f in [f_min, 1] im Landebrennen.

    Der Feststoffmotor gibt den Schubverlauf vor (Spitze, dann Schwanz), die Drossel nimmt nur einen Anteil
    weg. Geplant wird deshalb mit der Kurve selbst: gesucht ist ein in der Zeit lineares Drosselprofil
    f(tau) = c0 + c1 tau, das mit dem restlichen Schub ``scale * F`` Hoehe 0 und Sinkrate -v_final zum
    geplanten Aufsetzen te erreicht (zwei Bedingungen, zwei Unbekannte, jeden Takt neu geloest; gestellt wird
    c0). Fuer konstanten Schub ist das die bekannte Zero-Effort-Miss/-Velocity-Regel. In der Endphase
    (unter h_final oder kurz vor te) wird die Sinkrate gehalten, unter h_cut gehen die Pads ganz hinein."""
    tbc = np.clip(t_burn, 0.0, mom.te)
    T = mom.te - tbc
    k = scale / m
    m0 = np.interp(tbc, mom.t, mom.M0); m1 = np.interp(tbc, mom.t, mom.M1); m2 = np.interp(tbc, mom.t, mom.M2)
    s0 = k * m0; s1 = k * (m1 - tbc * m0); s2 = k * (m2 - 2 * tbc * m1 + tbc * tbc * m0)
    zev = -cfg.v_final - v + G * T
    zem = -(h + v * T - 0.5 * G * T * T)
    det = s1 * s1 - s0 * s2                      # <= 0 (Cauchy-Schwarz)
    c0 = (zev * (T * s1 - s2) - s1 * zem) / np.minimum(det, -1e-9)
    f_now = np.maximum(scale * np.interp(tbc, mom.t, mom.F), 0.5)
    f_end = m * (G + cfg.kv_final * (-cfg.v_final - v)) / f_now
    f = np.where((h > cfg.h_final) & (T > cfg.t_go_min), c0, f_end)
    f = np.clip(f / np.maximum(cos_tilt, 0.7), f_min, 1.0)
    return np.where(h <= cfg.h_cut, f_min, f)


def landing_1d(cfg: PinpointConfig, h0, v0, scale=1.0, m=None, act_tau: float = 0.08, dt: float = 0.01):
    """Senkrechtes Landebrennen ab Schubbeginn im Zustand (h0, v0) mit idealer Messung: haertestes Aufsetzen
    (m/s, positiv) einschliesslich Huepfern und dem Fall nach einem Brennschluss in der Luft. Felder."""
    tc, fc = load_thrust_curve(cfg.curve)
    imp = np.concatenate([[0.0], np.cumsum(0.5 * (fc[1:] + fc[:-1]) * np.diff(tc))])
    tb = float(tc[np.nonzero(fc)[0][-1] + 1])
    h = np.array(h0, dtype=float).copy(); v = np.array(v0, dtype=float).copy()
    h, v, scale = np.broadcast_arrays(h, v, np.asarray(scale, dtype=float))
    h = h.copy(); v = v.copy()
    m0 = cfg.m_land if m is None else m
    f_act = np.ones_like(h)
    worst = np.zeros_like(h)
    ground = h <= 0.0
    mom = thrust_moments(cfg)
    t = 0.0
    while t < tb + 0.1:
        t_motor = scale * np.interp(t, tc, fc, left=0.0, right=0.0)
        mass = m0 - cfg.fuel * np.interp(t, tc, imp) / imp[-1]
        f_cmd = vertical_law(cfg, mom, h, v, t, scale, mass, cfg.f_min) if cfg.f_min < 1.0 else np.ones_like(h)
        f_cmd = np.where(ground, cfg.f_min, f_cmd)
        f_act = f_act + (f_cmd - f_act) * dt / (act_tau + dt)
        thrust = t_motor * f_act
        drag = 0.5 * cfg.rho * cfg.cd_a * v * v * np.where(v < 0, 1.0, -1.0)
        a = (thrust + drag) / mass - G
        lift = ground & (a > 0.0)
        ground = ground & ~lift
        v = np.where(ground, 0.0, v + a * dt)
        h = np.where(ground, 0.0, h + v * dt)
        hit = (~ground) & (h <= 0.0)
        worst = np.where(hit, np.maximum(worst, -v), worst)
        ground = ground | hit
        h = np.where(hit, 0.0, h); v = np.where(hit, 0.0, v)
        t += dt
    air = ~ground
    v_fall = np.sqrt(np.maximum(0.0, v * v + 2.0 * G * np.maximum(h, 0.0)))
    return np.where(air, np.maximum(worst, v_fall), worst)


_TABLES: dict = {}


def ignition_table(cfg: PinpointConfig):
    """Zuendhoehe als Funktion der Sinkgeschwindigkeit bei Schubbeginn: fuer jedes v die Hoehe, die das
    schlechteste Aufsetzen ueber die Motoren ``ign_scales`` und die Zuendverzuege ``ign_delays`` minimiert
    (Mitte des Bandes, das hoechstens 0,3 m/s ueber dem Minimum liegt). Liefert (v_grid, h_ign, J)."""
    key = (cfg.curve, cfg.m_land, cfg.fuel, cfg.f_min, cfg.cd_a, cfg.rho, cfg.t_go_margin, cfg.t_go_min, cfg.v_final,
           cfg.h_final, cfg.h_cut, cfg.kv_final, cfg.ign_scales, cfg.ign_delays)
    if key in _TABLES:
        return _TABLES[key]
    vg = np.concatenate([np.arange(1.0, 10.0, 1.0), np.arange(10.0, 46.0, 2.0)])
    hg = np.concatenate([np.arange(0.5, 20.0, 0.5), np.arange(20.0, 90.1, 1.0)])
    V, H = np.meshgrid(vg, hg, indexing="ij")
    worst = np.zeros_like(V)
    for sc in cfg.ign_scales:
        for dd in cfg.ign_delays:
            # der Schub kommt dd spaeter (frueher) als angenommen: freier Fall um dd verschoben
            h0 = H - V * dd - 0.5 * G * dd * abs(dd)
            v0 = -(V + G * dd)
            worst = np.maximum(worst, landing_1d(cfg, h0, v0, sc))
    h_ign = np.empty(len(vg)); j_ign = np.empty(len(vg))
    for i in range(len(vg)):
        jmin = worst[i].min()
        ok = np.nonzero(worst[i] <= jmin + 0.3)[0]
        # zusammenhaengendes Band um das Minimum
        k0 = int(np.argmin(worst[i])); lo = hi = k0
        while lo - 1 in ok:
            lo -= 1
        while hi + 1 in ok:
            hi += 1
        mid = 0.5 * (hg[lo] + hg[hi])
        h_ign[i] = mid; j_ign[i] = np.interp(mid, hg, worst[i])
    _TABLES[key] = (vg, h_ign, j_ign)
    return _TABLES[key]


# ---------------------------------------------------------------- Kalman-Filter je Achse

class AxisKF:
    """Drei unabhaengige Filter (Ost, Nord, oben) mit je [Position, Geschwindigkeit, Beschleunigungsfehler]."""

    def __init__(self, n: int, cfg: PinpointConfig):
        self.cfg = cfg
        z = np.zeros((n, 3))
        self.p, self.v, self.b = z.copy(), z.copy(), z.copy()
        self.Ppp = np.full((n, 3), 0.1 ** 2); self.Pvv = np.full((n, 3), 0.05 ** 2); self.Pbb = np.full((n, 3), 0.3 ** 2)
        self.Ppv, self.Ppb, self.Pvb = z.copy(), z.copy(), z.copy()

    def predict(self, a, dt):
        an = a - self.b
        self.p = self.p + self.v * dt + 0.5 * an * dt * dt
        self.v = self.v + an * dt
        c, d = -0.5 * dt * dt, -dt
        a0 = self.Ppp + dt * self.Ppv + c * self.Ppb
        a1 = self.Ppv + dt * self.Pvv + c * self.Pvb
        a2 = self.Ppb + dt * self.Pvb + c * self.Pbb
        b1 = self.Pvv + d * self.Pvb
        b2 = self.Pvb + d * self.Pbb
        s2 = self.cfg.kf_sig_acc ** 2
        self.Ppp = a0 + dt * a1 + c * a2 + s2 * 0.25 * dt ** 4
        self.Ppv = a1 + d * a2 + s2 * 0.5 * dt ** 3
        self.Ppb = a2
        self.Pvv = b1 + d * b2 + s2 * dt * dt
        self.Pvb = b2
        self.Pbb = self.Pbb + self.cfg.kf_bias_rw ** 2 * dt

    def _update(self, y, s, kp, kv, kb, r0, r1, r2, mask):
        gate = (y * y <= self.cfg.kf_gate ** 2 * s) & mask
        kp, kv, kb = (np.where(gate, k, 0.0) for k in (kp, kv, kb))
        self.p = self.p + kp * y; self.v = self.v + kv * y; self.b = self.b + kb * y
        self.Ppp, self.Ppv, self.Ppb = self.Ppp - kp * r0, self.Ppv - kp * r1, self.Ppb - kp * r2
        self.Pvv, self.Pvb = self.Pvv - kv * r1, self.Pvb - kv * r2
        self.Pbb = self.Pbb - kb * r2

    def update_pos(self, z, r, mask):
        """Positionsmessung z (N, 3) mit Varianz r; mask (N, 3) sagt, welche Komponenten gelten."""
        s = self.Ppp + r
        self._update(z - self.p, s, self.Ppp / s, self.Ppv / s, self.Ppb / s, self.Ppp, self.Ppv, self.Ppb, mask)

    def update_vel(self, z, r, mask):
        s = self.Pvv + r
        self._update(z - self.v, s, self.Ppv / s, self.Pvv / s, self.Pvb / s, self.Ppv, self.Pvv, self.Pvb, mask)


# ---------------------------------------------------------------- Streuung ziehen

def _draw(cfg: PinpointConfig, n: int, rng: np.random.Generator) -> SimpleNamespace:
    s, z = cfg.scatter, cfg.noise
    nrm = rng.standard_normal
    uni = rng.uniform

    P = SimpleNamespace()
    sm, sa, so, se = s * cfg.sc_mass, s * cfg.sc_act, s * cfg.sc_motor, s * cfg.sc_aero

    def around(nominal, lo, hi, g):     # gleichverteilt in [lo, hi]; mit g -> 0 auf den Nennwert zusammengezogen
        c = 0.5 * (lo + hi)
        return nominal + min(1.0, g) * (c - nominal) + g * 0.5 * (hi - lo) * uni(-1.0, 1.0, n)

    P.m_land = cfg.m_land + sm * cfg.sig_mass * nrm(n)
    P.It = cfg.inertia_t * (1 + sm * cfg.sig_inertia * nrm(n))
    P.Ia = cfg.I_a * (1 + sm * cfg.sig_inertia * nrm(n))
    P.l = cfg.lever + sm * cfg.sig_lever * nrm(n)
    P.cg = sm * cfg.sig_cg_lat * nrm((n, 2))
    P.s1 = 1 + so * cfg.sig_impulse * nrm(n); P.k1 = 1 + so * cfg.sig_burntime * nrm(n)
    P.s2 = 1 + so * cfg.sig_impulse * nrm(n); P.k2 = 1 + so * cfg.sig_burntime * nrm(n)
    P.d1 = np.full(n, 0.0)
    P.d2 = around(cfg.ign_delay_assumed, cfg.ign_delay_lo, cfg.ign_delay_hi, so)
    P.kg = 1 + sa * cfg.sig_gim_gain * nrm(n)
    P.goff = sa * cfg.sig_gim_off * DEG * nrm((n, 2))
    P.gdead = around(0.5 * (cfg.gim_dead_lo + cfg.gim_dead_hi), cfg.gim_dead_lo, cfg.gim_dead_hi, sa)
    P.gwn = around(cfg.gim_wn, cfg.gim_wn_lo, cfg.gim_wn_hi, sa)
    P.fmin = np.clip(cfg.f_min * (1 + sa * cfg.sig_fmin * nrm(n)), 0.05, 1.0) if cfg.f_min < 1.0 else np.ones(n)
    P.gamma = around(1.0, cfg.gamma_lo, cfg.gamma_hi, sa)
    P.padside = sa * cfg.sig_pad_side * DEG * nrm((n, 2))
    P.padside = P.padside + np.array([cfg.pad_side_bias * (1.0 - cfg.pad_bias_comp) * DEG, 0.0])
    P.roll = sm * cfg.sig_roll_arm * nrm(n)
    P.cna_nose = cfg.cna_nose * (1 + se * cfg.sig_aero * nrm(n))
    P.cdc = cfg.cdc * (1 + se * cfg.sig_aero * nrm(n))
    P.cda = cfg.cd_a * (1 + se * cfg.sig_aero * nrm(n))
    P.cna_base = around(cfg.cna_base, cfg.cna_base_lo, cfg.cna_base_hi, se)
    P.r_nose = cfg.z_cp_nose + se * cfg.sig_cp * nrm(n) - cfg.z_cg
    P.r_base = cfg.z_cp_base - cfg.z_cg + np.zeros(n)
    P.r_cross = cfg.z_cp_cross + se * cfg.sig_cp * nrm(n) - cfg.z_cg
    P.psi0 = uni(-np.pi, np.pi, n)                       # Ausrichtung auf der Rampe, beliebig
    P.tilt0 = np.column_stack([sm * cfg.sig_pad_tilt * DEG * nrm((n, 2)), np.zeros(n)])
    wdir = uni(-np.pi, np.pi, n)
    P.wind = cfg.wind10 * np.column_stack([np.cos(wdir), np.sin(wdir), np.zeros(n)])
    P.gust_sig = cfg.gust_frac * cfg.wind10
    # Sensoren
    P.gb = z * cfg.gyro_bias * DEG * nrm((n, 3))
    P.gs = z * cfg.gyro_scale * nrm((n, 3))
    P.gm = z * cfg.gyro_mis * DEG * nrm((n, 3))          # kleine Drehung der Sensorachsen
    P.ab = z * cfg.acc_bias * nrm((n, 3))
    P.as_ = z * cfg.acc_scale * nrm((n, 3))
    P.mag_hard = z * cfg.mag_hard * nrm((n, 3))
    P.mag_soft = z * cfg.mag_soft * nrm((n, 3))
    P.mag_pad = z * cfg.mag_pad * nrm((n, 3))
    P.decl = z * cfg.mag_decl * DEG * nrm(n)
    P.baro_off = z * cfg.baro_off * nrm(n)
    P.baro_k = z * cfg.baro_kdyn * nrm(n)
    P.cam_mis = z * cfg.cam_mis * DEG * nrm((n, 2))
    return P


# ---------------------------------------------------------------- der Lauf

def run(cfg: PinpointConfig, n: int = 200, seed: int = 0, keep: int = 0) -> dict:
    """``n`` Fluege gleichzeitig. Liefert je Lauf die Groessen beim Aufsetzen und unterwegs (Felder der Laenge
    n) und fuer die ersten ``keep`` Laeufe die Bahn (``traj``: Zeit, Position, Kippwinkel, Schaetzfehler)."""
    rng = np.random.default_rng(seed)
    P = _draw(cfg, n, rng)
    dt = cfg.dt
    ar = np.arange(n)
    tc, fc = load_thrust_curve(cfg.curve)
    imp = np.concatenate([[0.0], np.cumsum(0.5 * (fc[1:] + fc[:-1]) * np.diff(tc))])
    total = imp[-1]
    tb_nom = float(tc[np.nonzero(fc)[0][-1] + 1])
    throttled = cfg.f_min < 1.0
    hop = cfg.mission == "hop"
    if cfg.landing and cfg.mission == "fall":
        tab_v, tab_h, _ = ignition_table(cfg)
    mom = thrust_moments(cfg)
    target = np.array([cfg.target_e, cfg.target_n])
    zn = cfg.noise

    # ----- Wahrheit -----
    p = np.zeros((n, 3)); v = np.zeros((n, 3)); w = np.zeros((n, 3))
    yaw = np.column_stack([np.cos(0.5 * P.psi0), np.zeros(n), np.zeros(n), np.sin(0.5 * P.psi0)])
    q = qmul(yaw, qexp(P.tilt0))
    gim = np.zeros((n, 2)); gimd = np.zeros((n, 2)); thr = np.zeros(n); thrd = np.zeros(n)
    lifted = np.zeros(n, bool); alive = np.ones(n, bool)
    t_ign2 = np.full(n, np.inf)
    t_bo1 = np.full(n, np.inf)
    if cfg.swap_time is not None:
        swap_t = cfg.swap_time * np.random.default_rng(seed + 7919).uniform(0.7, 1.5, n)
    gust =P.gust_sig * rng.standard_normal((n, 3)) * np.array([1.0, 1.0, 0.5])
    g_a = np.exp(-dt / cfg.gust_tau); g_s = P.gust_sig * np.sqrt(1 - g_a * g_a)

    def thrust_state(t):
        tb1 = (t - P.d1) / P.k1
        t1 = P.s1 / P.k1 * np.interp(tb1, tc, fc, left=0.0, right=0.0)
        b1 = np.interp(tb1, tc, imp, left=0.0, right=total) / total
        with np.errstate(invalid="ignore"):
            tb2 = np.where(np.isfinite(t_ign2), (t - t_ign2 - P.d2) / P.k2, -1.0)
        t2 = P.s2 / P.k2 * np.interp(tb2, tc, fc, left=0.0, right=0.0)
        b2 = np.interp(tb2, tc, imp, left=0.0, right=total) / total
        if hop:
            return t1, t2, P.m_land - cfg.fuel * b1, tb1, tb2
        return t1, t2, P.m_land + cfg.fuel * (1.0 - b1) - cfg.fuel * b2, tb1, tb2

    def forces(t, v, q, w, gim, thr, wind):
        R = rotmat(q)
        t1, t2, m, _, _ = thrust_state(t)
        uc = np.clip(thr, 0.0, 1.0)
        T = (t1 + t2) * (1.0 - (1.0 - P.fmin) * uc ** P.gamma)
        th = P.kg[:, None] * gim + P.goff + P.padside * uc[:, None]
        split = (t1 - t2) / np.maximum(t1 + t2, 1e-6)
        if cfg.motor_offset and cfg.motor_cant:
            th = th + np.column_stack([-cfg.motor_offset / cfg.lever * split, np.zeros(n)])
        k = T / np.sqrt(1.0 + th[:, 0] ** 2 + th[:, 1] ** 2)
        fx, fy, fz = k * th[:, 0], k * th[:, 1], k
        mx = -P.cg[:, 1] * fz + P.l * fy
        my = -P.l * fx + P.cg[:, 0] * fz
        if cfg.motor_offset:
            my = my - cfg.motor_offset * split * fz
        mz = P.roll * T
        if cfg.aero:
            vb = np.einsum("nji,nj->ni", R, v - wind)
            vz_b = vb[:, 2]
            fwd = vz_b >= 0.0
            r_lin = np.where(fwd, P.r_nose, P.r_base)
            cna = np.where(fwd, P.cna_nose, P.cna_base)
            ux = vb[:, 0] + w[:, 1] * r_lin; uy = vb[:, 1] - w[:, 0] * r_lin
            kl = -0.5 * cfg.rho * cfg.a_ref * cna * np.abs(vz_b)
            flx, fly = kl * ux, kl * uy
            cx = vb[:, 0] + w[:, 1] * P.r_cross; cy = vb[:, 1] - w[:, 0] * P.r_cross
            kc = -0.5 * cfg.rho * P.cdc * cfg.a_plan * np.sqrt(cx * cx + cy * cy)
            fcx, fcy = kc * cx, kc * cy
            fx = fx + flx + fcx; fy = fy + fly + fcy
            fz = fz - 0.5 * cfg.rho * P.cda * np.abs(vz_b) * vz_b
            mx = mx - r_lin * fly - P.r_cross * fcy
            my = my + r_lin * flx + P.r_cross * fcx
        return R, T, m, np.stack([fx, fy, fz], axis=1), np.stack([mx, my, mz], axis=1)

    def deriv(t, S, cg, cu, wind, act):
        p_, v_, q_, w_, g_, gd_, u_, ud_ = S
        R, T, m, fb, M = forces(t, v_, q_, w_, g_, u_, wind)
        acc = np.einsum("nij,nj->ni", R, fb) / m[:, None]
        acc[:, 2] -= G
        wd = np.stack([(M[:, 0] - (P.Ia - P.It) * w_[:, 1] * w_[:, 2]) / P.It,
                       (M[:, 1] - (P.It - P.Ia) * w_[:, 2] * w_[:, 0]) / P.It,
                       M[:, 2] / P.Ia], axis=1)
        zero = np.zeros((n, 1))
        qd = 0.5 * qmul(q_, np.concatenate([zero, w_], axis=1))
        a1 = act[:, None]
        gdd = (P.gwn ** 2)[:, None] * (cg - g_) - (2 * cfg.gim_zeta * P.gwn)[:, None] * gd_
        udd = cfg.thr_wn ** 2 * (cu - u_) - 2 * cfg.thr_zeta * cfg.thr_wn * ud_
        return (v_ * a1, acc * a1, qd * a1, wd * a1, gd_, gdd, ud_, udd)

    # ----- Totzeiten und Verlaeufe -----
    n_gd = np.rint(P.gdead / dt).astype(int)
    n_td = int(round(cfg.thr_dead / dt))
    L = int(max(n_gd.max(), n_td)) + 2
    gbuf = np.zeros((L, n, 2)); ubuf = np.zeros((L, n))
    n_gps = int(round(cfg.gps_delay / dt)); n_cam = int(round(cfg.cam_delay / dt))
    LH = max(n_gps, n_cam) + 2
    hp = np.zeros((LH, n, 3)); hv = np.zeros((LH, n, 3)); hq = np.tile(q, (LH, 1, 1)); hqe = None

    # ----- Schaetzer: Startlage aus Beschleunigung und Magnetometer (TRIAD), Rest null -----
    R0 = rotmat(q)
    f_pad = np.einsum("nji,nj->ni", R0, np.tile([0.0, 0.0, G], (n, 1)))
    f_pad_m = (1 + P.as_) * f_pad + P.ab
    b_nav = np.array([0.0, 20.0, -44.5]) + P.mag_pad                      # uT: Nord 20, abwaerts 44,5 (Mitteleuropa)
    m_body = (1 + P.mag_soft) * np.einsum("nji,nj->ni", R0, b_nav) + P.mag_hard
    up_b = _unit(f_pad_m)
    east_b = _unit(np.cross(m_body, up_b))
    north_b = np.cross(up_b, east_b)
    Re0 = np.stack([east_b, north_b, up_b], axis=1)
    yaw_e = np.column_stack([np.cos(0.5 * P.decl), np.zeros(n), np.zeros(n), np.sin(0.5 * P.decl)])
    qe = qmul(yaw_e, quat_from_R(Re0))
    hqe = np.tile(qe, (LH, 1, 1))
    kf = AxisKF(n, cfg)
    heading_err0 = _heading_error(q, qe)

    # ----- Reglerzustand -----
    a_lp = np.full(n, G); f_model = np.ones(n); f_prev = np.ones(n); scale_est = np.ones(n)
    integ = np.zeros((n, 2)); w_lp = np.zeros((n, 2)); cmd_prev = np.zeros((n, 2))
    I_ass = cfg.inertia_t
    Kp = I_ass * cfg.att_wn ** 2; Kd = 2 * cfg.att_zeta * cfg.att_wn * I_ass; Ki = cfg.att_ki * Kp
    d_alpha = 1 - np.exp(-2 * np.pi * cfg.d_lpf_hz * dt) if cfg.d_lpf_hz > 0 else 1.0
    gim_max = cfg.gim_max * DEG

    # ----- GPS, Kamera -----
    gps_on = cfg.gps != "none"
    gps_every = max(1, int(round(1.0 / (cfg.gps_hz * dt))))
    gps_dt = gps_every * dt
    gb_a = np.exp(-gps_dt / cfg.gps_bias_tau); gb_s = cfg.gps_bias * np.sqrt(1 - gb_a * gb_a)
    gps_b0 = zn * cfg.gps_bias * rng.standard_normal((n, 2)); gps_b = gps_b0.copy()
    gps_out = np.zeros(n)
    cam_every = max(1, int(round(1.0 / (cfg.cam_hz * dt))))
    baro_every = max(1, int(round(1.0 / (cfg.baro_hz * dt))))

    # ----- Ergebnisse -----
    nan = np.full(n, np.nan)
    out = {k: nan.copy() for k in ("t_td", "vz", "vh", "tilt", "rate", "x", "y", "apogee", "v_bo", "tilt_boost",
                                   "tilt_ign", "h_ign", "v_ign", "off_ign", "vh_ign", "t_rel", "nav_err", "nav_err_ign",
                                   "sat_land", "tilt_est_err")}
    out["apogee"][:] = 0.0; out["tilt_boost"][:] = 0.0
    out["burning"] = np.zeros(n, bool); out["relift"] = np.zeros(n, bool)
    sat_cnt = np.zeros(n); burn_cnt = np.zeros(n)
    w_prev = w.copy()
    t_lift = np.full(n, np.inf)
    traj = {"t": [], "p": [], "tilt": [], "pe": [], "thr": [], "gim": []} if keep else None
    n_steps = int(round(cfg.t_max / dt))

    for k in range(n_steps):
        t = k * dt
        gust = g_a * gust + g_s * rng.standard_normal((n, 3)) * np.array([1.0, 1.0, 0.5])
        wind = P.wind * ((np.maximum(p[:, 2], 1.0) / 10.0) ** cfg.wind_exp)[:, None] + gust
        R, T, m, fb, _ = forces(t, v, q, w, gim, thr, wind)
        t1, t2, _, tb1, tb2 = thrust_state(t)
        on1 = t1 > 0.5; on2 = t2 > 0.5; on = on1 | on2
        acc_z = np.einsum("nj,nj->n", R[:, 2, :], fb) / m - G
        new_lift = (~lifted) & (acc_z > 0.0)
        t_lift[new_lift] = t
        lifted |= new_lift

        # ---------------- Sensoren ----------------
        f_true = np.where(lifted[:, None], fb / m[:, None], np.einsum("nji,nj->ni", R, np.tile([0.0, 0.0, G], (n, 1))))
        w_avg = 0.5 * (w_prev + w)
        w_prev = w.copy()
        w_mis = w_avg + np.cross(P.gm, w_avg)
        g_sig = zn * (cfg.gyro_noise + cfg.gyro_vib * on) * DEG
        w_m = (1 + P.gs) * w_mis + P.gb + g_sig[:, None] * rng.standard_normal((n, 3))
        a_sig = zn * (cfg.acc_noise + cfg.acc_vib * on)
        f_m = (1 + P.as_) * f_true + P.ab + a_sig[:, None] * rng.standard_normal((n, 3))
        hp[k % LH] = p; hv[k % LH] = v; hq[k % LH] = q

        # ---------------- Schaetzer ----------------
        qe = qmul(qe, qexp(w_m * dt))
        qe /= np.linalg.norm(qe, axis=1, keepdims=True)
        hqe[k % LH] = qe
        Re = rotmat(qe)
        a_nav = np.einsum("nij,nj->ni", Re, f_m)
        a_nav[:, 2] -= G
        kf.predict(a_nav, dt)
        if cfg.baro and k % baro_every == 0:
            speed2 = np.einsum("nj,nj->n", v - wind, v - wind)
            zb = p[:, 2] + P.baro_k * speed2 / (2 * G) + P.baro_off + zn * cfg.baro_noise * rng.standard_normal(n)
            mask = np.zeros((n, 3), bool); mask[:, 2] = True
            kf.update_pos(np.column_stack([kf.p[:, 0], kf.p[:, 1], zb]), cfg.kf_r_baro ** 2, mask)
        if gps_on and k % gps_every == 0:
            gps_b = gb_a * gps_b + zn * gb_s * rng.standard_normal((n, 2))
            a_g = np.linalg.norm(f_true, axis=1) / G
            gps_out = np.where(a_g > cfg.gps_g_limit, t + cfg.gps_reacq, gps_out)
            ok = (t >= gps_out)
            kd = (k - n_gps) % LH
            zp = hp[kd][:, :2] + (gps_b - gps_b0) + zn * cfg.gps_white * rng.standard_normal((n, 2))
            zv = hv[kd][:, :2] + zn * cfg.gps_vel * rng.standard_normal((n, 2))
            mask = np.zeros((n, 3), bool); mask[:, :2] = ok[:, None]
            zp3 = np.column_stack([zp + kf.v[:, :2] * cfg.gps_delay, kf.p[:, 2]])
            kf.update_pos(zp3, cfg.kf_r_gps ** 2, mask)
            kf.update_vel(np.column_stack([zv, kf.v[:, 2]]), cfg.kf_r_gps_vel ** 2, mask)
        if cfg.cam and k % cam_every == 0:
            kd = (k - n_cam) % LH
            pd, Rd = hp[kd], rotmat(hq[kd])
            los = np.column_stack([target - pd[:, :2], -pd[:, 2]])
            rng_ = np.linalg.norm(los, axis=1)
            lb = np.einsum("nji,nj->ni", Rd, los) / np.maximum(rng_, 1e-6)[:, None]
            ok = (pd[:, 2] > 0.3) & (rng_ < cfg.cam_range) & (-lb[:, 2] > np.cos(cfg.cam_fov * DEG)) & lifted
            if cfg.cam_blind_burn:
                ok &= ~on2
            ang = zn * cfg.cam_noise * DEG * rng.standard_normal((n, 2)) + P.cam_mis
            lb_m = _unit(np.column_stack([lb[:, 0] + ang[:, 0], lb[:, 1] + ang[:, 1], lb[:, 2]]))
            ln = np.einsum("nij,nj->ni", rotmat(hqe[kd]), lb_m)
            ok &= ln[:, 2] < -0.3
            h_e = np.maximum(kf.p[:, 2] - kf.v[:, 2] * cfg.cam_delay, 0.05)
            rho_ = h_e / np.maximum(-ln[:, 2], 0.3)
            zp = target - rho_[:, None] * ln[:, :2] + kf.v[:, :2] * cfg.cam_delay
            r_cam = (rho_ * (cfg.cam_noise + cfg.cam_mis) * DEG) ** 2 + 0.05 ** 2
            mask = np.zeros((n, 3), bool); mask[:, :2] = ok[:, None]
            kf.update_pos(np.column_stack([zp, kf.p[:, 2]]), r_cam[:, None], mask)
        if cfg.lidar and k % baro_every == 0:
            cz = R[:, 2, 2]
            rng_ = p[:, 2] / np.maximum(cz, 0.3)
            ok = lifted & (cz > np.cos(30 * DEG)) & (rng_ < cfg.lidar_range) & (rng_ > 0.05)
            zl = (rng_ + zn * cfg.lidar_noise * rng.standard_normal(n)) * Re[:, 2, 2]
            mask = np.zeros((n, 3), bool); mask[:, 2] = ok
            kf.update_pos(np.column_stack([kf.p[:, 0], kf.p[:, 1], zl]), (2 * cfg.lidar_noise) ** 2, mask)

        pe, ve = kf.p, kf.v
        h_e, vz_e = pe[:, 2], ve[:, 2]

        # ---------------- Landezuendung ----------------
        if cfg.landing and not hop:
            d_a = cfg.ign_delay_assumed
            if cfg.mission == "fall":
                can = lifted & alive & ~np.isfinite(t_ign2) & (~on1) & (tb1 > 1.0) & (vz_e < -1.0)
                h_p = h_e + vz_e * d_a - 0.5 * G * d_a * d_a
                v_p = vz_e - G * d_a
                ign = can & (h_p <= np.interp(-v_p, tab_v, tab_h) + cfg.ign_extra_m)
            elif cfg.swap_time is not None:
                t_bo1 = np.where(lifted & ~on1 & (tb1 > 1.0) & ~np.isfinite(t_bo1), t, t_bo1)
                ign = alive & ~np.isfinite(t_ign2) & (t >= t_bo1 + swap_t)
            else:
                ign = lifted & alive & ~np.isfinite(t_ign2) & (t >= tb_nom - cfg.overlap)
            if ign.any():
                t_ign2[ign] = t
                out["tilt_ign"][ign] = np.arccos(np.clip(R[ign, 2, 2], -1, 1)) / DEG
                out["h_ign"][ign] = p[ign, 2]; out["v_ign"][ign] = v[ign, 2]
                out["off_ign"][ign] = np.linalg.norm(p[ign, :2] - target, axis=1)
                out["vh_ign"][ign] = np.linalg.norm(v[ign, :2], axis=1)
                out["nav_err_ign"][ign] = np.linalg.norm(pe[ign, :2] - p[ign, :2], axis=1)
                if cfg.mission == "fall":
                    integ[ign] = 0.0

        # ---------------- Schubschaetzung und Drossel ----------------
        a_norm = np.linalg.norm(f_m, axis=1)
        a_lp = a_lp + (a_norm - a_lp) * dt / (cfg.a_norm_tau + dt)
        b1_a = np.interp(t, tc, imp, left=0.0, right=total) / total
        if hop:
            land = lifted & (t >= cfg.t_hop_switch) & cfg.landing
            tb2_a = np.full(n, t)
            on_l = on1
            m_a = cfg.m_land - cfg.fuel * b1_a
        else:
            land = np.isfinite(t_ign2)
            with np.errstate(invalid="ignore"):
                tb2_a = np.where(land, t - t_ign2 - cfg.ign_delay_assumed, 0.0)
            on_l = on2
            b2_a = np.interp(tb2_a, tc, imp, left=0.0, right=total) / total
            m_a = cfg.m_land + cfg.fuel * (1.0 - b1_a) - cfg.fuel * b2_a
        T_est = m_a * np.maximum(a_lp, 1.0)
        f_model = f_model + (f_prev - f_model) * dt / (0.08 + dt)
        t_full = T_est / np.maximum(f_model, 0.2)
        cz_e = Re[:, 2, 2]
        f_cmd = np.ones(n)
        if throttled:
            # Massstab der wahren Schubkurve aus dem gemessenen Schub (nur bei nennenswertem Nennschub)
            f_nom = np.interp(tb2_a, tc, fc, left=0.0, right=0.0)
            upd = land & on_l & (f_nom > 5.0) & ~(on1 & on2)
            ratio = np.clip(t_full / np.maximum(f_nom, 1.0), 0.7, 1.3)
            scale_est = np.where(upd, scale_est + (ratio - scale_est) * dt / (0.15 + dt), scale_est)
            f_land = vertical_law(cfg, mom, h_e, vz_e, tb2_a, scale_est, m_a, cfg.f_min, cz_e)
            f_cmd = np.where(land & on_l, f_land, f_cmd)
            if cfg.throttle_ascent:
                v_ref = np.minimum(cfg.v_asc_max, np.sqrt(2 * cfg.a_dec_ascent * np.maximum(cfg.h_apo - h_e, 0.0)))
                a_c = np.maximum(0.0, G + cfg.kv_ascent * (v_ref - vz_e))
                f_asc = np.clip(m_a * a_c / np.maximum(cz_e, 0.7) / np.maximum(t_full, 0.1), cfg.f_min, 1.0)
                f_cmd = np.where(on1 & lifted & ~land, f_asc, f_cmd)
            if cfg.swap_time is not None and cfg.swap_open_lead > 0.0:
                f_cmd = np.where(~land & (t >= tb_nom - cfg.swap_open_lead), 1.0, f_cmd)
            u_cmd = (1.0 - f_cmd) / (1.0 - cfg.f_min)
        else:
            u_cmd = np.zeros(n)
        f_prev = f_cmd

        # ---------------- seitliche Fuehrung -> Sollrichtung des Schubs ----------------
        ex = pe[:, :2] - target
        a_xy = np.zeros((n, 2)); tilt_lim = np.zeros(n)
        if cfg.lateral:
            tg = np.maximum(cfg.t_go_lat_min, tb_nom - tb2_a - cfg.t_go_margin)[:, None]
            a_land = -6.0 * ex / (tg * tg) - 4.0 * ve[:, :2] / tg
            lim_land = np.interp(h_e, [0.3, cfg.h_upright], [cfg.tilt_max_ground, cfg.tilt_max_land]) * DEG
            sel = land & on_l
            a_xy = np.where(sel[:, None], a_land, a_xy); tilt_lim = np.where(sel, lim_land, tilt_lim)
        if cfg.ascent_hold:
            sel = on1 & lifted & ~land
            a_hold = -cfg.kp_hold * ex - cfg.kd_hold * ve[:, :2]
            a_xy = np.where(sel[:, None], a_hold, a_xy); tilt_lim = np.where(sel, cfg.tilt_max_ascent * DEG, tilt_lim)
        a_thr = np.maximum(a_lp, 3.0)
        a_mag = np.linalg.norm(a_xy, axis=1)
        sc = np.minimum(1.0, a_thr * np.tan(tilt_lim) / np.maximum(a_mag, 1e-9))
        n_cmd = _unit(np.column_stack([a_xy * sc[:, None], a_thr]))

        # ---------------- Lageregler ----------------
        nb = np.einsum("nji,nj->ni", Re, n_cmd)
        err = np.column_stack([-nb[:, 1], nb[:, 0]])
        w_lp = w_lp + d_alpha * (w_m[:, :2] - w_lp)
        integ = np.clip(integ + np.where(on[:, None], err * dt, 0.0), -cfg.att_int_max, cfg.att_int_max)
        M = Kp * err + Ki * integ - Kd * w_lp
        lt = cfg.lever * T_est
        cmd = np.column_stack([-M[:, 1] / lt, M[:, 0] / lt])
        if cfg.motor_ff and cfg.motor_offset and not hop:
            f1_n = np.interp(t, tc, fc, left=0.0, right=0.0)
            f2_n = np.where(land, np.interp(tb2_a, tc, fc, left=0.0, right=0.0), 0.0)
            cmd[:, 0] -= cfg.motor_offset / cfg.lever * (f1_n - f2_n) / np.maximum(f1_n + f2_n, 1.0)
        cmd = np.clip(cmd, -gim_max, gim_max)
        cmd = np.where(on[:, None], cmd, 0.0)
        step = cfg.gim_slew * DEG * dt
        cmd = cmd_prev + np.clip(cmd - cmd_prev, -step, step)
        cmd_prev = cmd
        gbuf[k % L] = cmd; ubuf[k % L] = u_cmd
        cg = gbuf[(k - n_gd) % L, ar]
        cu = ubuf[(k - n_td) % L]

        # ---------------- Buchfuehrung ----------------
        tilt_now = np.arccos(np.clip(R[:, 2, 2], -1, 1)) / DEG
        fly = alive & lifted
        out["apogee"] = np.where(fly, np.maximum(out["apogee"], p[:, 2]), out["apogee"])
        out["tilt_boost"] = np.where(fly & on1, np.maximum(out["tilt_boost"], tilt_now), out["tilt_boost"])
        bo = fly & ~on1 & (tb1 > 1.0) & np.isnan(out["v_bo"])
        out["v_bo"][bo] = np.linalg.norm(v[bo], axis=1)
        lb_ = fly & land & on_l
        burn_cnt += lb_
        sat_cnt += lb_ & (np.max(np.abs(cmd), axis=1) >= 0.98 * gim_max)
        if keep:
            traj["t"].append(t); traj["p"].append(p[:keep].copy()); traj["tilt"].append(tilt_now[:keep].copy())
            traj["pe"].append(pe[:keep].copy()); traj["thr"].append(np.clip(thr[:keep], 0, 1).copy())
            traj["gim"].append(gim[:keep].copy() / DEG)

        # ---------------- Integration (RK4) ----------------
        act = (alive & lifted).astype(float)
        S = (p, v, q, w, gim, gimd, thr, thrd)
        k1 = deriv(t, S, cg, cu, wind, act)
        k2 = deriv(t + 0.5 * dt, tuple(s + 0.5 * dt * d for s, d in zip(S, k1)), cg, cu, wind, act)
        k3 = deriv(t + 0.5 * dt, tuple(s + 0.5 * dt * d for s, d in zip(S, k2)), cg, cu, wind, act)
        k4 = deriv(t + dt, tuple(s + dt * d for s, d in zip(S, k3)), cg, cu, wind, act)
        p, v, q, w, gim, gimd, thr, thrd = (s + dt / 6.0 * (a + 2 * b + 2 * c + d)
                                            for s, a, b, c, d in zip(S, k1, k2, k3, k4))
        q /= np.linalg.norm(q, axis=1, keepdims=True)
        gimd = np.clip(gimd, -cfg.gim_rate * DEG, cfg.gim_rate * DEG)

        # ---------------- Aufsetzen ----------------
        td = alive & lifted & (p[:, 2] <= 0.0) & (t - t_lift > 0.3)
        if td.any():
            Rn = rotmat(q[td])
            t1_, t2_, m_, _, tb2_ = thrust_state(t + dt)
            out["t_td"][td] = t + dt
            out["vz"][td] = -v[td, 2]; out["vh"][td] = np.linalg.norm(v[td, :2], axis=1)
            out["tilt"][td] = np.arccos(np.clip(Rn[:, 2, 2], -1, 1)) / DEG
            out["rate"][td] = np.linalg.norm(w[td, :2], axis=1) / DEG
            out["x"][td] = p[td, 0] - target[0]; out["y"][td] = p[td, 1] - target[1]
            tl_ = t1_ + t2_
            out["burning"][td] = tl_[td] > 0.5
            out["relift"][td] = (tl_[td] * P.fmin[td]) > m_[td] * G
            t_bo = tb_nom * P.k1 if hop else t_ign2 + P.d2 + tb_nom * P.k2
            out["t_rel"][td] = (t + dt) - t_bo[td]
            out["nav_err"][td] = np.linalg.norm(kf.p[td, :2] - p[td, :2], axis=1)
            Ren = rotmat(qe[td])
            out["tilt_est_err"][td] = np.arccos(np.clip(np.einsum("nj,nj->n", Rn[:, :, 2], Ren[:, :, 2]), -1, 1)) / DEG
            alive &= ~td
        if not alive.any():
            break

    out["sat_land"] = sat_cnt / np.maximum(burn_cnt, 1)
    out["miss"] = np.hypot(out["x"], out["y"])
    out["landed"] = ~alive
    out["ignited"] = np.isfinite(t_ign2) | hop
    out["heading_err0"] = heading_err0
    out["cfg"] = cfg
    if keep:
        out["traj"] = {kk: np.array(vv) for kk, vv in traj.items()}
    return out


def _heading_error(q, qe):
    """Kursfehler der Startlage in Grad (Drehung um die Hochachse zwischen Wahrheit und Schaetzung)."""
    R, Re = rotmat(q), rotmat(qe)
    d = np.arctan2(Re[:, 1, 0], Re[:, 0, 0]) - np.arctan2(R[:, 1, 0], R[:, 0, 0])
    return (d + np.pi) % (2 * np.pi) - np.pi


# ---------------------------------------------------------------- Auswertung

def success(res: dict, radius: float | None = None) -> np.ndarray:
    c = res["cfg"]
    r = c.ok_radius if radius is None else radius
    with np.errstate(invalid="ignore"):
        return (res["landed"] & ~res["relift"] & (res["vz"] <= c.ok_vz) & (res["vh"] <= c.ok_vh)
                & (res["tilt"] <= c.ok_tilt) & (res["miss"] <= r))


def summarize(res: dict) -> dict:
    """Kennzahlen eines Laufs: Trefferradien, Aufsetzgroessen und Erfolgsanteile."""
    c = res["cfg"]

    def pct(a, qq):
        a = a[np.isfinite(a)]
        return float(np.percentile(a, qq)) if len(a) else float("nan")

    with np.errstate(invalid="ignore"):
        soft = (res["landed"] & ~res["relift"] & (res["vz"] <= c.ok_vz) & (res["vh"] <= c.ok_vh)
                & (res["tilt"] <= c.ok_tilt))
    return {
        "n": len(res["landed"]),
        "apogee": pct(res["apogee"], 50), "v_bo": pct(res["v_bo"], 50),
        "tilt_boost_p95": pct(res["tilt_boost"], 95),
        "tilt_ign_p50": pct(res["tilt_ign"], 50), "tilt_ign_p95": pct(res["tilt_ign"], 95),
        "off_ign_p50": pct(res["off_ign"], 50), "off_ign_p95": pct(res["off_ign"], 95),
        "miss_p50": pct(res["miss"], 50), "miss_p95": pct(res["miss"], 95),
        "vz_p50": pct(res["vz"], 50), "vz_p95": pct(res["vz"], 95),
        "vh_p50": pct(res["vh"], 50), "vh_p95": pct(res["vh"], 95),
        "tilt_p50": pct(res["tilt"], 50), "tilt_p95": pct(res["tilt"], 95),
        "nav_p50": pct(res["nav_err"], 50), "nav_p95": pct(res["nav_err"], 95),
        "sat_land": float(np.nanmean(res["sat_land"])),
        "heading_p95": pct(np.abs(res["heading_err0"]) / DEG, 95),
        "relift": float(np.mean(res["relift"])),
        "soft": float(np.mean(soft)),
        "ok_1m": float(np.mean(success(res, 1.0))), "ok_2m": float(np.mean(success(res, 2.0))),
        "ok_5m": float(np.mean(success(res, 5.0))),
        "r_soft_p90": pct(np.where(soft, res["miss"], np.nan), 90),
    }


# ---------------------------------------------------------------- Flugprofile

def profile(name: str, **kw) -> PinpointConfig:
    """Die vier untersuchten Flugprofile und der Erstflug (nur Aufstieg) als Konfiguration.

    ``bps``      wie Scout F: frei steigen, antriebslos ueber den Gipfel, Landebrennen mit dem zweiten Motor
    ``langsam``  gedrosselt auf 25 m steigen und bis zum Brennschluss schweben, kurzer Fall, Landebrennen
    ``wechsel``  in 6 m schweben, Motor 2 zuendet vor dem Brennschluss von Motor 1, nie ohne Schub
    ``huepfer``  ein Motor: gedrosselt auf 3 m und auf demselben Motor wieder herunter
    ``erstflug`` Kartonaut 1 (704 g, ein Motor, keine Drossel): nur der Aufstieg, fuer die Windgrenze
    """
    base = {
        "bps": dict(mission="fall", m_land=0.60, f_min=0.5),
        "langsam": dict(mission="fall", m_land=0.60, f_min=0.35, throttle_ascent=True, h_apo=25.0, v_asc_max=6.0,
                        ascent_hold=True),
        "wechsel": dict(mission="handover", m_land=0.80, f_min=0.35, throttle_ascent=True, h_apo=6.0, v_asc_max=4.0,
                        ascent_hold=True),
        "huepfer": dict(mission="hop", m_land=0.80, f_min=0.35, throttle_ascent=True, h_apo=3.0, v_asc_max=3.0,
                        t_hop_switch=1.3, ascent_hold=True),
        "erstflug": dict(mission="fall", landing=False, m_land=0.676, I_t=0.0211, lever=0.19, z_cg=0.26, f_min=1.0),
    }[name]
    base.update(kw)
    return PinpointConfig(**base)
