"""Tests for the real execution engine: entries, stops, targets, costs, losses."""

import pytest

from v01t import spec
from v01t.costs import CostModel, DEFAULT_COSTS, ZERO_COSTS
from v01t.dataset import Series
from v01t.live_engine import (
    EXIT_STOP, EXIT_TARGET, EXIT_TIME, LONG, SHORT, ExecutionEngine,
)


@pytest.fixture(scope="module")
def real_run():
    return ExecutionEngine(costs=DEFAULT_COSTS).run()


def synthetic(closes, start_ts=1767225600):
    return Series(
        symbol="TEST", interval="1h",
        timestamps=[start_ts + 3600 * i for i in range(len(closes))],
        closes=list(closes), origin="synthetic", source_url="test",
    )


# ------------------------------------------------------------------ costs ---

def test_entry_fill_is_adverse_for_longs():
    c = CostModel(spread_bps=1, slippage_bps=0.5, taker_fee_bps=0)
    assert c.entry_price(100.0, LONG) > 100.0


def test_entry_fill_is_adverse_for_shorts():
    c = CostModel(spread_bps=1, slippage_bps=0.5, taker_fee_bps=0)
    assert c.entry_price(100.0, SHORT) < 100.0


def test_exit_fill_is_adverse_in_the_opposite_direction():
    c = CostModel(spread_bps=1, slippage_bps=0.5)
    assert c.exit_price(100.0, LONG) < 100.0
    assert c.exit_price(100.0, SHORT) > 100.0


def test_fees_scale_with_notional():
    c = CostModel(taker_fee_bps=4)
    assert c.fee(1_000_000) == pytest.approx(400.0)


def test_funding_scales_with_time():
    c = CostModel(funding_bps_8h=1)
    assert c.funding(1_000_000, 8) == pytest.approx(100.0)
    assert c.funding(1_000_000, 4) == pytest.approx(50.0)


def test_leverage_amplifies_cost_against_equity():
    c = DEFAULT_COSTS
    assert c.round_trip_cost_pct_of_equity(50) == pytest.approx(
        c.round_trip_cost_pct_of_notional() * 50
    )


def test_breakeven_move_exceeds_the_stop_distance():
    """The decisive fact: costs are larger than the 0.05% stop."""
    assert DEFAULT_COSTS.breakeven_move_pct() > spec.STOP_PCT


def test_zero_cost_model_is_frictionless():
    assert ZERO_COSTS.entry_price(100.0, LONG) == 100.0
    assert ZERO_COSTS.fee(1_000_000) == 0.0
    assert ZERO_COSTS.round_trip_cost_pct_of_notional() == 0.0


# ------------------------------------------------------------- direction ---

def test_low_band_squeeze_goes_long():
    assert ExecutionEngine.direction_for(5.0) == LONG


def test_high_band_squeeze_goes_short():
    assert ExecutionEngine.direction_for(95.0) == SHORT


# ------------------------------------------------------------ exit levels ---

def test_long_stop_below_and_target_above():
    e = ExecutionEngine()
    stop, target = e._levels(100.0, LONG)
    assert stop < 100.0 < target
    assert stop == pytest.approx(100.0 * (1 - spec.STOP_PCT))
    assert target == pytest.approx(100.0 * (1 + spec.TP_PCT))


def test_short_stop_above_and_target_below():
    e = ExecutionEngine()
    stop, target = e._levels(100.0, SHORT)
    assert target < 100.0 < stop


def test_stop_is_checked_before_target():
    """Conservative: if a bar could have hit both, the stop wins."""
    e = ExecutionEngine()
    assert e._check_exit(89.0, LONG, stop_price=90.0, target_price=88.0) == EXIT_STOP


def test_no_exit_inside_the_band():
    e = ExecutionEngine()
    assert e._check_exit(100.0, LONG, 99.0, 101.0) is None


# ------------------------------------------------- deterministic scenarios ---

def _squeeze_prefix():
    """A series that genuinely triggers the elite filter.

    25 alternating +/-2% bars build a wide Bollinger band and a high long-window
    volatility, then five decreasing steps drift price down to the lower band
    while short-window volatility collapses. That gives BB% below 10 and an HV
    ratio below 0.8 — a real low-band squeeze, so direction is LONG.
    """
    # 35 alternating bars, so the squeeze lands past HV_MIN_CLOSES and is scanned
    base = [100.0]
    for i in range(34):
        base.append(base[-1] * (1 + (0.02 if i % 2 else -0.02)))
    target = base[-1] * 0.95
    closes = list(base)
    for _ in range(5):
        closes.append(closes[-1] + (target - closes[-1]) * 0.5)
    return closes


def test_squeeze_prefix_actually_triggers_the_filter():
    """Guard: the fixture must be a real elite squeeze, or the scenarios are vacuous."""
    from v01t.indicators import compute_bb_percentile, compute_hv_ratio, is_elite
    closes = _squeeze_prefix()
    bb, hv = compute_bb_percentile(closes), compute_hv_ratio(closes)
    assert is_elite(bb, hv), f"fixture not elite: bb={bb} hv={hv}"
    assert bb < spec.BB_LOW
    assert ExecutionEngine.direction_for(bb) == LONG


