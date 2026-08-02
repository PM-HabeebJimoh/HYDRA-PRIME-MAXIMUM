"""Do my winning trades sit AFTER a data gap (stale catch-up) or in
continuously-traded minutes (real, tradable)?
If accuracy collapses when I require BOTH the signal minute and the target
minute to be genuinely consecutive with real volume, the edge is fake."""
import numpy as np, sys, os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from load import load_1m
p=np.load('/tmp/ticks/xex_NEO.npy'); y=np.load('/tmp/ticks/xexy_NEO.npy'); t=np.load('/tmp/ticks/xext_NEO.npy')
v=np.isfinite(p); p=p[v];y=y[v];t=t[v].astype(np.int64)
a=load_1m('NEO')
bt=(a[:,0]/1000.0).astype(np.int64); bv=a[:,5]
S=set(bt.tolist())
VOL={int(x):float(z) for x,z in zip(bt,bv)}
# for each trade at minute t: was t-1 present? was t+1 present? volume at t+1?
prev_ok=np.array([ (x-60) in S for x in t])
next_ok=np.array([ (x+60) in S for x in t])
vol_next=np.array([ VOL.get(int(x+60),0.0) for x in t])
print("trades: %d"%len(t))
print("  prior minute has a bar : %.1f%%"%(100*prev_ok.mean()))
print("  NEXT minute has a bar  : %.1f%%"%(100*next_ok.mean()))
print("  next-minute volume median %.2f"%np.median(vol_next))
print()
def acc(mask,lbl,sf=0.005):
    if mask.sum()<100: print("  %-38s n too small"%lbl); return
    pp=p[mask];yy=y[mask]
    k=max(50,int(len(pp)*sf))
    sel=np.argsort(-np.abs(pp))[:k]
    a=100*(np.sign(pp[sel])==np.sign(yy[sel])).mean()
    bp=1e4*(np.sign(pp[sel])*yy[sel]).mean()
    print("  %-38s n=%6d  ACC %6.2f%%  %+8.2f bp"%(lbl,mask.sum(),a,bp))
print("ACCURACY AT TOP 0.5%, CONDITIONED ON DATA CONTINUITY")
acc(np.ones(len(t),bool),"ALL trades (my reported 86.98%)")
acc(prev_ok&next_ok,"BOTH neighbours present (no gap)")
acc(~(prev_ok&next_ok),"AT LEAST ONE neighbour missing (stale)")
q=np.quantile(vol_next[vol_next>0],0.5) if (vol_next>0).any() else 0
acc((prev_ok&next_ok)&(vol_next>=q),"no gap AND above-median next volume")
acc((prev_ok&next_ok)&(vol_next<q),"no gap AND below-median next volume")
