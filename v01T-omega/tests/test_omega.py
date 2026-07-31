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


# --- iteration 4: the lookahead regression test ----------------------------

def test_no_lookahead_signal_timing():
    """r[k] = close[k+1]/close[k] is observable only after bar k+1 CLOSES.

    Entering at open[k+1] is therefore lookahead: that open precedes the close
    that produced the signal. The earliest honest entry is open[k+2].

    This test pins the invariant by construction: a price series that is flat
    until a single jump must produce no tradable entry before the jump bar has
    closed.
    """
    from omega.emit4 import emit
    n = 3000
    close = np.full(n, 100.0)
    close[2000:] = 110.0                      # one jump at bar 2000
    ts = np.arange(n, dtype=np.int64) * 60000
    o = np.full(n, 100.0); o[2000:] = 110.0
    panel = {"A": dict(present=np.ones(n, dtype=bool), open=o,
                       high=o * 1.001, low=o * 0.999, close=close)}
    ev = emit(ts, close, panel, 3.5, 2.5, 1.75, 60, 6,
              min_edge_mult=0.0, min_cov=0.0)
    # every entry bar must be at least 2 bars after the signal-forming return
    for st, _, _, _, sig in ev:
        assert st >= sig + 2


def test_emit4_entry_is_two_bars_after_signal():
    from omega.emit4 import emit
    rng = np.random.RandomState(0)
    n = 4000
    close = 100 * np.exp(np.cumsum(rng.randn(n) * 0.0005))
    ts = np.arange(n, dtype=np.int64) * 60000
    panel = {"A": dict(present=np.ones(n, dtype=bool), open=close,
                       high=close * 1.002, low=close * 0.998, close=close)}
    ev = emit(ts, close, panel, 2.0, 2.0, 2.0, 30, 0,
              min_edge_mult=0.0, min_cov=0.0)
    assert len(ev) > 0
    assert all(st == sig + 2 for st, _, _, _, sig in ev)


# --- straddle double-stop fix ----------------------------------------------

from omega.straddle_fix import (true_range, atr_fraction, barriers,
                                resolve_straddle)


def test_true_range_first_is_undefined():
    h = np.array([2.0, 3.0]); l = np.array([1.0, 2.0]); c = np.array([1.5, 2.5])
    tr = true_range(h, l, c)
    assert np.isnan(tr[0]) and np.isfinite(tr[1])


def test_atr_fraction_is_causal():
    """ATR at bar i must not use bar i's own range."""
    n = 60
    h = np.full(n, 1.01); l = np.full(n, 0.99); c = np.ones(n)
    h[50] = 5.0                      # a huge bar at index 50
    a = atr_fraction(h, l, c, 20)
    before, after = a[50], a[51]
    assert np.isfinite(before) and np.isfinite(after)
    assert after > before            # the shock only shows up afterwards


def test_barriers_reject_bad_atr():
    assert barriers(np.nan) is None
    assert barriers(0.0) is None
    s, t = barriers(0.01, 1.5, 1.75)
    assert np.isclose(s, 0.015) and np.isclose(t, 0.0175)


def test_resolve_straddle_tie_is_adverse():
    """A bar spanning both barriers stops both legs; never a double win."""
    high = np.array([110.0]); low = np.array([90.0])
    rl, rs, both = resolve_straddle(high, low, 100.0, 0.02, 0.05)
    assert rl == -0.02 and rs == -0.02 and both


def test_resolve_straddle_clean_up_move():
    """A clean move up: long takes target, short takes stop, not both stopped."""
    high = np.array([100.5, 106.0]); low = np.array([99.9, 105.0])
    rl, rs, both = resolve_straddle(high, low, 100.0, 0.02, 0.05)
    assert rl == 0.05 and rs == -0.02 and not both


def test_wide_atr_stop_beats_tight_fixed_stop_on_whipsaw():
    """The mechanism of the fix, isolated.

    A whipsaw path dips 30bp then rallies 30bp without ever travelling far.
    A 5bp stop is inside that noise so BOTH legs die. A 1.5xATR-style stop
    (here 2%) sits outside the noise, so neither leg is stopped and the
    position survives to trade the eventual expansion.
    """
    path = np.array([100.0, 99.70, 100.30, 99.75, 100.25, 100.0])
    high, low = path * 1.0005, path * 0.9995
    _, _, both_tight = resolve_straddle(high, low, 100.0, 0.0005, 0.005)
    _, _, both_wide = resolve_straddle(high, low, 100.0, 0.02, 0.05)
    assert both_tight, "5bp stop should be taken out by 30bp noise on both sides"
    assert not both_wide, "2% stop should survive 30bp noise"


# --- v2 tests ---------------------------------------------------------------
import numpy as np
from omega.v2 import forecast_1h, atr_causal, resolve, solve_dd, signals


def _mk(n, seed=3):
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.001, n)))
    o = np.concatenate([[c[0]], c[:-1]])
    hi = np.maximum(o, c) * 1.001
    lo = np.minimum(o, c) * 0.999
    t = np.arange(n) * 300_000.0
    return np.column_stack([t, o, c, hi, lo, np.ones(n)])


def test_v2_atr_is_causal():
    f = _mk(300)
    a = atr_causal(f)
    assert np.isnan(a[0])
    # bar i's ATR must not change if bars > i are altered
    g = f.copy()
    g[200:, 3] *= 5.0
    assert np.allclose(atr_causal(g)[:200], a[:200], equal_nan=True)


def test_v2_forecast_streak_bounds():
    h = _mk(400)
    tu, td, r3, st = forecast_1h(h)
    ok = np.isfinite(st)
    assert st[ok].min() >= 0 and st[ok].max() <= 3
    assert not np.any(tu & td)          # cannot be up and down at once


def test_v2_resolve_honest_gap_fill():
    """If the bar opens beyond the stop, the fill must be the OPEN (worse),
    never the stop price. This is the artifact V82's doc leaves in."""
    f = np.array([
        [0.0, 100.0, 100.0, 100.5, 99.5, 1.0],
        [1.0,  90.0,  90.0,  90.5, 89.5, 1.0],   # gaps far below the stop
    ])
    R, _ = resolve(f, 0, 1, 1.0, tmult=3.0, cost=0.0)
    assert R < -1.0, "gap-through must fill worse than -1R"
    assert abs(R - (-10.0)) < 1e-9


def test_v2_resolve_respects_target():
    f = np.zeros((3, 6))
    f[:, 1] = [100.0, 100.0, 100.0]
    f[:, 2] = [100.0, 100.0, 100.0]
    f[:, 3] = [100.0, 104.0, 100.0]
    f[:, 4] = [100.0, 99.9, 100.0]
    R, _ = resolve(f, 0, 1, 1.0, tmult=3.0, cost=0.0)
    assert abs(R - 3.0) < 1e-9


def test_v2_solve_dd_respects_cap():
    rng = np.random.default_rng(5)
    ev = [(float(i), float(i) + 1.0, float(x))
          for i, x in enumerate(rng.normal(0.5, 2.0, 4000))]
    r = solve_dd(ev, target_dd=0.04)
    assert r["max_dd"] <= 0.0401
    assert r["risk_per_trade"] > 0


def test_v2_no_overlapping_positions():
    f, h = _mk(4000), _mk(400)
    h[:, 0] = np.arange(400) * 3_600_000.0
    ev = signals(f, h)
    for a, b in zip(ev, ev[1:]):
        assert b[0] >= a[1], "a trade opened before the previous one closed"
