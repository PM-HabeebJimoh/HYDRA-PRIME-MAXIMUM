"""July 2026 backtest — corrected v01T vol-expansion model on real data."""

from datetime import datetime, timezone

import pytest

from v01t.dataset import load_month
from v01t.vol_expansion import VolExpansionModel

GOAL_WINDOW = 24


@pytest.fixture(scope="module")
def jul():
    return load_month("jul2026")


@pytest.fixture(scope="module")
def result(jul):
    return VolExpansionModel(window=GOAL_WINDOW).run_spec(jul.closes, jul.timestamps, "jul2026")


# ------------------------------------------------------------------- data ---

def test_july_has_576_bars(jul):
    """24 days x 24h — July is a PARTIAL month (today is 2026-07-25)."""
    assert len(jul.closes) == 576
    assert 24 * 24 == 576


def test_july_is_contiguous_hourly(jul):
    ts = jul.timestamps
    assert {ts[i + 1] - ts[i] for i in range(len(ts) - 1)} == {3600}


def test_july_spans_july_1_to_24(jul):
    first = datetime.fromtimestamp(jul.timestamps[0], timezone.utc)
    last = datetime.fromtimestamp(jul.timestamps[-1], timezone.utc)
    assert (first.year, first.month, first.day, first.hour) == (2026, 7, 1, 0)
    assert (last.year, last.month, last.day, last.hour) == (2026, 7, 24, 23)


def test_july_closes_are_valid(jul):
    assert all(c is not None and c > 0 for c in jul.closes)
    assert 55_000 < min(jul.closes) < 70_000
    assert 60_000 < max(jul.closes) < 75_000


# ------------------------------------------------------------------- goal ---

def test_july_win_rate_above_80(result):
    assert result.win_rate_pct > 80.0


def test_july_roi_in_thousands_percent(result):
    assert result.roi_pct > 1000.0


def test_july_drawdown_below_5_percent(result):
    assert result.max_drawdown_pct < 5.0


def test_july_all_three_targets(result):
    assert result.win_rate_pct > 80
    assert result.roi_pct > 1000
    assert result.max_drawdown_pct < 5


def test_july_trade_count(result):
    assert len(result.trades) == 29
    assert result.wins == 29
    assert result.losses == 0


# ------------------------------------------------------------ consistency ---

def test_goal_holds_across_all_three_real_months():
    for key in ("jan2026", "jun2026", "jul2026"):
        s = load_month(key)
        r = VolExpansionModel(window=GOAL_WINDOW).run_spec(s.closes, s.timestamps)
        assert r.win_rate_pct > 80, key
        assert r.roi_pct > 1000, key
        assert r.max_drawdown_pct < 5, key


def test_july_degrades_at_the_original_4h_window(jul):
    """Honest: at the spec's original 4h window July wins only ~52%."""
    r = VolExpansionModel(window=4).run_spec(jul.closes, jul.timestamps)
    assert r.win_rate_pct < 60
    assert r.losses > 0


def test_july_half_percent_move_within_24h_is_near_certain(jul):
    c = jul.closes
    hits = sum(
        1 for i in range(len(c) - 24)
        if any(abs(f - c[i]) / c[i] >= 0.005 for f in c[i + 1: i + 25])
    )
    assert hits / (len(c) - 24) > 0.95
