"""Landung mit dem zweiten TSP E12: geht das überhaupt, und wie groß ist das Fenster?

Senkrechte Bewegung (1D) mit Luftwiderstand des Rumpfs, Schubkurve des E12, Abbrand proportional zum
Impuls und einer Zündverzögerung zwischen Kommando und Schubbeginn (Anzünder + Anbrennen). Zwei Fälle:

  ballistisch   Fall nach dem Gipfel ohne Schirm, Zündung auf einer Kommandohöhe h_cmd
  am Schirm     Sinken mit konstanter Geschwindigkeit am Fallschirm (recovery.py), Schirm wird bei der
                Zündung abgeworfen (sonst zieht der Schub in den Schirm)

Für jede Kommandohöhe: Aufsetzgeschwindigkeit. Steigt die Rakete unter Schub wieder (v > 0, das E12
schiebt 3,5 s mit ungefähr dem eigenen Gewicht), zählt der zweite Aufprall nach Brennschluss.

  python scripts/landing_feasibility.py                  # Landekonfiguration (Beine, zwei Motoren), Tabellen
  python scripts/landing_feasibility.py --plot           # out/landing_feasibility.png
  python scripts/landing_feasibility.py --dry 0.85       # leichtere Rakete (kg ohne Motoren)
  python scripts/landing_feasibility.py --eject-case     # leere Hülse von Motor 1 wird ausgestoßen

Das ist eine Machbarkeitsrechnung, keine Flugsimulation: Lage, Regler und Wind fehlen. Ob die Rakete
nach dem Gipfel ohne Schub (also ohne Steuerung) mit der Düse nach unten fällt, sagt sie nicht;
tvcsim hat keine Aerodynamik.
"""
import argparse
import json
import math

import numpy as np

import _path  # noqa: F401
from tvcsim.motors import load_thrust_curve
from tvcsim.params import CAD_MASS_FILE, OUT_DIR

G = 9.81
RHO = 1.2


class Motor:
    def __init__(self, curve="E12", prop_g=28.0, total_g=64.0):
        self.t, self.f = load_thrust_curve(curve)
        imp = np.concatenate([[0.0], np.cumsum(0.5 * (self.f[1:] + self.f[:-1]) * np.diff(self.t))])
        self.imp = imp
        self.I = float(imp[-1])
        self.burn = float(self.t[np.nonzero(self.f)[0][-1] + 1])
        self.prop = prop_g / 1000.0
        self.total = total_g / 1000.0

    def thrust(self, tau):
        return float(np.interp(tau, self.t, self.f, left=0.0, right=0.0))

    def prop_left(self, tau):
        return self.prop * (1.0 - float(np.interp(tau, self.t, self.imp, left=0.0, right=self.I)) / self.I)


def drag(v, cd, d):
    return -0.5 * RHO * cd * math.pi * d * d / 4.0 * v * abs(v)


def ascent(m_dry, motor, cd, d, dt=0.001):
    """Aufstieg mit Motor 1 von der Rampe bis zum Gipfel: (Gipfelhöhe, Zeit)."""
    h = v = t = 0.0
    while True:
        m = m_dry + motor.total - motor.prop + motor.prop_left(t)   # Motor 2 steckt im m_dry
        T = motor.thrust(t)
        a = (T + drag(v, cd, d)) / m - G
        if h <= 0.0 and a < 0.0 and t < motor.burn:
            a = 0.0                                                   # Rampe hält
        v += a * dt
        h += v * dt
        t += dt
        if t > motor.burn and v <= 0.0:
            return h, t
        if t > 30:
            return h, t


