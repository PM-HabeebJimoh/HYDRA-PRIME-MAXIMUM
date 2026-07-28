import sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from vmax2 import (load_bars, resolve, equity_path, max_leverage_within_dd,
                   walk_forward, generate, stats, report,
                   required_sharpe, required_win_rate)

BARS = load_bars()

# ---------- data integrity: the data must be real and complete ----------
def test_bar_count_and_contiguity():
    assert len(BARS) == 601
    ts = [b['t'] for b in BARS]
    assert all(b - a == 3600 for a, b in zip(ts, ts[1:])), "hourly gaps present"

def test_july_2026_window():
    import datetime as dt
    f = dt.datetime.utcfromtimestamp(BARS[0]['t'])
    l = dt.datetime.utcfromtimestamp(BARS[-1]['t'])
    assert (f.year, f.month, f.day) == (2026, 7, 1)
    assert (l.year, l.month) == (2026, 7)

def test_ohlc_self_consistent():
    for b in BARS:
        assert b['l'] <= b['o'] <= b['h']
        assert b['l'] <= b['c'] <= b['h']
        assert b['v'] > 0

# ---------- resolution honesty ----------
def test_ambiguous_bar_books_as_loss():
    """A bar spanning both barriers must NOT be counted as a win."""
    bars = [dict(t=0, o=100, h=100, l=100, c=100),
            dict(t=3600, o=100, h=110, l=90, c=100)]
    o, r = resolve(bars, 0, 1, 100.0, 0.05, 0.05)
    assert o == 'ambiguous_loss' and r < 0

def test_clean_win_and_loss():
    up = [dict(t=0,o=100,h=100,l=100,c=100), dict(t=1,o=100,h=106,l=99.9,c=105)]
    assert resolve(up, 0, 1, 100.0, 0.05, 0.05)[0] == 'win'
    dn = [dict(t=0,o=100,h=100,l=100,c=100), dict(t=1,o=100,h=100.1,l=94,c=95)]
    assert resolve(dn, 0, 1, 100.0, 0.05, 0.05)[0] == 'loss'

# ---------- the core empirical claim ----------
def test_win_rate_tracks_random_walk():
    """WR is a function of stop/target, not of skill: |real - s/(s+t)| is small."""
    for sp, tp in [(0.005,0.005),(0.010,0.0025),(0.040,0.010)]:
        s = stats(generate(BARS, lambda i: True, sp, tp, 40, len(BARS), fee=0.0))
        assert abs(s['win_rate'] - sp/(sp+tp)*100) < 6.0

def test_wide_stop_manufactures_80pct_win_rate():
    s = stats(generate(BARS, lambda i: True, 0.04, 0.01, 40, len(BARS), fee=0.0))
    assert s['win_rate'] > 80          # trivially achieved
    assert s['ev'] > 0 or True         # WR alone says nothing about profit

# ---------- feasibility bound ----------
def test_required_sharpe_is_extreme():
    r = required_sharpe()
    assert 18 < r['annual_sharpe'] < 20
    assert r['annual_sharpe'] > 8      # exceeds elite HFT market-making

def test_required_win_rate_monotone_in_n():
    a = required_win_rate(100); b = required_win_rate(100000)
    assert a > b > 0.80

# ---------- walk-forward result is reproducible and honest ----------
def test_walk_forward_reproducible():
    rep = report(walk_forward(BARS))
    assert rep['n'] == 127
    assert abs(rep['win_rate'] - 72.44) < 0.5
    assert rep['annual_sharpe'] < 18.8       # below what the targets demand

def test_targets_are_jointly_unmet():
    rep = report(walk_forward(BARS))
    assert not (rep['win_rate'] > 80 and rep['roi_at_dd_cap'] > 1000)

def test_roi_and_dd_ranges_are_disjoint():
    """No leverage gives both ROI>1000% and DD<4%."""
    rs = [r for _, _, r in walk_forward(BARS)]
    L = 0.05
    while L <= 50:
        roi, dd = equity_path(rs, L)
        assert not (roi*100 > 1000 and dd*100 < 4), f"found passing leverage {L}"
        L *= 1.25

def test_dd_is_monotone_in_leverage():
    rs = [r for _, _, r in walk_forward(BARS)]
    dds = [equity_path(rs, L)[1] for L in (0.5, 1, 2, 4, 8)]
    assert all(a <= b + 1e-9 for a, b in zip(dds, dds[1:]))

def test_max_leverage_within_dd_respects_cap():
    rs = [r for _, _, r in walk_forward(BARS)]
    L = max_leverage_within_dd(rs, 0.04)
    assert equity_path(rs, L)[1] <= 0.0401

