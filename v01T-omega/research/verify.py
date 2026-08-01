"""Is the CAUSAL +0.1489R real? Controls + OOS."""
import numpy as np, datetime as dt
A=np.load('/tmp/v82/events_causal.npy'); A=A[np.argsort(A[:,0])]
R=A[:,2]
print("CAUSAL EDGE: n=%d meanR %+.4f  WR %.2f%%  t=%.1f"%(len(R),R.mean(),100*(R>0).mean(),
    R.mean()/(R.std(ddof=1)/np.sqrt(len(R)))))
rng=np.random.default_rng(1)
b=np.array([rng.choice(R,len(R),replace=True).mean() for _ in range(2000)])
print("bootstrap 2000x: 95%% CI %+.4f to %+.4f  P(mean<=0)=%.4f"%(
    np.percentile(b,2.5),np.percentile(b,97.5),(b<=0).mean()))
SPLIT=dt.datetime(2020,1,1).timestamp()*1000
tr=R[A[:,1]<SPLIT]; te=R[A[:,0]>=SPLIT]
print("\nOOS: train n=%d meanR %+.4f  |  TEST n=%d meanR %+.4f"%(len(tr),tr.mean(),len(te),te.mean()))
print("\nper-symbol:")
pos=0
for s in np.unique(A[:,3]).astype(int):
    v=R[A[:,3]==s]
    if len(v)<200: continue
    if v.mean()>0: pos+=1
    print("   sym %2d n=%6d meanR %+.4f WR %.2f%%"%(s,len(v),v.mean(),100*(v>0).mean()))
print("positive on %d symbols"%pos)
