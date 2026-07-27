"""
goal.py — derive exactly what the three goals require. No assertions, only algebra.

This module answers, from first principles:
  1. what daily return is needed for 1000%/month
  2. what Sharpe that implies at a given daily volatility
  3. what day-level win rate that Sharpe produces
  4. whether DD<4% survives a k-sigma bad day
  5. how many independent bets are needed to reach that Sharpe

Everything here is closed-form and unit-tested. Nothing is simulated.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist
from typing import Dict

from . import spec

_N = NormalDist()


def required_daily_return(terminal_mult: float = spec.GOAL_TERMINAL_MULT,
                          days: int = spec.GOAL_DAYS) -> float:
    """Daily compounded return needed to reach terminal_mult in `days`."""
    if days <= 0:
        raise ValueError("days must be positive")
    return terminal_mult ** (1.0 / days) - 1.0


def daily_sharpe(daily_return: float, daily_vol: float) -> float:
    if daily_vol <= 0:
        raise ValueError("daily_vol must be positive")
    return daily_return / daily_vol


def annualized_sharpe(daily_sharpe_value: float, trading_days: int = 252) -> float:
    return daily_sharpe_value * math.sqrt(trading_days)


def day_win_rate(daily_sharpe_value: float) -> float:
    """P(daily return > 0) for a normal daily distribution."""
    return _N.cdf(daily_sharpe_value)


def sigma_day_outcome(daily_return: float, daily_vol: float, k: float) -> float:
    """Return on a k-sigma ADVERSE day."""
    return daily_return - k * daily_vol


def sharpe_from_win_rate(win_rate: float) -> float:
    """Invert a win rate into the Sharpe that produced it."""
    if not 0.0 < win_rate < 1.0:
        raise ValueError("win_rate must be strictly between 0 and 1")
    return _N.inv_cdf(win_rate)


def bets_needed(target_sharpe: float, sharpe_per_bet: float) -> float:
    """N such that sharpe_per_bet * sqrt(N) == target_sharpe."""
    if sharpe_per_bet <= 0:
        raise ValueError("sharpe_per_bet must be positive")
    return (target_sharpe / sharpe_per_bet) ** 2


def sharpe_per_bet_needed(target_sharpe: float, n_bets: float) -> float:
    if n_bets <= 0:
        raise ValueError("n_bets must be positive")
    return target_sharpe / math.sqrt(n_bets)


@dataclass
class GoalSolution:
    daily_return: float
    daily_vol: float
    daily_sharpe: float
    annual_sharpe: float
    day_win_rate: float
    worst_3sigma: float
    worst_4sigma: float
    meets_roi: bool
    meets_wr: bool
    meets_dd: bool

    @property
    def all_met(self) -> bool:
        return self.meets_roi and self.meets_wr and self.meets_dd

    def as_dict(self) -> Dict:
        d = dict(self.__dict__)
        d["all_met"] = self.all_met
        return d


def solve(daily_vol: float,
          terminal_mult: float = spec.GOAL_TERMINAL_MULT,
          days: int = spec.GOAL_DAYS,
          max_dd: float = spec.GOAL_MAX_DD,
          min_wr: float = spec.GOAL_WIN_RATE) -> GoalSolution:
    """Given a daily volatility, can the three goals be met simultaneously?"""
    r = required_daily_return(terminal_mult, days)
    s = daily_sharpe(r, daily_vol)
    wr = day_win_rate(s)
    w3 = sigma_day_outcome(r, daily_vol, 3)
    w4 = sigma_day_outcome(r, daily_vol, 4)
    # DD goal: a 3-sigma adverse day must not breach the drawdown cap.
    return GoalSolution(
        daily_return=r,
        daily_vol=daily_vol,
        daily_sharpe=s,
        annual_sharpe=annualized_sharpe(s),
        day_win_rate=wr,
        worst_3sigma=w3,
        worst_4sigma=w4,
        meets_roi=True,          # r is constructed to meet it by definition
        meets_wr=wr >= min_wr,
        meets_dd=abs(min(0.0, w3)) < max_dd,
    )


def max_daily_vol_for_goals(**kw) -> float:
    """Largest daily vol at which all three goals still hold. Bisection."""
    lo, hi = 1e-6, 0.5
    if not solve(lo, **kw).all_met:
        return 0.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if solve(mid, **kw).all_met:
            lo = mid
        else:
            hi = mid
    return lo
