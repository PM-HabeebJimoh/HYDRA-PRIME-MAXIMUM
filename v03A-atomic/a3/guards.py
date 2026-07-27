"""
guards.py — the invariants that make v03A's drawdown structurally zero.

These are not risk *preferences*. They are the conditions under which the
DD=0 claim is true at all. If any guard is bypassed, the model's central
property is void and the numbers in economics.py no longer apply.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from . import spec


class GuardViolation(Exception):
    """Raised when a submission would break a structural invariant."""


@dataclass(frozen=True)
class BundleIntent:
    """A proposed atomic arbitrage submission."""

    expected_profit_usd: float
    gas_cost_usd: float
    private_submission: bool
    simulated_ok: bool
    borrowed_capital_usd: float = 0.0
    own_capital_at_risk_usd: float = 0.0


def check_private_submission(intent: BundleIntent) -> None:
    """MANDATORY. Public mempool re-introduces failed-bid gas.

    Flashbots: "Failed trade privacy: Losing bids are never included in a
    block." That is the entire basis for worst_day_loss = infra only.
    FlashArb burned $8,400 in 3 months precisely because they sometimes
    "ate the loss and used public mempool anyway".
    """
    if spec.REQUIRE_PRIVATE_BUNDLES and not intent.private_submission:
        raise GuardViolation(
            "public mempool submission forbidden: failed bids would revert "
            "on-chain and burn gas, breaking the zero-trading-drawdown "
            "invariant that the entire v03A model rests on"
        )


def check_profit_covers_gas(intent: BundleIntent) -> None:
    """Never submit unless profit comfortably exceeds gas.

    The on-chain contract also enforces profit > 0 via revert, but this is
    the off-chain gate that keeps net_per_win positive with margin.
    """
    if intent.gas_cost_usd < 0:
        raise GuardViolation("gas cost cannot be negative")
    threshold = spec.MIN_PROFIT_MULTIPLE_OF_GAS * intent.gas_cost_usd
    if intent.expected_profit_usd < threshold:
        raise GuardViolation(
            f"expected profit ${intent.expected_profit_usd:.4f} below "
            f"{spec.MIN_PROFIT_MULTIPLE_OF_GAS}x gas ${intent.gas_cost_usd:.4f}"
        )


def check_simulated(intent: BundleIntent) -> None:
    """Every bundle must be simulated before submission."""
    if not intent.simulated_ok:
        raise GuardViolation("bundle not simulated; refusing to submit")


def check_no_own_capital_at_risk(intent: BundleIntent) -> None:
    """The trade capital must be BORROWED, not the operator's.

    This is what decouples profit from account size and removes the
    capacity wall that bounded v01T and v02M.
    """
    if intent.own_capital_at_risk_usd > 0:
        raise GuardViolation(
            "own capital at risk: v03A trades flash-loaned capital only; "
            "principal exposure re-introduces the capacity constraint"
        )


ALL_GUARDS = (
    check_private_submission,
    check_profit_covers_gas,
    check_simulated,
    check_no_own_capital_at_risk,
)


def validate(intent: BundleIntent) -> None:
    """Run every guard. Raises GuardViolation on the first failure."""
    for g in ALL_GUARDS:
        g(intent)


def is_valid(intent: BundleIntent) -> bool:
    try:
        validate(intent)
        return True
    except GuardViolation:
        return False


# ------------------------------------------------------- reserve governor ---

@dataclass
class ReserveGovernor:
    """Enforces the drawdown cap on the gas reserve at runtime."""

    reserve_usd: float
    peak_usd: float = 0.0
    halted: bool = False
    halt_reason: Optional[str] = None

    def __post_init__(self) -> None:
        if self.reserve_usd <= 0:
            raise ValueError("reserve must be positive")
        self.peak_usd = max(self.peak_usd, self.reserve_usd)

    @property
    def drawdown(self) -> float:
        if self.peak_usd <= 0:
            return 0.0
        return max(0.0, (self.peak_usd - self.reserve_usd) / self.peak_usd)

    def debit_infra(self, usd: float) -> None:
        """Infra is the only thing that can draw the reserve down."""
        if usd < 0:
            raise ValueError("infra debit cannot be negative")
        self.reserve_usd -= usd
        self._check()

    def credit_profit(self, usd: float) -> None:
        if usd < 0:
            raise ValueError("profit credit cannot be negative")
        self.reserve_usd += usd
        self.peak_usd = max(self.peak_usd, self.reserve_usd)

    def _check(self) -> None:
        if self.drawdown >= spec.KILL_SWITCH_DD:
            self.halted = True
            self.halt_reason = (
                f"drawdown {self.drawdown*100:.3f}% reached kill switch "
                f"{spec.KILL_SWITCH_DD*100:.1f}% (goal cap "
                f"{spec.GOAL_MAX_DD*100:.1f}%)"
            )

    def may_submit(self) -> bool:
        return not self.halted
