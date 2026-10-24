"""Lineares Modell einer Querachse, LQR-Entwurf und Stabilitaetsanalyse im Parameterraum.

Alle Regler dieses Pakets fordern ein Moment ``M_c`` und rechnen es ueber ``th = asin(-M_c/(l T_est))``
in einen TVC-Winkel um (``moments_to_commands``). Fuer kleine Winkel ist die Strecke je Querachse
dann, im Momentenbereich geschrieben:

    theta_dd = M / I,      M = kappa * G_servo(s) * M_c(t - tau)

mit dem Servo als PT2 (``wn``, ``zeta``), der Totzeit ``tau`` und dem Faktor

    kappa = (l * T) / (l_ctrl * T_est),

der alle Fehler der Modellinversion zusammenfasst (Hebelarm, Schubschaetzung; bei der Firmware
``MASS_KG`` und ``MOMENT_ARM_M``). Ohne Aerodynamik haengt die Dynamik nicht vom Winkel selbst
ab, deshalb braucht die Stabilitaetsanalyse ``theta`` nicht als Streckenzustand; die Regler
integrieren die Drehrate selbst (``rot``).

Das Modell wird exakt mit Zero-Order-Hold zum Regeltakt ``dt`` diskretisiert, die Totzeit als
Kette verzoegerter Eingaenge (auch gebrochene Vielfache von ``dt``). Darauf sitzt der
LQR-Entwurf (``design_lqr``), der PD-Entwurf mit derselben Kostenfunktion ohne Aktuatormodell
(``design_pd``) und die Analyse des geschlossenen Kreises (``closed_loop``, ``spectral_radius``,
``gain_margin``, ``delay_margin``).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import numpy as np
from scipy.linalg import expm, solve_discrete_are

RAD = math.pi / 180.0


def zoh(A: np.ndarray, B: np.ndarray, h: float) -> tuple[np.ndarray, np.ndarray]:
    """Exakte ZOH-Diskretisierung: ``Ad = e^{A h}``, ``Bd = int_0^h e^{A s} ds B``."""
    n, m = B.shape
    if h <= 0.0:
        return np.eye(n), np.zeros((n, m))
    M = np.zeros((n + m, n + m))
    M[:n, :n] = A
    M[:n, n:] = B
    E = expm(M * h)
    return E[:n, :n], E[:n, n:]


@dataclass
class AxisPlant:
    """Strecke einer Querachse im Momentenbereich (siehe Modulkopf)."""

    I: float                    # kg m^2, Traegheitsmoment quer
    kappa: float = 1.0          # Verstaerkungsfehler der Modellinversion, 1 = perfekt
    wn: float = 36.7            # rad/s, Servo-PT2
    zeta: float = 0.598
    tau: float = 0.030          # s, Totzeit
    dt: float = 0.01            # s, Regeltakt

    def continuous(self, with_theta: bool = True) -> tuple[np.ndarray, np.ndarray, dict]:
        """``x = [theta, omega, m, m_dot]`` (theta optional), Eingang verzoegertes ``M_c``."""
        idx = {}
        n = 0
        if with_theta:
            idx["theta"] = n; n += 1
        idx["omega"] = n; n += 1
        idx["m"] = n; n += 1
        idx["mdot"] = n; n += 1
        A = np.zeros((n, n)); B = np.zeros((n, 1))
        if with_theta:
            A[idx["theta"], idx["omega"]] = 1.0
        A[idx["omega"], idx["m"]] = 1.0 / self.I
        A[idx["m"], idx["mdot"]] = 1.0
        A[idx["mdot"], idx["m"]] = -self.wn ** 2
        A[idx["mdot"], idx["mdot"]] = -2.0 * self.zeta * self.wn
        B[idx["mdot"], 0] = self.kappa * self.wn ** 2
        return A, B, idx

    def discretize(self, with_theta: bool = True, with_integral: bool = False) -> tuple[np.ndarray, np.ndarray, dict]:
        """ZOH-Diskretisierung mit Totzeitkette.

        Zustand ``[theta?, omega, m, mdot, z_1..z_n, s?]`` mit ``z_j(k) = u(k-j)`` und
        ``s(k+1) = s(k) + dt theta(k)`` (Integralzustand fuer LQI). ``idx["chain"]`` listet die
        Kettenindizes, ``idx["u_direct"]`` sagt, ob ``u(k)`` direkt wirkt (tau < dt).
        """
        A, B, idx = self.continuous(with_theta)
        nc = A.shape[0]
        dt = self.dt
        tau = max(0.0, self.tau)
        d = int(math.floor(tau / dt + 1e-9))
        f = tau - d * dt
        if f < 1e-9:
            f = 0.0
        n_chain = d + (1 if f > 0.0 else 0)
        n = nc + n_chain + (1 if with_integral else 0)
        Ad = np.zeros((n, n)); Bd = np.zeros((n, 1))

        Ac, B0 = zoh(A, B, dt - f)              # Anteil von u(k-d), wirkt waehrend [f, dt)
        Ad[:nc, :nc] = expm(A * dt)
        if f > 0.0:
            _, Bf = zoh(A, B, f)                 # Anteil von u(k-d-1), wirkt waehrend [0, f)
            B1 = expm(A * (dt - f)) @ Bf
        else:
            B1 = None

        chain = list(range(nc, nc + n_chain))
        idx = dict(idx)
        idx["chain"] = chain
        idx["u_direct"] = (d == 0)
        # u(k-d): direkt oder aus z_d
        if d == 0:
            Bd[:nc, :] += B0
        else:
            Ad[:nc, chain[d - 1]] += B0[:, 0]
        # u(k-d-1) bei gebrochener Totzeit
        if B1 is not None:
            Ad[:nc, chain[d]] += B1[:, 0]
        # Kette schieben
        if n_chain:
            Bd[chain[0], 0] = 1.0
            for j in range(1, n_chain):
                Ad[chain[j], chain[j - 1]] = 1.0
        if with_integral:
            s = n - 1
            idx["integ"] = s
            Ad[s, s] = 1.0
            Ad[s, idx["theta"]] = dt
        return Ad, Bd, idx


@dataclass
class LQRWeights:
    """Bryson-Regel: ``Q = diag(1/x_max^2)``, ``R = 1/M_max^2``."""

    theta_max_deg: float = 3.0
    omega_max_dps: float = 30.0
    M_max: float = 0.35          # N m, etwa l T sin(5 Grad) fuer das CAD-Fahrzeug
    int_max_deg_s: float = 2.0   # nur mit Integralzustand


@dataclass
class LQRDesign:
    """Ergebnis von ``design_lqr``: Gewinnvektor und das Entwurfsmodell."""

    K: np.ndarray               # 1 x n, u = -K x
    Ad: np.ndarray
    Bd: np.ndarray
    idx: dict
    plant: AxisPlant
    weights: LQRWeights
    integral: bool
    state_names: list[str] = field(default_factory=list)

    def predictor(self) -> tuple[np.ndarray, np.ndarray, list[int]]:
        """Teilsystem ``[m, mdot, Kette]``: der Servopraediktor des Reglers (haengt nicht von theta, omega ab)."""
        sel = [self.idx["m"], self.idx["mdot"]] + list(self.idx["chain"])
        return self.Ad[np.ix_(sel, sel)], self.Bd[sel, :], sel

    def closed_loop_eigs(self) -> np.ndarray:
        return np.linalg.eigvals(self.Ad - self.Bd @ self.K)


def design_lqr(plant: AxisPlant, weights: LQRWeights = LQRWeights(), integral: bool = False) -> LQRDesign:
    """Diskreter LQR auf dem Entwurfsmodell (Winkel in rad, Momente in N m)."""
    Ad, Bd, idx = plant.discretize(with_theta=True, with_integral=integral)
    n = Ad.shape[0]
    Q = np.zeros((n, n))
    Q[idx["theta"], idx["theta"]] = 1.0 / (weights.theta_max_deg * RAD) ** 2
    Q[idx["omega"], idx["omega"]] = 1.0 / (weights.omega_max_dps * RAD) ** 2
    if integral:
        Q[idx["integ"], idx["integ"]] = 1.0 / (weights.int_max_deg_s * RAD) ** 2
    R = np.array([[1.0 / weights.M_max ** 2]])
    P = solve_discrete_are(Ad, Bd, Q, R)
    K = np.linalg.solve(R + Bd.T @ P @ Bd, Bd.T @ P @ Ad)
    names = [""] * n
    for k, v in idx.items():
        if isinstance(v, int) and not isinstance(v, bool):
            names[v] = k
    for j, c in enumerate(idx["chain"]):
        names[c] = f"u(k-{j + 1})"
    return LQRDesign(K=K, Ad=Ad, Bd=Bd, idx=idx, plant=plant, weights=weights, integral=integral,
                     state_names=names)


def design_pd(I: float, weights: LQRWeights = LQRWeights(), dt: float = 0.01,
              integral: bool = False) -> tuple[float, float, float]:
    """Dieselbe Kostenfunktion, aber ohne Aktuatormodell (ideales Servo, keine Totzeit).

    Liefert ``(K_theta, K_omega, K_int)`` in N m/rad, N m/(rad/s), N m/(rad s): das ist der
    modellbasierte PD (bzw. PID) als Spezialfall des LQR fuer den Doppelintegrator.
    """
    A = np.array([[0.0, 1.0], [0.0, 0.0]])
    B = np.array([[0.0], [1.0 / I]])
    Ad, Bd = zoh(A, B, dt)
    if integral:
        Ad = np.block([[Ad, np.zeros((2, 1))], [np.array([[dt, 0.0]]), np.ones((1, 1))]])
        Bd = np.vstack([Bd, np.zeros((1, 1))])
    n = Ad.shape[0]
    Q = np.zeros((n, n))
    Q[0, 0] = 1.0 / (weights.theta_max_deg * RAD) ** 2
    Q[1, 1] = 1.0 / (weights.omega_max_dps * RAD) ** 2
    if integral:
        Q[2, 2] = 1.0 / (weights.int_max_deg_s * RAD) ** 2
    R = np.array([[1.0 / weights.M_max ** 2]])
    P = solve_discrete_are(Ad, Bd, Q, R)
    K = np.linalg.solve(R + Bd.T @ P @ Bd, Bd.T @ P @ Ad)[0]
    return float(K[0]), float(K[1]), (float(K[2]) if integral else 0.0)


def gains_to_control_params(K_theta: float, K_omega: float, K_int: float = 0.0, dt: float = 0.01):
    """``(K_theta, K_omega, K_int)`` -> ``ControlParams`` des Simulink-Reglers.

    Simulink: ``u = kp (-0,01 rot_deg) + ki int(-0,01 rot_deg) + kd (-w_dps)``, also
    ``kp = K_theta * RAD * 100``, ``kd = K_omega * RAD``, ``ki = K_int * RAD * 100``.
    Firmware-Gewinne (Skala -100) sind ``Kp = kp``, ``Ki = ki``, ``Kd = 100 kd``.
    """
    from .params import ControlParams
    return ControlParams(kp=K_theta * RAD * 100.0, ki=K_int * RAD * 100.0, kd=K_omega * RAD, dt=dt)


def control_params_to_gains(cp) -> tuple[float, float, float]:
    """Umkehrung von ``gains_to_control_params``."""
    return cp.kp / (RAD * 100.0), cp.kd / RAD, cp.ki / (RAD * 100.0)


# ---------------------------------------------------------------------------
# Regler als lineare zeitdiskrete Systeme (Eingang omega in rad/s, Ausgang M_c)
# ---------------------------------------------------------------------------

@dataclass
class ControllerLTI:
    """``x_c(k+1) = Ac x_c + Bc omega + Bu u``, ``u = Cc x_c + Dc omega``."""

    Ac: np.ndarray
    Bc: np.ndarray
    Bu: np.ndarray
    Cc: np.ndarray
    Dc: float
    name: str = ""


def pid_lti(K_theta: float, K_omega: float, K_int: float, dt: float, form: str = "simulink") -> ControllerLTI:
    """PID auf ``rot = int(omega)``.

    ``form="simulink"``: ``rot(k) = sum_{j<k} omega_j dt`` (Integrator laeuft dem Takt nach),
    I-Anteil per Trapez wie ``SimulinkController``.
    ``form="firmware"``: ``rot += omega dt`` vor dem Regler (``main.cpp``), ``rot_int += rot dt``.
    Ohne I-Anteil (``K_int = 0``) entfaellt der Integratorzustand.
    """
    if form == "simulink":
        Ac = np.array([[1.0, 0.0], [dt, 1.0]])
        Bc = np.array([[dt], [0.5 * dt * dt]])
        Cc = np.array([[-K_theta, -K_int]])
        Dc = -K_omega
    elif form == "firmware":
        # rot_new = rot + dt w; eint_new = eint + dt rot_new
        Ac = np.array([[1.0, 0.0], [dt, 1.0]])
        Bc = np.array([[dt], [dt * dt]])
        Cc = np.array([[-K_theta - K_int * dt, -K_int]])
        Dc = -K_omega - K_theta * dt - K_int * dt * dt
    else:
        raise ValueError(form)
    if K_int == 0.0:
        Ac, Bc, Cc = Ac[:1, :1], Bc[:1, :], Cc[:, :1]
    return ControllerLTI(Ac, Bc, np.zeros((Ac.shape[0], 1)), Cc, float(Dc), name=f"pid-{form}")


def lqr_lti(design: LQRDesign) -> ControllerLTI:
    """LQR mit Servopraediktor: Zustand ``[rot, m^, mdot^, Kette, s^]``, ``theta^ = rot``."""
    dt = design.plant.dt
    Ap, Bp, sel = design.predictor()
    npred = len(sel)
    n = 1 + npred + (1 if design.integral else 0)
    Ac = np.zeros((n, n)); Bc = np.zeros((n, 1)); Bu = np.zeros((n, 1))
    Ac[0, 0] = 1.0; Bc[0, 0] = dt                       # rot(k+1) = rot + dt omega
    Ac[1:1 + npred, 1:1 + npred] = Ap
    Bu[1:1 + npred, :] = Bp
    if design.integral:
        Ac[n - 1, n - 1] = 1.0
        Ac[n - 1, 0] = dt                               # s(k+1) = s + dt rot
    K = design.K[0]
    idx = design.idx
    Cc = np.zeros((1, n))
    Cc[0, 0] = -K[idx["theta"]]
    for j, si in enumerate(sel):
        Cc[0, 1 + j] = -K[si]
    if design.integral:
        Cc[0, n - 1] = -K[idx["integ"]]
    Dc = -K[idx["omega"]]
    return ControllerLTI(Ac, Bc, Bu, Cc, float(Dc), name="lqi" if design.integral else "lqr")


def closed_loop(plant: AxisPlant, ctrl: ControllerLTI) -> np.ndarray:
    """Systemmatrix des geschlossenen Kreises (Strecke ohne theta, siehe Modulkopf)."""
    Ap, Bp, idx = plant.discretize(with_theta=False)
    npl = Ap.shape[0]
    Cp = np.zeros((1, npl)); Cp[0, idx["omega"]] = 1.0
    A11 = Ap + Bp @ (ctrl.Dc * Cp)
    A12 = Bp @ ctrl.Cc
    A21 = ctrl.Bc @ Cp + ctrl.Bu @ (ctrl.Dc * Cp)
    A22 = ctrl.Ac + ctrl.Bu @ ctrl.Cc
    return np.block([[A11, A12], [A21, A22]])


def spectral_radius(A: np.ndarray) -> float:
    return float(np.max(np.abs(np.linalg.eigvals(A))))


def decay_rate(A: np.ndarray, dt: float) -> float:
    """Abklingrate des langsamsten Pols in 1/s (``-ln(rho)/dt``); negativ = instabil."""
    return -math.log(max(spectral_radius(A), 1e-300)) / dt


def is_stable(plant: AxisPlant, ctrl: ControllerLTI, tol: float = 1e-9) -> bool:
    return spectral_radius(closed_loop(plant, ctrl)) < 1.0 - tol


def gain_margin(plant: AxisPlant, ctrl: ControllerLTI, k_max: float = 50.0, iters: int = 40) -> float:
    """Groesster Faktor auf ``kappa``, bei dem der Kreis noch stabil ist (Bisektion)."""
    if not is_stable(plant, ctrl):
        return 0.0
    lo, hi = 1.0, k_max
    if is_stable(replace(plant, kappa=plant.kappa * hi), ctrl):
        return float("inf")
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if is_stable(replace(plant, kappa=plant.kappa * mid), ctrl):
            lo = mid
        else:
            hi = mid
    return lo


def gain_margin_low(plant: AxisPlant, ctrl: ControllerLTI, iters: int = 40) -> float:
    """Kleinster Faktor auf ``kappa`` (< 1), bei dem der Kreis noch stabil ist; 0 wenn beliebig klein."""
    if not is_stable(plant, ctrl):
        return 1.0
    lo, hi = 0.0, 1.0
    if is_stable(replace(plant, kappa=plant.kappa * 1e-3), ctrl):
        return 0.0
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if is_stable(replace(plant, kappa=plant.kappa * mid), ctrl):
            hi = mid
        else:
            lo = mid
    return hi


def delay_margin(plant: AxisPlant, ctrl: ControllerLTI, tau_max: float = 0.3, step: float = 0.001) -> float:
    """Groesste Totzeit, bei der der Kreis noch stabil ist (Raster ``step``)."""
    if not is_stable(plant, ctrl):
        return 0.0
    tau = plant.tau
    while tau + step <= tau_max + 1e-12:
        if not is_stable(replace(plant, tau=tau + step), ctrl):
            return tau
        tau += step
    return float("inf")
