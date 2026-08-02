"""FIXED: drop the two PARTIAL months (2018-11 = 3 days, 2019-11 = 17 days).
Those were my 'weakest months' and they set the required leverage.
Re-run on the 11 COMPLETE months only, honest per-month ranking."""
import numpy as np, datetime as dt, math
SPREAD={'BTC':1.649,'NEO':12.802,'LTC':1.153}; FEE=4.0
DROP={'2018-11','2019-11'}
def build(nm):
    p=np.load('/tmp/ticks/xex_%s.npy'%nm); y=np.load('/tmp/ticks/xexy_%s.npy'%nm); t=np.load('/tmp/ticks/xext_%s.npy'%nm)
    v=np.isfinite(p); p=p[v];y=y[v];t=t[v]
    lab=np.array([dt.datetime.utcfromtimestamp(x).strftime('%Y-%m') for x in t])
    sel=[]
    for m in sorted(set(lab)):
        if m in DROP: continue
        idx=np.flatnonzero(lab==m)
        k=max(1,int(len(idx)*0.005))
        sel.append(idx[np.argsort(-np.abs(p[idx]))[:k]])
    sel=np.concatenate(sel); sel=sel[np.argsort(t[sel])]
    r=np.sign(p[sel])*y[sel]-(SPREAD[nm]+FEE)*1e-4
    return r, lab[sel]
need5000=math.log(51.0); need500=math.log(6.0)
for nm in ('NEO','LTC'):
    r,L=build(nm)
    print("=== %s : 11 COMPLETE months only ==="%nm)
    print("%-9s %7s %11s %13s %13s"%("month","trades","sum_edge","lev for 500%","lev for 5000%"))
    ses=[]
    for m in sorted(set(L)):
        rr=r[L==m]; s=rr.sum(); ses.append((m,s))
        print("%-9s %7d %10.2f%% %12.0fx %12.0fx"%(m,len(rr),100*s,need500/s if s>0 else 9e9,need5000/s if s>0 else 9e9))
    v=np.array([s for _,s in ses])
    w=v.min()
    print("  weakest complete month: %.2f%%"%(100*w))
    print("  lev needed EVERY month >=500%%  : %.0fx  (liq @ %.3f%%)"%(need500/w,100.0/(need500/w)))
    print("  lev needed EVERY month >=5000%% : %.0fx  (liq @ %.3f%%)"%(need5000/w,100.0/(need5000/w)))
    print("  measured worst 1-min move 1.39%% -> liquidated? %s / %s"%(
        "YES" if 1.39>=100.0/(need500/w) else "no", "YES" if 1.39>=100.0/(need5000/w) else "no"))
    print()
