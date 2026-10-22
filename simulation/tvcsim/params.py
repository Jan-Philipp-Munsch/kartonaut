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
        """``[Ix Iy Iz g l mis_y mis_z m_dry]`` wie der Constant-Block im Dynamics Model."""
        return (self.Ix, self.Iy, self.Iz, self.g, self.l, self.mis_y, self.mis_z, self.m_dry)


@dataclass
class MotorParams:
    """Schubmodell: zwei Motoren derselben Kurve, der zweite um ``secondburn`` Schritte spaeter."""

    curve: str = "E12"          # "E12" oder "F35" (data/<curve>_thrustcurve.csv)
    secondburn: int = 730       # Verzoegerung des zweiten Motors in Regelschritten (dt)
    second_motor: bool = True
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


@dataclass
class ControlParams:
    """Regler-Teilsystem (Simulink ``Controller``)."""

    kp: float = 1.0            # TVC6DOF.m: kp=1, ki=1, kd=0.1; pid_tuner.m: 3.1, 5, 0.385
    ki: float = 1.0
    kd: float = 0.1
    dt: float = 0.01           # s, Regeltakt (Zero-Order Hold)
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
    A_NORM_ALPHA: float = 0.1
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
    quantize_servo: bool = True   # Servo-Grad auf ganze Zahlen runden wie lroundf()
    apply_window: bool = True     # mechanische Fenster anwenden


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
    control: ControlParams = field(default_factory=ControlParams)
    firmware: FirmwareParams = field(default_factory=FirmwareParams)
    noise: NoiseParams = field(default_factory=NoiseParams)
    controller: str = "simulink"   # "simulink" oder "firmware"
    t_end: float = 12.0            # s, StopTime des Modells (Monte-Carlo: 7 s)
    substeps: int = 10             # RK4-Teilschritte je Regelschritt (dt/substeps = 1 ms)
    ground: bool = True            # Boden: auf der Rampe keine Bewegung nach unten, der Lauf endet bei der
                                   # Landung (Hoehe 0 nach dem Abheben). False = wie Simulink, ohne Boden.
    seed: int | None = None

    def with_(self, **kw) -> "SimParams":
        return replace(self, **kw)
