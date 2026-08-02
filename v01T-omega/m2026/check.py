"""Both negative. Before concluding: is this a 2026 REGIME effect, or does the
daily timeframe / n~25 make the statistic unreliable? Test the null."""
import json, numpy as np, math
D=json.load(open('/tmp/m2026.json'))
def roll(x,k):
    N=len(x);o=np.full(N,np.nan);v=np.nan_to_num(x)
    c=np.cumsum(np.insert(v,0,0.0));c2=np.cumsum(np.insert(v*v,0,0.0))
    m=(c[k:]-c[:-k])/k; var=(c2[k:]-c2[:-k])/k-m*m
    o[k-1:]=np.sqrt(np.maximum(var,0.0)*k/(k-1)); return o
def persist(c,W=3):
    c=np.array(c,float); N=len(c)
    r=np.zeros(N); r[1:]=np.log(np.maximum(c[1:],1e-12)/np.maximum(c[:-1],1e-12))
    s=roll(r,20); idx=np.arange(25,N-W-1)
    if len(idx)<20: return np.nan
    fwd=np.array([np.max(np.abs(c[i+1:i+1+W]-c[i]))/c[i] for i in idx])
    m=np.isfinite(s[idx])&np.isfinite(fwd)
    return np.corrcoef(s[idx][m],fwd[m])[0,1] if m.sum()>15 else np.nan
for k,lab in (('eur','EURUSD'),('btc','BTC-USD')):
    c=D[k]['c']
    full=persist(c)
    print("%-8s FULL-SAMPLE 2026 vol persistence (n=%d bars): %+.4f"%(lab,len(c),full))
print()
print("NULL TEST: how negative can this get by chance at n~25?")
rng=np.random.default_rng(0)
sims=[]
for _ in range(2000):
    x=np.cumprod(1+rng.normal(0,0.02,55))*100
    v=persist(x)
    if np.isfinite(v): sims.append(v)
sims=np.array(sims)
print("  random walk, 55 bars, %d sims"%len(sims))
print("  mean %+.4f  p5 %+.4f  p50 %+.4f  p95 %+.4f"%(sims.mean(),np.percentile(sims,5),np.median(sims),np.percentile(sims,95)))
print("  fraction NEGATIVE: %.1f%%"%(100*(sims<0).mean()))
print()
for k,lab,obs in (('eur','EURUSD',-0.2832),('btc','BTC-USD',-0.2050)):
    pct=100*(sims<=obs).mean()
    print("  %-8s observed monthly-mean %+.4f -> %.1f%% of random walks are this negative"%(lab,obs,pct))
