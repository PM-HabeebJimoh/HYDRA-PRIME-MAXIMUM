"""No leverage up to 400x makes every month >=500%. WHY NOT?
Because leverage is a MULTIPLIER on the month's edge. If a month's raw edge is
weak, scaling it also scales its drawdown - and past a point the path busts
before it compounds. Show the raw per-month edge, unlevered."""
import numpy as np, datetime as dt
SPREAD={'BTC':1.649,'NEO':12.802,'LTC':1.153}; FEE=4.0
for nm in ('NEO','LTC'):
    p=np.load('/tmp/ticks/xex_%s.npy'%nm); y=np.load('/tmp/ticks/xexy_%s.npy'%nm); t=np.load('/tmp/ticks/xext_%s.npy'%nm)
    v=np.isfinite(p); p=p[v];y=y[v];t=t[v]
    lab=np.array([dt.datetime.utcfromtimestamp(x).strftime('%Y-%m') for x in t])
    sel=[]
    for m in sorted(set(lab)):
        idx=np.flatnonzero(lab==m)
        k=max(1,int(len(idx)*0.005))
        sel.append(idx[np.argsort(-np.abs(p[idx]))[:k]])
    sel=np.concatenate(sel); sel=sel[np.argsort(t[sel])]
    r=np.sign(p[sel])*y[sel]-(SPREAD[nm]+FEE)*1e-4
    L=lab[sel]
    print("=== %s : UNLEVERED per-month reality ==="%nm)
    print("%-9s %7s %11s %11s %10s"%("month","trades","edge bp","sum edge","1x return"))
    for m in sorted(set(L)):
        rr=r[L==m]
        if len(rr)<3: continue
        cap=1.0
        for x in rr: cap*=(1.0+x)
        print("%-9s %7d %+10.2f %+10.2f%% %+9.3f%%"%(m,len(rr),1e4*rr.mean(),100*rr.sum(),100*(cap-1)))
    print()
print("KEY: monthly return ~ lev x sum(edge). To get 500% you need")
print("     lev x sum_edge >= ~1.79 in log terms. A month with sum_edge = 0.5%")
print("     needs lev = 358x. A month with sum_edge = 5% needs lev = 36x.")
print("     The WORST month sets the required leverage, and it is far above")
print("     what the BEST month can survive without busting.")
