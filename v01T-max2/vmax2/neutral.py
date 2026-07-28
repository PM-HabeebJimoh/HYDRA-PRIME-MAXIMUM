"""
Market-neutral ETH-vs-BTC spread.

Iteration 2 proved the prior 'edge' was directional beta: EV was a fixed fraction
of month drift and flipped sign in a down month. Iteration 3 removes beta BY
CONSTRUCTION - trade ETH against a beta-weighted BTC hedge, so the common dollar
move cancels algebraically rather than by hope.

Result: the hedge works (residual beta -0.034), and the edge disappears with it.
"""
import os, json, math

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
ETH = os.path.join(DATA, "eth_usd_6h_2026_coinbase_ohlc.json")
BTC = os.path.join(DATA, "btc_usd_6h_2026_coinbase_ohlc.json")
FEE_PAIR = 0.0008          # 4bp round trip x 2 legs

def _load(p):
    d = json.load(open(p)); return {int(k): v for k, v in d.items()}

def aligned():
    e, b = _load(ETH), _load(BTC)
    ts = sorted(set(e) & set(b))
    return ts, [e[t][3] for t in ts], [b[t][3] for t in ts]

def rets(x):
    return [(x[i] - x[i-1]) / x[i-1] for i in range(1, len(x))]

def hedge_beta(rb, re_, k, w=40):
    """OLS beta of ETH on BTC using ONLY returns before k. No lookahead."""
    lo = max(0, k - w)
    xs, ys = rb[lo:k], re_[lo:k]
    if len(xs) < 20: return None
    mx = sum(xs)/len(xs); my = sum(ys)/len(ys)
    cov = sum((xs[i]-mx)*(ys[i]-my) for i in range(len(xs)))/len(xs)
    vx  = sum((x-mx)**2 for x in xs)/len(xs)
    return cov/vx if vx else None

def residual_beta(rb, re_):
    """Beta of the hedged spread against BTC. Should be ~0 if the hedge works."""
    idx, sp = [], []
    for k in range(len(rb)):
        b = hedge_beta(rb, re_, k)
        if b is None: continue
        idx.append(k); sp.append(re_[k] - b*rb[k])
    xs = [rb[k] for k in idx]
    mx = sum(xs)/len(xs); my = sum(sp)/len(sp)
    cov = sum((xs[i]-mx)*(sp[i]-my) for i in range(len(xs)))/len(xs)
    vx  = sum((x-mx)**2 for x in xs)/len(xs)
    return cov/vx if vx else None

def zscore_prev(rb, re_, k, w=20):
    """z of the LAST COMPLETED spread return. Strictly before bar k."""
    lo = max(1, k - w); xs = []
    for i in range(lo, k):
        b = hedge_beta(rb, re_, i)
        if b is not None: xs.append(re_[i] - b*rb[i])
    if len(xs) < 15: return None
    m = sum(xs)/len(xs); s = math.sqrt(sum((x-m)**2 for x in xs)/len(xs))
    bl = hedge_beta(rb, re_, k-1)
    if not s or bl is None: return None
    return ((re_[k-1] - bl*rb[k-1]) - m) / s

def backtest(side, thr, hold, fee=FEE_PAIR):
    """Enter when z is extreme; hold `hold` bars; both legs at real closes."""
    ts, ec, bc = aligned()
    re_, rb = rets(ec), rets(bc)
    n = len(rb); out = []; k = 26
    while k < n - hold:
        z = zscore_prev(rb, re_, k)
        if z is None: k += 1; continue
        if not ((side > 0 and z < -thr) or (side < 0 and z > thr)):
            k += 1; continue
        b = hedge_beta(rb, re_, k) or 0.0
        pe = (ec[k+hold] - ec[k]) / ec[k]
        pb = (bc[k+hold] - bc[k]) / bc[k]
        out.append(side * (pe - b*pb) - fee)
        k += hold
    return out

def summary(tr):
    n = len(tr)
    if not n: return None
    m = sum(tr)/n
    s = math.sqrt(sum((x-m)**2 for x in tr)/n)
    return dict(n=n, ev=m, sd=s,
                win_rate=sum(1 for x in tr if x > 0)/n*100,
                t_stat=(m/(s/math.sqrt(n))) if s else 0.0,
                sharpe=(m/s*math.sqrt(n)) if s else 0.0)
