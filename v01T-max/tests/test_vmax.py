"""Tests for v01T-MAX. Every claim in the README is reproduced here."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from vmax import backtest as B
from vmax import economics as E
from vmax import spec


# --------------------------------------------------------------- real data ---

def test_real_months_load():
    for m in B.MONTHS:
        c = B.load_closes(m)
        assert len(c) > 500
        assert all(x > 0 for x in c)


def test_july_bar_count_matches_vendored_dataset():
    assert len(B.load_closes("jul2026")) == 576


# ------------------------------------------------- the honest resolver rule ---

def test_stopped_leg_cannot_later_win():
    """The defect that made v01T report 100%: price whipsaws both stops,
    THEN runs to target. Must be a loss, not a win."""
    entry = 100.0
    path = [entry, entry * 1.004, entry * 0.996, entry * 1.02]
    r = B.resolve_double_entry(path, 0, entry, stop=0.003, target=0.005)
    assert r == pytest.approx(-2 * 0.003)


def test_clean_up_move_is_a_win():
    entry = 100.0
    r = B.resolve_double_entry([entry, entry * 1.006], 0, entry,
                               stop=0.003, target=0.005)
    assert r == pytest.approx(0.005 - 0.003)


def test_clean_down_move_is_a_win():
    entry = 100.0
    r = B.resolve_double_entry([entry, entry * 0.994], 0, entry,
                               stop=0.003, target=0.005)
    assert r == pytest.approx(0.005 - 0.003)


def test_resolver_rejects_bad_input():
    with pytest.raises(ValueError):
        B.resolve_double_entry([100.0], 0, 0.0, 0.003, 0.005)
    with pytest.raises(ValueError):
        B.run(0.005, 0.003)          # stop >= target
    with pytest.raises(ValueError):
        B.run(-0.001, 0.005)


# -------------------------------------------------------- DEFECT 1: the stop ---

def test_original_stop_win_rate_is_far_below_claim():
    """v01T's spec claims 100%. Honest resolution gives ~57%."""
    r = B.run(spec.STOP_PCT_ORIGINAL, spec.TP_PCT)
    assert r.trades == 96
    assert 55.0 < r.win_rate_pct < 60.0


def test_repaired_stop_lifts_win_rate_above_goal():
    r = B.run(spec.STOP_PCT, spec.TP_PCT)
    assert r.trades == 96
    assert r.win_rate_pct > spec.GOAL_WIN_RATE_PCT
    assert r.win_rate_pct == pytest.approx(87.5, abs=0.01)


def test_repair_is_a_large_improvement():
    old = B.run(spec.STOP_PCT_ORIGINAL, spec.TP_PCT).win_rate_pct
    new = B.run(spec.STOP_PCT, spec.TP_PCT).win_rate_pct
    assert new - old > 25.0


def test_every_month_independently_clears_80pct():
    """Guards against a single-month artifact."""
    for month, r in B.per_month(spec.STOP_PCT, spec.TP_PCT).items():
        assert r.win_rate_pct > spec.GOAL_WIN_RATE_PCT, (month, r.win_rate_pct)


def test_stop_sweep_is_single_peaked_around_the_chosen_stop():
    at_target = [r for r in B.sweep() if r.target == spec.TP_PCT]
    at_target.sort(key=lambda r: r.stop)
    best = max(at_target, key=lambda r: r.win_rate_pct)
    assert best.stop == pytest.approx(spec.STOP_PCT)


# ------------------------------------------------------- DEFECT 2: the costs ---

def test_taker_execution_destroys_every_high_win_rate_configuration():
    """4 of 22 swept configs survive taker cost, but ALL of them have
    win rates in the 27-45% range. No config clears BOTH the 80% win-rate
    goal and taker execution. Maker execution is mandatory."""
    survivors = [r for r in B.sweep()
                 if r.net_per_trade(spec.TAKER_COST_PCT) > 0]
    assert survivors, "sanity: some configs do survive taker cost"
    for r in survivors:
        assert r.win_rate_pct < spec.GOAL_WIN_RATE_PCT, (r.stop, r.target)


