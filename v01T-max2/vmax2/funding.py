"""
ITERATION 5 - positioning data (funding), the last untested upstream source.

Funding rate is not price history. It is a direct readout of LEVERAGE IMBALANCE:
positive funding => longs pay shorts => crowded long => vulnerable to a forced
unwind. Forced liquidations are mechanically determined before price reacts, so
this is the strongest remaining candidate for "know the direction before the move".

Data: real Deribit BTC-PERPETUAL hourly funding + index price, July 2026,
two contiguous segments of 53 hours each.

RESULT: the raw signal looks strong and is an ARTIFACT. Funding has lag-1
autocorrelation +0.962, so overlapping k-hour windows are not independent
observations and inflate t-stats by ~sqrt(k). Corrected, the effect is n=12,
t=-1.27 - not significant.
"""
import os, json, math

DATA = os.path.join(os.path.dirname(__file__), "..", "data",
                    "deribit_btc_perp_funding_jul2026.json")

def load():
    return {int(k): v for k, v in json.load(open(DATA)).items()}

def segments():
    """Contiguous hourly runs. Funding gaps must not be bridged."""
    d = load(); ks = sorted(d)
    out, cur = [], [ks[0]]
    for a, b in zip(ks, ks[1:]):
        if b - a == 3600000: cur.append(b)
        else: out.append(cur); cur = [b]
    out.append(cur)
    return d, out

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

def funding_autocorr():
    d, segs = segments()
    f = [d[t][1] for t in segs[0]]
    return correlate(f[:-1], f[1:])['r']

def predict(k, overlapping=True):
    """Funding at hour i vs index return over the next k hours."""
    d, segs = segments()
    X, Y = [], []
    for s in segs:
        ip = [d[t][0] for t in s]; f8 = [d[t][1] for t in s]
        step = 1 if overlapping else k
        for i in range(0, len(s)-k, step):
            X.append(f8[i]); Y.append((ip[i+k]-ip[i])/ip[i])
    return correlate(X, Y)

def effective_n(nominal, k):
    """Overlapping windows on autocorrelated data carry ~n/k independent points."""
    return nominal / k
