"""INVERSION: iter29 fixed the 1H leak. But I never audited the 5m ENTRY bar.

V82 enters at C[i] = the CLOSE of 5m bar i, using signals computed from bar i.
BB%(i) uses C[i]. ATR is already shifted. But entering AT C[i] means you must
KNOW C[i] to decide -- and C[i] only exists when bar i has closed.
In reality you decide at C[i] and fill at O[i+1]. Test the gap.
"""
from load import *; from v82 import *
import numpy as np, bisect, sys
sys.path.insert(0,'/home/user/HYDRA-PRIME-MAXIMUM/v01T-omega')
from omega.indicators import bb_percent
HB=3600000.0

def harv(f,h,entry='close_same_bar',bb_lo=40.0,tm=3.0,cost=0.02):
    tu,td,r3,st=compute_1h_forecast(h); A=np.concatenate([[np.nan],atr(f)[:-1]])
    C=f[:,2]; bb=bb_percent(C); ht=list(h[:,0]); O,H,L=f[:,1],f[:,3],f[:,4]
    out=[];busy=-1
    for i in range(60,len(f)-13):
        if i<busy: continue
        k=bisect.bisect_right(ht,f[i,0]-HB)-1     # causal 1H (iter29 fix)
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
        if entry=='close_same_bar': S=C[i]; e=i        # iter29: fill at signal bar close
        else:                       S=O[i+1]; e=i+1    # realistic: fill next open
        stop=S-d*a; targ=S+d*tm*a; ex=None; jj=e+12
        for j in range(e+1,e+13):
            if j>=len(f): break
            op=O[j]
            if d==1:
                if op<=stop or op>=targ: ex=op;jj=j;break
                if L[j]<=stop: ex=stop;jj=j;break
                if H[j]>=targ: ex=targ;jj=j;break
            else:
                if op>=stop or op<=targ: ex=op;jj=j;break
                if H[j]>=stop: ex=stop;jj=j;break
                if L[j]<=targ: ex=targ;jj=j;break
        if ex is None:
            jj=min(e+12,len(f)-1); ex=C[jj]
        out.append((f[i,0],f[jj,0],(ex-S)*d/a-cost)); busy=jj
    return out

syms=['XLM','TRX','BTC','ETH','XRP','EOS','LTC','NEO','XMR','ETC','IOT','BSV','XTZ']
for mode in ('close_same_bar','next_open'):
    rec=[]
    for si,s in enumerate(syms):
        a=load_1m(s)
        if a is None or len(a)<50000: continue
        f=resample(a,5); h=resample(a,60)
        for (t0,t1,R) in harv(f,h,entry=mode): rec.append((t0,t1,R,si,0))
    Ar=np.array(rec,dtype=float); Ar=Ar[np.argsort(Ar[:,0])]
    R=Ar[:,2]
    print("%-16s n=%6d  WR %.2f%%  meanR %+.4f  t=%.1f"%(mode,len(R),100*(R>0).mean(),
          R.mean(),R.mean()/(R.std(ddof=1)/np.sqrt(len(R)))))
    np.save('/tmp/v82/ev_%s.npy'%mode,Ar)
