"""THE INVERSION, TESTED PROPERLY.
Claim under test: after a v01T squeeze, a vol SELLER has an edge.
Edge proxy = (premium a maker would charge) - (realised forward move).
Premium proxy = trailing realised max-move over the SAME horizon (causal).
Control = identical measurement on non-squeeze bars.
Real Bitfinex 1m data, 13 instruments, resampled to 1h."""
from load import load_1m, resample
import numpy as np

def bb_hv(c):
    n=len(c)
    bb=np.full(n,np.nan); hv=np.full(n,np.nan)
    # BB% 20, population stdev
    cs=np.cumsum(np.insert(c,0,0.0)); cs2=np.cumsum(np.insert(c*c,0,0.0))
    m=(cs[20:]-cs[:-20])/20.0
    ms=(cs2[20:]-cs2[:-20])/20.0
    sd=np.sqrt(np.maximum(ms-m*m,0.0))
    up=m+2*sd; lo=m-2*sd; w=up-lo
    idx=np.arange(19,n)
    good=w>0
    bb[idx[good]]=(c[idx[good]]-lo[good])/w[good]*100.0
    # HV ratio: stdev(5 rets)/stdev(20 rets), sample
    r=np.zeros(n); r[1:]=np.diff(c)/c[:-1]
    def rstd(x,k):
        a=np.cumsum(np.insert(x,0,0.0)); b=np.cumsum(np.insert(x*x,0,0.0))
        mm=(a[k:]-a[:-k])/k; ss=(b[k:]-b[:-k])/k
        v=np.maximum(ss-mm*mm,0.0)*k/(k-1.0)
        return np.sqrt(v)
    s5=rstd(r,5); s20=rstd(r,20)
    i5=np.arange(4,n); i20=np.arange(19,n)
    a5=np.full(n,np.nan); a5[i5]=s5
    a20=np.full(n,np.nan); a20[i20]=s20
    ok=np.isfinite(a5)&np.isfinite(a20)&(a20>0)
    hv[ok]=a5[ok]/a20[ok]
    hv[:21]=np.nan
    return bb,hv

H=4
SYMS=['XLM','TRX','BTC','ETH','XRP','EOS','LTC','NEO','XMR','ETC','IOT','BSV','XTZ']
S_ed=[]; N_ed=[]
for nm in SYMS:
    raw=load_1m(nm)
    if raw is None or len(raw)<50000: continue
    f=resample(raw,60)
    c=f[:,2]
    if len(c)<200: continue
    bb,hv=bb_hv(c)
    n=len(c)
    i=np.arange(H+20,n-H-1)
    e0=c[i]
    # forward max |move| over H bars
    fwd=np.zeros(len(i))
    for k in range(1,H+1): fwd=np.maximum(fwd,np.abs(c[i+k]-e0)/e0)
    # trailing max |move| over H bars, ending at i (causal)
    base=c[i-H]
    tr=np.zeros(len(i))
    for k in range(H-1,-1,-1): tr=np.maximum(tr,np.abs(c[i-k]-base)/base)
    edge=100*(tr-fwd)
    sq=((bb[i]<10)|(bb[i]>90))&(hv[i]<0.8)
    sq=np.nan_to_num(sq,nan=False).astype(bool)
    S_ed.append(edge[sq]); N_ed.append(edge[~sq])
    print("%-5s bars=%6d squeezes=%5d"%(nm,len(c),sq.sum()),flush=True)
S=np.concatenate(S_ed); N=np.concatenate(N_ed)
def rep(lbl,x):
    se=x.std(ddof=1)/np.sqrt(len(x))
    print("%-14s n=%7d  mean(trail-fwd) %+.5f%%  SE %.5f  t=%+7.2f"%(lbl,len(x),x.mean(),se,x.mean()/se))
    return x.mean(),se
print()
print("="*74); print("VOL-SELLING EDGE AFTER v01T SQUEEZE — 13 instruments, real 1h data"); print("="*74)
ms,ses=rep("SQUEEZE",S); mn,sen=rep("NON-SQUEEZE",N)
d=ms-mn; sd=np.sqrt(ses**2+sen**2)
print()
print("DIFFERENCE (squeeze - control) = %+.5f%%  SE %.5f  t=%+.2f"%(d,sd,d/sd))
print()
if d/sd>2: print("VERDICT: squeeze-specific vol-selling edge IS significant.")
else: print("VERDICT: NO squeeze-specific edge. Any premium is generic, not v01T.")
