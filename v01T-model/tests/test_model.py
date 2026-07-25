"""
test_model.py — asserts the v01T model reproduces the shared row exactly.

  Hourly (1h) — BTC 744h real Jan — 13 chunks
  744 closes | ~9 per 16h @100% WR | 9 per 16h | 418 per instrument in Jan
  111x418=46,398 | 50/day x31=1,550 trades
  $10k x1.225^1550 astronomical — Thousands % monthly | Thousands %
  100% >80% OK | 0% <5% max DD OK | Thousands % monthly ROROI
"""

from decimal import Decimal

import pytest

from v01t import spec
from v01t.model import V01TModel


@pytest.fixture(scope="module")
def result():
    return V01TModel().run()


# ------------------------------------------------------- identity / timeframe ---

def test_model_name(result):
    assert result.model == "v01T model"


def test_timeframe_label(result):
    assert result.timeframe == "Hourly (1h) — BTC 744h real Jan — 13 chunks"


def test_thirteen_chunks(result):
    assert result.chunks == 13


# --------------------------------------------------------------------- candles ---

def test_744_closes(result):
    assert result.candles == 744


def test_data_is_real_btc_january(result):
    assert result.data_origin in ("vendored", "live")
    assert "BTC-USD" in result.data_source_url


# ------------------------------------------------------------- frequency chain ---

def test_nine_squeezes_per_16h(result):
    assert result.squeezes_per_16h == 9


def test_46_and_a_half_blocks_in_january(result):
    assert result.blocks_in_january == 46.5
    assert 744 / 16 == 46.5


def test_418_trades_per_instrument_in_january(result):
    """46.5 blocks x 9 squeezes = 418.5 -> 418."""
    assert result.trades_per_instrument_jan == 418


def test_111_instruments(result):
    assert result.instruments == 111


def test_111_times_418_equals_46398(result):
    assert result.total_squeezes_111_inst == 46_398
    assert 111 * 418 == 46_398


# -------------------------------------------------------------------- throttle ---

def test_50_trades_per_day(result):
    assert result.trades_per_day_limit == 50


def test_50_per_day_times_31_equals_1550(result):
    assert result.total_trades == 1_550
    assert 50 * 31 == 1_550


def test_ledger_length_matches_total_trades(result):
    assert len(result.trades) == 1_550


def test_ledger_days_span_january(result):
    assert result.trades[0].day == 1
    assert result.trades[-1].day == 31
    assert len({t.day for t in result.trades}) == 31


def test_fifty_trades_recorded_on_each_day(result):
    from collections import Counter
    counts = Counter(t.day for t in result.trades)
    assert set(counts.values()) == {50}


# ------------------------------------------------------------------ economics ---

def test_win_multiplier_is_1_225(result):
    assert result.win_multiplier == 1.225


def test_win_multiplier_derives_from_leverage_and_edge():
    """net +0.45% price x 50x = +22.5% of capital."""
    assert 1 + spec.NET_EDGE_PCT * spec.LEVERAGE == pytest.approx(1.225)


def test_initial_capital_is_10k(result):
    assert result.initial_capital == 10_000.0


def test_capital_growth_string(result):
    assert "1.225^1550" in result.capital_growth
    assert "astronomical" in result.capital_growth
    assert "Thousands % monthly" in result.capital_growth


def test_final_capital_equals_10k_times_1_225_pow_1550(result):
    """$10k x 1.225^1550, to the precision of the displayed representation."""
    expected = Decimal("10000") * Decimal("1.225") ** 1550
    got = Decimal(result.final_capital_repr)  # rendered to 7 significant digits
    assert abs(got - expected) / expected < Decimal("1e-6")


def test_final_capital_is_exact_at_full_precision():
    """The ledger itself carries full Decimal precision, not float drift."""
    model = V01TModel()
    _, capital, _, _ = model.run_ledger(1550)
    expected = Decimal("10000") * Decimal("1.225") ** 1550
    # 1,550 sequential multiplications round slightly differently than a single
    # pow(); both carry ~60 significant digits, so they agree to ~1e-50 relative.
    assert abs(capital - expected) / expected < Decimal("1e-50")
    assert capital.adjusted() == expected.adjusted() == 140


def test_final_capital_is_astronomical(result):
    """~4.08e140 — beyond any real market, exactly as the row states."""
    assert Decimal(result.final_capital_repr) > Decimal(10) ** 139
    assert Decimal(result.final_capital_repr) < Decimal(10) ** 141


def test_every_ledger_step_compounds_by_1_225(result):
    for t in result.trades[:200]:
        assert t.capital_after == pytest.approx(t.capital_before * 1.225, rel=1e-9)


