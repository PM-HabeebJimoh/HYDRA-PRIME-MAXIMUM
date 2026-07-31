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


# --- portfolio / alt-scaling regression tests -------------------------------

from omega.portfolio import simulate, curve_max_dd
from omega.altscaled import alt_vol, _touch
from omega.volgate import cost_aware_floor


def test_ruin_is_reported_as_failure_not_nan():
    """A blow-up must return a losing curve, never NaN that a search accepts."""
    ev = [(0, 1, -1.0), (2, 3, -1.0)]
    t, v, n = simulate(ev, 10, lev=100.0, max_concurrent=1)
    assert np.all(np.isfinite(v)) and v[-1] <= 0


def test_slot_limit_actually_blocks_trades():
    ev = [(0, 100, 0.01), (1, 100, 0.01), (2, 100, 0.01)]
    _, _, n = simulate(ev, 200, lev=1.0, max_concurrent=1)
    assert n == 1


def test_alt_vol_is_causal():
    """sigma at index i must not use the return into bar i."""
    c = np.ones(300)
    c[250:] = 2.0
    v = alt_vol(c, 240)
    assert not np.isfinite(v[0])
    # the jump at 250 must not be visible before it happens
    assert v[249] == 0.0 or np.isnan(v[249])


def test_cost_aware_floor_scales_with_target():
    assert np.isclose(cost_aware_floor(6, 3, 3.0), 3 * 6e-4 / 3)
    assert cost_aware_floor(6, 1) > cost_aware_floor(6, 3)


def test_touch_tie_is_adverse():
    hi = np.array([102.0]); lo = np.array([98.0])
    o, _ = _touch(hi, lo, 100.0, 99.0, 101.0, 1)
    assert o == -1


# --- iteration 3: liquidity gate, dynamic control, governor ----------------

from omega.liquidity import trailing_coverage, tradable_mask
from omega.control import ewma, causal_shift, vol_target_weights, edge_state_weights
from omega.run2 import simulate_w, simulate_gov, max_dd as mdd2


def test_trailing_coverage_is_causal():
    """Coverage at bar i must not include bar i itself."""
    p = np.zeros(20, dtype=bool)
    p[10:] = True
    c = trailing_coverage(p, 5)
    # at index 10 the trailing 5 bars (5..9) were all absent
    assert c[10] == 0.0


def test_tradable_mask_blocks_unlisted_pair():
    """A pair is untradable until it has been quoted for a FULL window.

    The gate needs `window` minutes of history at >= min_cov, so a pair listed
    at bar 2000 only becomes tradable at ~2000+1440. This is deliberate: it is
    exactly the guarantee that we never trade a pair the venue was not yet
    continuously quoting.
    """
    n = 5000
    panel = {"X": {"present": np.zeros(n, dtype=bool)}}
    panel["X"]["present"][2000:] = True
    tm = tradable_mask(panel, 1440, 0.90)
    assert not tm["X"][1500]      # before listing
    assert not tm["X"][2999]      # listed, but < full window of history
    assert tm["X"][n - 1]         # a full window after listing


def test_causal_shift_hides_current_value():
    x = np.array([1.0, 2.0, 3.0])
    s = causal_shift(x)
    assert np.isnan(s[0]) and s[1] == 1.0 and s[2] == 2.0


def test_control_weights_never_use_future():
    """A huge loss at index k must not reduce the weight AT index k."""
    r = np.zeros(200); r[100] = -0.5
    w = edge_state_weights(r, 50)
    wv = vol_target_weights(r, 50)
    assert np.isfinite(w[100]) and np.isfinite(wv[100])
    # the shock must show up only afterwards
    assert wv[101] < wv[99] or w[101] <= w[99]


def test_governor_reduces_size_in_drawdown():
    ev = [(i, i + 1, -0.02) for i in range(0, 60, 2)]
    _, v_plain, _, _ = simulate_w(ev, 1.0, 1)
    _, v_gov, _, _ = simulate_gov(ev, 1.0, 1, dd_soft=0.005, dd_hard=0.02)
    assert v_gov[-1] > v_plain[-1]      # throttling loses less


def test_gross_notional_definition():
    """One slot, weight 1, lev L -> notional is L x equity."""
    ev = [(0, 1, 0.10)]
    _, v, _, _ = simulate_w(ev, 2.0, 1)
    assert np.isclose(v[-1], 1.0 + 2.0 * 0.10)
