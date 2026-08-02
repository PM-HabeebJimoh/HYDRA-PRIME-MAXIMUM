"""My SAFE check was garbage. Do it properly: at leverage L a single trade of
return x wipes the account if L*x <= -1, i.e. x <= -1/L. Count real breaches."""
import numpy as np, datetime as dt
SPREAD={'LTC':1.153}; FEE=4.0; DROP={'2018-11','2019-11'}
def build(sf):
    nm='LTC'
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
    return np.sign(p[sel])*y[sel]-(SPREAD[nm]+FEE)*1e-4
for sf in (0.005,0.10):
    r=build(sf)
    print("LTC slice %.1f%%  n=%d  worst trade %.3f%%  p0.1 %.3f%%"%(
        100*sf,len(r),100*r.min(),100*np.percentile(r,0.1)))
    print("  %-6s %12s %14s %12s"%("lev","liq at","trades <= liq","% of trades"))
    for lev in (5,10,15,25,38,50,84):
        thr=-1.0/lev
        n=(r<=thr).sum()
        print("  %5dx %11.3f%% %14d %11.4f%%  %s"%(lev,100*thr,n,100*n/len(r),
            "WIPES" if n>0 else "safe"))
    print()
