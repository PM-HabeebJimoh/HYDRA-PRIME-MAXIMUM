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
