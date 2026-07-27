"""Every claim in V02M_THESIS.md, re-derived independently."""

import json
import math
import os
import sys
from statistics import NormalDist

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from m2 import capacity, correlation, goal, spec


# ------------------------------------------------------------------- goal ---

def test_required_daily_return_matches_hand_arithmetic():
    r = goal.required_daily_return(11.0, 30)
    assert r == pytest.approx(11.0 ** (1 / 30) - 1)
    assert r == pytest.approx(0.083211, abs=1e-6)


def test_compounding_actually_reaches_11x():
    r = goal.required_daily_return(11.0, 30)
    assert (1 + r) ** 30 == pytest.approx(11.0, rel=1e-12)


def test_daily_sharpe_is_return_over_vol():
    assert goal.daily_sharpe(0.0832, 0.02) == pytest.approx(4.16, abs=0.01)


def test_win_rate_and_sharpe_are_inverses():
    for s in (0.5, 1.0, 2.0, 3.153, 4.16):
        assert goal.sharpe_from_win_rate(goal.day_win_rate(s)) == pytest.approx(s, abs=1e-9)


def test_virtu_benchmark_reproduces_from_sec_filing():
    """1,238 days, one loss -> daily Sharpe ~3.15, annualized ~50."""
    wr = 1237 / 1238
    s = goal.sharpe_from_win_rate(wr)
    assert s == pytest.approx(3.153, abs=0.01)
    assert goal.annualized_sharpe(s) == pytest.approx(50.1, abs=0.5)


def test_goal_met_at_two_percent_vol():
    s = goal.solve(0.02)
    assert s.all_met
    assert s.day_win_rate > 0.999
    assert s.worst_3sigma > 0            # 3-sigma bad day is still positive


def test_goal_fails_at_high_vol():
    assert not goal.solve(0.10).all_met


def test_max_vol_boundary_is_a_real_boundary():
    mv = goal.max_daily_vol_for_goals()
    assert goal.solve(mv * 0.999).all_met
    assert not goal.solve(mv * 1.01).all_met
    assert mv == pytest.approx(0.0411, abs=0.001)


def test_required_sharpe_is_below_virtu():
    """The headline claim: the goal needs LESS than Virtu's documented Sharpe."""
    mv = goal.max_daily_vol_for_goals()
    required = goal.solve(mv).annual_sharpe
    virtu = goal.annualized_sharpe(goal.sharpe_from_win_rate(1237 / 1238))
    assert required < virtu
    assert required / virtu == pytest.approx(0.64, abs=0.05)


def test_bets_needed_roundtrips():
    n = goal.bets_needed(4.16, 0.1)
    assert goal.sharpe_per_bet_needed(4.16, n) == pytest.approx(0.1)


def test_goal_rejects_bad_input():
    with pytest.raises(ValueError):
        goal.daily_sharpe(0.01, 0)
    with pytest.raises(ValueError):
        goal.sharpe_from_win_rate(1.0)
    with pytest.raises(ValueError):
        goal.bets_needed(1.0, 0)


# ------------------------------------------------------------ correlation ---

def test_pearson_against_known_values():
    assert correlation.pearson([1, 2, 3], [1, 2, 3]) == pytest.approx(1.0)
    assert correlation.pearson([1, 2, 3], [3, 2, 1]) == pytest.approx(-1.0)
    assert correlation.pearson([1, 1, 1], [1, 2, 3]) == 0.0


def test_effective_n_endpoints():
    assert correlation.effective_n(111, 0.0) == pytest.approx(111)
    assert correlation.effective_n(111, 1.0) == pytest.approx(1.0)
    assert correlation.effective_n(1, 0.5) == 1


def test_measured_directional_correlation_is_high():
    d = correlation.load()
    rets = {k: correlation.returns(v["close"]) for k, v in d["instruments"].items()}
    rep = correlation.correlation_report(rets)
    assert rep.avg_offdiag > 0.8
    assert rep.avg_offdiag == pytest.approx(spec.MEASURED_DIRECTIONAL_RHO, abs=0.01)