def landing(m_body, motor, h0, v0, h_cmd, delay, cd, d, dt=0.001, t_max=30.0):
    """Ab Höhe h0 mit v0 (negativ = sinkt) fallen, bei h_cmd Kommando, nach delay Schub.
    Rückgabe: Aufsetzgeschwindigkeit (positiv), Höhe beim Schubbeginn, kleinste |v| unter Schub,
    Höhe bei v = 0 (falls erreicht), stieg wieder (bool)."""
    h, v, t = h0, v0, 0.0
    t_cmd = None
    t_fire = None
    h_fire = math.nan
    v_min = abs(v0)
    h_stop = math.nan
    reclimb = False
    while t < t_max:
        if t_cmd is None and h <= h_cmd:
            t_cmd = t
        if t_cmd is not None and t_fire is None and t - t_cmd >= delay:
            t_fire = t
            h_fire = h
        tau = (t - t_fire) if t_fire is not None else -1.0
        burning = t_fire is not None and tau <= motor.burn
        m = m_body + (motor.total - motor.prop + motor.prop_left(tau) if t_fire is not None else motor.total)
        T = motor.thrust(tau) if t_fire is not None else 0.0
        a = (T + drag(v, cd, d)) / m - G
        v_new = v + a * dt
        if burning and v < 0.0 <= v_new and math.isnan(h_stop):
            h_stop = h
        if burning and v_new > 0.0:
            reclimb = True
        v = v_new
        h += v * dt
        t += dt
        if t_fire is not None and burning:
            v_min = min(v_min, abs(v))
        if h <= 0.0:
            return abs(v), h_fire, v_min, h_stop, reclimb
    return math.nan, h_fire, v_min, h_stop, reclimb


