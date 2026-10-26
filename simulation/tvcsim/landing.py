"""Landebrennen mit dem zweiten Feststoffmotor (Jan, 23.10.2026): Planung und Zuendentscheidung.

Ein Feststoffmotor laesst sich weder drosseln noch abschalten. Die einzige Stellgroesse der
Landung ist der Zuendzeitpunkt. Fuer eine gegebene Masse und Schubkurve gibt es zu jeder
Sinkgeschwindigkeit ``v0`` genau eine Zuendhoehe ``h_ign(v0)``, bei der die Rakete mit (nahezu)
Null Geschwindigkeit am Boden ankommt. Die Tabelle entsteht aus einer eindimensionalen
Integration der Schubkurve (senkrechter Motor, Luftwiderstand optional); die Firmware rechnet
dieselbe Tabelle beim Start (``firmware/src/LandingBurn.cpp``, Test gegen
``firmware/test/data/landing_table_E12.csv``).

Zuendentscheidung im Flug (``LandingPlanner``): der Anzuender braucht ``igniter_delay`` bis zum
Schub. Fuer den nach dem Verzug vorausgesagten Zustand wird jeden Takt die *Aufsetzkosten*
``J(h, v)`` berechnet: eine 1D-Simulation des ganzen Brennens mit Bodenkontakt (die Rakete bleibt
am Boden, solange der Schub kleiner als das Gewicht ist, und hebt sonst wieder ab); ``J`` ist die
groesste Aufsetzgeschwindigkeit bis zur Ruhe. Im freien Fall sinkt ``J`` zuerst (je spaeter die
Zuendung, desto tiefer der Stopp) und steigt dann (Bremsvermoegen reicht nicht mehr); gezuendet
wird im Minimum, also sobald ``J(jetzt) <= J(einen Takt spaeter)``. Das deckt alle drei Faelle ab:
Stopp in der Luft mit anschliessendem Fall, Huepfer (Aufsetzen vor Brennschluss, der Schwanz der
Kurve hebt die Rakete wieder) und zu schnelles Ankommen. Die Tabelle ``h_ign(v)`` (Zuendhoehe, bei
der die Rakete mit |v| <= v_tol ankommt) bleibt zur Anschauung und fuer den Vergleich mit der
Firmware.

Was die Studie (scripts/landing_study.py) zeigt: mit der E12 (38,6 Ns, 3,5 s) ist das Netto-
Bremsvermoegen ``int (F - m g) dt`` bei 0,6 kg etwa 17 m/s, bei 0,7 kg 12 m/s; die Rakete muss
also so hoch zuenden, dass sie in der Schubspitze bremst und im Schwanz der Kurve (11 N) gerade
noch getragen wird. Deshalb reagiert das Ergebnis stark auf Schubtoleranz und Masse.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .motors import load_thrust_curve

G = 9.81


def burn_1d(t_curve: np.ndarray, f_curve: np.ndarray, m: float, h0: float, v0: float,
            cd_a: float = 0.0, rho: float = 1.2, scale: float = 1.0, delay: float = 0.0,
            dt: float = 1e-3, fuel_kg: float = 0.0, t_max: float = 8.0) -> tuple[float, float, float]:
    """Senkrechter Brennvorgang aus (h0, v0): liefert (v beim Aufsetzen, Zeit bis dahin, hoechste
    Hoehe). Masse nimmt mit dem Impuls ab (``fuel_kg`` je Motor). Kein Aufsetzen bis t_max:
    v = +inf als Kennzeichen (Rakete steigt weg)."""
    h, v, t = h0, v0, 0.0
    imp = np.concatenate([[0.0], np.cumsum(0.5 * (f_curve[1:] + f_curve[:-1]) * np.diff(t_curve))])
    total = imp[-1] if imp[-1] > 0 else 1.0
    h_max = h0
    while h > 0.0:
        if t > t_max:
            return float("inf"), t, h_max
        tb = t - delay
        T = scale * float(np.interp(tb, t_curve, f_curve, left=0.0, right=0.0))
        burnt = float(np.interp(tb, t_curve, imp, left=0.0, right=total)) / total
        mass = m - fuel_kg * burnt
        D = 0.5 * rho * cd_a * v * v * (1.0 if v < 0 else -1.0)
        a = (T + D) / mass - G
        v += a * dt
        h += v * dt
        t += dt
        if h > h_max:
            h_max = h
    return v, t, h_max


def ignition_altitude(t_curve, f_curve, m: float, v0: float, cd_a: float = 0.0, rho: float = 1.2,
                      v_tol: float = 0.5, fuel_kg: float = 0.0, dt: float = 1e-3,
                      scale: float = 1.0, t_max: float = 8.0) -> tuple[float, float]:
    """Zuendhoehe fuer die Sinkgeschwindigkeit v0 (negativ): (h_ign, v beim Aufsetzen).

    Der Geschwindigkeitsverlauf waehrend des Brennens haengt nicht von der Hoehe ab (Dichte
    konstant), also reicht eine Integration von v(t) ab der Zuendung: die Zuendhoehe ist der
    Hoehenverlust bis zu dem Moment, in dem v zum ersten Mal -v_tol erreicht. Kommt v nie so
    weit (Bremsvermoegen reicht nicht), gilt der Punkt mit dem kleinsten |v| (bestes Ergebnis).
    """
    imp = np.concatenate([[0.0], np.cumsum(0.5 * (f_curve[1:] + f_curve[:-1]) * np.diff(t_curve))])
    total = imp[-1] if imp[-1] > 0 else 1.0
    v, t, drop = v0, 0.0, 0.0
    best_drop, best_v = 0.0, v0
    while t < t_max:
        T = scale * float(np.interp(t, t_curve, f_curve, left=0.0, right=0.0))
        burnt = float(np.interp(t, t_curve, imp, left=0.0, right=total)) / total
        mass = m - fuel_kg * burnt
        D = 0.5 * rho * cd_a * v * v * (1.0 if v < 0 else -1.0)
        v += ((T + D) / mass - G) * dt
        drop += v * dt
        t += dt
        if v >= -v_tol:
            return -drop, v
        if abs(v) < abs(best_v):
            best_drop, best_v = drop, v
        if T <= 0.0 and t > t_curve[-2]:
            break
    return -best_drop, best_v


@dataclass
class IgnitionTable:
    curve: str
    m: float
    cd_a: float = 0.0
    rho: float = 1.2
    v_tol: float = 0.5
    fuel_kg: float = 0.0
    v_grid: np.ndarray = field(default_factory=lambda: -np.arange(1.0, 41.0, 1.0))
    h_grid: np.ndarray = field(default_factory=lambda: np.zeros(0))
    v_td_grid: np.ndarray = field(default_factory=lambda: np.zeros(0))

    def __post_init__(self) -> None:
        self.t_curve, self.f_curve = load_thrust_curve(self.curve)
        if len(self.h_grid) == 0:
            hs, vs = [], []
            for v0 in self.v_grid:
                h, v = ignition_altitude(self.t_curve, self.f_curve, self.m, float(v0), self.cd_a, self.rho,
                                         self.v_tol, self.fuel_kg)
                hs.append(h); vs.append(v)
            self.h_grid = np.array(hs)
            self.v_td_grid = np.array(vs)

    def h_ign(self, v: float) -> float:
        """Zuendhoehe fuer die Sinkgeschwindigkeit v (negativ); ausserhalb des Rasters gehalten."""
        vv = -self.v_grid      # positiv, aufsteigend
        return float(np.interp(-v, vv, self.h_grid, left=self.h_grid[0], right=self.h_grid[-1]))

    def feasible_speed(self) -> float:
        """Groesste Sinkgeschwindigkeit, die die Tabelle noch auf |v| <= v_tol bringt."""
        ok = np.abs(self.v_td_grid) <= self.v_tol + 1e-6
        return float(-self.v_grid[ok].min()) if ok.any() else 0.0

    def should_ignite(self, h: float, v: float, delay: float, margin: float = 0.0) -> bool:
        """Zuenden, wenn der nach dem Zuendverzug vorausgesagte Zustand die Zuendhoehe erreicht."""
        if v >= 0.0:
            return False
        h_pred = h + v * delay - 0.5 * G * delay * delay
        v_pred = v - G * delay
        return h_pred <= self.h_ign(v_pred) + margin

    def to_rows(self) -> list[tuple[float, float, float]]:
        return [(float(v), float(h), float(vt)) for v, h, vt in zip(self.v_grid, self.h_grid, self.v_td_grid)]


def impact_cost(t_curve, f_curve, m: float, h0: float, v0: float, cd_a: float = 0.0, rho: float = 1.2,
                scale: float = 1.0, fuel_kg: float = 0.0, dt: float = 5e-3, t_max: float = 8.0,
                v_lift: float = 0.0) -> tuple[float, list[tuple[float, float, float]]]:
    """Aufsetzkosten J fuer eine Zuendung im Zustand (h0, v0): groesste Aufsetzgeschwindigkeit
    (positiv, m/s) bis zur Ruhe, dazu die Liste der Bodenkontakte (t, h, v). Am Boden bleibt die
    Rakete liegen (v = 0), solange der Schub das Gewicht nicht uebersteigt; sonst hebt sie ab."""
    imp = np.concatenate([[0.0], np.cumsum(0.5 * (f_curve[1:] + f_curve[:-1]) * np.diff(t_curve))])
    total = imp[-1] if imp[-1] > 0 else 1.0
    tb = float(t_curve[np.nonzero(f_curve)[0][-1] + 1]) if np.any(f_curve > 0) else 0.0
    h, v, t = h0, v0, 0.0
    worst = 0.0
    contacts: list[tuple[float, float, float]] = []
    on_ground = h <= 0.0
    while t < t_max:
        T = scale * float(np.interp(t, t_curve, f_curve, left=0.0, right=0.0))
        burnt = float(np.interp(t, t_curve, imp, left=0.0, right=total)) / total
        mass = m - fuel_kg * burnt
        if on_ground:
            if T / mass - G > v_lift:          # hebt wieder ab
                on_ground = False
                v = 0.0
            elif t > tb:
                break                          # Brennschluss am Boden: Ruhe
            else:
                t += dt
                continue
        D = 0.5 * rho * cd_a * v * v * (1.0 if v < 0 else -1.0)
        v += ((T + D) / mass - G) * dt
        h += v * dt
        t += dt
        if h <= 0.0:
            contacts.append((t, 0.0, v))
            worst = max(worst, -v)
            h, v, on_ground = 0.0, 0.0, True
            if t > tb:
                break
    if not on_ground:                          # noch in der Luft: freier Fall bis zum Boden
        v_td = -np.sqrt(max(0.0, v * v + 2 * G * h)) if cd_a <= 0 else _fall_speed(h, v, m, cd_a, rho)
        contacts.append((t, 0.0, v_td))
        worst = max(worst, -v_td)
    return worst, contacts


def _fall_speed(h: float, v: float, m: float, cd_a: float, rho: float, dt: float = 5e-3) -> float:
    while h > 0.0:
        v += (-G + 0.5 * rho * cd_a * v * v / m * (1.0 if v < 0 else -1.0)) * dt
        h += v * dt
    return v


@dataclass
class LandingPlanner:
    """Zuendentscheidung ueber die Aufsetzkosten J (siehe Modulkommentar)."""

    curve: str
    m: float
    cd_a: float = 0.0
    rho: float = 1.2
    fuel_kg: float = 0.0
    igniter_delay: float = 0.1
    dt_ctrl: float = 0.01
    scale: float = 1.0           # angenommene Schubtoleranz (Planung), nicht die wahre
    min_speed: float = 2.0       # unter dieser Sinkrate wird nicht gezuendet

    def __post_init__(self) -> None:
        self.t_curve, self.f_curve = load_thrust_curve(self.curve)
        self.last_J = float("nan")

    def predicted(self, h: float, v: float, tau: float) -> tuple[float, float]:
        return h + v * tau - 0.5 * G * tau * tau, v - G * tau

    def cost(self, h: float, v: float) -> float:
        return impact_cost(self.t_curve, self.f_curve, self.m, h, v, self.cd_a, self.rho, self.scale, self.fuel_kg)[0]

    def should_ignite(self, h: float, v: float) -> bool:
        if v > -self.min_speed:
            return False
        h_now, v_now = self.predicted(h, v, self.igniter_delay)
        h_next, v_next = self.predicted(h, v, self.igniter_delay + self.dt_ctrl)
        if h_now <= 0.0:
            return True
        J_now = self.cost(h_now, v_now)
        J_next = self.cost(h_next, v_next)
        self.last_J = J_now
        return J_now <= J_next


def net_braking_dv(curve: str, m: float) -> float:
    """``int (F - m g) dt`` ueber die Brenndauer, geteilt durch m: Bremsvermoegen ohne Luft."""
    t, f = load_thrust_curve(curve)
    tb = t[np.nonzero(f)[0][-1] + 1]
    sel = t <= tb
    return float(np.trapezoid(f[sel] - m * G, t[sel]) / m)
