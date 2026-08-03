"""
iter69c: netR is about -0.9R everywhere. That is not a signal problem - it means
COST is consuming ~90% of the stop distance. Compute the wall explicitly.

cost in R = cost_bp / (b * sigma_bp).  With BTC sigma(1m) ~ a few bp and
cost 5.65bp round trip, a 1-sigma stop is SMALLER than the cost itself.

So the fix is not a better formula - it is a WIDER STOP (bigger b*sigma), which
means a LONGER HORIZON. Quantify: what b*sigma makes cost < 10% of the stop?
Then re-run at that horizon.
"""
import numpy as np
def rstd(x,k):
    v=np.nan_to_num(x); o=np.full(len(x),np.nan)
    cs=np.cumsum(np.insert(v,0,0.0)); c2=np.cumsum(np.insert(v*v,0,0.0))
    m=(cs[k:]-cs[:-k])/k; var=(c2[k:]-c2[:-k])/k-m*m
    o[k-1:]=np.sqrt(np.maximum(var,0)); return o

A=np.load('/tmp/ticks/ohlc_BTCUSDT.npy')
c=A[:,4]; lc=np.log(np.maximum(c,1e-12))
ret=np.zeros(len(c)); ret[1:]=np.diff(lc)
s1=rstd(ret,60)
med=np.nanmedian(s1)*1e4
print("="*84)
print("THE COST WALL - BTCUSDT 1-minute")
print("="*84)
print(f"median 1-min sigma            = {med:.3f} bp")
print(f"round-trip cost               = 5.65 bp")
print(f"cost as multiple of 1-sigma   = {5.65/med:.2f}x")
print()
print("A stop at b*sigma costs (5.65 / (b*sigma)) in R units:")
print(f"{'b':>6}{'stop bp':>10}{'cost in R':>12}{'viable?':>10}")
for b in (1,2,3,5,10,20,40,80):
    stop=b*med
    print(f"{b:>6}{stop:>10.2f}{5.65/stop:>12.3f}{('YES' if 5.65/stop<0.10 else 'no'):>10}")
print()
print("Multi-bar sigma scales ~ sqrt(H). Horizon needed for a 1-sigma stop to")
print("be 10x the cost:")
for H in (1,5,15,60,240,1440):
    sH=med*np.sqrt(H)
    print(f"  H={H:>5} bars  sigma={sH:>8.2f} bp  cost/sigma={5.65/sH:>7.3f}  {'OK' if 5.65/sH<0.10 else ''}")
