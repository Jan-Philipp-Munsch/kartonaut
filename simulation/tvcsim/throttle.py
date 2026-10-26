"""Schubdrossel (Scout-F-Pads) und Landeregler mit Drossel (Jan, 23.10.2026).

Ohne Drossel hat die Landung mit einem Feststoffmotor nur den Zuendzeitpunkt als Stellgroesse
(``landing.py``). Mit Drossel wird daraus eine Regelung:

1. **Zuendung mit Reserve.** Gezuendet wird, sobald ein Brennen mit vollem Schub (Pads draussen)
   die Rakete hoechstens ``h_reserve`` ueber dem Boden zum Stehen braechte, gerechnet mit dem
   schwaechsten erwarteten Motor (``thrust_scale_assumed`` = 0,9, also -10 %). Die Rakete hat dann
   immer etwas zu viel Bremsvermoegen, das die Drossel wegnimmt. Reicht das Bremsvermoegen nie
   (zu schnell), gilt die Zuendung im Minimum der Aufsetzkosten wie ohne Drossel.
2. **Zeitbasierte Fuehrung.** Waehrend der Schubspitze (``throttle_after_s``) bleiben die Pads
   draussen: dort wird das meiste Bremsvermoegen geholt, und aus dem Beschleunigungssensor wird
   der Massstab der wahren Schubkurve geschaetzt (``T_mess = m |a| - Luftwiderstand`` gegen die
   Nennkurve, Tiefpass). Danach ist die Restbrenndauer ``t_go`` die harte Grenze: der Boden muss
   erreicht sein, bevor der Motor ausgeht. Die Fuehrung fordert die Schubbeschleunigung, die Hoehe
   und Sinkrate in ``t_go`` auf 0 bzw. ``-v_final`` bringt (Zero-Effort-Miss/-Velocity, lineares
   Beschleunigungsprofil): ``a_T = 6 ZEM / t_go^2 - 2 ZEV / t_go`` mit
   ``ZEM = -(h + v t_go - g t_go^2 / 2)`` und ``ZEV = -v_final - (v - g t_go)``. Schubbedarf
   ``T_req = m a_T - D``, Drossel ``f = T_req / T_verfuegbar`` in [f_min, 1]. Unter ``h_final``
   wird die Sinkrate auf ``-v_final`` gehalten, unter ``h_cut`` gehen die Pads ganz hinein
   (Schubabbruch), sonst hebt der Schwanz der Kurve die aufgesetzte Rakete wieder ab.
3. **Am Boden** bleibt die Rakete nur liegen, wenn ``f_min * T < m g``; sonst hebt sie wieder ab.
   Das ist die Bedingung an die Drosselspanne.

Das Modell der Pads ist linear in u: ``f(u) = 1 - (1 - f_min) u``; die Kennlinie misst
Experiment E05.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .landing import G, LandingPlanner, load_thrust_curve
from .params import ThrottleParams


def throttle_factor(u: float, f_min: float) -> float:
    u = 0.0 if u < 0.0 else (1.0 if u > 1.0 else u)
    return 1.0 - (1.0 - f_min) * u


def stop_height(t_curve, f_curve, m: float, h0: float, v0: float, cd_a: float, rho: float, fuel_kg: float,
                scale: float = 1.0, dt: float = 5e-3, t0: float = 0.0, f_now: float = 1.0, act_tau: float = 0.0) -> float:
    """Hoehe, in der ein Brennen mit vollem Schub aus (h0, v0) zum Stehen kommt (v >= 0); die
    Schubkurve wird ab ``t0`` (Zeit seit Schubbeginn) gelesen. Steht die Drossel gerade auf
    ``f_now`` < 1, kommt der volle Schub erst mit der Pad-Zeitkonstante ``act_tau`` zurueck
    (f(t) = 1 - (1 - f_now) exp(-t/tau)). Negativ = Boden vorher erreicht; -inf = kommt bis zum
    Brennschluss nicht zum Stehen."""
    imp = np.concatenate([[0.0], np.cumsum(0.5 * (f_curve[1:] + f_curve[:-1]) * np.diff(t_curve))])
    total = imp[-1] if imp[-1] > 0 else 1.0
    tb = float(t_curve[np.nonzero(f_curve)[0][-1] + 1])
    h, v, t = h0, v0, max(0.0, t0)
    t_start = t
    if v0 >= 0.0:
        return h0
    while t < tb + 0.05:
        T = scale * float(np.interp(t, t_curve, f_curve, left=0.0, right=0.0))
        if act_tau > 0.0 and f_now < 1.0:
            T *= 1.0 - (1.0 - f_now) * np.exp(-(t - t_start) / act_tau)
        mass = m - fuel_kg * float(np.interp(t, t_curve, imp, left=0.0, right=total)) / total
        D = 0.5 * rho * cd_a * v * v * (1.0 if v < 0 else -1.0)
        v += ((T + D) / mass - G) * dt
        h += v * dt
        t += dt
        if v >= 0.0:
            return h
        if h <= 0.0:
            return h
    return float("-inf")


@dataclass
class ThrottleLandingController:
    curve: str
    m: float                    # Masse bei der Landung (mit Drossel und vollem Motor)
    tp: ThrottleParams
    cd_a: float = 0.0
    rho: float = 1.2
    fuel_kg: float = 0.0
    igniter_delay: float = 0.1
    dt_ctrl: float = 0.01

    def __post_init__(self) -> None:
        self.t_curve, self.f_curve = load_thrust_curve(self.curve)
        self.f_est = 1.0            # Schaetzung des wirksamen Schubfaktors (PT1 auf das eigene Kommando)
        self.scale_est = self.tp.thrust_scale_assumed   # Massstab der wahren Kurve, aus |a| geschaetzt
        self.burn_time = float(self.t_curve[np.nonzero(self.f_curve)[0][-1] + 1])
        self.planner = LandingPlanner(self.curve, self.m, self.cd_a, self.rho, self.fuel_kg, self.igniter_delay,
                                      self.dt_ctrl, self.tp.thrust_scale_assumed)
        self.last = {}

    # --- Zuendung ---
    def should_ignite(self, h: float, v: float) -> bool:
        if v > -self.planner.min_speed:
            return False
        h_p, v_p = self.planner.predicted(h, v, self.igniter_delay)
        hs = stop_height(self.t_curve, self.f_curve, self.m, h_p, v_p, self.cd_a, self.rho, self.fuel_kg,
                         self.tp.thrust_scale_assumed)
        self.last["stop_height"] = hs
        if hs == float("-inf"):
            return self.planner.should_ignite(h, v)     # Bremsvermoegen reicht nicht: bestes Minimum
        return hs <= self.tp.h_reserve_m

    # --- Drossel waehrend des Brennens ---
    def drag(self, v: float) -> float:
        return 0.5 * self.rho * self.cd_a * v * v if v < 0 else 0.0

    def update_thrust_estimate(self, t_burn: float, a_meas: float | None, m: float, v: float) -> None:
        """Massstab der wahren Schubkurve aus der gemessenen spezifischen Kraft (nur bei nennenswertem Schub)."""
        if a_meas is None or t_burn > self.tp.throttle_after_s:
            return                      # nur in der Spitze schaetzen: dort stehen die Pads sicher draussen (f = 1)
        T_nom = float(np.interp(t_burn, self.t_curve, self.f_curve, left=0.0, right=0.0))
        if T_nom > 5.0:
            ratio = (m * a_meas - self.drag(v)) / T_nom
            ratio = min(1.3, max(0.7, ratio))
            self.scale_est += (ratio - self.scale_est) * min(1.0, self.dt_ctrl / 0.15)

    def throttle_command(self, t_since_ignition: float, h: float, v: float, m_now: float | None = None,
                         a_meas: float | None = None) -> float:
        """Kommando u in [0, 1] (0 = voller Schub). ``a_meas``: gemessene spezifische Kraft |a| [m/s^2]."""
        m = m_now if m_now is not None else self.m
        t_burn = t_since_ignition - self.igniter_delay
        self.update_thrust_estimate(t_burn, a_meas, m, v)
        T_avail = self.scale_est * float(np.interp(t_burn, self.t_curve, self.f_curve, left=0.0, right=0.0))
        if T_avail <= 0.1 or v >= 0.0:
            u = 0.0
            self._track(u)
            self.last.update({"T_avail": T_avail, "u": u, "hs": float("nan"), "v_ref": 0.0})
            return u
        if t_burn < self.tp.throttle_after_s:
            # Spitze der Kurve: Pads draussen, hier wird das meiste Bremsvermoegen geholt
            u = 0.0
            self._track(u)
            self.last.update({"T_avail": T_avail, "u": u, "hs": float("nan"), "v_ref": 0.0})
            return u
        if h > self.tp.h_final_m:
            # Fuehrung auf Hoehe 0 und Sinkrate -v_final zum (geschaetzten) Brennschluss
            t_go = max(self.tp.t_go_min_s, self.burn_time - t_burn - self.tp.t_go_margin_s)
            zem = -(h + v * t_go - 0.5 * G * t_go * t_go)
            zev = -self.tp.v_final_ms - (v - G * t_go)
            a_T = 6.0 * zem / (t_go * t_go) - 2.0 * zev / t_go
            T_req = max(0.0, m * a_T - self.drag(v))
            f = min(1.0, max(self.tp.f_min, T_req / T_avail))
            u = (1.0 - f) / (1.0 - self.tp.f_min) if self.tp.f_min < 1.0 else 0.0
            self._track(u)
            self.last.update({"T_avail": T_avail, "T_req": T_req, "f_cmd": f, "u": u, "v_ref": 0.0,
                              "scale_est": self.scale_est, "t_go": t_go, "zem": zem, "zev": zev})
            return u
        if h <= self.tp.h_cut_m:
            # Aufsetzen: Pads ganz rein, sonst hebt der Schwanz der Kurve die Rakete wieder ab
            u = 1.0
            self._track(u)
            self.last.update({"T_avail": T_avail, "u": u, "hs": float("nan"), "v_ref": -self.tp.v_final_ms})
            return u
        # Endphase: Sinkrate halten
        v_ref = -self.tp.v_final_ms
        a_cmd = G + self.tp.kv * (v_ref - v)
        T_req = max(0.0, m * a_cmd - self.drag(v))
        f = min(1.0, max(self.tp.f_min, T_req / T_avail))
        u = (1.0 - f) / (1.0 - self.tp.f_min) if self.tp.f_min < 1.0 else 0.0
        self._track(u)
        self.last.update({"T_avail": T_avail, "T_req": T_req, "f_cmd": f, "u": u, "v_ref": v_ref, "hs": float("nan")})
        return u

    def _track(self, u: float) -> None:
        """PT1-Schaetzung des wirksamen Schubfaktors aus dem eigenen Kommando."""
        f_cmd = throttle_factor(u, self.tp.f_min)
        a = self.dt_ctrl / max(self.tp.act_tau_s, self.dt_ctrl)
        self.f_est += (f_cmd - self.f_est) * a


def simulate_landing_1d(apogee: float, m_ctrl: float, tp: ThrottleParams, cd_a: float = 0.003, rho: float = 1.2,
                        fuel_kg: float = 0.028, igniter_delay_ctrl: float = 0.1, dt: float = 0.01,
                        truth_mass: float | None = None, truth_scale: float = 1.0, truth_delay: float | None = None,
                        act_wn: float = 36.7, act_zeta: float = 0.6, act_tau: float = 0.03,
                        rng=None, alt_sigma: float = 0.0, vz_sigma: float = 0.0, curve: str = "E12") -> dict:
    """Senkrechter Fall aus dem Gipfel, Zuendung und Drosselregelung wie in sim.py, Pads als PT2 mit
    Totzeit, Bodenkontakt mit Huepfern. Liefert Kontakte, haerteste Aufsetzgeschwindigkeit,
    Zuendzustand und Zeit bis zur Ruhe."""
    m_true = truth_mass if truth_mass is not None else m_ctrl
    delay_true = truth_delay if truth_delay is not None else igniter_delay_ctrl
    ctrl = ThrottleLandingController(curve, m_ctrl, tp, cd_a, rho, fuel_kg, igniter_delay_ctrl, dt)
    t_c, f_c = ctrl.t_curve, ctrl.f_curve
    imp = np.concatenate([[0.0], np.cumsum(0.5 * (f_c[1:] + f_c[:-1]) * np.diff(t_c))]); total = imp[-1]
    tb = float(t_c[np.nonzero(f_c)[0][-1] + 1])
    h, v, t = apogee, 0.0, 0.0
    x = np.zeros(2)                    # Pad-Aktuator [u, u_dot]
    hist: list[float] = []             # Kommandos fuer die Totzeit
    n_delay = int(round(act_tau / dt))
    t_ign = None; h_ign = v_ign = None
    contacts: list[tuple[float, float]] = []
    on_ground = False
    a_meas = G                         # spezifische Kraft entlang der Achse (Sensor)
    sub = 5; hh = dt / sub
    while t < 40.0:
        # Regler (Takt dt)
        h_est = h + (rng.normal(0, alt_sigma) if rng is not None else 0.0)
        v_est = v + (rng.normal(0, vz_sigma) if rng is not None else 0.0)
        if t_ign is None:
            if v < 0 and ctrl.should_ignite(h_est, v_est):
                t_ign = t; h_ign, v_ign = h, v
            u = 0.0
        elif not on_ground:
            u = ctrl.throttle_command(t - t_ign, h_est, v_est, m_ctrl, a_meas=a_meas)
        else:
            u = 1.0                     # am Boden: Pads rein
        hist.append(u)
        u_del = hist[-1 - n_delay] if len(hist) > n_delay else 0.0
        for _ in range(sub):
            tb2 = (t - t_ign - delay_true) if t_ign is not None else -1.0
            T_motor = truth_scale * float(np.interp(tb2, t_c, f_c, left=0.0, right=0.0)) if tb2 >= 0 else 0.0
            burnt = float(np.interp(tb2, t_c, imp, left=0.0, right=total)) / total if tb2 >= 0 else 0.0
            mass = m_true - fuel_kg * burnt
            f = throttle_factor(x[0], tp.f_min)
            T = T_motor * f
            a_meas = T / mass + (0.5 * rho * cd_a * v * v / mass if v < 0 else 0.0)
            # Aktuator PT2
            xdd = act_wn * act_wn * (u_del - x[0]) - 2 * act_zeta * act_wn * x[1]
            x[1] += xdd * hh; x[0] += x[1] * hh
            if on_ground:
                if T / mass > G:
                    on_ground = False; v = 0.0; h = 1e-6
                elif tb2 > tb:
                    return {"contacts": contacts, "v_land": min(v for _, v in contacts) if contacts else 0.0,
                            "t_ign": t_ign, "h_ign": h_ign, "v_ign": v_ign, "t_rest": t, "landed": True}
                else:
                    continue
            D = 0.5 * rho * cd_a * v * v * (1.0 if v < 0 else -1.0)
            v += ((T + D) / mass - G) * hh
            h += v * hh
            if h <= 0.0:
                contacts.append((t, v))
                h, v, on_ground = 0.0, 0.0, True
                if t_ign is None or tb2 > tb:
                    return {"contacts": contacts, "v_land": min(vv for _, vv in contacts), "t_ign": t_ign,
                            "h_ign": h_ign, "v_ign": v_ign, "t_rest": t, "landed": True}
        t += dt
    return {"contacts": contacts, "v_land": min(v for _, v in contacts) if contacts else float("nan"), "t_ign": t_ign,
            "h_ign": h_ign, "v_ign": v_ign, "t_rest": t, "landed": False}
