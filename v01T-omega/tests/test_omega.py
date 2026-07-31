import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from omega.indicators import rolling_std_pop, rolling_std_samp, bb_percent, hv_ratio, score_of
from omega.fastbarrier import first_touch
from omega.panel import align_to
from omega.statefilter import standdown_mask
from omega.strategy import max_leverage_at_dd
from omega.leadlag import max_drawdown


def test_pop_and_sample_std_match_numpy():
    y = np.random.RandomState(0).randn(60) * 100 + 60000
    assert np.allclose(rolling_std_pop(y, 20)[19], np.std(y[:20]))
    assert np.allclose(rolling_std_samp(y, 20)[19], np.std(y[:20], ddof=1))


def test_bb_percent_matches_definition():
    c = np.random.RandomState(1).randn(40).cumsum() + 100
    m, s = c[:20].mean(), np.std(c[:20])
    expect = (c[19] - (m - 2 * s)) / (4 * s) * 100
    assert np.allclose(bb_percent(c)[19], expect)


def test_score_thresholds_are_strict():
    bb = np.array([9.99, 10.0, 90.0, 90.01])
    s = score_of(bb)
    assert s[0] == 92 and s[1] == 72 and s[2] == 72 and s[3] == 85


def test_hv_ratio_undefined_early():
    c = np.arange(1, 30, dtype=float)
    assert np.isnan(hv_ratio(c)[:21]).all()


def test_barrier_tie_resolves_adverse():
    """A bar spanning both barriers must be scored as a LOSS, never a win."""
    high = np.array([101.0]); low = np.array([99.0])
    out, _ = first_touch(high, low, np.array([0]), np.array([100.0]),
                         np.array([99.5]), np.array([100.5]),
                         np.array([1], dtype=np.int8), 1)
    assert out[0] == -1


def test_barrier_clean_target():
    high = np.array([100.6]); low = np.array([99.9])
    out, _ = first_touch(high, low, np.array([0]), np.array([100.0]),
                         np.array([99.5]), np.array([100.5]),
                         np.array([1], dtype=np.int8), 1)
    assert out[0] == 1


def test_barrier_timeout_is_zero():
    high = np.array([100.1]); low = np.array([99.9])
    out, _ = first_touch(high, low, np.array([0]), np.array([100.0]),
                         np.array([99.5]), np.array([100.5]),
                         np.array([1], dtype=np.int8), 1)
    assert out[0] == 0


def test_align_marks_missing_bars_absent():
    master = np.array([0, 60000, 120000], dtype=np.int64)
    d = dict(ts=np.array([0, 120000], dtype=np.int64))
    present, ix = align_to(master, d)
    assert list(present) == [True, False, True]


def test_standdown_is_causal_and_skips_after_loss():
    net = np.array([-1.0, 1.0, -1.0, -1.0, 1.0])
    m = standdown_mask(net, 1)
    # first trade always taken; after a loss the next is skipped
    assert m[0] and not m[1]


def test_max_drawdown_basic():
    eq = np.array([1.0, 1.2, 0.9, 1.5])
    assert np.isclose(max_drawdown(eq), (1.2 - 0.9) / 1.2)


def test_leverage_search_respects_dd_cap():
    rng = np.random.RandomState(3)
    net = rng.randn(500) * 0.002 + 0.0008
    lev = max_leverage_at_dd(net, 0.04)
    eq = np.cumprod(1 + lev * net)
    assert max_drawdown(eq) <= 0.0401
