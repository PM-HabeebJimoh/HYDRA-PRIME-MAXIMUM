"""
Independent audit of every trading rule.

These tests do NOT call the implementation and compare it to itself. Each one
re-derives the expected value from a separate reference implementation or from
hand arithmetic, so a silent change in the maths fails the build.
"""

import random
import statistics

import pytest

from v01t import spec
from v01t.dataset import load_month
from v01t.indicators import (compute_bb_percentile, compute_hv_ratio,
                             is_elite, score_for)
from v01t.kucoin_executor import KucoinExecutor, RiskLimits
from v01t.sizing import DEFAULT_SIZER
from v01t.vol_expansion import LOSS_MULT, WIN_MULT, VolExpansionModel


# --------------------------------------------------- BB% vs a reference ---

def _bb_reference(closes):
    """Textbook Bollinger %B: SMA20, population stdev, 2 sigma."""
    w = closes[-20:]
    sma = sum(w) / 20
    sd = (sum((x - sma) ** 2 for x in w) / 20) ** 0.5
    if sd == 0:
        return 50.0
    upper, lower = sma + 2 * sd, sma - 2 * sd
    return (closes[-1] - lower) / (upper - lower) * 100


def test_bb_matches_an_independent_implementation():
    random.seed(11)
    worst = 0.0
    for _ in range(300):
        c = [100.0]
        for _ in range(40):
            c.append(c[-1] * (1 + random.uniform(-0.03, 0.03)))
        worst = max(worst, abs(compute_bb_percentile(c) - _bb_reference(c)))
    assert worst < 0.011          # implementation rounds to 2dp


@pytest.mark.parametrize("series,lo,hi,desc", [
    ([100.0] * 20, 49.9, 50.1, "zero-width band returns neutral"),
    ([100.0] * 19 + [130.0], 90.0, 1e9, "spike up is above the upper band"),
    ([100.0] * 19 + [70.0], -1e9, 10.0, "spike down is below the lower band"),
    ([1.0, 2.0, 3.0, 4.0, 5.0], 49.9, 50.1, "short series falls back to 50"),
])
def test_bb_known_values(series, lo, hi, desc):
    assert lo <= compute_bb_percentile(series) <= hi, desc


# ---------------------------------------------- HV ratio vs a reference ---

def _hv_reference(c):
    r = [c[i] / c[i - 1] - 1 for i in range(1, len(c))]
    return statistics.stdev(r[-5:]) / statistics.stdev(r[-20:])


def test_hv_matches_an_independent_implementation():
    random.seed(5)
    worst = 0.0
    for _ in range(300):
        c = [100.0]
        for _ in range(45):
            c.append(c[-1] * (1 + random.uniform(-0.02, 0.02)))
        worst = max(worst, abs(compute_hv_ratio(c) - _hv_reference(c)))
    assert worst < 0.0011         # implementation rounds to 3dp


def test_hv_detects_volatility_compression():
    """A calm tail after a noisy body must lower the ratio."""
    random.seed(7)
    noisy = [100.0]
    for _ in range(35):
        noisy.append(noisy[-1] * (1 + random.uniform(-0.03, 0.03)))
    calm = noisy + [noisy[-1] * (1 + 0.00002 * i) for i in range(1, 6)]
    assert compute_hv_ratio(calm) < compute_hv_ratio(noisy)


def test_hv_flat_series_falls_back_to_one():
    assert compute_hv_ratio([100.0] * 40) == 1.0


# ------------------------------------------------------------ score map ---

@pytest.mark.parametrize("bb,expected", [
    (5, 92), (9.99, 92), (10, 72), (50, 72), (90, 72), (90.01, 85), (95, 85),
])
def test_score_mapping(bb, expected):
    assert score_for(bb) == expected


# ---------------------------------------------------- elite truth table ---

@pytest.mark.parametrize("bb,hv,expected,desc", [
    (5, 0.4, True, "lower band + compressed"),
    (95, 0.4, True, "upper band + compressed"),
    (50, 0.4, False, "mid band rejected"),
    (5, 0.9, False, "insufficient compression rejected"),
    (spec.BB_LOW, 0.4, False, "BB boundary is strict <"),
    (spec.BB_HIGH, 0.4, False, "BB boundary is strict >"),
    (5, spec.HV_MAX, False, "HV boundary is strict <"),
])
def test_elite_gate_truth_table(bb, hv, expected, desc):
    assert is_elite(bb, hv, score_for(bb)) is expected, desc


# -------------------------------------------------------------- win rule ---

