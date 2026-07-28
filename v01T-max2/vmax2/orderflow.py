"""
ITERATION 4 - order flow, the only data that is CAUSALLY UPSTREAM of price.

Every prior iteration used price history. Aggressive orders consume resting
liquidity and THEN price moves, so signed order flow is upstream of the print,
not derived from it. If a knowable-before-the-move edge exists anywhere in
public data, this is where it lives.

Data: real Kraken BTC/USD trades with aggressor flags ('b'/'s') and order type
('m' market / 'l' limit), plus 1m OHLC carrying VWAP and trade count.
"""
import os, json, math

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
TICKS = [os.path.join(DATA, "kraken_btc_ticks_w1.json"),
         os.path.join(DATA, "kraken_btc_ticks_w2.json")]
BARS1M = os.path.join(DATA, "kraken_btc_1m_vwap_trades.json")

def load_ticks(path):
    """(price, volume, timestamp, aggressor, ordertype) - real Kraken tape."""
    return [(float(p), float(v), ts, s, t) for p, v, ts, s, t in json.load(open(path))]

def load_1m():
    rows = json.load(open(BARS1M))
    return [dict(t=r[0], o=float(r[1]), h=float(r[2]), l=float(r[3]),
                 c=float(r[4]), vwap=float(r[5]), vol=float(r[6]), n=int(r[7]))
            for r in rows]

def vwap_position(b):
    """Where volume transacted inside the bar. +1 = at the high, -1 = at the low."""
    if b['h'] <= b['l']: return 0.0
    return (b['vwap'] - (b['h'] + b['l']) / 2) / ((b['h'] - b['l']) / 2)

def bucketize(ticks, seconds, market_only=False):
    """Aggregate the tape into fixed windows, computing signed order-flow imbalance."""
    t0 = ticks[0][2]; acc = {}
    for p, v, ts, side, typ in ticks:
        if market_only and typ != 'm': continue
        k = int((ts - t0) // seconds)
        b = acc.setdefault(k, dict(bv=0.0, sv=0.0, first=p, last=p))
        if side == 'b': b['bv'] += v
        else:           b['sv'] += v
        b['last'] = p
    out = []
    for k in sorted(acc):
        b = acc[k]; tot = b['bv'] + b['sv']
        out.append(dict(ofi=(b['bv'] - b['sv']) / tot if tot else 0.0,
                        ret=(b['last'] - b['first']) / b['first']))
    return out

def correlate(x, y):
    n = len(x)
    if n < 6: return None
    mx = sum(x)/n; my = sum(y)/n
    cov = sum((x[i]-mx)*(y[i]-my) for i in range(n))/n
    sx = math.sqrt(sum((v-mx)**2 for v in x)/n)
    sy = math.sqrt(sum((v-my)**2 for v in y)/n)
    if not sx or not sy: return None
    r = cov/(sx*sy)
    return dict(r=r, t=r*math.sqrt(n-2)/math.sqrt(max(1e-12, 1-r*r)), n=n)

def lead_lag(seconds, lag, market_only=False):
    """Pooled across independent tick windows. lag=0 contemporaneous, lag>=1 predictive."""
    X, Y = [], []
    for p in TICKS:
        bs = bucketize(load_ticks(p), seconds, market_only)
        if len(bs) < 4: continue
        o = [b['ofi'] for b in bs]; r = [b['ret'] for b in bs]
        if lag: X += o[:-lag]; Y += r[lag:]
        else:   X += o;        Y += r
    return correlate(X, Y)

def effective_spread_bp(path=None):
    """Median bid-ask bounce from consecutive aggressor-side flips."""
    tk = load_ticks(path or TICKS[0]); f = []
    for i in range(1, len(tk)):
        p0, _, t0, s0, _ = tk[i-1]; p1, _, t1, s1, _ = tk[i]
        if s0 != s1 and abs(t1 - t0) < 2.0:
            f.append(abs(p1-p0)/((p0+p1)/2)*10000)
    f.sort()
    return f[len(f)//2] if f else 0.0

KRAKEN_TAKER_ROUND_TRIP_BP = 26.0   # 0.13% per side at entry volume tier
