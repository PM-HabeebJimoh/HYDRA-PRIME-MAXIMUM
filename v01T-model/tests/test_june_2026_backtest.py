"""Regression tests for the real June 2026 backtest."""

import pytest

from v01t import spec
from v01t.dataset import load_month
from v01t.engine import V01TBacktestEngine


@pytest.fixture(scope="module")
def series():
    return load_month("jun2026")


@pytest.fixture(scope="module")
def result(series):
    return V01TBacktestEngine().run(series, label="June 2026")


# ------------------------------------------------------------------- data ---

def test_june_has_720_bars(series):
    """30 days x 24h."""
    assert len(series.closes) == 720
    assert 30 * 24 == 720


def test_june_is_contiguous_hourly(series):
    ts = series.timestamps
    assert {ts[i + 1] - ts[i] for i in range(len(ts) - 1)} == {3600}


def test_june_covers_the_month(series):
    from datetime import datetime, timezone
    first = datetime.fromtimestamp(series.timestamps[0], timezone.utc)
    last = datetime.fromtimestamp(series.timestamps[-1], timezone.utc)
    assert (first.month, first.day, first.hour) == (6, 1, 0)
    assert (last.month, last.day, last.hour) == (6, 30, 23)


def test_june_no_nulls(series):
    assert all(c is not None and c > 0 for c in series.closes)


def test_june_endpoints(series):
    assert series.closes[0] == pytest.approx(73781.0703125)
    assert series.closes[-1] == pytest.approx(58523.9296875)


# ---------------------------------------------------------------- engine ---

def test_engine_produced_trades(result):
    assert result.trades == 27
    assert result.wins + result.losses == result.trades


def test_engine_records_real_losses(result):
    """The real engine must be capable of losing — unlike the spec ledger."""
    assert result.losses > 0
    assert result.losses == 19
    assert any(t.net_pnl < 0 for t in result.trade_list)


def test_stop_losses_actually_fire(result):
    assert result.outcomes.get("stop_loss", 0) == 18


def test_all_exit_types_are_valid(result):
    assert set(result.outcomes) <= {"stop_loss", "take_profit", "timeout"}


def test_measured_win_rate(result):
    assert result.win_rate_pct == pytest.approx(29.63, abs=0.01)


def test_measured_drawdown(result):
    assert result.max_drawdown_pct == pytest.approx(45.75, abs=0.01)


def test_measured_roi(result):
    assert result.roi_pct == pytest.approx(-33.17, abs=0.01)


def test_final_capital(result):
    assert result.final_capital == pytest.approx(6683.20, abs=0.5)


def test_goals_fail_on_real_june_data(result):
    """Documents the honest outcome: the published targets are not met."""
    assert result.goals["win_rate"]["passed"] is False
    assert result.goals["max_drawdown"]["passed"] is False
    assert result.goals["roi"]["passed"] is False
    assert result.goal_achieved is False


# ------------------------------------------------------------ mechanics ---

def test_direction_matches_band_side(result):
    for t in result.trade_list:
        if t.direction == "long":
            assert t.bb_pct < spec.BB_LOW
        else:
            assert t.bb_pct > spec.BB_HIGH


def test_every_trade_passed_the_elite_filter(result):
    for t in result.trade_list:
        assert t.bb_pct < spec.BB_LOW or t.bb_pct > spec.BB_HIGH
        assert t.hv_ratio < spec.HV_MAX
        assert t.score >= spec.SCORE_MIN


def test_hold_time_respects_the_cap(result):
    for t in result.trade_list:
        assert 1 <= t.bars_held <= 4


def test_no_overlapping_positions(result):
    for a, b in zip(result.trade_list, result.trade_list[1:]):
        assert b.entry_index > a.exit_index


def test_fees_are_charged(result):
    assert result.total_fees > 0
    for t in result.trade_list:
        assert t.fees > 0
        assert t.net_pnl == pytest.approx(t.gross_pnl - t.fees, abs=1e-6)


def test_equity_chain_is_consistent(result):
    equity = result.initial_capital
    for t in result.trade_list:
        assert t.equity_before == pytest.approx(equity, abs=1e-6)
        equity = t.equity_after
    assert equity == pytest.approx(result.final_capital, abs=0.01)


def test_position_sizing_respects_leverage_cap(result):
    for t in result.trade_list:
        assert t.notional <= t.equity_before * spec.LEVERAGE + 1e-6


def test_position_sizing_is_risk_based():
    """Notional = risk capital / stop distance, capped at leverage x equity."""
    eng = V01TBacktestEngine(leverage=1000)  # raise the cap so risk sizing binds
    qty, notional = eng.position_size(10_000.0, 50_000.0)
    expected_qty = (10_000.0 * spec.RISK_PCT) / (50_000.0 * spec.STOP_PCT)
    assert qty == pytest.approx(expected_qty)
    assert notional == pytest.approx(expected_qty * 50_000.0)


def test_leverage_cap_binds_at_default():
    eng = V01TBacktestEngine()
    _, notional = eng.position_size(10_000.0, 50_000.0)
    assert notional == pytest.approx(10_000.0 * spec.LEVERAGE)


# ----------------------------------------------------------- comparison ---

def test_costs_are_the_dominant_drag(series):
    """Removing fees and slippage flips the month from negative to positive."""
    with_costs = V01TBacktestEngine().run(series)
    without = V01TBacktestEngine(fee_pct=0.0, slippage_pct=0.0).run(series)
    assert with_costs.roi_pct < 0 < without.roi_pct


def test_engine_is_deterministic(series):
    a = V01TBacktestEngine().run(series)
    b = V01TBacktestEngine().run(series)
    assert a.final_capital == b.final_capital
    assert a.trades == b.trades
    assert a.win_rate_pct == b.win_rate_pct


def test_january_still_works_with_the_real_engine():
    """The engine is month-agnostic."""
    jan = load_month("jan2026")
    r = V01TBacktestEngine().run(jan)
    assert r.bars == 744
    assert r.trades > 0
    assert r.wins + r.losses == r.trades
