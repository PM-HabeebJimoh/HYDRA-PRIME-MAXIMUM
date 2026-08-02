"""2026 XLM shows vol persistence -0.3038 (NEGATIVE). The system assumes it is
POSITIVE. Before concluding anything, measure the SAME statistic on the
2018-2021 data the system was built on, at the SAME 6h timeframe and SAME n.
If 2018-21 is also negative at n=126, the metric is just noisy at small n."""
import numpy as np, math, sys, os, json
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from load import load_1m, resample
def roll(x,k,fn='mean'):
    N=len(x);o=np.full(N,np.nan);v=np.nan_to_num(x)
    c=np.cumsum(np.insert(v,0,0.0));m=(c[k:]-c[:-k])/k
    if fn=='mean': o[k-1:]=m
    else:
        c2=np.cumsum(np.insert(v*v,0,0.0));var=(c2[k:]-c2[:-k])/k-m*m
        o[k-1:]=np.sqrt(np.maximum(var,0.0)*k/(k-1))
    return o
def persistence(c,W=4):
    N=len(c)
    r=np.zeros(N); r[1:]=np.log(np.maximum(c[1:],1e-12)/np.maximum(c[:-1],1e-12))
    s20=roll(r,20,'std')
    idx=np.arange(60,N-W-1)
    if len(idx)<50: return np.nan,0
    fwd=np.array([np.max(np.abs(c[i+1:i+1+W]-c[i]))/c[i] for i in idx])
    m=np.isfinite(s20[idx])&np.isfinite(fwd)
    if m.sum()<50: return np.nan,0
    return np.corrcoef(s20[idx][m],fwd[m])[0,1], m.sum()
print("VOL PERSISTENCE corr(trailing 20-bar vol, forward 4-bar |move|), 6h bars")
print()
print("--- 2018-2021 Bitfinex SPOT, full history ---")
alls=[]
for s in ['XLM','TRX','BTC','ETH','XRP','EOS','LTC','NEO','XMR','ETC','IOT','BSV','XTZ']:
    a=load_1m(s)
    if a is None: continue
    f=resample(a,360)      # 6h
    c=f[:,2]
    p,n=persistence(c)
    if np.isfinite(p): alls.append(p); print("   %-5s n=%5d  %+.4f"%(s,n,p))
print("   MEAN %+.4f  (positive on %d/%d)"%(np.mean(alls),sum(1 for x in alls if x>0),len(alls)))
print()
print("--- SAME metric, but SUBSAMPLED to n=126 like the 2026 sample ---")
rng=np.random.default_rng(0)
sub=[]
a=load_1m('XLM'); f=resample(a,360); c=f[:,2]
N=len(c)
for _ in range(40):
    st=rng.integers(60,max(61,N-200))
    seg=c[st:st+186]
    if len(seg)<150: continue
    p,n=persistence(seg)
    if np.isfinite(p): sub.append(p)
sub=np.array(sub)
print("   40 random 186-bar windows of 2018-21 XLM:")
print("   mean %+.4f  min %+.4f  max %+.4f  NEGATIVE in %d/%d windows"%(
    sub.mean(),sub.min(),sub.max(),(sub<0).sum(),len(sub)))
print()
print("   2026 XLM measured: -0.3038 (n=126)")
pct=100*(sub<=-0.3038).mean()
print("   -> %.1f%% of 2018-21 windows are AT LEAST as negative"%pct)
