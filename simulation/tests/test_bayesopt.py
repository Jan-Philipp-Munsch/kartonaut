import numpy as np

from tvcsim.bayesopt import BayesOpt, GP


def test_gp_interpolates_smooth_function():
    rng = np.random.default_rng(0)
    X = rng.random((25, 2))
    y = np.sin(3 * X[:, 0]) + X[:, 1] ** 2
    gp = GP(X, y)
    Xt = rng.random((10, 2))
    mu, sd = gp.predict(Xt)
    assert np.max(np.abs(mu - (np.sin(3 * Xt[:, 0]) + Xt[:, 1] ** 2))) < 0.1
    assert np.all(sd >= 0)


def test_bayesopt_finds_minimum_of_noisy_log_bowl():
    """Minimum bei kp = 2, kd = 0,5 auf logarithmischen Achsen, mit Messrauschen."""
    rng = np.random.default_rng(1)

    def f(kp, kd):
        return (np.log(kp / 2.0)) ** 2 + 2 * (np.log(kd / 0.5)) ** 2 + rng.normal(0, 0.02)

    opt = BayesOpt({"kp": (0.3, 8.0, "log"), "kd": (0.05, 2.0, "log")}, seed=0)
    for _ in range(25):
        x = opt.ask()
        opt.tell(x, f(**x))
    x, mu, _ = opt.best()
    assert abs(np.log(x["kp"] / 2.0)) < 0.3
    assert abs(np.log(x["kd"] / 0.5)) < 0.3
