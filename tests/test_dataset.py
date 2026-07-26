"""Tests for the real January 2026 BTC hourly dataset."""

from datetime import datetime, timezone

import pytest

from v01t import spec
from v01t.dataset import load_vendored


@pytest.fixture(scope="module")
def series():
    return load_vendored()


def test_has_exactly_744_closes(series):
    """744h real Jan — the headline candle count."""
    assert len(series.closes) == 744
    assert len(series.closes) == spec.CANDLES


def test_744_equals_31_days_of_hours():
    assert spec.DAYS_IN_JANUARY * spec.HOURS_PER_DAY == 744


def test_symbol_and_interval(series):
    assert series.symbol == "BTC-USD"
    assert series.interval == "1h"


def test_no_null_or_nonpositive_closes(series):
    assert all(c is not None for c in series.closes)
    assert all(c > 0 for c in series.closes)


def test_timestamps_are_hourly_and_contiguous(series):
    ts = series.timestamps
    assert len(ts) == 744
    deltas = {ts[i + 1] - ts[i] for i in range(len(ts) - 1)}
    assert deltas == {3600}


def test_period_covers_january_2026_utc(series):
    first = datetime.fromtimestamp(series.timestamps[0], timezone.utc)
    last = datetime.fromtimestamp(series.timestamps[-1], timezone.utc)
    assert (first.year, first.month, first.day, first.hour) == (2026, 1, 1, 0)
    assert (last.year, last.month, last.day, last.hour) == (2026, 1, 31, 23)


def test_source_is_yahoo_chart_v8(series):
    assert "query1.finance.yahoo.com/v8/finance/chart/BTC-USD" in series.source_url
    assert "interval=1h" in series.source_url


def test_first_and_last_close_match_retrieved_values(series):
    """Guards the vendored snapshot against silent edits."""
    assert series.closes[0] == pytest.approx(87675.9296875)
    assert series.closes[-1] == pytest.approx(78626.125)


def test_prices_are_in_a_plausible_btc_range(series):
    lo, hi = min(series.closes), max(series.closes)
    assert 70_000 < lo < 90_000
    assert 90_000 < hi < 110_000


def test_build_script_reproduces_the_dataset():
    """The committed JSON is exactly what scripts/build_dataset.py produces."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    import build_dataset

    rebuilt = build_dataset.build()
    vendored = load_vendored()
    assert rebuilt["closes"] == vendored.closes
    assert rebuilt["timestamps"] == vendored.timestamps
