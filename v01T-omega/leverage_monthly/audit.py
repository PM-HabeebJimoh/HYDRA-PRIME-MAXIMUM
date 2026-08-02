"""13 of 13 months positive on all four configs. That is the signature of an
artifact, not a strategy. Two things must be checked before this is reportable.

1. SELECTION BIAS: the top 0.5% slice is chosen using |prediction| over the
   WHOLE sample. Confidence ranking is global, so which trades land in which
   month is decided with knowledge of the full period.
2. WALK-FORWARD COVERAGE: the model only produces out-of-sample predictions
   after the first training fold. Check when OOS actually starts."""
import numpy as np, datetime as dt
SPREAD={'BTC':1.649,'NEO':12.802,'LTC':1.153}; FEE=4.0
for nm in ('NEO','LTC'):
    p=np.load('/tmp/ticks/xex_%s.npy'%nm)
    y=np.load('/tmp/ticks/xexy_%s.npy'%nm)
    t=np.load('/tmp/ticks/xext_%s.npy'%nm)
    v=np.isfinite(p)
    print("=== %s ==="%nm)
    print("  total rows in array      : %d"%len(p))
    print("  rows with OOS prediction : %d (%.1f%%)"%(v.sum(),100*v.mean()))
    tv=t[v]
    print("  OOS window               : %s -> %s"%(
        dt.datetime.utcfromtimestamp(tv.min()).strftime('%Y-%m-%d'),
        dt.datetime.utcfromtimestamp(tv.max()).strftime('%Y-%m-%d')))
    ta=t[np.isfinite(t)]
    print("  FULL data window         : %s -> %s"%(
        dt.datetime.utcfromtimestamp(ta.min()).strftime('%Y-%m-%d'),
        dt.datetime.utcfromtimestamp(ta.max()).strftime('%Y-%m-%d')))
    # global-vs-monthly selection
    pv=p[v]; yv=y[v]
    k=int(len(pv)*0.005)
    glob=np.argsort(-np.abs(pv))[:k]
    lab=np.array([dt.datetime.utcfromtimestamp(x).strftime('%Y-%m') for x in tv])
    print("  top-0.5%% trades per month (GLOBAL ranking):")
    u,c=np.unique(lab[glob],return_counts=True)
    print("    "+"  ".join("%s:%d"%(a,b) for a,b in zip(u,c)))
    # honest alternative: rank WITHIN each month
    r_g=np.sign(pv[glob])*yv[glob]-(SPREAD[nm]+FEE)*1e-4
    sel_m=[]
    for m in sorted(set(lab)):
        idx=np.flatnonzero(lab==m)
        kk=max(1,int(len(idx)*0.005))
        sel_m.append(idx[np.argsort(-np.abs(pv[idx]))[:kk]])
    sel_m=np.concatenate(sel_m)
    r_m=np.sign(pv[sel_m])*yv[sel_m]-(SPREAD[nm]+FEE)*1e-4
    print("  mean edge, GLOBAL top0.5%%  : %+.2f bp (n=%d)"%(1e4*r_g.mean(),len(r_g)))
    print("  mean edge, PER-MONTH top0.5%%: %+.2f bp (n=%d)"%(1e4*r_m.mean(),len(r_m)))
    print()
