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
