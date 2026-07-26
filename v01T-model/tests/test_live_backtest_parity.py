"""The live monitor must reproduce the backtest EXACTLY, trade for trade.

The backtested model is the specification. The 24/7 runner is only correct if,
fed the same bars one at a time as if live, it produces an identical ledger.
"""

import pytest

from v01t.dataset import load_month
from v01t.ve_monitor import VolExpansionMonitor
from v01t.vol_expansion import VolExpansionModel

MONTHS = ["jan2026", "jun2026", "jul2026"]
WINDOW = 24


def _live(month, window=WINDOW, non_overlapping=False):
    """Stream a month bar-by-bar through the live monitor, exactly one pass."""
    s = load_month(month)
    m = VolExpansionMonitor(window=window, month=month, non_overlapping=non_overlapping)
    for _ in range(len(s.closes) - 30):
        m.cycle()
    return m


def _backtest(month, window=WINDOW, non_overlapping=False):
    s = load_month(month)
    return VolExpansionModel(window=window, non_overlapping=non_overlapping).run_spec(
        s.closes, s.timestamps
    )


@pytest.mark.parametrize("month", MONTHS)
def test_live_trade_count_matches_backtest(month):
    assert len(_live(month).state.history) == len(_backtest(month).trades)


@pytest.mark.parametrize("month", MONTHS)
def test_live_win_rate_matches_backtest(month):
    m, b = _live(month), _backtest(month)
    h = m.state.history
    wr = sum(1 for t in h if t.win) / len(h) * 100
    assert wr == pytest.approx(b.win_rate_pct, abs=1e-9)


@pytest.mark.parametrize("month", MONTHS)
def test_live_roi_matches_backtest(month):
    m, b = _live(month), _backtest(month)
    roi = (m.state.capital - 10_000) / 10_000 * 100
    assert roi == pytest.approx(b.roi_pct, rel=1e-6)


@pytest.mark.parametrize("month", MONTHS)
def test_live_final_capital_matches_backtest(month):
    m, b = _live(month), _backtest(month)
    assert m.state.capital == pytest.approx(b.final_capital, rel=1e-6)


@pytest.mark.parametrize("month", MONTHS)
def test_live_drawdown_matches_backtest(month):
    m, b = _live(month), _backtest(month)
    assert m.state.max_drawdown_pct == pytest.approx(b.max_drawdown_pct, abs=1e-9)


@pytest.mark.parametrize("month", MONTHS)
def test_live_outcome_mix_matches_backtest(month):
    """Not just the count — the same number of wins and losses."""
    m, b = _live(month), _backtest(month)
    assert sum(t.win for t in m.state.history) == b.wins
    assert sum(not t.win for t in m.state.history) == b.losses


@pytest.mark.parametrize("month", MONTHS)
def test_live_takes_exactly_the_same_entries(month):
    """Identical entry prices. Live history is ordered by RESOLUTION time
    (windows overlap and settle out of order), so compare as multisets."""
    m, b = _live(month), _backtest(month)
    assert sorted(t.entry_price for t in m.state.history) == pytest.approx(
        sorted(t.entry_price for t in b.trades)
    )


@pytest.mark.parametrize("month", MONTHS)
def test_live_resolves_every_window(month):
    """Nothing may be left hanging: every opened window must settle."""
    assert len(_live(month).state.pending) == 0


@pytest.mark.parametrize("month", MONTHS)
def test_live_meets_the_goal(month):
    m = _live(month)
    h = m.state.history
    wr = sum(1 for t in h if t.win) / len(h) * 100
    roi = (m.state.capital - 10_000) / 10_000 * 100
    assert wr > 80
    assert roi > 1000
    assert m.state.max_drawdown_pct < 5


def test_live_opens_on_every_elite_bar_not_once_per_streak():
    """Regression: the runner previously opened only the first bar of a streak,
    which under-traded the backtest (21 vs 30 in January)."""
    m, b = _live("jan2026"), _backtest("jan2026")
    assert len(m.state.history) == len(b.trades) == 30


def test_live_uses_only_spec_multipliers():
    for t in _live("jul2026").state.history:
        assert t.multiplier in (1.225, 0.975)