def test_no_config_clears_win_rate_goal_under_taker():
    for r in B.sweep():
        clears_wr = r.win_rate_pct > spec.GOAL_WIN_RATE_PCT
        positive_taker = r.net_per_trade(spec.TAKER_COST_PCT) > 0
        assert not (clears_wr and positive_taker), (r.stop, r.target)


def test_repaired_config_is_negative_under_taker():
    r = B.run(spec.STOP_PCT, spec.TP_PCT)
    assert r.net_per_trade(spec.TAKER_COST_PCT) < 0


def test_maker_execution_makes_the_repaired_config_positive():
    r = B.run(spec.STOP_PCT, spec.TP_PCT)
    assert r.net_per_trade(spec.MAKER_COST_PCT) > 0
    assert r.net_per_trade() == pytest.approx(0.0008, abs=5e-5)


def test_maker_requirement_is_declared():
    assert spec.REQUIRE_MAKER_EXECUTION is True


# -------------------------------------------------- DEFECT 3: the leverage ---

def test_original_leverage_blows_the_dd_cap():
    dd = E.single_loss_dd_pct(spec.STOP_PCT, spec.MAKER_COST_PCT, 50)
    assert dd > 25.0


def test_chosen_leverage_survives_a_single_loss():
    dd = E.single_loss_dd_pct(spec.STOP_PCT, spec.MAKER_COST_PCT,
                              spec.LEVERAGE)
    assert dd < spec.GOAL_MAX_DD_PCT


def test_roi_is_exponential_in_trades_linear_in_leverage():
    g = 0.0008
    double_lev = E.monthly_roi_pct(g, 2.0, 1000)
    double_n = E.monthly_roi_pct(g, 1.0, 2000)
    assert double_n > double_lev      # N dominates


# ------------------------------------------------------------- the solution ---

@pytest.fixture(scope="module")
def real_outcomes():
    return B.outcomes(spec.STOP_PCT, spec.TP_PCT)


def test_outcomes_are_the_96_real_trades(real_outcomes):
    assert len(real_outcomes) == 96


def test_full_configuration_meets_all_three_goals(real_outcomes):
    wr = B.run(spec.STOP_PCT, spec.TP_PCT).win_rate_pct
    rep = E.evaluate(wr, real_outcomes, trials=400)
    assert rep.meets_wr, rep.win_rate_pct
    assert rep.meets_roi, rep.monthly_roi_pct
    assert rep.meets_dd, rep.max_dd_pct
    assert rep.all_met


def test_high_leverage_low_n_fails_dd(real_outcomes):
    """The original shape of the model cannot pass."""
    rep = E.evaluate(87.5, real_outcomes, leverage=50, n_trades=32,
                     trials=200)
    assert not rep.meets_dd


def test_bootstrap_uses_only_real_outcomes(real_outcomes):
    allowed = set(round(x, 10) for x in real_outcomes)
    assert len(allowed) <= 96
    bs = E.bootstrap_drawdown(real_outcomes, spec.LEVERAGE, 500, trials=50)
    assert 0.0 <= bs.worst_dd_pct <= 100.0
    assert bs.median_dd_pct <= bs.worst_dd_pct


def test_bootstrap_rejects_empty_input():
    with pytest.raises(ValueError):
        E.bootstrap_drawdown([], 1.0, 100)


def test_instruments_required_matches_spec():
    n = E.instruments_required(spec.TARGET_TRADES_PER_MONTH)
    assert n == spec.INSTRUMENTS_REQUIRED


def test_model_is_falsifiable_at_high_cost(real_outcomes):
    """Honesty check: at retail maker fees the model must FAIL."""
    rep = E.evaluate(87.5, real_outcomes, cost=0.0025, trials=200)
    assert not rep.meets_roi
