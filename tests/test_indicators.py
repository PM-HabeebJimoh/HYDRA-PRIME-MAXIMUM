"""Tests for the BB% / HV / elite-filter primitives."""

import pytest

from v01t import spec
from v01t.dataset import load_vendored
from v01t.indicators import compute_bb_percentile, compute_hv_ratio, is_elite, score_for


# ------------------------------------------------------------------- BB% ---

def test_bb_neutral_when_window_too_short():
    assert compute_bb_percentile([1.0, 2.0, 3.0]) == 50.0


def test_bb_neutral_on_flat_series():
    assert compute_bb_percentile([100.0] * 20) == 50.0


def test_bb_midpoint_is_50_for_symmetric_window():
    closes = list(range(1, 20)) + [10]  # last close equals the mean of 1..19
    bb = compute_bb_percentile([float(c) for c in closes])
    assert bb == pytest.approx(50.0, abs=1.0)


def test_bb_is_finite_and_sane_on_real_data():
    """BB% can overshoot 0-100 when price breaks the 2-sigma band; it must stay finite."""
    closes = load_vendored().closes
    values = [compute_bb_percentile(closes[: i + 1]) for i in range(spec.BB_WINDOW, len(closes))]
    assert all(isinstance(v, float) for v in values)
    assert all(-200 <= v <= 300 for v in values)
    # the real January series does produce genuine band extremes
    assert any(v < spec.BB_LOW for v in values)
    assert any(v > spec.BB_HIGH for v in values)


def test_bb_high_when_last_close_spikes_up():
    closes = [100.0] * 19 + [130.0]
    assert compute_bb_percentile(closes) > spec.BB_HIGH


def test_bb_low_when_last_close_spikes_down():
    closes = [100.0] * 19 + [70.0]
    assert compute_bb_percentile(closes) < spec.BB_LOW


# --------------------------------------------------------------- HV ratio ---

def test_hv_neutral_when_series_too_short():
    assert compute_hv_ratio([1.0] * 10) == 1.0


def test_hv_neutral_on_flat_series():
    assert compute_hv_ratio([100.0] * 40) == 1.0


def test_hv_below_one_when_recent_vol_compresses():
    import random
    random.seed(7)
    noisy = [100.0]
    for _ in range(30):
        noisy.append(noisy[-1] * (1 + random.uniform(-0.02, 0.02)))
    calm = [noisy[-1] * (1 + 0.00001 * i) for i in range(1, 6)]
    assert compute_hv_ratio(noisy + calm) < 1.0


def test_hv_is_positive_on_real_data():
    closes = load_vendored().closes
    for i in range(spec.HV_MIN_CLOSES, len(closes), 17):
        assert compute_hv_ratio(closes[: i + 1]) > 0


# -------------------------------------------------------------------- score ---

def test_score_assignment():
    assert score_for(5.0) == 92
    assert score_for(95.0) == 85
    assert score_for(50.0) == 72


# ------------------------------------------------------------- elite filter ---

def test_elite_requires_band_extreme():
    assert not is_elite(50.0, 0.3, 92)


def test_elite_requires_hv_compression():
    assert not is_elite(5.0, 0.9, 92)


def test_elite_requires_score():
    assert not is_elite(5.0, 0.3, 80)


def test_elite_passes_lower_band_squeeze():
    assert is_elite(5.0, 0.3, 92)


def test_elite_passes_upper_band_squeeze():
    assert is_elite(95.0, 0.3, 85)


def test_elite_boundaries_are_strict():
    assert not is_elite(spec.BB_LOW, 0.3, 92)
    assert not is_elite(spec.BB_HIGH, 0.3, 85)
    assert not is_elite(5.0, spec.HV_MAX, 92)


def test_elite_infers_score_when_omitted():
    assert is_elite(5.0, 0.3)
    assert is_elite(95.0, 0.3)
    assert not is_elite(50.0, 0.3)
