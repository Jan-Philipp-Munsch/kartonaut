"""Kleiner Bayes-Optimierer: Gauß-Prozess (Matérn 5/2) mit Expected Improvement, nur numpy und scipy.

Gedacht für teure, verrauschte Zielfunktionen mit wenigen Parametern, hier die Reglergewinne gegen die Simulation
(``scripts/tune_bayes.py``). Die Parameter werden auf den Einheitswürfel abgebildet (wahlweise logarithmisch), die
Zielwerte standardisiert; die Hyperparameter des GP (Längenskalen, Signal, Rauschen) werden in jeder Runde per
Maximum-Likelihood mit L-BFGS-B neu geschätzt. Der nächste Punkt maximiert Expected Improvement gegen den besten
*vorhergesagten* Mittelwert (nicht den besten Messwert), weil die Zielfunktion verrauscht ist.

    opt = BayesOpt({"kp": (0.3, 8.0, "log"), "kd": (0.05, 2.0, "log")}, seed=0)
    for _ in range(30):
        x = opt.ask()
        opt.tell(x, f(**x))
    best = opt.best()          # Punkt mit dem kleinsten GP-Mittelwert unter den gemessenen
"""
from __future__ import annotations

import math

import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import minimize
from scipy.stats import norm


def _matern52(a: np.ndarray, b: np.ndarray, ls: np.ndarray) -> np.ndarray:
    d = np.sqrt(np.maximum(((a[:, None, :] - b[None, :, :]) / ls) ** 2, 0).sum(-1))
    s5 = math.sqrt(5.0) * d
    return (1.0 + s5 + s5 * s5 / 3.0) * np.exp(-s5)


class GP:
    """GP-Regression mit konstantem Mittel 0 auf standardisierten Zielwerten."""

    def __init__(self, X: np.ndarray, y: np.ndarray):
        self.X = X
        self.mu_y, self.sd_y = float(y.mean()), float(y.std() or 1.0)
        self.y = (y - self.mu_y) / self.sd_y
        self._fit()

    def _nll(self, theta):
        ls, sf, sn = np.exp(theta[:-2]), math.exp(theta[-2]), math.exp(theta[-1])
        K = sf * sf * _matern52(self.X, self.X, ls) + (sn * sn + 1e-8) * np.eye(len(self.X))
        try:
            c = cho_factor(K, lower=True)
        except np.linalg.LinAlgError:
            return 1e10
        a = cho_solve(c, self.y)
        return 0.5 * self.y @ a + np.log(np.diag(c[0])).sum()

    def _fit(self):
        d = self.X.shape[1]
        best = None
        for ls0 in (0.15, 0.4, 1.0):
            th0 = np.array([math.log(ls0)] * d + [0.0, math.log(0.2)])
            bounds = [(math.log(0.03), math.log(3.0))] * d + [(math.log(0.1), math.log(10.0)), (math.log(1e-3), math.log(1.0))]
            r = minimize(self._nll, th0, method="L-BFGS-B", bounds=bounds)
            if best is None or r.fun < best.fun:
                best = r
        th = best.x
        self.ls, self.sf, self.sn = np.exp(th[:-2]), math.exp(th[-2]), math.exp(th[-1])
        K = self.sf ** 2 * _matern52(self.X, self.X, self.ls) + (self.sn ** 2 + 1e-8) * np.eye(len(self.X))
        self.c = cho_factor(K, lower=True)
        self.alpha = cho_solve(self.c, self.y)

    def predict(self, Xs: np.ndarray):
        Ks = self.sf ** 2 * _matern52(Xs, self.X, self.ls)
        mu = Ks @ self.alpha
        v = cho_solve(self.c, Ks.T)
        var = np.maximum(self.sf ** 2 - (Ks * v.T).sum(1), 1e-12)
        return mu * self.sd_y + self.mu_y, np.sqrt(var) * self.sd_y


class BayesOpt:
    """Minimiert eine Zielfunktion über einen Kasten. ``space``: Name -> (unten, oben, "lin" | "log")."""

    def __init__(self, space: dict, n_init: int | None = None, seed: int = 0, xi: float = 0.01):
        self.names = list(space)
        self.space = space
        self.rng = np.random.default_rng(seed)
        self.n_init = n_init or max(5, 3 * len(space))
        self.xi = xi
        self.U: list[np.ndarray] = []
        self.y: list[float] = []
        self._init = self._lhs(self.n_init)

    # --- Abbildung Einheitswürfel <-> Parameter
    def _to_x(self, u):
        out = {}
        for i, n in enumerate(self.names):
            lo, hi, sc = self.space[n]
            out[n] = float(math.exp(math.log(lo) + u[i] * (math.log(hi) - math.log(lo))) if sc == "log" else lo + u[i] * (hi - lo))
        return out

    def _to_u(self, x):
        u = []
        for n in self.names:
            lo, hi, sc = self.space[n]
            u.append((math.log(x[n]) - math.log(lo)) / (math.log(hi) - math.log(lo)) if sc == "log" else (x[n] - lo) / (hi - lo))
        return np.array(u)

    def _lhs(self, n):
        d = len(self.names)
        cut = (np.arange(n)[:, None] + self.rng.random((n, d))) / n
        for j in range(d):
            cut[:, j] = cut[self.rng.permutation(n), j]
        return list(cut)

    # --- Schnittstelle
    def ask(self) -> dict:
        if len(self.U) < len(self._init):
            return self._to_x(self._init[len(self.U)])
        gp = GP(np.array(self.U), np.array(self.y))
        mu_obs, _ = gp.predict(np.array(self.U))
        f_best = float(mu_obs.min())
        cand = self.rng.random((4000, len(self.names)))
        mu, sd = gp.predict(cand)
        z = (f_best - mu - self.xi * gp.sd_y) / sd
        ei = (f_best - mu - self.xi * gp.sd_y) * norm.cdf(z) + sd * norm.pdf(z)
        u0 = cand[int(np.argmax(ei))]

        def neg_ei(u):
            m, s = gp.predict(u[None, :])
            zz = (f_best - m[0] - self.xi * gp.sd_y) / s[0]
            return -((f_best - m[0] - self.xi * gp.sd_y) * norm.cdf(zz) + s[0] * norm.pdf(zz))

        r = minimize(neg_ei, u0, method="L-BFGS-B", bounds=[(0.0, 1.0)] * len(self.names))
        return self._to_x(np.clip(r.x, 0.0, 1.0))

    def tell(self, x: dict, y: float) -> None:
        self.U.append(self._to_u(x))
        self.y.append(float(y))

    def best(self) -> tuple[dict, float, float]:
        """Gemessener Punkt mit dem kleinsten GP-Mittelwert: (Parameter, GP-Mittel, GP-Streuung)."""
        gp = GP(np.array(self.U), np.array(self.y))
        mu, sd = gp.predict(np.array(self.U))
        i = int(np.argmin(mu))
        return self._to_x(self.U[i]), float(mu[i]), float(sd[i])