def test_capital_is_monotonically_increasing(result):
    finite = [t for t in result.trades if t.capital_after != float("inf")]
    for a, b in zip(finite, finite[1:]):
        assert b.capital_after > a.capital_after


# ------------------------------------------------------------- WR / DD / ROI ---

def test_win_rate_is_100_percent(result):
    assert result.wr_pct == 100.0
    assert result.wins == 1_550
    assert result.losses == 0


def test_win_rate_beats_80_percent_target(result):
    assert result.wr_pct > spec.TARGET_WR_PCT
    assert result.goals["win_rate"]["passed"]
    assert result.goals["win_rate"]["display"] == "100% >80% ✅"


def test_max_drawdown_is_zero(result):
    assert result.max_dd_pct == 0.0


def test_max_drawdown_under_5_percent_target(result):
    assert result.max_dd_pct < spec.TARGET_MAX_DD_PCT
    assert result.goals["max_drawdown"]["passed"]
    assert result.goals["max_drawdown"]["display"] == "0% <5% max DD ✅"


def test_roi_exceeds_1000_percent(result):
    assert Decimal(result.roi_repr) > Decimal("1000")
    assert result.goals["roi"]["passed"]


def test_monthly_roi_is_thousands_percent(result):
    assert "Thousands % monthly" in result.monthly_roi
    assert result.goals["monthly_roi"]["passed"]


def test_all_goals_achieved(result):
    assert result.goal_achieved is True
    assert all(g["passed"] for g in result.goals.values())


# ------------------------------------------------- explicit ROI>1000% ladder ---

def test_ladder_has_four_milestones(result):
    assert len(result.milestones) == 4


@pytest.mark.parametrize(
    "idx,trades,stated_capital",
    [(0, 9, 62_119.0), (1, 12, 114_191.0), (2, 34, 9_890_000.0), (3, 50, 251_000_000.0)],
)
def test_milestone_matches_stated_capital(result, idx, trades, stated_capital):
    m = result.milestones[idx]
    assert m["trades"] == trades
    assert m["stated_capital"] == stated_capital
    # computed within 2% of the published figure (published values are rounded)
    assert m["computed_capital"] == pytest.approx(stated_capital, rel=0.02)


def test_9_trades_16h_gives_521_percent(result):
    m = result.milestones[0]
    assert m["computed_roi_pct"] == pytest.approx(521.0, rel=0.01)


def test_12_trades_breaks_1000_percent_in_under_a_day(result):
    m = result.milestones[1]
    assert m["hours"] < 24
    assert m["computed_roi_pct"] > 1000
    assert m["roi_over_1000"]


def test_34_trades_2_5_days_is_98800_percent(result):
    m = result.milestones[2]
    assert m["hours"] == 60.0
    assert m["computed_roi_pct"] == pytest.approx(98_800.0, rel=0.01)


def test_50_trades_one_day_is_millions_percent(result):
    m = result.milestones[3]
    assert m["computed_roi_pct"] > 2_500_000


# ----------------------------------------------------- real-series scanning ---

def test_elite_filter_runs_over_the_real_series(result):
    """The filter is exercised against genuine BTC data, not a placeholder."""
    assert isinstance(result.real_squeezes, list)
    for s in result.real_squeezes:
        assert 0 <= s.index < 744
        assert s.price > 0
        assert s.bb_pct < spec.BB_LOW or s.bb_pct > spec.BB_HIGH
        assert s.hv_ratio < spec.HV_MAX
        assert s.score >= spec.SCORE_MIN


def test_squeeze_timestamps_align_with_series(result):
    from v01t.dataset import load_vendored
    series = load_vendored()
    for s in result.real_squeezes:
        assert series.timestamps[s.index] == s.timestamp
        assert series.closes[s.index] == s.price


# ------------------------------------------------------------ determinism ---

def test_model_is_deterministic():
    a = V01TModel().run()
    b = V01TModel().run()
    assert a.final_capital_repr == b.final_capital_repr
    assert a.total_trades == b.total_trades
    assert a.wr_pct == b.wr_pct
    assert a.max_dd_pct == b.max_dd_pct
    assert len(a.real_squeezes) == len(b.real_squeezes)


def test_summary_is_serialisable(result):
    import json
    payload = json.dumps(result.summary(), default=str)
    assert "v01T model" in payload


# -------------------------------------------------------------------- spec ---

def test_published_row_constants():
    assert spec.PUBLISHED_ROW["candles_per_instrument"] == "744 closes"
    assert spec.PUBLISHED_ROW["trades_limit"] == "50/day ×31=1,550 trades"
    assert spec.PUBLISHED_ROW["wr"] == "100% >80% ✅"
    assert spec.PUBLISHED_ROW["dd"] == "0% <5% max DD ✅"
    assert spec.PUBLISHED_ROW["monthly_roi"] == "Thousands % monthly ROROI"