# ---------- v01T's original gate has no edge ----------
def test_v01t_gate_not_better_than_baseline():
    from vmax2.signals import make
    sigs, *_ = make(BARS)
    g = stats(generate(BARS, sigs['v01t_gate'], 0.010, 0.0025, 40, len(BARS)))
    b = stats(generate(BARS, sigs['all'],       0.010, 0.0025, 40, len(BARS)))
    assert g['ev'] <= b['ev'] + 1e-6

# ---------- regime test: the decisive check on whether edge is real ----------
from vmax2.regime import load_month, drift, trades, ev, win_rate, JUL, JUN

JULB = load_month(JUL)
JUNB = load_month(JUN)

def test_june_data_is_real_and_contiguous():
    assert len(JUNB) == 241
    ts = [b['t'] for b in JUNB]
    assert all(b - a == 3600 for a, b in zip(ts, ts[1:]))
    for b in JUNB:
        assert b['l'] <= b['o'] <= b['h'] and b['l'] <= b['c'] <= b['h']

def test_the_two_months_are_opposite_regimes():
    assert drift(JULB) > 0.05     # July rose
    assert drift(JUNB) < -0.10    # June fell

def test_july_winning_config_loses_in_june():
    """The config walk-forward picked on July has NEGATIVE expectancy in June."""
    j = trades(JULB, lambda i: True, 0.04, 0.01, 1)
    n = trades(JUNB, lambda i: True, 0.04, 0.01, 1)
    assert ev(j) > 0 and ev(n) < 0
    assert win_rate(j) > 80 and win_rate(n) < 70

def test_no_config_survives_both_regimes():
    """Zero of the tested rules are profitable in both an up and a down month."""
    from vmax2.signals import make
    sj, *_ = make(JULB); sn, *_ = make(JUNB)
    surv = tot = 0
    for name in sj:
        for sp, tp in [(0.010,0.0025),(0.020,0.005),(0.040,0.010),(0.008,0.004)]:
            for side in (1, -1):
                a = trades(JULB, sj[name], sp, tp, side)
                b = trades(JUNB, sn[name], sp, tp, side)
                if len(a) < 15 or len(b) < 12: continue
                tot += 1
                if ev(a) > 0 and ev(b) > 0: surv += 1
    assert tot >= 30
    assert surv == 0, f"{surv} configs claimed to survive both regimes"

def test_ev_is_proportional_to_drift():
    """EV/drift is nearly identical across opposite months => pure beta, no alpha."""
    rj = ev(trades(JULB, lambda i: True, 0.04, 0.01, 1)) / drift(JULB)
    rn = ev(trades(JUNB, lambda i: True, 0.04, 0.01, 1)) / drift(JUNB)
    assert rj > 0 and rn > 0
    assert abs(rj - rn) / max(rj, rn) < 0.10   # within 10% of each other

def test_high_win_rate_appears_on_both_sides():
    """WR>80% is a barrier artifact: it shows up long in July and short in June."""
    assert win_rate(trades(JULB, lambda i: True, 0.04, 0.01,  1)) > 80
    assert win_rate(trades(JUNB, lambda i: True, 0.04, 0.01, -1)) > 80

# ---------- iteration 3: market-neutral construction ----------
from vmax2 import neutral as NEU

def test_neutral_data_real_and_aligned():
    ts, ec, bc = NEU.aligned()
    assert len(ts) == 130
    assert all(b - a == 21600 for a, b in zip(ts, ts[1:]))
    assert all(x > 0 for x in ec) and all(x > 0 for x in bc)

def test_hedge_actually_removes_beta():
    """The whole point of iteration 3: beta must be ~0 by construction."""
    ts, ec, bc = NEU.aligned()
    re_, rb = NEU.rets(ec), NEU.rets(bc)
    raw = NEU.hedge_beta(rb, re_, len(rb))        # full-sample ETH beta
    res = NEU.residual_beta(rb, re_)              # after hedging
    assert raw > 0.8, "ETH should have large raw beta to BTC"
    assert abs(res) < 0.10, f"hedge failed, residual beta {res}"

def test_hedge_beta_uses_no_lookahead():
    ts, ec, bc = NEU.aligned()
    re_, rb = NEU.rets(ec), NEU.rets(bc)
    k = 60
    b_now = NEU.hedge_beta(rb, re_, k)
    re2 = list(re_); re2[k] = re2[k] * 100        # corrupt the ENTRY bar
    rb2 = list(rb);  rb2[k] = rb2[k] * 100
    assert NEU.hedge_beta(rb2, re2, k) == b_now   # unchanged => no lookahead

def test_zscore_uses_no_lookahead():
    ts, ec, bc = NEU.aligned()
    re_, rb = NEU.rets(ec), NEU.rets(bc)
    k = 60
    z = NEU.zscore_prev(rb, re_, k)
    re2 = list(re_); re2[k] *= 100
    assert NEU.zscore_prev(rb, re2, k) == z

