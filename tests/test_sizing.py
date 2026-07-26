"""Tests for lot-size / position-size calculation."""

import pytest

from v01t import spec
from v01t.sizing import Sizer, DEFAULT_SIZER


def test_risk_based_size_risks_exactly_the_budget():
    """Losing the stop distance must cost exactly risk_pct of equity."""
    s = Sizer(risk_pct=0.025, leverage=10_000, lot_step=0)  # leverage effectively unbound
    pos = s.size(equity=10_000, entry_price=90_000, stop_pct=0.01)
    assert pos.risk_amount == pytest.approx(250.0)
    assert pos.risk_pct_of_equity == pytest.approx(0.025)
    assert pos.capped_by == "risk"


def test_units_formula():
    s = Sizer(risk_pct=0.02, leverage=10_000, lot_step=0)
    pos = s.size(equity=50_000, entry_price=100.0, stop_pct=0.05)
    # (50000*0.02) / (100*0.05) = 1000/5 = 200 units
    assert pos.units == pytest.approx(200.0)


def test_spec_parameters_sit_exactly_on_the_leverage_boundary():
    """RISK_PCT / STOP_PCT = 0.025 / 0.0005 = 50 = LEVERAGE.

    The spec's risk budget and stop distance imply precisely 50x, so at the
    spec parameters the risk-based size and the leverage cap coincide. Risk is
    reported as the binding constraint because it is evaluated first.
    """
    assert spec.RISK_PCT / spec.STOP_PCT == pytest.approx(spec.LEVERAGE)
    pos = DEFAULT_SIZER.size(equity=10_000, entry_price=90_000, stop_pct=spec.STOP_PCT)
    assert pos.capped_by == "risk"
    assert pos.notional == pytest.approx(10_000 * spec.LEVERAGE, rel=1e-5)
    assert pos.effective_leverage == pytest.approx(spec.LEVERAGE, rel=1e-5)
    assert pos.risk_pct_of_equity == pytest.approx(spec.RISK_PCT, rel=1e-5)


def test_leverage_cap_binds_when_the_stop_is_tighter_than_the_spec():
    """A stop tighter than RISK_PCT/LEVERAGE forces the leverage cap to clamp."""
    pos = DEFAULT_SIZER.size(equity=10_000, entry_price=90_000, stop_pct=0.0001)
    assert pos.capped_by == "leverage"
    assert pos.effective_leverage == pytest.approx(spec.LEVERAGE, rel=1e-5)
    # clamped below the requested risk budget
    assert pos.risk_pct_of_equity < DEFAULT_SIZER.risk_pct


def test_margin_is_notional_over_leverage():
    pos = DEFAULT_SIZER.size(equity=10_000, entry_price=90_000)
    assert pos.margin == pytest.approx(pos.notional / spec.LEVERAGE)


def test_stop_distance_is_price_times_stop_pct():
    pos = DEFAULT_SIZER.size(equity=10_000, entry_price=90_000, stop_pct=0.0005)
    assert pos.stop_distance == pytest.approx(45.0)


def test_zero_or_negative_equity_yields_no_position():
    assert not DEFAULT_SIZER.size(0, 90_000).is_open
    assert not DEFAULT_SIZER.size(-5, 90_000).is_open


def test_zero_price_yields_no_position():
    assert not DEFAULT_SIZER.size(10_000, 0).is_open


def test_dust_equity_below_min_lot_yields_no_position():
    s = Sizer(min_lot=1.0, lot_step=1.0)
    pos = s.size(equity=0.01, entry_price=90_000)
    assert not pos.is_open
    assert pos.capped_by == "min_lot"


def test_lot_step_floors_the_size():
    s = Sizer(lot_step=0.1, min_lot=0.1, leverage=10_000)
    pos = s.size(equity=10_000, entry_price=100.0, stop_pct=0.0333)
    assert abs(pos.units / 0.1 - round(pos.units / 0.1)) < 1e-9


def test_size_scales_linearly_with_equity():
    a = DEFAULT_SIZER.size(10_000, 90_000)
    b = DEFAULT_SIZER.size(20_000, 90_000)
    assert b.units == pytest.approx(a.units * 2, rel=1e-6)


def test_max_margin_pct_limits_notional():
    s = Sizer(max_margin_pct=0.5)
    pos = s.size(10_000, 90_000, spec.STOP_PCT)
    assert pos.notional == pytest.approx(10_000 * spec.LEVERAGE * 0.5, rel=1e-6)
