"""WR 34.69% still beats the 25% random baseline by 9.7 points -- yet meanR is
NEGATIVE. That means the barrier geometry, not the signal, is the problem.
Test: does the signal predict anything executable at all?
Measure FORWARD RETURN from the next open, with NO barriers (pure directional).
"""
from load import *; from v82 import *
import numpy as np, bisect, sys
sys.path.insert(0,'/home/user/HYDRA-PRIME-MAXIMUM/v01T-omega')
from omega.indicators import bb_percent
HB=3600000.0
rng=np.random.default_rng(5)

def fwd(f,h,bb_lo=40.0,horizons=(1,3,6,12,24,48)):
    tu,td,r3,st=compute_1h_forecast(h); A=np.concatenate([[np.nan],atr(f)[:-1]])
    C=f[:,2]; bb=bb_percent(C); ht=list(h[:,0]); O=f[:,1]
    res={k:[] for k in horizons}; ctl={k:[] for k in horizons}
    for i in range(60,len(f)-60):
        k=bisect.bisect_right(ht,f[i,0]-HB)-1
        if k<60: continue
        a=A[i]
        if not np.isfinite(a) or a<=0: continue
        b=bb[i]
        if not np.isfinite(b): continue
        if tu[k] and st[k]>=2 and r3[k]>0: d=1
        elif td[k] and st[k]<=1 and r3[k]<0: d=-1
        else: continue
        if d==1 and not b<bb_lo: continue
        if d==-1 and not b>100-bb_lo: continue
        e=i+1; S=O[e]
        dr=1 if rng.random()<0.5 else -1
        for H in horizons:
            j=e+H
            if j>=len(f): break
            res[H].append((O[j]-S)*d/a)
            ctl[H].append((O[j]-S)*dr/a)
    return res,ctl

syms=['XLM','TRX','BTC','ETH','XRP','EOS','LTC','NEO','XMR','ETC','IOT','BSV','XTZ']
agg={};ac={}
for s in syms:
    a=load_1m(s)
    if a is None or len(a)<50000: continue
    f=resample(a,5); h=resample(a,60)
    r,c=fwd(f,h)
    for k in r:
        agg.setdefault(k,[]).extend(r[k]); ac.setdefault(k,[]).extend(c[k])
print("PURE DIRECTIONAL FORWARD RETURN (in ATR units) from NEXT OPEN — no barriers")
print("%-8s %9s %11s %9s %11s %9s"%("horizon","n","signal","t","random","edge"))
for k in sorted(agg):
    v=np.array(agg[k]); c=np.array(ac[k])
    se=v.std(ddof=1)/np.sqrt(len(v))
    print("%-8s %9d %+11.5f %+9.2f %+11.5f %+9.5f"%("%dx5m"%k,len(v),v.mean(),v.mean()/se,c.mean(),v.mean()-c.mean()))
