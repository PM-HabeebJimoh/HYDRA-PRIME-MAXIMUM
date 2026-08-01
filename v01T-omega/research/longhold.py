"""The signal INVERTS sign around bar 12. V82 exits at 12 -- precisely at the
zero crossing, capturing the negative half and none of the positive half.
Test: hold 48 bars, executable next-open fill, honest gap fills."""
from load import *; from v82 import *
import numpy as np, bisect, sys
sys.path.insert(0,'/home/user/HYDRA-PRIME-MAXIMUM/v01T-omega')
from omega.indicators import bb_percent
HB=3600000.0

def harv(f,h,hold,tm,bb_lo=40.0,cost=0.02,sl=1.0):
    tu,td,r3,st=compute_1h_forecast(h); A=np.concatenate([[np.nan],atr(f)[:-1]])
    C=f[:,2]; bb=bb_percent(C); ht=list(h[:,0]); O,H,L=f[:,1],f[:,3],f[:,4]
    out=[];busy=-1
    for i in range(60,len(f)-hold-3):
        if i<busy: continue
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
        stop=S-d*sl*a; targ=S+d*tm*a; ex=None; jj=e+hold
        for j in range(e+1,e+hold+1):
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
            jj=min(e+hold,len(f)-1); ex=C[jj]
        out.append((f[i,0],f[jj,0],(ex-S)*d/a-cost)); busy=jj
    return out

syms=['XLM','TRX','BTC','ETH','XRP','EOS','LTC','NEO','XMR','ETC','IOT','BSV','XTZ']
D={}
for s in syms:
    a=load_1m(s)
    if a is None or len(a)<50000: continue
    D[s]=(resample(a,5),resample(a,60))
print("EXECUTABLE (next-open fill, causal 1H). Varying HOLD and STOP:")
print("%-22s %8s %8s %10s %8s"%("config","n","WR%","meanR","t"))
best=None
for hold,tm,sl in [(12,3,1),(24,3,1),(48,3,1),(48,6,2),(48,4,2),(48,6,3),(96,6,3),(48,8,3)]:
    rec=[]
    for s,(f,h) in D.items():
        for (t0,t1,R) in harv(f,h,hold,tm,sl=sl): rec.append((t0,t1,R,0,0))
    A=np.array(rec,dtype=float); R=A[:,2]
    se=R.std(ddof=1)/np.sqrt(len(R))
    lbl="hold%d T%dR SL%dR"%(hold,tm,sl)
    print("%-22s %8d %8.2f %+10.4f %+8.2f"%(lbl,len(R),100*(R>0).mean(),R.mean(),R.mean()/se))
    if best is None or R.mean()>best[0]: best=(R.mean(),lbl,A)
print("\nBEST: %s meanR %+.4f"%(best[1],best[0]))
np.save('/tmp/v82/ev_best.npy',best[2][np.argsort(best[2][:,0])])
