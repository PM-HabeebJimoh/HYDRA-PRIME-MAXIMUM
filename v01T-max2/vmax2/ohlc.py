"""Real OHLC loading + honest barrier resolution. No synthetic data anywhere."""
import json, os, math

DATA = os.path.join(os.path.dirname(__file__), "..", "data",
                    "btc_usd_1h_jul2026_coinbase_ohlc.json")

def load_bars(path=None):
    """601 real Coinbase BTC-USD 1h bars, 2026-07-01..2026-07-26, zero gaps."""
    d = json.load(open(path or DATA))
    out = []
    for t in sorted(int(k) for k in d):
        lo, hi, op, cl, vol = d[str(t)]
        out.append(dict(t=t, o=op, h=hi, l=lo, c=cl, v=vol))
    return out

def resolve(bars, i, side, entry, stop_p, targ_p, horizon=720):
    """
    Resolve a barrier trade entered at close of bar i using REAL subsequent OHLC.

    CONSERVATIVE RULE: when a single bar's high/low range spans BOTH the target
    and the stop, the intrabar ordering is unknowable at 1h resolution, so the
    trade is booked as a LOSS ('ambiguous_loss'). This is the fix for v01T's
    100%-win-rate artifact, which counted such bars as wins.
    """
    if side > 0:
        tp, sl = entry * (1 + targ_p), entry * (1 - stop_p)
    else:
        tp, sl = entry * (1 - targ_p), entry * (1 + stop_p)
    for j in range(i + 1, min(i + 1 + horizon, len(bars))):
        b = bars[j]
        hit_tp = b['h'] >= tp if side > 0 else b['l'] <= tp
        hit_sl = b['l'] <= sl if side > 0 else b['h'] >= sl
        if hit_tp and hit_sl:
            return 'ambiguous_loss', -stop_p
        if hit_tp:
            return 'win', targ_p
        if hit_sl:
            return 'loss', -stop_p
    last = bars[min(i + horizon, len(bars) - 1)]['c']
    return 'timeout', side * (last - entry) / entry

def stdev(xs, pop=True):
    n = len(xs); m = sum(xs) / n
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (n if pop else n - 1)), m

def equity_path(returns, leverage):
    """Compound net per-trade returns at leverage; return (roi, max_drawdown)."""
    eq = pk = 1.0; dd = 0.0
    for r in returns:
        eq *= (1 + leverage * r)
        if eq <= 0:
            return -1.0, 1.0
        pk = max(pk, eq); dd = max(dd, (pk - eq) / pk)
    return eq - 1.0, dd

def max_leverage_within_dd(returns, dd_cap=0.04):
    lo, hi = 0.0, 100.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if equity_path(returns, mid)[1] < dd_cap: lo = mid
        else: hi = mid
    return lo
