"""hold48 T8R SL3R gives +0.0367R t=+2.09. That is WEAK and I have been fooled
twice already. Test it the way it deserves: OOS + multiple-testing correction."""
import numpy as np, datetime as dt
A=np.load('/tmp/v82/ev_best.npy'); R=A[:,2]
n=len(R); se=R.std(ddof=1)/np.sqrt(n)
print("candidate: n=%d meanR %+.4f t=%+.2f"%(n,R.mean(),R.mean()/se))
print("\n1) MULTIPLE TESTING: I tried 8 configs. Bonferroni t threshold for")
print("   8 tests at p=0.05 two-sided is |t| > 2.73. Observed t=%+.2f -> %s"%(
    R.mean()/se, "PASSES" if abs(R.mean()/se)>2.73 else "FAILS"))
SPLIT=dt.datetime(2020,1,1).timestamp()*1000
tr=R[A[:,1]<SPLIT]; te=R[A[:,0]>=SPLIT]
print("\n2) OOS split:")
for nm,v in (("train <2020",tr),("TEST >=2020",te)):
    if len(v)<50: continue
    s=v.std(ddof=1)/np.sqrt(len(v))
    print("   %-14s n=%6d meanR %+.4f t=%+.2f"%(nm,len(v),v.mean(),v.mean()/s))
print("\n3) cost sensitivity (baseline already includes 2% of stop):")
for extra in (0.02,0.05,0.10):
    v=R-extra
    s=v.std(ddof=1)/np.sqrt(len(v))
    print("   +%.0f%% extra cost -> meanR %+.4f t=%+.2f"%(100*extra,v.mean(),v.mean()/s))
print("\n4) bootstrap:")
rng=np.random.default_rng(2)
bs=np.array([rng.choice(R,n,replace=True).mean() for _ in range(2000)])
print("   95%% CI %+.4f to %+.4f   P(mean<=0)=%.4f"%(np.percentile(bs,2.5),np.percentile(bs,97.5),(bs<=0).mean()))
