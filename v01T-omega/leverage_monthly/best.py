"""LTC 10% slice: 24,632 trades, weakest month +38.99%, needs only 5x for 500%
and 10x for 5000%. Run the real paths and check liquidation headroom."""
import numpy as np, datetime as dt
SPREAD={'BTC':1.649,'NEO':12.802,'LTC':1.153}; FEE=4.0
DROP={'2018-11','2019-11'}
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
for sf,levs in ((0.10,(5,10,15)),):
    r,L=build('LTC',sf)
    print("LTC slice %.0f%%  n=%d  worst single trade %.3f%%"%(100*sf,len(r),100*r.min()))
    for lev in levs:
        print()
        print("=== LTC %.0f%% slice at %dx : liquidation @ %.3f%% ==="%(100*sf,lev,100.0/lev))
        print("%-9s %8s %14s %10s %8s"%("month","trades","MONTH RETURN","maxDD","WR%"))
        vals=[];bust=0
        for m in sorted(set(L)):
            rr=r[L==m]
            cap=1.0;peak=1.0;dd=0.0;b=False
            for x in rr:
                cap*=(1.0+lev*x)
                if cap<=0: b=True;cap=0.0;break
                peak=max(peak,cap);dd=max(dd,(peak-cap)/peak)
            if b: bust+=1
            vals.append(cap-1.0)
            print("%-9s %8d %+13.2f%% %9.2f%% %7.1f%%%s"%(m,len(rr),100*(cap-1),100*dd,100*(rr>0).mean()," BUST" if b else ""))
        v=np.array(vals)
        print("  >=500%%: %d/%d | >=5000%%: %d/%d | worst %+.2f%% | maxDD %.1f%% | busts %d"%(
            (v>=5.0).sum(),len(v),(v>=50.0).sum(),len(v),100*v.min(),100*max(0,0),bust))
        print("  worst trade at %dx = %.2f%%  vs liq %.3f%%  -> %s"%(
            lev,100*lev*r.min(),100.0/lev,"SAFE" if abs(100*lev*r.min())<100.0/lev*100 else "check"))
