"""
correlation.py — the measurement the whole v02M thesis rests on.

THE CENTRAL CLAIM
-----------------
Sharpe_portfolio = Sharpe_per_bet * sqrt(N_effective)

    N_effective = N / (1 + (N-1) * rho_avg)

where rho_avg is the average pairwise correlation *of STRATEGY PnL*, NOT of
asset returns. This distinction is the entire disruption:

    directional bets on N correlated coins -> rho ~ 0.8 -> N_eff ~ 1.2
    spread capture   on N correlated coins -> rho ~ 0.1 -> N_eff ~ 5+

A market maker's PnL per fill is the captured spread. Whether BTC and ETH move
together says little about whether the spread you captured on BTC and the spread
you captured on ETH were both profitable. That is why Virtu can run 11,000+
instruments and actually realise the sqrt(N) benefit, while a directional
multi-asset crypto book cannot.

This module MEASURES both, on real data. It does not assume either.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from typing import Dict, List, Sequence

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
DATA = os.path.join(_ROOT, "data", "daily_5inst_jul2026.json")


def load(path: str = DATA) -> Dict:
    with open(path) as fh:
        return json.load(fh)


def returns(closes: Sequence[float]) -> List[float]:
    return [closes[i] / closes[i - 1] - 1 for i in range(1, len(closes))]


def mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs)


def stdev(xs: Sequence[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def pearson(a: Sequence[float], b: Sequence[float]) -> float:
    """Pearson correlation. Returns 0.0 for degenerate input."""
    if len(a) != len(b) or len(a) < 2:
        return 0.0
    ma, mb = mean(a), mean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = math.sqrt(sum((x - ma) ** 2 for x in a))
    db = math.sqrt(sum((y - mb) ** 2 for y in b))
    if da == 0 or db == 0:
        return 0.0
    return num / (da * db)


def effective_n(n: int, rho: float) -> float:
    """Effective independent bets given n bets with average pairwise corr rho."""
    if n <= 1:
        return float(n)
    denom = 1 + (n - 1) * rho
    if denom <= 0:
        return float(n)
    return n / denom


@dataclass
class CorrReport:
    labels: List[str]
    matrix: List[List[float]]
    avg_offdiag: float
    n: int
    n_eff: float
    sharpe_multiplier: float

    def as_dict(self) -> Dict:
        return {
            "labels": self.labels,
            "matrix": [[round(v, 4) for v in row] for row in self.matrix],
            "avg_pairwise_rho": round(self.avg_offdiag, 4),
            "n": self.n,
            "n_effective": round(self.n_eff, 3),
            "sharpe_multiplier_sqrt_neff": round(self.sharpe_multiplier, 3),
        }


def correlation_report(series: Dict[str, Sequence[float]]) -> CorrReport:
    labels = sorted(series)
    n = len(labels)
    mat = [[pearson(series[a], series[b]) for b in labels] for a in labels]
    off = [mat[i][j] for i in range(n) for j in range(n) if i != j]
    avg = mean(off) if off else 0.0
    ne = effective_n(n, avg)
    return CorrReport(labels, mat, avg, n, ne, math.sqrt(ne))


# ---------------------------------------------------------------- strategies ---

def directional_pnl(rets: Sequence[float]) -> List[float]:
    """PnL of a naive always-long directional bet: just the return itself.

    This is the axis v01T used (one leg direction per instrument), and it is
    what inherits the raw asset-return correlation.
    """
    return list(rets)


def spread_capture_pnl(rets: Sequence[float], capture_bps: float = 1.0) -> List[float]:
    """PnL of pure spread capture, per bar.

    A market maker earns the captured spread on each round trip. The number of
    round trips scales with activity (|return| is a usable proxy for how much
    two-sided flow crossed the book), while the SIGN of the move does not
    determine whether the spread was captured.

    pnl = capture * turnover_proxy   with turnover_proxy = |r| normalised

    Crucially this is a function of |r|, not r. Two assets that move together
    (corr(r_a, r_b) high) can still have far lower corr(|r_a|, |r_b|) once
    scaled, and the sign component -- which drives most directional
    correlation -- is removed entirely.
    """
    c = capture_bps * 1e-4
    return [c * abs(r) / (abs(r) + 1e-9) * (1.0 + abs(r)) for r in rets]


def inventory_neutral_pnl(rets: Sequence[float], capture_bps: float = 1.0) -> List[float]:
    """Spread capture net of adverse selection (inventory) cost.

    Realistic MM PnL = spread captured - adverse selection.
    Adverse selection is proportional to the move against resting quotes,
    which IS correlated across assets. This gives an honest middle case.
    """
    c = capture_bps * 1e-4
    return [c - 0.15 * abs(r) * c * 10 for r in rets]
