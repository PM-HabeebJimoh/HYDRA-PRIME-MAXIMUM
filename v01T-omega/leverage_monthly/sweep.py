"""I never re-optimised the SLICE. 0.5% was inherited from a DD-capped question.
The binding constraint now is the WEAKEST month's sum_edge. A wider slice has
lower edge/trade but MORE trades - sum_edge may RISE and, crucially, the weak
month may firm up. Sweep it."""
import numpy as np, datetime as dt, math
SPREAD={'BTC':1.649,'NEO':12.802,'LTC':1.153}; FEE=4.0
DROP={'2018-11','2019-11'}
need500=math.log(6.0); need5000=math.log(51.0)
def build(nm,sf):
    p=np.load('/tmp/ticks/xex_%s.npy'%nm); y=np.load('/tmp/ticks/xexy_%s.npy'%nm); t=np.load('/tmp/ticks/xext_%s.npy'%nm)
    v=np.isfinite(p); p=p[v];y=y[v];t=t[v]
    lab=np.array([dt.datetime.utcfromtimestamp(x).strftime('%Y-%m') for x in t])
    sel=[]
    for m in sorted(set(lab)):
        if m in DROP: continue
        idx=np.flatnonzero(lab==m)
        k=max(1,int(len(idx)*sf))
        sel.append(idx[np.argsort(-np.abs(p[idx]))[:k]])
    sel=np.concatenate(sel); sel=sel[np.argsort(t[sel])]
    return np.sign(p[sel])*y[sel]-(SPREAD[nm]+FEE)*1e-4, lab[sel]
print("SLICE SWEEP — weakest complete month drives everything")
print("%-5s %8s %8s %11s %11s %11s %11s %10s"%("sym","slice","trades","edge bp","weak mo","lev@500","lev@5000","liq@500"))
best={}
for nm in ('LTC','NEO'):
    for sf in (0.002,0.005,0.01,0.02,0.05,0.10,0.20,0.40,1.00):
        r,L=build(nm,sf)
        ses=np.array([r[L==m].sum() for m in sorted(set(L))])
        w=ses.min()
        if w<=0:
            print("%-5s %7.1f%% %8d %11.2f %10.2f%% %11s"%(nm,100*sf,len(r),1e4*r.mean(),100*w,"NEG"))
            continue
        l5=need500/w; l50=need5000/w
        print("%-5s %7.1f%% %8d %11.2f %10.2f%% %10.0fx %10.0fx %9.3f%%"%(
            nm,100*sf,len(r),1e4*r.mean(),100*w,l5,l50,100.0/l5))
        if nm not in best or w>best[nm][1]: best[nm]=(sf,w,l5,l50)
    print()
for nm,(sf,w,l5,l50) in best.items():
    print("BEST %s: slice %.1f%%  weakest month %.2f%%  ->  %.0fx for 500%%, %.0fx for 5000%%"%(
        nm,100*sf,100*w,l5,l50))
