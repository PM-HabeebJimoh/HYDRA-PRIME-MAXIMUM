"""THE REAL FIX. v01T's thesis is RIGHT (squeeze -> movement, t=+11).
Its EXECUTION is wrong: a 0.05% stop inside a 2.24% move is noise.

A straddle whose legs both stay open until one target hits is NOT a straddle
with stops - it is a pure LONG-VOLATILITY position. Its payoff is |move| - cost.
No stop can be hit because there is no stop. Test that directly, path-resolved."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import load_1m, resample
import numpy as np
from still import bb_hv_vec, SY

def run(tf_min, W, tp, cost_price, use_gate=True):
    """Long-vol straddle, NO STOPS. Exit when |move| >= tp or window ends.
    Payoff = (realised |move at exit| - cost) as fraction of PRICE."""
    out=[]
    for s in SY:
        a=load_1m(s)
        if a is None or len(a)<50000: continue
        f=resample(a,tf_min); c=f[:,2]; h=f[:,3]; l=f[:,4]; t=f[:,0]
        if len(c)<200: continue
        bb,hv=bb_hv_vec(c)
        sc=np.where(bb<10,92,np.where(bb>90,85,72))
        elite=((bb<10)|(bb>90))&(hv<0.8)&(sc>=85)
        N=len(c)
        i=30; busy=-1
        while i < N-W-1:
            if not (elite[i] if use_gate else True):
                i+=1; continue
            if i<busy: i+=1; continue
            e=i+1                       # EXECUTABLE: enter next bar open
            entry=f[e,1]
            hit=None
            for k in range(0,W):
                j=e+k
                if j>=N: break
                up=(h[j]-entry)/entry; dn=(entry-l[j])/entry
                if max(up,dn)>=tp:
                    hit=tp; break
            if hit is None:
                j=min(e+W-1,N-1)
                hit=abs(c[j]-entry)/entry
            out.append(hit-cost_price)
            busy=e+W
            i=e+W
    return np.array(out)

print("="*78)
print("LONG-VOL STRADDLE, NO STOPS — payoff = |move| - cost, as %% of PRICE")
print("="*78)
print("%-30s %8s %11s %10s %8s"%("config","n","mean%","t","ann.Sharpe"))
for tf,W,label in ((60,4,'1h x 4 bars = 4h'),(60,12,'1h x 12 bars = 12h'),(60,24,'1h x 24 = 1d')):
    for tp in (0.005,0.01,0.02):
        for fee,fl in ((0.0016,'4bp'),(0.0026,'6.5bp')):
            r=run(tf,W,tp,fee)
            if len(r)<100: continue
            se=r.std(ddof=1)/np.sqrt(len(r))
            print("%-30s %8d %+10.4f%% %+10.2f"%("%s tp%.1f%% %s"%(label,100*tp,fl),len(r),100*r.mean(),r.mean()/se))