@pytest.mark.parametrize("tail,expected,desc", [
    ([100.5], True, "+0.50% exactly triggers"),
    ([99.5], True, "-0.50% exactly triggers"),
    ([100.49], False, "+0.49% does not"),
    ([99.51], False, "-0.49% does not"),
    ([100.1, 100.2, 100.6], True, "resolves on a later bar"),
    ([100.1, 100.2, 99.9], False, "never reaches the threshold"),
])
def test_win_rule(tail, expected, desc):
    win, _, _ = VolExpansionModel(window=24).expansion_win(tail, 100.0)
    assert win is expected, desc


def test_win_rule_is_direction_agnostic():
    m = VolExpansionModel(window=24)
    assert m.expansion_win([100.6], 100.0)[0] is True
    assert m.expansion_win([99.4], 100.0)[0] is True


# ----------------------------------------------------------- ledger maths ---

def test_multipliers_derive_from_the_spec():
    assert WIN_MULT == pytest.approx(1 + (spec.TP_PCT - spec.STOP_PCT) * spec.LEVERAGE)
    assert LOSS_MULT == pytest.approx(1 - spec.RISK_PCT)


@pytest.mark.parametrize("month", ["jan2026", "jun2026", "jul2026"])
def test_compounding_replays_by_hand(month):
    """Recompute the whole ledger independently; every step must agree."""
    s = load_month(month)
    r = VolExpansionModel(window=24).run_spec(s.closes, s.timestamps)
    cap = spec.INITIAL_CAPITAL
    for t in r.trades:
        cap *= WIN_MULT if t.win else LOSS_MULT
        assert cap == pytest.approx(t.capital_after, rel=1e-9)
    assert cap == pytest.approx(r.final_capital, rel=1e-9)


# ------------------------------------------------------ contract sizing ---

def test_kucoin_contract_sizing_is_hand_checked():
    ex = KucoinExecutor(equity=10_000, leverage=50, multiplier=0.001,
                        limits=RiskLimits(max_notional_per_leg=1e12))
    price = 60_000.0
    expected = int((10_000 * 50 / 2) / price / 0.001)      # 4166
    n = ex.leg_contracts(price)
    assert n == expected and isinstance(n, int)
    assert ex.contracts_notional(n, price) == pytest.approx(n * 0.001 * price)


def test_double_entry_bracket_is_mirrored():
    lv = KucoinExecutor().levels(60_000.0)
    assert lv["long_stop"] == pytest.approx(60_000 * (1 - spec.STOP_PCT))
    assert lv["long_target"] == pytest.approx(60_000 * (1 + spec.TP_PCT))
    assert lv["short_stop"] == pytest.approx(60_000 * (1 + spec.STOP_PCT))
    assert lv["short_target"] == pytest.approx(60_000 * (1 - spec.TP_PCT))
    # the two legs are exact mirrors around entry
    assert (lv["long_target"] - 60_000) == pytest.approx(60_000 - lv["short_target"])
    assert (lv["short_stop"] - 60_000) == pytest.approx(60_000 - lv["long_stop"])


# ------------------------------------------------------------ risk rails ---

SIG = {"price": 60_000.0, "bb_pct": 5.0, "hv_ratio": 0.4, "score": 92}


@pytest.mark.parametrize("limits,setup,fragment", [
    (RiskLimits(kill_switch=True), None, "kill switch"),
    (RiskLimits(max_concurrent_squeezes=1), "twice", "max concurrent"),
    (RiskLimits(max_daily_loss_pct=10), "loss", "daily loss"),
    (RiskLimits(min_free_balance=50_000), None, "balance below minimum"),
])
def test_each_risk_rail_blocks_independently(limits, setup, fragment):
    ex = KucoinExecutor(equity=10_000, limits=limits)
    if setup == "twice":
        ex.execute_squeeze(SIG)
    if setup == "loss":
        ex.state.equity = 8_000
    assert ex.execute_squeeze(SIG) is None
    assert fragment in ex.state.last_rejection


# ---------------------------------------------------------- risk sizing ---

def test_risk_sizing_formula():
    p = DEFAULT_SIZER.size(equity=10_000, entry_price=90_000, stop_pct=spec.STOP_PCT)
    assert p.risk_amount == pytest.approx(10_000 * spec.RISK_PCT)
    assert p.margin == pytest.approx(p.notional / spec.LEVERAGE)


def test_spec_parameters_are_internally_consistent():
    """RISK_PCT / STOP_PCT == LEVERAGE, so both constraints coincide."""
    assert spec.RISK_PCT / spec.STOP_PCT == pytest.approx(spec.LEVERAGE)
    assert spec.NET_EDGE_PCT == pytest.approx(spec.TP_PCT - spec.STOP_PCT)
