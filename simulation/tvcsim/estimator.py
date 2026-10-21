"""Estimator-Block (chart_32): Durchreichen, Schub aus |a| und bekannter Masse."""
from __future__ import annotations

import numpy as np


def estimate(rdd_n, w_n, q_n, m_meas):
    """``w_est = w_n; q_est = q_n; T_est = norm(rdd_n) * m_meas``."""
    return np.asarray(w_n, dtype=float), np.asarray(q_n, dtype=float), float(np.linalg.norm(rdd_n) * m_meas)
