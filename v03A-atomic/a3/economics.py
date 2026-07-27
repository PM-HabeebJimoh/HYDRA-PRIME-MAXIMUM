"""
economics.py — the v03A profit/risk model. Closed form, no simulation.

Everything here is algebra over the constants in spec.py. Nothing is
randomised, nothing is fitted, nothing is back-solved to hit a target.

THE MASTER RATIO
----------------
    ROI > 1000%/mo          =>  reserve < monthly_net / 10
    DD  < 4% over N dead days =>  reserve > N * infra_day / 0.04

    FEASIBLE  <=>  monthly_net / infra_day  >  250 * N

This single number decides all three goals at once and is architecture
independent. Measured operators on Ethereum mainnet sit at 36-57.
v03A on an L2 with free-tier infra clears 9,000+.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional

from . import spec


# --------------------------------------------------------------- primitives ---

def flasharb_wins_per_day() -> float:
    """[MEASURED] successful arbs per day from the FlashArb disclosure."""
    return spec.FA_TX_SUCCESS / spec.FA_DAYS


def flasharb_gross_per_win() -> float:
    """[MEASURED] gross USD per successful arb."""
    return spec.FA_GROSS_USD / spec.FA_TX_SUCCESS


def flasharb_gas_per_tx() -> float:
    """[DERIVED] blended gas per submitted tx on Ethereum mainnet."""
    return (spec.FA_GAS_SUCCESS_USD + spec.FA_GAS_FAILED_USD) / spec.FA_TX_SUBMITTED


def flasharb_monthly_net_public_mempool() -> float:
    """[MEASURED] what the operator actually netted, paying failed-bid gas."""
    total = (spec.FA_GROSS_USD - spec.FA_GAS_SUCCESS_USD
             - spec.FA_GAS_FAILED_USD - spec.FA_INFRA_USD)
    return total / (spec.FA_DAYS / 30.0)


def flasharb_monthly_net_private_bundles() -> float:
    """[DERIVED] the same operation with failed-bid gas eliminated.

    Justified by the Flashbots primary source quoted in spec.py: losing
    bids are never included in a block, so they cost nothing.
    """
    total = (spec.FA_GROSS_USD - spec.FA_GAS_SUCCESS_USD - spec.FA_INFRA_USD)
    return total / (spec.FA_DAYS / 30.0)


# ------------------------------------------------------------- the L2 model ---

@dataclass(frozen=True)
class Economics:
    """A fully specified v03A configuration."""

    gross_per_win: float
    gas_per_tx: float
    wins_per_day: float
    infra_usd_month: float

    @property
    def infra_per_day(self) -> float:
        return self.infra_usd_month / 30.0

    @property
    def net_per_win(self) -> float:
        """Always positive: the contract reverts unless profit > gas."""
        return self.gross_per_win - self.gas_per_tx

    @property
    def daily_net(self) -> float:
        return self.wins_per_day * self.net_per_win - self.infra_per_day

    @property
    def monthly_net(self) -> float:
        return self.daily_net * 30.0

    @property
    def master_ratio(self) -> float:
        """monthly_net / infra_per_day. Decides all three goals."""
        if self.infra_per_day <= 0:
            return math.inf
        return self.monthly_net / self.infra_per_day

    @property
    def breakeven_wins_per_day(self) -> float:
        """Wins needed to cover infra. Below this a day is a loss."""
        if self.net_per_win <= 0:
            return math.inf
        return self.infra_per_day / self.net_per_win

    def day_loss_probability(self) -> float:
        """P(a day nets negative), Poisson on the win count.

        Opportunity arrivals are independent events -> Poisson is the
        correct model. A day loses only if wins < breakeven_wins_per_day.
        """
        lam = self.wins_per_day
        k = self.breakeven_wins_per_day
        if math.isinf(k):
            return 1.0
        kmax = int(math.floor(k))
        return sum(math.exp(-lam) * lam ** i / math.factorial(i)
                   for i in range(0, kmax + 1))

    def day_win_rate(self) -> float:
        return 1.0 - self.day_loss_probability()

    # ------------------------------------------------------ reserve sizing ---

    def min_reserve_for_dd(self, dead_days: int = spec.GOAL_DEAD_DAY_HORIZON,
                           max_dd: float = spec.GOAL_MAX_DD) -> float:
        """Smallest reserve that survives `dead_days` inside the DD cap."""
        return dead_days * self.infra_per_day / max_dd

    def max_reserve_for_roi(self, min_roi_pct: float = spec.GOAL_MONTHLY_ROI_PCT
                            ) -> float:
        """Largest reserve that still clears the ROI floor."""
        return self.monthly_net / (min_roi_pct / 100.0)

    def feasible_window(self, dead_days: int = spec.GOAL_DEAD_DAY_HORIZON):
        lo = self.min_reserve_for_dd(dead_days)
        hi = self.max_reserve_for_roi()
        return (lo, hi) if lo < hi else None

    def recommended_reserve(self, dead_days: int = spec.GOAL_DEAD_DAY_HORIZON
                            ) -> Optional[float]:
        """Geometric mean of the window: maximal margin on both constraints."""
        w = self.feasible_window(dead_days)
        return math.sqrt(w[0] * w[1]) if w else None


# ------------------------------------------------------------- goal report ---

@dataclass
class GoalReport:
    reserve: float
    monthly_roi_pct: float
    day_win_rate_pct: float
    worst_day_dd_pct: float
    dead_horizon_dd_pct: float
    trading_dd_pct: float
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


def evaluate(e: Economics, reserve: float,
             dead_days: int = spec.GOAL_DEAD_DAY_HORIZON) -> GoalReport:
    """Score one configuration against all three goals."""
    if reserve <= 0:
        raise ValueError("reserve must be positive")
    roi = e.monthly_net / reserve * 100.0
    wr = e.day_win_rate() * 100.0
    dd1 = e.infra_per_day / reserve * 100.0
    ddN = dead_days * e.infra_per_day / reserve * 100.0
    return GoalReport(
        reserve=reserve,
        monthly_roi_pct=roi,
        day_win_rate_pct=wr,
        worst_day_dd_pct=dd1,
        dead_horizon_dd_pct=ddN,
        trading_dd_pct=0.0,          # atomic revert: structurally zero
        meets_roi=roi > spec.GOAL_MONTHLY_ROI_PCT,
        meets_wr=wr > spec.GOAL_DAY_WIN_RATE * 100.0,
        meets_dd=ddN < spec.GOAL_MAX_DD * 100.0,
    )


# ------------------------------------------------------------ constructors ---

def l2_economics(gas_per_tx: float = spec.GAS_BASE_USD,
                 infra_usd_month: float = spec.INFRA_CHAINSTACK_ENTRY_USD_MO,
                 penalty: float = spec.L2_OPPORTUNITY_PENALTY) -> Economics:
    """The v03A configuration: FlashArb frequency, L2 gas, penalised size.

    `penalty` is the load-bearing ASSUMPTION (see spec.L2_OPPORTUNITY_PENALTY).
    """
    if penalty <= 0:
        raise ValueError("penalty must be positive")
    return Economics(
        gross_per_win=flasharb_gross_per_win() / penalty,
        gas_per_tx=gas_per_tx,
        wins_per_day=flasharb_wins_per_day(),
        infra_usd_month=infra_usd_month,
    )


def mainnet_economics_public() -> Economics:
    """FlashArb as actually run: mainnet gas, public mempool, archive nodes."""
    return Economics(
        gross_per_win=flasharb_gross_per_win(),
        gas_per_tx=flasharb_gas_per_tx(),
        wins_per_day=flasharb_wins_per_day(),
        infra_usd_month=spec.INFRA_FLASHARB_MAINNET_USD_MO,
    )