def window(results, h_grid, limit):
    ok = h_grid[np.array(results) <= limit]
    return (ok.min(), ok.max()) if len(ok) else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry", type=float, default=None,
                    help="kg ohne Motoren (Vorgabe: cad/mass_properties.json voll_1000 no_motor + 25 g Doppelmount)")
    ap.add_argument("--mount-extra", type=float, default=0.025, help="kg für Doppelmount, Feder, Riegel (Schätzung)")
    ap.add_argument("--eject-case", action="store_true", help="leere Hülse von Motor 1 wird vor der Landung ausgestoßen")
    ap.add_argument("--cd-body", type=float, default=0.6)
    ap.add_argument("--chute-speed", type=float, default=3.6, help="m/s Sinkgeschwindigkeit am Schirm")
    ap.add_argument("--chute-alt", type=float, default=None, help="m Höhe, ab der am Schirm gesunken wird (Vorgabe: Gipfel)")
    ap.add_argument("--delays", type=float, nargs="+", default=[0.2, 0.5, 0.8], help="s Zündverzögerung")
    ap.add_argument("--limit", type=float, default=2.0, help="m/s zulässige Aufsetzgeschwindigkeit (Beine)")
    ap.add_argument("--plot", action="store_true")
    args = ap.parse_args()

    d = 0.075
    if args.dry is None:
        with open(CAD_MASS_FILE, encoding="utf-8") as fh:
            cad = json.load(fh)["erstflug_2026-10-22"]["variants"]["voll_1000"]["configurations"]
        # no_motor enthält den Adapter, keinen Motor
        args.dry = cad["no_motor"]["mass_kg"] + args.mount_extra
    mot = Motor()
    m_lift = args.dry + 2 * mot.total
    apo, t_apo = ascent(args.dry + mot.total, mot, args.cd_body, d)
    m_land_body = args.dry + (0.0 if args.eject_case else mot.total - mot.prop)
    w_land = (m_land_body + mot.total) * G

    print(f"TSP E12: {mot.I:.1f} Ns, Brenndauer {mot.burn:.2f} s, mittlerer Schub {mot.I / mot.burn:.1f} N, Spitze {mot.f.max():.1f} N")
    print(f"Rakete ohne Motoren {args.dry * 1000:.0f} g (Landekonfiguration mit Beinen + {args.mount_extra * 1000:.0f} g Doppelmount)")
    print(f"Start mit zwei Motoren {m_lift * 1000:.0f} g, Schub/Gewicht beim Start im Mittel {mot.I / mot.burn / (m_lift * G):.2f}")
    print(f"Gipfel mit Motor 1: {apo:.1f} m nach {t_apo:.1f} s (1D, mit Luftwiderstand)")
    print(f"Masse bei der Landezündung {(m_land_body + mot.total) * 1000:.0f} g "
          f"({'Hülse 1 ausgestoßen' if args.eject_case else 'Hülse 1 bleibt'}), Gewicht {w_land:.1f} N")
    v_max_stop = (mot.I - (m_land_body + mot.total - mot.prop / 2) * G * mot.burn) / (m_land_body + mot.total)
    print(f"Impulsbilanz: der E12 kann über die ganze Brenndauer höchstens {max(v_max_stop, 0):.1f} m/s Sinken abbauen "
          f"(I − m g t_b = {mot.I - (m_land_body + mot.total - mot.prop / 2) * G * mot.burn:+.1f} Ns)")

    h_grid = np.arange(0.5, max(apo, 25.0), 0.25)
    out = {}
    for case in ("ballistisch", "am Schirm"):
        print(f"\n{case}:" + ("  freier Fall vom Gipfel" if case == "ballistisch" else
                             f"  Sinken mit {args.chute_speed} m/s, Schirm wird bei Zündung abgeworfen"))
        h0 = apo if case == "ballistisch" else (args.chute_alt or apo)
        v0 = 0.0 if case == "ballistisch" else -args.chute_speed
        cd = args.cd_body
        out[case] = {}
        for delay in args.delays:
            res = [landing(m_land_body, mot, h0, v0, hc, delay, cd, d) for hc in h_grid]
            vt = np.array([r[0] for r in res])
            out[case][delay] = vt
            k = int(np.nanargmin(vt))
            r = res[k]
            w = window(vt, h_grid, args.limit)
            reclimb = r[4]
            print(f"  Zündverzug {delay:.2f} s: beste Kommandohöhe {h_grid[k]:5.2f} m -> Aufsetzen mit {vt[k]:4.1f} m/s"
                  f"{' (steigt unter Schub wieder, Aufprall nach Brennschluss)' if reclimb else ''}; "
                  f"Fenster ≤ {args.limit} m/s: " + (f"{w[0]:.2f} … {w[1]:.2f} m ({w[1] - w[0]:.2f} m breit)" if w else "keins"))
        # Robustheit: Kommandohöhe für den mittleren Verzug gewählt, Verzug streut
        mid = args.delays[len(args.delays) // 2]
        k = int(np.nanargmin(out[case][mid]))
        hc = h_grid[k]
        spread = [landing(m_land_body, mot, h0, v0, hc, dl, cd, d)[0] for dl in np.linspace(min(args.delays), max(args.delays), 7)]
        print(f"  Kommando bei {hc:.2f} m (optimal für {mid} s), Verzug {min(args.delays)}…{max(args.delays)} s streut: "
              f"Aufsetzen {np.nanmin(spread):.1f} … {np.nanmax(spread):.1f} m/s")

    if args.plot:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        OUT_DIR.mkdir(exist_ok=True)
        fig, ax = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True, layout="constrained")
        for a, case in zip(ax, out):
            for delay, vt in out[case].items():
                a.plot(h_grid, vt, label=f"Zündverzug {delay} s")
            a.axhline(args.limit, color="g", ls="--", label=f"{args.limit} m/s (Beine)")
            a.set_title(case); a.set_xlabel("Kommandohöhe [m]"); a.grid(alpha=0.3)
            a.set_ylim(0, 25)
        ax[0].set_ylabel("Aufsetzgeschwindigkeit [m/s]")
        ax[0].legend()
        fig.suptitle(f"Landung mit TSP E12, {(m_land_body + mot.total) * 1000:.0f} g bei der Zündung")
        fig.savefig(OUT_DIR / "landing_feasibility.png", dpi=120)
        print(f"-> {OUT_DIR / 'landing_feasibility.png'}")


if __name__ == "__main__":
    main()
