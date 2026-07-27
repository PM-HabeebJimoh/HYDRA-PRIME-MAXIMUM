"""Tests for v03A. Every claim in the README must be reproduced here."""

import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from a3 import economics as E
from a3 import guards as G
from a3 import spec


# ------------------------------------------------ measured inputs are intact ---

def test_flasharb_disclosure_arithmetic():
    assert E.flasharb_wins_per_day() == pytest.approx(892 / 90)
    assert E.flasharb_gross_per_win() == pytest.approx(47_320 / 892)
    assert E.flasharb_gas_per_tx() == pytest.approx((12_180 + 8_400) / 1247)


def test_public_mempool_net_matches_operator_disclosure():
    """FlashArb reported ~$8,213/month net. Reproduce it."""
    assert E.flasharb_monthly_net_public_mempool() == pytest.approx(8213.33, abs=1.0)


def test_private_bundles_recover_failed_gas():
    pub = E.flasharb_monthly_net_public_mempool()
    priv = E.flasharb_monthly_net_private_bundles()
    assert priv > pub
    # the entire difference is the failed-bid gas, monthly
    assert priv - pub == pytest.approx(spec.FA_GAS_FAILED_USD / 3.0, abs=1.0)


# ----------------------------------------------------- the capacity break ---

def test_mainnet_public_fails_the_goal():
    """The architecture as actually run by FlashArb does NOT hit the goal."""
    e = E.mainnet_economics_public()
    assert e.feasible_window(dead_days=30) is None


def test_l2_free_tier_meets_all_three_goals():
    e = E.l2_economics(infra_usd_month=spec.INFRA_FREE_TIER_USD_MO)
    r = e.recommended_reserve()
    assert r is not None
    rep = E.evaluate(e, r)
    assert rep.meets_roi, rep.monthly_roi_pct
    assert rep.meets_wr, rep.day_win_rate_pct
    assert rep.meets_dd, rep.dead_horizon_dd_pct
    assert rep.all_met


def test_l2_paid_entry_tier_meets_all_three_goals():
    e = E.l2_economics(infra_usd_month=spec.INFRA_CHAINSTACK_ENTRY_USD_MO)
    r = e.recommended_reserve()
    assert r is not None
    assert E.evaluate(e, r).all_met


def test_master_ratio_clears_30_dead_day_threshold():
    e = E.l2_economics(infra_usd_month=spec.INFRA_CHAINSTACK_ENTRY_USD_MO)
    assert e.master_ratio > 250 * spec.GOAL_DEAD_DAY_HORIZON


def test_master_ratio_formula_matches_feasibility():
    """ratio > 250*N  <=>  a feasible reserve window exists."""
    for infra in (0.5, 5.0, 50.0, 500.0, 700.0):
        e = E.l2_economics(infra_usd_month=infra)
        has_window = e.feasible_window(30) is not None
        clears = e.master_ratio > 250 * 30
        assert has_window == clears, infra


# ---------------------------------------------------------- win rate model ---

def test_day_win_rate_exceeds_80_percent():
    e = E.l2_economics()
    assert e.day_win_rate() > 0.80


def test_trade_level_win_rate_is_below_80_but_day_level_is_not():
    """The Virtu inversion: unit of account changes the win rate."""
    trade_wr = spec.FA_TX_SUCCESS / spec.FA_TX_SUBMITTED
    assert trade_wr < 0.80
    assert E.l2_economics().day_win_rate() > 0.80


def test_breakeven_far_below_actual_arrival_rate():
    e = E.l2_economics()
    assert e.breakeven_wins_per_day < e.wins_per_day / 5


def test_poisson_probability_is_a_probability():
    e = E.l2_economics()
    p = e.day_loss_probability()
    assert 0.0 <= p <= 1.0


# ------------------------------------------------------------ trading DD=0 ---

def test_net_per_win_is_always_positive():
    e = E.l2_economics()
    assert e.net_per_win > 0


def test_trading_drawdown_is_structurally_zero():
    e = E.l2_economics()
    rep = E.evaluate(e, e.recommended_reserve())
    assert rep.trading_dd_pct == 0.0


# ----------------------------------------------------------------- guards ---

def _ok_intent(**kw):
    base = dict(expected_profit_usd=5.0, gas_cost_usd=0.02,
                private_submission=True, simulated_ok=True,
                borrowed_capital_usd=100_000.0, own_capital_at_risk_usd=0.0)
    base.update(kw)
    return G.BundleIntent(**base)


def test_public_mempool_submission_is_rejected():
    with pytest.raises(G.GuardViolation, match="public mempool"):
        G.validate(_ok_intent(private_submission=False))


def test_unsimulated_bundle_rejected():
    with pytest.raises(G.GuardViolation, match="not simulated"):
        G.validate(_ok_intent(simulated_ok=False))


def test_thin_profit_rejected():
    with pytest.raises(G.GuardViolation):
        G.validate(_ok_intent(expected_profit_usd=0.03, gas_cost_usd=0.02))


def test_own_capital_at_risk_rejected():
    with pytest.raises(G.GuardViolation, match="own capital"):
        G.validate(_ok_intent(own_capital_at_risk_usd=1.0))


def test_valid_intent_passes():
    assert G.is_valid(_ok_intent())


# -------------------------------------------------------- reserve governor ---

def test_governor_halts_before_goal_cap():
    gov = G.ReserveGovernor(reserve_usd=100.0)
    for _ in range(1000):
        if not gov.may_submit():
            break
        gov.debit_infra(0.10)
    assert gov.halted
    assert gov.drawdown < spec.GOAL_MAX_DD + 1e-9


def test_governor_profit_raises_peak():
    gov = G.ReserveGovernor(reserve_usd=100.0)
    gov.credit_profit(50.0)
    assert gov.peak_usd == pytest.approx(150.0)
    assert gov.drawdown == 0.0


def test_governor_rejects_negative_amounts():
    gov = G.ReserveGovernor(reserve_usd=100.0)
    with pytest.raises(ValueError):
        gov.debit_infra(-1.0)
    with pytest.raises(ValueError):
        gov.credit_profit(-1.0)


# ------------------------------------------------------ sensitivity to the ---
#                                                        central assumption ---

def test_goal_survives_much_harsher_l2_penalty():
    """Even at 50x penalty (5x worse than assumed) the goal still holds."""
    e = E.l2_economics(penalty=50.0,
                       infra_usd_month=spec.INFRA_FREE_TIER_USD_MO)
    r = e.recommended_reserve()
    assert r is not None
    assert E.evaluate(e, r).all_met


def test_goal_breaks_at_extreme_penalty():
    """Honesty check: the model is falsifiable, not unconditionally true."""
    e = E.l2_economics(penalty=1e6,
                       infra_usd_month=spec.INFRA_FLASHARB_MAINNET_USD_MO)
    assert e.feasible_window(30) is None


def test_evaluate_rejects_nonpositive_reserve():
    with pytest.raises(ValueError):
        E.evaluate(E.l2_economics(), 0.0)