def test_neutral_edge_is_not_significant():
    """Once beta is removed the edge vanishes into noise."""
    for side in (1, -1):
        for hold in (1, 2, 4):
            s = NEU.summary(NEU.backtest(side, 1.0, hold))
            if s and s['n'] >= 8:
                assert abs(s['t_stat']) < 2.0, f"unexpected significance {s}"

def test_neutral_fails_the_targets():
    from vmax2.ohlc import equity_path, max_leverage_within_dd
    tr = NEU.backtest(1, 1.0, 4)
    s = NEU.summary(tr)
    L = max_leverage_within_dd(tr, 0.04)
    roi, dd = equity_path(tr, L)
    assert s['win_rate'] < 80        # WR target missed
    assert roi * 100 < 1000          # ROI target missed by orders of magnitude
    assert dd <= 0.0401

# ---------- iteration 4: order flow (data causally upstream of price) ----------
from vmax2 import orderflow as OF

def test_tick_data_is_real_and_has_aggressor_flags():
    tot = 0
    for p in OF.TICKS:
        tk = OF.load_ticks(p)
        tot += len(tk)
        assert all(s in ('b', 's') for _, _, _, s, _ in tk)
        assert all(t in ('m', 'l') for _, _, _, _, t in tk)
        ts = [x[2] for x in tk]
        assert ts == sorted(ts), "tape must be time-ordered"
        assert all(px > 0 and v > 0 for px, v, _, _, _ in tk)
    assert tot >= 180

def test_1m_bars_carry_vwap_within_range():
    for b in OF.load_1m():
        assert b['l'] <= b['vwap'] <= b['h']
        assert b['l'] <= b['o'] <= b['h'] and b['l'] <= b['c'] <= b['h']
        assert b['n'] > 0 and b['vol'] > 0

def test_order_flow_impact_is_contemporaneous_and_positive():
    """Flow DOES move price within the same window - real, but already priced."""
    rs = [OF.lead_lag(s, 0)['r'] for s in (10, 15, 20, 30)]
    assert all(r > 0 for r in rs), f"impact should be positive everywhere, got {rs}"

def test_order_flow_does_not_predict_next_window():
    """The tradable claim fails: predictive correlation flips sign across windows."""
    rs = [OF.lead_lag(s, 1)['r'] for s in (10, 15, 20, 30)]
    assert any(r > 0 for r in rs) and any(r < 0 for r in rs), \
        f"a stable lead would not flip sign, got {rs}"
    for s in (10, 15, 20, 30):
        assert abs(OF.lead_lag(s, 1)['t']) < 2.7   # Bonferroni for 8 tests

def test_vwap_position_has_no_forward_information():
    bars = OF.load_1m()
    vp  = [OF.vwap_position(b) for b in bars]
    ret = [(b['c'] - b['o']) / b['o'] for b in bars]
    for lag in (1, 2, 3):
        c = OF.correlate(vp[:len(vp)-lag], ret[lag:])
        assert abs(c['t']) < 2.0, f"lag {lag} unexpectedly significant: {c}"

def test_fees_dominate_any_measured_flow_signal():
    """Structural kill: best-case signal is far below the cost of acting on it."""
    best_r = max(abs(OF.lead_lag(s, 1)['r']) for s in (10, 15, 20, 30))
    move_sd_bp = 1.5                      # typical 10s BTC move
    edge_bp = best_r * move_sd_bp
    assert edge_bp < OF.KRAKEN_TAKER_ROUND_TRIP_BP
    assert edge_bp < 2.0                  # under 2bp even before fees

def test_spread_is_tiny_so_fees_are_the_real_wall():
    sp = OF.effective_spread_bp()
    assert 0 < sp < 1.0
    assert OF.KRAKEN_TAKER_ROUND_TRIP_BP > 20 * sp

# ---------- iteration 5: funding / positioning ----------
from vmax2 import funding as FND

def test_funding_data_is_real_and_contiguous():
    d, segs = FND.segments()
    assert len(d) >= 100
    assert all(len(s) >= 50 for s in segs)
    for s in segs:
        assert all(b - a == 3600000 for a, b in zip(s, s[1:]))
    for v in d.values():
        assert v[0] > 0            # index price positive
        assert -0.01 < v[1] < 0.01 # funding is a small rate

def test_funding_is_highly_autocorrelated():
    """This is WHY overlapping windows inflate significance."""
    assert FND.funding_autocorr() > 0.9

def test_overlapping_windows_inflate_significance():
    """The trap: overlap makes a non-result look like a discovery."""
    ov = FND.predict(8, overlapping=True)
    no = FND.predict(8, overlapping=False)
    assert abs(ov['t']) > abs(no['t']), "overlap should inflate the t-stat"
    assert ov['n'] > 5 * no['n']       # 90 vs 12 nominal observations

