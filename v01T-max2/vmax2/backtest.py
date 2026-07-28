"""Backtest engine. Walk-forward is the headline result; in-sample is diagnostic."""
import math
from .ohlc import load_bars, resolve, equity_path, max_leverage_within_dd
from .signals import make

FEE_ROUND_TRIP = 0.0004   # 4 bps, maker both legs

BARRIERS = [(0.005,0.00125),(0.008,0.004),(0.010,0.0025),(0.020,0.005),(0.040,0.010)]

def generate(bars, pred, stop_p, targ_p, lo, hi, side=1, fee=FEE_ROUND_TRIP):
    """Non-overlapping trades in [lo,hi). Returns list of (index, outcome, net_return)."""
    out, busy = [], -1
    for i in range(max(40, lo), min(hi, len(bars) - 1)):
        if i <= busy or not pred(i):
            continue
        o, r = resolve(bars, i, side, bars[i]['c'], stop_p, targ_p)
        out.append((i, o, r - fee)); busy = i + 1
    return out

def stats(trades):
    n = len(trades)
    if n == 0: return None
    rs = [r for _, _, r in trades]
    mu = sum(rs)/n
    sd = math.sqrt(sum((x-mu)**2 for x in rs)/n)
    wins = sum(1 for _, o, _ in trades if o == 'win')
    sharpe_m = (mu/sd*math.sqrt(n)) if sd else 0.0
    return dict(n=n, win_rate=wins/n*100, ev=mu, sd=sd,
                t_stat=(mu/(sd/math.sqrt(n))) if sd else 0.0,
                monthly_sharpe=sharpe_m, annual_sharpe=sharpe_m*math.sqrt(12))

def walk_forward(bars, train_bars=240, step=24):
    """
    Select (signal, barrier) by Sharpe on data strictly BEFORE each window,
    then trade that window. No lookahead of any kind.
    """
    sigs, *_ = make(bars)
    live = []
    for start in range(train_bars, len(bars)-1, step):
        end = min(start+step, len(bars)-1)
        best = None
        for name, pred in sigs.items():
            for sp, tp in BARRIERS:
                tr = generate(bars, pred, sp, tp, 40, start)
                if len(tr) < 20: continue
                s = stats(tr)
                if best is None or s['monthly_sharpe'] > best[0]:
                    best = (s['monthly_sharpe'], name, pred, sp, tp)
        if best is None: continue
        _, name, pred, sp, tp = best
        live += generate(bars, pred, sp, tp, start, end)
    return live

def report(trades, dd_cap=0.04):
    s = stats(trades)
    rs = [r for _, _, r in trades]
    L = max_leverage_within_dd(rs, dd_cap)
    roi, dd = equity_path(rs, L)
    s.update(max_leverage_at_dd_cap=L, roi_at_dd_cap=roi*100, dd_at_cap=dd*100)
    return s
