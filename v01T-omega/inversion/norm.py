"""MY ERROR: I compared ABSOLUTE premium (0.19%) to ABSOLUTE fee (0.26%).
But an OPTION's price is not fixed - it scales with the vol used to price it.

HV ratio < 0.8 means recent realised vol is LOW. A short-dated option is priced
off recent realised vol. So at a squeeze the option is CHEAP in absolute terms,
while the forward move is LARGE. Cost scales DOWN, payoff scales UP.

The correct statistic is the RATIO: forward move / trailing vol.
That is exactly the option mispricing."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import load_1m, resample
import numpy as np
from still import bb_hv_vec, SY
W=4
rs=[];rb=[];hs=[];hb=[]
print("%-6s %8s %11s %11s %8s"%("sym","sq_n","sq ratio","base ratio","lift"),flush=True)
for s in SY:
    a=load_1m(s)
    if a is None or len(a)<50000: continue
    f=resample(a,60); c=f[:,2]
    if len(c)<200: continue
    bb,hv=bb_hv_vec(c)
    sc=np.where(bb<10,92,np.where(bb>90,85,72))
    el=((bb<10)|(bb>90))&(hv<0.8)&(sc>=85)
    r=np.zeros(len(c)); r[1:]=c[1:]/c[:-1]-1
    # trailing 5-bar vol = what prices a short-dated option
    N=len(c); sig=np.full(N,np.nan)
    cx=np.cumsum(np.insert(r,0,0.0)); cx2=np.cumsum(np.insert(r*r,0,0.0))
    k=5; m=(cx[k:]-cx[:-k])/k; v=(cx2[k:]-cx2[:-k])/k-m*m
    sig[k-1:]=np.sqrt(np.maximum(v,0.0)*k/(k-1))
    idx=np.arange(30,N-W)
    mx=np.max(np.stack([np.abs(c[idx+kk]-c[idx])/c[idx] for kk in range(1,W+1)]),axis=0)
    exp=sig[idx]*np.sqrt(W)               # expected move priced off recent vol
    ok=np.isfinite(exp)&(exp>1e-9)
    ratio=np.full(len(idx),np.nan); ratio[ok]=mx[ok]/exp[ok]
    e=el[idx]&ok; b=(~el[idx])&ok
    if e.sum()<20: continue
    rs.append(ratio[e]); rb.append(ratio[b]); hs.append(mx[e]); hb.append(mx[b])
    print("%-6s %8d %11.4f %11.4f %8.3f"%(s,e.sum(),ratio[e].mean(),ratio[b].mean(),ratio[e].mean()/ratio[b].mean()),flush=True)
RS=np.concatenate(rs);RB=np.concatenate(rb)
se=np.sqrt(RS.var(ddof=1)/len(RS)+RB.var(ddof=1)/len(RB))
print()
print("POOLED  squeeze %.4f (n=%d) | baseline %.4f (n=%d)"%(RS.mean(),len(RS),RB.mean(),len(RB)))
print("LIFT = %.4fx    difference %+.4f   t = %+.2f"%(RS.mean()/RB.mean(),RS.mean()-RB.mean(),(RS.mean()-RB.mean())/se))
print()
print("Interpretation: an option priced off trailing 5-bar vol pays out")
print("%.4fx more per unit premium after a squeeze than at a random bar."%(RS.mean()/RB.mean()))
