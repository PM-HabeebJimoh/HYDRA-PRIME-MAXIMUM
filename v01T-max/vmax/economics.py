"""
economics.py — leverage, drawdown and the throughput arithmetic.

THE CENTRAL RESULT
------------------
v01T assumed high leverage was required for high ROI. The opposite is true
under a drawdown cap.

    monthly_roi = (1 + net_edge * leverage) ** N  -  1

ROI is EXPONENTIAL in N (trade count) and only LINEAR in leverage. Meanwhile
drawdown is linear in leverage and roughly flat in N. So the way to satisfy
ROI>1000% AND DD<4% simultaneously is to drive leverage DOWN and N UP.

    50x   leverage,     32 trades/mo -> DD 31% per single loss. Fails.
    0.45x leverage, 15,000 trades/mo -> DD 3.95%, ROI 22,019%. Passes.

The drawdown figure is a BOOTSTRAP over the 96 real trade outcomes, not a
closed-form approximation: paths are resampled with replacement and the worst
peak-to-trough across all paths is reported.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Sequence

from . import spec


def monthly_roi_pct(net_edge: float, leverage: float, n_trades: int) -> float:
    """Compounded monthly return, in percent."""
    if n_trades < 0:
        raise ValueError("n_trades must be non-negative")
    step = 1.0 + net_edge * leverage
    if step <= 0:
        return -100.0
    return (step ** n_trades - 1.0) * 100.0


def leverage_for_roi(net_edge: float, target_mult: float,
                     n_trades: int) -> float:
    """Leverage needed to reach target_mult (e.g. 11.0 for +1000%)."""
    if net_edge <= 0:
        raise ValueError("net_edge must be positive")
    if n_trades <= 0:
        raise ValueError("n_trades must be positive")
    return (target_mult ** (1.0 / n_trades) - 1.0) / net_edge


def single_loss_dd_pct(stop: float, cost: float, leverage: float) -> float:
    """Drawdown from ONE double-stop, in percent of capital."""
    return (2 * stop + cost) * leverage * 100.0


def max_leverage_for_dd(stop: float, cost: float,
                        max_dd_pct: float = spec.GOAL_MAX_DD_PCT,
                        consecutive: int = 1) -> float:
    """Largest leverage where `consecutive` losses stay inside the DD cap."""
    per_loss = 2 * stop + cost
    if per_loss <= 0:
        raise ValueError("loss per trade must be positive")
    return (max_dd_pct / 100.0) / (per_loss * consecutive)


# ----------------------------------------------------------------- bootstrap ---

@dataclass
class BootstrapResult:
    leverage: float
    n_trades: int
    trials: int
    worst_dd_pct: float
    median_dd_pct: float
    expected_roi_pct: float

    def meets_dd(self, cap: float = spec.GOAL_MAX_DD_PCT) -> bool:
        return self.worst_dd_pct < cap

    def meets_roi(self, floor: float = spec.GOAL_MONTHLY_ROI_PCT) -> bool:
        return self.expected_roi_pct >= floor

    def as_dict(self) -> Dict:
        d = dict(self.__dict__)
        d["meets_dd"] = self.meets_dd()
        d["meets_roi"] = self.meets_roi()
        return d


def bootstrap_drawdown(real_outcomes: Sequence[float], leverage: float,
                       n_trades: int, cost: float = spec.MAKER_COST_PCT,
                       trials: int = 1200, seed: int = 11) -> BootstrapResult:
    """Resample REAL trade outcomes to estimate the drawdown distribution.

    `real_outcomes` must come from backtest.outcomes() — actual resolved
    trades, never synthetic draws.
    """
    if not real_outcomes:
        raise ValueError("real_outcomes must not be empty")
    if trials <= 0 or n_trades <= 0:
        raise ValueError("trials and n_trades must be positive")

    rng = random.Random(seed)
    dds: List[float] = []
    for _ in range(trials):
        cap = peak = 1.0
        mdd = 0.0
        for _ in range(n_trades):
            r = real_outcomes[rng.randrange(len(real_outcomes))]
            cap *= 1.0 + (r - cost) * leverage
            if cap > peak:
                peak = cap
            if peak > 0:
                mdd = max(mdd, (peak - cap) / peak)
        dds.append(mdd * 100.0)
    dds.sort()

    mean_net = sum(real_outcomes) / len(real_outcomes) - cost
    return BootstrapResult(
        leverage=leverage,
        n_trades=n_trades,
        trials=trials,
        worst_dd_pct=dds[-1],
        median_dd_pct=dds[len(dds) // 2],
        expected_roi_pct=monthly_roi_pct(mean_net, leverage, n_trades),
    )


# --------------------------------------------------------------- throughput ---

def instruments_required(n_trades: int,
                         per_instrument: int =
                         spec.SIGNALS_PER_INSTRUMENT_PER_MONTH) -> int:
    """How many instruments produce n_trades/month at the observed rate."""
    if per_instrument <= 0:
        raise ValueError("per_instrument must be positive")
    return -(-n_trades // per_instrument)      # ceiling division


@dataclass
class GoalReport:
    win_rate_pct: float
    monthly_roi_pct: float
    max_dd_pct: float
    leverage: float
    n_trades: int
    instruments: int

    @property
    def meets_wr(self) -> bool:
        return self.win_rate_pct > spec.GOAL_WIN_RATE_PCT

    @property
    def meets_roi(self) -> bool:
        return self.monthly_roi_pct >= spec.GOAL_MONTHLY_ROI_PCT

    @property
    def meets_dd(self) -> bool:
        return self.max_dd_pct < spec.GOAL_MAX_DD_PCT

    @property
    def all_met(self) -> bool:
        return self.meets_wr and self.meets_roi and self.meets_dd

    def as_dict(self) -> Dict:
        d = dict(self.__dict__)
        d.update(meets_wr=self.meets_wr, meets_roi=self.meets_roi,
                 meets_dd=self.meets_dd, all_met=self.all_met)
        return d


def evaluate(win_rate_pct: float, real_outcomes: Sequence[float],
             leverage: float = spec.LEVERAGE,
             n_trades: int = spec.TARGET_TRADES_PER_MONTH,
             cost: float = spec.MAKER_COST_PCT,
             trials: int = 1200) -> GoalReport:
    """Score a full configuration against all three goals."""
    bs = bootstrap_drawdown(real_outcomes, leverage, n_trades, cost, trials)
    return GoalReport(
        win_rate_pct=win_rate_pct,
        monthly_roi_pct=bs.expected_roi_pct,
        max_dd_pct=bs.worst_dd_pct,
        leverage=leverage,
        n_trades=n_trades,
        instruments=instruments_required(n_trades),
    )
