"""
ITERATION 5 - CROSS-VENUE MECHANICAL FORCING.

Every prior iteration looked for a STATISTICAL tendency inside one venue.
This one looks for a MECHANICAL constraint between two venues: when Coinbase and
Kraken disagree on the price of the same asset at the same instant, arbitrage
capital MUST close the gap. That is enforced by economics, not by a pattern.

Data: 100 timestamp-MATCHED 1-minute bars, real Coinbase BTC-USD and real Kraken
XBT/USD, 2026-07-28 02:55-04:34 UTC.

FINDING: the edge is REAL and strong (mean reversion t = -8.00; 92.31% win rate,
t = +6.03 at a 1bp threshold; it survives a VWAP re-specification at t = +7.79).
It is killed by EXECUTION, not by statistics - see fill_feasibility().
"""
import os, json, math

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
COINBASE = os.path.join(DATA, "coinbase_btc_1m_matched.json")
KRAKEN   = os.path.join(DATA, "kraken_btc_1m_vwap_trades.json")

# Public fee schedules at entry volume tier, basis points PER SIDE
COINBASE_TAKER_BP = 40.0
KRAKEN_TAKER_BP   = 26.0

def load_matched():
    """Timestamp-aligned closes. Returns (timestamps, coinbase, kraken, kraken_vwap)."""
    cb = {r[0]: r[4] for r in json.load(open(COINBASE))}
    krr = json.load(open(KRAKEN))
    kr = {r[0]: float(r[4]) for r in krr}
    kv = {r[0]: float(r[5]) for r in krr}
    ts = sorted(set(cb) & set(kr))
    return ts, [cb[t] for t in ts], [kr[t] for t in ts], [kv[t] for t in ts]

def dislocation_bp(a, b):
    """Cross-venue price gap in basis points."""
    return [(a[i] - b[i]) / b[i] * 10000 for i in range(len(a))]

def _corr(x, y):
    n = len(x)
    if n < 6: return None
    mx = sum(x)/n; my = sum(y)/n
    cov = sum((x[i]-mx)*(y[i]-my) for i in range(n))/n
    sx = math.sqrt(sum((v-mx)**2 for v in x)/n)
    sy = math.sqrt(sum((v-my)**2 for v in y)/n)
    if not sx or not sy: return None
    r = cov/(sx*sy)
    return dict(r=r, t=r*math.sqrt(n-2)/math.sqrt(max(1e-12, 1-r*r)), n=n)

def mean_reversion(spread):
    """Regress change-in-gap on level. Negative => the gap is forced closed."""
    lev = spread[:-1]
    d = [spread[i+1] - spread[i] for i in range(len(spread)-1)]
    c = _corr(lev, d)
    mx = sum(lev)/len(lev); my = sum(d)/len(d)
    cov = sum((lev[i]-mx)*(d[i]-my) for i in range(len(d)))/len(d)
    vx = sum((x-mx)**2 for x in lev)/len(lev)
    phi = cov/vx
    c['decay'] = phi
    c['half_life_bars'] = -math.log(2)/math.log(1+phi) if -1 < phi < 0 else float('nan')
    return c

def convergence_trades(spread, threshold_bp):
    """Fade the gap when |gap| > threshold; mark to the next bar. Gross, pre-cost."""
    out = []
    for i in range(len(spread)-1):
        if abs(spread[i]) < threshold_bp: continue
        out.append(-math.copysign(1, spread[i]) * (spread[i+1] - spread[i]))
    return out

def summary(pnl_bp):
    n = len(pnl_bp)
    if not n: return None
    m = sum(pnl_bp)/n
    sd = math.sqrt(sum((x-m)**2 for x in pnl_bp)/n)
    return dict(n=n, win_rate=sum(1 for x in pnl_bp if x > 0)/n*100,
                mean_bp=m, t_stat=(m/(sd/math.sqrt(n))) if sd else 0.0)

def fill_feasibility(threshold_bp=1.0):
    """
    THE CRUX. Capturing the gap as a maker needs BOTH passive legs to fill.
    Measure how often both venues actually move the favourable way.
    """
    ts, C, K, _ = load_matched()
    S = dislocation_bp(C, K)
    both = one = neither = 0
    for i in range(len(S)-1):
        if abs(S[i]) < threshold_bp: continue
        dc = (C[i+1]-C[i]); dk = (K[i+1]-K[i])
        if S[i] > 0: a, b = dc < 0, dk > 0      # CB rich
        else:        a, b = dc > 0, dk < 0      # CB cheap
        if a and b: both += 1
        elif a or b: one += 1
        else: neither += 1
    tot = both + one + neither
    return dict(episodes=tot, both=both, one_leg=one, neither=neither,
                both_pct=both/tot*100 if tot else 0.0)

def net_after_costs(gross_bp, crossed_legs=('kraken',)):
    """Subtract taker cost for each leg that must be crossed rather than posted."""
    c = 0.0
    for leg in crossed_legs:
        c += KRAKEN_TAKER_BP if leg == 'kraken' else COINBASE_TAKER_BP
    return gross_bp - c

def full_round_trip_taker_bp():
    return 2*COINBASE_TAKER_BP + 2*KRAKEN_TAKER_BP
