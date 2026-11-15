"""Parameter der TVC-Simulation.

Die Namen folgen `TVC6DOF.m` und dem Simulink-Modell `TVC6DOF_sim.slx`, damit man die
Werte wiedererkennt. Es gibt zwei Nominalsaetze (siehe README, Abschnitt Parameter):

* ``VehicleParams.nominal()`` - die Werte aus ``TVC6DOF.m`` (Monte-Carlo-Skript).
* ``VehicleParams.preload()`` - die Werte aus dem PreLoadFcn-Callback der ``.slx``.
  Die gelten, wenn das Modell geoeffnet wird, ohne vorher ``TVC6DOF.m`` auszufuehren,
  also vermutlich bei ``pid_tuner.m``.
* ``VehicleParams.cad()`` - Masse, Hebelarm und Traegheitsmomente aus dem CAD-Massenmodell
  ``cad/mass_properties.json`` (Startzustand mit vollem Motor, Konfiguration ``voll``, 981 g).
* ``VehicleParams.stand2b()`` - dasselbe aus ``cad/mass_stand2b.json``, der Modulbauweise
  Kartonaut 1 Stand 2b (22.10.2026): kuerzeres Rohr, CO2-Ausstoss, kein Rollmotor.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUT_DIR = Path(__file__).resolve().parent.parent / "out"
REPO_DIR = Path(__file__).resolve().parent.parent.parent
CAD_MASS_FILE = REPO_DIR / "cad" / "mass_properties.json"
STAND2B_MASS_FILE = REPO_DIR / "cad" / "mass_stand2b.json"
FUEL_PER_MOTOR_KG = 0.028   # TSP E12: 28 g Treibstoff

# Regeltakt. Die Firmware rechnet seit November 2026 mit 250 Hz (Servo-PWM 250 Hz, Gyro/Accel als Mittel
# der FIFO-Werte ueber den 4-ms-Takt); bis dahin 100 Hz wie das Simulink-Modell (dt = 0,01 s).
CONTROL_RATE_HZ = 250.0
DT_CONTROL = 1.0 / CONTROL_RATE_HZ    # 0,004 s, Vorgabe von ControlParams.dt
DT_SIMULINK = 0.01                    # Simulink-Modell und Firmware bis Oktober 2026 (100 Hz)

# Wirksames Traegheitsmoment des bewegten Kardans (Motor, Adapter, Motorrohr, Innenrahmen) fuer das
# Reaktionsmoment auf den Rumpf, Stand 2b (cad/mass_stand2b.md, Kardanpunkt 69,5 mm ueber der Duese):
# I_Drehpunkt ~ 1,0e-4 kg m^2 (Motor 64 g, Schwerpunkt 28 mm unter dem Drehpunkt: 0,8e-4; Adapter 15 g:
# 0,12e-4; Motorrohr und Innenrahmen: 0,1e-4) plus Kopplung m_g d l = 2,1e-3 kg m * 0,19 m = 4,1e-4
# (der Schwerpunkt des Kardans liegt unter dem Drehpunkt; seine Querbeschleunigung stoesst am Hebelarm l
# gegen den Rumpf). Zusammen ~5e-4 kg m^2, 2,4 % des Quer-Traegheitsmoments der Rakete (0,021).
GIMBAL_INERTIA_STAND2B = 5.0e-4


@dataclass
class VehicleParams:
    """Fahrzeugparameter, Eingang ``params`` des Blocks *Equations of Motion*."""

    Ix: float = 0.1            # kg m^2, Platzhalter (TVC6DOF.m)
    Iy: float = 0.1
    Iz: float = 0.1
    g: float = 9.81            # m/s^2
    l: float = 0.3             # m, Abstand TVC-Lager - Schwerpunkt
    mis_y: float = 0.0         # m, Fehlplatzierung des TVC-Lagers quer zur Laengsachse
    mis_z: float = 0.0
    m_dry: float = 0.94        # kg, alles ausser Treibstoff
    static_error_y: float = 0.0   # Grad, statischer Fehler der Servo-Nullstellung (Stufenprofil)
    static_error_z: float = 0.0   # Grad, statischer Fehler (konstant)
    servo_delay: float | None = None  # s, Totzeit des Servomodells; None = Wert aus dem Fit
    l_meas: float | None = None   # m, Hebelarm, mit dem der Regler rechnet (None = l)
    # Luftwiderstand (nicht im Simulink-Modell, seit 23.10.2026 als Option): D = -1/2 rho cd_a |v| v
    # entlang der Fluggeschwindigkeit, angriffsfrei (kein Moment). cd_a = Cd * A in m^2;
    # Rumpf Ø 75 mm: A = 0,0044 m^2, Cd ~ 0,6..0,8 -> cd_a ~ 0,003. 0 = aus (wie Simulink).
    cd_a: float = 0.0
    rho: float = 1.2
    # Reaktionsmoment des Kardans (nicht im Simulink-Modell, seit 05.11.2026 als Option): beschleunigt
    # der Servo den Kardan um die Querachse, dreht der Rumpf mit -gimbal_inertia * theta_ddot dagegen
    # (Drehimpuls bleibt), und das sieht der Gyro. Wirksames Traegheitsmoment in kg m^2 bezogen auf den
    # Schwerpunkt der Rakete (I_Drehpunkt + m_Kardan * d * l), 0 = aus (wie Simulink).
    # Stand 2b: GIMBAL_INERTIA_STAND2B = 5e-4.
    gimbal_inertia: float = 0.0

    @classmethod
    def nominal(cls) -> "VehicleParams":
        """Nominalwerte aus TVC6DOF.m."""
        return cls()

    @classmethod
    def preload(cls) -> "VehicleParams":
        """Werte aus dem PreLoadFcn der .slx (gelten in pid_tuner.m ohne TVC6DOF.m)."""
        return cls(Ix=3 / 800 + 1 / 24, Iy=3 / 800 + 1 / 24, Iz=3 / 800 + 1 / 24,
                   l=0.5, m_dry=0.7, static_error_y=1.0, static_error_z=0.6,
                   l_meas=0.5)

    @classmethod
    def cad(cls, config: str = "liftoff", path: Path | None = None) -> "VehicleParams":
        """Massenmodell aus ``cad/mass_properties.json`` (CadQuery-Stabmodell, 21.10.2026).

        CAD-Achsen: z = Laengsachse, x/y quer. Simulink: x = Laengsachse, y/z quer. Also
        ``Ix = Izz``, ``Iy = Ixx``, ``Iz = Iyy``; ``l`` ist der Hebelarm Kardan-Drehpunkt bis
        Schwerpunkt; ``m_dry`` = Masse der Konfiguration minus 28 g Treibstoff eines Motors
        (die Treibstoffmasse kommt zur Laufzeit ueber ``MotorParams.fuel_model`` dazu).
        Die seitliche Schwerpunktlage wird als Fehlplatzierung ``mis_y/mis_z`` uebernommen.
        """
        with open(path or CAD_MASS_FILE, encoding="utf-8") as f:
            cfg = json.load(f)["configurations"][config]
        I = cfg["inertia_kgm2"]
        lat = cfg.get("cg_lateral_m", [0.0, 0.0])
        return cls(Ix=I["Izz"], Iy=I["Ixx"], Iz=I["Iyy"],
                   l=cfg["lever_arm_m"], l_meas=cfg["lever_arm_m"],
                   m_dry=cfg["mass_kg"] - FUEL_PER_MOTOR_KG,
                   mis_y=float(lat[0]), mis_z=float(lat[1]))

    @classmethod
    def stand2b(cls, config: str = "liftoff", path: Path | None = None) -> "VehicleParams":
        """Massenbudget der Modulbauweise Stand 2b (``cad/mass_stand2b.py``), gleiches Format wie ``cad()``."""
        return cls.cad(config=config, path=path or STAND2B_MASS_FILE)

    @property
    def l_ctrl(self) -> float:
        return self.l if self.l_meas is None else self.l_meas

    def as_eom_params(self) -> tuple[float, ...]:
        """``[Ix Iy Iz g l mis_y mis_z m_dry]`` wie der Constant-Block im Dynamics Model,
        dazu ``cd_a, rho`` fuer den Luftwiderstand (0 = aus)."""
        return (self.Ix, self.Iy, self.Iz, self.g, self.l, self.mis_y, self.mis_z, self.m_dry, self.cd_a, self.rho)

    @classmethod
    def light(cls, m_landing_kg: float, fuel_per_motor_kg: float = FUEL_PER_MOTOR_KG, cd_a: float = 0.003) -> "VehicleParams":
        """Leichte Landekonfiguration (Jan, 23.10.2026: deutlich unter 700 g). Geometrie wie
        ``erstflug`` (Hebelarm 0,242 m), Traegheit aus dem Erstflug-Modell (0,046 kg m^2 bei
        0,761 kg) mit der Masse skaliert. ``m_landing_kg`` ist die Masse bei der Landung mit
        vollem zweitem Motor; ``m_dry`` = ohne jeden Treibstoff."""
        m_dry = m_landing_kg - fuel_per_motor_kg
        scale = m_landing_kg / 0.761
        return cls(Ix=0.0006 * scale, Iy=0.046 * scale, Iz=0.046 * scale, l=0.242, m_dry=m_dry,
                   static_error_y=0.5, static_error_z=0.5, cd_a=cd_a)


@dataclass
class MotorParams:
    """Schubmodell: zwei Motoren derselben Kurve, der zweite um ``secondburn`` Schritte spaeter."""

    curve: str = "E12"          # "E12" oder "F35" (data/<curve>_thrustcurve.csv)
    secondburn: int = 730       # Verzoegerung des zweiten Motors in Schritten zu secondburn_dt (Simulink: 7,3 s)
    secondburn_dt: float = DT_SIMULINK   # s je Schritt; fest 10 ms, unabhaengig vom Regeltakt
    second_motor: bool = True
    # Zuendung des zweiten Motors: "time" nach secondburn Schritten (Simulink), "landing" aus
    # dem Zustand (Landebrennen, tvcsim.landing: Zuendhoehe als Funktion der Sinkgeschwindigkeit)
    second_mode: str = "time"
    igniter_delay: float = 0.10     # s, Zuendverzug Anzuender -> Schub (Landemodus)
    thrust_scale2: float = 1.0      # Schubtoleranz des zweiten Motors (Landemodus)
    landing_alt_sigma: float = 0.3  # m, Rauschen der Hoehenschaetzung fuer die Zuendentscheidung
    landing_vz_sigma: float = 0.3   # m/s, Rauschen der Sinkgeschwindigkeit
    landing_margin_m: float = 0.0   # m, Zuendung so viel hoeher als die Tabelle (Sicherheitsaufschlag)
    landing_v_tol: float = 0.5      # m/s, Zielwert |v| beim Aufsetzen der Planung
    # Treibstoffmodell fuer die Masse m = m_dry + m_fuel/1000:
    #  "signalbuilder": die Kurve aus dem Signal Builder der .slx (60 g -> 0 g bis 3,45 s,
    #                   nur der erste Motor), 1:1 wie das Simulink-Modell
    #  "impulse":       fuel_mass_g je Motor, Abbrand proportional zum Impuls der Schubkurve,
    #                   fuer beide Motoren (Annahme aus Plan 21.10., Abschnitt 3.3)
    fuel_model: str = "signalbuilder"
    fuel_mass_g: float = 28.0   # g je Motor (TSP E12), nur fuer fuel_model="impulse"


@dataclass
class ServoParams:
    """Uebertragungsfunktion Servo-Soll (Grad) -> Kardanwinkel (Grad), Ersatz fuer ``tf5``.

    PT2 mit Totzeit: G(s) = K * wn^2 / (s^2 + 2 zeta wn s + wn^2) * exp(-s tau).
    Die Vorgabewerte stammen aus ``scripts/fit_servo.py`` (SG90 im Kardan,
    ``data/servo_step_response.csv``). Werte bitte nach einem neuen Fit hier eintragen.
    """

    K: float = 0.1662          # Kardan-Grad je Servo-Grad (DC-Gain, 1/6,0)
    wn: float = 36.7           # rad/s (5,8 Hz)
    zeta: float = 0.598        # -
    tau: float = 0.030         # s, Totzeit (Fit: RMS 0,57 Grad ueber die ganze Messung)
    # Gain-Block "Multiply" (6) hinter tf5 im Simulink-Modell: Umrechnung TVC-Grad -> Servo-Grad.
    # 6 aus der Identifikation (35 Servo-Grad -> 5,5 Kardan-Grad), Config.h sagt 23.
    servo_deg_per_tvc_deg: float = 6.0
    sat_deg: float = 5.0       # Saettigung des Kommandos (Block "Saturation", +-5 Grad)
    # Stellratenbegrenzung des Servos in Servo-Grad/s (0 = aus, wie Simulink). Am Kardan wirkt
    # rate_limit_dps / servo_deg_per_tvc_deg. SG90-Messung: ~70 Grad/s am Kardan (bei Gain 6: 420 Servo-Grad/s).
    rate_limit_dps: float = 0.0

    @classmethod
    def w5652h(cls, t_eq: float = 0.025, rate_s_per_60: float = 0.06, tau: float = 0.004,
               servo_deg_per_tvc_deg: float = 6.0) -> "ServoParams":
        """Annahme fuer die FrSky Xact W5652H am 2S-Akku, bis E01 sie vermisst (Datenblatt: 0,05 s/60 Grad
        bei 8,4 V, 0,10 s bei 4,2 V; am 2S ~0,06 s). Verzoegerung erster Ordnung t_eq (20..30 ms), hier als
        aperiodisches PT2 (zeta = 1, wn = 2 / t_eq, gleiche mittlere Verzoegerung), damit die
        Kardanbeschleunigung fuer das Reaktionsmoment endlich bleibt; Totzeit tau (PWM-Rahmen 250 Hz, im
        Mittel 2 ms, plus Servo-Elektronik); Ratenbegrenzung 60 Grad / rate_s_per_60."""
        return cls(K=1.0 / servo_deg_per_tvc_deg, wn=2.0 / t_eq, zeta=1.0, tau=tau,
                   servo_deg_per_tvc_deg=servo_deg_per_tvc_deg, rate_limit_dps=60.0 / rate_s_per_60)


@dataclass
class ThrottleParams:
    """Schubdrossel nach BPS Scout F (Jan, 23.10.2026): zwei Pads schwenken symmetrisch unter der
    Duese in den Abgasstrahl und lenken ihn seitlich ab. Modell: Axialschub = Motorschub * f(u),
    Kommando u in [0, 1] (0 = Pads draussen), f(u) = 1 - (1 - f_min) * u, dahinter dieselbe
    Servodynamik wie am Kardan (PT2 mit Totzeit, ServoParams). Wirkt auf den Gesamtschub, also
    auf jeden Motor im Rohr. f_min ist unbekannt und wird in der Studie variiert (0,3 / 0,5 / 0,7);
    Experiment E05 misst die Kennlinie am Pruefstand. Zusatzmasse ca. 60 g (zwei Servos, Pads, Gehaeuse)."""

    enabled: bool = False
    f_min: float = 0.5
    mass_kg: float = 0.06
    # Landeregler mit Drossel (tvcsim.throttle.ThrottleLandingController)
    h_reserve_m: float = 3.0      # zuenden, sobald ein Vollschub-Brennen hoechstens so hoch ueber dem Boden stoppen wuerde
    throttle_after_s: float = 0.8 # erst nach der Schubspitze drosseln (E12: 28 N bei 0,54 s, ab 0,8 s unter 14 N)
    act_tau_s: float = 0.12       # Ersatzzeitkonstante der Pads (PT1) fuer die eigene Schaetzung des Schubfaktors
    t_go_margin_s: float = 0.15   # die Fuehrung plant das Aufsetzen so viel vor dem geschaetzten Brennschluss
    t_go_min_s: float = 0.3       # kleinste Restzeit, mit der die Fuehrung rechnet
    kv: float = 3.0               # 1/s, Rueckfuehrung der Sinkrate in der Endphase
    v_final_ms: float = 0.5       # Sollsinkrate unter h_final
    h_final_m: float = 0.8
    h_cut_m: float = 0.25         # darunter Pads ganz rein (Schubabbruch beim Aufsetzen, gegen den Huepfer)
    thrust_scale_assumed: float = 0.9   # Kurve, mit der der Regler plant: der schwaechste erwartete Motor (-10 %);
                                        # einen staerkeren drosselt er weg (die wahre Kurve: MotorParams.thrust_scale2)


@dataclass
class ControlParams:
    """Regler-Teilsystem (Simulink ``Controller``)."""

    kp: float = 1.0            # TVC6DOF.m: kp=1, ki=1, kd=0.1; pid_tuner.m: 3.1, 5, 0.385
    ki: float = 1.0
    kd: float = 0.1
    dt: float = DT_CONTROL     # s, Regeltakt (Zero-Order Hold); 250 Hz wie die Firmware, DT_SIMULINK = 0,01 wie Simulink
    error_scale: float = -0.01  # Gain12: Winkel (Grad) -> Regelfehler
    secondburn: int = 730      # Step-Block, der die I-Anteile bei secondburn/100 s zuruecksetzt

    @classmethod
    def tuner(cls) -> "ControlParams":
        """Letzter Stand von pid_tuner.m."""
        return cls(kp=3.1, ki=5.0, kd=0.385)

    @classmethod
    def preload(cls) -> "ControlParams":
        """PreLoadFcn der .slx."""
        return cls(kp=2.0, ki=1.0, kd=0.004)


@dataclass
class FirmwareParams:
    """Konstanten aus ``firmware/src/Config.h``, wie sie ``Control_updatePY`` benutzt."""

    PY_KP: float = 5.0
    PY_KI: float = 0.0
    PY_KD: float = 1.0
    PY_ERROR_SCALE: float = -100.0
    MASS_KG: float = 0.70
    MOMENT_ARM_M: float = 0.30
    A_NORM_MIN: float = 1.0
    # |a|-Tiefpass, seit 11/2026 zeitbasiert (main.cpp: lowpassStep(y, x, A_NORM_TAU_S, dt) = y + (x - y) dt/(tau + dt)).
    # A_NORM_ALPHA != None rechnet wie vorher mit festem Faktor je Takt (0,1 bei 100 Hz ~ tau 95 ms).
    A_NORM_TAU_S: float = 0.095
    A_NORM_ALPHA: float | None = None
    PY_INT_LIMIT: float = 500.0   # Anti-Windup des I-Anteils, Grad s (ControlLaw.cpp)
    SERVO_YAW_GAIN: float = -23.0
    SERVO_YAW_OFFSET: float = 92.5
    SERVO_PITCH_GAIN: float = 23.0
    SERVO_PITCH_OFFSET: float = 82.5
    SERVO_YAW_MIN_DEG: float = 70.0
    SERVO_YAW_MAX_DEG: float = 115.0
    SERVO_PITCH_MIN_DEG: float = 60.0
    SERVO_PITCH_MAX_DEG: float = 105.0
    G_MS2: float = 9.81
    # Abbildung auf die Simulink-Achsen (siehe README, Koordinaten):
    # Firmware x = Yaw  -> Simulink-Koerperachse y, Firmware y = Pitch -> Simulink z.
    # Die Firmware rechnet delta = +asin(M/(l m |a|)), das Simulink-Modell braucht fuer
    # dasselbe Moment th = asin(-M/(l T)). Das Vorzeichen sitzt in der Hardware in
    # SERVO_*_GAIN und ist am Tisch zu pruefen; hier ist es ein Parameter.
    axis_sign_yaw: float = -1.0
    axis_sign_pitch: float = -1.0
    coast_center: bool = True     # ohne Schub (T < 0,5 N) Servos auf Mitte, wie main.cpp ausserhalb von BOOST/LANDING_BURN
    quantize_servo: bool = False  # True = auf ganze Grad runden wie die Firmware bis 22.10.2026 (PWMServo);
                                  # seitdem 16-Bit-PWM ohne Rundung
    apply_window: bool = True     # mechanische Fenster anwenden
    # 250-Hz-Takt, wie Config.h seit 05.11.2026 (0 = aus):
    D_LPF_HZ: float = 30.0        # PY_D_LPF_HZ: Tiefpass 1. Ordnung auf omega nur im D-Anteil (Grenzfrequenz Hz)
    SERVO_SLEW_DPS: float = 2300.0  # PY_SLEW_TVC_DPS 100 Kardan-Grad/s x |SERVO_*_GAIN| 23, in Servo-Grad/s


@dataclass
class NoiseParams:
    """Avionics-Block: Rauschen der Messwerte, alle mit Abtastzeit dt."""

    enabled: bool = True
    q_angle_sigma: float = 0.01    # rad, zufaellige Kleinstdrehung der Quaternion
    w_sigma: float = 0.4           # Grad/s, ein Skalar auf alle drei Komponenten (so im Modell)
    rdd_sigma: float = 1.0         # m/s^2, Random-Number-Block (Varianz 1), ein Skalar auf alle drei
    # Was der Beschleunigungssensor liefert:
    #  "rdd":            die inertiale Beschleunigung inkl. g, wie im Simulink-Modell
    #  "specific_force": Schub/Masse im Koerpersystem, wie eine echte IMU
    accel_model: str = "rdd"
    # Gyro und Beschleunigung als Mittel ueber den Regeltakt (Boxcar ueber [t_k - dt, t_k], Gruppenlaufzeit
    # dt/2: bei 250 Hz 2 ms), wie die Firmware die FIFO-Werte (960 Hz) je 4-ms-Takt mittelt.
    # False = Momentanwert zum Takt (Simulink-Modell, Firmware bei 100 Hz).
    imu_average: bool = True


@dataclass
class MonteCarloParams:
    """Streuungen aus TVC6DOF.m (``randn * v`` als Abweichung vom Nominalwert)."""

    runs: int = 100
    t_end: float = 7.0
    Ix_v: float = 1e-4
    Iy_v: float = 1e-4
    Iz_v: float = 1e-4
    m_dry_v: float = 1e-4
    servo_delay_v: float = 0.01
    mis_y_v: float = 0.001
    mis_z_v: float = 0.001
    static_error_y_v: float = 1.0
    static_error_z_v: float = 1.0
    l_v: float = 0.01


@dataclass
class SimParams:
    vehicle: VehicleParams = field(default_factory=VehicleParams)
    motor: MotorParams = field(default_factory=MotorParams)
    servo: ServoParams = field(default_factory=ServoParams)
    throttle: ThrottleParams = field(default_factory=ThrottleParams)
    control: ControlParams = field(default_factory=ControlParams)
    firmware: FirmwareParams = field(default_factory=FirmwareParams)
    noise: NoiseParams = field(default_factory=NoiseParams)
    controller: str = "simulink"   # "simulink" oder "firmware"
    t_end: float = 12.0            # s, StopTime des Modells (Monte-Carlo: 7 s)
    substeps: int | None = None    # RK4-Teilschritte je Regelschritt; None = so viele, dass dt/substeps ~ 1 ms
    ground: bool = True            # Boden: auf der Rampe keine Bewegung nach unten, der Lauf endet bei der
                                   # Landung (Hoehe 0 nach dem Abheben). False = wie Simulink, ohne Boden.
    seed: int | None = None

    def with_(self, **kw) -> "SimParams":
        return replace(self, **kw)

    @property
    def n_substeps(self) -> int:
        if self.substeps is not None:
            return int(self.substeps)
        return max(1, int(round(self.control.dt / 1e-3)))

    def at_rate(self, rate_hz: float, imu_average: bool | None = None) -> "SimParams":
        """Kopie mit Regeltakt ``rate_hz``. ``imu_average`` None: Mittelung an ab 200 Hz (Firmware ab
        November 2026), bei 100 Hz Momentanwert wie bisher; so rechnet ``at_rate(100)`` die alten Zahlen."""
        avg = (rate_hz >= 200.0) if imu_average is None else imu_average
        return replace(self, control=replace(self.control, dt=1.0 / rate_hz),
                       noise=replace(self.noise, imu_average=avg))