def test_beta_hedging_materially_reduces_correlation():
    """The honest finding: hedging helps, but not enough on its own."""
    d = correlation.load()
    rets = {k: correlation.returns(v["close"]) for k, v in d["instruments"].items()}
    btc = rets["BTC-USD"]
    res = {}
    for k, v in rets.items():
        if k == "BTC-USD":
            continue
        mb, mv = correlation.mean(btc), correlation.mean(v)
        cov = sum((x - mb) * (y - mv) for x, y in zip(btc, v))
        var = sum((x - mb) ** 2 for x in btc)
        beta = cov / var
        res[k] = [y - beta * x for x, y in zip(btc, v)]
    rep = correlation.correlation_report(res)
    assert rep.avg_offdiag == pytest.approx(spec.MEASURED_RESIDUAL_RHO, abs=0.01)
    assert rep.avg_offdiag < spec.MEASURED_DIRECTIONAL_RHO


def test_cross_section_alone_cannot_reach_goal():
    """111 instruments at measured residual rho gives only ~2.2 effective bets."""
    ne = correlation.effective_n(111, spec.MEASURED_RESIDUAL_RHO)
    assert ne < 3.0
    assert math.sqrt(ne) < 2.0


def test_time_axis_supplies_the_missing_n():
    """1,000 fills/day x 2.23 cross gives an achievable per-fill Sharpe."""
    total = 1000 * correlation.effective_n(111, spec.MEASURED_RESIDUAL_RHO)
    need = goal.sharpe_per_bet_needed(4.16, total)
    assert need < 0.15


# --------------------------------------------------------------- capacity ---

def test_volumes_load_and_are_positive():
    v = capacity.load_volumes()
    assert len(v) >= 4
    assert all(x > 0 for x in v.values())


def test_required_notional_inverts_capture():
    n = capacity.required_notional(10_000, 0.0832, 1.0)
    assert n * 1e-4 == pytest.approx(10_000 * 0.0832)


def test_capacity_binds_and_caps_growth():
    v = capacity.load_volumes()
    tot = sum(v.values())
    r = goal.required_daily_return()
    rep = capacity.project(spec.INITIAL_CAPITAL, r, 1.0, tot, days=60)
    assert rep.first_capped_day is not None
    assert rep.first_capped_day < 30
    # capped path must fall far short of the uncapped fantasy
    assert rep.terminal_equity_capped < rep.terminal_equity_uncapped / 5


def test_max_sustainable_equity_is_bounded():
    r = goal.required_daily_return()
    m = capacity.max_equity_at_capacity(2.0, r, 200e9)
    assert m < 1_000_000          # the ceiling is real
    assert m > 100_000            # but month-1 target fits under it


def test_month_one_target_fits_under_capacity_ceiling():
    """The central verdict: month 1 feasible, month 2 not."""
    r = goal.required_daily_return()
    ceiling = capacity.max_equity_at_capacity(2.0, r, 200e9)
    month1 = spec.INITIAL_CAPITAL * 11.0
    assert month1 < ceiling
    month2 = spec.INITIAL_CAPITAL * 121.0
    assert month2 > ceiling


# ------------------------------------------------------------------ guards ---

def test_v02m_does_not_import_v01t():
    """v02M must be completely independent of the v01T model."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for dirpath, _dirs, files in os.walk(os.path.join(root, "m2")):
        for f in files:
            if not f.endswith(".py"):
                continue
            src = open(os.path.join(dirpath, f)).read()
            assert "v01t" not in src.lower() or "v01T" in src  # only prose refs
            assert "import v01t" not in src
            assert "from v01t" not in src


def test_leverage_is_sane():
    assert spec.MAX_LEVERAGE <= 3
    assert spec.KILL_SWITCH_DD < spec.GOAL_MAX_DD


def test_maker_fee_is_a_rebate():
    assert spec.MAKER_FEE_BPS < 0
    assert spec.TAKER_FEE_BPS > 0


def test_dataset_is_real_and_aligned():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    d = json.load(open(os.path.join(root, "data", "daily_5inst_jul2026.json")))
    assert "Yahoo" in d["source"]
    n = d["bars"]
    assert n == len(d["timestamps"])
    for sym, series in d["instruments"].items():
        assert len(series["close"]) == n, sym
        assert all(c > 0 for c in series["close"]), sym