def _forced_squeeze_series(tail_multipliers):
    """A genuine low-band squeeze (-> LONG), followed by tail prices expressed
    as multipliers of the squeeze close."""
    pre = _squeeze_prefix()
    last = pre[-1]
    return synthetic(pre + [last * m for m in tail_multipliers])


def test_engine_records_a_stop_loss():
    e = ExecutionEngine(costs=ZERO_COSTS, stop_pct=0.01, tp_pct=0.05, max_hold_bars=4)
    r = e.run(_forced_squeeze_series([0.97] * 4))
    assert r.trades
    assert r.trades[0].exit_reason == EXIT_STOP
    assert r.trades[0].net_pnl < 0


def test_engine_records_a_take_profit():
    e = ExecutionEngine(costs=ZERO_COSTS, stop_pct=0.05, tp_pct=0.01, max_hold_bars=4)
    r = e.run(_forced_squeeze_series([1.03] * 4))
    assert r.trades
    assert r.trades[0].exit_reason == EXIT_TARGET
    assert r.trades[0].net_pnl > 0


def test_engine_records_a_time_exit():
    e = ExecutionEngine(costs=ZERO_COSTS, stop_pct=0.5, tp_pct=0.5, max_hold_bars=2)
    r = e.run(_forced_squeeze_series([1.0005] * 4))
    assert r.trades
    assert r.trades[0].exit_reason == EXIT_TIME
    assert r.trades[0].bars_held == 2


def test_costs_reduce_pnl_versus_frictionless():
    series = _forced_squeeze_series([1.03] * 4)
    free = ExecutionEngine(costs=ZERO_COSTS, stop_pct=0.05, tp_pct=0.01).run(series)
    paid = ExecutionEngine(costs=DEFAULT_COSTS, stop_pct=0.05, tp_pct=0.01).run(series)
    assert paid.trades[0].net_pnl < free.trades[0].net_pnl
    assert paid.trades[0].fees > 0


# --------------------------------------------------- run on the real series ---

def test_engine_executes_trades_on_real_data(real_run):
    assert len(real_run.trades) > 0
    assert real_run.signals_detected > 0


def test_engine_produces_real_losses(real_run):
    """The decisive difference from the spec ledger: losses exist."""
    assert real_run.losses > 0
    assert real_run.win_rate_pct < 100.0


def test_engine_drawdown_is_real(real_run):
    assert real_run.max_drawdown_pct > 0.0


def test_engine_win_rate_misses_the_80_percent_target(real_run):
    """Measured, not assumed."""
    assert real_run.win_rate_pct < spec.TARGET_WR_PCT


def test_engine_drawdown_breaches_the_5_percent_target(real_run):
    assert real_run.max_drawdown_pct > spec.TARGET_MAX_DD_PCT


def test_engine_charges_fees_and_funding(real_run):
    assert real_run.total_fees > 0
    assert real_run.total_funding > 0


def test_every_trade_has_a_stop_and_a_target(real_run):
    for t in real_run.trades:
        assert t.stop_price > 0 and t.target_price > 0
        if t.direction == LONG:
            assert t.stop_price < t.entry_fill < t.target_price
        else:
            assert t.target_price < t.entry_fill < t.stop_price


def test_every_trade_is_sized_and_leveraged(real_run):
    for t in real_run.trades:
        assert t.units > 0
        assert t.notional == pytest.approx(t.units * t.entry_fill, rel=1e-9)
        assert t.margin == pytest.approx(t.notional / spec.LEVERAGE, rel=1e-6)


def test_net_pnl_is_gross_minus_costs(real_run):
    for t in real_run.trades:
        assert t.net_pnl == pytest.approx(t.gross_pnl - t.fees - t.funding, rel=1e-9)


def test_equity_chain_is_consistent(real_run):
    for t in real_run.trades:
        assert t.equity_after == pytest.approx(max(0.0, t.equity_before + t.net_pnl), rel=1e-9)


def test_exit_reasons_are_valid(real_run):
    for t in real_run.trades:
        assert t.exit_reason in {EXIT_STOP, EXIT_TARGET, EXIT_TIME, "end_of_data"}


def test_trades_do_not_overlap_by_default(real_run):
    for a, b in zip(real_run.trades, real_run.trades[1:]):
        assert b.entry_index > a.exit_index


def test_equity_never_goes_negative(real_run):
    assert real_run.final_equity >= 0
    assert all(e >= 0 for e in real_run.equity_curve)


def test_engine_is_deterministic():
    a = ExecutionEngine(costs=DEFAULT_COSTS).run()
    b = ExecutionEngine(costs=DEFAULT_COSTS).run()
    assert a.final_equity == b.final_equity
    assert len(a.trades) == len(b.trades)


def test_engine_summary_serialises(real_run):
    import json
    assert "win_rate_pct" in json.dumps(real_run.summary(), default=str)
