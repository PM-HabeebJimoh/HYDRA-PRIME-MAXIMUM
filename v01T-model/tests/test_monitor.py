"""Tests for the 24/7 monitor: cycles, ON/OFF alerts, position management."""

import asyncio

import pytest

from v01t import spec
from v01t.costs import ZERO_COSTS
from v01t.dataset import Series
from v01t.monitor import Monitor


def synthetic(closes):
    return Series(
        symbol="TEST", interval="1h",
        timestamps=[1767225600 + 3600 * i for i in range(len(closes))],
        closes=list(closes), origin="synthetic", source_url="test",
    )


# ------------------------------------------------------------------ cycles ---

def test_cycle_increments_counter():
    m = Monitor()
    assert m.state.cycles == 0
    m.cycle()
    m.cycle()
    assert m.state.cycles == 2


def test_cycle_records_timing():
    m = Monitor()
    m.cycle()
    assert m.state.last_cycle_at is not None
    assert m.state.last_cycle_duration_ms >= 0


def test_cycle_advances_through_the_series():
    m = Monitor()
    first = m._window_for(spec.SYMBOL)[1]
    second = m._window_for(spec.SYMBOL)[1]
    assert second == first + 1


def test_cursor_wraps_for_continuous_operation():
    """A 24/7 monitor must never run out of data and stall."""
    m = Monitor()
    series = m._default_series(spec.SYMBOL)
    m._cursor[spec.SYMBOL] = len(series.closes) + 5
    _, idx, _ = m._window_for(spec.SYMBOL)
    assert idx == spec.HV_MIN_CLOSES + 1


def test_many_cycles_never_raise():
    m = Monitor()
    for _ in range(200):
        m.cycle()
    assert m.state.errors == 0
    assert m.state.cycles == 200


# ------------------------------------------------------- opportunities ON/OFF ---

def test_monitor_raises_opportunities_and_trades_them():
    m = Monitor(costs=ZERO_COSTS)
    saw_open = False
    for _ in range(120):
        r = m.cycle()
        if r["opened"]:
            saw_open = True
            break
    assert saw_open, "monitor should open at least one position over the series"


def test_off_alert_fires_when_elite_lapses():
    m = Monitor(costs=ZERO_COSTS)
    saw_off = False
    for _ in range(200):
        r = m.cycle()
        if r["off"]:
            saw_off = True
            break
    assert saw_off, "monitor should emit an OFF alert when a squeeze releases"


def test_off_records_a_reason_and_timestamp():
    m = Monitor(costs=ZERO_COSTS)
    for _ in range(200):
        m.cycle()
        if m.state.off_opportunities:
            break
    assert m.state.off_opportunities
    off = m.state.off_opportunities[0]
    assert off.is_off is True
    assert off.off_reason and "elite requirement no longer met" in off.off_reason
    assert off.off_at is not None


def test_opportunity_id_is_stable_while_still_elite():
    m = Monitor(costs=ZERO_COSTS)
    ids = {}
    for _ in range(200):
        m.cycle()
        for inst, opp in m.state.opportunities.items():
            if inst in ids and opp.cycles_active > 1:
                assert opp.id == ids[inst], "ID must persist while the asset stays elite"
            ids[inst] = opp.id


def test_active_opportunities_satisfy_the_elite_filter():
    m = Monitor(costs=ZERO_COSTS)
    for _ in range(150):
        m.cycle()
        for opp in m.state.opportunities.values():
            assert opp.bb_pct < spec.BB_LOW or opp.bb_pct > spec.BB_HIGH
            assert opp.hv_ratio < spec.HV_MAX
            assert opp.score >= spec.SCORE_MIN


# ---------------------------------------------------------- position mgmt ---

def test_positions_are_opened_with_stops_and_targets():
    m = Monitor(costs=ZERO_COSTS)
    for _ in range(120):
        m.cycle()
        for p in m.state.open_positions.values():
            assert p.stop_price > 0 and p.target_price > 0
            assert p.units > 0 and p.notional > 0
            assert p.margin == pytest.approx(p.notional / spec.LEVERAGE, rel=1e-6)


def test_positions_eventually_close_into_history():
    m = Monitor(costs=ZERO_COSTS)
    for _ in range(200):
        m.cycle()
        if m.state.history:
            break
    assert m.state.history, "positions must be closed and recorded"
    t = m.state.history[0]
    assert t.exit_reason in {"stop_loss", "take_profit", "time_exit"}


def test_history_trades_have_full_cost_accounting():
    m = Monitor()
    for _ in range(250):
        m.cycle()
        if m.state.history:
            break
    assert m.state.history
    for t in m.state.history:
        assert t.net_pnl == pytest.approx(t.gross_pnl - t.fees - t.funding, rel=1e-9)
        assert t.fees > 0


def test_equity_and_drawdown_update_on_close():
    m = Monitor(costs=ZERO_COSTS)
    start = m.state.equity
    for _ in range(250):
        m.cycle()
        if m.state.history:
            break
    assert m.state.equity != start or not m.state.history
    assert m.state.max_drawdown_pct >= 0


def test_no_duplicate_position_per_instrument():
    m = Monitor(costs=ZERO_COSTS)
    for _ in range(250):
        m.cycle()
        instruments = [p.instrument for p in m.state.open_positions.values()]
        assert len(instruments) == len(set(instruments))


def test_equity_never_negative():
    m = Monitor()
    for _ in range(400):
        m.cycle()
        assert m.state.equity >= 0


def test_history_is_capped():
    m = Monitor(costs=ZERO_COSTS, max_history=5)
    for _ in range(600):
        m.cycle()
    assert len(m.state.history) <= 5


# ----------------------------------------------------------------- snapshot ---

def test_snapshot_shape():
    m = Monitor()
    for _ in range(50):
        m.cycle()
    snap = m.state.snapshot()
    for key in (
        "running", "cycles", "equity", "open_positions", "active_opportunities",
        "off_opportunities", "closed_trades", "win_rate_pct", "realised_pnl",
    ):
        assert key in snap


def test_snapshot_serialises():
    import json
    m = Monitor()
    m.cycle()
    assert json.dumps(m.state.snapshot(), default=str)


# ------------------------------------------------------------- async 24/7 ---

def test_monitor_runs_continuously_in_the_background():
    async def scenario():
        m = Monitor(interval_seconds=0.02, costs=ZERO_COSTS)
        await m.start()
        assert m.state.running is True
        await asyncio.sleep(0.35)
        cycles = m.state.cycles
        await m.stop()
        return cycles, m.state.running, m.state.errors

    cycles, running, errors = asyncio.run(scenario())
    assert cycles >= 3, f"expected repeated cycles, got {cycles}"
    assert running is False
    assert errors == 0


def test_start_is_idempotent():
    async def scenario():
        m = Monitor(interval_seconds=0.05)
        await m.start()
        await m.start()
        await asyncio.sleep(0.1)
        await m.stop()
        return m.state.errors

    assert asyncio.run(scenario()) == 0


def test_loop_survives_a_failing_cycle():
    """24/7 means an exception must not kill the loop."""
    async def scenario():
        m = Monitor(interval_seconds=0.02)
        calls = {"n": 0}
        original = m.cycle

        def flaky():
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("boom")
            return original()

        m.cycle = flaky
        await m.start()
        await asyncio.sleep(0.2)
        await m.stop()
        return m.state.errors, calls["n"]

    errors, calls = asyncio.run(scenario())
    assert errors >= 1
    assert calls > 1, "loop must keep cycling after an error"
