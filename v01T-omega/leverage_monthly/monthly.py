"""MONTH-BY-MONTH breakdown of the EXACT system that produced +1,234%/mo.
Same arrays, same slice, same costs, same leverage as capacity/lev2550.py.
The only change: split the equity path by calendar month instead of reporting
one blended CAGR."""
import numpy as np, datetime as dt
SPREAD={'BTC':1.649,'NEO':12.802,'LTC':1.153}
FEE=4.0
def load(nm,slice_frac=0.005):
    p=np.load('/tmp/ticks/xex_%s.npy'%nm)
    y=np.load('/tmp/ticks/xexy_%s.npy'%nm)
    t=np.load('/tmp/ticks/xext_%s.npy'%nm)
    v=np.isfinite(p); p=p[v];y=y[v];t=t[v]
    k=int(len(p)*slice_frac)
    sel=np.argsort(-np.abs(p))[:k]
    sel=sel[np.argsort(t[sel])]
    r=np.sign(p[sel])*y[sel]-(SPREAD[nm]+FEE)*1e-4
    return r, t[sel]
def monthly(nm,lev):
    r,t=load(nm)
    lab=np.array([dt.datetime.utcfromtimestamp(x).strftime('%Y-%m') for x in t])
    out=[]
    for m in sorted(set(lab)):
        k=lab==m
        rr=r[k]
        if len(rr)<3: 
            out.append((m,len(rr),None,None,None)); continue
        cap=1.0;peak=1.0;dd=0.0;bust=False
        for x in rr:
            cap*=(1.0+lev*x)
            if cap<=0: bust=True;cap=0.0;break
            peak=max(peak,cap);dd=max(dd,(peak-cap)/peak)
        wr=100*(rr>0).mean()
        out.append((m,len(rr),(cap-1.0) if not bust else -1.0,dd,wr))
    return out
for nm,lev in (('NEO',50),('LTC',25),('LTC',50),('NEO',25)):
    rows=monthly(nm,lev)
    print("="*78)
    print("%s at %dx — the system that reported +1,234%%/mo (NEO50) / +1,398%%/mo (LTC25)"%(nm,lev))
    print("="*78)
    print("%-9s %7s %14s %10s %8s"%("month","trades","MONTH RETURN","maxDD","WR%"))
    vals=[]
    for m,n,ret,dd,wr in rows:
        if ret is None:
            print("%-9s %7d   (too few trades)"%(m,n)); continue
        vals.append(ret)
        flag=" BUST" if ret<=-1.0 else ""
        print("%-9s %7d %+13.2f%% %9.2f%% %7.1f%%%s"%(m,n,100*ret,100*dd,wr,flag))
    v=np.array(vals)
    if len(v):
        print("-"*78)
        print("months: %d | positive: %d | median %+.2f%% | mean %+.2f%% | worst %+.2f%%"%(
            len(v),(v>0).sum(),100*np.median(v),100*v.mean(),100*v.min()))
    print()
