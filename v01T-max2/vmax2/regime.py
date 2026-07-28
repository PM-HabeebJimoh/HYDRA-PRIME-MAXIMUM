"""
Regime test: the decisive check for whether an edge is real or drift capture.

A rule with genuine alpha is profitable in an up month AND a down month.
A rule that merely holds directional exposure flips sign with the market.
Real data: July 2026 (+10.20%) vs June 2026 (-16.29%), both Coinbase 1h OHLC.
"""
import os, json
from .ohlc import resolve

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
JUL = os.path.join(DATA_DIR, "btc_usd_1h_jul2026_coinbase_ohlc.json")
JUN = os.path.join(DATA_DIR, "btc_usd_1h_jun2026_coinbase_ohlc.json")

def load_month(path):
    d = json.load(open(path)); out = []
    for t in sorted(int(k) for k in d):
        lo, hi, op, cl, v = d[str(t)]
        out.append(dict(t=t, o=op, h=hi, l=lo, c=cl, v=v))
    return out

def drift(bars):
    return (bars[-1]['c'] - bars[0]['c']) / bars[0]['c']

def trades(bars, pred, stop_p, targ_p, side=1, fee=0.0004):
    out, busy = [], -1
    for i in range(40, len(bars) - 1):
        if i <= busy or not pred(i): continue
        o, r = resolve(bars, i, side, bars[i]['c'], stop_p, targ_p)
        out.append((o, r - fee)); busy = i + 1
    return out

def ev(tr):
    return sum(r for _, r in tr) / len(tr) if tr else 0.0

def win_rate(tr):
    return sum(1 for o, _ in tr if o == 'win') / len(tr) * 100 if tr else 0.0

def survives_both_regimes(pred_jul, pred_jun, stop_p, targ_p, side=1):
    """True only if the rule has positive expectancy in BOTH months."""
    a = trades(load_month(JUL), pred_jul, stop_p, targ_p, side)
    b = trades(load_month(JUN), pred_jun, stop_p, targ_p, side)
    if len(a) < 15 or len(b) < 12: return None
    return ev(a) > 0 and ev(b) > 0