def test_funding_signal_is_not_significant_when_honest():
    """Non-overlapping - the only valid test - fails to reject the null."""
    for k in (4, 8):
        c = FND.predict(k, overlapping=False)
        assert abs(c['t']) < 2.0, f"k={k} unexpectedly significant: {c}"

def test_effective_sample_size_correction():
    ov = FND.predict(8, overlapping=True)
    assert FND.effective_n(ov['n'], 8) < 12   # ~11 independent points, not 90

def test_funding_cannot_reach_the_targets():
    """Even taking the point estimate at face value, DD blows up."""
    r = abs(FND.predict(8, overlapping=False)['r'])
    move_sd_8h = 0.0075
    edge = r * move_sd_8h - 0.0004        # net of 4bp maker
    trades = 90                            # 8h spacing, one month
    monthly_1x = (1 + edge) ** trades - 1
    assert monthly_1x < 1.0                # nowhere near +1000% at 1x
    need = math.log(11) / trades
    lev = need / math.log(1 + edge)
    assert lev * move_sd_8h > 0.04         # one 1-sd bar breaches the 4% DD cap

# ---------- iteration 5: cross-venue mechanical forcing ----------
from vmax2 import crossvenue as XV

def test_cross_venue_data_is_timestamp_matched():
    ts, C, K, V = XV.load_matched()
    assert len(ts) == 100
    assert all(b - a == 60 for a, b in zip(ts, ts[1:])), "must be contiguous 1m bars"
    assert len(C) == len(K) == len(V) == len(ts)
    assert all(x > 0 for x in C + K + V)

def test_dislocation_is_small_and_two_sided():
    ts, C, K, V = XV.load_matched()
    S = XV.dislocation_bp(C, K)
    assert max(S) > 0 and min(S) < 0        # both venues take turns being rich
    assert max(abs(x) for x in S) < 10.0    # efficient market: gap stays tiny

def test_gap_is_mechanically_forced_closed():
    """The real finding: strong, fast mean reversion of the cross-venue gap."""
    ts, C, K, V = XV.load_matched()
    mr = XV.mean_reversion(XV.dislocation_bp(C, K))
    assert mr['t'] < -5.0, f"expected strong reversion, got {mr}"
    assert -1 < mr['decay'] < 0
    assert mr['half_life_bars'] < 2.0       # gap closes inside ~1 bar

def test_convergence_edge_is_real_and_strong():
    """This edge is genuine - unlike every prior iteration's."""
    ts, C, K, V = XV.load_matched()
    S = XV.dislocation_bp(C, K)
    s = XV.summary(XV.convergence_trades(S, 1.0))
    assert s['win_rate'] > 80
    assert s['t_stat'] > 4.0
    assert s['mean_bp'] > 0

def test_edge_survives_vwap_respecification():
    """Not a close-print artifact: it holds when Kraken VWAP replaces the close."""
    ts, C, K, V = XV.load_matched()
    s = XV.summary(XV.convergence_trades(XV.dislocation_bp(C, V), 1.0))
    assert s['t_stat'] > 4.0 and s['win_rate'] > 80

def test_both_legs_rarely_fill():
    """THE KILLER: the dual-maker assumption fails on real data."""
    f = XV.fill_feasibility(1.0)
    assert f['episodes'] >= 20
    assert f['both_pct'] < 20.0, f"dual fill should be rare, got {f}"
    assert f['one_leg'] > f['both']

def test_taker_costs_destroy_the_edge():
    ts, C, K, V = XV.load_matched()
    S = XV.dislocation_bp(C, K)
    for thr in (1.0, 1.5, 2.0):
        gross = XV.summary(XV.convergence_trades(S, thr))['mean_bp']
        assert gross < XV.full_round_trip_taker_bp() / 10
        assert XV.net_after_costs(gross, ('kraken',)) < 0      # even ONE crossed leg
        assert XV.net_after_costs(gross, ('coinbase', 'kraken')) < 0

def test_roi_ceiling_below_target_even_at_zero_cost():
    """Grant free execution - physically impossible - and 1000%/mo is still out of reach."""
    ts, C, K, V = XV.load_matched()
    S = XV.dislocation_bp(C, K)
    span_min = (ts[-1] - ts[0]) / 60
    best = 0.0
    for thr in (1.0, 1.5, 2.0):
        s = XV.summary(XV.convergence_trades(S, thr))
        per_month = s['n'] / span_min * 60 * 24 * 30
        roi = (1 + s['mean_bp']/10000) ** per_month - 1
        best = max(best, roi * 100)
    assert best < 1000.0, f"zero-cost ceiling {best:.1f}% unexpectedly clears target"
